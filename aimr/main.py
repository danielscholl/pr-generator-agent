import argparse
import git
from openai import AzureOpenAI, OpenAI
import anthropic
import os
import sys
import tiktoken
import subprocess
import json
from typing import Tuple, Dict, Any

# ANSI color codes
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"

# System and user prompts for AI models
SYSTEM_PROMPT = """You are a helpful assistant for generating Merge Requests.
Your task is to analyze Git changes and vulnerability comparison data to create clear, well-structured merge request descriptions.
Please include:
- A concise summary of the changes
- Key modifications and their purpose
- Any notable technical details
- Security impact analysis (when vulnerability data is provided)

Important Guidelines:
1. Focus only on the specific changes shown in the diff and vulnerability comparison
2. Each point must be directly tied to actual code changes or security findings
3. When analyzing vulnerabilities:
   - Highlight critical security changes
   - Explain the impact of new vulnerabilities
   - Acknowledge fixed vulnerabilities
4. DO NOT include any of the following:
   - Generic concluding statements (e.g., "This improves the overall system")
   - Broad claims about improvements (e.g., "This enhances development processes")
   - Value judgments about the changes (e.g., "This is a significant improvement")
   - Future benefits or implications

Your response should end with the last specific change or security finding discussed.
If you find yourself wanting to write a concluding statement, stop writing instead."""

def generate_user_prompt(diff, vuln_data=None):
    prompt = (
        "Please evaluate the following Git changes and provide a well-structured Merge Request "
        "in markdown format.\n\n"
        "Git Diff:\n"
        f"{diff}"
    )
    
    if vuln_data:
        prompt += "\n\nVulnerability Analysis:\n" + vuln_data
    
    return prompt

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

