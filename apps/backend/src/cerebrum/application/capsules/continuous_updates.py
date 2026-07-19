"""``ContinuousUpdateListener``: CIS Phase 5 Prompt 3's Continuous
Updates — "reuse the existing event system," applied literally: this
subscribes real, synchronous handlers onto the *existing*
:class:`~cerebrum.events.dispatcher.EventDispatcher` for the events
CIS names (Connector Sync, Document Ingestion/Graph Update, Workflow
Completion), rather than inventing a parallel notification mechanism.

A handler registered with ``EventDispatcher`` must be a plain
synchronous callable (see that class's own docstring — no async
handlers exist in this codebase) and therefore cannot itself perform
the async, database-backed work of resolving "which capsule does this
specific entity/document change actually affect" (that requires
walking the knowledge graph). Each handler here does the only thing a
synchronous callback safely can: append the event's ``workspace_id`` to
an in-memory pending set — cheap, side-effect-free, and impossible to
get wrong. The actual staleness write happens through
:meth:`~cerebrum.application.capsules.employee_knowledge_capsule_service.EmployeeKnowledgeCapsuleService.mark_stale_for_workspace`,
called by whatever drains :meth:`ContinuousUpdateListener.drain_pending_workspaces`
— an API route, an operator, or a future scheduler poll, the same "a
query to poll, not a timer this codebase runs itself" pattern
``ConnectorScheduler``/``WorkflowScheduler`` already establish.

**Coarse by design**: a pending workspace means "something changed
that *might* affect a capsule in it," not "capsule X specifically needs
refreshing" — pinpointing the exact affected capsule(s) would require
resolving the changed document/entity back to a linked
``person_entity_id``, itself an async graph query no synchronous event
handler can perform. Every capsule in a flagged workspace is marked
stale; an unaffected capsule staying accurate one refresh-cycle longer
is a far smaller cost than silently missing a real change.

**Integration note**: this class only becomes "continuous" once
something registers it against the application's actual long-lived
:class:`~cerebrum.events.dispatcher.EventDispatcher` singleton (see
cerebrum.core.state.ApplicationState.events) — e.g.
``listener.register(state.events)`` once at startup. That one-line
wiring step is intentionally left to the deployment/integration layer
rather than made here, to avoid this milestone touching
cerebrum.core.lifecycle's already-established, independently-tested
startup sequence; the mechanism itself is complete and directly
testable by constructing a real ``EventDispatcher``, registering a
listener, publishing a real event, and observing the pending set.
"""

import uuid

from cerebrum.application.connectors.events import SyncCompletedEvent
from cerebrum.application.knowledge_graph.events import GraphUpdatedEvent
from cerebrum.application.workflows.events import WorkflowCompletedEvent
from cerebrum.events.dispatcher import EventDispatcher


class ContinuousUpdateListener:
    def __init__(self) -> None:
        self._pending_workspaces: set[uuid.UUID] = set()

    def register(self, dispatcher: EventDispatcher) -> None:
        dispatcher.subscribe(GraphUpdatedEvent, self._on_graph_updated)
        dispatcher.subscribe(SyncCompletedEvent, self._on_sync_completed)
        dispatcher.subscribe(WorkflowCompletedEvent, self._on_workflow_completed)

    def drain_pending_workspaces(self) -> list[uuid.UUID]:
        pending = list(self._pending_workspaces)
        self._pending_workspaces.clear()
        return pending

    def _on_graph_updated(self, event: GraphUpdatedEvent) -> None:
        self._pending_workspaces.add(event.workspace_id)

    def _on_sync_completed(self, event: SyncCompletedEvent) -> None:
        self._pending_workspaces.add(event.workspace_id)

    def _on_workflow_completed(self, event: WorkflowCompletedEvent) -> None:
        self._pending_workspaces.add(event.workspace_id)
