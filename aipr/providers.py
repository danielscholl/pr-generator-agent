import json
import os
from typing import Any, Dict, Optional

import anthropic
from openai import AzureOpenAI, OpenAI


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

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    if verbose:
        print("\nSending request to Anthropic API:")
        print(f"  Model: {model}")
        print(
            "  Parameters:",
            json.dumps({"max_tokens": 1000, "temperature": 0.2}, indent=2),
        )
        print("\nRequest Messages:")
        print("\nSYSTEM MESSAGE:")
        print(system_prompt)
        print("\nUSER MESSAGE:")
        if len(diff) > 500:
            print(diff[:500] + "...")
        else:
            print(diff)
        print("\nMaking API call...")

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            temperature=0.2,
            system=system_prompt,
            messages=[{"role": "user", "content": diff}],
        )
        if verbose:
            print("\nRaw API Response:")
            print(f"  Model: {response.model}")
            print(f"  Usage: {response.usage.model_dump() if response.usage else 'N/A'}")
            print("\nResponse Content:")
        return response.content[0].text
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

    if not endpoint or not api_key:
        raise ValueError(
            "Missing Azure OpenAI configuration. "
            "Please set AZURE_OPENAI_ENDPOINT and AZURE_API_KEY environment variables."
        )

    try:
        if verbose:
            print("\nInitializing Azure OpenAI client with:")
            print(f"  Endpoint: {endpoint}")
            print("  API Version: 2024-02-15-preview")

        client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-02-15-preview",
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
                "max_completion_tokens": 8000,  # Higher limit for reasoning + output
                # temperature parameter not supported - uses default (1.0)
            }
        else:
            # Standard parameters for older models
            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": 1000,
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

    # GPT-5 series models have special requirements (same as Azure GPT-5):
    # - Use max_completion_tokens instead of max_tokens
    # - Only support default temperature (1.0), cannot customize
    # - Use reasoning tokens internally, need higher limits (reasoning + visible output)
    if model.startswith("gpt-5"):
        kwargs = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": 8000,  # Higher limit for reasoning + output
            # temperature parameter not supported - uses default (1.0)
        }
    else:
        # Standard parameters for older models
        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": 1000,
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
            json.dumps({"max_tokens": 1000, "temperature": 0.2}, indent=2),
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
            max_tokens=1000,
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
