/** Workspace API — mirrors apps/backend/src/cerebrum/api/v1/workspaces.py. */

import { apiGetPage, apiSend } from "@/lib/api/client";

export interface Workspace {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export async function listWorkspaces(): Promise<Workspace[]> {
  const { items } = await apiGetPage<Workspace>("/workspaces", {
    query: { page: 1, page_size: 100 },
    skipWorkspace: true,
  });
  return items;
}

export async function createWorkspace(
  name: string,
  slug: string,
): Promise<Workspace> {
  return apiSend<Workspace>(
    "/workspaces",
    "POST",
    { name, slug },
    { skipWorkspace: true },
  );
}

export async function renameWorkspace(
  workspaceId: string,
  name: string,
): Promise<Workspace> {
  return apiSend<Workspace>(
    `/workspaces/${workspaceId}`,
    "PATCH",
    { name },
    { skipWorkspace: true },
  );
}

export async function deleteWorkspace(workspaceId: string): Promise<void> {
  return apiSend<void>(`/workspaces/${workspaceId}`, "DELETE", undefined, {
    skipWorkspace: true,
  });
}
