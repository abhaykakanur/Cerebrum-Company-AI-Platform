/** Semantic Search API — mirrors apps/backend/src/cerebrum/api/v1/semantic.py. */

import { apiGet } from "@/lib/api/client";

export interface Citation {
  document_id: string | null;
  document_version_id: string | null;
  chunk_id: string | null;
  entity_id: string | null;
  confidence: number;
  provenance: Record<string, unknown>;
}

export interface SearchHit {
  source_id: string;
  kind: string;
  title: string;
  snippet: string;
  fused_score: number;
  vector_score: number | null;
  keyword_score: number | null;
  citation: Citation;
}

export interface SemanticStatistics {
  vector_count: number;
  indexed_document_count: number;
}

export async function semanticSearch(
  q: string,
  kinds?: string[],
  limit = 10,
): Promise<SearchHit[]> {
  const params = new URLSearchParams();
  params.set("q", q);
  params.set("limit", String(limit));
  kinds?.forEach((k) => params.append("kinds", k));
  return apiGet<SearchHit[]>(`/search/semantic?${params.toString()}`);
}

export async function hybridSearch(
  q: string,
  options: {
    kinds?: string[];
    tags?: string[];
    limit?: number;
    vectorWeight?: number;
    keywordWeight?: number;
  } = {},
): Promise<SearchHit[]> {
  const { limit = 10, vectorWeight = 1.0, keywordWeight = 1.0 } = options;
  const params = new URLSearchParams();
  params.set("q", q);
  params.set("limit", String(limit));
  params.set("vector_weight", String(vectorWeight));
  params.set("keyword_weight", String(keywordWeight));
  options.kinds?.forEach((k) => params.append("kinds", k));
  options.tags?.forEach((t) => params.append("tags", t));
  return apiGet<SearchHit[]>(`/search/hybrid?${params.toString()}`);
}

export async function autocomplete(
  prefix: string,
  limit = 10,
): Promise<string[]> {
  const { suggestions } = await apiGet<{ suggestions: string[] }>(
    "/search/autocomplete",
    {
      query: { prefix, limit },
    },
  );
  return suggestions;
}

export async function getSemanticStatistics(): Promise<SemanticStatistics> {
  return apiGet<SemanticStatistics>("/search/statistics");
}
