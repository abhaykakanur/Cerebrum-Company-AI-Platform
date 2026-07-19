"""The Conversation API surface — CIS Phase 4 Prompt 2's Conversation
Management, Session Management, Streaming, and Search endpoints, built
entirely on
:class:`~cerebrum.application.conversation.session_service.SessionService`/
:class:`~cerebrum.application.conversation.conversation_service.ConversationService`
(see cerebrum.application.conversation's package docstring). Reuses
``LLMProviderDep`` from cerebrum.api.v1.ai and this same module's own
SSE encoding helpers from that file (see :func:`_encode_sse`'s import)
rather than duplicating provider selection or event serialization.

``"conversations:write"`` gates every mutating route (create/rename/
archive/delete/send/stream); ``"conversations:read"`` gates read-only
routes — mirroring cerebrum.api.v1.documents's read/write permission
split. User Ownership (CIS Phase 4 Prompt 2's Security requirement) is
enforced one layer down, in ``ConversationService``/``SessionService``
themselves (see that service's docstring) — every route here that
targets one conversation gets a ``PermissionDeniedException`` for free
if the caller does not own it.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import (
    build_collection_response,
    build_success_response,
)
from cerebrum.api.schemas.conversation import (
    ConversationDetailResponse,
    ConversationExportResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    RenameConversationRequest,
    SendMessageRequest,
    TurnResponse,
)
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.v1.ai import _encode_sse
from cerebrum.dependencies.ai import LLMProviderDep
from cerebrum.dependencies.auth import (
    CurrentUserDep,
    WorkspaceIdDep,
    require_permission,
)
from cerebrum.dependencies.conversation import ConversationServiceDep, SessionServiceDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.infrastructure.database.models.conversation import ConversationStatus
from cerebrum.repositories.contracts import Pagination, map_page
from cerebrum.shared.errors.exceptions import ValidationException

router = APIRouter(
    prefix="/conversations", tags=["Conversations"], responses=STANDARD_ERROR_RESPONSES
)

_write = Depends(require_permission("conversations:write"))
_read = Depends(require_permission("conversations:read"))

_DISCONNECT_POLL_SECONDS = 0.5


@router.post(
    "",
    response_model=SuccessResponse[ConversationResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[_write],
)
async def create_conversation(
    body: CreateConversationRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    sessions: SessionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ConversationResponse]:
    conversation = await sessions.create_session(
        workspace_id=workspace_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        title=body.title,
        session_id=body.session_id,
    )
    return build_success_response(
        ConversationResponse.model_validate(conversation), settings=settings
    )


@router.get(
    "",
    response_model=SuccessResponse[list[ConversationResponse]],
    dependencies=[_read],
)
async def list_conversations(
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    conversations: ConversationServiceDep,
    settings: SettingsDep,
    conversation_status: Annotated[ConversationStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[ConversationResponse]]:
    page_result = await conversations.list_in_workspace(
        workspace_id=workspace_id,
        user_id=current_user.id,
        pagination=Pagination(page=page, page_size=page_size),
        status=conversation_status,
    )
    return build_collection_response(
        map_page(page_result, ConversationResponse.model_validate), settings=settings
    )


@router.get(
    "/search",
    response_model=SuccessResponse[list[ConversationResponse]],
    dependencies=[_read],
)
async def search_conversations(
    workspace_id: WorkspaceIdDep,
    conversations: ConversationServiceDep,
    settings: SettingsDep,
    q: Annotated[str, Query(min_length=1)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[ConversationResponse]]:
    page_result = await conversations.search_conversations(
        workspace_id=workspace_id,
        query_text=q,
        pagination=Pagination(page=page, page_size=page_size),
    )
    return build_collection_response(
        map_page(page_result, ConversationResponse.model_validate), settings=settings
    )


@router.get(
    "/search/messages",
    response_model=SuccessResponse[list[MessageResponse]],
    dependencies=[_read],
)
async def search_messages(
    workspace_id: WorkspaceIdDep,
    conversations: ConversationServiceDep,
    settings: SettingsDep,
    q: Annotated[str | None, Query(min_length=1)] = None,
    reference_id: Annotated[uuid.UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[MessageResponse]]:
    """Search Messages / Search by citation / Search by entity / Search
    by document — all one endpoint: ``q`` searches message content;
    ``reference_id`` searches by citation, entity, or document id (see
    cerebrum.repositories.postgres.message_repository.MessageRepository.search_by_citation_reference).
    Exactly one of the two must be supplied.
    """
    pagination = Pagination(page=page, page_size=page_size)
    if reference_id is not None:
        page_result = await conversations.search_by_reference(
            workspace_id=workspace_id, reference_id=reference_id, pagination=pagination
        )
    elif q is not None:
        page_result = await conversations.search_messages(
            workspace_id=workspace_id, query_text=q, pagination=pagination
        )
    else:
        raise ValidationException("Provide either 'q' or 'reference_id'.")
    return build_collection_response(
        map_page(page_result, MessageResponse.model_validate), settings=settings
    )


@router.get(
    "/{conversation_id}",
    response_model=SuccessResponse[ConversationDetailResponse],
    dependencies=[_read],
)
async def get_conversation(
    conversation_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    conversations: ConversationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ConversationDetailResponse]:
    conversation = await conversations.get(
        conversation_id, workspace_id=workspace_id, user_id=current_user.id
    )
    history = await conversations.get_history(
        conversation_id, workspace_id=workspace_id, user_id=current_user.id
    )
    detail = ConversationDetailResponse(
        **ConversationResponse.model_validate(conversation).model_dump(),
        messages=[MessageResponse.model_validate(m) for m in history],
    )
    return build_success_response(detail, settings=settings)


@router.patch(
    "/{conversation_id}",
    response_model=SuccessResponse[ConversationResponse],
    dependencies=[_write],
)
async def rename_conversation(
    conversation_id: uuid.UUID,
    body: RenameConversationRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    conversations: ConversationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ConversationResponse]:
    conversation = await conversations.rename(
        conversation_id,
        workspace_id=workspace_id,
        user_id=current_user.id,
        title=body.title,
    )
    return build_success_response(
        ConversationResponse.model_validate(conversation), settings=settings
    )


@router.post(
    "/{conversation_id}/archive",
    response_model=SuccessResponse[ConversationResponse],
    dependencies=[_write],
)
async def archive_conversation(
    conversation_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    conversations: ConversationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ConversationResponse]:
    conversation = await conversations.archive(
        conversation_id, workspace_id=workspace_id, user_id=current_user.id
    )
    return build_success_response(
        ConversationResponse.model_validate(conversation), settings=settings
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_write],
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    conversations: ConversationServiceDep,
) -> None:
    await conversations.delete(
        conversation_id, workspace_id=workspace_id, user_id=current_user.id
    )


@router.get(
    "/{conversation_id}/export",
    response_model=SuccessResponse[ConversationExportResponse],
    dependencies=[_read],
)
async def export_conversation(
    conversation_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    conversations: ConversationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ConversationExportResponse]:
    export = await conversations.export(
        conversation_id, workspace_id=workspace_id, user_id=current_user.id
    )
    return build_success_response(
        ConversationExportResponse(**export), settings=settings
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=SuccessResponse[TurnResponse],
    dependencies=[_write],
)
async def send_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    sessions: SessionServiceDep,
    provider: LLMProviderDep,
    settings: SettingsDep,
) -> SuccessResponse[TurnResponse]:
    turn = await sessions.send_message(
        conversation_id,
        workspace_id=workspace_id,
        user_id=current_user.id,
        question=body.question,
        provider=provider,
        strategy=body.strategy,
        model=body.model,
        limit=body.limit,
        max_context_tokens=body.max_context_tokens,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
    )
    return build_success_response(TurnResponse.from_turn(turn), settings=settings)


@router.post("/{conversation_id}/messages/stream", dependencies=[_write])
async def stream_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    sessions: SessionServiceDep,
    provider: LLMProviderDep,
    request: Request,
) -> StreamingResponse:
    """Stream Message — the same Server-Sent-Events framing
    cerebrum.api.v1.ai.stream_answer uses (see :func:`_encode_sse`),
    reused rather than duplicated; the only difference is that each
    turn here is persisted (see
    cerebrum.application.conversation.session_service.SessionService.send_message_stream).
    """
    cancellation = asyncio.Event()

    async def _watch_for_disconnect() -> None:
        while not cancellation.is_set():
            if await request.is_disconnected():
                cancellation.set()
                return
            await asyncio.sleep(_DISCONNECT_POLL_SECONDS)

    async def _body() -> AsyncIterator[bytes]:
        watcher = asyncio.create_task(_watch_for_disconnect())
        try:
            async for event in sessions.send_message_stream(
                conversation_id,
                workspace_id=workspace_id,
                user_id=current_user.id,
                question=body.question,
                provider=provider,
                strategy=body.strategy,
                model=body.model,
                limit=body.limit,
                max_context_tokens=body.max_context_tokens,
                max_tokens=body.max_tokens,
                temperature=body.temperature,
                cancellation=cancellation,
            ):
                yield _encode_sse(event)
        finally:
            cancellation.set()
            watcher.cancel()

    return StreamingResponse(_body(), media_type="text/event-stream")
