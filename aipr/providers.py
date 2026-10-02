import json
import os
from typing import Any, Dict, Optional

import anthropic
from openai import AzureOpenAI, OpenAI

# Output-token ceiling for every provider. On current Anthropic models
# adaptive thinking spends from the same budget as visible text, so this
# has to leave room for both; it is a cap, not a target.
MAX_OUTPUT_TOKENS = 16000

# Thinking depth for Anthropic models that accept output_config.effort.
# Commit messages and PR descriptions are short, single-shot classification
# and summarization tasks; "medium" keeps type/scope selection reliable
# without paying for deep reasoning on every diff.
ANTHROPIC_EFFORT = "medium"

# Beta header for the scalar fallbacks="default" form, which re-runs a
# request the safety classifiers declined on a fallback model server-side.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Models that reject sampling parameters (temperature returns a 400) and
# support adaptive thinking plus output_config.effort.
_ADAPTIVE_THINKING = ("claude-sonnet-5-5",)

# Models with refusal fallback targets published on /v1/models. Only these
# accept the fallbacks parameter; sending it elsewhere is a 400.
_HAS_FALLBACKS = ("claude-sonnet-5-5",)

# OpenAI model families that take max_completion_tokens and reject a custom
# temperature.
_OPENAI_REASONING = ("gpt-5", "gpt-6")


def _anthropic_extra_params(model: str) -> Dict[str, Any]:
    """Return per-model request parameters for Anthropic models.

    Any model added to aipr/main.py's Anthropic allowlist must be classified
    here, or it falls through to the temperature branch and every request
    to a current-generation model fails.

    Args:
        model: Resolved Anthropic model identifier.

    Returns:
        Extra keyword arguments to pass to the messages.create call.
    """
    if model.startswith(_ADAPTIVE_THINKING):
        return {
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": ANTHROPIC_EFFORT},
        }
    return {"temperature": 0.2}


def _anthropic_uses_fallbacks(model: str) -> bool:
    """Return True when the model publishes refusal fallback targets."""
    return model.startswith(_HAS_FALLBACKS)


def _format_api_error(error: Exception) -> str:
    """Return a one-line, human-readable message for an SDK exception.

    The SDK's default string embeds the raw JSON error body; prefer the
    server's message when the body carries one.
    """
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        message = (
            body.get("error", {}).get("message") if isinstance(body.get("error"), dict) else None
        )
        if message:
            status = getattr(error, "status_code", None)
            return f"{message} (HTTP {status})" if status else message
    return str(error)


def _extract_text(response: Any) -> str:
    """Return the visible text of a Messages API response.

    With thinking enabled the first content block is a thinking block, so
    content[0].text is wrong; join every text block instead. A refusal is
    surfaced as an error rather than an empty commit message.
    """
    stop_reason = getattr(response, "stop_reason", None)
    if stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        category = getattr(details, "category", None)
        suffix = f" (category: {category})" if category else ""
        raise ValueError(f"The model declined to generate a response{suffix}")

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    if stop_reason == "max_tokens":
        raise ValueError(
            f"Response was truncated at {MAX_OUTPUT_TOKENS} output tokens; "
            "try a smaller diff or commit range"
        )
    return text


def generate_with_anthropic(
    diff: str,
    vuln_data: Optional[Dict[str, Any]],
    model: str,
    system_prompt: str,
    verbose: bool = False,
) -> str:
    """Generate description using Anthropic's Claude."""
    if verbose:
        print("\nInitializing Anthropic client...")

    # Zero-arg client: the SDK resolves ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN.
    client = anthropic.Anthropic()
    extra_params = _anthropic_extra_params(model)
    use_fallbacks = _anthropic_uses_fallbacks(model)

    if verbose:
        print("\nSending request to Anthropic API:")
        print(f"  Model: {model}")
        shown = {"max_tokens": MAX_OUTPUT_TOKENS, **extra_params}
        if use_fallbacks:
            shown["fallbacks"] = "default"
        print("  Parameters:", json.dumps(shown, indent=2))
        print("\nRequest Messages:")
        print("\nSYSTEM MESSAGE:")
        print(system_prompt)
        print("\nUSER MESSAGE:")
        if len(diff) > 500:
            print(diff[:500] + "...")
        else:
            print(diff)
        print("\nMaking API call...")

    request = {
        "model": model,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "system": system_prompt,
        "messages": [{"role": "user", "content": diff}],
        **extra_params,
    }

    try:
        if use_fallbacks:
            response = client.beta.messages.create(
                betas=[_FALLBACK_BETA], fallbacks="default", **request
            )
        else:
            response = client.messages.create(**request)
        if verbose:
            print("\nRaw API Response:")
            print(f"  Model: {response.model}")
            print(f"  Stop reason: {response.stop_reason}")
            print(f"  Usage: {response.usage.model_dump() if response.usage else 'N/A'}")
            print("\nResponse Content:")
        return _extract_text(response)
    except anthropic.APIError as e:
        message = _format_api_error(e)
        if verbose:
            print(f"\nAPI Error: {message}")
        raise ValueError(f"Anthropic API error: {message}")
    except ValueError:
        raise
    except Exception as e:
        if verbose:
            print(f"\nAPI Error: {str(e)}")
        raise ValueError(f"Anthropic API error: {str(e)}")


