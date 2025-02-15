# AIMR - AI-powered Merge Request Description Generator

AIMR automatically generates high-quality merge request descriptions by analyzing git diffs and optionally performing vulnerability scanning. It uses state-of-the-art AI models to create comprehensive, well-structured descriptions that save time and improve code review quality.

## Supported AI Models

Choose from multiple AI providers for generating descriptions:

### Azure OpenAI (Default)
- `azure/o1-mini` (default)
- `azure/gpt-4o`
- `azure/gpt-4o-mini`
- `azure/gpt-4` (alias for gpt-4o)

### OpenAI
- `gpt-4`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

### Anthropic
- `claude-3.5-sonnet` (latest)
- `claude-3.5-haiku` (latest)
- `claude-3-opus` (latest)
- `claude-3-sonnet`
- `claude-3-haiku`
- `claude-3` (alias for claude-3-opus)

## Key Features

- **Smart Branch Detection**: Automatically detects whether to show working tree changes or compare branches
- **Vulnerability Scanning**: Optional security analysis between branches using Trivy
- **Multiple Project Support**: Works with Java, Node.js, Python, and other project types
- **CI/CD Integration**: Works seamlessly with GitLab and GitHub CLI tools

## Installation

### Prerequisites
- Python 3.8 or higher
- Git
- Trivy (optional, for vulnerability scanning)
- One of the following API keys:
  - Azure OpenAI API key (default)
  - OpenAI API key
  - Anthropic API key

### Install from Repository
```bash
# Clone the repository
git clone https://github.com/danielscholl/mr-generator-agent.git
cd mr-generator-agent

# Install using pipx (recommended)
pipx install .

# Or install using pip
pip install .
```

### Install from GitHub (without cloning)
```bash
# Install using pipx (recommended)
pipx install git+https://github.com/danielscholl/mr-generator-agent.git

# Or install using pip
pip install git+https://github.com/danielscholl/mr-generator-agent.git
```

Note: Once the package is published to PyPI, you'll be able to install it directly using:
```bash
pipx install aimr  # Not available yet
```

### API Configuration
```bash
# For Azure OpenAI (default)
export AZURE_API_KEY="your-api-key"
export AZURE_API_BASE="your-api-base"
export AZURE_API_VERSION="2024-02-15-preview"  # Optional

# For OpenAI
export OPENAI_API_KEY="your-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-api-key"
```

## Usage

### Basic Commands
```bash
# Generate MR description (auto-detects changes)
aimr

# Compare with specific target branch
aimr -t develop

# Include vulnerability scanning
aimr --vulns

# Force showing only working tree changes
aimr -t -
```

### Smart Detection
The tool intelligently decides what to compare:
1. If you have staged/unstaged changes, it shows those changes
2. If your branch is clean, it compares against:
   - The specified target branch (with `-t`)
   - Or tries to find a default branch ('main', 'master', 'develop')

### CI/CD Integration
```bash
# GitLab MR creation
glab mr create -d "$(aimr -s)" -t "your title"  # Auto-detects target
glab mr create -d "$(aimr -s -t master)" -t "your title"  # Specific target

# GitHub PR creation
gh pr create -b "$(aimr -s)" -t "your title"  # Auto-detects target
gh pr create -b "$(aimr -s -t develop)" -t "your title"  # Specific target
```

For all available options:
```bash
aimr --help
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:
- Setting up your development environment
- Our development workflow
- Code style guidelines
- Pull request process
- Running tests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.