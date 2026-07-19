"use client";

import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/lib/api/health";
import { getGraphStatistics } from "@/lib/api/knowledge-graph";
import { getRetrievalStatistics } from "@/lib/api/retrieval";
import { getAIStatistics } from "@/lib/api/ai";
import { listConnectors } from "@/lib/api/connectors";
import { listWorkflows } from "@/lib/api/workflows";
import { listDocuments } from "@/lib/api/documents";

/**
 * Aggregates the Dashboard's widgets from real endpoints only. Doc
 * 88_Dashboard_Architecture.md's idealized 12-widget catalog includes
 * widgets (Search Analytics trends, Jobs Queue Status) that would require
 * backend aggregate/analytics capability that doesn't exist in the
 * implemented API — this hook is scoped to what CIS Phase 1-5.3 actually
 * shipped: system health, knowledge graph size, retrieval index size, AI
 * usage, connector health, workflow activity, and document count.
 */
export function useDashboardData() {
  const health = useQuery({
    queryKey: ["dashboard", "health"],
    queryFn: getHealth,
    staleTime: 15_000,
  });
  const graphStats = useQuery({
    queryKey: ["dashboard", "graph-statistics"],
    queryFn: getGraphStatistics,
  });
  const retrievalStats = useQuery({
    queryKey: ["dashboard", "retrieval-statistics"],
    queryFn: getRetrievalStatistics,
  });
  const aiStats = useQuery({
    queryKey: ["dashboard", "ai-statistics"],
    queryFn: getAIStatistics,
  });
  const connectors = useQuery({
    queryKey: ["dashboard", "connectors"],
    queryFn: () => listConnectors(undefined, undefined, 1, 100),
  });
  const workflows = useQuery({
    queryKey: ["dashboard", "workflows"],
    queryFn: () => listWorkflows(undefined, 1, 100),
  });
  const documents = useQuery({
    queryKey: ["dashboard", "documents"],
    queryFn: () => listDocuments(undefined, 1, 1),
  });

  return {
    health,
    graphStats,
    retrievalStats,
    aiStats,
    connectors,
    workflows,
    documents,
    isLoading:
      health.isLoading ||
      graphStats.isLoading ||
      retrievalStats.isLoading ||
      aiStats.isLoading ||
      connectors.isLoading ||
      workflows.isLoading ||
      documents.isLoading,
  };
}
