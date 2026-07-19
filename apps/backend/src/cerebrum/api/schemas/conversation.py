"""Request/response schemas for CIS Phase 4 Prompt 2's Conversational
AI API. Every response model inherits
:class:`~cerebrum.api.schemas.base.APIModel` (``from_attributes=True``)
so a route can return ``XResponse.model_validate(orm_object)`` directly
— see cerebrum.api.schemas.knowledge's identical docstring precedent.
Reuses :class:`~cerebrum.api.schemas.ai.RAGAnswerResponse` for the
generated-answer portion of a turn rather than redefining it — CIS
Phase 4 Prompt 2 reuses CIS Phase 4 Prompt 1's RAG Engine, not a parallel
one.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import Field

from cerebrum.api.schemas.ai import RAGAnswerResponse
from cerebrum.api.schemas.base import APIModel
from cerebrum.application.retrieval.retrieval_service import RetrievalStrategy

if TYPE_CHECKING:
    from cerebrum.application.conversation.session_service import TurnResult

# --- Requests -----------------------------------------------------------------


class CreateConversationRequest(APIModel):
    title: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RenameConversationRequest(APIModel):
    title: str = Field(min_length=1, max_length=500)


class SendMessageRequest(APIModel):
    question: str = Field(min_length=1)
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    limit: int = Field(default=10, ge=1, le=50)
    max_context_tokens: int = Field(default=3000, ge=1)
    max_tokens: int = Field(default=1024, ge=1, le=32_000)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    model: str | None = None


# --- Responses ------------------------------------------------------------


class MessageResponse(APIModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sequence_index: int
    role: str
    content: str
    citations: list[dict[str, Any]]
    context_references: list[dict[str, Any]]
    confidence: float | None
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime


class ConversationResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    session_id: str | None
    title: str
    status: str
    summary: str | None
    conversation_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]


class TurnResponse(APIModel):
    conversation: ConversationResponse
    user_message: MessageResponse
    assistant_message: MessageResponse
    answer: RAGAnswerResponse

    @classmethod
    def from_turn(cls, turn: "TurnResult") -> "TurnResponse":
        return cls(
            conversation=ConversationResponse.model_validate(turn.conversation),
            user_message=MessageResponse.model_validate(turn.user_message),
            assistant_message=MessageResponse.model_validate(turn.assistant_message),
            answer=RAGAnswerResponse.from_answer(turn.answer),
        )


class ConversationExportResponse(APIModel):
    conversation: dict[str, Any]
    messages: list[dict[str, Any]]