def generate_with_azure_openai(
    diff: str,
    vuln_data: Optional[Dict[str, Any]],
    model: str,
    system_prompt: str,
    verbose: bool = False,
) -> str:
    """Generate description using Azure OpenAI."""
    # Check required environment variables
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_API_KEY")
    api_version = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")

    if not endpoint or not api_key:
        raise ValueError(
            "Missing Azure OpenAI configuration. "
            "Please set AZURE_OPENAI_ENDPOINT and AZURE_API_KEY environment variables."
        )

    try:
        if verbose:
            print("\nInitializing Azure OpenAI client with:")
            print(f"  Endpoint: {endpoint}")
            print(f"  API Version: {api_version}")

        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
        )

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": diff},
        ]

        # GPT-5 series models have special requirements:
        # - Use max_completion_tokens instead of max_tokens
        # - Only support default temperature (1.0), cannot customize
        # - Use reasoning tokens internally, need higher limits (reasoning + visible output)
        if model.startswith("gpt-5") or model.startswith("gpt-4.1"):
            kwargs = {
                "model": model,
                "messages": messages,
                "max_completion_tokens": MAX_OUTPUT_TOKENS,
                # temperature parameter not supported - uses default (1.0)
            }
        else:
            # Standard parameters for older models
            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "temperature": 0.2,
            }

        if verbose:
            print("\nSending request to Azure OpenAI API:")
            print(f"  Model: {model}")
            print(
                "  Parameters:",
                json.dumps({k: v for k, v in kwargs.items() if k != "messages"}, indent=2),
            )
            print("\nRequest Messages:")
            for msg in messages:
                print(f"\n{msg['role'].upper()} MESSAGE:")
                content = msg["content"]
                if len(content) > 500:
                    print(content[:500] + "...")
                else:
                    print(content)

        try:
            if verbose:
                print("\nMaking API call...")
            response = client.chat.completions.create(**kwargs)
            if not response.choices:
                raise ValueError("No completion choices returned from the API")
            if verbose:
                print("\nRaw API Response:")
                print(f"  Model: {response.model}")
                print(f"  Usage: {response.usage.model_dump() if response.usage else 'N/A'}")
                print("\nResponse Content:")
            return response.choices[0].message.content
        except Exception as api_error:
            error_msg = str(api_error)
            if verbose:
                print(f"\nAPI Error: {error_msg}")
            if "status" in error_msg:
                raise ValueError(f"Azure OpenAI API error (HTTP {error_msg})")
            raise ValueError(f"Azure OpenAI API error: {error_msg}")

    except Exception as e:
        if verbose:
            print(f"\nProvider Error: {str(e)}")
        raise ValueError(f"Azure OpenAI provider error: {str(e)}")


