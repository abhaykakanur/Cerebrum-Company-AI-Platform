import * as React from "react";

import { cn } from "@/lib/utils";

// Timeline — Feedback & Status catalog. Renders chronologically ordered
// content (docs/architecture/specification/87_Component_Library.md) —
// the Employee Knowledge Capsule's Organizational Timeline and AI
// Chat's reasoning trace both consume this.
export interface TimelineItem {
  id: string;
  title: string;
  description?: string | null;
  timestamp: string;
  icon?: React.ReactNode;
  tone?: "default" | "success" | "warning" | "danger" | "info";
}

const toneDot: Record<NonNullable<TimelineItem["tone"]>, string> = {
  default: "bg-foreground-muted",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info",
};

export function Timeline({
  items,
  className,
}: {
  items: TimelineItem[];
  className?: string;
}) {
  if (items.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-foreground-muted">
        No timeline events yet.
      </p>
    );
  }

  return (
    <ol
      className={cn(
        "relative space-y-6 border-l border-border pl-6",
        className,
      )}
    >
      {items.map((item) => (
        <li key={item.id} className="relative">
          <span
            className={cn(
              "absolute -left-[1.65rem] top-1 flex h-3 w-3 items-center justify-center rounded-full ring-4 ring-background",
              toneDot[item.tone ?? "default"],
            )}
          />
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-foreground">
                {item.title}
              </p>
              <time className="shrink-0 text-xs text-foreground-muted">
                {item.timestamp}
              </time>
            </div>
            {item.description && (
              <p className="text-sm text-foreground-muted">
                {item.description}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
