import argparse
import git
from openai import AzureOpenAI, OpenAI
import anthropic
import os
import sys
import tiktoken
from typing import Tuple

# ANSI color codes
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"

# System and user prompts for AI models
SYSTEM_PROMPT = """You are a helpful assistant for generating Merge Requests.
Your task is to analyze Git changes and create clear, well-structured merge request descriptions.
Please include:
- A concise summary of the changes
- Key modifications and their purpose
- Any notable technical details

Important Guidelines:
1. Focus only on the specific changes shown in the diff
2. Each point must be directly tied to actual code changes
3. DO NOT include any of the following:
   - Generic concluding statements (e.g., "This improves the overall system")
   - Broad claims about improvements (e.g., "This enhances development processes")
   - Value judgments about the changes (e.g., "This is a significant improvement")
   - Future benefits or implications

Your response should end with the last specific change or technical detail discussed.
If you find yourself wanting to write a concluding statement, stop writing instead."""

def generate_user_prompt(diff):
    return (
        "Please evaluate the following Git changes and provide a well-structured Merge Request "
        "in markdown format.\n\n"
        "Git Diff:\n"
        f"{diff}"
    )

def generate_with_openai(prompt, system_prompt, model):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.2,
    )
    return response.choices[0].message.content

def generate_with_azure_openai(prompt, system_prompt, model, verbose=False):
    # Configure the Azure OpenAI client
    # Convert services.ai.azure.com to openai.azure.com
    azure_endpoint = os.getenv("AZURE_API_BASE").replace('services.ai.azure.com', 'openai.azure.com')

    client = AzureOpenAI(
        api_key=os.getenv("AZURE_API_KEY"),
        api_version=os.getenv("AZURE_API_VERSION", "2024-08-01-preview"),
        azure_endpoint=azure_endpoint
    )

    if verbose:
        print("\nDebug - Azure OpenAI Request:", file=sys.stderr)
        print(f"Debug - Deployment: {model}", file=sys.stderr)
        print(f"Debug - API Version: {os.getenv('AZURE_API_VERSION')}", file=sys.stderr)
        print(f"Debug - Endpoint: {azure_endpoint}\n", file=sys.stderr)

    try:
        # Combine system prompt and user prompt for Azure OpenAI
        combined_prompt = f"{system_prompt}\n\n{prompt}"

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": combined_prompt}
            ],
            max_completion_tokens=4000  # Use max_completion_tokens instead of max_tokens
        )

        if not response.choices:
            raise Exception("No response received from the model")

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise Exception("Empty response received from the model")

        if verbose:
            print("\nDebug - Response received successfully", file=sys.stderr)

        return content
    except Exception as e:
        if verbose:
            print(f"\nDebug - Azure OpenAI Response Error: {str(e)}", file=sys.stderr)
            print("Debug - Request details:", file=sys.stderr)
            print(f"System prompt length: {len(system_prompt)}", file=sys.stderr)
            print(f"User prompt length: {len(prompt)}", file=sys.stderr)
        raise

def generate_with_anthropic(prompt, system_prompt, model):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=model,
        max_tokens=1000,
        temperature=0.2,
        system=system_prompt,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return message.content[0].text

def detect_provider_and_model(model_arg: str | None) -> Tuple[str, str]:
    """
    Detect the provider and normalize the model name based on the input.
    Returns a tuple of (provider, model_name)
    """
    if not model_arg:
        return "azure", "o1-mini"  # Default to Azure OpenAI's o1-mini deployment

    model_lower = model_arg.lower()

    # Azure OpenAI models
    if model_lower.startswith('azure/'):
        model_name = model_lower.split('/', 1)[1]
        # Map azure model names to deployment names
        azure_models = {
            'o1-mini': 'o1-mini',          # Direct mapping to o1-mini deployment
            'gpt-4o': 'gpt-4o',            # Direct mapping to gpt-4o deployment
            'gpt-4o-mini': 'gpt-4o-mini',  # Direct mapping to gpt-4o-mini deployment
            'gpt-4': 'gpt-4o'              # Alias for gpt-4o
        }
        return "azure", azure_models.get(model_name, model_name)

    # OpenAI models
    if model_lower.startswith(('gpt-', 'gpt4')):
        # Handle various GPT model formats
        if model_lower in ['gpt4', 'gpt-4']:
            return "openai", "gpt-4"
        elif model_lower in ['gpt4-turbo', 'gpt-4-turbo']:
            return "openai", "gpt-4-turbo-preview"
        elif model_lower in ['gpt3', 'gpt-3']:
            return "openai", "gpt-3.5-turbo"
        return "openai", model_arg

    # Anthropic models
    if model_lower.startswith('claude'):
        # Map common Claude model names
        claude_models = {
            'claude-3.5-sonnet': 'claude-3-5-sonnet-20241022',
            'claude-3.5-haiku': 'claude-3-5-haiku-20241022',
            'claude-3-opus': 'claude-3-opus-20240229',
            'claude-3-sonnet': 'claude-3-sonnet-20240229',
            'claude-3-haiku': 'claude-3-haiku-20240307',
            'claude-3': 'claude-3-opus-20240229',  # Default to Opus for claude-3
        }
        return "anthropic", claude_models.get(model_lower, model_arg)

    # Default to Azure OpenAI's o1-mini if model format is unrecognized
    print(f"Warning: Unrecognized model '{model_arg}', defaulting to azure/o1-mini")
    return "azure", "o1-mini"

