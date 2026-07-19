import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { InsightEntry } from "@/services/capsules";

/** Renders `expertise_map`/`ownership_map`/`collaboration_network`/
 * `active_projects`/`technical_leadership` entries — all the same
 * underlying insight shape, differing only in which fields are present
 * (score vs. strength, plus ownership's share/category). */
export function InsightList({
  entries,
  metric,
  emptyMessage,
}: {
  entries: InsightEntry[];
  metric: "score" | "share" | "strength";
  emptyMessage: string;
}) {
  if (entries.length === 0) {
    return <p className="text-sm text-foreground-muted">{emptyMessage}</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {entries.map((entry, index) => {
        const value = entry[metric] ?? 0;
        return (
          <div
            key={`${entry.entity_id ?? index}`}
            className="flex flex-col gap-1.5 rounded-md border border-border p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-sm font-medium">
                {entry.canonical_name ?? "Unknown"}
              </span>
              <div className="flex shrink-0 items-center gap-1.5">
                {entry.entity_type && (
                  <Badge variant="outline" className="capitalize">
                    {entry.entity_type}
                  </Badge>
                )}
                {entry.ownership_category && (
                  <Badge variant="info" className="capitalize">
                    {entry.ownership_category}
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Progress value={value * 100} className="h-1.5 flex-1" />
              <span className="w-10 shrink-0 text-right text-xs text-foreground-muted">
                {Math.round(value * 100)}%
              </span>
            </div>
            {entry.evidence_count !== undefined && (
              <span className="text-xs text-foreground-muted">
                {entry.evidence_count} evidence record
                {entry.evidence_count === 1 ? "" : "s"}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
