"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import type { TriggerType } from "@/lib/api/workflows";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { WorkflowEditor } from "@/features/workflows/workflow-editor";
import type { WorkflowStep } from "@/features/workflows/step-types";
import { useCreateWorkflow } from "@/services/workflows";

const TRIGGER_TYPES: TriggerType[] = [
  "manual",
  "scheduled",
  "connector_sync_completed",
  "document_uploaded",
  "knowledge_updated",
  "api_request",
  "custom_event",
];

export default function NewWorkflowPage() {
  const router = useRouter();
  const createWorkflow = useCreateWorkflow();
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [triggerType, setTriggerType] = React.useState<TriggerType>("manual");
  const [isTemplate, setIsTemplate] = React.useState(false);
  const [steps, setSteps] = React.useState<WorkflowStep[]>([]);

  const handleSave = async () => {
    if (steps.length === 0) {
      toast.error("A workflow must define at least one step.");
      return;
    }
    try {
      const workflow = await createWorkflow.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        trigger_type: triggerType,
        steps: steps as unknown as Record<string, unknown>[],
        is_template: isTemplate,
      });
      toast.success("Workflow created.");
      router.push(`/workflows/${workflow.id}`);
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to create workflow.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-h1 font-semibold">New Workflow</h1>
        <p className="text-sm text-foreground-muted">
          Define a trigger and a sequence of steps.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="workflow-name">Name</Label>
          <Input
            id="workflow-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label>Trigger</Label>
          <Select
            value={triggerType}
            onValueChange={(v) => setTriggerType(v as TriggerType)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TRIGGER_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {type.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-2 sm:col-span-2">
          <Label htmlFor="workflow-description">Description</Label>
          <Textarea
            id="workflow-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Checkbox
            id="is-template"
            checked={isTemplate}
            onCheckedChange={(v) => setIsTemplate(v === true)}
          />
          <Label htmlFor="is-template">Save as reusable template</Label>
        </div>
      </div>

      <WorkflowEditor steps={steps} onChange={setSteps} />

      <div className="flex justify-end">
        <Button
          onClick={handleSave}
          loading={createWorkflow.isPending}
          disabled={!name.trim()}
        >
          Create workflow
        </Button>
      </div>
    </div>
  );
}
