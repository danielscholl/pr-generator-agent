# ADR-004: Security Scanning Integration

## Status
**Accepted** - 2024-12-01

## Context
Modern pull requests should include security analysis to help reviewers understand the security impact of changes. AIPR needs to integrate vulnerability scanning to compare security states between branches and include this information in PR descriptions.

## Decision
Integrate Trivy as an optional security scanner with automatic project type detection and vulnerability comparison between branches.

## Rationale
1. **Industry Standard**: Trivy is widely adopted and well-maintained by Aqua Security
2. **Multi-Language**: Supports Java, Node.js, Python, Go, and more out of the box
3. **Fast Scanning**: Efficient scanning with local vulnerability database
4. **CI/CD Friendly**: Designed for automation and pipeline integration
5. **Rich Output**: Provides detailed vulnerability information including CVEs and fixes

## Alternatives Considered
1. **Built-in Security Scanning**
   - **Pros**: No external dependencies, full control
   - **Cons**: Massive undertaking, maintaining vulnerability databases
   - **Decision**: Rejected as impractical and outside core competency

2. **Snyk CLI**
   - **Pros**: Good developer experience, fix suggestions
   - **Cons**: Requires account/API key, usage limits
   - **Decision**: Rejected due to authentication requirements

3. **OWASP Dependency Check**
   - **Pros**: Mature, comprehensive
   - **Cons**: Slower, Java-focused, complex setup
   - **Decision**: Rejected due to performance and complexity

4. **GitHub Security Scanning API**
   - **Pros**: Integrated with GitHub
   - **Cons**: GitHub-specific, requires API access
   - **Decision**: Rejected to maintain tool independence

## Consequences
**Positive:**
- Zero-configuration scanning for users
- Fast, local scanning without API calls
- Comprehensive language support
- Clear vulnerability reporting
- Optional feature doesn't impact core functionality

**Negative:**
- Requires Trivy installation (external dependency)
- Trivy database updates needed for accuracy
- Additional complexity in diff analysis
- Potential for false positives

## Implementation Design

### Project Type Detection
```python
def detect_project_type(repo_path: str) -> str:
    """Auto-detect project type for enhanced scanning"""
    files = os.listdir(repo_path)

    if "pom.xml" in files or "build.gradle" in files:
        return "java"
    elif "package.json" in files:
        return "nodejs"
    elif "requirements.txt" in files or "setup.py" in files:
        return "python"
    elif "go.mod" in files:
        return "golang"

    return "auto"  # Let Trivy auto-detect
```

### Vulnerability Comparison
```python
def compare_vulnerabilities(base_vulns: List[dict], head_vulns: List[dict]) -> dict:
    """Compare vulnerability sets between branches"""

    base_ids = {v['id'] for v in base_vulns}
    head_ids = {v['id'] for v in head_vulns}

    return {
        'fixed': base_ids - head_ids,
        'introduced': head_ids - base_ids,
        'severity_summary': count_by_severity(head_vulns)
    }
```

### Integration Flow
1. Checkout base branch, run Trivy scan
2. Checkout head branch, run Trivy scan
3. Parse JSON outputs from both scans
4. Compare and summarize differences
5. Format results for prompt injection

### Error Handling
- Gracefully handle missing Trivy installation
- Continue without scanning if Trivy fails
- Clear user messaging about scan failures
- Never block PR generation due to scan issues

## CLI Integration
```bash
# Enable vulnerability scanning
aipr pr --vulns

# Works with all providers
aipr pr --model azure --vulns

# Appears in PR description only if enabled
```

## Success Criteria
- Scanning completes in < 30 seconds for typical projects
- Clear differentiation between fixed/introduced vulnerabilities
- Zero-impact on users who don't use the feature
- Actionable vulnerability information in PR descriptions
