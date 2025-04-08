# AIPR - Agentic Pull Request Description Generator

Automatically analyze git diffs and vulnerabilities to generate comprehensive, well-structured pull request descriptions. By intelligently detecting changes, performing security scans, and leveraging state-of-the-art AI models, AIPR helps teams save time while maintaining high-quality, consistent pull request descriptions.


```bash
# Install with pipx (recommended)
pipx install pr-generator-agent

# Or with pip
pip install pr-generator-agent

# Set the environment variable for the API key
export ANTHROPIC_API_KEY="your-api-key"

# Generate a PR description
aipr

# Custom usage - Analyze changes against main branch
# Include: Vulnerability scanning
# Use: Azure OpenAI o1-mini model
# Prompt: meta template
# Ouptut: Verbose
aipr -t main --vulns -p meta -m azure/o1-mini -v

# Inline with merge request creation
gh pr create -b "$(aipr -s)" -t "feat: New Feature"
```

## Key Features

- 🔍 **Smart Detection**: Automatically analyzes working tree changes or compares branches
- 🛡️ **Security First**: Optional vulnerability scanning between branches using Trivy
- 🤖 **AI-Powered**: Multiple AI providers (Azure OpenAI, OpenAI, Anthropic) for optimal results
- 🔄 **CI/CD Ready**: Seamless integration with GitLab and GitHub workflows

## Example Output

```
Change Summary:

1. **Added User Authentication**
   - Implemented JWT middleware
   - Added login/register endpoints
   - Updated bcrypt to v5.1.1

2. **Security Updates**
   - Fixed 2 medium severity vulnerabilities
   - Updated deprecated crypto functions

Security Analysis:
✓ No new vulnerabilities introduced
```

## Requirements

- Python 3.10 or higher (3.10, 3.11 officially supported)
- Git
- LLM API Key (Anthropic, OpenAI, or Azure OpenAI)
- [Trivy](https://aquasecurity.github.io/trivy/latest/getting-started/installation/) (used for `--vulns` scanning)

## Environment Variables

#### Anthropic (Default)
- `ANTHROPIC_API_KEY`: Anthropic API key

#### Azure OpenAI
- `AZURE_API_KEY`: Azure OpenAI API key
- `AZURE_API_BASE`: Azure endpoint URL
- `AZURE_API_VERSION`: API version (default: "2024-02-15-preview")

#### OpenAI
- `OPENAI_API_KEY`: OpenAI API key

#### Google Gemini
- `GEMINI_API_KEY`: Google Gemini API key

## Usage

### Command Options
- `-t, --target`: Compare changes with specific branch (default: auto-detects main/master)
- `-p, --prompt`: Select prompt template (e.g., 'meta')
- `-v, --verbose`: Show API interaction details
- `-d, --debug`: Preview prompts without API calls
- `-s, --silent`: Output only the description
- `--vulns`: Include vulnerability scanning
- `-m, --model`: Specify AI model to use

The tool intelligently detects changes by:
1. Using staged/unstaged changes if present
2. Comparing against target branch if working tree is clean

## Supported AI Models

Choose from multiple AI providers:

| Provider | Model | Notes |
|----------|--------|-------|
| Anthropic | `claude-3-sonnet` | default |
| | `claude-3.5-sonnet` | latest |
| | `claude-3.5-haiku` | latest |
| | `claude-3-opus` | latest |
| | `claude-3-haiku` | |
| | `claude` | alias for `claude-3-sonnet` |
| Azure OpenAI | `azure/o1-mini` | |
| | `azure/gpt-4o-mini` | |
| | `azure/gpt-4o` | |
| | `azure` | alias for `azure/gpt-4o-mini` |
| OpenAI | `gpt-4o` | |
| | `gpt-4-turbo` | |
| | `gpt-3.5-turbo` | |
| | `openai` | alias for `gpt-4o` |
| Google Gemini | `gemini-1.5-pro` | default for Gemini |
| | `gemini-1.5-flash` | |
| | `gemini-2.5-pro-experimental` | maps to `gemini-2.5-pro-exp-03-25` |
| | `gemini` | alias for `gemini-2.5-pro-experimental` |

## Custom Prompts

AIPR supports custom prompt templates that allow you to tailor merge request descriptions to your team's specific needs. Custom prompts enable you to:
- Define consistent formatting across your team
- Include organization-specific requirements
- Add custom sections and validation rules
- Provide examples that match your team's standards

For detailed information on creating and using custom prompts, see our [Custom Prompts Tutorial](docs/custom_prompts.md).

## Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details on:
- Setting up your development environment
- Our development workflow
- Code style guidelines
- Pull request process
- Running tests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.