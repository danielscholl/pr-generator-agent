# ADR Catalog

Architecture Decision Records for AIPR - AI-Powered Pull Request Generator

## Index

| ID  | Title                               | Status   | Date       | Details |
| --- | ----------------------------------- | -------- | ---------- | ------- |
| 001 | Provider Architecture Pattern       | Accepted | 2024-11-15 | [ADR-001](001-provider-architecture.md) |
| 002 | XML-Based Prompt Template System    | Accepted | 2024-11-20 | [ADR-002](002-xml-prompt-templates.md) |
| 003 | Git Integration Strategy            | Accepted | 2024-11-25 | [ADR-003](003-git-integration-strategy.md) |
| 004 | Security Scanning Integration       | Accepted | 2024-12-01 | [ADR-004](004-security-scanning-integration.md) |

## Overview

These Architecture Decision Records document the key design choices made in the AIPR project. Each ADR explains the context, decision, rationale, and consequences of significant architectural choices.

## Quick Reference

### Core Architecture Decisions

**Provider Architecture (ADR-001)**
- Function-based provider pattern with central routing
- Model aliasing for improved UX
- Environment-based configuration

**Prompt System (ADR-002)**
- XML format for templates
- Placeholder-based content injection
- Support for custom prompts

**Git Integration (ADR-003)**
- GitPython library over subprocess calls
- Smart change detection logic
- Robust error handling

**Security Scanning (ADR-004)**
- Trivy integration for vulnerability analysis
- Optional feature with zero impact when disabled
- Automatic project type detection

## Contributing

When adding new ADRs:
1. Use the next sequential number
2. Follow the established format
3. Update this index
4. Status should be: Draft → Proposed → Accepted/Rejected
5. Include implementation examples where relevant
