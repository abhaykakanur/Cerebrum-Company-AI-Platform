"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  checkConnectorHealth,
  deleteConnector,
  getSyncHistory,
  listConnectors,
  registerConnector,
  startSync,
  stopSync,
  type RegisterConnectorRequest,
  type SyncType,
} from "@/lib/api/connectors";

const LIST_KEY = ["connectors"];

export function useConnectors() {
  return useQuery({
    queryKey: LIST_KEY,
    queryFn: () => listConnectors(undefined, undefined, 1, 100),
  });
}

export function useRegisterConnector() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: RegisterConnectorRequest) => registerConnector(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

export function useDeleteConnector() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteConnector(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

export function useCheckConnectorHealth() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => checkConnectorHealth(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

export function useStartSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, syncType }: { id: string; syncType?: SyncType }) =>
      startSync(id, syncType),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: LIST_KEY });
      void queryClient.invalidateQueries({
        queryKey: ["sync-history", variables.id],
      });
    },
  });
}

export function useStopSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      connectorId,
      syncRunId,
    }: {
      connectorId: string;
      syncRunId: string;
    }) => stopSync(connectorId, syncRunId),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["sync-history", variables.connectorId],
      });
    },
  });
}

export function useSyncHistory(connectorId: string | null) {
  return useQuery({
    queryKey: ["sync-history", connectorId],
    queryFn: () => getSyncHistory(connectorId as string, 1, 50),
    enabled: connectorId !== null,
    refetchInterval: 5000,
  });
}
