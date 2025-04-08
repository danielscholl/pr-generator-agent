"""
Tests for the main AIPR functionality
"""

from unittest.mock import MagicMock, Mock, call, patch

import pytest
from git import Repo
from git.exc import InvalidGitRepositoryError

from aipr.main import (
    ENDC,
    YELLOW,
    compare_vulnerabilities,
    detect_provider_and_model,
    main,
    run_trivy_scan,
)
from aipr.prompts import PromptManager
from aipr.providers import generate_with_anthropic, generate_with_azure_openai, generate_with_openai


def test_version():
    """Test that version is properly set"""
    from aipr import __version__

    assert isinstance(__version__, str)
    assert len(__version__.split(".")) == 3


# Model Detection Tests
def test_detect_provider_and_model_defaults():
    """Test default model detection"""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        provider, model = detect_provider_and_model(None)
        assert provider == "anthropic"
        assert model == "claude-3-sonnet-20240229"

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=True):
        provider, model = detect_provider_and_model(None)
        assert provider == "gemini"
        assert model == "gemini-2.5-pro-experimental"


def test_detect_provider_and_model_aliases():
    """Test all documented model aliases"""
    test_cases = [
        # Simple provider aliases
        ("claude", ("anthropic", "claude-3-sonnet-20240229")),
        ("azure", ("azure", "gpt-4o-mini")),
        ("openai", ("openai", "gpt-4o")),
        ("gemini", ("gemini", "gemini-2.5-pro-experimental")),
        # Azure model aliases
        ("azure/gpt-4", ("azure", "gpt-4o")),
        ("azure/gpt-4o", ("azure", "gpt-4o")),
        ("azure/gpt-4o-mini", ("azure", "gpt-4o-mini")),
        ("azure/o1-mini", ("azure", "o1-mini")),
        # OpenAI model aliases
        ("gpt-4o", ("openai", "gpt-4")),
        ("gpt-4-turbo", ("openai", "gpt-4-turbo")),
        ("gpt-3.5-turbo", ("openai", "gpt-3.5-turbo")),
        # Anthropic model aliases
        ("claude-3", ("anthropic", "claude-3-opus-20240229")),
        ("claude-3-opus", ("anthropic", "claude-3-opus-20240229")),
        ("claude-3.5-sonnet", ("anthropic", "claude-3-5-sonnet-20241022")),
        ("claude-3-sonnet", ("anthropic", "claude-3-sonnet-20240229")),
        ("claude-3.5-haiku", ("anthropic", "claude-3-5-haiku-20241022")),
        ("claude-3-haiku", ("anthropic", "claude-3-haiku-20240307")),
        # Gemini model aliases
        ("gemini-1.5-pro", ("gemini", "gemini-1.5-pro")),
        ("gemini-1.5-flash", ("gemini", "gemini-1.5-flash")),
        ("gemini-2.5-pro-experimental", ("gemini", "gemini-2.5-pro-exp-03-25")),
    ]

    for input_model, expected in test_cases:
        provider, model = detect_provider_and_model(input_model)
        assert (provider, model) == expected, f"Failed for input model: {input_model}"


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
        ("gpt-4-turbo", ("openai", "gpt-4-turbo")),
        ("gpt-3.5-turbo", ("openai", "gpt-3.5-turbo")),
    ]
    for input_model, expected in test_cases:
        provider, model = detect_provider_and_model(input_model)
        assert (provider, model) == expected


