# AIMR - AI-powered Merge Request Description Generator

AIMR is a command-line tool that generates high-quality merge request descriptions using AI models. It analyzes git diffs and optionally performs vulnerability scanning to create comprehensive, well-structured merge request descriptions.

## Features

- Generates merge request descriptions using various AI models (Azure OpenAI, OpenAI, Anthropic)
- Supports vulnerability scanning and comparison between branches using Trivy
- Integrates with GitLab and GitHub CLI tools
- Supports multiple project types (Java, Node.js, Python)

## Installation

Install using pipx (recommended):

```bash
pipx install aimr
```

Or using pip:

```bash
pip install aimr
```

## Prerequisites

- Python 3.8 or higher
- Git
- Trivy (optional, for vulnerability scanning)
- One of the following API keys:
  - Azure OpenAI API key (default)
  - OpenAI API key
  - Anthropic API key

## Environment Variables

Set up the required API keys:

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

Basic usage:

```bash
# Generate MR description for current branch
aimr

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
```

Available options:

```bash
aimr --help
```

## Available Models

### Azure OpenAI
- azure/o1-mini (default)
- azure/gpt-4o
- azure/gpt-4o-mini
- azure/gpt-4 (alias for gpt-4o)

### OpenAI
- gpt-4
- gpt-4-turbo
- gpt-3.5-turbo

### Anthropic
- claude-3.5-sonnet (latest)
- claude-3.5-haiku (latest)
- claude-3-opus (latest)
- claude-3-sonnet
- claude-3-haiku
- claude-3 (alias for claude-3-opus)

## License

MIT

## Development

If you want to develop or contribute to AIMR, we recommend using `uv` for a faster and more reliable development environment.

### Setting up the Development Environment

1. Install `uv` if you haven't already:
```bash
pip install uv
```

2. Clone the repository:
```bash
git clone https://github.com/danielscholl/mr-generator-agent.git
cd mr-generator-agent
```

3. Create a virtual environment and install dependencies:
```bash
uv venv
uv pip install -e ".[dev]"  # Install in editable mode with development dependencies
```

### Development Workflow

1. Activate the virtual environment:
```bash
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows
```

2. Make your changes to the code

3. Run the development version:
```bash
python -m aimr.main  # Run directly from source
# or
pip install -e .     # Install in editable mode
aimr                 # Run the installed development version
```

### Adding Dependencies

To add new dependencies:

1. Add them to `pyproject.toml` in the appropriate section:
```toml
[project]
dependencies = [
    # Runtime dependencies
]

[project.optional-dependencies]
dev = [
    # Development dependencies
]
```

2. Update your development environment:
```bash
uv pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

### Building the Package

To build the package for distribution:

```bash
uv pip install build
python -m build
```

This will create both wheel and source distribution in the `dist/` directory.

### Local Testing

To test your changes locally before committing:

1. Build the package:
```bash
python -m build
```

2. Install it with pipx in editable mode:
```bash
pipx install -e .
```

Or test it in a temporary environment:
```bash
pipx install --suffix=@dev -e .
aimr@dev --help
```

### Code Style

We use:
- Black for code formatting
- isort for import sorting
- flake8 for linting

Format your code before committing:
```bash
black aimr/
isort aimr/
flake8 aimr/
```