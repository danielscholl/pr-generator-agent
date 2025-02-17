# Contributing to AIPR

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

2. **Package and Command Names**
   - PyPI Package Name: `pr-generator-agent` (for installation)
   - Module Name: `aipr` (for imports)
   - Command Name: `aipr` (CLI tool)
   
   Example usage:
   ```bash
   # Installing the package
   pip install pr-generator-agent
   
   # Using the CLI tool
   aipr
   
   # Importing in Python
   from aipr import ...
   ```

3. **Development Commands**
```bash
# Key make targets
make install  # Sets up the virtualenv and installs dependencies
make check    # Runs linting, formatting, tests
make test     # Just run the test suite
make pr       # Creates a pull request via gh/glab
make clean    # Removes build artifacts & venv
```

4. **Code Style**
- We use Black for code formatting and Flake8 for linting
- All code must pass `make check` before being merged
- GitHub Actions will automatically verify these checks on your PR

5. **Commit Conventions**
We use [Conventional Commits](https://www.conventionalcommits.org/) to automate versioning and changelog generation. Your commit messages should follow this format:
```
type(optional-scope): description

[optional body]
[optional footer(s)]
```

Types that affect versioning:
- `feat:` - New feature (bumps minor version)
- `fix:` - Bug fix (bumps patch version)
- `feat!:` or `fix!:` - Breaking change (bumps major version)

Other types (don't affect version):
- `docs:` - Documentation changes
- `style:` - Code style changes
- `refactor:` - Code changes that neither fix a bug nor add a feature
- `test:` - Adding/updating tests
- `chore:` - Maintenance tasks

Examples:
```bash
git commit -m "feat: add support for OpenAI models"
git commit -m "fix: handle empty commit messages"
git commit -m "feat!: switch to new API version"
git commit -m "docs: update installation instructions"
```

6. **Initial Setup**
```bash
# Verify GitHub CLI is installed and authenticated
gh auth status

# Fork the repository and clone it
gh repo fork danielscholl/pr-generator-agent --clone=true
cd pr-generator-agent

# The gh fork command automatically sets up the upstream remote
# You can verify with: git remote -v

# Create virtual environment and install dependencies
make install

# Activate the virtual environment
source .venv/bin/activate 
```

7. **Making Changes**
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
git commit -m "feat: description of your changes"  # Use conventional commits!
git push -u origin feature-name

# Create a pull request
make pr                         # Uses commit messages for title and description
make pr title="Add new feature" # Uses a specific title
```

## Release Process

Releases are automated using Release Please. Here's how it works:

1. **Versioning**
   - Commits to `main` automatically trigger version updates based on conventional commits
   - `fix:` commits bump the patch version (0.1.0 → 0.1.1)
   - `feat:` commits bump the minor version (0.1.0 → 0.2.0)
   - `feat!:` or any commit with `!` bump the major version (0.1.0 → 1.0.0)

2. **Release Flow**
   - Push commits to main using conventional commit messages
   - Release Please automatically creates/updates a release PR
   - When the release PR is merged:
     - Version is bumped in `pyproject.toml` and `__init__.py`
     - Changelog is updated
     - GitHub release is created
     - Git tag is created

3. **Publishing**
   - Publishing to PyPI is a manual step
   - Go to Actions → Release Management
   - Click "Run workflow"
   - Select "Publish current release to PyPI"
   - Click "Run workflow"

## Pull Request Process

1. After opening a PR, a maintainer will review your changes
2. We aim to respond within 3 business days
3. We may request changes or additional tests
4. Once approved and all checks pass, we'll merge your contribution

## License

By contributing, you agree that your contributions will be licensed under the MIT License.