# AIMR - AI-powered Merge Request Description Generator

Save time on writing Merge Request descriptions by automatically analyzing git diffs and vulnerabilities. AIMR generates comprehensive, well-structured descriptions that improve code review quality and maintain consistency across your team's merge requests.

📦 **Now available on PyPI!** ([See PyPI Listing](https://pypi.org/project/aimr/))

```bash
# Install with pipx (recommended)
pipx install aimr

# Or with pip
pip install aimr

# Or development version from GitHub
pipx install git+https://github.com/danielscholl/mr-generator-agent.git

# Configure API key (using Anthropic Claude as default)
export ANTHROPIC_API_KEY="your-api-key"

# Generate an MR description
aimr  # Uses Claude 3 Sonnet by default
```

## Why Use AIMR?

AIMR analyzes your code changes and automatically generates high-quality merge request descriptions. It detects changes intelligently, performs optional security scanning, and leverages state-of-the-art AI models to create descriptions that are thorough, consistent, and save your team valuable time during code reviews.

## Key Features

- 🔍 **Smart Detection**: Automatically analyzes working tree changes or compares branches
- 🛡️ **Security First**: Optional vulnerability scanning between branches using Trivy
- 🤖 **AI-Powered**: Multiple AI providers (Azure OpenAI, OpenAI, Anthropic) for optimal results
- 🔄 **CI/CD Ready**: Seamless integration with GitLab and GitHub workflows

## Example Usage

```bash
# Basic usage - analyze current changes
aimr

# Compare with specific branch and include security scan
aimr -t main --vulns
```

Example Output:
```
AIMR - AI-powered Merge Request Description Generator

Changes:

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

# Create merge requests directly
```bash
# GitHub
make mr

# Or manually with GitHub CLI
gh pr create -b "$(aimr -s)" -t "feat: Add authentication"

# Or with GitLab CLI
glab mr create -d "$(aimr -s)" -t "feat: Add authentication"
```

## Requirements

- Python 3.10 or higher (3.10, 3.11 officially supported)
- Git
- One of these API keys:
  - Anthropic (default)
  - Azure OpenAI
  - OpenAI
- Trivy (required only for `--vulns` scanning feature)
  ```bash
  # Install Trivy (macOS)
  brew install trivy
  
  # Other platforms: see https://aquasecurity.github.io/trivy/latest/getting-started/installation/
  ```

## Configuration

By default, AIMR uses Anthropic Claude. Configure your preferred provider with these environment variables:

```bash
# Anthropic (default provider)
export ANTHROPIC_API_KEY="your-api-key"

# Or Azure OpenAI
export AZURE_API_KEY="your-api-key"
export AZURE_API_BASE="your-api-base"
export AZURE_API_VERSION="2024-02-15-preview"

# Or OpenAI
export OPENAI_API_KEY="your-api-key"
```

## Usage

### Basic Commands
```bash
# Auto-detect and describe changes
aimr

# Compare with specific branch
aimr -t develop

# Include vulnerability scanning
aimr --vulns

# Show only working tree changes
aimr -t -

# See all options
aimr --help
```

### Smart Detection
The tool intelligently determines the comparison scope:
1. If you have staged/unstaged changes, it shows those changes
2. If your branch is clean, it compares against:
   - The specified target branch (with `-t`)
   - Or tries to find a default branch ('main', 'master', 'develop')

### CI/CD Integration
```bash
# GitHub PR creation
gh pr create -b "$(aimr -s --vulns)" -t "your title"

# GitLab MR creation
glab mr create -d "$(aimr -s)" --fill
```

## Supported AI Models

Choose from multiple AI providers:

### Anthropic (Default)
- `claude-3-sonnet` (default)
- `claude-3.5-sonnet` (latest)
- `claude-3.5-haiku` (latest)
- `claude-3-opus` (latest)
- `claude-3-haiku`
- `claude-3` (alias for claude-3-opus)

### Azure OpenAI
- `azure/o1-mini`
- `azure/gpt-4o`
- `azure/gpt-4o-mini`
- `azure/gpt-4` (alias for gpt-4o)

### OpenAI
- `gpt-4`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

## Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details on:
- Setting up your development environment
- Our development workflow
- Code style guidelines
- Pull request process
- Running tests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.