# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2](https://github.com/danielscholl/pr-generator-agent/compare/v0.1.1...v0.1.2) (2025-02-17)


### Bug Fixes

* improve release-please version management configuration ([d5a62c9](https://github.com/danielscholl/pr-generator-agent/commit/d5a62c9a98d1cc1f6999c37162955b44edaa735c))
* update release-please configuration for better version management ([71b1277](https://github.com/danielscholl/pr-generator-agent/commit/71b1277a71d238fc804b7616a70aabab05a87816))

## [0.1.1](https://github.com/danielscholl/pr-generator-agent/compare/v0.1.0...v0.1.1) (2025-02-17)


### Bug Fixes

* project file ([040d592](https://github.com/danielscholl/pr-generator-agent/commit/040d5920db5d082cb5f7de23ff5939cb70608313))
* update package name to pr-generator-agent and align documentation ([a8605ba](https://github.com/danielscholl/pr-generator-agent/commit/a8605ba3bd1b2cb7ac21c315f5c19a119f990f8c))

## 0.1.0 (2025-02-16)


### Features

* initial release of AIPR ([81b40cb](https://github.com/danielscholl/pr-generator-agent/commit/81b40cbd77e0bc767e93f657c71d701f494d261b))

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
