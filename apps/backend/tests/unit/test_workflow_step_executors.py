"""Proves CIS Phase 5 Prompt 2's Workflow Step executors
(cerebrum.application.workflows.step_executors) call into the exact
existing service each is documented to reuse, with the config
resolved through :func:`~cerebrum.application.workflows.template.resolve_value`
first — each test fakes only the one underlying service that step type
wraps (``ConnectorSyncService``/``RAGService``/``RetrievalService``/
``SearchService``), never re-implements its behavior.
"""

import uuid
from dataclasses import dataclass, field

import pytest

from cerebrum.application.ai.ai_response_service import ConfidenceBreakdown, RAGAnswer
from cerebrum.application.retrieval.retrieval_service import RetrievalResult
from cerebrum.application.semantic.hybrid_search_service import SearchHit
from cerebrum.application.workflows.step_executors import (
    AIReasoningStepExecutor,
    ConnectorActionStepExecutor,
    CustomStepExecutor,
    NotificationStepExecutor,
    RetrievalStepExecutor,
    SearchStepExecutor,
    StepExecutionError,
)
from cerebrum.application.workflows.template import ExecutionContext
from cerebrum.config.ai import AISettings
from cerebrum.infrastructure.database.models.connector_sync_run import SyncType
from cerebrum.shared.errors.exceptions import NotFoundException

pytestmark = pytest.mark.unit


@dataclass
class _FakeSyncRun:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: str = "completed"
    items_processed: int = 3
    items_failed: int = 0


class _FakeConnectorSyncService:
    def __init__(self, *, raises: Exception | None = None) -> None:
        self.raises = raises
        self.calls: list[dict] = []

    async def start_sync(self, connector_id, *, workspace_id, triggered_by, sync_type):  # type: ignore[no-untyped-def]
        self.calls.append(
            {
                "connector_id": connector_id,
                "workspace_id": workspace_id,
                "triggered_by": triggered_by,
                "sync_type": sync_type,
            }
        )
        if self.raises is not None:
            raise self.raises
        return _FakeSyncRun()


async def test_connector_action_executor_starts_sync() -> None:
    connector_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    fake = _FakeConnectorSyncService()
    executor = ConnectorActionStepExecutor(connector_sync_service=fake)  # type: ignore[arg-type]

    outcome = await executor.execute(
        {"connector_id": str(connector_id), "sync_type": "full_resync"},
        workspace_id=workspace_id,
        triggered_by=None,
        context=ExecutionContext(),
    )

    assert outcome.output["status"] == "completed"
    assert outcome.output["items_processed"] == 3
    assert fake.calls[0]["connector_id"] == connector_id
    assert fake.calls[0]["sync_type"] == SyncType.FULL_RESYNC


async def test_connector_action_executor_resolves_templated_connector_id() -> None:
    connector_id = uuid.uuid4()
    fake = _FakeConnectorSyncService()
    executor = ConnectorActionStepExecutor(connector_sync_service=fake)  # type: ignore[arg-type]
    context = ExecutionContext(variables={"target": str(connector_id)})

    await executor.execute(
        {"connector_id": "{{ variables.target }}"},
        workspace_id=uuid.uuid4(),
        triggered_by=None,
        context=context,
    )

    assert fake.calls[0]["connector_id"] == connector_id


async def test_connector_action_executor_requires_connector_id() -> None:
    fake_sync_service = _FakeConnectorSyncService()
    executor = ConnectorActionStepExecutor(connector_sync_service=fake_sync_service)  # type: ignore[arg-type]
    with pytest.raises(StepExecutionError):
        await executor.execute(
            {}, workspace_id=uuid.uuid4(), triggered_by=None, context=ExecutionContext()
        )


async def test_connector_action_executor_wraps_service_errors() -> None:
    fake = _FakeConnectorSyncService(raises=NotFoundException("no such connector"))
    executor = ConnectorActionStepExecutor(connector_sync_service=fake)  # type: ignore[arg-type]
    with pytest.raises(StepExecutionError):
        await executor.execute(
            {"connector_id": str(uuid.uuid4())},
            workspace_id=uuid.uuid4(),
            triggered_by=None,
            context=ExecutionContext(),
        )


def _rag_answer(answer_text: str = "The answer.") -> RAGAnswer:
    return RAGAnswer(
        answer=answer_text,
        citations=[],
        confidence=ConfidenceBreakdown(
            retrieval_confidence=0.9,
            citation_coverage=0.8,
            context_completeness=0.7,
            source_diversity=0.6,
            overall=0.75,
        ),
        strategy="hybrid",
        provider="local",
        model="local-extractive-v1",
        prompt_tokens=10,
        completion_tokens=5,
        context_truncated=False,
        all_retrieved_citations=[],
    )


