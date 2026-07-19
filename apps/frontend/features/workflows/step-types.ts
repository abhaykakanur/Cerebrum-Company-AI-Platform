/** Mirrors apps/backend/src/cerebrum/infrastructure/database/models/
 * workflow_version.py's `StepType` enum and
 * apps/backend/src/cerebrum/application/workflows/validation.py's
 * `_REQUIRED_STEP_CONFIG_KEYS` — the only real, backend-validated step
 * shape. A step is `{ id, type, config: {...required keys...} }`;
 * execution order is array order (no separate edge/"next" field exists
 * server-side), which is why the visual editor renders steps as a
 * strictly linear chain rather than an arbitrary node graph. */
export type StepType =
  | "connector_action"
  | "ai_reasoning"
  | "retrieval"
  | "search"
  | "notification"
  | "custom"
  | "condition"
  | "delay"
  | "parallel";

export const STEP_TYPES: StepType[] = [
  "connector_action",
  "ai_reasoning",
  "retrieval",
  "search",
  "notification",
  "custom",
  "condition",
  "delay",
  "parallel",
];

export const REQUIRED_CONFIG_KEYS: Record<StepType, string[]> = {
  connector_action: ["connector_id"],
  ai_reasoning: ["question"],
  retrieval: ["query"],
  search: ["query"],
  notification: ["message"],
  custom: ["handler"],
  condition: ["condition", "then"],
  delay: ["seconds"],
  parallel: ["steps"],
};

export interface WorkflowStep {
  id: string;
  type: StepType;
  config: Record<string, unknown>;
}

export const STEP_TYPE_LABELS: Record<StepType, string> = {
  connector_action: "Connector Action",
  ai_reasoning: "AI Reasoning",
  retrieval: "Retrieval",
  search: "Search",
  notification: "Notification",
  custom: "Custom",
  condition: "Condition",
  delay: "Delay",
  parallel: "Parallel",
};
