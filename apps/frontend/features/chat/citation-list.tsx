import { FileText, Share2 } from "lucide-react";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";

/** Reads a field defensively — used because `Message.citations` is
 * declared `Record<string, any>[]` at the backend schema layer (an
 * untyped JSON blob at persistence time), unlike the freshly-streamed
 * {@link import("@/lib/api/ai").RAGAnswer}'s strictly-typed
 * `EnrichedCitation[]`. Rather than assuming the persisted shape always
 * matches the live one, every field is read optionally here. */
function field(
  citation: Record<string, unknown>,
  key: string,
): string | number | null {
  const value = citation[key];
  return typeof value === "string" || typeof value === "number" ? value : null;
}

// Citation reference list — 57_Citation_Engine.md's seven required
// citation fields, rendered as a reference list with each citation
// navigable to its source (FR-CT-002). Kept as a compact reference list
// rather than inline markers since the backend returns citations as a
// flat array with no span offsets into `answer` to anchor inline markers.
export function CitationList({
  citations,
}: {
  citations: Record<string, unknown>[];
}) {
  if (citations.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {citations.map((citation, index) => {
        const entityId = field(citation, "entity_id");
        const documentId = field(citation, "document_id");
        const confidence = field(citation, "confidence");
        return (
          <Popover key={`${documentId ?? entityId ?? index}-${index}`}>
            <PopoverTrigger asChild>
              <button type="button">
                <Badge
                  variant="outline"
                  className="cursor-pointer gap-1 hover:bg-accent"
                >
                  {entityId ? (
                    <Share2 className="h-icon-xs w-icon-xs" />
                  ) : (
                    <FileText className="h-icon-xs w-icon-xs" />
                  )}
                  [{index + 1}]
                </Badge>
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-72 text-sm">
              <p className="font-medium">
                {field(citation, "document_name") ??
                  field(citation, "entity_name") ??
                  "Source"}
              </p>
              {field(citation, "chunk_index") !== null && (
                <p className="text-xs text-foreground-muted">
                  Chunk #{field(citation, "chunk_index")}
                </p>
              )}
              {field(citation, "version_number") !== null && (
                <p className="text-xs text-foreground-muted">
                  Version {field(citation, "version_number")}
                </p>
              )}
              {typeof confidence === "number" && (
                <p className="mt-2 text-xs text-foreground-muted">
                  Confidence: {Math.round(confidence * 100)}%
                </p>
              )}
            </PopoverContent>
          </Popover>
        );
      })}
    </div>
  );
}
