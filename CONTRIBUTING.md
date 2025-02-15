# Contributing to AIMR

Thank you for your interest in contributing to AIMR! This document provides guidelines and instructions for contributing.

## Development Guide

1. **Prerequisites**
   - Python 3.10 or higher
   - Git
   - GitHub account
   - GitHub CLI (`gh`) - https://cli.github.com

2. **Initial Setup**
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

3. **Making Changes**
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

4. **Cleanup**
```bash
# Exit development environment
deactivate

# Remove virtual environment and build artifacts (optional)
make clean
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License. 