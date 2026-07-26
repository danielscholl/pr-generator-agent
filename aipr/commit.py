"""Commit message generation for AIPR."""

import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import git

# Maximum length for a conventional commit subject line.
# Matches the "under 72 characters" guidance in aipr/prompts/commit.xml.
MAX_SUBJECT_LENGTH = 72

# Matches a conventional commit subject: type, optional scope, optional "!",
# then ": " (e.g. "feat: ...", "fix(core): ...", "refactor(api)!: ...").
_COMMIT_SUBJECT_RE = re.compile(
    r"^(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore)" r"(?:\([^)]*\))?!?:\s",
    re.IGNORECASE,
)


def _is_fence(line: str) -> bool:
    """Return True if a line is a markdown code fence marker (``` or ```lang)."""
    return line.strip().startswith("```")


def _split_subject(subject: str, limit: int) -> Tuple[str, str]:
    """Split an over-long subject at the last word boundary at or before ``limit``.

    Args:
        subject: The subject line to split.
        limit: Maximum length for the head (subject) portion.

    Returns:
        A ``(head, tail)`` tuple. If no suitable word boundary exists at or
        before ``limit`` (e.g. a single very long token), the subject is
        returned unchanged with an empty tail.
    """
    if len(subject) <= limit:
        return subject, ""
    break_at = subject.rfind(" ", 0, limit + 1)
    if break_at <= 0:
        return subject, ""
    return subject[:break_at].rstrip(), subject[break_at:].strip()


def normalize_commit_message(message: str) -> str:
    """Normalize a raw AI-generated commit message into a well-formed commit.

    Model output cannot be trusted to match the repository's conventions, so
    this enforces them deterministically after generation.

    Guarantees:
    - No surrounding markdown code fences or leading explanatory prose.
    - A single-line subject separated from any body by exactly one blank line.
    - A subject no longer than ``MAX_SUBJECT_LENGTH``; overflow from a run-on
      subject is wrapped into the body at a word boundary rather than shipped
      as a single long line, whether or not a body already exists.
    - No trailing period on the subject line.

    Args:
        message: The raw text returned by the AI provider.

    Returns:
        A cleaned commit message ready to hand to ``git commit``.
    """
    if not message or not message.strip():
        return ""

    lines = message.strip().splitlines()

    # 1. Strip leading/trailing markdown code fences the model may wrap around
    #    the message (handles ```, ```bash, and a fenced-then-preamble mix).
    while lines and _is_fence(lines[0]):
        lines = lines[1:]
    while lines and _is_fence(lines[-1]):
        lines = lines[:-1]

    # 2. Drop any leading preamble before the real conventional-commit line
    #    (e.g. "Here is your commit message:").
    subject_idx = next(
        (i for i, line in enumerate(lines) if _COMMIT_SUBJECT_RE.match(line.strip())),
        None,
    )
    if subject_idx:  # truthy => a subject was found at index > 0
        lines = lines[subject_idx:]

    # 3. Separate the subject (first non-empty line) from the body.
    while lines and not lines[0].strip():
        lines = lines[1:]
    if not lines:
        return ""

    subject = lines[0].strip()
    body_lines = lines[1:]

    # 4. Strip a single trailing period from the subject (but keep an ellipsis).
    if subject.endswith(".") and not subject.endswith(".."):
        subject = subject[:-1].rstrip()

    # Collapse blank lines that lead the body.
    while body_lines and not body_lines[0].strip():
        body_lines = body_lines[1:]
    body = "\n".join(body_lines).strip("\n")

    # 5. A run-on subject is the failure mode we most want to prevent: wrap
    #    the overflow into the body instead of shipping it, prepending to any
    #    body the model already produced.
    if len(subject) > MAX_SUBJECT_LENGTH:
        head, tail = _split_subject(subject, MAX_SUBJECT_LENGTH)
        if tail:
            subject = head
            body = f"{tail}\n{body}" if body else tail

    if body:
        return f"{subject}\n\n{body}"
    return subject


