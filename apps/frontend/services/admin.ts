"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getMyOrganization,
  renameMyOrganization,
} from "@/lib/api/organizations";
import {
  createWorkspace,
  deleteWorkspace,
  listWorkspaces,
  renameWorkspace,
} from "@/lib/api/workspaces";

export function useOrganization() {
  return useQuery({ queryKey: ["organization"], queryFn: getMyOrganization });
}

export function useRenameOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => renameMyOrganization(name),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["organization"] }),
  });
}

export function useAdminWorkspaces() {
  return useQuery({ queryKey: ["admin-workspaces"], queryFn: listWorkspaces });
}

export function useAdminCreateWorkspace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, slug }: { name: string; slug: string }) =>
      createWorkspace(name, slug),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-workspaces"] }),
  });
}

export function useAdminRenameWorkspace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      renameWorkspace(id, name),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-workspaces"] }),
  });
}

export function useAdminDeleteWorkspace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteWorkspace(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-workspaces"] }),
  });
}
