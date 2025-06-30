# ADR-005: CLI Architecture and Command Design

## Status
**Accepted** - 2025-06-30

## Context
AIPR has evolved from a simple single-purpose tool to a comprehensive CLI application supporting multiple use cases: PR description generation, commit message generation, and commit range analysis. The CLI needed to be restructured to support this expanded functionality while maintaining backward compatibility and providing an intuitive user experience.

## Decision
Implement a subcommand-based CLI architecture using argparse with the following structure:

1. **Primary Commands**: `pr` and `commit` as distinct subcommands
2. **Backward Compatibility**: Main command without subcommand defaults to `pr` behavior
3. **Global Flags**: Consistent flags (`-d`, `-s`, `-v`, `-m`) available across all commands
4. **Argument Validation**: Comprehensive validation with clear error messages
5. **Commit Range Support**: `--from` and `--to` flags for both commands with mutual exclusivity rules

## Rationale

### Subcommand Architecture
1. **Clarity**: Users can immediately understand the tool's capabilities (`aipr pr`, `aipr commit`)
2. **Extensibility**: Easy to add new commands in the future
3. **Separation of Concerns**: Each command has its own argument set and validation
4. **Discoverability**: Help system clearly shows available commands and options

### Global Flags Design
1. **Consistency**: Same behavior across all commands reduces cognitive load
2. **Predictability**: Users expect `-v` to mean verbose everywhere
3. **Implementation Simplicity**: Flags are added to each subparser to ensure they work

### Commit Range Functionality
1. **Flexibility**: Users can analyze any commit range, not just staged changes
2. **Git Workflow Integration**: Supports complex git workflows and history analysis
3. **Consistent Interface**: Same `--from`/`--to` pattern for both `pr` and `commit` commands

## Alternatives Considered

### 1. Single Command with Mode Flags
```bash
aipr --mode pr --target main
aipr --mode commit --staged
```
- **Pros**: Simpler argument parsing
- **Cons**: Less discoverable, unclear interface, harder to extend
- **Decision**: Rejected due to poor UX

### 2. Separate Executables
```bash
aipr-pr --target main
aipr-commit --staged
```
- **Pros**: Complete separation, no argument conflicts
- **Cons**: Multiple binaries to maintain, harder installation, fragmented experience
- **Decision**: Rejected due to deployment complexity

### 3. Plugin-Style Architecture
```bash
aipr pr --target main
aipr commit --staged
aipr <future-plugin> --options
```
- **Pros**: Highly extensible, clean separation
- **Cons**: Over-engineering for current needs, added complexity
- **Decision**: Considered for future but too complex for current requirements

## Implementation Patterns

### Command Structure
```python
def create_parser():
    parser = argparse.ArgumentParser(prog="aipr")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # PR command
    pr_parser = subparsers.add_parser("pr", help="Generate PR descriptions")
    add_global_flags(pr_parser)
    add_pr_specific_flags(pr_parser)
    
    # Commit command  
    commit_parser = subparsers.add_parser("commit", help="Generate commit messages")
    add_global_flags(commit_parser)
    add_commit_specific_flags(commit_parser)
    
    return parser
```

### Global Flags Pattern
```python
def add_global_flags(parser):
    """Add flags that work across all commands."""
    parser.add_argument("-d", "--debug", action="store_true", help="Debug mode")
    parser.add_argument("-s", "--silent", action="store_true", help="Silent mode")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")
    parser.add_argument("-m", "--model", help="AI model to use")
```

### Argument Validation Pattern
```python
def validate_commit_range_args(args, command_name: str) -> None:
    """Validate commit range arguments with clear error messages."""
    if getattr(args, "to_commit", None) and not getattr(args, "from_commit", None):
        raise ValueError("--to can only be used together with --from")
    
    if command_name == "pr":
        if getattr(args, "from_commit", None) and getattr(args, "target", None):
            raise ValueError("--from/--to cannot be used with --target (mutually exclusive)")
```

### Mode Determination Pattern
```python
def determine_pr_mode(args) -> str:
    """Determine which mode to use for PR generation."""
    if getattr(args, "from_commit", None):
        return "range"
    elif getattr(args, "working_tree", False):
        return "working_tree"
    elif getattr(args, "target", None):
        return "target"
    else:
        return "auto"
```

## Consequences

### Positive
- **Clear Interface**: Users immediately understand available functionality
- **Extensible**: Easy to add new commands (`aipr analyze`, `aipr validate`, etc.)
- **Consistent**: Global flags work the same way across all commands
- **Powerful**: Commit range functionality enables complex git workflow analysis
- **Backward Compatible**: Existing usage patterns continue to work
- **Well-Validated**: Comprehensive argument validation prevents user errors

### Negative
- **Complexity**: More complex argument parsing logic
- **Test Coverage**: More test cases needed to cover all combinations
- **Documentation**: More documentation needed to explain all options
- **Learning Curve**: Users need to learn subcommand structure

## Success Criteria
- All existing usage patterns continue to work (backward compatibility)
- New functionality is discoverable through help system
- Error messages are clear and actionable
- Global flags work consistently across all commands
- Commit range functionality works reliably with all git references
- CLI performance remains under 1 second for typical operations

## Examples

### Basic Usage
```bash
# Backward compatible - generates PR description
aipr

# Explicit subcommands
aipr pr
aipr commit

# With global flags
aipr pr -v -m claude
aipr commit -d -s
```

### Commit Range Usage
```bash
# PR description from commit range
aipr pr --from abc123 --to def456

# Commit message from commit to HEAD
aipr commit --from v1.0.0

# With other options
aipr pr --from main --to feature-branch --vulns -v
```

### Error Cases
```bash
# Clear error messages
aipr pr --to def456  # Error: --to requires --from
aipr pr --from abc123 --target main  # Error: --from/--to cannot be used with --target
```

## Future Considerations
- **Additional Commands**: `aipr analyze` for repo analysis, `aipr validate` for PR validation
- **Plugin System**: If the tool grows significantly, consider plugin architecture
- **Configuration Files**: Support for `.aipr.yml` configuration files
- **Interactive Mode**: `aipr interactive` for guided usage
- **Batch Operations**: Support for processing multiple commits/PRs at once