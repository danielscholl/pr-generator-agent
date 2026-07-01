"""
Tests for the commit message generation functionality
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from git import Repo
from git.exc import InvalidGitRepositoryError

from aipr.commit import MAX_SUBJECT_LENGTH, CommitAnalyzer, normalize_commit_message
from aipr.main import handle_commit_command


class TestCommitAnalyzer:
    """Test the CommitAnalyzer class."""

    def test_init_with_valid_repo(self, tmp_path):
        """Test initializing CommitAnalyzer with a valid git repository."""
        # Create a temporary git repository
        repo = Repo.init(tmp_path)

        analyzer = CommitAnalyzer(str(tmp_path))
        assert analyzer.repo is not None

    def test_init_with_invalid_repo(self, tmp_path):
        """Test initializing CommitAnalyzer with an invalid repository."""
        with pytest.raises(ValueError, match="Invalid git repository"):
            CommitAnalyzer(str(tmp_path))

    @patch("git.Repo")
    def test_get_staged_changes_no_changes(self, mock_repo_class):
        """Test getting staged changes when no changes are staged."""
        mock_repo = MagicMock()
        mock_repo.git.diff.return_value = ""
        mock_repo_class.return_value = mock_repo

        analyzer = CommitAnalyzer()

        with pytest.raises(ValueError, match="No staged changes found"):
            analyzer.get_staged_changes()

    @patch("git.Repo")
    def test_get_staged_changes_with_changes(self, mock_repo_class):
        """Test getting staged changes when changes are staged."""
        mock_repo = MagicMock()
        mock_repo.git.diff.side_effect = [
            "diff --git a/test.py b/test.py\n+def test():\n+    pass",  # staged diff
            "A\ttest.py",  # name-status
        ]
        mock_repo_class.return_value = mock_repo

        analyzer = CommitAnalyzer()

        diff, stats = analyzer.get_staged_changes()

        assert "def test():" in diff
        assert stats["total"] == 1
        assert stats["added"] == 1
        assert stats["files"][0]["status"] == "A"
        assert stats["files"][0]["path"] == "test.py"

    def test_categorize_file_docs(self):
        """Test file categorization for documentation files."""
        analyzer = CommitAnalyzer()

        assert analyzer._categorize_file("README.md", "M") == "docs"
        assert analyzer._categorize_file("docs/guide.rst", "A") == "docs"
        assert analyzer._categorize_file("CHANGELOG.txt", "M") == "docs"

    def test_categorize_file_tests(self):
        """Test file categorization for test files."""
        analyzer = CommitAnalyzer()

        assert analyzer._categorize_file("tests/test_module.py", "A") == "test"
        assert analyzer._categorize_file("module_test.py", "M") == "test"
        assert analyzer._categorize_file("conftest.py", "A") == "test"

    def test_categorize_file_ci(self):
        """Test file categorization for CI files."""
        analyzer = CommitAnalyzer()

        assert analyzer._categorize_file(".github/workflows/test.yml", "M") == "ci"
        assert analyzer._categorize_file("azure-pipelines.yml", "A") == "ci"
        assert analyzer._categorize_file(".gitlab-ci.yml", "M") == "ci"

    def test_categorize_file_build(self):
        """Test file categorization for build files."""
        analyzer = CommitAnalyzer()

        assert analyzer._categorize_file("setup.py", "M") == "build"
        assert analyzer._categorize_file("pyproject.toml", "A") == "build"
        assert analyzer._categorize_file("package.json", "M") == "build"
        assert analyzer._categorize_file("requirements.txt", "M") == "build"

    def test_categorize_changes_single_type(self):
        """Test change categorization with single file type."""
        analyzer = CommitAnalyzer()

        file_stats = {"files": [{"path": "README.md", "status": "M"}], "total": 1}
        diff_content = "diff --git a/README.md b/README.md\n+New documentation"

        result = analyzer.categorize_changes(file_stats, diff_content)
        assert result == "docs"

    def test_categorize_changes_mixed_types_feat_priority(self):
        """Test change categorization with mixed types, feat should take priority."""
        analyzer = CommitAnalyzer()

        file_stats = {
            "files": [
                {"path": "src/new_feature.py", "status": "A"},
                {"path": "README.md", "status": "M"},
            ],
            "total": 2,
        }
        diff_content = "diff --git a/src/new_feature.py\n+def new_function():\n+    return True"

        result = analyzer.categorize_changes(file_stats, diff_content)
        assert result == "feat"

    def test_analyze_diff_content_feature_patterns(self):
        """Test diff content analysis for feature patterns."""
        analyzer = CommitAnalyzer()

        diff_content = """
