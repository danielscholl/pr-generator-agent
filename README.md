# Agentic - Merge Request Generator

A command-line tool that uses AI models to automatically generate merge request descriptions from git diffs.

## Features

- Analyzes git diffs and generates structured merge request descriptions in Markdown format
- Supports comparing against target branches (e.g., comparing your current branch with a specified target branch)
- Works with any Git repository

## Prerequisites

- Python 3.8+
- Git installed and accessible from the command line
- API key for either OpenAI or Anthropic (set as environment variables)
- uv package manager ([Learn more about uv](https://github.com/astral-sh/uv))

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd mr-generator-agent
```

2. Set up your API key(s):

```bash
# For OpenAI
export OPENAI_API_KEY='your-openai-key'

# For Anthropic
export ANTHROPIC_API_KEY='your-anthropic-key'
```

3. Set up the shell function (see "Creating a Shell Function" section below)

The shell function will automatically create a virtual environment and install dependencies when you first run the command.

## Usage

Display the full list of options by running:

```bash
uv run python main.py --help
```

### Basic Usage

Generate a merge request description:

```bash
uv run python main.py /path/to/repo
```

### Using a Target Branch

To compare the current branch against a target branch (e.g., develop):

```bash
uv run python main.py /path/to/repo --target develop
```

### Specifying Models

You can specify different AI models using either `--model` or `-m` flag:

```bash
# OpenAI Models
uv run python main.py -m gpt-4
uv run python main.py -m gpt-4-turbo
uv run python main.py -m gpt-3.5-turbo

# Anthropic Models
uv run python main.py -m claude-3-opus
uv run python main.py -m claude-3-sonnet
uv run python main.py -m claude-2
```

The tool will automatically map common model aliases to their full versions (e.g., 'claude-3' → 'claude-3-opus-20240229')

### Creating a Shell Function (Optional)

To run the tool from any directory, you can create a shell function in your `~/.zshrc` or `~/.bashrc`:

```bash
function aimr() {
    # Store the project directory path
    MR_GENERATOR_DIR="$HOME/source/github/danielscholl/mr-generator-agent"

    # Create virtual environment if it doesn't exist and install dependencies
    if [ ! -d "$MR_GENERATOR_DIR/.venv" ]; then
        cd "$MR_GENERATOR_DIR"
        uv venv
        uv sync
    fi

    # Run the script using the virtual environment
    "$MR_GENERATOR_DIR/.venv/bin/python" "$MR_GENERATOR_DIR/main.py" "$PWD" "$@"
}
```

After saving and reloading your shell configuration (`. ~/.zshrc` or `. ~/.bashrc`):

```bash
# Basic usage
aimr

# With model specification
aimr -m claude-3-opus

# With target branch
aimr -t develop
```

## Example Output

The tool will generate a structured merge request description that includes:
- A concise summary of the changes
- Key modifications and their purpose
- Notable technical details

The output is in markdown format, ready to be pasted into your Git platform's merge request description.