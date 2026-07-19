"use client";

import { StopCircle } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { formatStatusLabel, statusVariant } from "@/utils/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useStopSync, useSyncHistory } from "@/services/connectors";

export function SyncHistoryPanel({ connectorId }: { connectorId: string }) {
  const { data, isLoading } = useSyncHistory(connectorId);
  const stopSync = useStopSync();

  const handleStop = async (syncRunId: string) => {
    try {
      await stopSync.mutateAsync({ connectorId, syncRunId });
      toast.success("Sync stopped.");
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to stop sync.",
      );
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return <p className="text-sm text-foreground-muted">No sync runs yet.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {data.items.map((run) => (
        <div
          key={run.id}
          className="flex flex-col gap-2 rounded-md border border-border p-3 text-sm"
        >
          <div className="flex items-center justify-between">
            <span className="capitalize">{run.sync_type} sync</span>
            <Badge variant={statusVariant(run.status)}>
              {formatStatusLabel(run.status)}
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-1 text-xs text-foreground-muted">
            <span>Discovered: {run.items_discovered}</span>
            <span>Processed: {run.items_processed}</span>
            <span>Skipped: {run.items_skipped}</span>
            <span>Failed: {run.items_failed}</span>
          </div>
          <p className="text-xs text-foreground-muted">
            Started {new Date(run.started_at).toLocaleString()}
          </p>
          {run.error_message && (
            <p className="text-xs text-danger">{run.error_message}</p>
          )}
          {run.status === "running" && (
            <Button
              variant="outline"
              size="sm"
              className="w-fit gap-1.5"
              onClick={() => handleStop(run.id)}
            >
              <StopCircle className="h-icon-xs w-icon-xs" />
              Stop
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
