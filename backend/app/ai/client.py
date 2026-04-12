"""
Unified AI client using LiteLLM.

Wraps litellm.acompletion to provide a single async interface for all
LLM providers. The model and provider are configured via Dynaconf settings:

  AI_PROVIDER = "ollama"       # or "anthropic", "openai", etc.
  AI_MODEL = "qwen2.5:3b"     # provider-specific model name
  AI_BASE_URL = "http://..."   # only needed for local providers
  AI_API_KEY = ""              # only needed for cloud providers
"""

import json

import litellm

from app.config import settings


def _model_string() -> str:
    """Build the LiteLLM model string from config.

    LiteLLM uses format: "provider/model" for most providers.
    e.g. "ollama/qwen2.5:3b", "anthropic/claude-3-haiku-20240307", "gpt-4o-mini"
    """
    provider = settings.AI_PROVIDER
    model = settings.AI_MODEL

    if provider == "openai":
        return model  # OpenAI models don't need a prefix
    return f"{provider}/{model}"


async def generate(
    system: str,
    prompt: str,
    schema: dict,
) -> dict:
    """Send a prompt to the configured LLM and get structured JSON back.

    Args:
        system: System prompt.
        prompt: User prompt.
        schema: JSON schema for the expected output.

    Returns:
        Parsed dict from the LLM's JSON response.
    """
    response = await litellm.acompletion(
        model=_model_string(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "schema": schema,
            },
        },
        api_base=settings.AI_BASE_URL or None,
        api_key=settings.AI_API_KEY or None,
    )

    content = response.choices[0].message.content
    return json.loads(content)
