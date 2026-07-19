import { formatStatusLabel } from "@/utils/status";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useEntityDetail, useEntityRelationships } from "@/services/graph";

export function GraphContextPanel({ entityId }: { entityId: string | null }) {
  const { data: entity, isLoading: entityLoading } = useEntityDetail(entityId);
  const { data: relationships, isLoading: relLoading } =
    useEntityRelationships(entityId);

  if (!entityId) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-center text-sm text-foreground-muted">
        Select a node to see its details.
      </div>
    );
  }

  if (entityLoading || !entity) {
    return (
      <div className="flex flex-col gap-3 p-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-4">
      <div>
        <Badge variant="outline" className="mb-2 capitalize">
          {entity.entity_type}
        </Badge>
        <h3 className="text-h3 font-semibold">{entity.canonical_name}</h3>
        {entity.description && (
          <p className="mt-1 text-sm text-foreground-muted">
            {entity.description}
          </p>
        )}
      </div>

      {entity.aliases.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-foreground-muted">
            Aliases
          </p>
          <div className="flex flex-wrap gap-1">
            {entity.aliases.map((alias) => (
              <Badge key={alias} variant="outline">
                {alias}
              </Badge>
            ))}
          </div>
        </div>
      )}

      <div>
        <p className="mb-1 text-xs font-medium text-foreground-muted">
          Confidence
        </p>
        <p className="text-sm">{Math.round(entity.confidence * 100)}%</p>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium text-foreground-muted">
          Relationships{" "}
          {relationships &&
            `(${relationships.pagination?.total_items ?? relationships.items.length})`}
        </p>
        {relLoading && <Skeleton className="h-16 w-full" />}
        <div className="flex flex-col gap-2">
          {relationships?.items.map((rel) => (
            <div
              key={rel.id}
              className="flex items-center justify-between rounded-sm border border-border p-2 text-xs"
            >
              <span>
                {formatStatusLabel(
                  rel.custom_type_name ?? rel.relationship_type,
                )}
              </span>
              <Badge variant="outline">
                {Math.round(rel.confidence * 100)}%
              </Badge>
            </div>
          ))}
          {relationships && relationships.items.length === 0 && (
            <p className="text-xs text-foreground-muted">
              No outgoing relationships.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
