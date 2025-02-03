import argparse
import git
import openai
import anthropic
import os
import sys
from typing import Tuple

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
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.2,
    )
    return response['choices'][0]['message']['content']

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
        return "openai", "gpt-4o"

    model_lower = model_arg.lower()

    # Simple model mapping
    model_mapping = {
        'claude': ("anthropic", "claude-3-5-sonnet-20241022"),
        'gpt-4o': ("openai", "gpt-4o"),
        'gpt4o': ("openai", "gpt-4o"),
        'gpt-4o-mini': ("openai", "gpt-4o-mini"),
        'gpt4o-mini': ("openai", "gpt-4o-mini")
    }

    if model_lower in model_mapping:
        return model_mapping[model_lower]

    # Default to gpt-4o if model not recognized
    print(f"Warning: Unrecognized model '{model_arg}', defaulting to gpt-4o")
    return "openai", "gpt-4o"

def main():
    parser = argparse.ArgumentParser(
        description="Generates a Merge Request Description from Git diffs using AI models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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
        help="AI model to use (e.g., gpt-4, claude-3-sonnet, claude-2). Defaults to gpt-4"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    args = parser.parse_args()

    # Detect provider and normalize model name
    provider, model = detect_provider_and_model(args.model)

    try:
        repo = git.Repo(args.path)
    except git.exc.InvalidGitRepositoryError:
        print(f"Error: Directory '{args.path}' is not a valid Git repository.")
        sys.exit(1)

    try:
        current_branch = repo.active_branch.name
    except TypeError:
        current_branch = repo.head.commit.hexsha

    if args.target:
        target_branch = args.target
        local_branches = [h.name for h in repo.heads]
        if target_branch not in local_branches:
            print(f"Error: Target branch '{target_branch}' does not exist in the repository.")
            sys.exit(1)
        diff = repo.git.diff(f"{target_branch}...{current_branch}")
    else:
        diff = repo.git.diff()

    if not diff.strip():
        print("No changes found in the Git repository.")
        sys.exit(0)

    print(f"Repository: {os.path.abspath(args.path)}")
    print(f"Current branch: {current_branch}")
    if args.target:
        print(f"Target branch: {args.target}")
    print(f"\nProcessing Merge Request Description using {provider} ({model})...\n")

    # Check for appropriate API key
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OpenAI API key not set. Please set the OPENAI_API_KEY environment variable.")
            sys.exit(1)
        openai.api_key = api_key
    else:  # anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: Anthropic API key not set. Please set the ANTHROPIC_API_KEY environment variable.")
            sys.exit(1)

    try:
        if provider == "openai":
            merge_request = generate_with_openai(
                generate_user_prompt(diff),
                SYSTEM_PROMPT,
                model
            )
        else:
            merge_request = generate_with_anthropic(
                generate_user_prompt(diff),
                SYSTEM_PROMPT,
                model
            )

        if args.verbose:
            print("\n### Merge Request ###\n")
        print(merge_request)
    except (openai.OpenAIError, anthropic.APIError) as e:
        print(f"Error: {provider.title()} API - {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
