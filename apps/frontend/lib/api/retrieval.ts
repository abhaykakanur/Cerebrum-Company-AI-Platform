/** Retrieval API — mirrors apps/backend/src/cerebrum/api/v1/retrieval.py. */

import { apiGet } from "@/lib/api/client";
import type { Citation, SearchHit } from "@/lib/api/semantic";

export type RetrievalStrategy =
  "hybrid" | "semantic" | "keyword" | "graph" | "metadata";

export interface RankingFactors {
  hybrid_score: number;
  vector_similarity: number;
  bm25_score: number;
  graph_proximity: number;
  entity_importance: number;
  recency: number;
  source_confidence: number;
  document_quality: number;
}

export interface RankedResult {
  hit: SearchHit;
  factors: RankingFactors;
  final_score: number;
}

export interface RetrievalStatistics {
  vector_count: number;
  indexed_document_count: number;
  entity_count: number;
  relationship_count: number;
}

export interface EnrichedCitation extends Citation {
  document_name: string | null;
  version_number: number | null;
  chunk_index: number | null;
  entity_name: string | null;
}

export interface ContextPackage {
  query_text: string | null;
  documents: {
    document_id: string;
    name: string;
    version_id: string | null;
    version_number: number | null;
  }[];
  chunks: {
    chunk_id: string;
    document_version_id: string;
    chunk_index: number;
    text: string;
    citation: Citation;
  }[];
  entities: {
    entity_id: string;
    entity_type: string;
    canonical_name: string;
    description: string | null;
    confidence: number;
    citation: Citation;
  }[];
  entities_by_type: Record<string, unknown[]>;
  relationships: {
    relationship_id: string;
    source_entity_id: string;
    target_entity_id: string;
    relationship_type: string;
    confidence: number;
  }[];
  graph_neighbors: Record<string, Record<string, unknown>[]>;
  version_history: {
    document_id: string;
    version_id: string;
    version_number: number;
    is_current: boolean;
  }[];
  citations: EnrichedCitation[];
  truncated: boolean;
}

export async function retrieve(
  q: string,
  options: { strategy?: RetrievalStrategy; limit?: number } = {},
): Promise<RankedResult[]> {
  const { strategy = "hybrid", limit = 10 } = options;
  return apiGet<RankedResult[]>("/retrieval/retrieve", {
    query: { q, strategy, limit },
  });
}

export async function getRetrievalStatistics(): Promise<RetrievalStatistics> {
  return apiGet<RetrievalStatistics>("/retrieval/statistics");
}

export async function getGraphContext(
  entityId: string,
  depth = 1,
  limit = 20,
): Promise<ContextPackage> {
  return apiGet<ContextPackage>(`/retrieval/graph-context/${entityId}`, {
    query: { depth, limit },
  });
}