def run_trivy_scan(path: str) -> Dict[str, Any]:
    """Run trivy filesystem scan and return the results as a dictionary."""
    try:
        # Determine project type and scanning approach
        is_java = os.path.exists(os.path.join(path, 'pom.xml'))
        is_node = os.path.exists(os.path.join(path, 'package.json'))
        is_python = os.path.exists(os.path.join(path, 'requirements.txt')) or os.path.exists(os.path.join(path, 'setup.py'))
        
        trivy_args = [
            'trivy',
            'fs',
            '--format', 'json',
            '--scanners', 'vuln,secret,config'
        ]

        # Add dependency scanning for supported project types
        if is_java:
            try:
                print(f"{BLUE}Detected Java project, resolving Maven dependencies...{ENDC}", file=sys.stderr)
                subprocess.run(
                    ['mvn', 'dependency:resolve', '-DskipTests'],
                    cwd=path,
                    check=True,
                    capture_output=True
                )
                trivy_args.append('--dependency-tree')
            except subprocess.CalledProcessError as e:
                print(f"{YELLOW}Warning: Maven dependency resolution failed: {e}{ENDC}", file=sys.stderr)
        elif is_node or is_python:
            print(f"{BLUE}Detected {'Node.js' if is_node else 'Python'} project, including dependency scanning...{ENDC}", file=sys.stderr)
            trivy_args.append('--dependency-tree')
        else:
            print(f"{BLUE}No specific package manager detected, performing filesystem scan...{ENDC}", file=sys.stderr)

        # Add the path as the last argument
        trivy_args.append(path)

        # Run trivy scan
        result = subprocess.run(
            trivy_args,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error running trivy scan: {e}{ENDC}", file=sys.stderr)
        if e.stderr:
            print(f"{RED}Trivy error details: {e.stderr}{ENDC}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"{RED}Error parsing trivy output: {e}{ENDC}", file=sys.stderr)
        return {}

def compare_vulnerabilities(current_scan: Dict[str, Any], target_scan: Dict[str, Any]) -> Tuple[str, str]:
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
        for result in scan_data.get('Results', []):
            target = result.get('Target', '')
            type = result.get('Type', '')
            for vuln in result.get('Vulnerabilities', []):
                vulns.append({
                    'id': vuln.get('VulnerabilityID'),
                    'pkg': vuln.get('PkgName'),
                    'version': vuln.get('InstalledVersion'),
                    'severity': vuln.get('Severity'),
                    'description': vuln.get('Description'),
                    'fix_version': vuln.get('FixedVersion'),
                    'target': target,
                    'type': type,
                    'title': vuln.get('Title'),
                    'references': vuln.get('References', [])
                })
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
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'UNKNOWN': 4}
    
    def group_by_severity(vulns_keys: set, vuln_list: list) -> Dict[str, list]:
        grouped = {}
        for vuln in vuln_list:
            key = create_vuln_key(vuln)
            if key in vulns_keys:
                sev = vuln['severity'] or 'UNKNOWN'
                if sev not in grouped:
                    grouped[sev] = []
                grouped[sev].append(vuln)
        return {k: grouped[k] for k in sorted(grouped.keys(), key=lambda x: severity_order.get(x, 999))}
    
    # Prepare detailed analysis data
    if new_vulns:
        analysis_data.append("\nNew Vulnerabilities Details:")
        grouped_new = group_by_severity(new_vulns, current_vulns)
        for severity, vulns in grouped_new.items():
            analysis_data.append(f"\n{severity} Severity:")
            for vuln in sorted(vulns, key=lambda x: x['id']):
                analysis_data.append(f"\n- {vuln['id']} ({vuln['type']}):")
                analysis_data.append(f"  - Package: {vuln['pkg']} {vuln['version']}")
                analysis_data.append(f"  - In: {vuln['target']}")
                analysis_data.append(f"  - Title: {vuln['title']}")
                analysis_data.append(f"  - Description: {vuln['description']}")
                if vuln['fix_version']:
                    analysis_data.append(f"  - Fix available in version: {vuln['fix_version']}")
                if vuln['references']:
                    analysis_data.append("  - References:")
                    for ref in vuln['references'][:3]:  # Limit to first 3 references
                        analysis_data.append(f"    * {ref}")
    
    if fixed_vulns:
        analysis_data.append("\nFixed Vulnerabilities Details:")
        grouped_fixed = group_by_severity(fixed_vulns, target_vulns)
        for severity, vulns in grouped_fixed.items():
            analysis_data.append(f"\n{severity} Severity:")
            for vuln in sorted(vulns, key=lambda x: x['id']):
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
            for vuln in sorted(vulns, key=lambda x: x['id']):
                report.append(f"- {vuln['id']} in {vuln['pkg']} {vuln['version']} ({vuln['target']})")
    
    if fixed_vulns:
        report.append("\n### Fixed Vulnerabilities\n")
        grouped_fixed = group_by_severity(fixed_vulns, target_vulns)
        for severity, vulns in grouped_fixed.items():
            report.append(f"\n#### {severity}\n")
            for vuln in sorted(vulns, key=lambda x: x['id']):
                report.append(f"- {vuln['id']} in {vuln['pkg']} {vuln['version']} ({vuln['target']})")
    
    if not new_vulns and not fixed_vulns:
        report.append("\nNo vulnerability changes detected between branches.")
        analysis_data.append("\nNo security changes to analyze.")
    
    return "\n".join(report), "\n".join(analysis_data)

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

  # Include vulnerability comparison
  aimr -t main --vulns

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
    parser.add_argument(
        "--vulns",
        action="store_true",
        help="Include vulnerability comparison between branches using trivy"
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
                args.verbose and not args.silent
            )
        else:  # anthropic
            merge_request = generate_with_anthropic(
                user_prompt,
                SYSTEM_PROMPT,
                model
            )

        # Add vulnerability comparison if requested
        if args.vulns and args.target:
            if not args.silent:
                print("\nRunning vulnerability scans...")
            
            # Create temporary directory for target branch scan
            import tempfile
            import shutil
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy current repository to temp directory
                shutil.copytree(args.path, os.path.join(temp_dir, 'repo'), dirs_exist_ok=True)
                
                # Initialize repo and checkout target branch
                temp_repo = git.Repo(os.path.join(temp_dir, 'repo'))
                temp_repo.git.checkout(args.target)
                
                # Run vulnerability scans with proper dependency resolution
                if not args.silent:
                    print(f"\nScanning target branch ({args.target})...")
                target_scan = run_trivy_scan(os.path.join(temp_dir, 'repo'))
                
                if not args.silent:
                    print(f"\nScanning current branch ({current_branch})...")
                current_scan = run_trivy_scan(args.path)
                
                # Generate vulnerability comparison and analysis
                vuln_report, vuln_analysis = compare_vulnerabilities(current_scan, target_scan)
                
                # Update the user prompt with vulnerability analysis
                user_prompt = generate_user_prompt(diff, vuln_analysis)
                
                if not args.silent:
                    print("\nGenerating merge request with vulnerability analysis...")
                
                # Generate new merge request with vulnerability context
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
                        args.verbose and not args.silent
                    )
                else:  # anthropic
                    merge_request = generate_with_anthropic(
                        user_prompt,
                        SYSTEM_PROMPT,
                        model
                    )
                
                # Append the vulnerability report
                merge_request = f"{merge_request}\n\n{vuln_report}"

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
