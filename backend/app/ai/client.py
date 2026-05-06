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
import logfire
import structlog
from opentelemetry import trace

from app.config import settings

logger = structlog.get_logger()


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


@logfire.instrument("llm_call {model}")
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
    model = _model_string()

    logger.info(
        "llm_request",
        model=model,
        system_prompt=system,
        user_prompt=prompt,
        response_schema=schema,
    )

    try:
        response = await litellm.acompletion(
            model=model,
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
    except Exception as exc:
        logger.info(
            "llm_error",
            model=model,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise

    content = response.choices[0].message.content

    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)

    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.set_attribute("llm.prompt_tokens", prompt_tokens or 0)
        current_span.set_attribute("llm.completion_tokens", completion_tokens or 0)

    logger.info(
        "llm_response",
        model=model,
        response_content=content,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    return json.loads(content)
