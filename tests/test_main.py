"""
Tests for the main AIMR functionality
"""

from unittest.mock import MagicMock, call, patch

import pytest
from git import Repo
from git.exc import InvalidGitRepositoryError

from aimr.main import (
    ENDC,
    YELLOW,
    compare_vulnerabilities,
    detect_provider_and_model,
    generate_user_prompt,
    main,
    run_trivy_scan,
)


def test_version():
    """Test that version is properly set"""
    from aimr import __version__

    assert isinstance(__version__, str)
    assert len(__version__.split(".")) == 3


# Model Detection Tests
def test_detect_provider_and_model_defaults():
    """Test default model detection"""
    provider, model = detect_provider_and_model(None)
    assert provider == "anthropic"
    assert model == "claude-3-sonnet-20240229"


def test_detect_provider_and_model_azure():
    """Test Azure model detection"""
    test_cases = [
        ("azure/o1-mini", ("azure", "o1-mini")),
        ("azure/gpt-4o", ("azure", "gpt-4o")),
        ("azure/gpt-4", ("azure", "gpt-4o")),  # Alias test
    ]
    for input_model, expected in test_cases:
        provider, model = detect_provider_and_model(input_model)
        assert (provider, model) == expected


def test_detect_provider_and_model_openai():
    """Test OpenAI model detection"""
    test_cases = [
        ("gpt-4", ("openai", "gpt-4")),
        ("gpt4", ("openai", "gpt-4")),
        ("gpt-4-turbo", ("openai", "gpt-4-turbo-preview")),
        ("gpt-3.5-turbo", ("openai", "gpt-3.5-turbo")),
    ]
    for input_model, expected in test_cases:
        provider, model = detect_provider_and_model(input_model)
        assert (provider, model) == expected


def test_detect_provider_and_model_anthropic():
    """Test Anthropic model detection"""
    test_cases = [
        ("claude-3", ("anthropic", "claude-3-opus-20240229")),
        ("claude-3-opus", ("anthropic", "claude-3-opus-20240229")),
        ("claude-3.5-sonnet", ("anthropic", "claude-3-5-sonnet-20241022")),
    ]
    for input_model, expected in test_cases:
        provider, model = detect_provider_and_model(input_model)
        assert (provider, model) == expected


# Trivy Scanning Tests
@patch("subprocess.run")
def test_run_trivy_scan_python_poetry(mock_run, tmp_path):
    """Test Trivy scanning with Poetry project"""
    # Create mock Python project with Poetry
    poetry_lock = tmp_path / "poetry.lock"
    pyproject_toml = tmp_path / "pyproject.toml"
    poetry_lock.touch()
    pyproject_toml.touch()

    mock_run.return_value.stdout = '{"Results": []}'
    mock_run.return_value.returncode = 0

    result = run_trivy_scan(str(tmp_path), silent=True)

    assert mock_run.called
    args = mock_run.call_args[0][0]
    assert "--dependency-tree" in args
    assert str(tmp_path) in args


@patch("subprocess.run")
def test_run_trivy_scan_python_pip(mock_run, tmp_path):
    """Test Trivy scanning with pip requirements"""
    requirements = tmp_path / "requirements.txt"
    requirements.touch()

    mock_run.return_value.stdout = '{"Results": []}'
    mock_run.return_value.returncode = 0

    result = run_trivy_scan(str(tmp_path), silent=True)

    assert mock_run.called
    args = mock_run.call_args[0][0]
    assert "--dependency-tree" in args
    assert str(tmp_path) in args


# Vulnerability Comparison Tests
def test_compare_vulnerabilities_empty():
    """Test vulnerability comparison with empty scans"""
    report, analysis = compare_vulnerabilities({}, {})
    assert "Error: Unable to generate vulnerability comparison" in report
    assert analysis == ""


def test_compare_vulnerabilities_no_changes():
    """Test vulnerability comparison with no changes"""
    current_scan = {"Results": []}
    target_scan = {"Results": []}

    report, analysis = compare_vulnerabilities(current_scan, target_scan)
    assert "No vulnerability changes detected" in report
    assert "No security changes to analyze" in analysis


def test_compare_vulnerabilities_new_vulns():
    """Test vulnerability comparison with new vulnerabilities"""
    current_scan = {
        "Results": [
            {
                "Target": "requirements.txt",
                "Type": "pip",
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-2024-0001",
                        "PkgName": "requests",
                        "InstalledVersion": "2.25.0",
                        "Severity": "HIGH",
                        "Description": "Test vulnerability",
                        "Title": "Test Title",
                    }
                ],
            }
        ]
    }
    target_scan = {"Results": []}

    report, analysis = compare_vulnerabilities(current_scan, target_scan)
    assert "New Vulnerabilities" in report
    assert "HIGH" in report
    assert "CVE-2024-0001" in report
    assert "requests" in report


# Prompt Generation Tests
def test_generate_user_prompt_basic():
    """Test basic prompt generation without vulnerabilities"""
    diff = "test diff content"
    prompt = generate_user_prompt(diff)
    assert "Git Diff:" in prompt
    assert diff in prompt
    assert "Vulnerability Analysis:" not in prompt


