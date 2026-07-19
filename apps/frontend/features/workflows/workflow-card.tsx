"use client";

import Link from "next/link";
import { Pause, Play, Trash2, Zap } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { formatStatusLabel, statusVariant } from "@/utils/status";
import type { Workflow } from "@/lib/api/workflows";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useDeleteWorkflow,
  useExecuteWorkflow,
  useTogglePauseWorkflow,
} from "@/services/workflows";

export function WorkflowCard({ workflow }: { workflow: Workflow }) {
  const togglePause = useTogglePauseWorkflow();
  const execute = useExecuteWorkflow();
  const deleteWorkflow = useDeleteWorkflow();

  const handleExecute = async () => {
    try {
      await execute.mutateAsync(workflow.id);
      toast.success("Workflow execution started.");
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to execute workflow.",
      );
    }
  };

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div className="min-w-0">
          <CardTitle className="truncate text-base">
            <Link
              href={`/workflows/${workflow.id}`}
              className="hover:underline"
            >
              {workflow.name}
            </Link>
          </CardTitle>
          {workflow.description && (
            <p className="truncate text-xs text-foreground-muted">
              {workflow.description}
            </p>
          )}
        </div>
        <Badge variant={statusVariant(workflow.status)}>
          {formatStatusLabel(workflow.status)}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={handleExecute}
          loading={execute.isPending}
        >
          <Zap className="h-icon-xs w-icon-xs" />
          Run now
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() =>
            togglePause.mutate({
              id: workflow.id,
              pause: workflow.status === "active",
            })
          }
        >
          {workflow.status === "active" ? (
            <>
              <Pause className="h-icon-xs w-icon-xs" />
              Pause
            </>
          ) : (
            <>
              <Play className="h-icon-xs w-icon-xs" />
              Resume
            </>
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto h-8 w-8"
          onClick={() => deleteWorkflow.mutate(workflow.id)}
        >
          <Trash2 className="h-icon-xs w-icon-xs text-danger" />
        </Button>
      </CardContent>
    </Card>
  );
}
