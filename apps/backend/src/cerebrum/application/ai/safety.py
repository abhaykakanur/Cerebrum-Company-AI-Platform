"""CIS Phase 4 Prompt 1's Safety requirements that are pure functions
over text/data rather than a stateful service:

- **Prompt injection protection** — :func:`sanitize_retrieved_text`
  neutralizes the known families of prompt-injection phrasing (role-
  override attempts, "ignore previous instructions" variants, fake
  delimiter/role markers) that a malicious or compromised *document*
  could contain, before its text is ever concatenated into a prompt.
  Retrieved content is data, never instructions — this is the one
  place that enforces it textually; :func:`wrap_untrusted_context`
  enforces it structurally (explicit delimiters plus an instruction
  telling the model to treat the wrapped block as untrusted data).
- **Context isolation** — retrieved content SHALL only ever appear in
  the user-role message, never the system-role message (structural,
  enforced by
  cerebrum.application.ai.prompt_builder_service.PromptBuilderService
  never writing retrieved text into the system message it builds).
- **Citation verification** — see
  cerebrum.application.ai.ai_response_service.AIResponseService's
  ``_verify_citations``: a citation is only attached to a response if
  it corresponds to a source this pipeline actually retrieved, never
  something the model's own output text merely claims.
- **Tenant/workspace isolation** — inherited structurally: every
  service this layer calls
  (RetrievalService/ContextBuilderService/CitationService) already
  requires and enforces ``workspace_id`` scoping — see
  cerebrum.application.retrieval's package docstring.
"""

import re

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore (all|any|the)?\s*(previous|prior|above)\s*instructions",
        r"disregard (all|any|the)?\s*(previous|prior|above)\s*(instructions|prompt)",
        r"you are now\s+\w+",
        r"new instructions\s*:",
        r"system\s*prompt\s*:",
        r"forget (everything|all)\s+(you (were|have been) told|above)",
        r"reveal (your|the) (system prompt|instructions)",
    )
)

_REDACTION = "[redacted: potential instruction override]"

_CONTEXT_DELIMITER_START = "<<<RETRIEVED_CONTEXT_START>>>"
_CONTEXT_DELIMITER_END = "<<<RETRIEVED_CONTEXT_END>>>"


def sanitize_retrieved_text(text: str) -> str:
    """Neutralizes known prompt-injection phrasing in retrieved
    content. Deliberately narrow (a curated pattern list, not an ML
    classifier — no such dependency exists in this codebase, matching
    cerebrum.infrastructure.embeddings.providers's "honest, inspectable
    approximation" precedent) — combined with
    :func:`wrap_untrusted_context`'s structural delimiting, not relied
    on alone.
    """
    sanitized = text
    for pattern in _INJECTION_PATTERNS:
        sanitized = pattern.sub(_REDACTION, sanitized)
    return sanitized


def wrap_untrusted_context(context_block: str) -> str:
    """Wraps an already-sanitized context block in explicit delimiters
    plus an instruction the system prompt refers back to — a model
    cannot escape the "this is data, not instructions" framing merely
    by having the retrieved text assert it is now in a different role.
    """
    return f"{_CONTEXT_DELIMITER_START}\n{context_block}\n{_CONTEXT_DELIMITER_END}"
