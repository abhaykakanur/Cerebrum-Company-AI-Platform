/** Labels API — mirrors apps/backend/src/cerebrum/api/v1/labels.py. */

import { apiGetPage, apiSend, type PaginationMeta } from "@/lib/api/client";

export interface Label {
  id: string;
  workspace_id: string;
  name: string;
  color: string | null;
  created_at: string;
}

export async function listLabels(
  page = 1,
  pageSize = 100,
): Promise<{ items: Label[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Label>("/labels", { query: { page, page_size: pageSize } });
}

export async function createLabel(
  name: string,
  color?: string,
): Promise<Label> {
  return apiSend<Label>("/labels", "POST", { name, color });
}

export async function deleteLabel(labelId: string): Promise<void> {
  return apiSend<void>(`/labels/${labelId}`, "DELETE");
}

export async function assignLabel(
  documentId: string,
  labelId: string,
): Promise<void> {
  return apiSend<void>(`/documents/${documentId}/labels/${labelId}`, "POST");
}

export async function unassignLabel(
  documentId: string,
  labelId: string,
): Promise<void> {
  return apiSend<void>(`/documents/${documentId}/labels/${labelId}`, "DELETE");
}
