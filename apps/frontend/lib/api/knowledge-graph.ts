/** Knowledge Graph API — mirrors apps/backend/src/cerebrum/api/v1/knowledge_graph.py. */

import { apiGet } from "@/lib/api/client";

export interface GraphStatistics {
  entity_count: number;
  relationship_count: number;
}

export interface GraphConsistency {
  is_consistent: boolean;
  issues: string[];
}

export async function getGraphStatistics(): Promise<GraphStatistics> {
  return apiGet<GraphStatistics>("/graph/statistics");
}

export async function validateGraph(): Promise<GraphConsistency> {
  return apiGet<GraphConsistency>("/graph/validate");
}
