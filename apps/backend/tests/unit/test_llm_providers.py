"""Proves CIS Phase 4 Prompt 1's five ``LLMProvider`` adapters.

The four HTTP-based adapters (OpenAI/Anthropic/Gemini/Ollama) are
exercised against a real ``httpx.AsyncClient`` wired to
``httpx.MockTransport`` — real request construction (URL, headers,
JSON body shape) and real response parsing, without any live network
call (real provider endpoints are unreachable in this sandbox) — a
stronger proof than a hand-written fake `LLMProvider` would give, since
it catches a wrong header name or a misread response field the same
way a live integration test would. ``LocalProvider`` needs no HTTP
client at all and is tested directly.
"""

import json

import httpx
import pytest

from cerebrum.infrastructure.llm.anthropic_provider import AnthropicProvider
from cerebrum.infrastructure.llm.gemini_provider import GeminiProvider
from cerebrum.infrastructure.llm.local_provider import LocalProvider
from cerebrum.infrastructure.llm.ollama_provider import OllamaProvider
from cerebrum.infrastructure.llm.openai_provider import OpenAIProvider
from cerebrum.infrastructure.llm.provider import LLMMessage, LLMProviderError
from cerebrum.infrastructure.llm.registry import (
    available_providers,
    build_llm_provider,
)

pytestmark = pytest.mark.unit


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


_MESSAGES = [
    LLMMessage(role="system", content="You are helpful."),
    LLMMessage(role="user", content="What is Acme Corp?"),
]


# --- OpenAI ------------------------------------------------------------


async def test_openai_generate_parses_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer sk-test"
        body = json.loads(request.content)
        assert body["messages"][0] == {"role": "system", "content": "You are helpful."}
        assert body["stream"] is False
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": "Acme is a company."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 6},
                "model": "gpt-4o-mini",
            },
        )

    provider = OpenAIProvider(
        http_client=_client(handler),
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )

    response = await provider.generate(_MESSAGES)

    assert response.content == "Acme is a company."
    assert response.provider == "openai"
    assert response.usage.prompt_tokens == 12
    assert response.usage.completion_tokens == 6
    assert response.usage.total_tokens == 18
    assert response.finish_reason == "stop"


async def test_openai_generate_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    provider = OpenAIProvider(
        http_client=_client(handler),
        api_key="bad-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )

    with pytest.raises(LLMProviderError):
        await provider.generate(_MESSAGES)


async def test_openai_stream_yields_delta_tokens() -> None:
    sse_body = (
        b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
        b"data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        return httpx.Response(200, content=sse_body)

    provider = OpenAIProvider(
        http_client=_client(handler),
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )

    tokens = [token async for token in provider.stream(_MESSAGES)]

    assert tokens == ["Hello", " world"]


# --- Anthropic ------------------------------------------------------------


async def test_anthropic_generate_extracts_system_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "anthropic-key"
        body = json.loads(request.content)
        assert body["system"] == "You are helpful."
        assert body["messages"] == [{"role": "user", "content": "What is Acme Corp?"}]
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "Acme is a company."}],
                "model": "claude-3-5-haiku-20241022",
                "usage": {"input_tokens": 20, "output_tokens": 8},
                "stop_reason": "end_turn",
            },
        )

    provider = AnthropicProvider(
        http_client=_client(handler),
        api_key="anthropic-key",
        base_url="https://api.anthropic.com",
        default_model="claude-3-5-haiku-20241022",
    )

    response = await provider.generate(_MESSAGES)

    assert response.content == "Acme is a company."
    assert response.provider == "anthropic"
    assert response.usage.prompt_tokens == 20
    assert response.usage.completion_tokens == 8


async def test_anthropic_stream_yields_content_block_deltas() -> None:
    sse_body = (
        b'data: {"type":"message_start"}\n\n'
        b'data: {"type":"content_block_delta",'
        b'"delta":{"type":"text_delta","text":"Acme"}}\n\n'
        b'data: {"type":"content_block_delta",'
        b'"delta":{"type":"text_delta","text":" Corp"}}\n\n'
        b'data: {"type":"message_stop"}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse_body)

    provider = AnthropicProvider(
        http_client=_client(handler),
        api_key="anthropic-key",
        base_url="https://api.anthropic.com",
        default_model="claude-3-5-haiku-20241022",
    )

    tokens = [token async for token in provider.stream(_MESSAGES)]

    assert tokens == ["Acme", " Corp"]


# --- Gemini ------------------------------------------------------------


async def test_gemini_generate_uses_query_param_key_and_system_instruction() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["key"] == "gemini-key"
        assert "gemini-1.5-flash:generateContent" in str(request.url)
        body = json.loads(request.content)
        assert body["systemInstruction"] == {"parts": [{"text": "You are helpful."}]}
        assert body["contents"] == [
            {"role": "user", "parts": [{"text": "What is Acme Corp?"}]}
        ]
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "Acme is a company."}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 15,
                    "candidatesTokenCount": 7,
                },
            },
        )

    provider = GeminiProvider(
        http_client=_client(handler),
        api_key="gemini-key",
        base_url="https://generativelanguage.googleapis.com",
        default_model="gemini-1.5-flash",
    )

    response = await provider.generate(_MESSAGES)

    assert response.content == "Acme is a company."
    assert response.usage.prompt_tokens == 15
    assert response.usage.completion_tokens == 7


