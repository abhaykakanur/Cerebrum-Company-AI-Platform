"use client";

import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/lib/api/health";
import { getRetrievalStatistics } from "@/lib/api/retrieval";
import { getAIStatistics } from "@/lib/api/ai";
import { formatStatusLabel, statusVariant } from "@/utils/status";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ResponsiveGrid } from "@/components/ui/responsive-grid";
import { Skeleton } from "@/components/ui/skeleton";
import { AiUsageChart } from "@/features/monitoring/ai-usage-chart";
import { useConnectors } from "@/services/connectors";

export default function MonitoringPage() {
  const health = useQuery({
    queryKey: ["monitoring", "health"],
    queryFn: getHealth,
    refetchInterval: 15_000,
  });
  const retrievalStats = useQuery({
    queryKey: ["monitoring", "retrieval-statistics"],
    queryFn: getRetrievalStatistics,
  });
  const aiStats = useQuery({
    queryKey: ["monitoring", "ai-statistics"],
    queryFn: getAIStatistics,
  });
  const connectors = useConnectors();

  const aiUsageData = aiStats.data
    ? Object.entries(aiStats.data.providers).map(([provider, count]) => ({
        provider,
        count,
      }))
    : [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-h1 font-semibold">Monitoring</h1>
        <p className="text-sm text-foreground-muted">
          System health, connector health, and knowledge index statistics.
        </p>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle>System Health</CardTitle>
          {health.data && (
            <div className="flex items-center gap-2 text-xs text-foreground-muted">
              <span>v{health.data.version}</span>
              <span>· {health.data.environment}</span>
              <span>· up {Math.floor(health.data.uptime_seconds / 3600)}h</span>
              <Badge variant={statusVariant(health.data.status)}>
                {formatStatusLabel(health.data.status)}
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {health.isLoading && <Skeleton className="h-24 w-full" />}
          <ResponsiveGrid cols={3}>
            {health.data?.components.map((component) => (
              <div
                key={component.name}
                className="flex flex-col gap-1 rounded-md border border-border p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm capitalize">{component.name}</span>
                  <Badge variant={statusVariant(component.status)}>
                    {formatStatusLabel(component.status)}
                  </Badge>
                </div>
                {component.detail && (
                  <p className="text-xs text-foreground-muted">
                    {component.detail}
                  </p>
                )}
              </div>
            ))}
          </ResponsiveGrid>
        </CardContent>
      </Card>

      <ResponsiveGrid cols={4}>
        <Card glass>
          <CardHeader>
            <CardTitle className="text-sm text-foreground-muted">
              Vector Index Size
            </CardTitle>
          </CardHeader>
          <CardContent>
            {retrievalStats.isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <p className="text-h2 font-semibold">
                {retrievalStats.data?.vector_count ?? 0}
              </p>
            )}
          </CardContent>
        </Card>
        <Card glass>
          <CardHeader>
            <CardTitle className="text-sm text-foreground-muted">
              Indexed Documents
            </CardTitle>
          </CardHeader>
          <CardContent>
            {retrievalStats.isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <p className="text-h2 font-semibold">
                {retrievalStats.data?.indexed_document_count ?? 0}
              </p>
            )}
          </CardContent>
        </Card>
        <Card glass>
          <CardHeader>
            <CardTitle className="text-sm text-foreground-muted">
              Graph Entities
            </CardTitle>
          </CardHeader>
          <CardContent>
            {retrievalStats.isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <p className="text-h2 font-semibold">
                {retrievalStats.data?.entity_count ?? 0}
              </p>
            )}
          </CardContent>
        </Card>
        <Card glass>
          <CardHeader>
            <CardTitle className="text-sm text-foreground-muted">
              Graph Relationships
            </CardTitle>
          </CardHeader>
          <CardContent>
            {retrievalStats.isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <p className="text-h2 font-semibold">
                {retrievalStats.data?.relationship_count ?? 0}
              </p>
            )}
          </CardContent>
        </Card>
      </ResponsiveGrid>

      <ResponsiveGrid cols={2}>
        <Card>
          <CardHeader>
            <CardTitle>AI Usage by Provider</CardTitle>
          </CardHeader>
          <CardContent>
            {aiStats.isLoading ? (
              <Skeleton className="h-56 w-full" />
            ) : (
              <AiUsageChart data={aiUsageData} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Connector Health</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {connectors.isLoading && <Skeleton className="h-32 w-full" />}
            {!connectors.isLoading && connectors.data?.items.length === 0 && (
              <p className="text-sm text-foreground-muted">
                No connectors registered.
              </p>
            )}
            {connectors.data?.items.map((connector) => (
              <div
                key={connector.id}
                className="flex items-center justify-between rounded-md border border-border p-2 text-sm"
              >
                <span>{connector.name}</span>
                <Badge variant={statusVariant(connector.health_status)}>
                  {formatStatusLabel(connector.health_status)}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </ResponsiveGrid>
    </div>
  );
}
