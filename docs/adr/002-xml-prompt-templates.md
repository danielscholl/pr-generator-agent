# ADR-002: XML-Based Prompt Template System

## Status
**Accepted** - 2024-11-20

## Context
AIPR needs a flexible prompt system that allows users to customize how their pull request descriptions are generated. The system must support both built-in prompts and user-defined custom prompts while maintaining consistency and providing clear injection points for dynamic content (git changes and vulnerabilities).

## Decision
Use XML format for prompt templates with defined placeholders (`<changes-set>` and `<vulnerabilities-set>`) that are replaced with actual content at runtime. Prompts consist of `<system>` and `<user>` elements.

## Rationale
1. **Structure**: XML provides clear hierarchical structure for system/user prompts
2. **Validation**: Easy to validate required elements and structure
3. **Familiarity**: XML is widely understood and has good tooling support
4. **Flexibility**: Users can create complex prompts while maintaining standard injection points
5. **Separation**: Clear separation between static template and dynamic content

## Alternatives Considered
1. **YAML Format**
   - **Pros**: More human-readable, less verbose
   - **Cons**: Indentation sensitivity, less structure validation
   - **Decision**: Rejected due to potential formatting issues

2. **JSON Templates**
   - **Pros**: Native Python support, programmatic manipulation
   - **Cons**: Poor multi-line string support, less readable
   - **Decision**: Rejected due to readability concerns

3. **Jinja2 Templates**
   - **Pros**: Powerful templating features, conditionals
   - **Cons**: Over-complex for current needs, another dependency
   - **Decision**: Rejected as overkill for simple substitution

## Consequences
**Positive:**
- Clear contract for custom prompts
- Easy to validate prompt structure
- Simple placeholder replacement mechanism
- Version control friendly (diff-able)
- Can embed examples and complex instructions

**Negative:**
- XML verbosity
- Need to escape special XML characters
- Limited to simple substitution (no conditionals)

## Implementation Details
```xml
<prompt>
  <system>You are an AI assistant that creates pull request descriptions.</system>
  <user>
    Analyze these changes and create a description:

    <changes-set>
    <!-- Git diff content injected here -->
    </changes-set>

    <vulnerabilities-set>
    <!-- Security scan results injected here -->
    </vulnerabilities-set>
  </user>
</prompt>
```

## PromptManager Design
```python
class PromptManager:
    def __init__(self):
        self.builtin_prompts = self._load_builtin_prompts()

    def get_prompt(self, name: str, custom_path: str = None):
        if custom_path:
            return self._load_custom_prompt(custom_path)
        return self.builtin_prompts.get(name, self.builtin_prompts['default'])

    def prepare_prompt(self, template: dict, changes: str, vulns: str):
        user_prompt = template['user']
        user_prompt = user_prompt.replace('<changes-set>', changes)
        user_prompt = user_prompt.replace('<vulnerabilities-set>', vulns)
        return template['system'], user_prompt
```

## Validation Rules
1. Must have `<system>` element
2. Must have `<user>` element
3. User element must contain `<changes-set>` placeholder
4. `<vulnerabilities-set>` is optional
5. Raise `InvalidPromptError` with clear message on validation failure

## Success Criteria
- Users can create custom prompts in < 10 minutes
- Clear error messages for invalid prompts
- Built-in prompts cover common use cases
- Prompts are version-control friendly
