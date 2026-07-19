"use client";

import * as React from "react";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import { Plus, Trash2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  REQUIRED_CONFIG_KEYS,
  STEP_TYPES,
  STEP_TYPE_LABELS,
  type StepType,
  type WorkflowStep,
} from "@/features/workflows/step-types";

/**
 * Renders and edits a workflow's `steps` array as a strictly linear
 * node chain — the real backend model (see step-types.ts) has no
 * edge/branch field outside `condition`/`parallel`'s nested `config`,
 * so a freeform node graph would let the user draw connections the
 * execution engine can't express. Editing a `condition`/`parallel`
 * step's nested branches is done via its `config` JSON field directly
 * rather than a recursive sub-canvas — a deliberate scope limit.
 */
export function WorkflowEditor({
  steps,
  onChange,
}: {
  steps: WorkflowStep[];
  onChange: (steps: WorkflowStep[]) => void;
}) {
  const [selectedId, setSelectedId] = React.useState<string | null>(
    steps[0]?.id ?? null,
  );
  const selectedStep = steps.find((s) => s.id === selectedId) ?? null;

  const nodes: Node[] = steps.map((step, index) => ({
    id: step.id,
    position: { x: 40, y: index * 100 },
    data: { label: `${index + 1}. ${STEP_TYPE_LABELS[step.type]}` },
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    style: {
      border:
        step.id === selectedId
          ? "2px solid hsl(var(--primary))"
          : "1px solid hsl(var(--border))",
      borderRadius: 8,
      padding: 8,
      fontSize: 12,
      background: "hsl(var(--card))",
      color: "hsl(var(--foreground))",
      width: 200,
    },
  }));

  const edges: Edge[] = [];
  for (let i = 1; i < steps.length; i += 1) {
    const previous = steps[i - 1];
    const current = steps[i];
    if (previous && current) {
      edges.push({
        id: `${previous.id}-${current.id}`,
        source: previous.id,
        target: current.id,
      });
    }
  }

  const addStep = () => {
    const id = `step-${Date.now().toString(36)}`;
    const newStep: WorkflowStep = { id, type: "ai_reasoning", config: {} };
    onChange([...steps, newStep]);
    setSelectedId(id);
  };

  const removeStep = (id: string) => {
    onChange(steps.filter((s) => s.id !== id));
    if (selectedId === id) setSelectedId(null);
  };

  const updateStep = (id: string, patch: Partial<WorkflowStep>) => {
    onChange(steps.map((s) => (s.id === id ? { ...s, ...patch } : s)));
  };

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
      <div className="flex h-96 flex-col gap-2 rounded-lg border border-border">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodeClick={(_, node) => setSelectedId(node.id)}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="flex flex-col gap-3">
        <Button variant="outline" className="gap-1.5" onClick={addStep}>
          <Plus className="h-icon-sm w-icon-sm" />
          Add step
        </Button>
        {selectedStep ? (
          <StepEditor
            key={selectedStep.id}
            step={selectedStep}
            onChange={(patch) => updateStep(selectedStep.id, patch)}
            onRemove={() => removeStep(selectedStep.id)}
          />
        ) : (
          <p className="text-sm text-foreground-muted">
            Select a step to edit it, or add a new one.
          </p>
        )}
      </div>
    </div>
  );
}

function StepEditor({
  step,
  onChange,
  onRemove,
}: {
  step: WorkflowStep;
  onChange: (patch: Partial<WorkflowStep>) => void;
  onRemove: () => void;
}) {
  const [configText, setConfigText] = React.useState(
    JSON.stringify(step.config, null, 2),
  );
  const [configError, setConfigError] = React.useState<string | null>(null);
  const requiredKeys = REQUIRED_CONFIG_KEYS[step.type];

  const applyConfig = (text: string) => {
    setConfigText(text);
    try {
      const parsed: unknown = JSON.parse(text || "{}");
      if (
        typeof parsed !== "object" ||
        parsed === null ||
        Array.isArray(parsed)
      ) {
        throw new Error("Config must be a JSON object.");
      }
      setConfigError(null);
      onChange({ config: parsed as Record<string, unknown> });
    } catch {
      setConfigError("Invalid JSON.");
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border p-3">
      <div className="flex items-center justify-between">
        <Label>Step ID</Label>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={onRemove}
        >
          <Trash2 className="h-icon-xs w-icon-xs text-danger" />
        </Button>
      </div>
      <Input value={step.id} disabled />

      <Label>Type</Label>
      <Select
        value={step.type}
        onValueChange={(value) =>
          onChange({ type: value as StepType, config: {} })
        }
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {STEP_TYPES.map((type) => (
            <SelectItem key={type} value={type}>
              {STEP_TYPE_LABELS[type]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="flex items-center justify-between">
        <Label>Config (JSON)</Label>
        <div className="flex gap-1">
          {requiredKeys.map((key) => (
            <Badge key={key} variant="outline" className="text-[10px]">
              {key}
            </Badge>
          ))}
        </div>
      </div>
      <Textarea
        value={configText}
        onChange={(e) => applyConfig(e.target.value)}
        className={cn(
          "min-h-32 font-mono text-xs",
          configError && "border-danger",
        )}
      />
      {configError && <p className="text-xs text-danger">{configError}</p>}
    </div>
  );
}
