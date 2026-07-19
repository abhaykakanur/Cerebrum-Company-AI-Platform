import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { statusVariant, formatStatusLabel } from "@/utils/status";
import type { HealthResponse } from "@/lib/api/health";

export function HealthPanel({
  health,
  loading,
}: {
  health: HealthResponse | undefined;
  loading: boolean;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>System Health</CardTitle>
        {health && (
          <Badge variant={statusVariant(health.status)}>
            {formatStatusLabel(health.status)}
          </Badge>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {loading || !health ? (
          <>
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-full" />
          </>
        ) : (
          health.components.map((component) => (
            <div
              key={component.name}
              className="flex items-center justify-between text-sm"
            >
              <span className="capitalize">{component.name}</span>
              <Badge variant={statusVariant(component.status)}>
                {formatStatusLabel(component.status)}
              </Badge>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
