"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  archiveConversation,
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  renameConversation,
  searchConversations,
  streamMessage,
  type Conversation,
  type ConversationStatus,
  type Message,
} from "@/lib/api/conversations";
import type { AskRequest, RAGAnswer, StreamEvent } from "@/lib/api/ai";

export function useConversations(status: ConversationStatus = "active") {
  return useQuery({
    queryKey: ["conversations", status],
    queryFn: () => listConversations(status, 1, 100),
  });
}

export function useConversationSearch(query: string) {
  return useQuery({
    queryKey: ["conversations", "search", query],
    queryFn: () => searchConversations(query, 1, 50),
    enabled: query.trim().length > 0,
  });
}

export function useConversation(conversationId: string | null) {
  return useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => getConversation(conversationId as string),
    enabled: conversationId !== null,
  });
}

export function useCreateConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (title?: string) => createConversation(title),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

export function useRenameConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      renameConversation(id, title),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

export function useArchiveConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => archiveConversation(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteConversation(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

/** Local-only pin state — 89_AI_Chat_Architecture.md notes Pin is "likely
 * backed by User Preference Memory rather than a new domain," but no such
 * preference-storage endpoint exists yet in the implemented API. Pinning
 * is therefore per-browser (localStorage), not synced across devices —
 * an honest scope limit, not a bug. */
const PINNED_KEY = "cerebrum.pinned_conversations";

export function usePinnedConversations() {
  const [pinned, setPinned] = React.useState<Set<string>>(new Set());

  React.useEffect(() => {
    const raw = window.localStorage.getItem(PINNED_KEY);
    if (raw) setPinned(new Set(JSON.parse(raw) as string[]));
  }, []);

  const togglePin = React.useCallback((conversationId: string) => {
    setPinned((prev) => {
      const next = new Set(prev);
      if (next.has(conversationId)) next.delete(conversationId);
      else next.add(conversationId);
      window.localStorage.setItem(PINNED_KEY, JSON.stringify(Array.from(next)));
      return next;
    });
  }, []);

  return { pinned, togglePin };
}

export interface StreamingState {
  status: "idle" | "streaming" | "error";
  stage: string | null;
  partialText: string;
  error: string | null;
}

/** Drives a single streamed turn against
 * `POST /conversations/{id}/messages/stream`, accumulating `token` events
 * into `partialText` and resolving with the backend's final,
 * fully-computed {@link RAGAnswer} on `completed` — the UI never computes
 * its own answer text or confidence score. */
export function useStreamingTurn(conversationId: string | null) {
  const queryClient = useQueryClient();
  const [state, setState] = React.useState<StreamingState>({
    status: "idle",
    stage: null,
    partialText: "",
    error: null,
  });
  const abortRef = React.useRef<AbortController | null>(null);

  const send = React.useCallback(
    async (body: AskRequest, onCompleted: (answer: RAGAnswer) => void) => {
      if (!conversationId) return;
      const controller = new AbortController();
      abortRef.current = controller;
      setState({
        status: "streaming",
        stage: "starting",
        partialText: "",
        error: null,
      });

      try {
        for await (const event of streamMessage(
          conversationId,
          body,
          controller.signal,
        )) {
          handleEvent(event, setState, onCompleted);
        }
      } catch (error) {
        if (controller.signal.aborted) {
          setState((prev) => ({ ...prev, status: "idle" }));
        } else {
          setState({
            status: "error",
            stage: null,
            partialText: "",
            error: error instanceof Error ? error.message : "Stream failed.",
          });
        }
      } finally {
        void queryClient.invalidateQueries({
          queryKey: ["conversation", conversationId],
        });
        void queryClient.invalidateQueries({ queryKey: ["conversations"] });
      }
    },
    [conversationId, queryClient],
  );

  const cancel = React.useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { state, send, cancel };
}

function handleEvent(
  event: StreamEvent,
  setState: React.Dispatch<React.SetStateAction<StreamingState>>,
  onCompleted: (answer: RAGAnswer) => void,
) {
  switch (event.type) {
    case "progress":
      setState((prev) => ({ ...prev, stage: event.stage }));
      break;
    case "token":
      setState((prev) => ({
        ...prev,
        partialText: prev.partialText + event.token,
      }));
      break;
    case "completed":
      setState({ status: "idle", stage: null, partialText: "", error: null });
      onCompleted(event.answer);
      break;
    case "cancelled":
      setState((prev) => ({ ...prev, status: "idle" }));
      break;
    case "error":
      setState({
        status: "error",
        stage: null,
        partialText: "",
        error: event.message,
      });
      break;
  }
}

export type { Conversation, Message };