def count_tokens(text: str, model: str) -> int:
    """Count the number of tokens in a text string."""
    try:
        if model.startswith(('gpt-3', 'gpt-4')):
            encoding = tiktoken.encoding_for_model(model)
        else:
            # Default to cl100k_base for other models (including Azure and Claude)
            encoding = tiktoken.get_encoding('cl100k_base')
        return len(encoding.encode(text))
    except Exception:
        # If we can't get a token count, return an estimate
        return len(text) // 4  # Rough estimate of tokens

def print_token_info(prompt: str, system_prompt: str, verbose: bool = False):
    """Print token count information."""
    total_prompt = f"{system_prompt}\n\n{prompt}"
    token_count = count_tokens(total_prompt, "gpt-4")  # Use gpt-4 encoding as default
    if verbose:
        print(f"System prompt tokens: {count_tokens(system_prompt, 'gpt-4')}")
        print(f"User prompt tokens: {count_tokens(prompt, 'gpt-4')}")
    print(f"Total tokens: {token_count}")

def print_separator(char="─", color=GREEN):
    """Print a separator line with the given character and color."""
    terminal_width = os.get_terminal_size().columns
    print(f"{color}{char * terminal_width}{ENDC}")

def print_header(text, color=BLUE):
    """Print a header with the given color."""
    print(f"\n{color}{BOLD}{text}{ENDC}")

def main():
    parser = argparse.ArgumentParser(
        prog="aimr",
        description="Generates a Merge Request Description from Git diffs using AI models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Generate MR description for current branch
  aimr

  # Use Azure OpenAI (default)
  aimr -m azure/o1-mini

  # Compare with target branch using specific model
  aimr -t main -m claude-3-sonnet

  # Create GitLab MR with description
  glab mr create -d "$(aimr -s -t master)" -t "your title"
  glab mr create -d "$(aimr -s -t master)" --fill  # Use commit info for title

  # Create GitHub PR with description
  gh pr create -b "$(aimr -s -t main)" -t "your title"
  gh pr create -b "$(aimr -s -t main)" --fill  # Use commit info for title

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
        help="The target branch to merge into (defaults to showing working tree changes)."
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="""AI model to use. Available options:
Azure OpenAI:
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
  - claude-3 (alias for claude-3-opus)
Defaults to azure/o1-mini"""
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--silent", "-s",
        action="store_true",
        help="Silent mode - only output the model response (useful with glab mr create -d)"
    )
    args = parser.parse_args()

    # Detect provider and normalize model name
    provider, model = detect_provider_and_model(args.model)

    try:
        repo = git.Repo(args.path)
    except git.exc.InvalidGitRepositoryError:
        print(f"Error: Directory '{args.path}' is not a valid Git repository.", file=sys.stderr)
        sys.exit(1)

    try:
        current_branch = repo.active_branch.name
    except TypeError:
        current_branch = repo.head.commit.hexsha

    if args.target:
        target_branch = args.target
        local_branches = [h.name for h in repo.heads]
        if target_branch not in local_branches:
            print(f"Error: Target branch '{target_branch}' does not exist in the repository.", file=sys.stderr)
            sys.exit(1)
        diff = repo.git.diff(f"{target_branch}...{current_branch}")
    else:
        diff = repo.git.diff()

    if not diff.strip():
        print("No changes found in the Git repository.", file=sys.stderr)
        sys.exit(0)

    # Only show these in non-silent mode
    if not args.silent:
        print_header("Repository Information")
        print(f"Repository: {os.path.abspath(args.path)}")
        print(f"Current branch: {current_branch}")
        if args.target:
            print(f"Target branch: {args.target}")

        # Add token count information
        user_prompt = generate_user_prompt(diff)
        print_header("\nToken Information")
        print_token_info(user_prompt, SYSTEM_PROMPT, args.verbose)

        print_header(f"\nProcessing Merge Request Description")
        print(f"Using {provider} ({model})...")
    else:
        user_prompt = generate_user_prompt(diff)

    try:
        if provider == "openai":
            merge_request = generate_with_openai(
                user_prompt,
                SYSTEM_PROMPT,
                model
            )
        elif provider == "azure":
            merge_request = generate_with_azure_openai(
                user_prompt,
                SYSTEM_PROMPT,
                model,
                args.verbose and not args.silent  # Only show verbose output if not in silent mode
            )
        else:  # anthropic
            merge_request = generate_with_anthropic(
                user_prompt,
                SYSTEM_PROMPT,
                model
            )

        if not args.silent:
            # Print separator before merge request
            print_separator()
            if args.verbose:
                print(f"\n{BOLD}### Merge Request ###\n{ENDC}")

        # Always print the merge request
        print(merge_request)

        if not args.silent:
            # Print separator after merge request
            print_separator()

            # Print response token count
            print_header("\nResponse Information")
            print(f"Response tokens: {count_tokens(merge_request, 'gpt-4')}")

    except Exception as e:
        print(f"{RED}Error: {provider.title()} API - {e}{ENDC}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
