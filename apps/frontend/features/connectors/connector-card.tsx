"use client";

import { HeartPulse, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { formatStatusLabel, statusVariant } from "@/utils/status";
import type { Connector } from "@/lib/api/connectors";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useCheckConnectorHealth,
  useDeleteConnector,
  useStartSync,
} from "@/services/connectors";

export function ConnectorCard({
  connector,
  onOpenHistory,
}: {
  connector: Connector;
  onOpenHistory: () => void;
}) {
  const checkHealth = useCheckConnectorHealth();
  const startSync = useStartSync();
  const deleteConnector = useDeleteConnector();

  const handleSync = async () => {
    try {
      await startSync.mutateAsync({ id: connector.id });
      toast.success("Sync started.");
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to start sync.",
      );
    }
  };

  const handleDelete = async () => {
    try {
      await deleteConnector.mutateAsync(connector.id);
      toast.success(`"${connector.name}" removed.`);
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to remove connector.",
      );
    }
  };

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="text-base">{connector.name}</CardTitle>
          <p className="text-xs capitalize text-foreground-muted">
            {connector.connector_type}
          </p>
        </div>
        <Badge variant={statusVariant(connector.status)}>
          {formatStatusLabel(connector.status)}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-center justify-between text-xs">
          <span className="text-foreground-muted">Health</span>
          <Badge variant={statusVariant(connector.health_status)}>
            {formatStatusLabel(connector.health_status)}
          </Badge>
        </div>
        {connector.health_message && (
          <p className="text-xs text-foreground-muted">
            {connector.health_message}
          </p>
        )}
        <div className="flex items-center justify-between text-xs text-foreground-muted">
          <span>Last sync</span>
          <span>
            {connector.last_sync_at
              ? new Date(connector.last_sync_at).toLocaleString()
              : "Never"}
          </span>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={handleSync}
            loading={startSync.isPending}
          >
            <RefreshCw className="h-icon-xs w-icon-xs" />
            Sync now
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => checkHealth.mutate(connector.id)}
            loading={checkHealth.isPending}
          >
            <HeartPulse className="h-icon-xs w-icon-xs" />
            Check health
          </Button>
          <Button variant="ghost" size="sm" onClick={onOpenHistory}>
            View history
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-8 w-8"
            onClick={handleDelete}
          >
            <Trash2 className="h-icon-xs w-icon-xs text-danger" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
