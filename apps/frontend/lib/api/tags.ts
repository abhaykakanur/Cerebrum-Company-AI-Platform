/** Tags API — mirrors apps/backend/src/cerebrum/api/v1/tags.py. */

import { apiGetPage, apiSend, type PaginationMeta } from "@/lib/api/client";

export interface Tag {
  id: string;
  workspace_id: string;
  name: string;
  created_at: string;
}

export async function listTags(
  page = 1,
  pageSize = 100,
): Promise<{ items: Tag[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Tag>("/tags", { query: { page, page_size: pageSize } });
}

export async function createTag(name: string): Promise<Tag> {
  return apiSend<Tag>("/tags", "POST", { name });
}

export async function deleteTag(tagId: string): Promise<void> {
  return apiSend<void>(`/tags/${tagId}`, "DELETE");
}

export async function assignTag(
  documentId: string,
  tagId: string,
): Promise<void> {
  return apiSend<void>(`/documents/${documentId}/tags/${tagId}`, "POST");
}

export async function unassignTag(
  documentId: string,
  tagId: string,
): Promise<void> {
  return apiSend<void>(`/documents/${documentId}/tags/${tagId}`, "DELETE");
}
