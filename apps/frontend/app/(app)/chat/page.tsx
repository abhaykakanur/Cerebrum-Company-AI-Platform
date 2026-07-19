"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, MessageSquare } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import { Skeleton } from "@/components/ui/skeleton";
import { ConversationList } from "@/features/chat/conversation-list";
import { MessageBubble } from "@/features/chat/message-bubble";
import { MessageComposer } from "@/features/chat/message-composer";
import { Markdown } from "@/features/chat/markdown";
import { useConversation, useStreamingTurn } from "@/services/chat";
import { exportConversation } from "@/lib/api/conversations";

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const conversationId = searchParams.get("c");

  const { data: conversation, isLoading } = useConversation(conversationId);
  const { state, send, cancel } = useStreamingTurn(conversationId);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  const select = (id: string) => router.push(`/chat?c=${id}`);

  const messages = conversation?.messages ?? [];
  const lastUserQuestion =
    [...messages].reverse().find((m) => m.role === "user")?.content ?? null;

  React.useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length, state.partialText]);

  const handleSend = (question: string) => {
    void send({ question }, () => {});
  };

  const handleRegenerate = () => {
    if (lastUserQuestion) handleSend(lastUserQuestion);
  };

  const handleExport = async () => {
    if (!conversationId) return;
    try {
      await exportConversation(
        conversationId,
        conversation?.title ?? "conversation",
      );
      toast.success("Conversation exported.");
    } catch {
      toast.error("Failed to export conversation.");
    }
  };

  return (
    <ResizablePanelGroup
      direction="horizontal"
      className="-m-6 h-[calc(100vh-7.5rem)]"
    >
      <ResizablePanel defaultSize={22} minSize={18} maxSize={35}>
        <ConversationList activeId={conversationId} onSelect={select} />
      </ResizablePanel>
      <ResizableHandle />
      <ResizablePanel defaultSize={78}>
        <div className="flex h-full flex-col">
          {!conversationId ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center">
              <MessageSquare className="h-icon-xl w-icon-xl text-foreground-muted" />
              <p className="text-foreground-muted">
                Select a conversation or start a new one.
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between border-b border-border px-4 py-3">
                <h2 className="truncate font-medium">
                  {conversation?.title || "Conversation"}
                </h2>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1.5"
                  onClick={handleExport}
                >
                  <Download className="h-icon-xs w-icon-xs" />
                  Export
                </Button>
              </div>
              <div
                ref={scrollRef}
                className="flex flex-1 flex-col gap-4 overflow-y-auto p-4"
              >
                {isLoading &&
                  Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-2/3" />
                  ))}
                {messages.map((message, index) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    isLastAssistant={
                      message.role === "assistant" &&
                      index === messages.length - 1
                    }
                    onRegenerate={handleRegenerate}
                  />
                ))}
                {state.status === "streaming" && (
                  <div className="flex flex-col gap-1">
                    <div className="max-w-2xl rounded-lg border border-border bg-card px-4 py-3">
                      {state.partialText ? (
                        <Markdown content={state.partialText} />
                      ) : (
                        <p className="text-sm text-foreground-muted">
                          {state.stage ?? "Thinking..."}
                        </p>
                      )}
                    </div>
                  </div>
                )}
                {state.status === "error" && (
                  <p className="text-sm text-danger">
                    {state.error ?? "Something went wrong."}
                  </p>
                )}
              </div>
              <MessageComposer
                onSend={handleSend}
                onCancel={cancel}
                isStreaming={state.status === "streaming"}
              />
            </>
          )}
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
