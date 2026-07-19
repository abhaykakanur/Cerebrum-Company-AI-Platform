"""CIS Phase 5 Prompt 2's Workflow Step executors — the reusable step
abstractions that call directly into an already-existing application
service: Connector Action ->
cerebrum.application.connectors.connector_sync_service.ConnectorSyncService,
AI Reasoning -> cerebrum.application.ai.rag_service.RAGService,
Retrieval -> cerebrum.application.retrieval.retrieval_service.RetrievalService,
Search -> cerebrum.application.semantic.search_service.SearchService.
"Reuse all existing services... do not duplicate connector, retrieval,
reasoning or AI logic" — this module is the one place a workflow step
adapts an existing service's call signature to the uniform
:class:`StepExecutor` shape; it contains no retrieval/reasoning/sync
logic of its own.

``condition``/``delay``/``parallel`` are control flow, not represented
here — see
cerebrum.application.workflows.workflow_run_service.WorkflowRunService's
module docstring for why they are handled by the execution engine
itself instead.

``Notification`` has no concrete delivery channel (email/Slack/Teams)
wired at this milestone — see cerebrum.workers's "interfaces only"
precedent for the same honest scoping — so
:class:`NotificationStepExecutor` records the notification's channel
and message as its step output rather than delivering it anywhere.
``Custom`` is a named extension point with an empty handler registry by
default — no custom handlers ship yet.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from cerebrum.application.ai.rag_service import RAGService
from cerebrum.application.connectors.connector_sync_service import ConnectorSyncService
from cerebrum.application.retrieval.retrieval_service import (
    RetrievalService,
    RetrievalStrategy,
)
from cerebrum.application.semantic.search_service import SearchService
from cerebrum.application.workflows.template import ExecutionContext, resolve_value
from cerebrum.config.ai import AISettings
from cerebrum.infrastructure.database.models.connector_sync_run import SyncType
from cerebrum.infrastructure.llm.registry import build_llm_provider
from cerebrum.shared.errors.exceptions import (
    NotFoundException,
    ValidationException,
)


class StepExecutionError(Exception):
    """Raised by a step executor when its underlying service call
    fails — caught by
    cerebrum.application.workflows.workflow_run_service.WorkflowRunService's
    per-step retry loop, mirroring
    cerebrum.infrastructure.connectors.base.ConnectorError's identical
    role for connector adapters.
    """


@dataclass(frozen=True, slots=True)
class StepOutcome:
    output: dict[str, Any] = field(default_factory=dict)


class StepExecutor(Protocol):
    async def execute(
        self,
        config: dict[str, Any],
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> StepOutcome: ...


def _require(resolved: dict[str, Any], key: str, step_kind: str) -> Any:
    value = resolved.get(key)
    if value in (None, ""):
        raise StepExecutionError(f"{step_kind} step requires '{key}'.")
    return value


class ConnectorActionStepExecutor:
    """config: ``{"connector_id": <uuid str>, "sync_type": <"incremental"|
    "manual"|"full_resync", optional, default "manual">}``. The only
    supported action at this milestone is running a sync — see this
    module's docstring.
    """

    def __init__(self, *, connector_sync_service: ConnectorSyncService) -> None:
        self._sync_service = connector_sync_service

    async def execute(
        self,
        config: dict[str, Any],
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> StepOutcome:
        resolved = resolve_value(config, context)
        connector_id = uuid.UUID(
            str(_require(resolved, "connector_id", "connector_action"))
        )
        sync_type = SyncType(resolved.get("sync_type", SyncType.MANUAL.value))
        try:
            run = await self._sync_service.start_sync(
                connector_id,
                workspace_id=workspace_id,
                triggered_by=triggered_by,
                sync_type=sync_type,
            )
        except (NotFoundException, ValidationException) as exc:
            raise StepExecutionError(str(exc)) from exc
        return StepOutcome(
            output={
                "sync_run_id": str(run.id),
                "status": run.status,
                "items_processed": run.items_processed,
                "items_failed": run.items_failed,
            }
        )


class AIReasoningStepExecutor:
    """config: ``{"question": <str>, "provider": <str, optional>,
    "strategy": <str, optional>, "model": <str, optional>, "limit":
    <int, optional>}``.
    """

    def __init__(
        self,
        *,
        rag_service: RAGService,
        ai_settings: AISettings,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._rag = rag_service
        self._ai_settings = ai_settings
        self._http_client = http_client

    async def execute(
        self,
        config: dict[str, Any],
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> StepOutcome:
        resolved = resolve_value(config, context)
        question = str(_require(resolved, "question", "ai_reasoning"))
        provider_name = resolved.get("provider") or self._ai_settings.default_provider
        try:
            provider = build_llm_provider(
                provider_name, settings=self._ai_settings, http_client=self._http_client
            )
            strategy = RetrievalStrategy(
                resolved.get("strategy", RetrievalStrategy.HYBRID.value)
            )
            answer = await self._rag.ask(
                question,
                workspace_id=workspace_id,
                provider=provider,
                strategy=strategy,
                model=resolved.get("model"),
                limit=int(resolved.get("limit", 10)),
            )
        except (ValidationException, ValueError) as exc:
            raise StepExecutionError(str(exc)) from exc
        return StepOutcome(
            output={
                "answer": answer.answer,
                "citation_count": len(answer.citations),
                "confidence": answer.confidence.overall,
                "provider": answer.provider,
                "model": answer.model,
            }
        )


class RetrievalStepExecutor:
    """config: ``{"query": <str>, "strategy": <str, optional>, "limit":
    <int, optional>}``.
    """

    def __init__(self, *, retrieval_service: RetrievalService) -> None:
        self._retrieval = retrieval_service

    async def execute(
        self,
        config: dict[str, Any],
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> StepOutcome:
        resolved = resolve_value(config, context)
        query_text = str(_require(resolved, "query", "retrieval"))
        try:
            strategy = RetrievalStrategy(
                resolved.get("strategy", RetrievalStrategy.HYBRID.value)
            )
            result = await self._retrieval.retrieve(
                query_text,
                workspace_id=workspace_id,
                strategy=strategy,
                limit=int(resolved.get("limit", 10)),
            )
        except ValueError as exc:
            raise StepExecutionError(str(exc)) from exc
        return StepOutcome(
            output={
                "hit_count": len(result.hits),
                "hits": [
                    {
                        "source_id": hit.source_id,
                        "kind": hit.kind,
                        "title": hit.title,
                        "snippet": hit.snippet,
                        "score": hit.fused_score,
                    }
                    for hit in result.hits[:20]
                ],
            }
        )


class SearchStepExecutor:
    """config: ``{"query": <str>, "limit": <int, optional>}``."""

    def __init__(self, *, search_service: SearchService) -> None:
        self._search = search_service

    async def execute(
        self,
        config: dict[str, Any],
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> StepOutcome:
        resolved = resolve_value(config, context)
        query_text = str(_require(resolved, "query", "search"))
        result = await self._search.search(
            query_text=query_text,
            workspace_id=workspace_id,
            limit=int(resolved.get("limit", 10)),
        )
        return StepOutcome(output=result)


class NotificationStepExecutor:
    """config: ``{"channel": <str, optional, default "log">, "message": <str>}``.
    See this module's docstring: no concrete delivery channel exists
    yet, so the recorded output *is* the delivery — a future channel
    adapter changes what this executor does, not a workflow's
    definition.
    """

    async def execute(
        self,
        config: dict[str, Any],
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> StepOutcome:
        resolved = resolve_value(config, context)
        message = str(_require(resolved, "message", "notification"))
        channel = str(resolved.get("channel", "log"))
        return StepOutcome(
            output={"channel": channel, "message": message, "sent": True}
        )


CustomStepHandler = Callable[
    [dict[str, Any], ExecutionContext], Awaitable[dict[str, Any]]
]


class CustomStepExecutor:
    """config: ``{"handler": <registered name>, "params": <dict, optional>}``.
    ``handlers`` is empty by default — no custom step handlers ship at
    this milestone; this is the named extension point a future
    integration registers into.
    """

    def __init__(self, *, handlers: dict[str, CustomStepHandler] | None = None) -> None:
        self._handlers = handlers or {}

    async def execute(
        self,
        config: dict[str, Any],
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> StepOutcome:
        resolved = resolve_value(config, context)
        handler_name = str(_require(resolved, "handler", "custom"))
        handler = self._handlers.get(handler_name)
        if handler is None:
            raise StepExecutionError(
                f"No custom step handler registered as '{handler_name}'."
            )
        output = await handler(resolved.get("params", {}), context)
        return StepOutcome(output=output)
