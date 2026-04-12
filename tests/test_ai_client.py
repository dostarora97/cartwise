"""Unit tests for the AI client layer."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.client import _model_string, generate


def test_model_string_ollama(monkeypatch):
    monkeypatch.setattr("app.ai.client.settings", _FakeAISettings("ollama", "qwen2.5:3b"))
    assert _model_string() == "ollama/qwen2.5:3b"


def test_model_string_anthropic(monkeypatch):
    monkeypatch.setattr("app.ai.client.settings", _FakeAISettings("anthropic", "claude-3-haiku"))
    assert _model_string() == "anthropic/claude-3-haiku"


def test_model_string_openai_no_prefix(monkeypatch):
    monkeypatch.setattr("app.ai.client.settings", _FakeAISettings("openai", "gpt-4o-mini"))
    assert _model_string() == "gpt-4o-mini"


async def test_generate_calls_litellm_and_parses_json(monkeypatch):
    monkeypatch.setattr(
        "app.ai.client.settings",
        _FakeAISettings("ollama", "test-model", "http://localhost:11434", ""),
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"category": "item"}'

    with patch("app.ai.client.litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        mock_acomp.return_value = mock_response

        result = await generate(
            system="classify this",
            prompt="Classify: {row}",
            schema={"type": "object", "properties": {"category": {"type": "string"}}},
        )

    assert result == {"category": "item"}
    mock_acomp.assert_called_once()

    # Verify the call shape
    call_kwargs = mock_acomp.call_args
    assert call_kwargs.kwargs["model"] == "ollama/test-model"
    assert len(call_kwargs.kwargs["messages"]) == 2
    assert call_kwargs.kwargs["messages"][0]["role"] == "system"
    assert call_kwargs.kwargs["messages"][1]["role"] == "user"


class _FakeAISettings:
    def __init__(self, provider="ollama", model="test", base_url="", api_key=""):
        self.AI_PROVIDER = provider
        self.AI_MODEL = model
        self.AI_BASE_URL = base_url
        self.AI_API_KEY = api_key
