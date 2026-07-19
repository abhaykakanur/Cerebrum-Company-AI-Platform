/** Relationships API — mirrors apps/backend/src/cerebrum/api/v1/relationships.py. */

import { apiGetPage, type PaginationMeta } from "@/lib/api/client";

export type RelationshipType =
  | "references"
  | "mentions"
  | "ownership"
  | "membership"
  | "dependency"
  | "parent_child"
  | "collaboration"
  | "uses"
  | "produced_by"
  | "reports_to"
  | "custom";

export interface Relationship {
  id: string;
  workspace_id: string;
  organization_id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: RelationshipType;
  custom_type_name: string | null;
  confidence: number;
  evidence: string | null;
  source_chunk_id: string | null;
  source_document_id: string | null;
  valid_from: string | null;
  valid_to: string | null;
  created_at: string;
  updated_at: string;
}

export async function listRelationships(
  page = 1,
  pageSize = 100,
  filter?: string,
): Promise<{ items: Relationship[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Relationship>("/relationships", {
    query: { page, page_size: pageSize, filter },
  });
}
