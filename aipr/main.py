import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional, Tuple

import git
import tiktoken

from .commit import CommitAnalyzer
from .prompts import InvalidPromptError, PromptManager
from .providers import (
    generate_with_anthropic,
    generate_with_azure_openai,
    generate_with_gemini,
    generate_with_openai,
)

# ANSI color codes
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"


def detect_provider_and_model(model: Optional[str]) -> Tuple[str, str]:
    """Detect which provider and model to use based on environment and args."""
    if model:
        # Handle simple aliases first
        if model == "claude":
            return "anthropic", "claude-sonnet-4-20250514"
        if model == "azure":
            return "azure", "gpt-4o-mini"
        if model == "openai":
            return "openai", "gpt-4o"
        if model == "gemini":
            return "gemini", "gemini-2.5-pro-experimental"

        # Handle Azure models
        if model.startswith("azure/"):
            _, model_name = model.split("/", 1)
            # Map azure model names to deployment names
            azure_models = {
                "o1-mini": "o1-mini",
                "gpt-4o": "gpt-4o",
                "gpt-4o-mini": "gpt-4o-mini",
                "gpt-4": "gpt-4o",  # Alias for gpt-4o
            }
            return "azure", azure_models.get(model_name, model_name)

        # Handle Gemini models
        if model.startswith("gemini"):
            gemini_models = {
                "gemini-1.5-pro": "gemini-1.5-pro",
                "gemini-1.5-flash": "gemini-1.5-flash",
                "gemini-2.5-pro-experimental": "gemini-2.5-pro-exp-03-25",
            }
            return "gemini", gemini_models.get(model, model)

        # Handle OpenAI models
        if model.startswith("gpt") or model == "gpt4":
            # Only use Azure if explicitly configured with endpoint
            if os.getenv("AZURE_OPENAI_ENDPOINT") and model.startswith("azure/"):
                openai_models = {
                    "gpt4": "gpt-4",
                    "gpt-4-turbo": "gpt-4-turbo",
                    "gpt-4o": "gpt-4",
                }
                return "azure", openai_models.get(model, model)
            else:
                openai_models = {
                    "gpt4": "gpt-4",
                    "gpt-4-turbo": "gpt-4-turbo",
                    "gpt-4o": "gpt-4",
                }
                return "openai", openai_models.get(model, model)

        # Handle Anthropic models
        if model.startswith("claude"):
            anthropic_models = {
                "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
                "claude-3.5-haiku": "claude-3-5-haiku-20241022",
                "claude-3-haiku": "claude-3-haiku-20240307",
                "claude-4": "claude-sonnet-4-20250514",
                "claude-4.0": "claude-sonnet-4-20250514",
            }
            return "anthropic", anthropic_models.get(model, model)

    # No model specified, check environment for default
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic", "claude-sonnet-4-20250514"
    if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_API_KEY"):
        return "azure", "gpt-4"
    if os.getenv("OPENAI_API_KEY"):
        return "openai", "gpt-4"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini", "gemini-2.5-pro-experimental"

    raise Exception(
        "No API key found. Please set ANTHROPIC_API_KEY, AZURE_API_KEY, "
        "OPENAI_API_KEY, or GEMINI_API_KEY"
    )


def count_tokens(text: str, model: str) -> int:
    """Count the number of tokens in a text string."""
    try:
        if model.startswith(("gpt-3", "gpt-4")):
            encoding = tiktoken.encoding_for_model(model)
        else:
            # Default to cl100k_base for other models (including Azure and Claude)
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # If we can't get a token count, return an estimate
        return len(text) // 4  # Rough estimate of tokens


def print_token_info(user_prompt: str, system_prompt: str, verbose: bool):
    """Print token information for the prompts."""
    if verbose:
        print(f"System Prompt:\n{system_prompt}\n")
        print(f"User Prompt:\n{user_prompt}\n")
    # Add actual token counting if needed


def print_separator(char="─", color=GREEN):
    """Print a separator line with the given character and color."""
    terminal_width = os.get_terminal_size().columns
    print(f"{color}{char * terminal_width}{ENDC}")


def print_header(text: str, level: int = 1):
    """Print a header with the given text and level."""
    if level == 1:
        print(f"\n{text}")
        print("=" * len(text))
    else:
        print(f"\n{text}")
        print("-" * len(text))


