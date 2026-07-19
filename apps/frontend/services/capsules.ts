"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  compareCapsules,
  createCapsule,
  deleteCapsule,
  getAICapsule,
  getBusFactor,
  getCapsule,
  getCapsuleTimeline,
  getCoverageReport,
  getCriticalDependencies,
  getOrganizationalKnowledgeMap,
  getSuccessorPlan,
  linkPersonEntity,
  listCapsules,
  refreshCapsule,
  searchExpertise,
  searchOwnership,
  updateCapsuleProfile,
} from "@/lib/api/capsules";

export type {
  InsightEntry,
  OpenWorkEntry,
  ReadingMaterialEntry,
} from "@/lib/api/capsules";

const LIST_KEY = ["capsules"];

export function useCapsules() {
  return useQuery({ queryKey: LIST_KEY, queryFn: () => listCapsules(1, 100) });
}

export function useCapsule(capsuleId: string | null) {
  return useQuery({
    queryKey: ["capsule", capsuleId],
    queryFn: () => getCapsule(capsuleId as string),
    enabled: capsuleId !== null,
  });
}

export function useCreateCapsule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => createCapsule(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

export function useDeleteCapsule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteCapsule(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

export function useLinkPersonEntity(capsuleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entityId: string) => linkPersonEntity(capsuleId, entityId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["capsule", capsuleId] }),
  });
}

export function useUpdateCapsuleProfile(capsuleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      organizational_role?: string | null;
      responsibilities?: string[] | null;
    }) => updateCapsuleProfile(capsuleId, body),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["capsule", capsuleId] }),
  });
}

export function useRefreshCapsule(capsuleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => refreshCapsule(capsuleId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["capsule", capsuleId] });
      void queryClient.invalidateQueries({
        queryKey: ["capsule-timeline", capsuleId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["successor-plan", capsuleId],
      });
    },
  });
}

export function useCapsuleTimeline(capsuleId: string | null) {
  return useQuery({
    queryKey: ["capsule-timeline", capsuleId],
    queryFn: () => getCapsuleTimeline(capsuleId as string, 1, 100),
    enabled: capsuleId !== null,
  });
}

export function useAICapsule(capsuleId: string | null) {
  return useQuery({
    queryKey: ["ai-capsule", capsuleId],
    queryFn: () => getAICapsule(capsuleId as string),
    enabled: capsuleId !== null,
  });
}

export function useSuccessorPlan(capsuleId: string | null) {
  return useQuery({
    queryKey: ["successor-plan", capsuleId],
    queryFn: () => getSuccessorPlan(capsuleId as string),
    enabled: capsuleId !== null,
  });
}

export function useCompareCapsules(
  userIdA: string | null,
  userIdB: string | null,
) {
  return useQuery({
    queryKey: ["capsule-compare", userIdA, userIdB],
    queryFn: () => compareCapsules(userIdA as string, userIdB as string),
    enabled: userIdA !== null && userIdB !== null && userIdA !== userIdB,
  });
}

export function useExpertiseSearch(query: string) {
  return useQuery({
    queryKey: ["expertise-search", query],
    queryFn: () => searchExpertise(query),
    enabled: query.trim().length > 1,
  });
}

export function useOwnershipSearch(query: string) {
  return useQuery({
    queryKey: ["ownership-search", query],
    queryFn: () => searchOwnership(query),
    enabled: query.trim().length > 1,
  });
}

export function useOrganizationalKnowledgeMap() {
  return useQuery({
    queryKey: ["org-knowledge-map"],
    queryFn: getOrganizationalKnowledgeMap,
  });
}

export function useBusFactor(entityId: string | null) {
  return useQuery({
    queryKey: ["bus-factor", entityId],
    queryFn: () => getBusFactor(entityId as string),
    enabled: entityId !== null,
  });
}

export function useCoverageReport() {
  return useQuery({
    queryKey: ["coverage-report"],
    queryFn: getCoverageReport,
  });
}

export function useCriticalDependencies() {
  return useQuery({
    queryKey: ["critical-dependencies"],
    queryFn: getCriticalDependencies,
  });
}
