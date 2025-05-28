# ADR-003: Git Integration Strategy

## Status
**Accepted** - 2024-11-25

## Context
AIPR needs robust Git integration to analyze repository changes, detect branches, and generate diffs. The integration must handle various Git workflows (staged/unstaged changes, branch comparisons) while providing clear error messages and supporting different repository states.

## Decision
Use GitPython library for all Git operations instead of subprocess calls to git commands.

## Rationale
1. **Type Safety**: GitPython provides typed interfaces reducing runtime errors
2. **Error Handling**: Better exception hierarchy for different Git failures
3. **Cross-Platform**: Consistent behavior across Windows/Mac/Linux
4. **Pythonic API**: More maintainable than parsing command outputs
5. **Performance**: Direct access to Git objects without process overhead

## Alternatives Considered
1. **Subprocess Git Commands**
   - **Pros**: No dependencies, direct git CLI usage, easier debugging
   - **Cons**: Output parsing complexity, platform differences, error handling
   - **Decision**: Rejected due to parsing complexity and error handling

2. **pygit2 (libgit2 bindings)**
   - **Pros**: High performance, low-level control
   - **Cons**: Complex API, C dependencies, harder installation
   - **Decision**: Rejected due to complexity and installation issues

3. **Custom Git Implementation**
   - **Pros**: Full control, no dependencies
   - **Cons**: Massive undertaking, reinventing the wheel
   - **Decision**: Rejected as completely impractical

## Consequences
**Positive:**
- Robust error handling with specific exceptions
- Clean API for common operations
- Type hints improve code quality
- Consistent behavior across platforms
- Easy to mock for testing

**Negative:**
- Additional dependency to manage
- GitPython occasionally lags behind new Git features
- Learning curve for developers unfamiliar with the library
- Slightly harder to debug than raw git commands

## Implementation Patterns

### Repository Detection
```python
def is_git_repo(path: str = ".") -> bool:
    try:
        git.Repo(path)
        return True
    except git.InvalidGitRepositoryError:
        return False
```

### Smart Change Detection
```python
def get_changes(repo: git.Repo, target_branch: str = None) -> tuple[str, str]:
    # Priority order:
    # 1. Staged changes (if any)
    # 2. Working directory changes (if any)
    # 3. Diff against target branch

    staged = repo.index.diff("HEAD")
    if staged:
        return "staged", get_staged_diff(repo)

    unstaged = repo.index.diff(None)
    if unstaged:
        return "working", get_working_diff(repo)

    if target_branch:
        return "branch", get_branch_diff(repo, target_branch)
```

### Branch Detection
```python
def get_default_branch(repo: git.Repo) -> str:
    # Try common default branch names
    for branch_name in ["main", "master", "develop"]:
        if branch_name in repo.heads:
            return branch_name

    # Fall back to first branch
    if repo.heads:
        return repo.heads[0].name

    raise ValueError("No branches found")
```

## Error Handling Strategy
- `git.InvalidGitRepositoryError`: Not a git repository
- `git.NoSuchPathError`: Invalid path
- `git.GitCommandError`: Git operation failed
- Always provide actionable error messages

## Success Criteria
- Git operations complete in < 1 second for typical repos
- Clear error messages for common failures
- Support for all major Git workflows
- Easy to test with mock repositories
