"use client";

import * as React from "react";
import { Search } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useEntitySearch } from "@/services/graph";
import type { GraphMode } from "@/features/graph/graph-canvas";

const MODES: { value: GraphMode; label: string }[] = [
  { value: "explore", label: "Explore" },
  { value: "cluster", label: "Cluster" },
  { value: "dependency", label: "Dependency" },
  { value: "timeline", label: "Timeline" },
];

export function GraphToolbar({
  mode,
  onModeChange,
  depth,
  onDepthChange,
  onSelectEntity,
}: {
  mode: GraphMode;
  onModeChange: (mode: GraphMode) => void;
  depth: number;
  onDepthChange: (depth: number) => void;
  onSelectEntity: (entityId: string, name: string) => void;
}) {
  const [query, setQuery] = React.useState("");
  const { data, isLoading } = useEntitySearch(query);

  return (
    <div className="flex flex-wrap items-center gap-4">
      <Popover open={query.trim().length > 1}>
        <PopoverTrigger asChild>
          <div className="relative w-72">
            <Search className="absolute left-2.5 top-2.5 h-icon-sm w-icon-sm text-foreground-muted" />
            <Input
              placeholder="Find an entity to center the graph on..."
              className="pl-8"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-72 p-1">
          {isLoading && (
            <p className="p-2 text-xs text-foreground-muted">Searching...</p>
          )}
          {!isLoading && data?.items.length === 0 && (
            <p className="p-2 text-xs text-foreground-muted">
              No entities found.
            </p>
          )}
          {data?.items.map((entity) => (
            <button
              key={entity.id}
              type="button"
              className="flex w-full flex-col rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent"
              onClick={() => {
                onSelectEntity(entity.id, entity.canonical_name);
                setQuery("");
              }}
            >
              <span>{entity.canonical_name}</span>
              <span className="text-xs capitalize text-foreground-muted">
                {entity.entity_type}
              </span>
            </button>
          ))}
        </PopoverContent>
      </Popover>

      <div className="flex items-center gap-1.5">
        {MODES.map((m) => (
          <button
            key={m.value}
            type="button"
            onClick={() => onModeChange(m.value)}
          >
            <Badge
              variant={mode === m.value ? "default" : "outline"}
              className={cn(
                "cursor-pointer",
                mode === m.value && "border-transparent",
              )}
            >
              {m.label}
            </Badge>
          </button>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-foreground-muted">Depth</span>
        {[1, 2, 3, 4, 5].map((d) => (
          <button key={d} type="button" onClick={() => onDepthChange(d)}>
            <Badge
              variant={depth === d ? "info" : "outline"}
              className="cursor-pointer"
            >
              {d}
            </Badge>
          </button>
        ))}
      </div>
    </div>
  );
}
