"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  cancelWorkflowRun,
  createWorkflow,
  createWorkflowSchedule,
  deleteWorkflow,
  deleteWorkflowSchedule,
  executeWorkflow,
  getWorkflow,
  getWorkflowRunSteps,
  listWorkflowRuns,
  listWorkflowSchedules,
  listWorkflowTemplates,
  listWorkflows,
  pauseWorkflow,
  resumeWorkflow,
  retryWorkflowRun,
  type CreateWorkflowRequest,
  type ScheduleType,
  type WorkflowStatus,
} from "@/lib/api/workflows";

const LIST_KEY = ["workflows"];

export function useWorkflows(status?: WorkflowStatus) {
  return useQuery({
    queryKey: [...LIST_KEY, status],
    queryFn: () => listWorkflows(status, 1, 100),
  });
}

export function useWorkflowTemplates() {
  return useQuery({
    queryKey: ["workflow-templates"],
    queryFn: () => listWorkflowTemplates(1, 100),
  });
}

export function useWorkflow(workflowId: string | null) {
  return useQuery({
    queryKey: ["workflow", workflowId],
    queryFn: () => getWorkflow(workflowId as string),
    enabled: workflowId !== null,
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateWorkflowRequest) => createWorkflow(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: LIST_KEY });
      void queryClient.invalidateQueries({ queryKey: ["workflow-templates"] });
    },
  });
}

export function useDeleteWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteWorkflow(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

export function useTogglePauseWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, pause }: { id: string; pause: boolean }) =>
      pause ? pauseWorkflow(id) : resumeWorkflow(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

export function useExecuteWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => executeWorkflow(id),
    onSuccess: (_data, id) =>
      queryClient.invalidateQueries({ queryKey: ["workflow-runs", id] }),
  });
}

export function useWorkflowRuns(workflowId: string | null) {
  return useQuery({
    queryKey: ["workflow-runs", workflowId],
    queryFn: () => listWorkflowRuns(workflowId as string, 1, 50),
    enabled: workflowId !== null,
    refetchInterval: 5000,
  });
}

export function useWorkflowRunSteps(
  workflowId: string | null,
  runId: string | null,
) {
  return useQuery({
    queryKey: ["workflow-run-steps", workflowId, runId],
    queryFn: () => getWorkflowRunSteps(workflowId as string, runId as string),
    enabled: workflowId !== null && runId !== null,
  });
}

export function useCancelWorkflowRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      workflowId,
      runId,
    }: {
      workflowId: string;
      runId: string;
    }) => cancelWorkflowRun(workflowId, runId),
    onSuccess: (_data, variables) =>
      queryClient.invalidateQueries({
        queryKey: ["workflow-runs", variables.workflowId],
      }),
  });
}

export function useRetryWorkflowRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      workflowId,
      runId,
    }: {
      workflowId: string;
      runId: string;
    }) => retryWorkflowRun(workflowId, runId),
    onSuccess: (_data, variables) =>
      queryClient.invalidateQueries({
        queryKey: ["workflow-runs", variables.workflowId],
      }),
  });
}

export function useWorkflowSchedules(workflowId: string | null) {
  return useQuery({
    queryKey: ["workflow-schedules", workflowId],
    queryFn: () => listWorkflowSchedules(workflowId as string),
    enabled: workflowId !== null,
  });
}

export function useCreateWorkflowSchedule(workflowId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      schedule_type: ScheduleType;
      cron_expression?: string;
      run_at?: string;
    }) => createWorkflowSchedule(workflowId, body),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["workflow-schedules", workflowId],
      }),
  });
}

export function useDeleteWorkflowSchedule(workflowId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scheduleId: string) =>
      deleteWorkflowSchedule(workflowId, scheduleId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["workflow-schedules", workflowId],
      }),
  });
}
