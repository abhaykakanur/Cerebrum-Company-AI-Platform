/**
 * AI API — mirrors apps/backend/src/cerebrum/api/v1/ai.py. The two
 * `/stream` endpoints return raw `text/event-stream` (not the
 * SuccessResponse envelope), so they're parsed manually here rather than
 * going through `apiRequest`.
 */

import {
  apiGet,
  apiSend,
  API_BASE_URL,
  getAccessToken,
  getCurrentWorkspaceId,
} from "@/lib/api/client";
import type { EnrichedCitation, RetrievalStrategy } from "@/lib/api/retrieval";

export interface ConfidenceBreakdown {
  retrieval_confidence: number;
  citation_coverage: number;
  context_completeness: number;
  source_diversity: number;
  overall: number;
}

export interface RAGAnswer {
  answer: string;
  citations: EnrichedCitation[];
  confidence: ConfidenceBreakdown;
  strategy: string;
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  context_truncated: boolean;
}

export interface AskRequest {
  question: string;
  strategy?: RetrievalStrategy;
  limit?: number;
  max_context_tokens?: number;
  max_tokens?: number;
  temperature?: number;
  model?: string;
}

export interface AIUsageStatistics {
  question_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  providers: Record<string, number>;
}

export interface AIProviderConfig {
  available_providers: string[];
  default_provider: string;
  default_temperature: number;
  default_max_tokens: number;
  default_max_context_tokens: number;
  default_model_by_provider: Record<string, string>;
}

export type StreamEvent =
  | { type: "progress"; stage: string }
  | { type: "token"; token: string }
  | { type: "completed"; answer: RAGAnswer }
  | { type: "cancelled" }
  | { type: "error"; message: string };

export async function ask(body: AskRequest): Promise<RAGAnswer> {
  return apiSend<RAGAnswer>("/ai/ask", "POST", body);
}

export async function getAIStatistics(): Promise<AIUsageStatistics> {
  return apiGet<AIUsageStatistics>("/ai/statistics");
}

export async function getAIConfig(): Promise<AIProviderConfig> {
  return apiGet<AIProviderConfig>("/ai/config");
}

/** Shared SSE frame parser for `/ai/ask/stream` and
 * `/conversations/{id}/messages/stream` — both emit identical
 * `data: {...}\n\n` frames via the backend's `_encode_sse`. */
export async function* streamSse(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const workspaceId = getCurrentWorkspaceId();
  if (workspaceId) headers["X-Workspace-ID"] = workspaceId;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`Stream request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      const json = line.slice("data:".length).trim();
      if (!json) continue;
      yield JSON.parse(json) as StreamEvent;
    }
  }
}

export function streamAsk(
  body: AskRequest,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  return streamSse("/ai/ask/stream", body, signal);
}
