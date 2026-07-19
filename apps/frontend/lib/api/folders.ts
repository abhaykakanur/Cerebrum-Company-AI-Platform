/** Folders API — mirrors apps/backend/src/cerebrum/api/v1/folders.py. */

import { apiGetPage, apiSend, type PaginationMeta } from "@/lib/api/client";

export interface Folder {
  id: string;
  workspace_id: string;
  parent_id: string | null;
  name: string;
  version: number;
  is_deleted: boolean;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export async function listFolders(
  parentId?: string,
  page = 1,
  pageSize = 100,
): Promise<{ items: Folder[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Folder>("/folders", {
    query: { parent_id: parentId, page, page_size: pageSize },
  });
}

export async function createFolder(
  name: string,
  parentId?: string,
): Promise<Folder> {
  return apiSend<Folder>("/folders", "POST", { name, parent_id: parentId });
}

export async function renameFolder(
  folderId: string,
  name: string,
): Promise<Folder> {
  return apiSend<Folder>(`/folders/${folderId}`, "PATCH", { name });
}

export async function deleteFolder(folderId: string): Promise<void> {
  return apiSend<void>(`/folders/${folderId}`, "DELETE");
}