def test_generate_user_prompt_with_vulns():
    """Test prompt generation with vulnerability data"""
    diff = "test diff content"
    vuln_data = "test vulnerability data"
    prompt = generate_user_prompt(diff, vuln_data)
    assert "Git Diff:" in prompt
    assert diff in prompt
    assert "Vulnerability Analysis:" in prompt
    assert vuln_data in prompt


# Main Function Integration Tests
@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
def test_main_clean_branch(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with a clean branch"""
    mock_repo_class.return_value = mock_repo
    mock_generate.return_value = "Test MR description"

    # Run main with silent mode
    try:
        main(["--silent"])
    except SystemExit:
        pass  # Ignore exit

    # Verify git operations
    assert mock_repo.git.diff.called
    # Verify AI model was called
    mock_generate.assert_called_once()
    # Verify output
    captured = capsys.readouterr()
    assert "Test MR description" in captured.out


@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
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
        main(["--silent"])
    except SystemExit:
        pass

    # Verify the auto-detection flow
    assert mock_repo.index.diff.call_count == 2  # Called for both staged and unstaged
    mock_repo.git.diff.assert_has_calls([call("HEAD", "--cached"), call()])
    mock_generate.assert_called_once()

    # Verify output
    captured = capsys.readouterr()
    assert "Test MR description" in captured.out


@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
def test_main_explicit_working_tree(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with explicit working tree changes flag"""
    # Set up mock repository
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = "test diff content"
    mock_repo_class.return_value = mock_repo
    mock_generate.return_value = "Test MR description"

    # Run main with explicit working tree flag
    try:
        main(["--silent", "-t", "-"])
    except SystemExit:
        pass

    # Verify explicit working tree path includes both staged and unstaged changes
    mock_repo.git.diff.assert_has_calls([call("HEAD", "--cached"), call()])
    mock_generate.assert_called_once()

    # Verify output
    captured = capsys.readouterr()
    assert "Test MR description" in captured.out


@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
def test_main_explicit_target(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with explicit target branch"""
    # Set up mock repository
    mock_repo_class.return_value = mock_repo
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.heads = [MagicMock(name="main"), MagicMock(name="feature-branch")]
    for head in mock_repo.heads:
        head.name = head._mock_name

    # Set up the mock git interface
    mock_repo.git.diff.return_value = "test diff content"

    # Mock that there are no working tree changes
    mock_repo.index.diff.return_value = []  # No staged changes
    mock_repo.untracked_files = []  # No untracked files

    # Mock AI response
    mock_generate.return_value = "Test MR description"

    try:
        main(["--silent", "-t", "main"])
    except SystemExit:
        pass

    # Verify correct branch comparison
    mock_repo.git.diff.assert_called_with("main...feature-branch")
    mock_generate.assert_called_once()
    captured = capsys.readouterr()
    assert "Test MR description" in captured.out


@patch("aimr.main.git.Repo")
def test_main_invalid_repo(mock_repo_class, capsys):
    """Test main function with invalid repository"""
    mock_repo_class.side_effect = InvalidGitRepositoryError

    try:
        main([])
    except SystemExit as e:
        assert e.code == 1

    # Verify error message
    captured = capsys.readouterr()
    assert "not a valid Git repository" in captured.err


@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
def test_main_no_changes(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with no changes"""
    mock_repo.git.diff.return_value = ""
    mock_repo_class.return_value = mock_repo

    try:
        main(["--silent"])
    except SystemExit:
        pass

    # Verify no AI generation was attempted
    mock_generate.assert_not_called()
    captured = capsys.readouterr()
    assert "No changes found" in captured.err


def test_help(capsys):
    """Test help output"""
    try:
        main(["--help"])
    except SystemExit:
        pass

    # Verify help content
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "Generate MR description" in captured.out


@patch("aimr.main.run_trivy_scan")
@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
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
                        "References": ["https://example.com/cve"],
                    }
                ],
            }
        ]
    }

    # Mock AI response
    mock_generate.return_value = "Test MR description"

    # Run main with vulnerability scanning
    try:
        main(["--silent", "--vulns"])
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
    assert "requests" in output


@patch("subprocess.run")
@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
def test_main_with_vulnerability_workflow(
    mock_repo_class, mock_generate, mock_trivy_run, mock_repo, capsys
):
    """Test main function with vulnerability scanning workflow"""
    # Set up mock repository
    mock_repo_class.return_value = mock_repo
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = "test diff content"

    # Mock Trivy scan results
    mock_trivy_run.return_value.stdout = """
    {
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
                        "Title": "Test Title"
                    }
                ]
            }
        ]
    }"""
    mock_trivy_run.return_value.returncode = 0

    # Mock AI responses with correct format
    mock_generate.side_effect = [
        """### Merge Request

Initial description of changes""",
        """### Merge Request

Updated description with security context

## Vulnerability Scan

### HIGH Severity
- CVE-2024-0001 in requests 2.25.0 (requirements.txt)""",
    ]

    # Run main with vulnerability scanning
    try:
        main(["--silent", "--vulns"])
    except SystemExit:
        pass

    # Verify Trivy scan was performed
    assert mock_trivy_run.called
    trivy_args = mock_trivy_run.call_args[0][0]
    assert "--dependency-tree" in trivy_args

    # Verify AI was called twice (initial + vuln update)
    assert mock_generate.call_count == 2

    # Verify output format
    captured = capsys.readouterr()
    output = captured.out
    assert "### Merge Request" in output
    assert "## Vulnerability Scan" in output
    assert "### HIGH Severity" in output
    assert "CVE-2024-0001" in output
    assert "requests" in output


