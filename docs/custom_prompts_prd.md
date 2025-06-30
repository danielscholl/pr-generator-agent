# Custom Prompt File Integration for AIPR

## Overview
Enable users to specify an external custom prompt file when invoking AIPR. This feature will allow users to supply their own XML prompt template via a command-line option, without modifying or placing files inside the read-only pipx installation environment.

## Problem Statement
Users installing AIPR via pipx cannot alter the installed package files. However, some users want to use a custom prompt template. Currently, the system may assume the prompt file is bundled or located within the package. This feature is needed to allow users to provide an absolute file path to their own prompt file while maintaining the integrity of the pipx installation.

## Goals and Objectives
- Allow users to provide the full path to a custom prompt file via a command-line parameter
- Prevent users from having to drop custom files into the AIPR package folder
- Ensure that if the file exists and is valid, the application loads and uses it
- Display clear error messages when the provided file path is invalid or the file content does not meet the required format
- Update the documentation to clearly explain how to use this new option

## User Stories
- As an AIPR user, I want to supply a custom XML prompt file through a command-line option so that I can use my personalized prompt without altering the package
- As an AIPR user, I need clear feedback if the file path is incorrect or if the file format is invalid so that I can correct the issue promptly
- As a developer, I want to update the user documentation to clearly explain how to invoke AIPR with a custom prompt file

## Functional Requirements
1. The prompt manager should check if a custom prompt parameter is provided via the command-line (e.g., using the "-p" flag)
2. The application must verify that the given value is a valid file path on the user's filesystem
3. If the file exists, the system should load the XML content from that file and parse it as the prompt template
4. If the file does not exist or fails validation (e.g., does not follow the expected XML structure), the system must display a clear, user-friendly error message
5. If no custom prompt is provided, the system should continue to use the default built-in prompt template
6. The feature must work seamlessly in a pipx environment where the package is installed in a read-only location

## Non-Functional Requirements
- The solution should be backward-compatible with existing usages where no custom prompt is specified
- Error handling must be robust, ensuring users receive actionable feedback
- Documentation and help texts must be updated to reflect the new functionality
- Unit and integration tests must cover scenarios including valid custom file, invalid file path, and invalid file format

## Assumptions
- Users are capable of creating and maintaining their own XML prompt file that conforms to the expected structure
- Users will supply an absolute path or a path relative to their current working directory
- The file system is accessible from the environment where AIPR is invoked

## Dependencies
- Modifications to the prompt manager module to support file path detection and XML parsing of external files
- Changes to the command-line argument parsing logic if necessary
- Updates to user documentation (README, user guides) and possibly the release notes
- Changelog should exist to track the changes to the project

## Acceptance Criteria
- When a valid custom prompt file path is provided via the command-line option, AIPR loads and uses the custom prompt template
- If the provided path is invalid or the file content is improperly formatted, AIPR displays an appropriate error message
- Users do not need to modify any files inside the AIPR installation folder
- Documentation clearly explains how to create a valid custom prompt file and how to supply its path when running AIPR
- Automated tests exist to verify the feature under different scenarios (valid file, missing file, invalid file format)

## Prompt System Design
The prompt system should support the following capabilities:

### Built-in Prompts
- AIPR should ship with a set of built-in, tested prompt templates
- Built-in prompts should be accessible by name (e.g., `aipr pr -p meta`)
- The system should maintain a registry of available built-in prompts
- Built-in prompts should be versioned with the package

### Custom Prompts
- Users should be able to provide their own prompt files via file path
- Custom prompts should follow the same XML schema as built-in prompts
- The system should validate custom prompts before use
- Clear error messages should guide users in fixing invalid prompts

### Command-Line Interface
- The `-p/--prompt` flag should accept either:
  - A built-in prompt name (e.g., `aipr pr -p meta`)
  - A path to a custom prompt file (e.g., `aipr pr -p ~/prompts/custom.xml`)
- When an invalid prompt is specified, the system should list available built-in prompts
- Help text should clearly explain both usage patterns

### Documentation Requirements
- Document the XML schema for prompt files
- Provide examples of valid prompt files
- List all available built-in prompts and their intended use cases
- Include best practices for creating custom prompts
- Document all error messages and their resolution steps

## Testing Requirements

### Unit Tests
- Test prompt loading for both built-in and custom prompts
- Test validation of XML prompt files
- Test error handling for:
  - Invalid file paths
  - Malformed XML files
  - Missing required XML elements
  - Invalid prompt names
- Test the prompt registry system
- Test backward compatibility with existing functionality

## Linting and Code Quality Requirements
- All new code must pass:
  - `black` for code formatting
  - `isort` for import sorting
  - `flake8` for style guide enforcement
- Type hints must be included for all new functions and methods
- Documentation strings required for all new classes and functions
- Comments required for complex logic or business rules
- No `pylint` warnings or errors in new code
- All test files must follow the same code quality standards

## Documentation Testing
- Verify all code examples in documentation are correct and functional
- Test documentation for clarity and completeness
- Ensure help text and error messages are clear and actionable
