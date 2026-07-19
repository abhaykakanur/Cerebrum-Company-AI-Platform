"use client";

import * as React from "react";
import { RotateCcw, StopCircle } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { formatStatusLabel, statusVariant } from "@/utils/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCancelWorkflowRun,
  useRetryWorkflowRun,
  useWorkflowRunSteps,
  useWorkflowRuns,
} from "@/services/workflows";

function RunSteps({
  workflowId,
  runId,
}: {
  workflowId: string;
  runId: string;
}) {
  const { data: steps, isLoading } = useWorkflowRunSteps(workflowId, runId);
  if (isLoading) return <Skeleton className="h-12 w-full" />;
  if (!steps || steps.length === 0)
    return <p className="text-xs text-foreground-muted">No step data.</p>;
  return (
    <div className="flex flex-col gap-1.5 border-t border-border pt-2">
      {steps.map((step) => (
        <div
          key={step.id}
          className="flex items-center justify-between text-xs"
        >
          <span>
            {step.step_id}{" "}
            <span className="text-foreground-muted">({step.step_type})</span>
          </span>
          <div className="flex items-center gap-2">
            {step.duration_ms !== null && (
              <span className="text-foreground-muted">
                {step.duration_ms}ms
              </span>
            )}
            <Badge variant={statusVariant(step.status)}>
              {formatStatusLabel(step.status)}
            </Badge>
          </div>
        </div>
      ))}
    </div>
  );
}

export function RunHistory({ workflowId }: { workflowId: string }) {
  const { data, isLoading } = useWorkflowRuns(workflowId);
  const [expanded, setExpanded] = React.useState<string | null>(null);
  const cancelRun = useCancelWorkflowRun();
  const retryRun = useRetryWorkflowRun();

  const handleCancel = async (runId: string) => {
    try {
      await cancelRun.mutateAsync({ workflowId, runId });
      toast.success("Run cancelled.");
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to cancel run.",
      );
    }
  };

  const handleRetry = async (runId: string) => {
    try {
      await retryRun.mutateAsync({ workflowId, runId });
      toast.success("Run retried.");
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to retry run.",
      );
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return <p className="text-sm text-foreground-muted">No runs yet.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      {data.items.map((run) => (
        <div key={run.id} className="rounded-md border border-border p-3">
          <button
            type="button"
            className="flex w-full items-center justify-between text-left text-sm"
            onClick={() => setExpanded(expanded === run.id ? null : run.id)}
          >
            <span className="capitalize">{run.trigger_type} trigger</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-foreground-muted">
                {run.started_at
                  ? new Date(run.started_at).toLocaleString()
                  : "Pending"}
              </span>
              <Badge variant={statusVariant(run.status)}>
                {formatStatusLabel(run.status)}
              </Badge>
            </div>
          </button>
          {run.error_message && (
            <p className="mt-1 text-xs text-danger">{run.error_message}</p>
          )}
          <div className="mt-2 flex gap-2">
            {run.status === "running" && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => handleCancel(run.id)}
              >
                <StopCircle className="h-icon-xs w-icon-xs" />
                Cancel
              </Button>
            )}
            {run.status === "failed" && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => handleRetry(run.id)}
              >
                <RotateCcw className="h-icon-xs w-icon-xs" />
                Retry
              </Button>
            )}
          </div>
          {expanded === run.id && (
            <RunSteps workflowId={workflowId} runId={run.id} />
          )}
        </div>
      ))}
    </div>
  );
}