class _FakeRAGService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def ask(self, question, *, workspace_id, provider, strategy, model, limit):  # type: ignore[no-untyped-def]
        self.calls.append(
            {"question": question, "provider": provider.name, "limit": limit}
        )
        return _rag_answer(f"Answer to: {question}")


async def test_ai_reasoning_executor_calls_rag_service() -> None:
    fake_rag = _FakeRAGService()
    executor = AIReasoningStepExecutor(
        rag_service=fake_rag,  # type: ignore[arg-type]
        ai_settings=AISettings(),
        http_client=None,  # type: ignore[arg-type]
    )

    outcome = await executor.execute(
        {"question": "What is Cerebrum?"},
        workspace_id=uuid.uuid4(),
        triggered_by=None,
        context=ExecutionContext(),
    )

    assert outcome.output["answer"] == "Answer to: What is Cerebrum?"
    assert outcome.output["provider"] == "local"
    assert fake_rag.calls[0]["provider"] == "local"


async def test_ai_reasoning_executor_requires_question() -> None:
    executor = AIReasoningStepExecutor(
        rag_service=_FakeRAGService(),  # type: ignore[arg-type]
        ai_settings=AISettings(),
        http_client=None,  # type: ignore[arg-type]
    )
    with pytest.raises(StepExecutionError):
        await executor.execute(
            {}, workspace_id=uuid.uuid4(), triggered_by=None, context=ExecutionContext()
        )


class _FakeRetrievalService:
    async def retrieve(self, query_text, *, workspace_id, strategy, limit):  # type: ignore[no-untyped-def]
        return RetrievalResult(
            hits=[
                SearchHit(
                    source_id="doc-1",
                    kind="document",
                    title="Q1 report",
                    snippet="revenue grew",
                    fused_score=0.9,
                    vector_score=0.9,
                    keyword_score=None,
                    citation=None,  # type: ignore[arg-type]
                )
            ],
            strategy=strategy,
            query_text=query_text,
        )


async def test_retrieval_executor_calls_retrieval_service() -> None:
    executor = RetrievalStepExecutor(retrieval_service=_FakeRetrievalService())  # type: ignore[arg-type]

    outcome = await executor.execute(
        {"query": "revenue"},
        workspace_id=uuid.uuid4(),
        triggered_by=None,
        context=ExecutionContext(),
    )

    assert outcome.output["hit_count"] == 1
    assert outcome.output["hits"][0]["title"] == "Q1 report"


async def test_retrieval_executor_rejects_unknown_strategy() -> None:
    executor = RetrievalStepExecutor(retrieval_service=_FakeRetrievalService())  # type: ignore[arg-type]
    with pytest.raises(StepExecutionError):
        await executor.execute(
            {"query": "revenue", "strategy": "not_a_real_strategy"},
            workspace_id=uuid.uuid4(),
            triggered_by=None,
            context=ExecutionContext(),
        )


class _FakeSearchService:
    async def search(self, *, query_text, workspace_id, limit):  # type: ignore[no-untyped-def]
        return {"total": 1, "results": [{"id": "doc-1", "title": query_text}]}


async def test_search_executor_calls_search_service() -> None:
    executor = SearchStepExecutor(search_service=_FakeSearchService())  # type: ignore[arg-type]

    outcome = await executor.execute(
        {"query": "acme"},
        workspace_id=uuid.uuid4(),
        triggered_by=None,
        context=ExecutionContext(),
    )

    assert outcome.output == {"total": 1, "results": [{"id": "doc-1", "title": "acme"}]}


async def test_notification_executor_records_channel_and_message() -> None:
    executor = NotificationStepExecutor()

    outcome = await executor.execute(
        {"channel": "ops", "message": "Sync finished"},
        workspace_id=uuid.uuid4(),
        triggered_by=None,
        context=ExecutionContext(),
    )

    assert outcome.output == {
        "channel": "ops",
        "message": "Sync finished",
        "sent": True,
    }


async def test_notification_executor_requires_message() -> None:
    executor = NotificationStepExecutor()
    with pytest.raises(StepExecutionError):
        await executor.execute(
            {}, workspace_id=uuid.uuid4(), triggered_by=None, context=ExecutionContext()
        )


async def test_custom_executor_dispatches_to_registered_handler() -> None:
    async def handler(params, context):  # type: ignore[no-untyped-def]
        return {"echoed": params}

    executor = CustomStepExecutor(handlers={"echo": handler})

    outcome = await executor.execute(
        {"handler": "echo", "params": {"value": 42}},
        workspace_id=uuid.uuid4(),
        triggered_by=None,
        context=ExecutionContext(),
    )

    assert outcome.output == {"echoed": {"value": 42}}


async def test_custom_executor_raises_for_unregistered_handler() -> None:
    executor = CustomStepExecutor()
    with pytest.raises(StepExecutionError):
        await executor.execute(
            {"handler": "does_not_exist"},
            workspace_id=uuid.uuid4(),
            triggered_by=None,
            context=ExecutionContext(),
        )
