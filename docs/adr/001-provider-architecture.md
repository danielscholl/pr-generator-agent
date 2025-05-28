# ADR-001: Provider Architecture Pattern

## Status
**Accepted** - 2024-11-15

## Context
AIPR needs to support multiple AI providers (Anthropic, OpenAI, Azure OpenAI, Google Gemini) with different APIs, authentication methods, and model capabilities. We need a flexible architecture that allows easy addition of new providers while maintaining consistent behavior across all providers.

## Decision
Implement a function-based provider architecture where each provider has its own dedicated function (`call_anthropic()`, `call_openai()`, etc.) with a central routing function (`call_llm()`) that selects the appropriate provider based on the model string.

## Rationale
1. **Simplicity**: Function-based approach is straightforward and easy to understand
2. **Flexibility**: Each provider can have unique parameters without affecting others
3. **No Over-Engineering**: Avoids complex class hierarchies for a relatively simple use case
4. **Easy Testing**: Individual provider functions can be mocked independently
5. **Clear Separation**: Each provider's quirks are isolated in its own function

## Alternatives Considered
1. **Abstract Base Class with Provider Subclasses**
   - **Pros**: Better polymorphism, enforced interface contracts
   - **Cons**: Over-engineering for current needs, harder to handle provider-specific parameters
   - **Decision**: Rejected due to added complexity without clear benefits

2. **Single Function with Provider Switch**
   - **Pros**: All logic in one place
   - **Cons**: Would become a large, complex function; harder to test
   - **Decision**: Rejected due to maintainability concerns

## Consequences
**Positive:**
- Easy to add new providers (just add a new function and update router)
- Provider-specific handling is explicit and localized
- Simple to understand and debug
- Each provider can evolve independently

**Negative:**
- No enforced interface contract between providers
- Some code duplication across provider functions
- Manual routing logic needs maintenance

## Implementation Details
```python
def call_llm(model_name: str, system_prompt: str, user_prompt: str, temperature: float = 0.5):
    """Route to appropriate provider based on model name"""
    if "/" in model_name:
        provider = model_name.split("/")[0]
    else:
        # Use environment variables to detect provider
        provider = detect_provider(model_name)

    if provider == "anthropic":
        return call_anthropic(...)
    elif provider == "openai":
        return call_openai(...)
    # etc.
```

## Model Aliasing
To improve user experience, we implement model aliases:
- `"claude"` → `"claude-3-5-sonnet-20241022"`
- `"azure"` → `"gpt-4o"`
- `"openai"` → `"gpt-4o"`
- `"gemini"` → `"gemini-2.0-flash-exp"`

## Success Criteria
- New providers can be added in < 30 minutes
- Provider-specific bugs don't affect other providers
- Clear error messages when providers are misconfigured