@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
def test_main_target_branch_fallback(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with target branch fallback logic"""
    mock_repo_class.return_value = mock_repo
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = "test diff content"
    mock_generate.return_value = "Test MR description"

    # Set up mock branches
    mock_repo.heads = [MagicMock(name="main"), MagicMock(name="feature-branch")]
    for head in mock_repo.heads:
        head.name = head._mock_name

    # Run main with non-existent target branch (without silent mode)
    try:
        main(["-t", "nonexistent"])
    except SystemExit:
        pass

    # Verify fallback to 'main'
    mock_repo.git.diff.assert_called_with("main...feature-branch")

    # Verify warning message (matching the actual warning format in the code)
    captured = capsys.readouterr()
    assert (
        f"{YELLOW}Warning: Target branch 'nonexistent' not found, using 'main' instead.{ENDC}"
        in captured.err
    )


@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
def test_main_mr_output_format(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function output format verification"""
    mock_repo_class.return_value = mock_repo
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = """
diff --git a/test.py b/test.py
index 1234567..89abcdef 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
+import os
 def test_function():
-    return False
+    return True
"""

    # Mock a detailed MR description
    mock_generate.return_value = """
### Merge Request

**Branch:** feature-branch

**Changes:**
- Added import os
- Modified test_function return value

**Impact:**
Low impact change to test functionality.

**Testing:**
- Unit tests updated
- All tests passing
"""

    try:
        main(["--silent"])
    except SystemExit:
        pass

    # Verify output format
    captured = capsys.readouterr()
    output = captured.out

    # Check for required sections
    assert "### Merge Request" in output
    assert "**Branch:**" in output
    assert "**Changes:**" in output
    assert "**Impact:**" in output
    assert "**Testing:**" in output

    # Check content details
    assert "feature-branch" in output
    assert "Added import os" in output
    assert "Modified test_function" in output


@patch("aimr.main.run_trivy_scan")
@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
def test_main_working_tree_with_vulns(
    mock_repo_class, mock_generate, mock_trivy, mock_repo, capsys
):
    """Test main function with working tree (-t "-") and vulnerability scanning"""
    # Set up mock repository
    mock_repo_class.return_value = mock_repo
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = "test diff content"

    # Mock vulnerability scan results for single branch scan
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
                        "Severity": "HIGH",
                    }
                ],
            }
        ]
    }

    mock_generate.return_value = "Test MR description with vulnerabilities"

    # Run main with both working tree and vulnerability scanning
    try:
        main(["--silent", "-t", "-", "--vulns"])
    except SystemExit:
        pass

    # Verify only one Trivy scan was performed (no temp repo clone)
    mock_trivy.assert_called_once()

    # Verify git operations were for working tree
    mock_repo.git.diff.assert_has_calls([call("HEAD", "--cached"), call()])

    # Verify output
    captured = capsys.readouterr()
    assert "Test MR description with vulnerabilities" in captured.out


@patch("aimr.main.run_trivy_scan")
@patch("aimr.main.generate_with_anthropic")
@patch("aimr.main.git.Repo")
def test_main_single_branch_vuln_scan(
    mock_repo_class, mock_generate, mock_trivy, mock_repo, capsys
):
    """Test main function with vulnerability scanning on a single branch (no target comparison)"""
    # Set up mock repository with no target branch
    mock_repo_class.return_value = mock_repo
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = "test diff content"
    mock_repo.heads = [MagicMock(name="feature-branch")]  # Only current branch exists
    for head in mock_repo.heads:
        head.name = head._mock_name

    # Simulate working tree changes to ensure we take the working tree path
    mock_repo.index.diff.return_value = ["some_change"]  # Simulate staged changes
    mock_repo.untracked_files = ["untracked_file"]  # Simulate untracked files

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
                        "Severity": "HIGH",
                    }
                ],
            }
        ]
    }

    mock_generate.return_value = "Test MR description with single branch vulnerabilities"

    # Run main with vulnerability scanning but no valid target branch
    try:
        main(["--silent", "--vulns"])
    except SystemExit:
        pass

    # Verify only one Trivy scan was performed (no comparison scan)
    mock_trivy.assert_called_once()

    # Verify git operations were for working tree changes (staged and unstaged)
    mock_repo.git.diff.assert_has_calls([call("HEAD", "--cached"), call()])
    assert mock_repo.git.diff.call_count == 2  # Called for both staged and unstaged changes

    # Verify output
    captured = capsys.readouterr()
    assert "Test MR description with single branch vulnerabilities" in captured.out
