# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-02-17

### Added
- Initial release of AIPR (AI Pull Request Generator)
- Core functionality to generate AI-powered pull request descriptions
- Support for both OpenAI and Anthropic Claude models
- Git integration for analyzing changes and generating contextual PR descriptions
- Command-line interface with customizable options
- Automatic token counting and context management
- Support for Python 3.10 and above
- Comprehensive test suite with pytest
- GitHub Actions workflows for testing and releases
- Development environment setup with black, isort, and flake8

### Features
- Customizable prompt system with XML-based prompt definitions ([Custom Prompts PRD](docs/custom_prompts_prd.md))

[1.0.0]: https://github.com/danielscholl/pr-generator-agent/releases/tag/v1.0.0 