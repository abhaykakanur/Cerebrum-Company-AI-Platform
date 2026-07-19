"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getEntity,
  getEntityNeighbors,
  listEntities,
} from "@/lib/api/entities";
import { listRelationships } from "@/lib/api/relationships";

export function useEntitySearch(query: string) {
  return useQuery({
    queryKey: ["graph", "entity-search", query],
    queryFn: () => listEntities(1, 20, `canonical_name:contains:${query}`),
    enabled: query.trim().length > 1,
  });
}

export function useEntityNeighbors(entityId: string | null, depth: number) {
  return useQuery({
    queryKey: ["graph", "neighbors", entityId, depth],
    queryFn: () => getEntityNeighbors(entityId as string, depth),
    enabled: entityId !== null,
  });
}

export function useEntityDetail(entityId: string | null) {
  return useQuery({
    queryKey: ["graph", "entity", entityId],
    queryFn: () => getEntity(entityId as string),
    enabled: entityId !== null,
  });
}

export function useEntityRelationships(entityId: string | null) {
  return useQuery({
    queryKey: ["graph", "entity-relationships", entityId],
    queryFn: () => listRelationships(1, 200, `source_entity_id:eq:${entityId}`),
    enabled: entityId !== null,
  });
}
