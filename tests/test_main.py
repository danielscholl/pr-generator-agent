"""
Tests for the main AIMR functionality
"""
import os
import pytest
from unittest.mock import patch, MagicMock, call
import git
from git import Repo
from aimr.main import main

@pytest.fixture
def mock_repo():
    """Create a mock git repository for testing"""
    mock = MagicMock(spec=Repo)
    mock.active_branch.name = "feature-branch"
    mock.is_dirty.return_value = False
    mock.heads = [
        MagicMock(name="main"),
        MagicMock(name="feature-branch")
    ]
    # Make branch names accessible via name attribute
    for head in mock.heads:
        head.name = head._mock_name
    mock.git.diff.return_value = "test diff content"
    return mock

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv('AZURE_API_KEY', 'test-key')
    monkeypatch.setenv('AZURE_API_BASE', 'test-base')
    monkeypatch.setenv('AZURE_API_VERSION', '2024-02-15-preview')

def test_version():
    """Test that version is properly set"""
    from aimr import __version__
    assert isinstance(__version__, str)
    assert len(__version__.split('.')) == 3

@patch('aimr.main.generate_with_azure_openai')
@patch('aimr.main.git.Repo')
def test_main_clean_branch(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with a clean branch"""
    mock_repo_class.return_value = mock_repo
    mock_generate.return_value = "Test MR description"
    
    # Run main with silent mode
    try:
        main(['--silent'])
    except SystemExit:
        pass  # Ignore exit
    
    # Verify git operations
    assert mock_repo.git.diff.called
    # Verify AI model was called
    mock_generate.assert_called_once()
    # Verify output
    captured = capsys.readouterr()
    assert "Test MR description" in captured.out

@patch('aimr.main.generate_with_azure_openai')
@patch('aimr.main.git.Repo')
def test_main_with_changes(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with working tree changes (auto-detection)"""
    # Set up mock repository with working tree changes
    mock_repo.index.diff.return_value = ["some_change"]  # Simulate staged changes
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = "test diff content"
    mock_repo_class.return_value = mock_repo
    mock_generate.return_value = "Test MR description"

    # Run main without specifying target (should auto-detect changes)
    try:
        main(['--silent'])
    except SystemExit:
        pass

    # Verify the auto-detection flow
    assert mock_repo.index.diff.call_count == 2  # Called for both staged and unstaged
    mock_repo.git.diff.assert_has_calls([
        call('HEAD', '--cached'),
        call()
    ])
    mock_generate.assert_called_once()
    
    # Verify output
    captured = capsys.readouterr()
    assert "Test MR description" in captured.out

@patch('aimr.main.generate_with_azure_openai')
@patch('aimr.main.git.Repo')
def test_main_explicit_working_tree(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with explicit working tree changes flag"""
    # Set up mock repository
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = "test diff content"
    mock_repo_class.return_value = mock_repo
    mock_generate.return_value = "Test MR description"

    # Run main with explicit working tree flag
    try:
        main(['--silent', '-t', '-'])
    except SystemExit:
        pass

    # Verify explicit working tree path includes both staged and unstaged changes
    mock_repo.git.diff.assert_has_calls([
        call('HEAD', '--cached'),
        call()
    ])
    mock_generate.assert_called_once()
    
    # Verify output
    captured = capsys.readouterr()
    assert "Test MR description" in captured.out

@patch('aimr.main.generate_with_azure_openai')
@patch('aimr.main.git.Repo')
def test_main_explicit_target(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with explicit target branch"""
    mock_repo_class.return_value = mock_repo
    mock_generate.return_value = "Test MR description"
    
    try:
        main(['--silent', '-t', 'main'])
    except SystemExit:
        pass
    
    # Verify correct branch comparison
    assert mock_repo.git.diff.called
    mock_repo.git.diff.assert_called_with('main...feature-branch')
    mock_generate.assert_called_once()
    captured = capsys.readouterr()
    assert "Test MR description" in captured.out

@patch('aimr.main.git.Repo')
def test_main_invalid_repo(mock_repo_class, capsys):
    """Test main function with invalid repository"""
    mock_repo_class.side_effect = git.exc.InvalidGitRepositoryError
    
    try:
        main([])
    except SystemExit as e:
        assert e.code == 1
    
    # Verify error message
    captured = capsys.readouterr()
    assert "not a valid Git repository" in captured.err

@patch('aimr.main.generate_with_azure_openai')
@patch('aimr.main.git.Repo')
def test_main_no_changes(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with no changes"""
    mock_repo.git.diff.return_value = ""
    mock_repo_class.return_value = mock_repo
    
    try:
        main(['--silent'])
    except SystemExit:
        pass
    
    # Verify no AI generation was attempted
    mock_generate.assert_not_called()
    captured = capsys.readouterr()
    assert "No changes found" in captured.err

def test_help(capsys):
    """Test help output"""
    try:
        main(['--help'])
    except SystemExit:
        pass
    
    # Verify help content
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "Generate MR description" in captured.out

@patch('aimr.main.run_trivy_scan')
@patch('aimr.main.generate_with_azure_openai')
@patch('aimr.main.git.Repo')
def test_main_with_vulns(mock_repo_class, mock_generate, mock_trivy, mock_repo, capsys):
    """Test main function with vulnerability scanning"""
    # Set up mock repository
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = "test diff content"
    mock_repo_class.return_value = mock_repo
    
    # Mock vulnerability scan results
    mock_trivy.return_value = {
        "Results": [
            {
                "Target": "requirements.txt",
                "Type": "pip",
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-2024-0001",
                        "PkgName": "requests",
                        "InstalledVersion": "2.25.0",
                        "FixedVersion": "2.31.0",
                        "Severity": "HIGH",
                        "Description": "Test vulnerability",
                        "Title": "Test Title",
                        "References": ["https://example.com/cve"]
                    }
                ]
            }
        ]
    }
    
    # Mock AI response
    mock_generate.return_value = "Test MR description"
    
    # Run main with vulnerability scanning
    try:
        main(['--silent', '--vulns'])
    except SystemExit:
        pass
    
    # Verify vulnerability scanning was performed
    mock_trivy.assert_called_once()
    
    # Verify AI model was called with vulnerability data
    assert mock_generate.call_count == 2  # Called once for initial MR, once with vuln data
    
    # Verify output includes both MR description and vulnerability report
    captured = capsys.readouterr()
    output = captured.out
    assert "Test MR description" in output
    assert "## Vulnerability Scan" in output
    assert "HIGH Severity" in output
    assert "CVE-2024-0001" in output 