diff --git a/module.py b/module.py
+def new_feature():
+    return True
+
+class NewClass:
+    pass
"""

        result = analyzer._analyze_diff_content(diff_content)
        assert result == "feat"

    def test_analyze_diff_content_fix_patterns(self):
        """Test diff content analysis for fix patterns."""
        analyzer = CommitAnalyzer()

        diff_content = """
diff --git a/module.py b/module.py
+if error:
+    fix_issue()
+
-    buggy_code()
"""

        result = analyzer._analyze_diff_content(diff_content)
        assert result == "fix"

    def test_determine_scope_single_directory(self):
        """Test scope determination with single directory."""
        analyzer = CommitAnalyzer()

        file_stats = {
            "files": [
                {"path": "aipr/module.py", "status": "M"},
                {"path": "aipr/another.py", "status": "A"},
            ]
        }

        scope = analyzer.determine_scope(file_stats)
        assert scope == "core"  # aipr -> core mapping

    def test_determine_scope_multiple_directories(self):
        """Test scope determination with multiple directories."""
        analyzer = CommitAnalyzer()

        file_stats = {
            "files": [
                {"path": "tests/test_module.py", "status": "M"},
                {"path": "tests/test_another.py", "status": "A"},
            ]
        }

        scope = analyzer.determine_scope(file_stats)
        assert scope == "test"

    def test_determine_scope_mixed_directories(self):
        """Test scope determination with mixed directories."""
        analyzer = CommitAnalyzer()

        file_stats = {
            "files": [
                {"path": "src/module.py", "status": "M"},
                {"path": "docs/guide.md", "status": "A"},
                {"path": "tests/test.py", "status": "M"},
            ]
        }

        scope = analyzer.determine_scope(file_stats)
        # Should return None for mixed scopes
        assert scope is None

    def test_generate_description_feat(self):
        """Test description generation for features."""
        analyzer = CommitAnalyzer()

        file_stats = {"files": [{"path": "src/auth.py", "status": "A"}]}

        description = analyzer.generate_description("feat", "auth", file_stats, "")
        assert "add authentication functionality" in description

    def test_generate_description_fix(self):
        """Test description generation for fixes."""
        analyzer = CommitAnalyzer()

        file_stats = {"files": [{"path": "src/user.py", "status": "M"}]}

        description = analyzer.generate_description("fix", "api", file_stats, "")
        assert "resolve issue in user" in description

    def test_generate_description_multiple_files(self):
        """Test description generation for multiple files."""
        analyzer = CommitAnalyzer()

        file_stats = {
            "files": [
                {"path": "src/module1.py", "status": "M"},
                {"path": "src/module2.py", "status": "A"},
                {"path": "src/module3.py", "status": "M"},
            ]
        }

        description = analyzer.generate_description("feat", None, file_stats, "")
        assert "3 files" in description

    @patch("git.Repo")
    def test_generate_conventional_commit(self, mock_repo_class):
        """Test generating a complete conventional commit message."""
        mock_repo = MagicMock()
        mock_repo.git.diff.side_effect = [
            "diff --git a/src/auth.py b/src/auth.py\n+def login():\n+    pass",  # staged diff
            "A\tsrc/auth.py",  # name-status
        ]
        mock_repo_class.return_value = mock_repo

        analyzer = CommitAnalyzer()

        commit_message = analyzer.generate_conventional_commit()

        # Should be in format: type(scope): description
        assert ":" in commit_message
        parts = commit_message.split(":", 1)
        assert len(parts) == 2

        type_and_scope = parts[0].strip()
        description = parts[1].strip()

        # Should contain a valid type
        assert any(
            commit_type in type_and_scope for commit_type in analyzer.CONVENTIONAL_TYPES.keys()
        )
        assert len(description) > 0

    @patch("git.Repo")
    def test_generate_conventional_commit_with_context(self, mock_repo_class):
        """Test generating conventional commit message with context."""
        mock_repo = MagicMock()
        mock_repo.git.diff.side_effect = [
            "diff --git a/README.md b/README.md\n+New docs",
            "M\tREADME.md",
        ]
        mock_repo_class.return_value = mock_repo

        analyzer = CommitAnalyzer()

        commit_message = analyzer.generate_conventional_commit("upstream sync")

        assert "upstream sync" in commit_message


class TestCommitMainIntegration:
    """Test integration with main command handling."""

    @patch("aipr.main.CommitAnalyzer")
    @patch("aipr.main.generate_commit_message")
    @patch("aipr.main.detect_provider_and_model")
    def test_handle_commit_command_success(self, mock_detect, mock_generate, mock_analyzer_class):
        """Test successful commit command handling."""
        # Setup mocks
        mock_analyzer = MagicMock()
        mock_analyzer.get_staged_changes.return_value = ("diff content", {"total": 1})
        mock_analyzer_class.return_value = mock_analyzer

        mock_detect.return_value = ("anthropic", "claude-sonnet-4-6")
        mock_generate.return_value = "feat: add new functionality"

        # Create args mock
        args = MagicMock()
        args.debug = False
        args.silent = True
        args.verbose = False
        args.model = None
        args.context = ""
        args.from_commit = None
        args.to_commit = None

        # Test the function
        with patch("sys.exit") as mock_exit:
            with patch("builtins.print") as mock_print:
                handle_commit_command(args)

                # Verify the commit message was generated and printed
                mock_print.assert_called_with("feat: add new functionality")
                mock_exit.assert_not_called()

    @patch("aipr.main.CommitAnalyzer")
    def test_handle_commit_command_no_staged_changes(self, mock_analyzer_class):
        """Test commit command with no staged changes."""
        # Setup mock to raise ValueError
        mock_analyzer = MagicMock()
        mock_analyzer.get_staged_changes.side_effect = ValueError("No staged changes found")
        mock_analyzer_class.return_value = mock_analyzer

        args = MagicMock()
        args.debug = False
        args.silent = True
        args.from_commit = None
        args.to_commit = None

        # Test the function
        with patch("sys.exit") as mock_exit:
            handle_commit_command(args)
            mock_exit.assert_called_with(1)

    @patch("aipr.main.CommitAnalyzer")
    @patch("aipr.main.generate_commit_message")
    @patch("aipr.main.detect_provider_and_model")
    def test_handle_commit_command_with_fallback(
        self, mock_detect, mock_generate, mock_analyzer_class
    ):
        """Test commit command with AI failure and fallback."""
        # Setup mocks
        mock_analyzer = MagicMock()
        mock_analyzer.get_staged_changes.return_value = ("diff content", {"total": 1})
        mock_analyzer.generate_conventional_commit.return_value = "feat: fallback message"
        mock_analyzer_class.return_value = mock_analyzer

        mock_detect.return_value = ("anthropic", "claude-sonnet-4-6")
        mock_generate.side_effect = Exception("API Error")

        args = MagicMock()
        args.debug = False
        args.silent = True
        args.verbose = False
        args.model = None
        args.context = ""
        args.from_commit = None
        args.to_commit = None

        # Test the function
        with patch("sys.exit") as mock_exit:
            with patch("builtins.print") as mock_print:
                handle_commit_command(args)

                # Verify fallback was used
                mock_print.assert_called_with("feat: fallback message")
                mock_exit.assert_not_called()

    @patch("aipr.main.CommitAnalyzer")
    def test_handle_commit_command_debug_mode(self, mock_analyzer_class):
        """Test commit command in debug mode."""
        # Setup mocks
        mock_analyzer = MagicMock()
        mock_analyzer.get_staged_changes.return_value = ("diff content", {"total": 1})
        mock_analyzer.get_analysis_summary.return_value = {
            "detected_type": "feat",
            "detected_scope": "core",
            "staged_files": {"total": 1},
        }
        mock_analyzer_class.return_value = mock_analyzer

        args = MagicMock()
        args.debug = True
        args.model = None
        args.silent = True
        args.verbose = False
        args.context = ""
        args.from_commit = None
        args.to_commit = None

        # Test the function
        with patch("sys.exit") as mock_exit:
            with patch("builtins.print") as mock_print:
                handle_commit_command(args)

                # Verify debug output was printed
                mock_exit.assert_called_with(0)
                # Check that some debug info was printed
                assert mock_print.call_count > 0


class TestCommitPromptGeneration:
    """Test commit prompt generation."""

    def test_commit_prompt_generation(self):
        """Test that commit prompts can be generated."""
        from aipr.prompts import PromptManager

        manager = PromptManager()

        staged_changes = "diff --git a/test.py b/test.py\n+def test(): pass"
        file_summary = {
            "total": 1,
            "added": 1,
            "modified": 0,
            "deleted": 0,
            "files": [{"status": "A", "path": "test.py"}],
        }

        prompt = manager.get_commit_prompt(staged_changes, file_summary, "test context")

        assert "staged-changes" in prompt
        assert "def test(): pass" in prompt
        assert "Files changed: 1" in prompt
        assert "test context" in prompt

    def test_commit_system_prompt(self):
        """Test commit system prompt generation."""
        from aipr.prompts import PromptManager

        manager = PromptManager()
        system_prompt = manager.get_commit_system_prompt()

        assert "conventional commit" in system_prompt.lower()
        assert "type(scope): description" in system_prompt


class TestNormalizeCommitMessage:
    """Test normalization of raw AI-generated commit messages."""

    def test_clean_single_line_passthrough(self):
        """A well-formed single-line subject is returned unchanged."""
        assert (
            normalize_commit_message("feat: add new functionality") == "feat: add new functionality"
        )

    def test_empty_input(self):
        """Empty or whitespace-only input returns an empty string."""
        assert normalize_commit_message("") == ""
        assert normalize_commit_message("   \n  ") == ""

    def test_strips_surrounding_whitespace(self):
        """Leading/trailing whitespace is trimmed."""
        assert normalize_commit_message("\n  fix: correct bug  \n") == "fix: correct bug"

    def test_strips_plain_code_fence(self):
        """A message wrapped in a bare ``` fence is unwrapped."""
        raw = "```\nfeat: add feature\n```"
        assert normalize_commit_message(raw) == "feat: add feature"

    def test_strips_language_code_fence(self):
        """A ```bash fenced message is unwrapped."""
        raw = "```bash\nfix(api): handle null user\n```"
        assert normalize_commit_message(raw) == "fix(api): handle null user"

    def test_strips_leading_preamble(self):
        """Explanatory prose before the commit line is dropped."""
        raw = "Here is your commit message:\nfeat: add parser"
        assert normalize_commit_message(raw) == "feat: add parser"

    def test_preamble_and_fence_combination(self):
        """A preamble plus a trailing fence are both removed."""
        raw = "Sure! Here you go:\n```\nfeat: add thing\n```"
        assert normalize_commit_message(raw) == "feat: add thing"

    def test_inserts_blank_line_between_subject_and_body(self):
        """A body glued directly to the subject gets a blank-line separator."""
        raw = "feat: add x\nExtra detail about the change"
        assert normalize_commit_message(raw) == "feat: add x\n\nExtra detail about the change"

    def test_collapses_extra_blank_lines(self):
        """Multiple blank lines between subject and body collapse to one."""
        raw = "feat: add x\n\n\n\nbody detail"
        assert normalize_commit_message(raw) == "feat: add x\n\nbody detail"

    def test_strips_trailing_period_from_subject(self):
        """A single trailing period on the subject is removed."""
        assert normalize_commit_message("fix: correct the thing.") == "fix: correct the thing"

    def test_preserves_ellipsis(self):
        """An ellipsis on the subject is preserved (not stripped to '..')."""
        assert normalize_commit_message("chore: work in progress...") == (
            "chore: work in progress..."
        )

    def test_wraps_run_on_subject_with_no_body(self):
        """A long run-on subject with no body is wrapped into subject + body."""
        run_on = (
            "feat: implement conventional commit generation with detailed "
            "analysis of staged changes and automatic type detection and scope"
        )
        assert len(run_on) > MAX_SUBJECT_LENGTH

        result = normalize_commit_message(run_on)
        subject = result.split("\n\n", 1)[0]

        # Subject is now within the limit and a body was created.
        assert len(subject) <= MAX_SUBJECT_LENGTH
        assert "\n\n" in result
        # No content is lost: subject head + body reconstruct the original.
        head, body = result.split("\n\n", 1)
        assert f"{head} {body}" == run_on

    def test_does_not_wrap_subject_when_body_present(self):
        """An over-long subject with an explicit body is left intact."""
        long_subject = "feat: " + "word " * 30  # well over the limit
        raw = f"{long_subject.strip()}\n\nexisting body"
        result = normalize_commit_message(raw)
        # Subject preserved as-is (we don't shuffle content into an existing body).
        assert result.split("\n\n", 1)[0] == long_subject.strip()
        assert result.endswith("existing body")

    def test_unbreakable_long_token_left_unchanged(self):
        """A subject with no whitespace to break on is returned as-is."""
        raw = "feat:" + "a" * 100
        assert normalize_commit_message(raw) == raw


# Fixtures
@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = Repo.init(tmp_dir)
        yield repo, tmp_dir


@pytest.fixture
def commit_analyzer_with_changes(temp_git_repo):
    """Create a CommitAnalyzer with staged changes."""
    repo, tmp_dir = temp_git_repo

    # Create a file and stage it
    test_file = Path(tmp_dir) / "test.py"
    test_file.write_text("def test():\n    pass\n")
    repo.index.add([str(test_file)])

    analyzer = CommitAnalyzer(tmp_dir)
    return analyzer