def generate_with_openai(
    diff: str,
    vuln_data: Optional[Dict[str, Any]],
    model: str,
    system_prompt: str,
    verbose: bool = False,
) -> str:
    """Generate description using OpenAI."""
    if verbose:
        print("\nInitializing OpenAI client...")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": diff},
    ]

    # GPT-5 and GPT-6 series models have special requirements (same as Azure GPT-5):
    # - Use max_completion_tokens instead of max_tokens
    # - Only support default temperature (1.0), cannot customize
    # - Use reasoning tokens internally, need higher limits (reasoning + visible output)
    if model.startswith(_OPENAI_REASONING):
        kwargs = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": MAX_OUTPUT_TOKENS,
            # temperature parameter not supported - uses default (1.0)
        }
    else:
        # Standard parameters for older models
        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.2,
        }

    if verbose:
        print("\nSending request to OpenAI API:")
        print(f"  Model: {model}")
        print(
            "  Parameters:",
            json.dumps({k: v for k, v in kwargs.items() if k != "messages"}, indent=2),
        )
        print("\nRequest Messages:")
        for msg in messages:
            print(f"\n{msg['role'].upper()} MESSAGE:")
            content = msg["content"]
            if len(content) > 500:
                print(content[:500] + "...")
            else:
                print(content)
        print("\nMaking API call...")

    try:
        response = client.chat.completions.create(**kwargs)
        if verbose:
            print("\nRaw API Response:")
            print(f"  Model: {response.model}")
            print(f"  Usage: {response.usage.model_dump() if response.usage else 'N/A'}")
            print("\nResponse Content:")
        return response.choices[0].message.content
    except Exception as e:
        if verbose:
            print(f"\nAPI Error: {str(e)}")
        raise ValueError(f"OpenAI API error: {str(e)}")


def generate_with_gemini(
    diff: str,
    vuln_data: Optional[Dict[str, Any]],
    model: str,
    system_prompt: str,
    verbose: bool = False,
) -> str:
    """Generate description using Google's Gemini."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ValueError(
            "Google Generative AI library not installed. "
            "Please install with: pip install google-generativeai"
        )

    if verbose:
        print("\nInitializing Gemini client...")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing Gemini API key. Please set GEMINI_API_KEY environment variable.")

    genai.configure(api_key=api_key)

    # Create messages in the format Gemini expects
    messages = [
        {
            "role": "user",
            "parts": [{"text": f"System instructions: {system_prompt}\n\n{diff}"}],
        },
    ]

    if verbose:
        print("\nSending request to Gemini API:")
        print(f"  Model: {model}")
        print("  Parameters:", json.dumps({"temperature": 0.2}, indent=2))
        print("\nRequest Messages:")
        for msg in messages:
            print(f"\n{msg['role'].upper()} MESSAGE:")
            content = msg["parts"][0]["text"]
            if len(content) > 500:
                print(content[:500] + "...")
            else:
                print(content)
        print("\nMaking API call...")

    try:
        model_instance = genai.GenerativeModel(model)
        response = model_instance.generate_content(
            messages,
            generation_config={"temperature": 0.2},
        )

        if verbose:
            print("\nRaw API Response:")
            print(f"  Model: {model}")
            print("\nResponse Content:")

        return response.text
    except Exception as e:
        if verbose:
            print(f"\nAPI Error: {str(e)}")
        raise ValueError(f"Gemini API error: {str(e)}")


def generate_with_xai(
    diff: str,
    vuln_data: Optional[Dict[str, Any]],
    model: str,
    system_prompt: str,
    verbose: bool = False,
) -> str:
    """Generate description using xAI's Grok models."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("Missing xAI API key. Please set XAI_API_KEY environment variable.")

    if verbose:
        print("\nInitializing xAI client...")

    # xAI uses OpenAI-compatible API format
    try:
        from openai import OpenAI
    except ImportError:
        raise ValueError(
            "OpenAI library required for xAI integration. Please install with: pip install openai"
        )

    # xAI API endpoint
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": diff},
    ]

    if verbose:
        print("\nSending request to xAI API:")
        print(f"  Model: {model}")
        print(
            "  Parameters:",
            json.dumps({"max_tokens": MAX_OUTPUT_TOKENS, "temperature": 0.2}, indent=2),
        )
        print("\nRequest Messages:")
        for msg in messages:
            print(f"\n{msg['role'].upper()} MESSAGE:")
            content = msg["content"]
            if len(content) > 500:
                print(content[:500] + "...")
            else:
                print(content)
        print("\nMaking API call...")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.2,
        )
        if verbose:
            print("\nRaw API Response:")
            print(f"  Model: {response.model}")
            print(f"  Usage: {response.usage.model_dump() if response.usage else 'N/A'}")
            print("\nResponse Content:")
        return response.choices[0].message.content
    except Exception as e:
        if verbose:
            print(f"\nAPI Error: {str(e)}")
        raise ValueError(f"xAI API error: {str(e)}")
