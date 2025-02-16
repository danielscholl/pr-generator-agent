# Contributing to AIMR

We welcome pull requests from everyone! Whether it's a bug fix, new feature, or documentation improvement, we appreciate your help. This guide will help you get started.

## Before You Start

- If you're planning a large or complex change, please open an issue first to discuss the approach.
- Have questions? Open a Discussion or create an Issue with the "question" label.
- All contributions must follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Development Guide

1. **Prerequisites**
   - Python 3.10 or higher
   - Git
   - GitHub account
   - GitHub CLI (`gh`) - https://cli.github.com

2. **Development Commands**
```bash
# Key make targets
make install  # Sets up the virtualenv and installs dependencies
make check    # Runs linting, formatting, tests
make test     # Just run the test suite
make mr       # Creates a merge request via gh/glab
make clean    # Removes build artifacts & venv
```

3. **Code Style**
- We use Black for code formatting and Flake8 for linting
- All code must pass `make check` before being merged
- GitHub Actions will automatically verify these checks on your PR

4. **Initial Setup**
```bash
# Verify GitHub CLI is installed and authenticated
gh auth status

# Fork the repository and clone it
gh repo fork danielscholl/mr-generator-agent --clone=true
cd mr-generator-agent

# The gh fork command automatically sets up the upstream remote
# You can verify with: git remote -v

# Create virtual environment and install dependencies
make install

# Activate the virtual environment
source .venv/bin/activate 
```

5. **Making Changes**
```bash
# Ensure your fork is up to date
git fetch upstream
git checkout main
git merge upstream/main

# Create a new branch
git checkout -b feature-name

# Make your changes...

# Verify your changes
make check

# Commit and push your changes
git add .
git commit -m "Description of your changes"
git push -u origin feature-name

# Create a pull request
make pr                         # Uses commit messages for title and description
make pr title="Add new feature" # Uses a specific title
```

## Pull Request Process

1. After opening a PR, a maintainer will review your changes
2. We aim to respond within 3 business days
3. We may request changes or additional tests
4. Once approved and all checks pass, we'll merge your contribution

## License

By contributing, you agree that your contributions will be licensed under the MIT License. 