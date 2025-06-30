# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIPR is an AI-powered tool that automatically generates comprehensive pull request descriptions by analyzing git diffs and vulnerabilities. It supports multiple AI providers (Anthropic Claude, OpenAI, Azure OpenAI, Google Gemini) and integrates with Trivy for security scanning.

## Key Commands

### Development
- `make install` - Set up virtual environment and install all dependencies
- `make format` - Auto-format code with Black and isort
- `make lint` - Run flake8 linting
- `make test` - Run pytest with coverage
- `make check` - Run format, lint, and test in sequence
- `make clean` - Remove build artifacts and virtual environment
- `make build` - Build distribution packages

### Testing
- Run all tests: `make test`
- Run specific test: `pytest tests/test_main.py::test_name`
- Run with coverage: `pytest --cov=aipr`

### Usage
- Generate PR description: `aipr --model claude` or `aipr pr --model claude`
- Generate commit message: `aipr commit --model claude`
- Generate PR description from commit range: `aipr pr --from abc123 --to def456 --model claude`
- Generate commit message from commit range: `aipr commit --from v1.0.0 --model claude`
- With custom prompt: `aipr pr --model claude --prompt path/to/prompt.xml`
- Create GitHub PR: `make pr title="Your PR title"`

## Architecture

### Core Components
- **`aipr/main.py`**: CLI entry point with subcommand routing, orchestrates git operations, provider routing, and Trivy integration
- **`aipr/commit.py`**: Commit message analysis and generation with conventional commit format support
- **`aipr/providers.py`**: AI provider integrations (Anthropic, OpenAI, Azure OpenAI, Gemini)
- **`aipr/prompts/prompts.py`**: Prompt management with PromptManager class, handles built-in and custom XML prompts

### Provider-Specific Notes
- **Azure OpenAI**: o1-mini model requires special handling (no temperature parameter, system prompt prepended to user message)
- **Model Aliases**: "claude" → claude-sonnet-4-20250514, "azure" → gpt-4o-mini, "openai" → gpt-4o, "gemini" → gemini-2.5-pro-experimental

### Custom Prompts
**PR Description Prompts** must be XML files with:
- `<system>` element for system prompt
- `<user>` element with `<changes-set>` and `<vulnerabilities-set>` placeholders

**Commit Message Prompts** must be XML files with:
- Built-in commit prompt at `aipr/prompts/commit.xml`
- Placeholders: `<staged-changes>`, `<file-summary>`, `<context>`
- Focuses on conventional commit format generation

## Core Documentation

- @CONTRIBUTING.md - AI-driven development workflow
- @docs/adr/README.md - Architectural decisions index
- @CHANGELOG.md - Feature history with architectural context

## Environment Setup

Required environment variables:
- `ANTHROPIC_API_KEY` - For Claude models
- `AZURE_API_KEY` and `AZURE_ENDPOINT` - For Azure OpenAI
- `OPENAI_API_KEY` - For OpenAI models
- `GEMINI_API_KEY` - For Google Gemini models

## Important Conventions

1. **Python Version**: Requires Python 3.11+
2. **Package/Module Names**: Package is `pr-generator-agent`, import as `aipr`
3. **Commit Messages**: Use conventional commits format (feat:, fix:, chore:, etc.)
4. **Testing**: All new features should have corresponding tests in `tests/`
5. **Formatting**: Code must pass `make check` before committing

## Code Style
- Use Python type hints for function parameters and return values
- Follow PEP 8 conventions with 100-char line length (as configured)
- Use docstrings with Args/Returns/Raises sections in Google style
- Group imports: stdlib, third-party, local (enforced by isort)
- Error handling: Use built-in exceptions or custom ones in aipr/
- Class naming: PascalCase
- Function/variable naming: snake_case
- Constants: UPPER_SNAKE_CASE
- Validate input parameters with clear error messages
- Tests should use pytest fixtures and mock external API calls

## Commit Guidelines
- Use conventional commit message format (Release Please compatible):
  * Format: `<type>(<scope>): <description>`
  * Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
  * Example: `fix(cache): update TTL for metadata caching`
  * Breaking changes: Add `!` after type/scope and include `BREAKING CHANGE:` in body
  * Example: `feat(api)!: change response format` with body containing `BREAKING CHANGE: API now returns JSON instead of XML`
- Ensure commit messages are concise and descriptive
- Explain the purpose and impact of changes in the commit message
- Group related changes in a single commit
- Keep commits focused and atomic
- For version bumps, use `chore(release): v1.2.3` format

## PR Description Guidelines
Use the output of the git diff to create the description of the Merge Request. Follow this structure exactly:

1. **Title**
   *A one-line summary of the change (max 60 characters).*

2. **Summary**
   *Briefly explain what this PR does and why.*

3. **Changes**
   *List each major change as a bullet:*
   - Change A: what was done
   - Change B: what was done

4. **Technical Details**
   *Highlight any notable technical details relevant to the changes*

## CHANGELOG Guidelines
- CHANGELOG.md is automatically maintained by Release Please
- Do NOT manually edit CHANGELOG.md
- Changes are extracted from conventional commit messages
- Release Please groups changes by type:
  * `feat:` → Features section
  * `fix:` → Bug Fixes section
  * `docs:` → Documentation section
  * `chore:`, `style:`, `refactor:` → Not included in changelog
- Version numbers and dates are automatically managed

## Essential Commands

```bash
# Quality checks (run before committing)
make check                      # Run all checks (format, lint, test)

# Individual commands
make test                       # Run all tests with coverage
make format                     # Auto-format code with black and isort
make lint                       # Run flake8 linting
pytest -xvs tests/test_main.py  # Run specific test file, stop on failure
pytest -xvs tests/test_commit.py  # Run commit-specific tests

# Development workflow
make install                    # Set up development environment
make clean                      # Remove build artifacts
make build                      # Build distribution packages

# Using AIPR
aipr pr                         # Generate PR description (default)
aipr commit                     # Generate conventional commit message
aipr pr --from abc123 --to def456  # Generate PR description from commit range
aipr commit --from v1.0.0       # Generate commit message from commit to HEAD
aipr commit --debug             # Show analysis without AI call
aipr pr --debug                 # Show PR prompts without AI call

# Pre-commit hooks (after installation)
pre-commit install              # Install git hooks
pre-commit run --all-files      # Run all hooks manually
```
