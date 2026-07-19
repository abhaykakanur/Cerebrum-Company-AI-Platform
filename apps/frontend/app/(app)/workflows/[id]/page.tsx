"use client";

import { useParams } from "next/navigation";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { formatStatusLabel, statusVariant } from "@/utils/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RunHistory } from "@/features/workflows/run-history";
import { ScheduleManager } from "@/features/workflows/schedule-manager";
import { useExecuteWorkflow, useWorkflow } from "@/services/workflows";

export default function WorkflowDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: workflow, isLoading } = useWorkflow(params.id);
  const execute = useExecuteWorkflow();

  const handleExecute = async () => {
    try {
      await execute.mutateAsync(params.id);
      toast.success("Workflow execution started.");
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to execute workflow.",
      );
    }
  };

  if (isLoading || !workflow) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-h1 font-semibold">{workflow.name}</h1>
            <Badge variant={statusVariant(workflow.status)}>
              {formatStatusLabel(workflow.status)}
            </Badge>
          </div>
          {workflow.description && (
            <p className="text-sm text-foreground-muted">
              {workflow.description}
            </p>
          )}
        </div>
        <Button onClick={handleExecute} loading={execute.isPending}>
          Run now
        </Button>
      </div>

      <Tabs defaultValue="runs">
        <TabsList>
          <TabsTrigger value="runs">Execution History</TabsTrigger>
          <TabsTrigger value="schedules">Scheduling</TabsTrigger>
        </TabsList>
        <TabsContent value="runs">
          <RunHistory workflowId={workflow.id} />
        </TabsContent>
        <TabsContent value="schedules">
          <ScheduleManager workflowId={workflow.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
