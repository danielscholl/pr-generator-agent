"""Commit message generation for AIPR."""

import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import git


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

        # If no specific patterns matched, analyze diff content
        if all(count == 0 for count in type_counts.values()):
            content_type = self._analyze_diff_content(diff_content)
            if content_type:
                type_counts[content_type] = 1

        # Analyze diff content for feature/fix patterns first if mixed types
        total_typed_files = sum(type_counts.values())
        content_type = self._analyze_diff_content(diff_content)

        # If content analysis suggests feat or fix, and we have mixed types, prioritize content
        if content_type in ["feat", "fix"] and total_typed_files > 0:
            return content_type

        # Determine primary type based on priority and count
        if type_counts["feat"] > 0:
            return "feat"
        elif type_counts["fix"] > 0:
            return "fix"
        elif type_counts["docs"] > 0 and sum(type_counts.values()) == type_counts["docs"]:
            return "docs"
        elif type_counts["test"] > 0 and sum(type_counts.values()) == type_counts["test"]:
            return "test"
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
        # Patterns that suggest new features
        feature_patterns = [
            r"^\+.*def\s+\w+",  # New function definitions
            r"^\+.*class\s+\w+",  # New class definitions
            r"^\+.*import\s+\w+",  # New imports (might indicate new functionality)
            r"^\+.*from\s+\w+.*import",  # New imports
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

        # Count feature indicators
        feature_count = 0
        for pattern in feature_patterns:
            feature_count += len(
                [line for line in added_lines if re.search(pattern, line, re.IGNORECASE)]
            )

        # Count fix indicators
        fix_count = 0
        for pattern in fix_patterns:
            fix_count += len([line for line in lines if re.search(pattern, line, re.IGNORECASE)])

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

    def _extract_code_elements(self, diff_content: str) -> Dict[str, list]:
        """Extract meaningful code elements from diff content."""
        elements = {
            "new_classes": [],
            "new_functions": [],
            "new_imports": [],
            "new_constants": [],
            "modified_functions": [],
        }

        lines = diff_content.split("\n")
        for line in lines:
            if not line.startswith("+"):
                continue

            line = line[1:].strip()  # Remove + and whitespace

            # New class definitions
            class_match = re.search(r"class\s+(\w+)", line)
            if class_match:
                elements["new_classes"].append(class_match.group(1))

            # New function definitions
            func_match = re.search(r"def\s+(\w+)", line)
            if func_match:
                elements["new_functions"].append(func_match.group(1))

            # New imports
            import_match = re.search(r"(?:from\s+[\w.]+\s+)?import\s+([\w.,\s]+)", line)
            if import_match:
                imports = [imp.strip() for imp in import_match.group(1).split(",")]
                elements["new_imports"].extend(imports)

            # Constants and variables
            const_match = re.search(r"(\w+)\s*=\s*[\"'\[\{]", line)
            if const_match and const_match.group(1).isupper():
                elements["new_constants"].append(const_match.group(1))

        return elements

    def _generate_specific_description(
        self, commit_type: str, elements: Dict[str, list], files: list
    ) -> Optional[str]:
        """Generate specific description based on extracted code elements."""
        if commit_type == "feat":
            # Prioritize classes, then functions, then imports
            if elements["new_classes"]:
                main_class = elements["new_classes"][0]
                if len(elements["new_classes"]) == 1:
                    return f"add {main_class} class"
                else:
                    return f"add {main_class} and {len(elements['new_classes'])-1} other classes"

            elif elements["new_functions"]:
                main_func = elements["new_functions"][0]
                if len(elements["new_functions"]) == 1:
                    # Try to infer purpose from function name
                    if "parse" in main_func.lower():
                        return f"add {main_func} parser"
                    elif "analyze" in main_func.lower():
                        return f"add {main_func} analysis"
                    elif "generate" in main_func.lower():
                        return f"add {main_func} generation"
                    elif "validate" in main_func.lower():
                        return f"add {main_func} validation"
                    else:
                        return f"implement {main_func} functionality"
                else:
                    return f"add {len(elements['new_functions'])} new functions"

            elif elements["new_imports"]:
                # Check for specific library imports that indicate functionality
                imports = elements["new_imports"]
                if any("auth" in imp.lower() for imp in imports):
                    return "add authentication support"
                elif any("test" in imp.lower() for imp in imports):
                    return "add testing framework"
                elif any("api" in imp.lower() for imp in imports):
                    return "add API integration"

        elif commit_type == "fix" and elements["new_functions"]:
            # Look for error-related patterns in function names
            func_names = " ".join(elements["new_functions"]).lower()
            if "error" in func_names or "exception" in func_names:
                return "improve error handling"
            elif "validate" in func_names:
                return "fix validation logic"

        return None

    def generate_description(
        self, commit_type: str, scope: Optional[str], file_stats: Dict[str, any], diff_content: str
    ) -> str:
        """Generate a concise description for the commit message."""
        files = file_stats.get("files", [])

        if not files:
            return "update configuration"

        # Extract code elements from diff
        elements = self._extract_code_elements(diff_content)

        # Try to generate specific description based on code analysis
        specific_desc = self._generate_specific_description(commit_type, elements, files)
        if specific_desc:
            return specific_desc

        # Fallback to enhanced generic descriptions
        if commit_type == "feat":
            if len(files) == 1:
                filename = Path(files[0]["path"]).stem
                # Try to infer from filename
                if "commit" in filename.lower():
                    return "add commit message generation"
                elif "auth" in filename.lower():
                    return "add authentication functionality"
                elif "parse" in filename.lower():
                    return "add parsing functionality"
                else:
                    return f"add {filename} functionality"
            else:
                return f"add new functionality across {len(files)} files"

        elif commit_type == "fix":
            if len(files) == 1:
                filename = Path(files[0]["path"]).stem
                return f"resolve issue in {filename}"
            else:
                return f"fix issues in {len(files)} files"

        elif commit_type == "docs":
            if any("README" in f["path"] for f in files):
                return "update README documentation"
            elif any("CONTRIBUTING" in f["path"] for f in files):
                return "update contributing guidelines"
            elif any("CLAUDE" in f["path"] for f in files):
                return "update AI development documentation"
            else:
                return "update documentation"

        elif commit_type == "test":
            if len(files) == 1:
                filename = Path(files[0]["path"]).stem
                test_target = filename.replace("test_", "").replace("_test", "")
                return f"add {test_target} tests"
            else:
                return f"add tests for {len(files)} modules"

        elif commit_type == "ci":
            return "update CI configuration"

        elif commit_type == "build":
            if any("requirements" in f["path"] for f in files):
                return "update dependencies"
            elif any("pyproject" in f["path"] for f in files):
                return "update project configuration"
            else:
                return "update build configuration"

        else:  # chore, refactor, style, perf
            action_map = {
                "chore": "update",
                "refactor": "refactor",
                "style": "format",
                "perf": "optimize",
            }
            action = action_map.get(commit_type, "update")

            if len(files) == 1:
                filename = Path(files[0]["path"]).stem
                return f"{action} {filename}"
            else:
                return f"{action} multiple files"

    def generate_conventional_commit(self, context: Optional[str] = None) -> str:
        """Generate a conventional commit message from staged changes."""
        diff_content, file_stats = self.get_staged_changes()

        # Analyze the changes
        commit_type = self.categorize_changes(file_stats, diff_content)
        scope = self.determine_scope(file_stats)
        description = self.generate_description(commit_type, scope, file_stats, diff_content)

        # Add context if provided
        if context:
            description = f"{context}: {description}"

        # Format the conventional commit message
        if scope:
            return f"{commit_type}({scope}): {description}"
        else:
            return f"{commit_type}: {description}"

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
