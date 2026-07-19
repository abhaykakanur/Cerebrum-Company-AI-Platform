import type * as React from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { useAICapsule } from "@/services/capsules";

function titleCase(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function renderValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined)
    return <span className="text-foreground-muted">—</span>;
  if (Array.isArray(value)) {
    if (value.length === 0)
      return <span className="text-foreground-muted">None</span>;
    return (
      <ul className="ml-4 list-disc space-y-0.5">
        {value.map((item, i) => (
          <li key={i}>
            {typeof item === "object" ? JSON.stringify(item) : String(item)}
          </li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object") {
    return (
      <div className="flex flex-col gap-1 pl-3">
        {Object.entries(value as Record<string, unknown>).map(([key, val]) => (
          <div key={key}>
            <span className="text-foreground-muted">{titleCase(key)}: </span>
            {renderValue(val)}
          </div>
        ))}
      </div>
    );
  }
  return <span>{String(value)}</span>;
}

/**
 * AI Capsule — a structured summary assembled entirely from the
 * capsule's own already-computed, evidence-backed fields. Per the
 * design decision behind this feature: it never calls an LLM, so there
 * is no unverifiable generated prose about a real person — every value
 * shown here traces back to a field already visible elsewhere on this
 * page.
 */
export function AICapsulePanel({ capsuleId }: { capsuleId: string }) {
  const { data, isLoading } = useAICapsule(capsuleId);

  if (isLoading || !data) return <Skeleton className="h-48 w-full" />;

  return (
    <div className="flex flex-col gap-3 text-sm">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="rounded-md border border-border p-3">
          <p className="mb-1 font-medium">{titleCase(key)}</p>
          {renderValue(value)}
        </div>
      ))}
    </div>
  );
}
