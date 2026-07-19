import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { RetrievalStrategy } from "@/lib/api/retrieval";
import type { SearchFilters } from "@/services/search";

const STRATEGIES: { value: RetrievalStrategy; label: string }[] = [
  { value: "hybrid", label: "Hybrid" },
  { value: "semantic", label: "Semantic" },
  { value: "keyword", label: "Keyword" },
  { value: "graph", label: "Graph" },
];

const KINDS = ["document", "chunk", "entity"];

export function SearchFiltersBar({
  filters,
  onChange,
}: {
  filters: SearchFilters;
  onChange: (filters: SearchFilters) => void;
}) {
  const toggleKind = (kind: string) => {
    const kinds = filters.kinds.includes(kind)
      ? filters.kinds.filter((k) => k !== kind)
      : [...filters.kinds, kind];
    onChange({ ...filters, kinds });
  };

  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="flex items-center gap-1.5">
        <span className="text-xs font-medium text-foreground-muted">
          Strategy
        </span>
        {STRATEGIES.map((s) => (
          <button
            key={s.value}
            type="button"
            onClick={() => onChange({ ...filters, strategy: s.value })}
          >
            <Badge
              variant={filters.strategy === s.value ? "default" : "outline"}
              className={cn(
                "cursor-pointer",
                filters.strategy === s.value && "border-transparent",
              )}
            >
              {s.label}
            </Badge>
          </button>
        ))}
      </div>
      <div className="flex items-center gap-1.5">
        <span className="text-xs font-medium text-foreground-muted">Kinds</span>
        {KINDS.map((kind) => (
          <button key={kind} type="button" onClick={() => toggleKind(kind)}>
            <Badge
              variant={filters.kinds.includes(kind) ? "info" : "outline"}
              className="cursor-pointer capitalize"
            >
              {kind}
            </Badge>
          </button>
        ))}
      </div>
    </div>
  );
}