def test_detect_provider_and_model_gemini():
    """Test Gemini model detection"""
    test_cases = [
        ("gemini-1.5-pro", ("gemini", "gemini-1.5-pro")),
        ("gemini-1.5-flash", ("gemini", "gemini-1.5-flash")),
        ("gemini-2.5-pro-experimental", ("gemini", "gemini-2.5-pro-exp-03-25")),
        ("gemini", ("gemini", "gemini-2.5-pro-experimental")),  # Alias test
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
def test_prompt_generation():
    """Test prompt generation with and without vulnerabilities"""
    manager = PromptManager()

    # Test without vulnerabilities
    diff = "test diff content"
    prompt = manager.get_user_prompt(diff)
    assert "Git Diff:" in prompt
    assert diff in prompt
    assert "Vulnerability Analysis:" not in prompt

    # Test with vulnerabilities
    vuln_data = "test vulnerability data"
    prompt = manager.get_user_prompt(diff, vuln_data)
    assert "Git Diff:" in prompt
    assert diff in prompt
    assert "Vulnerability Analysis:" in prompt
    assert vuln_data in prompt


# Main Function Integration Tests
@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.git.Repo")
def test_main_with_changes(mock_repo_class, mock_generate, capsys):
    """Test main function with changes"""
    # Setup mock repo
    mock_repo = MagicMock()
    mock_repo_class.return_value = mock_repo
    mock_repo.is_dirty.return_value = True
    mock_repo.git.diff.return_value = "test diff"

    # Setup mock generate
    mock_generate.return_value = "test response"

    # Run with environment variable set
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        try:
            main([])
        except SystemExit:
            pass

    # Verify the response
    mock_generate.assert_called_once()
    captured = capsys.readouterr()
    assert "test response" in captured.out


@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.git.Repo")
def test_main_clean_branch(mock_repo_class, mock_generate, capsys):
    """Test main function with clean branch"""
    # Setup mock repo
    mock_repo = MagicMock()
    mock_repo_class.return_value = mock_repo
    mock_repo.is_dirty.return_value = False
    mock_repo.git.diff.return_value = "test diff"
    mock_repo.active_branch.name = "feature"
    mock_repo.heads = [MagicMock(name="main")]
    for head in mock_repo.heads:
        head.name = head._mock_name

    # Setup mock generate
    mock_generate.return_value = "test response"

    # Run with environment variable set
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        try:
            main(["-t", "main"])
        except SystemExit:
            pass

    # Verify the response
    mock_generate.assert_called_once()
    captured = capsys.readouterr()
    assert "test response" in captured.out


@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.git.Repo")
def test_main_explicit_working_tree(mock_repo_class, mock_generate, capsys):
    """Test main function with explicit working tree flag"""
    # Setup mock repo
    mock_repo = MagicMock()
    mock_repo_class.return_value = mock_repo
    mock_repo.git.diff.return_value = "test diff"

    # Setup mock generate
    mock_generate.return_value = "test response"

    # Run with environment variable set
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        try:
            main(["--working-tree"])
        except SystemExit:
            pass

    # Verify the response
    mock_generate.assert_called_once()
    captured = capsys.readouterr()
    assert "test response" in captured.out


@patch("aipr.main.git.Repo")
def test_main_invalid_repo(mock_repo_class, capsys):
    """Test main function with invalid repository"""
    mock_repo_class.side_effect = InvalidGitRepositoryError()

    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Directory is not a valid Git repository" in captured.err


@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.git.Repo")
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
    assert "Generate PR description" in captured.out


@patch("aipr.main.run_trivy_scan")
@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.git.Repo")
def test_main_with_vulnerability_workflow(
    mock_repo_class, mock_generate, mock_trivy_run, mock_repo, capsys
):
    """Test main function with vulnerability scanning workflow"""
    # Set up mock repository
    mock_repo_class.return_value = mock_repo
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = "test diff content"

    # Mock Trivy scan results
    mock_trivy_run.return_value = {
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
                    }
                ],
            }
        ]
    }

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
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        try:
            main(["--silent", "--vulns"])
        except SystemExit:
            pass

    # Verify Trivy scan was performed
    assert mock_trivy_run.called
    assert mock_generate.called

    # Verify output format
    captured = capsys.readouterr()
    output = captured.out
    assert "### Merge Request" in output
    assert "Initial description of changes" in output


@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.git.Repo")
def test_main_target_branch_fallback(mock_repo_class, mock_generate, mock_repo, capsys):
    """Test main function with target branch fallback logic"""
    mock_repo_class.return_value = mock_repo
    mock_repo.active_branch.name = "feature-branch"
    mock_repo.git.diff.return_value = "test diff content"
    mock_repo.is_dirty.return_value = False
    mock_generate.return_value = "Test PR description"

    # Set up mock branches with main as default
    mock_repo.heads = [MagicMock(name="main"), MagicMock(name="feature-branch")]
    for head in mock_repo.heads:
        head.name = head._mock_name

    # Run main without specifying target branch
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        try:
            main([])  # No target specified, should fall back to main
        except SystemExit:
            pass

    # Verify fallback to 'main'
    mock_repo.git.diff.assert_any_call("main...feature-branch")

    # Verify output
    captured = capsys.readouterr()
    assert "Test PR description" in captured.out


@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.git.Repo")
def test_main_pr_output_format(mock_repo_class, mock_generate, mock_repo, capsys):
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

    # Mock a detailed PR description
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


