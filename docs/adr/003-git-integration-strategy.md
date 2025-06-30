# ADR-003: Git Integration Strategy

## Status
**Accepted** - 2024-11-25  
**Updated** - 2025-06-30 (Added commit range functionality)

## Context
AIPR needs robust Git integration to analyze repository changes, detect branches, and generate diffs. The integration must handle various Git workflows (staged/unstaged changes, branch comparisons, commit range analysis) while providing clear error messages and supporting different repository states.

**Update Context (2025-06-30):** Added support for commit range analysis where users can specify arbitrary commit ranges (SHA to SHA) for both PR descriptions and commit message generation.

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

### Commit Range Analysis (Added 2025-06-30)
```python
def get_commit_range_diff(repo: git.Repo, from_commit: str, to_commit: str = "HEAD") -> tuple[str, dict]:
    """Get diff and file statistics for a commit range."""
    try:
        # Validate that both commits exist
        repo.git.cat_file("-e", f"{from_commit}^{{commit}}")
        repo.git.cat_file("-e", f"{to_commit}^{{commit}}")
        
        # Get the diff between commits
        diff_content = repo.git.diff(f"{from_commit}..{to_commit}")
        
        # Get file statistics
        name_status = repo.git.diff(f"{from_commit}..{to_commit}", "--name-status")
        
        # Parse file statistics
        files = []
        for line in name_status.split("\n"):
            if line.strip():
                status, filepath = line.split("\t", 1)
                files.append({"status": status, "path": filepath})
        
        return diff_content, {"files": files, "total": len(files)}
        
    except git.exc.GitCommandError as e:
        if "does not exist" in str(e) or "bad revision" in str(e):
            raise ValueError(f"Invalid commit reference: {from_commit} or {to_commit}")
        else:
            raise ValueError(f"Failed to get commit range diff: {e}")
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
- Support for all major Git workflows (staged, unstaged, branch comparison, commit ranges)
- Robust commit range validation with helpful error messages
- Easy to test with mock repositories
- Commit range operations work with any valid git reference (SHA, branch, tag)
