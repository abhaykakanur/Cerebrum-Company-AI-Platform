/** Entities API — mirrors apps/backend/src/cerebrum/api/v1/entities.py. */

import {
  apiGet,
  apiGetPage,
  apiSend,
  type PaginationMeta,
} from "@/lib/api/client";

export type EntityType =
  | "person"
  | "organization"
  | "team"
  | "project"
  | "technology"
  | "product"
  | "customer"
  | "document"
  | "meeting"
  | "decision"
  | "policy"
  | "procedure"
  | "location"
  | "date"
  | "custom";

export interface Entity {
  id: string;
  workspace_id: string;
  organization_id: string;
  entity_type: EntityType;
  custom_type_name: string | null;
  canonical_name: string;
  aliases: string[];
  description: string | null;
  confidence: number;
  source_chunk_id: string | null;
  source_document_id: string | null;
  provenance: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
}

export interface GraphNode {
  id: string;
  workspace_id: string;
  entity_type: string;
  canonical_name: string;
  aliases: string[];
  confidence: number;
}

export interface EntityCreateRequest {
  entity_type: EntityType;
  canonical_name: string;
  custom_type_name?: string;
  aliases?: string[];
  description?: string;
  confidence?: number;
}

export async function listEntities(
  page = 1,
  pageSize = 50,
  filter?: string,
): Promise<{ items: Entity[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Entity>("/entities", {
    query: { page, page_size: pageSize, filter },
  });
}

export async function getEntity(entityId: string): Promise<Entity> {
  return apiGet<Entity>(`/entities/${entityId}`);
}

export async function createEntity(body: EntityCreateRequest): Promise<Entity> {
  return apiSend<Entity>("/entities", "POST", body);
}

export async function deleteEntity(entityId: string): Promise<void> {
  return apiSend<void>(`/entities/${entityId}`, "DELETE");
}

export async function getEntityNeighbors(
  entityId: string,
  depth = 1,
): Promise<GraphNode[]> {
  return apiGet<GraphNode[]>(`/entities/${entityId}/neighbors`, {
    query: { depth },
  });
}
