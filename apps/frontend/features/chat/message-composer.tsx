"use client";

import * as React from "react";
import { Send, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function MessageComposer({
  onSend,
  onCancel,
  isStreaming,
}: {
  onSend: (question: string) => void;
  onCancel: () => void;
  isStreaming: boolean;
}) {
  const [value, setValue] = React.useState("");

  const submit = () => {
    const question = value.trim();
    if (!question || isStreaming) return;
    onSend(question);
    setValue("");
  };

  return (
    <div className="flex items-end gap-2 border-t border-border p-4">
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Ask about your organization's knowledge..."
        className="min-h-11 flex-1 resize-none"
        rows={1}
      />
      {isStreaming ? (
        <Button
          variant="outline"
          size="icon"
          onClick={onCancel}
          aria-label="Stop generating"
        >
          <Square className="h-icon-sm w-icon-sm" />
        </Button>
      ) : (
        <Button
          size="icon"
          onClick={submit}
          disabled={!value.trim()}
          aria-label="Send message"
        >
          <Send className="h-icon-sm w-icon-sm" />
        </Button>
      )}
    </div>
  );
}
