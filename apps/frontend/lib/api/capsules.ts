/**
 * Employee Knowledge Capsule API — mirrors
 * apps/backend/src/cerebrum/api/v1/capsules.py. The backend leaves
 * `expertise_map`/`ownership_map`/`collaboration_network`/`active_projects`/
 * `technical_leadership` and the `/ai-capsule` payload as untyped
 * `dict[str, Any]` (no dedicated Pydantic schema) — kept as
 * `Record<string, unknown>` here rather than inventing a shape the backend
 * doesn't itself commit to.
 */

import {
  apiGet,
  apiGetPage,
  apiSend,
  type PaginationMeta,
} from "@/lib/api/client";

/**
 * The backend's Pydantic schema layer types these as untyped
 * `dict[str, Any]` (no dedicated response model exists server-side for
 * an "insight" concept), but their actual construction is fixed in
 * apps/backend/src/cerebrum/application/capsules/employee_knowledge_capsule_service.py
 * and successor_planning_service.py. Modeled precisely here — with every
 * field optional, since the backend contract itself doesn't guarantee
 * these keys — so the UI can render real fields instead of a generic
 * key-value dump.
 */
export interface InsightEntry {
  entity_id?: string;
  canonical_name?: string;
  entity_type?: string;
  ownership_category?: string;
  share?: number;
  strength?: number;
  score?: number;
  evidence_count?: number;
}

export interface OpenWorkEntry {
  event_type?: string;
  title?: string;
  occurred_at?: string;
}

export interface ReadingMaterialEntry {
  insight_key?: string;
  document_id?: string | null;
  external_url?: string | null;
  description?: string;
  confidence?: number;
}

export interface Capsule {
  id: string;
  workspace_id: string;
  user_id: string;
  person_entity_id: string | null;
  organizational_role: string | null;
  responsibilities: string[];
  expertise_map: InsightEntry[];
  ownership_map: InsightEntry[];
  active_projects: InsightEntry[];
  collaboration_network: InsightEntry[];
  technical_leadership: InsightEntry[];
  is_stale: boolean;
  stale_reason: string | null;
  last_refreshed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CapsuleTimelineEvent {
  id: string;
  event_type: string;
  occurred_at: string;
  title: string;
  description: string | null;
}

export interface CapsuleComparison {
  user_id_a: string;
  user_id_b: string;
  shared_expertise: string[];
  unique_expertise_a: string[];
  unique_expertise_b: string[];
  shared_ownership: string[];
  unique_ownership_a: string[];
  unique_ownership_b: string[];
}

export interface ExpertiseSearchResult {
  user_id: string;
  capsule_id: string;
  matches: Record<string, unknown>[];
}

export interface OwnershipSearchResult {
  user_id: string;
  capsule_id: string;
  matches: Record<string, unknown>[];
}

export interface OrganizationalKnowledgeMapEntry {
  user_id: string;
  capsule_id: string;
  organizational_role: string | null;
  top_expertise: InsightEntry[];
  top_ownership: InsightEntry[];
  is_stale: boolean;
}

export interface SuccessorPlan {
  capsule_id: string;
  critical_repositories: InsightEntry[];
  key_collaborators: InsightEntry[];
  learning_sequence: InsightEntry[];
  recommended_reading: ReadingMaterialEntry[];
  open_work: OpenWorkEntry[];
  immediate_priorities: string[];
}

export interface OwnerShare {
  person_entity_id: string;
  canonical_name: string;
  share: number;
}

export interface BusFactor {
  entity_id: string;
  canonical_name: string;
  bus_factor: number;
  owners: OwnerShare[];
  risk_level: string;
}

export interface CoverageReport {
  workspace_id: string;
  total_owned_entities: number;
  covered_entities: number;
  coverage_score: number;
  single_owner_entities: BusFactor[];
}

export async function listCapsules(
  page = 1,
  pageSize = 50,
): Promise<{ items: Capsule[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Capsule>("/capsules", {
    query: { page, page_size: pageSize },
  });
}

export async function createCapsule(userId: string): Promise<Capsule> {
  return apiSend<Capsule>("/capsules", "POST", { user_id: userId });
}

export async function getCapsule(capsuleId: string): Promise<Capsule> {
  return apiGet<Capsule>(`/capsules/${capsuleId}`);
}

export async function deleteCapsule(capsuleId: string): Promise<void> {
  return apiSend<void>(`/capsules/${capsuleId}`, "DELETE");
}

export async function linkPersonEntity(
  capsuleId: string,
  entityId: string,
): Promise<Capsule> {
  return apiSend<Capsule>(`/capsules/${capsuleId}/link`, "POST", {
    entity_id: entityId,
  });
}

export async function updateCapsuleProfile(
  capsuleId: string,
  body: {
    organizational_role?: string | null;
    responsibilities?: string[] | null;
  },
): Promise<Capsule> {
  return apiSend<Capsule>(`/capsules/${capsuleId}/profile`, "PATCH", body);
}

export async function refreshCapsule(capsuleId: string): Promise<Capsule> {
  return apiSend<Capsule>(`/capsules/${capsuleId}/refresh`, "POST");
}

export async function getCapsuleTimeline(
  capsuleId: string,
  page = 1,
  pageSize = 50,
): Promise<{
  items: CapsuleTimelineEvent[];
  pagination: PaginationMeta | null;
}> {
  return apiGetPage<CapsuleTimelineEvent>(`/capsules/${capsuleId}/timeline`, {
    query: { page, page_size: pageSize },
  });
}

export async function getAICapsule(
  capsuleId: string,
): Promise<Record<string, unknown>> {
  return apiGet<Record<string, unknown>>(`/capsules/${capsuleId}/ai-capsule`);
}

export async function getSuccessorPlan(
  capsuleId: string,
): Promise<SuccessorPlan> {
  return apiGet<SuccessorPlan>(`/capsules/${capsuleId}/successor-plan`);
}

export async function compareCapsules(
  userIdA: string,
  userIdB: string,
): Promise<CapsuleComparison> {
  return apiGet<CapsuleComparison>("/capsules/compare", {
    query: { user_id_a: userIdA, user_id_b: userIdB },
  });
}

export async function searchExpertise(
  query: string,
): Promise<ExpertiseSearchResult[]> {
  return apiGet<ExpertiseSearchResult[]>("/capsules/search/expertise", {
    query: { query },
  });
}

export async function searchOwnership(
  query: string,
): Promise<OwnershipSearchResult[]> {
  return apiGet<OwnershipSearchResult[]>("/capsules/search/ownership", {
    query: { query },
  });
}

export async function getOrganizationalKnowledgeMap(): Promise<
  OrganizationalKnowledgeMapEntry[]
> {
  return apiGet<OrganizationalKnowledgeMapEntry[]>(
    "/capsules/organizational-knowledge-map",
  );
}

export async function getBusFactor(entityId: string): Promise<BusFactor> {
  return apiGet<BusFactor>(`/capsules/risk/bus-factor/${entityId}`);
}

export async function getCoverageReport(): Promise<CoverageReport> {
  return apiGet<CoverageReport>("/capsules/risk/coverage");
}

export async function getCriticalDependencies(): Promise<BusFactor[]> {
  return apiGet<BusFactor[]>("/capsules/risk/critical-dependencies");
}