@patch("aipr.main.run_trivy_scan")
@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.git.Repo")
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

    mock_generate.return_value = "Test PR description with vulnerabilities"

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
    assert "Test PR description with vulnerabilities" in captured.out


@patch("aipr.main.run_trivy_scan")
@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.git.Repo")
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

    mock_generate.return_value = "Test PR description with single branch vulnerabilities"

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
    assert "Test PR description with single branch vulnerabilities" in captured.out


@pytest.fixture
def mock_repo():
    with patch("git.Repo") as mock:
        repo = MagicMock()
        repo.is_dirty.return_value = True
        repo.git.diff.return_value = "test diff"
        repo.working_dir = "/test/dir"
        mock.return_value = repo
        yield mock


@pytest.fixture
def mock_anthropic():
    with patch("aipr.main.generate_with_anthropic") as mock:
        mock.return_value = "Test description"
        yield mock


@pytest.fixture
def mock_azure():
    with patch("aipr.main.generate_with_azure_openai") as mock:
        mock.return_value = "Test description"
        yield mock


@pytest.fixture
def mock_openai():
    with patch("aipr.main.generate_with_openai") as mock:
        mock.return_value = "Test description"
        yield mock


@pytest.fixture
def mock_trivy():
    with patch("aipr.main.run_trivy_scan") as mock:
        mock.return_value = {"vulnerabilities": []}
        yield mock


def test_main_anthropic(mock_repo, mock_anthropic):
    args = Mock(
        model="claude-3-opus-20240229",
        target="-",
        vulns=False,
        silent=True,
        verbose=False,
        prompt=None,
    )

    with patch("aipr.main.parse_args", return_value=args):
        try:
            result = main(args)
            assert result == "Test description"
            mock_anthropic.assert_called_once()
        except SystemExit:
            pass


@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.generate_with_azure_openai")
@patch("aipr.main.generate_with_openai")
def test_main_openai(mock_openai_gen, mock_azure_gen, mock_anthropic_gen, mock_repo):
    """Test main function with OpenAI"""
    args = Mock(model="gpt-4", target="-", vulns=False, silent=True, verbose=False, prompt=None)
    mock_openai_gen.return_value = "Test description"

    with patch("aipr.main.parse_args", return_value=args):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            try:
                result = main(args)
                assert result == "Test description"
                mock_openai_gen.assert_called_once()
                mock_azure_gen.assert_not_called()
                mock_anthropic_gen.assert_not_called()
            except SystemExit:
                pass


@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.generate_with_azure_openai")
@patch("aipr.main.generate_with_openai")
def test_main_azure(mock_openai_gen, mock_azure_gen, mock_anthropic_gen, mock_repo):
    """Test main function with Azure OpenAI"""
    args = Mock(
        model="azure/gpt-4", target="-", vulns=False, silent=True, verbose=False, prompt=None
    )
    mock_azure_gen.return_value = "Test description"

    with patch("aipr.main.parse_args", return_value=args):
        with patch.dict(
            "os.environ",
            {
                "AZURE_API_KEY": "test-key",
                "AZURE_API_BASE": "test-base",
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            },
        ):
            try:
                result = main(args)
                assert result == "Test description"
                mock_azure_gen.assert_called_once()
                mock_openai_gen.assert_not_called()
                mock_anthropic_gen.assert_not_called()
            except SystemExit:
                pass


@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.generate_with_azure_openai")
@patch("aipr.main.generate_with_openai")
def test_main_with_vulns(
    mock_openai_gen, mock_azure_gen, mock_anthropic_gen, mock_repo, mock_trivy
):
    """Test main function with vulnerability scanning"""
    args = Mock(
        model="gpt-4", target="-", vulns=True, silent=True, verbose=False, prompt=None, debug=False
    )
    mock_openai_gen.return_value = "Test description"

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

    with patch("aipr.main.parse_args", return_value=args):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            try:
                main(args)
            except SystemExit:
                pass

            # Verify the API calls and data
            mock_trivy.assert_called_once()
            mock_openai_gen.assert_called_once()
            mock_azure_gen.assert_not_called()
            mock_anthropic_gen.assert_not_called()

            # Verify vulnerability data was passed to the model
            vuln_data = mock_openai_gen.call_args[0][1]  # Get the vuln_data argument
            assert isinstance(vuln_data, dict)
            assert "Results" in vuln_data
            assert "CVE-2024-0001" in str(vuln_data)


