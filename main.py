import git
import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(
        prog="aimr",
        description="Generates a Merge Request Description from Git diffs using AI models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Auto-detect changes and generate description
  aimr 

  # Compare with specific target branch
  aimr -t develop

  # Use specific AI model
  aimr -m claude-3-sonnet

  # Include vulnerability scanning
  aimr -t develop --vulns

  # Integration with GitHub
  gh pr create -b "$(aimr -s)" -t "your title"
""")
    parser.add_argument(
        "path",
        nargs='?',
        default='.',
        help="The directory path of the Git repository (defaults to current directory)."
    )
    parser.add_argument(
        "--target", "-t",
        default=None,
        help="The target branch to merge into. If not specified:\n"
             "- Shows working tree changes if there are staged/unstaged changes\n"
             "- Compares against 'main' if the current branch is clean\n"
             "Use '-' to force showing working tree changes"
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="""AI model to use. Available options:

Azure OpenAI (Default):
  - azure/o1-mini (default)
  - azure/gpt-4o
  - azure/gpt-4o-mini
  - azure/gpt-4 (alias for gpt-4o)

OpenAI:
  - gpt-4
  - gpt-4-turbo
  - gpt-3.5-turbo

Anthropic:
  - claude-3.5-sonnet (latest)
  - claude-3.5-haiku (latest)
  - claude-3-opus (latest)
  - claude-3-sonnet
  - claude-3-haiku
  - claude-3 (alias for claude-3-opus)"""
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output (shows token counts, API details, etc.)"
    )
    parser.add_argument(
        "--silent", "-s",
        action="store_true",
        help="Silent mode - only output the generated description (useful for CI/CD integration)"
    )
    parser.add_argument(
        "--vulns",
        action="store_true",
        help="Include vulnerability comparison using trivy. Works with both working tree and branch comparisons."
    )

    try:
        repo = git.Repo(args.path)
    except git.exc.InvalidGitRepositoryError:
        print(f"Error: Directory '{args.path}' is not a valid Git repository.", file=sys.stderr)
        sys.exit(1)

    try:
        current_branch = repo.active_branch.name
    except TypeError:
        current_branch = repo.head.commit.hexsha

    # Check if we have any working tree changes
    has_changes = repo.is_dirty(untracked_files=True)
    
    # Determine if we should do branch comparison or working tree changes
    if args.target == "-":
        # Explicit request for working tree changes
        diff = repo.git.diff()
        target_branch = None
    elif args.target:
        # Explicit target branch specified
        target_branch = args.target
        local_branches = [h.name for h in repo.heads]
        
        # Try common default branch names if the specified branch doesn't exist
        if target_branch not in local_branches:
            # Prioritize 'main' as the first default branch
            if "main" in local_branches:
                if not args.silent:
                    print(f"{YELLOW}Warning: Target branch '{target_branch}' not found, using 'main' instead.{ENDC}", file=sys.stderr)
                target_branch = "main"
            else:
                # Fall back to other common branch names
                default_branches = ["master", "develop"]
                for branch in default_branches:
                    if branch in local_branches:
                        if not args.silent:
                            print(f"{YELLOW}Warning: Target branch '{target_branch}' not found, using '{branch}' instead.{ENDC}", file=sys.stderr)
                        target_branch = branch
                        break
                else:
                    print(f"{RED}Error: Target branch '{target_branch}' does not exist in the repository.{ENDC}", file=sys.stderr)
                    sys.exit(1)
        
        diff = repo.git.diff(f"{target_branch}...{current_branch}")
    else:
        # No target specified, auto-detect what to do
        if has_changes:
            # Show working tree changes if we have any
            if not args.silent:
                print(f"{BLUE}Detected working tree changes, showing diff of current changes...{ENDC}", file=sys.stderr)
            diff = repo.git.diff()
            target_branch = None
        else:
            # No working tree changes, try to compare against default branch
            local_branches = [h.name for h in repo.heads]
            
            # First try 'main' as the default branch
            if "main" in local_branches and "main" != current_branch:
                if not args.silent:
                    print(f"{BLUE}No working tree changes, comparing against 'main'...{ENDC}", file=sys.stderr)
                target_branch = "main"
                diff = repo.git.diff(f"main...{current_branch}")
            else:
                # Fall back to other common branch names
                default_branches = ["master", "develop"]
                for branch in default_branches:
                    if branch in local_branches and branch != current_branch:
                        if not args.silent:
                            print(f"{BLUE}No working tree changes, comparing against '{branch}'...{ENDC}", file=sys.stderr)
                        target_branch = branch
                        diff = repo.git.diff(f"{branch}...{current_branch}")
                        break
                else:
                    # No suitable default branch found
                    print(f"{YELLOW}No default target branch found and no working tree changes.{ENDC}", file=sys.stderr)
                    sys.exit(0)

    if not diff.strip():
        print("No changes found in the Git repository.", file=sys.stderr)
        sys.exit(0)

    # Only show these in non-silent mode
    if not args.silent:
        print_header("Repository Information")
        print(f"Repository: {os.path.abspath(args.path)}")
        print(f"Current branch: {current_branch}")
        
        # Show comparison information
        if target_branch:
            print(f"Comparing: {current_branch} → {target_branch}")
        elif has_changes:
            print(f"Comparing: Working tree changes in {current_branch}")
        
        # Add a blank line for better readability
        print()

        # Add token count information
        user_prompt = generate_user_prompt(diff)
        print_header("Token Information")
        print_token_info(user_prompt, SYSTEM_PROMPT, args.verbose)

        print_header(f"\nProcessing Merge Request Description")
        print(f"Using {provider} ({model})...")
        
        if args.vulns:
            if target_branch:
                print(f"\nVulnerability comparison: {current_branch} → {target_branch}")
            else:
                print(f"\nVulnerability scanning: {current_branch}")
    else:
        user_prompt = generate_user_prompt(diff) 