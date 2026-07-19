/** Conversations API — mirrors apps/backend/src/cerebrum/api/v1/conversations.py. */

import {
  apiGet,
  apiGetPage,
  apiSend,
  type PaginationMeta,
} from "@/lib/api/client";
import {
  streamSse,
  type AskRequest,
  type RAGAnswer,
  type StreamEvent,
} from "@/lib/api/ai";

export type ConversationStatus = "active" | "archived" | "deleted";

export interface Conversation {
  id: string;
  workspace_id: string;
  user_id: string;
  session_id: string | null;
  title: string;
  status: string;
  summary: string | null;
  conversation_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  sequence_index: number;
  role: string;
  content: string;
  citations: Record<string, unknown>[];
  context_references: Record<string, unknown>[];
  confidence: number | null;
  prompt_tokens: number;
  completion_tokens: number;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface TurnResponse {
  conversation: Conversation;
  user_message: Message;
  assistant_message: Message;
  answer: RAGAnswer;
}

export async function listConversations(
  status?: ConversationStatus,
  page = 1,
  pageSize = 50,
): Promise<{ items: Conversation[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Conversation>("/conversations", {
    query: { conversation_status: status, page, page_size: pageSize },
  });
}

export async function createConversation(
  title?: string,
): Promise<Conversation> {
  return apiSend<Conversation>("/conversations", "POST", { title });
}

export async function getConversation(
  conversationId: string,
): Promise<ConversationDetail> {
  return apiGet<ConversationDetail>(`/conversations/${conversationId}`);
}

export async function renameConversation(
  conversationId: string,
  title: string,
): Promise<Conversation> {
  return apiSend<Conversation>(`/conversations/${conversationId}`, "PATCH", {
    title,
  });
}

export async function archiveConversation(
  conversationId: string,
): Promise<Conversation> {
  return apiSend<Conversation>(
    `/conversations/${conversationId}/archive`,
    "POST",
  );
}

export async function deleteConversation(
  conversationId: string,
): Promise<void> {
  return apiSend<void>(`/conversations/${conversationId}`, "DELETE");
}

export async function searchConversations(
  q: string,
  page = 1,
  pageSize = 50,
): Promise<{ items: Conversation[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Conversation>("/conversations/search", {
    query: { q, page, page_size: pageSize },
  });
}

export async function sendMessage(
  conversationId: string,
  body: AskRequest,
): Promise<TurnResponse> {
  return apiSend<TurnResponse>(
    `/conversations/${conversationId}/messages`,
    "POST",
    body,
  );
}

export interface ConversationExport {
  conversation: Record<string, unknown>;
  messages: Record<string, unknown>[];
}

/** Downloads the conversation's export payload as a `.json` file
 * client-side — FR-CV-004, preserving citations since the backend's
 * export includes the full persisted `messages` (citations included). */
export async function exportConversation(
  conversationId: string,
  title: string,
): Promise<void> {
  const data = await apiGet<ConversationExport>(
    `/conversations/${conversationId}/export`,
  );
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${title.replace(/[^a-z0-9]+/gi, "-").toLowerCase() || "conversation"}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

export function streamMessage(
  conversationId: string,
  body: AskRequest,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  return streamSse(
    `/conversations/${conversationId}/messages/stream`,
    body,
    signal,
  );
}
