# Contributing to AIMR

Thank you for your interest in contributing to AIMR! This document provides guidelines and instructions for contributing.

## Development Setup

1. Install `uv` package manager:
```bash
pip install uv
```

2. Clone and prepare the repository:
```bash
git clone https://github.com/danielscholl/mr-generator-agent.git
cd mr-generator-agent
uv venv
uv pip install -e ".[dev]"  # Install in editable mode with development dependencies
```

## Development Workflow

1. Create a new branch for your feature or bugfix:
```bash
git checkout -b feature-name
```

2. Make your changes following our code style guidelines.

3. Run tests and linters:
```bash
# Run all tests
pytest

# Run linters
black aimr/
isort aimr/
flake8 aimr/
```

4. Commit your changes:
```bash
git add .
git commit -m "Description of changes"
```

5. Push your branch and create a pull request.

## Code Style Guidelines

- We use `black` for code formatting with a line length of 100
- Imports are sorted using `isort`
- Code should pass `flake8` checks
- Write meaningful commit messages
- Include tests for new features
- Update documentation as needed

## Pull Request Process

1. Ensure your code passes all tests and linting checks
2. Update the README.md if needed
3. Update the version number in `aimr/__init__.py` if applicable
4. The PR will be reviewed by maintainers
5. Once approved, it will be merged into the main branch

## Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=aimr

# Run specific test file
pytest tests/test_specific.py
```

## Questions or Problems?

- Open an issue for bugs
- Start a discussion for feature requests or questions
- Tag issues appropriately

## License

By contributing, you agree that your contributions will be licensed under the MIT License. 