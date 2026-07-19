"use client";

import * as React from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import type { ScheduleType } from "@/lib/api/workflows";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCreateWorkflowSchedule,
  useDeleteWorkflowSchedule,
  useWorkflowSchedules,
} from "@/services/workflows";

export function ScheduleManager({ workflowId }: { workflowId: string }) {
  const { data: schedules, isLoading } = useWorkflowSchedules(workflowId);
  const createSchedule = useCreateWorkflowSchedule(workflowId);
  const deleteSchedule = useDeleteWorkflowSchedule(workflowId);
  const [scheduleType, setScheduleType] = React.useState<ScheduleType>("cron");
  const [cronExpression, setCronExpression] = React.useState("0 0 * * *");
  const [runAt, setRunAt] = React.useState("");

  const handleCreate = async () => {
    try {
      await createSchedule.mutateAsync(
        scheduleType === "cron"
          ? { schedule_type: "cron", cron_expression: cronExpression }
          : { schedule_type: "one_time", run_at: runAt },
      );
      toast.success("Schedule created.");
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to create schedule.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex flex-col gap-1">
          <Label>Type</Label>
          <Select
            value={scheduleType}
            onValueChange={(v) => setScheduleType(v as ScheduleType)}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="cron">Cron</SelectItem>
              <SelectItem value="one_time">One-time</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {scheduleType === "cron" ? (
          <div className="flex flex-col gap-1">
            <Label>Cron expression</Label>
            <Input
              className="w-48 font-mono text-xs"
              value={cronExpression}
              onChange={(e) => setCronExpression(e.target.value)}
            />
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            <Label>Run at</Label>
            <Input
              type="datetime-local"
              value={runAt}
              onChange={(e) => setRunAt(e.target.value)}
            />
          </div>
        )}
        <Button
          size="sm"
          className="gap-1.5"
          onClick={handleCreate}
          loading={createSchedule.isPending}
        >
          <Plus className="h-icon-xs w-icon-xs" />
          Add
        </Button>
      </div>

      {isLoading && <Skeleton className="h-10 w-full" />}
      <div className="flex flex-col gap-2">
        {schedules?.map((schedule) => (
          <div
            key={schedule.id}
            className="flex items-center justify-between rounded-md border border-border p-2 text-sm"
          >
            <div>
              <p className="font-mono text-xs">
                {schedule.cron_expression ?? schedule.run_at}
              </p>
              <p className="text-xs text-foreground-muted">
                Next:{" "}
                {schedule.next_run_at
                  ? new Date(schedule.next_run_at).toLocaleString()
                  : "—"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{schedule.status}</Badge>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => deleteSchedule.mutate(schedule.id)}
              >
                <Trash2 className="h-icon-xs w-icon-xs text-danger" />
              </Button>
            </div>
          </div>
        ))}
        {schedules?.length === 0 && (
          <p className="text-sm text-foreground-muted">
            No schedules configured.
          </p>
        )}
      </div>
    </div>
  );
}
