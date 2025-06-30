# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0](https://github.com/danielscholl/pr-generator-agent/compare/v1.2.0...v1.3.0) (2025-06-30)


### Features

* **commit:** add conventional commit message generation ([0b5a36a](https://github.com/danielscholl/pr-generator-agent/commit/0b5a36af59687403a2cff44f90bbc7144030815f))
* improve CLI UX with pr command and fix global flags ([b9c4c12](https://github.com/danielscholl/pr-generator-agent/commit/b9c4c12f11172ffd9b01564dadfea75efd7b0e07))
* update default model to claude-4 and remove claude-3-sonnet ([b89780b](https://github.com/danielscholl/pr-generator-agent/commit/b89780b744a00d583a021530d5c57aedc705accf))


### Documentation

* update remaining documentation for pr command migration ([8627a7b](https://github.com/danielscholl/pr-generator-agent/commit/8627a7b2e5963e2a060d1fe667f2238acc3e7eca))

## [1.2.0](https://github.com/danielscholl/pr-generator-agent/compare/v1.1.0...v1.2.0) (2025-05-28)


### Features

* add Claude 4.0 model support and remove deprecated Opus models ([419dbb3](https://github.com/danielscholl/pr-generator-agent/commit/419dbb37db7ef9cb301d8eb41985ff59a136ad13))
* Add Claude 4.0 model support and remove deprecated Opus models ([3fe0ff0](https://github.com/danielscholl/pr-generator-agent/commit/3fe0ff08c796d8f8186bd312a00240bdf21da851))
* enhance repository management with pre-commit hooks and CI improvements ([e50aa4e](https://github.com/danielscholl/pr-generator-agent/commit/e50aa4e1a07bfc2b5e4cb8d94f85fbc71cd5734d))
* enhance repository management with pre-commit hooks and CI improvements ([cf55baf](https://github.com/danielscholl/pr-generator-agent/commit/cf55bafce68cb33f77d7182448f84922a28166bf)), closes [#31](https://github.com/danielscholl/pr-generator-agent/issues/31)


### Bug Fixes

* add colorama dependency for isort --color flag in CI ([2957b84](https://github.com/danielscholl/pr-generator-agent/commit/2957b84a1901a4c513f8cfdecafd206fdeef299f)), closes [#31](https://github.com/danielscholl/pr-generator-agent/issues/31)
* update black target version to py311 ([f13c84a](https://github.com/danielscholl/pr-generator-agent/commit/f13c84a23442e990df0a8746793f9771f5c09636))


### Documentation

* add ADRs and enhance AI-driven development workflow ([1b55696](https://github.com/danielscholl/pr-generator-agent/commit/1b556962e34cf373123d1207793f69dd61476381))
* add ADRs and enhance AI-driven development workflow ([a88e0b9](https://github.com/danielscholl/pr-generator-agent/commit/a88e0b9667ebc5c63f96f0732b61244c95a7b0fb))
* add badges and AI-driven development section to README ([d1f9815](https://github.com/danielscholl/pr-generator-agent/commit/d1f9815648152d7b237848cc5cadd6e8eed5d539))
* address PR review comments ([9a8f2b7](https://github.com/danielscholl/pr-generator-agent/commit/9a8f2b73dc9f688706d546282105d554e02a1f4c)), closes [#32](https://github.com/danielscholl/pr-generator-agent/issues/32)
* updates ([1a7e5a7](https://github.com/danielscholl/pr-generator-agent/commit/1a7e5a7d56e02ced984c0f2b873b2341a823693b))

## [1.1.0](https://github.com/danielscholl/pr-generator-agent/compare/v1.0.0...v1.1.0) (2025-04-08)


### Features

* add Google Gemini as an AI provider ([64f1be1](https://github.com/danielscholl/pr-generator-agent/commit/64f1be17ac75e1ac0391d9faa13696ffa7465940)), closes [#28](https://github.com/danielscholl/pr-generator-agent/issues/28)

## [1.0.0](https://github.com/danielscholl/pr-generator-agent/compare/v0.1.2...v1.0.0) (2025-02-17)


### ⚠ BREAKING CHANGES

* Promoting to first major release 1.0.0. This marks the first stable release of the AIPR tool.

### Features

* promote to version 1.0.0 ([ae85038](https://github.com/danielscholl/pr-generator-agent/commit/ae850384909425efe311c770e3a1cc087dbdd059))

## [0.1.2](https://github.com/danielscholl/pr-generator-agent/compare/v0.1.1...v0.1.2) (2025-02-17)


### Bug Fixes

* add explicit path to release-please config ([6343f66](https://github.com/danielscholl/pr-generator-agent/commit/6343f66db39c196e97d114e2a7e82eb7b7c44579))
* correct release-please versioning configuration ([58b6718](https://github.com/danielscholl/pr-generator-agent/commit/58b6718c299c318b402c071659fb646675e12537))
* file ([645c225](https://github.com/danielscholl/pr-generator-agent/commit/645c2255e813254852e541b44d8876db37578c4e))
* file ([e761857](https://github.com/danielscholl/pr-generator-agent/commit/e76185745e08934aab79b4998499dcb748d0c728))
* improve release-please version management configuration ([d5a62c9](https://github.com/danielscholl/pr-generator-agent/commit/d5a62c9a98d1cc1f6999c37162955b44edaa735c))
* update release-please config to use toml type and path ([939a94f](https://github.com/danielscholl/pr-generator-agent/commit/939a94ff3a819e919fa4421d805f73f4945857e9))
* update release-please configuration for better version management ([4de1559](https://github.com/danielscholl/pr-generator-agent/commit/4de1559a73153a739423a74ab353828429553524))
* update release-please configuration for better version management ([71b1277](https://github.com/danielscholl/pr-generator-agent/commit/71b1277a71d238fc804b7616a70aabab05a87816))
* update release-please extra-files type to simple ([1e71c6e](https://github.com/danielscholl/pr-generator-agent/commit/1e71c6eb1cdd016c468b737bee09efc93440cfb4))
* update release-please setup for single package ([2e45307](https://github.com/danielscholl/pr-generator-agent/commit/2e4530796519f008b1a9150b856e0abd2342f728))

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
- Support for Python 3.12 and above
- Comprehensive test suite with pytest
- GitHub Actions workflows for testing and releases
- Development environment setup with black, isort, and flake8

### Features
- Customizable prompt system with XML-based prompt definitions ([Custom Prompts PRD](docs/custom_prompts_prd.md))

[1.0.0]: https://github.com/danielscholl/pr-generator-agent/releases/tag/v1.0.0
