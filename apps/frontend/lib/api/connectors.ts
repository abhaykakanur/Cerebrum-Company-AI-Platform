/** Connectors API — mirrors apps/backend/src/cerebrum/api/v1/connectors.py. */

import {
  apiGet,
  apiGetPage,
  apiSend,
  type PaginationMeta,
} from "@/lib/api/client";

export type ConnectorType =
  | "github"
  | "gitlab"
  | "bitbucket"
  | "jira"
  | "azure_devops"
  | "confluence"
  | "notion"
  | "slack"
  | "teams";

export type ConnectorAuthType =
  "oauth2" | "personal_access_token" | "api_key" | "service_account";
export type SyncType = "initial" | "incremental" | "manual" | "full_resync";

export interface Connector {
  id: string;
  workspace_id: string;
  connector_type: string;
  name: string;
  status: string;
  auth_type: string;
  config: Record<string, unknown>;
  health_status: string;
  health_checked_at: string | null;
  health_message: string | null;
  sync_interval_seconds: number | null;
  last_sync_at: string | null;
  last_successful_sync_at: string | null;
  next_sync_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SyncRun {
  id: string;
  connector_id: string;
  sync_type: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  items_discovered: number;
  items_processed: number;
  items_skipped: number;
  items_failed: number;
  cursor: string | null;
  error_message: string | null;
  triggered_by: string | null;
}

export interface RegisterConnectorRequest {
  connector_type: ConnectorType;
  name: string;
  auth_type: ConnectorAuthType;
  credentials: Record<string, unknown>;
  config?: Record<string, unknown>;
  sync_interval_seconds?: number;
}

export async function listConnectors(
  status?: string,
  type?: string,
  page = 1,
  pageSize = 50,
): Promise<{ items: Connector[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Connector>("/connectors", {
    query: {
      connector_status: status,
      connector_type: type,
      page,
      page_size: pageSize,
    },
  });
}

export async function registerConnector(
  body: RegisterConnectorRequest,
): Promise<Connector> {
  return apiSend<Connector>("/connectors", "POST", body);
}

export async function getConnector(connectorId: string): Promise<Connector> {
  return apiGet<Connector>(`/connectors/${connectorId}`);
}

export async function checkConnectorHealth(
  connectorId: string,
): Promise<Connector> {
  return apiGet<Connector>(`/connectors/${connectorId}/health`);
}

export async function deleteConnector(connectorId: string): Promise<void> {
  return apiSend<void>(`/connectors/${connectorId}`, "DELETE");
}

export async function startSync(
  connectorId: string,
  syncType: SyncType = "incremental",
  resume = false,
): Promise<SyncRun> {
  return apiSend<SyncRun>(`/connectors/${connectorId}/sync`, "POST", {
    sync_type: syncType,
    resume,
  });
}

export async function stopSync(
  connectorId: string,
  syncRunId: string,
): Promise<SyncRun> {
  return apiSend<SyncRun>(
    `/connectors/${connectorId}/sync/${syncRunId}/stop`,
    "POST",
  );
}

export async function getSyncHistory(
  connectorId: string,
  page = 1,
  pageSize = 50,
): Promise<{ items: SyncRun[]; pagination: PaginationMeta | null }> {
  return apiGetPage<SyncRun>(`/connectors/${connectorId}/sync-history`, {
    query: { page, page_size: pageSize },
  });
}
