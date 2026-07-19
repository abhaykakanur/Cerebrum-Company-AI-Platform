/** Workflows API — mirrors apps/backend/src/cerebrum/api/v1/workflows.py. */

import {
  apiGet,
  apiGetPage,
  apiSend,
  type PaginationMeta,
} from "@/lib/api/client";

export type WorkflowStatus = "draft" | "active" | "paused" | "archived";
export type TriggerType =
  | "manual"
  | "scheduled"
  | "connector_sync_completed"
  | "document_uploaded"
  | "knowledge_updated"
  | "api_request"
  | "custom_event";
export type ScheduleType = "cron" | "one_time";

export interface Workflow {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  status: string;
  is_template: boolean;
  current_version_id: string | null;
  workflow_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  workflow_version_id: string;
  status: string;
  trigger_type: string;
  trigger_context: Record<string, unknown>;
  variables: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface WorkflowStepRun {
  id: string;
  workflow_run_id: string;
  step_id: string;
  step_type: string;
  status: string;
  attempt: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  output: Record<string, unknown>;
  error_message: string | null;
}

export interface WorkflowSchedule {
  id: string;
  workflow_id: string;
  schedule_type: string;
  cron_expression: string | null;
  run_at: string | null;
  status: string;
  next_run_at: string | null;
  last_run_at: string | null;
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  trigger_type: TriggerType;
  trigger_config?: Record<string, unknown>;
  steps: Record<string, unknown>[];
  workflow_metadata?: Record<string, unknown>;
  is_template?: boolean;
}

export async function listWorkflows(
  status?: WorkflowStatus,
  page = 1,
  pageSize = 50,
): Promise<{ items: Workflow[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Workflow>("/workflows", {
    query: { workflow_status: status, page, page_size: pageSize },
  });
}

export async function listWorkflowTemplates(
  page = 1,
  pageSize = 50,
): Promise<{ items: Workflow[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Workflow>("/workflows/templates", {
    query: { page, page_size: pageSize },
  });
}

export async function createWorkflow(
  body: CreateWorkflowRequest,
): Promise<Workflow> {
  return apiSend<Workflow>("/workflows", "POST", body);
}

export async function getWorkflow(workflowId: string): Promise<Workflow> {
  return apiGet<Workflow>(`/workflows/${workflowId}`);
}

export async function pauseWorkflow(workflowId: string): Promise<Workflow> {
  return apiSend<Workflow>(`/workflows/${workflowId}/pause`, "POST");
}

export async function resumeWorkflow(workflowId: string): Promise<Workflow> {
  return apiSend<Workflow>(`/workflows/${workflowId}/resume`, "POST");
}

export async function deleteWorkflow(workflowId: string): Promise<void> {
  return apiSend<void>(`/workflows/${workflowId}`, "DELETE");
}

export async function executeWorkflow(
  workflowId: string,
  variables: Record<string, unknown> = {},
): Promise<WorkflowRun> {
  return apiSend<WorkflowRun>(`/workflows/${workflowId}/execute`, "POST", {
    variables,
  });
}

export async function listWorkflowRuns(
  workflowId: string,
  page = 1,
  pageSize = 50,
): Promise<{ items: WorkflowRun[]; pagination: PaginationMeta | null }> {
  return apiGetPage<WorkflowRun>(`/workflows/${workflowId}/runs`, {
    query: { page, page_size: pageSize },
  });
}

export async function getWorkflowRunSteps(
  workflowId: string,
  runId: string,
): Promise<WorkflowStepRun[]> {
  return apiGet<WorkflowStepRun[]>(
    `/workflows/${workflowId}/runs/${runId}/steps`,
  );
}

export async function cancelWorkflowRun(
  workflowId: string,
  runId: string,
): Promise<WorkflowRun> {
  return apiSend<WorkflowRun>(
    `/workflows/${workflowId}/runs/${runId}/cancel`,
    "POST",
  );
}

export async function retryWorkflowRun(
  workflowId: string,
  runId: string,
): Promise<WorkflowRun> {
  return apiSend<WorkflowRun>(
    `/workflows/${workflowId}/runs/${runId}/retry`,
    "POST",
  );
}

export async function listWorkflowSchedules(
  workflowId: string,
): Promise<WorkflowSchedule[]> {
  return apiGet<WorkflowSchedule[]>(`/workflows/${workflowId}/schedules`);
}

export async function createWorkflowSchedule(
  workflowId: string,
  body: {
    schedule_type: ScheduleType;
    cron_expression?: string;
    run_at?: string;
  },
): Promise<WorkflowSchedule> {
  return apiSend<WorkflowSchedule>(
    `/workflows/${workflowId}/schedules`,
    "POST",
    body,
  );
}

export async function deleteWorkflowSchedule(
  workflowId: string,
  scheduleId: string,
): Promise<void> {
  return apiSend<void>(
    `/workflows/${workflowId}/schedules/${scheduleId}`,
    "DELETE",
  );
}