def run_trivy_scan(path: str, silent: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """Run trivy filesystem scan and return the results as a dictionary."""
    try:
        # Determine project type and scanning approach
        is_java = os.path.exists(os.path.join(path, "pom.xml"))
        is_node = os.path.exists(os.path.join(path, "package.json"))

        # Enhanced Python project detection
        python_files = [
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
            "poetry.lock",
            "Pipfile",
            "Pipfile.lock",
        ]
        is_python = any(os.path.exists(os.path.join(path, f)) for f in python_files)

        trivy_args = [
            "trivy",
            "fs",
            "--format",
            "json",
            "--scanners",
            "vuln,secret,config",
        ]

        # Add dependency scanning for supported project types
        if is_java:
            try:
                if not silent:
                    print(
                        f"{BLUE}Detected Java project, " f"resolving Maven dependencies...{ENDC}",
                        file=sys.stderr,
                    )
                subprocess.run(
                    ["mvn", "dependency:resolve", "-DskipTests"],
                    cwd=path,
                    check=True,
                    capture_output=True,
                )
                trivy_args.append("--dependency-tree")
            except subprocess.CalledProcessError as e:
                print(
                    f"{YELLOW}Warning: Maven dependency resolution failed: {e}{ENDC}",
                    file=sys.stderr,
                )
        elif is_node:
            if not silent:
                print(
                    f"{BLUE}Detected Node.js project, including dependency scanning...{ENDC}",
                    file=sys.stderr,
                )
            trivy_args.append("--dependency-tree")
        elif is_python:
            if not silent:
                print(
                    f"{BLUE}Detected Python project, including enhanced scanning...{ENDC}",
                    file=sys.stderr,
                )

            # Check which package management files exist
            pkg_files = []
            has_poetry = os.path.exists(os.path.join(path, "poetry.lock"))
            has_pipenv = os.path.exists(os.path.join(path, "Pipfile.lock"))
            has_pip = os.path.exists(os.path.join(path, "requirements.txt"))
            has_setup = os.path.exists(os.path.join(path, "setup.py"))
            has_pyproject = os.path.exists(os.path.join(path, "pyproject.toml"))

            if has_poetry:
                pkg_files.append("poetry.lock")
                if has_pyproject:
                    pkg_files.append("pyproject.toml")
                if not silent:
                    print(
                        f"{BLUE}Using Poetry for dependency scanning "
                        f"(transitive dependencies, excludes dev)...{ENDC}",
                        file=sys.stderr,
                    )
            elif has_pipenv:
                pkg_files.append("Pipfile.lock")
                if not silent:
                    print(
                        f"{BLUE}Using Pipenv for dependency scanning "
                        f"(transitive dependencies, includes dev)...{ENDC}",
                        file=sys.stderr,
                    )
            elif has_pip:
                pkg_files.append("requirements.txt")
                if not silent:
                    print(
                        f"{BLUE}Using pip requirements "
                        f"(direct dependencies only, includes dev)...{ENDC}",
                        file=sys.stderr,
                    )
            elif has_setup or has_pyproject:
                if has_setup:
                    pkg_files.append("setup.py")
                if has_pyproject:
                    pkg_files.append("pyproject.toml")
                if not silent:
                    print(
                        f"{BLUE}Using Python package metadata files...{ENDC}",
                        file=sys.stderr,
                    )

            if pkg_files and not silent:
                print(
                    f"{BLUE}Found package files: {', '.join(pkg_files)}{ENDC}",
                    file=sys.stderr,
                )

            # Add Python-specific scanning options
            trivy_args.append("--dependency-tree")
        else:
            if not silent:
                print(
                    f"{BLUE}No specific package manager detected, "
                    f"performing filesystem scan...{ENDC}",
                    file=sys.stderr,
                )

        # Add the path as the last argument
        trivy_args.append(path)

        if not silent and verbose:
            print(
                f"{BLUE}Running trivy with args: {' '.join(trivy_args)}{ENDC}",
                file=sys.stderr,
            )

        # Run trivy scan
        result = subprocess.run(trivy_args, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error running trivy scan: {e}{ENDC}", file=sys.stderr)
        if e.stderr:
            print(f"{RED}Trivy error details: {e.stderr}{ENDC}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"{RED}Error parsing trivy output: {e}{ENDC}", file=sys.stderr)
        return {}


def compare_vulnerabilities(
    current_scan: Dict[str, Any], target_scan: Dict[str, Any]
) -> Tuple[str, str]:
    """
    Compare vulnerability scans between branches and return a tuple of
    (markdown_report, analysis_data)
    """
    if not current_scan or not target_scan:
        return "Error: Unable to generate vulnerability comparison", ""

    report = ["## Vulnerability Comparison\n"]
    analysis_data = ["### Security Analysis Data\n"]

    # Get vulnerabilities from both scans
    current_vulns = []
    target_vulns = []

    def extract_vulns(scan_data: Dict[str, Any]) -> list:
        vulns = []
        for result in scan_data.get("Results", []):
            target = result.get("Target", "")
            type = result.get("Type", "")
            for vuln in result.get("Vulnerabilities", []):
                vulns.append(
                    {
                        "id": vuln.get("VulnerabilityID"),
                        "pkg": vuln.get("PkgName"),
                        "version": vuln.get("InstalledVersion"),
                        "severity": vuln.get("Severity"),
                        "description": vuln.get("Description"),
                        "fix_version": vuln.get("FixedVersion"),
                        "target": target,
                        "type": type,
                        "title": vuln.get("Title"),
                        "references": vuln.get("References", []),
                    }
                )
        return vulns

    current_vulns = extract_vulns(current_scan)
    target_vulns = extract_vulns(target_scan)

    # Create unique identifiers for comparison
    def create_vuln_key(v: Dict[str, Any]) -> str:
        return f"{v['id']}:{v['pkg']}:{v['version']}:{v['target']}"

    current_vuln_keys = {create_vuln_key(v) for v in current_vulns}
    target_vuln_keys = {create_vuln_key(v) for v in target_vulns}

    # Find new and fixed vulnerabilities
    new_vulns = current_vuln_keys - target_vuln_keys
    fixed_vulns = target_vuln_keys - current_vuln_keys

    # Group vulnerabilities by severity for analysis
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}

    def group_by_severity(vulns_keys: set, vuln_list: list) -> Dict[str, list]:
        grouped = {}
        for vuln in vuln_list:
            key = create_vuln_key(vuln)
            if key in vulns_keys:
                sev = vuln["severity"] or "UNKNOWN"
                if sev not in grouped:
                    grouped[sev] = []
                grouped[sev].append(vuln)
        return {
            k: grouped[k] for k in sorted(grouped.keys(), key=lambda x: severity_order.get(x, 999))
        }

    # Prepare detailed analysis data
    if new_vulns:
        analysis_data.append("\nNew Vulnerabilities Details:")
        grouped_new = group_by_severity(new_vulns, current_vulns)
        for severity, vulns in grouped_new.items():
            analysis_data.append(f"\n{severity} Severity:")
            for vuln in sorted(vulns, key=lambda x: x["id"]):
                analysis_data.append(f"\n- {vuln['id']} ({vuln['type']}):")
                analysis_data.append(f"  - Package: {vuln['pkg']} {vuln['version']}")
                analysis_data.append(f"  - In: {vuln['target']}")
                analysis_data.append(f"  - Title: {vuln['title']}")
                analysis_data.append(f"  - Description: {vuln['description']}")
                if vuln["fix_version"]:
                    fix_info = f"  - Fix available in version: " f"{vuln['fix_version']}"
                    analysis_data.append(fix_info)
                if vuln["references"]:
                    analysis_data.append("  - References:")
                    for ref in vuln["references"][:3]:  # Limit to first 3 references
                        analysis_data.append(f"    * {ref}")

    if fixed_vulns:
        analysis_data.append("\nFixed Vulnerabilities Details:")
        grouped_fixed = group_by_severity(fixed_vulns, target_vulns)
        for severity, vulns in grouped_fixed.items():
            analysis_data.append(f"\n{severity} Severity:")
            for vuln in sorted(vulns, key=lambda x: x["id"]):
                analysis_data.append(f"\n- {vuln['id']} ({vuln['type']}):")
                analysis_data.append(f"  - Package: {vuln['pkg']} {vuln['version']}")
                analysis_data.append(f"  - In: {vuln['target']}")
                analysis_data.append(f"  - Title: {vuln['title']}")

    # Generate markdown report
    if new_vulns:
        report.append("\n### New Vulnerabilities\n")
        grouped_new = group_by_severity(new_vulns, current_vulns)
        for severity, vulns in grouped_new.items():
            report.append(f"\n#### {severity}\n")
            for vuln in sorted(vulns, key=lambda x: x["id"]):
                vuln_line = (
                    f"- {vuln['id']} in {vuln['pkg']} " f"{vuln['version']} ({vuln['target']})"
                )
                report.append(vuln_line)

    if fixed_vulns:
        report.append("\n### Fixed Vulnerabilities\n")
        grouped_fixed = group_by_severity(fixed_vulns, target_vulns)
        for severity, vulns in grouped_fixed.items():
            report.append(f"\n#### {severity}\n")
            for vuln in sorted(vulns, key=lambda x: x["id"]):
                vuln_line = (
                    f"- {vuln['id']} in {vuln['pkg']} " f"{vuln['version']} ({vuln['target']})"
                )
                report.append(vuln_line)

    if not new_vulns and not fixed_vulns:
        report.append("\nNo vulnerability changes detected between branches.")
        analysis_data.append("\nNo security changes to analyze.")

    return "\n".join(report), "\n".join(analysis_data)


class ColorHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom formatter to preserve colors in help text."""

    def _split_lines(self, text, width):
        return text.splitlines()


def parse_args(args=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="AI-powered tool for generating PR descriptions and commit messages",
        formatter_class=ColorHelpFormatter,
        epilog=f"""
recommended models:
  {GREEN}claude-4{ENDC} (default)             Anthropic's Claude 4.0 Sonnet
  {YELLOW}azure/o1-mini{ENDC}                  Azure OpenAI o1-mini
  {YELLOW}azure/gpt-4o{ENDC}                   Azure OpenAI GPT-4
  {YELLOW}gpt-4{ENDC}                          OpenAI GPT-4
  {YELLOW}gemini-2.5-pro-experimental{ENDC}    Google's Gemini 2.5 Pro

prompt templates:
  {BLUE}meta{ENDC}                          Default XML prompt template for merge requests
  {BLUE}commit{ENDC}                        XML prompt template for commit messages""",
    )

    # Global options
    parser.add_argument("-s", "--silent", action="store_true", help="Silent mode")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Debug mode - show prompts without sending to LLM",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose mode - show detailed API interaction",
    )
    parser.add_argument(
        "-m",
        "--model",
        help="AI model to use (see recommended models below)",
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # PR command (generate pull request descriptions)
    pr_parser = subparsers.add_parser(
        "pr",
        help="Generate pull request description from git diff or commit range",
        formatter_class=ColorHelpFormatter,
    )
    # Add global flags to pr subcommand
    pr_parser.add_argument("-s", "--silent", action="store_true", help="Silent mode")
    pr_parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Debug mode - show prompts without sending to LLM",
    )
    pr_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose mode - show detailed API interaction"
    )
    pr_parser.add_argument("-m", "--model", help="AI model to use")
    # PR-specific arguments
    pr_parser.add_argument("-t", "--target", help="Target branch for comparison")
    pr_parser.add_argument("--vulns", action="store_true", help="Include vulnerability scan")
    pr_parser.add_argument("--working-tree", action="store_true", help="Use working tree")
    pr_parser.add_argument(
        "-p",
        "--prompt",
        help=(
            "Specify either a built-in prompt name (e.g., 'meta') or "
            "a path to a custom XML prompt file (e.g., '~/prompts/custom.xml')"
        ),
    )
    pr_parser.add_argument(
        "--from",
        dest="from_commit",
        help="Starting commit for range analysis (SHA, branch, tag, etc.)",
    )
    pr_parser.add_argument(
        "--to",
        dest="to_commit",
        help="Ending commit for range analysis (defaults to HEAD, requires --from)",
    )

    # Commit command (generate commit messages)
    commit_parser = subparsers.add_parser(
        "commit",
        help="Generate conventional commit message from staged changes or commit range",
        formatter_class=ColorHelpFormatter,
    )
    # Add global flags to commit subcommand
    commit_parser.add_argument("-s", "--silent", action="store_true", help="Silent mode")
    commit_parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Debug mode - show prompts without sending to LLM",
    )
    commit_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose mode - show detailed API interaction"
    )
    commit_parser.add_argument("-m", "--model", help="AI model to use")
    # Commit-specific arguments
    commit_parser.add_argument(
        "--conventional", action="store_true", help="Generate conventional commit message (default)"
    )
    commit_parser.add_argument(
        "--format",
        choices=["conventional"],
        default="conventional",
        help="Format for commit message (default: conventional)",
    )
    commit_parser.add_argument("--context", help="Additional context for the commit message")
    commit_parser.add_argument(
        "--from",
        dest="from_commit",
        help="Starting commit for range analysis (SHA, branch, tag, etc.)",
    )
    commit_parser.add_argument(
        "--to",
        dest="to_commit",
        help="Ending commit for range analysis (defaults to HEAD, requires --from)",
    )

    # Check if args look like old-style (no subcommand) before parsing
    is_old_style = True
    if args is not None:
        # If first arg is a known subcommand or help, it's new style
        if len(args) > 0 and args[0] in ["pr", "commit", "-h", "--help"]:
            is_old_style = False
    else:
        # Check sys.argv for subcommands
        import sys

        if len(sys.argv) > 1 and sys.argv[1] in ["pr", "commit", "-h", "--help"]:
            is_old_style = False

    if is_old_style:
        # Parse with old-style expectations - need to separate global args from subcommand args
        if args is not None:
            args_list = list(args)
        else:
            import sys

            args_list = sys.argv[1:]

        # Separate global args from pr-specific args
        global_args = []
        pr_args = []

        i = 0
        while i < len(args_list):
            arg = args_list[i]
            if arg in ["-s", "--silent", "-d", "--debug", "-v", "--verbose"]:
                global_args.append(arg)
            elif arg in ["-m", "--model"] and i + 1 < len(args_list):
                global_args.extend([arg, args_list[i + 1]])
                i += 1  # Skip the next arg as it's the value
            else:
                pr_args.append(arg)
            i += 1

        # Construct args in proper order: global_args + ["pr"] + pr_args
        args_to_parse = global_args + ["pr"] + pr_args
        parsed_args = parser.parse_args(args_to_parse)
    else:
        # Parse normally with subcommands
        parsed_args = parser.parse_args(args)

    # If command is None after parsing, set default
    if not hasattr(parsed_args, "command") or parsed_args.command is None:
        # Create a mock args object for pr command with default values
        class PRArgs:
            def __init__(self):
                self.command = "pr"
                self.silent = parsed_args.silent
                self.debug = parsed_args.debug
                self.verbose = parsed_args.verbose
                self.model = parsed_args.model
                # Add pr-specific defaults
                self.target = None
                self.vulns = False
                self.working_tree = False
                self.prompt = None

        # Check if original args had pr-specific flags
        if args is not None:
            pr_args = PRArgs()
            # Parse original args to extract pr-specific flags
            if "--vulns" in args:
                pr_args.vulns = True
            if "--working-tree" in args:
                pr_args.working_tree = True
            if "-t" in args:
                target_idx = args.index("-t")
                if target_idx + 1 < len(args):
                    pr_args.target = args[target_idx + 1]
            if "--target" in args:
                target_idx = args.index("--target")
                if target_idx + 1 < len(args):
                    pr_args.target = args[target_idx + 1]
            if "-p" in args:
                prompt_idx = args.index("-p")
                if prompt_idx + 1 < len(args):
                    pr_args.prompt = args[prompt_idx + 1]
            if "--prompt" in args:
                prompt_idx = args.index("--prompt")
                if prompt_idx + 1 < len(args):
                    pr_args.prompt = args[prompt_idx + 1]
            return pr_args
        else:
            return PRArgs()

    return parsed_args


def detect_default_branch(repo: git.Repo) -> str:
    """Detect the default branch of the repository."""
    for branch in ["main", "master", "develop"]:
        try:
            repo.git.rev_parse("--verify", branch)
            return branch
        except git.exc.GitCommandError:
            continue
    raise Exception("Could not detect default branch")


def get_commit_range_diff(
    repo: git.Repo, from_commit: str, to_commit: str = "HEAD"
) -> Tuple[str, Dict[str, any]]:
    """Get diff and file statistics for a commit range.

    Args:
        repo: Git repository object
        from_commit: Starting commit (SHA, branch name, tag, etc.)
        to_commit: Ending commit (defaults to HEAD)

    Returns:
        Tuple of (diff_content, file_stats)

    Raises:
        ValueError: If commits don't exist or range is invalid
    """
    try:
        # Validate that both commits exist
        repo.git.cat_file("-e", f"{from_commit}^{{commit}}")
        repo.git.cat_file("-e", f"{to_commit}^{{commit}}")

        # Get the diff between commits
        diff_content = repo.git.diff(f"{from_commit}..{to_commit}")

        if not diff_content.strip():
            raise ValueError(f"No changes found between {from_commit} and {to_commit}")

        # Get file statistics
        name_status = repo.git.diff(f"{from_commit}..{to_commit}", "--name-status")

        files = []
        added = modified = deleted = 0

        if name_status.strip():
            for line in name_status.split("\n"):
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

        file_stats = {
            "files": files,
            "added": added,
            "modified": modified,
            "deleted": deleted,
            "total": len(files),
        }

        return diff_content, file_stats

    except git.exc.GitCommandError as e:
        if "does not exist" in str(e) or "bad revision" in str(e):
            raise ValueError(f"Invalid commit reference: {from_commit} or {to_commit}")
        else:
            raise ValueError(f"Failed to get commit range diff: {e}")


def validate_commit_range_args(args, command_name: str) -> None:
    """Validate commit range arguments for pr and commit commands.

    Args:
        args: Parsed command line arguments
        command_name: Name of the command ("pr" or "commit") for error messages

    Raises:
        ValueError: If argument combination is invalid
    """
    from_commit = getattr(args, "from_commit", None)
    to_commit = getattr(args, "to_commit", None)

    # Rule: --to can only be used with --from
    if to_commit and not from_commit:
        raise ValueError("--to can only be used together with --from")

    # For pr command: check mutual exclusivity
    if command_name == "pr":
        target = getattr(args, "target", None)
        working_tree = getattr(args, "working_tree", False)

        if from_commit and target:
            raise ValueError("--from/--to cannot be used with --target (mutually exclusive)")

        if from_commit and working_tree:
            raise ValueError("--from/--to cannot be used with --working-tree (mutually exclusive)")


def determine_pr_mode(args) -> str:
    """Determine which mode the pr command should use.

    Returns:
        Mode string: "range", "working_tree", "target", or "auto"
    """
    from_commit = getattr(args, "from_commit", None)
    working_tree = getattr(args, "working_tree", False)
    target = getattr(args, "target", None)

    if from_commit:
        return "range"
    elif working_tree or target == "-":
        return "working_tree"  # "-" means working tree mode
    elif target:
        return "target"
    else:
        return "auto"


def determine_commit_mode(args) -> str:
    """Determine which mode the commit command should use.

    Returns:
        Mode string: "range" or "staged"
    """
    from_commit = getattr(args, "from_commit", None)

    if from_commit:
        return "range"
    else:
        return "staged"


def get_vulnerability_data() -> Optional[str]:
    """Get vulnerability scan data using trivy."""
    try:
        result = subprocess.run(
            ["trivy", "fs", "--quiet", "--severity", "HIGH,CRITICAL", "."],
            capture_output=True,
            text=True,
        )
        return result.stdout if result.stdout.strip() else None
    except FileNotFoundError:
        print("Warning: trivy not found. Skipping vulnerability scan.")
        return None


def generate_description(
    diff: str,
    vuln_data: Optional[str],
    provider: str,
    model: str,
    system_prompt: str,
    verbose: bool = False,
    prompt_manager: Optional[PromptManager] = None,
) -> str:
    """Generate description using the specified provider."""
    # Get the user prompt from the prompt manager
    if prompt_manager is None:
        prompt_manager = PromptManager()
    user_prompt = prompt_manager.get_user_prompt(diff, vuln_data)

    if provider == "anthropic":
        return generate_with_anthropic(user_prompt, vuln_data, model, system_prompt, verbose)
    if provider == "azure":
        return generate_with_azure_openai(user_prompt, vuln_data, model, system_prompt, verbose)
    if provider == "openai":
        return generate_with_openai(user_prompt, vuln_data, model, system_prompt, verbose)
    if provider == "gemini":
        return generate_with_gemini(user_prompt, vuln_data, model, system_prompt, verbose)
    raise ValueError(f"Unknown provider: {provider}")


def generate_commit_message(
    staged_changes: str,
    file_summary: Dict[str, Any],
    provider: str,
    model: str,
    verbose: bool = False,
    context: str = "",
) -> str:
    """Generate commit message using the specified provider."""
    prompt_manager = PromptManager()
    system_prompt = prompt_manager.get_commit_system_prompt()
    user_prompt = prompt_manager.get_commit_prompt(staged_changes, file_summary, context)

    if provider == "anthropic":
        return generate_with_anthropic(user_prompt, None, model, system_prompt, verbose)
    if provider == "azure":
        return generate_with_azure_openai(user_prompt, None, model, system_prompt, verbose)
    if provider == "openai":
        return generate_with_openai(user_prompt, None, model, system_prompt, verbose)
    if provider == "gemini":
        return generate_with_gemini(user_prompt, None, model, system_prompt, verbose)
    raise ValueError(f"Unknown provider: {provider}")


def handle_pr_command(args):
    """Handle the pr command (PR description generation)."""
    try:
        repo = git.Repo(os.getcwd(), search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        print(
            f"{RED}Error: Directory is not a valid Git repository{ENDC}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        prompt_manager = PromptManager(getattr(args, "prompt", None))
    except InvalidPromptError as e:
        print(f"{RED}Error: {str(e)}{ENDC}")
        sys.exit(1)

    # Validate arguments
    try:
        validate_commit_range_args(args, "pr")
    except ValueError as e:
        print(f"{RED}Error: {e}{ENDC}", file=sys.stderr)
        sys.exit(1)

    provider, model = detect_provider_and_model(args.model)

    # Determine which mode to use and get the diff
    mode = determine_pr_mode(args)
    diff = ""

    try:
        if mode == "range":
            # Commit range mode
            from_commit = args.from_commit
            to_commit = getattr(args, "to_commit", None) or "HEAD"

            if not args.silent:
                print(
                    f"{BLUE}Analyzing commit range {from_commit}..{to_commit}...{ENDC}",
                    file=sys.stderr,
                )

            diff, _ = get_commit_range_diff(repo, from_commit, to_commit)

        elif mode == "working_tree":
            # Working tree changes
            if not args.silent:
                print(f"{BLUE}Showing working tree changes...{ENDC}", file=sys.stderr)
            diff = repo.git.diff("HEAD", "--cached") + "\n" + repo.git.diff()

        elif mode == "target":
            # Target branch comparison
            target = args.target
            if not args.silent:
                print(f"{BLUE}Comparing with {target}...{ENDC}", file=sys.stderr)
            diff = repo.git.diff(f"{target}...{repo.active_branch.name}")

        else:  # mode == "auto"
            # Auto-detect mode (existing behavior)
            if repo.is_dirty():
                # Show working tree changes
                if not args.silent:
                    print(f"{BLUE}Showing working tree changes...{ENDC}", file=sys.stderr)
                diff = repo.git.diff("HEAD", "--cached") + "\n" + repo.git.diff()
            else:
                # Try to find default branch
                target = None
                for branch in ["main", "master", "develop"]:
                    if branch in [h.name for h in repo.heads]:
                        target = branch
                        break

                if target:
                    if not args.silent:
                        print(f"{BLUE}Comparing with {target}...{ENDC}", file=sys.stderr)
                    diff = repo.git.diff(f"{target}...{repo.active_branch.name}")
                else:
                    print(f"{YELLOW}No suitable target branch found.{ENDC}", file=sys.stderr)
                    sys.exit(1)

        if not diff.strip():
            print("No changes found in the Git repository.", file=sys.stderr)
            sys.exit(0)

    except ValueError as e:
        print(f"{RED}Error: {e}{ENDC}", file=sys.stderr)
        sys.exit(1)

    # Get vulnerability data if requested
    vuln_data = None
    vulns = getattr(args, "vulns", False)
    if vulns:
        if not args.silent:
            print(f"{BLUE}Running vulnerability scan...{ENDC}", file=sys.stderr)
        vuln_data = run_trivy_scan(repo.working_dir, args.silent, False)

    # Generate the description
    if not args.silent:
        print_header("\nGenerating Description")
        print(f"Using {provider} ({model})...")

    try:
        # In debug mode, show the prompts that would be sent
        if args.debug:
            # Get the prompts first
            system_prompt = prompt_manager.get_system_prompt()
            user_prompt = prompt_manager.get_user_prompt(diff, vuln_data)

            # Prepare the API parameters
            if provider == "azure" and model == "o1-mini":
                combined_prompt = (
                    f"System Instructions:\n{system_prompt}\n\n" f"User Request:\n{user_prompt}"
                )
                messages = [{"role": "user", "content": combined_prompt}]
                params = {
                    "model": model,
                    "messages": messages,
                    "max_completion_tokens": 1000,
                }
            elif provider == "anthropic":
                params = {
                    "model": model,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.2,
                }
            elif provider == "gemini":
                # Structure for Gemini
                gemini_text = "System instructions: " + system_prompt + "\n\n" + user_prompt
                params = {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "parts": [{"text": gemini_text}],
                        }
                    ],
                    "generation_config": {"temperature": 0.2},
                }
            else:
                params = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.2,
                }

            # Print debug information in a structured way
            print_header("Debug Information")

            print_header("API Call Structure", level=2)
            print(f"Provider: {provider}")
            print(f"Model: {model}")
            print(
                f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT', 'Not Set')}"
                if provider == "azure"
                else ""
            )
            print("\nParameters:")
            print("─" * 40)
            print(json.dumps({k: v for k, v in params.items() if k != "messages"}, indent=2))
            print("\nMessages:")
            print("─" * 40)
            for msg in params["messages"]:
                print(f"\n{msg['role'].upper()} MESSAGE:")
                print(msg["content"])
            print()
            sys.exit(0)

        # Generate the description
        description = generate_description(
            diff,
            vuln_data,
            provider,
            model,
            (
                prompt_manager.get_system_prompt()
                if prompt_manager
                else PromptManager().get_system_prompt()
            ),
            args.verbose,
            prompt_manager or PromptManager(),  # Ensure we always pass a valid PromptManager
        )

        if args.verbose:
            print("\nAPI Response:")
            print("─" * 40)
        print(description)

    except Exception as e:
        print(f"{RED}Error: {provider.title()} API - {e}{ENDC}", file=sys.stderr)
        sys.exit(1)


def handle_commit_command(args):
    """Handle the commit command (commit message generation)."""
    try:
        # Validate arguments
        validate_commit_range_args(args, "commit")
    except ValueError as e:
        print(f"{RED}Error: {e}{ENDC}", file=sys.stderr)
        sys.exit(1)

    try:
        # Determine mode and get changes/file summary
        mode = determine_commit_mode(args)

        if mode == "range":
            # Commit range mode
            repo = git.Repo(os.getcwd(), search_parent_directories=True)
            from_commit = args.from_commit
            to_commit = getattr(args, "to_commit", None) or "HEAD"

            if not args.silent:
                print(
                    f"{BLUE}Analyzing commit range {from_commit}..{to_commit}...{ENDC}",
                    file=sys.stderr,
                )

            changes, file_summary = get_commit_range_diff(repo, from_commit, to_commit)

            if args.debug:
                print_header("Commit Range Analysis Debug")
                print(f"Range: {from_commit}..{to_commit}")
                print(f"Files changed: {file_summary.get('total', 0)}")
                print(
                    f"Added: {file_summary.get('added', 0)}, Modified: {file_summary.get('modified', 0)}, Deleted: {file_summary.get('deleted', 0)}"
                )
                print("\nCommit range changes preview:")
                print("─" * 40)
                preview = changes[:500] + "..." if len(changes) > 500 else changes
                print(preview)
                sys.exit(0)

        else:  # mode == "staged"
            # Staged changes mode (existing behavior)
            commit_analyzer = CommitAnalyzer()
            changes, file_summary = commit_analyzer.get_staged_changes()

            if args.debug:
                # Show analysis without generating AI response
                analysis = commit_analyzer.get_analysis_summary()
                print_header("Staged Changes Analysis Debug")
                print(f"Detected type: {analysis.get('detected_type', 'unknown')}")
                print(f"Detected scope: {analysis.get('detected_scope', 'none')}")
                print(f"Staged files: {analysis.get('staged_files', {}).get('total', 0)}")
                print("\nStaged changes preview:")
                print("─" * 40)
                preview = changes[:500] + "..." if len(changes) > 500 else changes
                print(preview)
                sys.exit(0)

        provider, model = detect_provider_and_model(args.model)

        if not args.silent:
            mode_text = "commit range" if mode == "range" else "staged changes"
            print(f"{BLUE}Analyzing {mode_text}...{ENDC}", file=sys.stderr)
            print(f"Using {provider} ({model})...", file=sys.stderr)

        # Get context if provided
        context = getattr(args, "context", "") or ""

        try:
            # Generate commit message using AI
            commit_message = generate_commit_message(
                changes, file_summary, provider, model, args.verbose, context
            )

            # Clean up the response (remove any extra whitespace/newlines)
            commit_message = commit_message.strip()

            if args.verbose:
                print("\nGenerated commit message:", file=sys.stderr)
                print("─" * 40, file=sys.stderr)

            print(commit_message)

        except Exception as e:
            print(f"{RED}Error generating commit message: {e}{ENDC}", file=sys.stderr)

            # Fallback to local analysis only for staged changes mode
            if mode == "staged":
                if not args.silent:
                    print(f"{YELLOW}Falling back to local analysis...{ENDC}", file=sys.stderr)

                try:
                    commit_analyzer = CommitAnalyzer()
                    fallback_message = commit_analyzer.generate_conventional_commit(context)
                    print(fallback_message)
                except Exception as fallback_error:
                    print(f"{RED}Fallback failed: {fallback_error}{ENDC}", file=sys.stderr)
                    sys.exit(1)
            else:
                # No fallback for commit range mode
                print(
                    f"{RED}AI generation failed for commit range mode. Local analysis not available for ranges.{ENDC}",
                    file=sys.stderr,
                )
                sys.exit(1)

    except ValueError as e:
        print(f"{RED}Error: {e}{ENDC}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"{RED}Unexpected error: {e}{ENDC}", file=sys.stderr)
        sys.exit(1)


def main(args=None):
    """Main entry point for AIPR"""
    parsed_args = parse_args(args)

    # Route to appropriate command handler
    if parsed_args.command == "commit":
        handle_commit_command(parsed_args)
    elif parsed_args.command == "pr":
        handle_pr_command(parsed_args)
    else:
        # Default to pr command
        handle_pr_command(parsed_args)

    sys.exit(0)


if __name__ == "__main__":
    main()
