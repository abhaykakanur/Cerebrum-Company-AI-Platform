"""Minimal Server-Sent-Events line parsing shared by the OpenAI,
Anthropic, and Gemini adapters (all three stream chat completions as
``text/event-stream``, per each provider's own streaming API docs) —
kept separate from any one provider module since it is genuinely
provider-independent (just the SSE wire format, RFC-defined, not
implied by any provider's response *shape*).
"""

from collections.abc import AsyncIterator

import httpx


async def iter_sse_data(response: httpx.Response) -> AsyncIterator[str]:
    """Yields the ``data:`` payload of every SSE event in
    ``response``'s body, stripped of the ``data:`` prefix and leading
    space. Blank lines (event separators) and non-``data:`` fields
    (``event:``, ``id:``, comments) are skipped — no provider this
    package supports uses them for content.
    """
    async for line in response.aiter_lines():
        if not line or not line.startswith("data:"):
            continue
        yield line[len("data:") :].strip()
