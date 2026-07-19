import { FileText, MessageSquare, Share2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { SearchHit } from "@/lib/api/semantic";
import type { RankedResult } from "@/lib/api/retrieval";

const KIND_ICON: Record<string, typeof FileText> = {
  document: FileText,
  chunk: MessageSquare,
  entity: Share2,
};

export function SearchResults({
  hits,
  ranked,
  isLoading,
  hasQuery,
}: {
  hits: SearchHit[];
  ranked: RankedResult[] | null;
  isLoading: boolean;
  hasQuery: boolean;
}) {
  if (!hasQuery) {
    return (
      <p className="text-sm text-foreground-muted">
        Enter a query to search your workspace&apos;s knowledge.
      </p>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  if (hits.length === 0) {
    return <p className="text-sm text-foreground-muted">No results found.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {hits.map((hit, index) => {
        const Icon = KIND_ICON[hit.kind] ?? FileText;
        const factors = ranked?.[index]?.factors;
        return (
          <Card key={`${hit.source_id}-${index}`}>
            <CardContent className="flex flex-col gap-2 pt-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-2">
                  <Icon className="h-icon-sm w-icon-sm shrink-0 text-foreground-muted" />
                  <p className="font-medium">{hit.title}</p>
                </div>
                <Badge variant="info">
                  {Math.round(hit.fused_score * 100)}% match
                </Badge>
              </div>
              <p className="text-sm text-foreground-muted">{hit.snippet}</p>
              <div className="flex flex-wrap gap-3 text-xs text-foreground-muted">
                <span className="capitalize">{hit.kind}</span>
                {hit.vector_score !== null && (
                  <span>Vector: {hit.vector_score.toFixed(2)}</span>
                )}
                {hit.keyword_score !== null && (
                  <span>Keyword: {hit.keyword_score.toFixed(2)}</span>
                )}
                {factors && (
                  <span>
                    Graph proximity: {factors.graph_proximity.toFixed(2)}
                  </span>
                )}
                <span>
                  Citation confidence:{" "}
                  {Math.round(hit.citation.confidence * 100)}%
                </span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