def test_detect_provider_and_model():
    """Test provider and model detection"""
    # Test Anthropic models
    provider, model = detect_provider_and_model("claude-3-opus-20240229")
    assert provider == "anthropic"
    assert model == "claude-3-opus-20240229"

    # Test Azure OpenAI models with explicit azure/ prefix
    with patch.dict(
        "os.environ",
        {
            "AZURE_API_KEY": "test-key",
            "AZURE_API_BASE": "test-base",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        },
    ):
        provider, model = detect_provider_and_model("azure/gpt-4")
        assert provider == "azure"
        assert model == "gpt-4o"

    # Test OpenAI models
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        provider, model = detect_provider_and_model("gpt-4")
        assert provider == "openai"
        assert model == "gpt-4"


def test_prompt_manager():
    manager = PromptManager()

    # Test system prompt
    system_prompt = manager.get_system_prompt()
    assert isinstance(system_prompt, str)
    assert len(system_prompt) > 0

    # Test user prompt without vulnerabilities
    user_prompt = manager.get_user_prompt("test diff")
    assert isinstance(user_prompt, str)
    assert "test diff" in user_prompt

    # Test user prompt with vulnerabilities
    vuln_data = {
        "Results": [{"severity": "HIGH", "description": "Test vulnerability"}]
    }  # Updated structure
    user_prompt_with_vulns = manager.get_user_prompt("test diff", vuln_data)
    assert isinstance(user_prompt_with_vulns, str)
    assert "test diff" in user_prompt_with_vulns
    assert "Test vulnerability" in user_prompt_with_vulns


@patch("aipr.providers.OpenAI")
@patch("aipr.providers.AzureOpenAI")
@patch("aipr.providers.anthropic.Anthropic")
def test_provider_clients(mock_anthropic, mock_azure, mock_openai):
    """Test that provider clients are created correctly"""
    # Setup mock responses
    mock_anthropic_instance = mock_anthropic.return_value
    mock_anthropic_instance.messages.create.return_value = type(
        "Response", (), {"content": [type("Content", (), {"text": "Test response"})()]}
    )

    mock_azure.return_value.chat.completions.create.return_value.choices = [
        type("Choice", (), {"message": type("Message", (), {"content": "Test response"})()})()
    ]
    mock_openai.return_value.chat.completions.create.return_value.choices = [
        type("Choice", (), {"message": type("Message", (), {"content": "Test response"})()})()
    ]

    # Test Anthropic
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        result = generate_with_anthropic("test", None, "claude-3", "test prompt")
        assert result == "Test response"
        mock_anthropic.assert_called_once()
        mock_anthropic_instance.messages.create.assert_called_once()

    # Test Azure
    with patch.dict(
        "os.environ",
        {
            "AZURE_API_KEY": "test-key",
            "AZURE_API_BASE": "test-base",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        },
    ):
        result = generate_with_azure_openai("test", None, "gpt-4", "test prompt")
        assert result == "Test response"
        mock_azure.assert_called_once()

    # Test OpenAI
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        result = generate_with_openai("test", None, "gpt-4", "test prompt")
        assert result == "Test response"
        mock_openai.assert_called_once()


@patch("aipr.main.generate_with_anthropic")
@patch("aipr.main.generate_with_azure_openai")
@patch("aipr.main.generate_with_openai")
def test_main_azure_o1_mini(mock_openai_gen, mock_azure_gen, mock_anthropic_gen, mock_repo):
    """Test main function with Azure OpenAI o1-mini model that doesn't support system messages"""
    args = Mock(
        model="azure/o1-mini",
        target="-",
        vulns=False,
        silent=True,
        verbose=False,
        prompt=None,
        debug=False,
    )
    mock_azure_gen.return_value = "Test description"

    # Mock repo with some diff content
    mock_repo = MagicMock()
    mock_repo.git.diff.return_value = "test diff"

    with patch("aipr.main.parse_args", return_value=args):
        with patch.dict(
            "os.environ",
            {
                "AZURE_API_KEY": "test-key",
                "AZURE_API_BASE": "test-base",
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            },
        ):
            try:
                main(args)
            except SystemExit:
                pass

            # Verify the correct provider was called
            mock_azure_gen.assert_called_once()
            mock_openai_gen.assert_not_called()
            mock_anthropic_gen.assert_not_called()

            # Verify the model name was passed correctly
            assert mock_azure_gen.call_args[0][2] == "o1-mini"  # Check model parameter