class CommitAnalyzer:
    """Analyzes git changes to generate conventional commit messages."""

    CONVENTIONAL_TYPES = {
        "feat": "A new feature",
        "fix": "A bug fix",
        "docs": "Documentation only changes",
        "style": "Changes that do not affect the meaning of the code",
        "refactor": "A code change that neither fixes a bug nor adds a feature",
        "perf": "A code change that improves performance",
        "test": "Adding missing tests or correcting existing tests",
        "build": "Changes that affect the build system or external dependencies",
        "ci": "Changes to CI configuration files and scripts",
        "chore": "Other changes that don't modify src or test files",
    }

    # File patterns for categorizing changes - order matters!
    CATEGORIZATION_PATTERNS = {
        "build": [
            r"^Makefile$",
            r"^CMakeLists\.txt$",
            r"^setup\.py$",
            r"^pyproject\.toml$",
            r"^poetry\.lock$",
            r"^package\.json$",
            r"^package-lock\.json$",
            r"^yarn\.lock$",
            r"^Cargo\.toml$",
            r"^Cargo\.lock$",
            r"^pom\.xml$",
            r"^build\.gradle$",
            r"^requirements.*\.txt$",
            r"^Pipfile",
            r"^\.pre-commit-config\.yaml$",
        ],
        "test": [
            r"^tests?/",
            r"^test/",
            r"_test\.py$",
            r"test_.*\.py$",
            r"\.test\.",
            r"spec\.py$",
            r"conftest\.py$",
        ],
        "ci": [
            r"^\.github/",
            r"^\.gitlab-ci",
            r"^\.travis",
            r"^\.circleci/",
            r"Jenkinsfile",
            r"azure-pipelines",
            r"\.yml$",
            r"\.yaml$",
        ],
        "docs": [
            r"\.md$",
            r"\.rst$",
            r"\.txt$",  # This comes after build patterns so requirements.txt is caught first
            r"^docs/",
            r"^documentation/",
            r"README",
            r"CHANGELOG",
            r"LICENSE",
        ],
    }

    def __init__(self, repo_path: str = "."):
        """Initialize the commit analyzer with a repository path."""
        try:
            self.repo = git.Repo(repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"Invalid git repository: {repo_path}")

    def get_staged_changes(self) -> Tuple[str, Dict[str, any]]:
        """Get staged changes and file statistics."""
        try:
            # Get staged diff
            staged_diff = self.repo.git.diff("--cached")

            if not staged_diff.strip():
                raise ValueError("No staged changes found. Use 'git add' to stage changes first.")

            # Get file statistics
            stats = self._get_file_stats()

            return staged_diff, stats
        except git.exc.GitCommandError as e:
            raise ValueError(f"Failed to get staged changes: {e}")

    def _get_file_stats(self) -> Dict[str, any]:
        """Get statistics about staged files."""
        try:
            # Get staged files with status
            staged_files = self.repo.git.diff("--cached", "--name-status").strip()

            if not staged_files:
                return {"files": [], "added": 0, "modified": 0, "deleted": 0}

            files = []
            added = modified = deleted = 0

            for line in staged_files.split("\n"):
                if line.strip():
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        status, filepath = parts
                        files.append({"status": status, "path": filepath})

                        if status == "A":
                            added += 1
                        elif status == "M":
                            modified += 1
                        elif status == "D":
                            deleted += 1

            return {
                "files": files,
                "added": added,
                "modified": modified,
                "deleted": deleted,
                "total": len(files),
            }
        except git.exc.GitCommandError:
            return {"files": [], "added": 0, "modified": 0, "deleted": 0}

    def categorize_changes(self, file_stats: Dict[str, any], diff_content: str) -> str:
        """Categorize changes to determine the conventional commit type."""
        files = file_stats.get("files", [])

        if not files:
            return "chore"

        # Count file types
        type_counts = dict.fromkeys(self.CONVENTIONAL_TYPES.keys(), 0)

        for file_info in files:
            filepath = file_info["path"]
            detected_type = self._categorize_file(filepath, file_info["status"])
            if detected_type:
                type_counts[detected_type] += 1

        content_type = self._analyze_diff_content(diff_content)

        # A change confined to docs, tests, CI, or build files keeps that type
        # whatever the diff text looks like - a doc that mentions "error" is not
        # a fix. Compare against every file, not just the categorized ones, so a
        # single uncategorized source file still opens this up to content
        # analysis.
        for exclusive_type in ("docs", "test", "ci", "build"):
            if type_counts[exclusive_type] == len(files):
                return exclusive_type

        if content_type in ("feat", "fix"):
            return content_type

        # Determine primary type based on priority and count
        if type_counts["feat"] > 0:
            return "feat"
        elif type_counts["fix"] > 0:
            return "fix"
        elif type_counts["ci"] > 0:
            return "ci"
        elif type_counts["build"] > 0:
            return "build"
        else:
            # Fall back to content analysis or chore
            return content_type if content_type else "chore"

    def _categorize_file(self, filepath: str, status: str) -> Optional[str]:
        """Categorize a single file based on its path and status."""
        # Check patterns in priority order: build, test, ci, docs
        pattern_order = ["build", "test", "ci", "docs"]

        for commit_type in pattern_order:
            if commit_type in self.CATEGORIZATION_PATTERNS:
                patterns = self.CATEGORIZATION_PATTERNS[commit_type]
                for pattern in patterns:
                    if re.search(pattern, filepath, re.IGNORECASE):
                        return commit_type

        # Default categorization based on file status
        if status == "A":  # New files might be features
            return None  # Let content analysis decide
        elif status == "D":  # Deleted files
            return "chore"

        return None

    def _analyze_diff_content(self, diff_content: str) -> Optional[str]:
        """Analyze diff content to determine commit type."""
        # Patterns that suggest new features. Imports are deliberately absent:
        # every kind of change adds them, so they swamped the ratio below and
        # typed ordinary refactors as features.
        feature_patterns = [
            r"^\+.*def\s+\w+",  # New function definitions
            r"^\+.*class\s+\w+",  # New class definitions
            r"^\+.*function\s+\w+",  # JavaScript functions
            r"^\+.*const\s+\w+.*=.*=>",  # Arrow functions
            r"^\+.*export\s+(default\s+)?",  # Export statements
        ]

        # Patterns that suggest bug fixes
        fix_patterns = [
            r"^\+.*fix",
            r"^\+.*bug",
            r"^\+.*error",
            r"^\+.*exception",
            r"^\+.*try.*catch",
            r"^\+.*if.*error",
            r"^\-.*(?:bug|error|exception)",  # Removing buggy code
        ]

        lines = diff_content.split("\n")
        added_lines = [
            line for line in lines if line.startswith("+") and not line.startswith("+++")
        ]
        removed_lines = [
            line for line in lines if line.startswith("-") and not line.startswith("---")
        ]
        # Only lines the commit actually touches. Scanning every line let
        # unchanged context - or the diff header - decide the type, so any file
        # that merely mentioned "error" nearby was typed as a fix.
        changed_lines = added_lines + removed_lines

        # Count feature indicators
        feature_count = 0
        for pattern in feature_patterns:
            feature_count += len(
                [line for line in added_lines if re.search(pattern, line, re.IGNORECASE)]
            )

        # Count fix indicators
        fix_count = 0
        for pattern in fix_patterns:
            fix_count += len(
                [line for line in changed_lines if re.search(pattern, line, re.IGNORECASE)]
            )

        # Simple heuristic: if more than 50% of added lines suggest features
        if feature_count > len(added_lines) * 0.1:  # 10% threshold for features
            return "feat"
        elif fix_count > 0:
            return "fix"

        return None

    def determine_scope(self, file_stats: Dict[str, any]) -> Optional[str]:
        """Determine the scope for the conventional commit message."""
        files = file_stats.get("files", [])

        if not files:
            return None

        # Extract directory paths
        dirs = set()
        for file_info in files:
            filepath = file_info["path"]
            path_parts = Path(filepath).parts

            # Use the first meaningful directory
            if len(path_parts) > 1:
                first_dir = path_parts[0]
                # Skip common top-level directories
                if first_dir not in {".", "..", "__pycache__", ".git"}:
                    dirs.add(first_dir)

        # Common scope mappings
        scope_mappings = {
            "aipr": "core",
            "tests": "test",
            "docs": "docs",
            "scripts": "build",
            ".github": "ci",
            "src": "core",
            "lib": "core",
            "api": "api",
            "ui": "ui",
            "frontend": "ui",
            "backend": "api",
            "database": "db",
            "config": "config",
            "utils": "util",
            "helpers": "util",
        }

        # If only one directory, use it as scope
        if len(dirs) == 1:
            dir_name = list(dirs)[0]
            return scope_mappings.get(dir_name, dir_name)

        # If multiple directories, try to find a common meaningful scope
        if len(dirs) > 1:
            # Check if all are related to the same functional area
            mapped_scopes = {scope_mappings.get(d, d) for d in dirs}
            if len(mapped_scopes) == 1:
                return list(mapped_scopes)[0]

        return None

    def get_analysis_summary(self) -> Dict[str, any]:
        """Get a summary of the staged changes for debugging/verbose output."""
        try:
            diff_content, file_stats = self.get_staged_changes()
            commit_type = self.categorize_changes(file_stats, diff_content)
            scope = self.determine_scope(file_stats)

            return {
                "staged_files": file_stats,
                "detected_type": commit_type,
                "detected_scope": scope,
                "diff_length": len(diff_content),
                "has_changes": bool(diff_content.strip()),
            }
        except ValueError as e:
            return {"error": str(e)}
