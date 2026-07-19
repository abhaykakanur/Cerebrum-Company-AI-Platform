"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createDocument,
  deleteDocument,
  getVersionChunks,
  getVersionMetadata,
  getVersionProcessingJobs,
  getVersionProgress,
  listDocumentVersions,
  listDocuments,
  renameDocument,
  uploadDocumentVersion,
} from "@/lib/api/documents";
import {
  createFolder,
  deleteFolder,
  listFolders,
  renameFolder,
} from "@/lib/api/folders";

export function useFolders(parentId: string | undefined) {
  return useQuery({
    queryKey: ["folders", parentId ?? "root"],
    queryFn: () => listFolders(parentId, 1, 100),
  });
}

export function useDocuments(folderId: string | undefined) {
  return useQuery({
    queryKey: ["documents", folderId ?? "root"],
    queryFn: () => listDocuments(folderId, 1, 100),
  });
}

export function useCreateFolder(parentId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => createFolder(name, parentId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["folders", parentId ?? "root"],
      }),
  });
}

export function useRenameFolder(parentId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      renameFolder(id, name),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["folders", parentId ?? "root"],
      }),
  });
}

export function useDeleteFolder(parentId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteFolder(id),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["folders", parentId ?? "root"],
      }),
  });
}

export function useCreateDocument(folderId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, file }: { name: string; file?: File }) => {
      const document = await createDocument(name, folderId);
      if (file) await uploadDocumentVersion(document.id, file);
      return document;
    },
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["documents", folderId ?? "root"],
      }),
  });
}

export function useRenameDocument(folderId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      renameDocument(id, name),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["documents", folderId ?? "root"],
      }),
  });
}

export function useDeleteDocument(folderId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["documents", folderId ?? "root"],
      }),
  });
}

export function useDocumentVersions(documentId: string | null) {
  return useQuery({
    queryKey: ["document-versions", documentId],
    queryFn: () => listDocumentVersions(documentId as string, 1, 50),
    enabled: documentId !== null,
  });
}

export function useVersionMetadata(
  documentId: string | null,
  versionId: string | null,
) {
  return useQuery({
    queryKey: ["version-metadata", documentId, versionId],
    queryFn: () =>
      getVersionMetadata(documentId as string, versionId as string),
    enabled: documentId !== null && versionId !== null,
  });
}

export function useVersionProgress(
  documentId: string | null,
  versionId: string | null,
) {
  return useQuery({
    queryKey: ["version-progress", documentId, versionId],
    queryFn: () =>
      getVersionProgress(documentId as string, versionId as string),
    enabled: documentId !== null && versionId !== null,
    refetchInterval: (query) =>
      query.state.data && query.state.data.overall_progress_percent >= 100
        ? false
        : 3000,
  });
}

export function useVersionChunks(
  documentId: string | null,
  versionId: string | null,
) {
  return useQuery({
    queryKey: ["version-chunks", documentId, versionId],
    queryFn: () => getVersionChunks(documentId as string, versionId as string),
    enabled: documentId !== null && versionId !== null,
  });
}

export function useVersionProcessingJobs(
  documentId: string | null,
  versionId: string | null,
) {
  return useQuery({
    queryKey: ["version-jobs", documentId, versionId],
    queryFn: () =>
      getVersionProcessingJobs(documentId as string, versionId as string),
    enabled: documentId !== null && versionId !== null,
  });
}
