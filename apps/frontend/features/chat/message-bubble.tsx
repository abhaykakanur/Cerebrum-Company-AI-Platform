"use client";

import * as React from "react";
import { RotateCcw, ThumbsDown, ThumbsUp } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/features/chat/markdown";
import { ConfidenceIndicator } from "@/features/chat/confidence-indicator";
import { CitationList } from "@/features/chat/citation-list";
import type { Message } from "@/lib/api/conversations";

/** FR-CF-004's Confidence Calibration Feedback Loop UI surface. No
 * message-feedback endpoint exists in the implemented backend, so this
 * records nothing server-side — it's an honest, session-local
 * acknowledgement only (see 89_AI_Chat_Architecture capability table's
 * backend mapping for this gap). */
function FeedbackButtons() {
  const [given, setGiven] = React.useState<"up" | "down" | null>(null);
  const give = (value: "up" | "down") => {
    setGiven(value);
    toast.success("Thanks for the feedback.");
  };
  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        aria-label="Good response"
        onClick={() => give("up")}
        disabled={given !== null}
      >
        <ThumbsUp
          className={cn(
            "h-icon-xs w-icon-xs",
            given === "up" && "text-success",
          )}
        />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        aria-label="Poor response"
        onClick={() => give("down")}
        disabled={given !== null}
      >
        <ThumbsDown
          className={cn(
            "h-icon-xs w-icon-xs",
            given === "down" && "text-danger",
          )}
        />
      </Button>
    </div>
  );
}

export function MessageBubble({
  message,
  onRegenerate,
  isLastAssistant,
}: {
  message: Message;
  onRegenerate?: () => void;
  isLastAssistant?: boolean;
}) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex flex-col gap-2",
        isUser ? "items-end" : "items-start",
      )}
    >
      <div
        className={cn(
          "max-w-2xl rounded-lg px-4 py-3",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border border-border bg-card",
        )}
      >
        <Markdown content={message.content} />
      </div>
      {!isUser && (
        <div className="flex flex-wrap items-center gap-2">
          {message.confidence !== null && (
            <ConfidenceIndicator
              confidence={{
                overall: message.confidence,
                retrieval_confidence: message.confidence,
                citation_coverage: message.confidence,
                context_completeness: message.confidence,
                source_diversity: message.confidence,
              }}
            />
          )}
          <CitationList citations={message.citations} />
          <FeedbackButtons />
          {isLastAssistant && onRegenerate && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs"
              onClick={onRegenerate}
            >
              <RotateCcw className="h-icon-xs w-icon-xs" />
              Regenerate
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
