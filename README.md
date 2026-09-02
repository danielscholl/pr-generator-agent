# AIPR - Agentic Pull Request Description Generator

[![CI](https://github.com/danielscholl/pr-generator-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/danielscholl/pr-generator-agent/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/danielscholl/pr-generator-agent)](https://github.com/danielscholl/pr-generator-agent/releases)
[![Python](https://img.shields.io/badge/python-3.11%20|%203.12-blue)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Automatically analyze git diffs and vulnerabilities to generate comprehensive, well-structured pull request descriptions. By intelligently detecting changes, performing security scans, and leveraging state-of-the-art AI models, AIPR helps teams save time while maintaining high-quality, consistent pull request descriptions.

## AI-Driven Development

[![AI-Driven](https://img.shields.io/badge/AI--Driven-Development-blueviolet)](https://github.com/danielscholl/pr-generator-agent/blob/main/docs/adr/index.md)
[![Claude Ready](https://img.shields.io/badge/Claude%20Code-Ready-8A2BE2?logo=anthropic)](https://github.com/danielscholl/pr-generator-agent/blob/main/CLAUDE.md)

This project follows an AI-driven development workflow:
- 🤖 **Built with AI** - Developed using Claude Code with comprehensive AI guidance
- 📋 **AI Task Assignment** - Structured workflow for AI agents documented in [CONTRIBUTING.md](CONTRIBUTING.md)
- 📚 **AI-Friendly Documentation** - Comprehensive guides for AI agents in [CLAUDE.md](CLAUDE.md) and [Architecture Decision Records](docs/adr/index.md)
- 🏗️ **Architecture-First Design** - ADRs define behavior and guide implementation patterns


```bash
# Install with pipx (recommended)
pipx install pr-generator-agent

# Or with pip
pip install pr-generator-agent

# Set the environment variable for the API key
export ANTHROPIC_API_KEY="your-api-key"

# Generate a PR description
aipr

# Generate a conventional commit message
aipr commit

# Generate PR description from commit range
aipr pr --from abc123 --to def456

# Generate commit message from commit range
aipr commit --from v1.0.0

# Custom usage - Analyze changes against main branch
# Include: Vulnerability scanning
# Use: Azure OpenAI GPT-5 Mini model
# Prompt: meta template
# Output: Verbose
aipr pr -t main --vulns -p meta -m azure/gpt-5-mini -v

# Inline with merge request creation
gh pr create -b "$(aipr pr -s)" -t "feat: New Feature"

# Inline with commit creation
git commit -m "$(aipr commit)"
```

## Key Features

- 🔍 **Smart Detection**: Automatically analyzes working tree changes, compares branches, or analyzes commit ranges
- 📝 **Conventional Commits**: Generate conventional commit messages from staged changes or commit ranges
- 📊 **Commit Range Analysis**: Generate descriptions and commit messages from any commit range (SHA to SHA)
- 🛡️ **Security First**: Optional vulnerability scanning between branches using Trivy
- 🤖 **AI-Powered**: Multiple AI providers (Azure OpenAI, OpenAI, Anthropic, Gemini) for optimal results
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

### Commit Message Generation

```bash
$ git add src/auth.py tests/test_auth.py
$ aipr commit
feat(auth): add OAuth2 authentication support

$ git add requirements.txt
$ aipr commit
build(deps): update dependencies to latest versions

$ git add README.md docs/guide.md
$ aipr commit
docs: update installation and usage documentation
```

## Requirements

- Python 3.11 or higher (3.11, 3.12 officially supported)
- Git
- LLM API Key (Anthropic, OpenAI, or Azure OpenAI)
- [Trivy](https://aquasecurity.github.io/trivy/latest/getting-started/installation/) (used for `--vulns` scanning)

## Environment Variables

The tool automatically detects which provider to use based on available environment variables, with the following priority order:

1. **Anthropic (Default - Highest Priority)**
   - `ANTHROPIC_API_KEY`: Anthropic API key

2. **Azure OpenAI**
   - `AZURE_API_KEY`: Azure OpenAI API key
   - `AZURE_OPENAI_ENDPOINT`: Azure endpoint URL
   - `AZURE_API_VERSION`: API version (default: "2024-02-15-preview")

3. **OpenAI**
   - `OPENAI_API_KEY`: OpenAI API key

4. **Google Gemini**
   - `GEMINI_API_KEY`: Google Gemini API key

5. **xAI**
   - `XAI_API_KEY`: xAI API key for Grok models

## Usage

AIPR provides two main commands:

### PR Command (Pull Request Descriptions)
```bash
aipr pr [options]  # or just 'aipr' for backward compatibility
```

**Options:**
- `-t, --target`: Compare changes with specific branch (default: auto-detects main/master)
- `-p, --prompt`: Select prompt template (e.g., 'meta')
- `--vulns`: Include vulnerability scanning
- `--working-tree`: Use working tree changes
- `--context`: Additional context for the PR description
- `--from`: Starting commit for range analysis (SHA, branch, tag, etc.)
- `--to`: Ending commit for range analysis (defaults to HEAD, requires --from)
- `--max-input-tokens`: Refuse to call the API above this estimated input size (default 100000, 0 disables)

**Global Options:**
- `-v, --verbose`: Show API interaction details
- `-d, --debug`: Preview prompts without API calls
- `-s, --silent`: Output only the description
- `-m, --model`: Specify AI model to use
- `-V, --version`: Show the installed aipr version and exit

The tool intelligently detects changes by:
1. Using staged/unstaged changes if present
2. Comparing against target branch if working tree is clean

### Commit Command (Conventional Commit Messages)
```bash
aipr commit [options]
```

**Options:**
- `--conventional`: Generate conventional commit message (default)
- `--format`: Message format (currently only 'conventional')
- `--context`: Additional context for the commit message
- `--from`: Starting commit for range analysis (SHA, branch, tag, etc.)
- `--to`: Ending commit for range analysis (defaults to HEAD, requires --from)
- `--max-input-tokens`: Refuse to call the API above this estimated input size (default 100000, 0 disables)

**Examples:**
```bash
# Basic commit message generation from staged changes
git add .
aipr commit

# Generate commit message from commit range
aipr commit --from abc123 --to def456

# Generate commit message from specific commit to HEAD
aipr commit --from abc123

# With additional context
aipr commit --context "upstream sync"

# Use in automation
git commit -m "$(aipr commit)"
```

## Cost Safeguards

Before any API call, aipr shapes the diff and checks its size:

- Lock files, minified bundles, images, notebooks, and build or vendor directories are replaced by a one-line marker. The model still sees that the file changed, not its contents.
- A single file longer than 1500 diff lines is cut with a marker so one generated file cannot crowd out the rest.
- The estimated input size is printed to stderr, and anything over the ceiling is refused with a clear message and a non-zero exit before a request is sent. Set the ceiling with `--max-input-tokens` or `AIPR_MAX_INPUT_TOKENS`; `0` disables it.
- On the commit command, a subject line the model overruns past 72 characters triggers one rewrite request before the fallback wrap into the body. That retry resends the diff, so the worst case is twice the admitted budget.

## Supported AI Models

Choose from multiple AI providers:

| Provider | Model | Notes |
|----------|--------|-------|
| **Anthropic** | `claude-opus-5` | Claude Opus 5 (default) |
| | `claude-sonnet-5` | Claude Sonnet 5 (lower cost) |
| | `claude-fable-5-1` | Claude Fable 5.1 (most capable, highest cost) |
| | `claude-haiku-4-5` | Claude Haiku 4.5 (fastest, most economical) |
| | `claude-opus-4-8` | Claude Opus 4.8 (previous generation) |
| | `claude-sonnet-4-6` | Claude Sonnet 4.6 (previous generation) |
| | `claude`, `opus`, `claude-opus` | aliases for `claude-opus-5` |
| | `sonnet` | alias for `claude-sonnet-5` |
| | `fable` | alias for `claude-fable-5-1` |
| | `haiku` | alias for `claude-haiku-4-5` |
| **Azure OpenAI** | `azure/gpt-5-nano` | default Azure model |
| | `azure/gpt-4.1-nano` | Lightweight model |
| | `azure/gpt-5-chat` | Conversational model |
| | `azure/gpt-5-mini` | Mid-tier model |
| | `azure` | alias for `azure/gpt-5-nano` |
| **OpenAI** | `gpt-5` | Latest GPT-5 model (default) |
| | `gpt-5-mini` | Mid-tier GPT-5 model |
| | `gpt-5-nano` | Lightweight GPT-5 model |
| | `openai` | alias for `gpt-5` |
| **Google Gemini** | `gemini-2.5-flash` | Best price-performance (default) |
| | `gemini-2.5-pro` | Flagship thinking model with 1M token context |
| | `gemini-2.5-flash-lite` | Most cost-effective model |
| | `gemini` | alias for `gemini-2.5-flash` |
| **xAI** | `grok-code-fast-1` | Specialized for coding tasks |
| | `grok`, `xai` | aliases for `grok-code-fast-1` |

Current-generation Anthropic models run with adaptive thinking at medium effort. Opus 5 and Fable 5.1 requests opt into Anthropic's server-side refusal fallback, so a diff the safety classifiers decline is retried on a fallback model instead of failing the commit.

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