async def test_gemini_stream_yields_candidate_text() -> None:
    sse_body = (
        b'data: {"candidates":[{"content":{"parts":[{"text":"Acme"}]}}]}\n\n'
        b'data: {"candidates":[{"content":{"parts":[{"text":" Corp"}]}}]}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert "alt=sse" in str(request.url)
        return httpx.Response(200, content=sse_body)

    provider = GeminiProvider(
        http_client=_client(handler),
        api_key="gemini-key",
        base_url="https://generativelanguage.googleapis.com",
        default_model="gemini-1.5-flash",
    )

    tokens = [token async for token in provider.stream(_MESSAGES)]

    assert tokens == ["Acme", " Corp"]


# --- Ollama ------------------------------------------------------------


async def test_ollama_generate_parses_single_json_object() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        body = json.loads(request.content)
        assert body["stream"] is False
        return httpx.Response(
            200,
            json={
                "model": "llama3.1",
                "message": {"role": "assistant", "content": "Acme is a company."},
                "done": True,
                "prompt_eval_count": 9,
                "eval_count": 4,
                "done_reason": "stop",
            },
        )

    provider = OllamaProvider(
        http_client=_client(handler),
        base_url="http://localhost:11434",
        default_model="llama3.1",
    )

    response = await provider.generate(_MESSAGES)

    assert response.content == "Acme is a company."
    assert response.usage.prompt_tokens == 9
    assert response.usage.completion_tokens == 4


async def test_ollama_stream_yields_message_content_until_done() -> None:
    ndjson_body = (
        b'{"message":{"content":"Acme"},"done":false}\n'
        b'{"message":{"content":" Corp"},"done":false}\n'
        b'{"message":{"content":""},"done":true}\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=ndjson_body)

    provider = OllamaProvider(
        http_client=_client(handler),
        base_url="http://localhost:11434",
        default_model="llama3.1",
    )

    tokens = [token async for token in provider.stream(_MESSAGES)]

    assert tokens == ["Acme", " Corp"]


# --- Local ------------------------------------------------------------


def _local_messages(context: str, question: str) -> list[LLMMessage]:
    return [
        LLMMessage(role="system", content="system prompt"),
        LLMMessage(role="user", content=f"{context}\n\nQuestion: {question}"),
    ]


async def test_local_generate_selects_overlapping_sentence() -> None:
    provider = LocalProvider()
    context = "Acme Corp makes widgets. Bob works at Acme Corp. The sky is blue."
    messages = _local_messages(context, "What does Acme Corp make?")

    response = await provider.generate(messages)

    assert "widgets" in response.content
    assert response.provider == "local"
    assert response.finish_reason == "stop"
    assert response.usage.prompt_tokens > 0


async def test_local_generate_falls_back_when_nothing_overlaps() -> None:
    provider = LocalProvider()
    context = "Acme Corp makes widgets."
    messages = _local_messages(context, "What is the capital of France?")

    response = await provider.generate(messages)

    assert "No sentence" in response.content


async def test_local_stream_yields_the_same_text_as_generate() -> None:
    provider = LocalProvider()
    context = "Acme Corp makes widgets."
    messages = _local_messages(context, "What does Acme Corp make?")

    generated = await provider.generate(messages)
    streamed = "".join([token async for token in provider.stream(messages)])

    assert streamed.strip() == generated.content.strip()


async def test_local_generate_handles_no_question() -> None:
    provider = LocalProvider()

    response = await provider.generate([LLMMessage(role="system", content="hi")])

    assert "No question" in response.content


# --- Registry ------------------------------------------------------------


def test_available_providers_always_includes_local_and_ollama() -> None:
    from cerebrum.config.ai import AISettings

    settings = AISettings(
        openai_api_key=None, anthropic_api_key=None, gemini_api_key=None
    )

    names = available_providers(settings)

    assert names == ["local", "ollama"]


def test_available_providers_includes_configured_keys() -> None:
    from cerebrum.config.ai import AISettings

    settings = AISettings(openai_api_key="sk-test")

    names = available_providers(settings)

    assert "openai" in names


def test_build_llm_provider_local_needs_no_key() -> None:
    from cerebrum.config.ai import AISettings

    provider = build_llm_provider(
        "local",
        settings=AISettings(),
        http_client=_client(lambda r: httpx.Response(200)),
    )

    assert provider.name == "local"


def test_build_llm_provider_raises_for_unconfigured_provider() -> None:
    from cerebrum.config.ai import AISettings
    from cerebrum.shared.errors.exceptions import ValidationException

    with pytest.raises(ValidationException):
        build_llm_provider(
            "openai",
            settings=AISettings(openai_api_key=None),
            http_client=_client(lambda r: httpx.Response(200)),
        )


def test_build_llm_provider_raises_for_unknown_name() -> None:
    from cerebrum.config.ai import AISettings
    from cerebrum.shared.errors.exceptions import ValidationException

    with pytest.raises(ValidationException):
        build_llm_provider(
            "not-a-real-provider",
            settings=AISettings(),
            http_client=_client(lambda r: httpx.Response(200)),
        )
