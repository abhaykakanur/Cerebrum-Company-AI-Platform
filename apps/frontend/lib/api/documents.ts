/** Documents API — mirrors apps/backend/src/cerebrum/api/v1/documents.py. */

import {
  apiGet,
  apiGetPage,
  apiSend,
  type PaginationMeta,
} from "@/lib/api/client";

export type DocumentStatus =
  "draft" | "uploaded" | "active" | "archived" | "deleted";
export type UploadStatus =
  | "uploaded"
  | "validated"
  | "stored"
  | "ready_for_processing"
  | "archived"
  | "deleted"
  | "quarantined";

export interface Document {
  id: string;
  workspace_id: string;
  folder_id: string | null;
  name: string;
  status: DocumentStatus;
  current_version_id: string | null;
  version: number;
  is_deleted: boolean;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  version_type: "major" | "minor";
  is_current: boolean;
  upload_status: UploadStatus;
  change_summary: string | null;
  created_at: string;
  created_by: string | null;
}

export interface DocumentMetadata {
  id: string;
  document_version_id: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_checksum: string;
  storage_path: string;
  original_filename: string;
  uploaded_filename: string;
  uploaded_at: string;
  quarantine_status: "pending" | "clean" | "quarantined";
}

export interface ProcessingJob {
  id: string;
  document_version_id: string;
  job_type: "ocr" | "parsing" | "chunking" | "embeddings";
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress_percent: number;
  retry_count: number;
  max_retries: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Chunk {
  id: string;
  document_version_id: string;
  extraction_id: string;
  parent_chunk_id: string | null;
  strategy: string;
  chunk_index: number;
  text: string;
  character_count: number;
  start_offset: number;
  end_offset: number;
  overlap_with_previous: number;
  chunk_metadata: Record<string, unknown>;
  created_at: string;
}

export interface PipelineProgress {
  extraction_status: string | null;
  extraction_progress_percent: number;
  chunking_status: string | null;
  chunking_progress_percent: number;
  overall_progress_percent: number;
}

export async function listDocuments(
  folderId?: string,
  page = 1,
  pageSize = 50,
): Promise<{ items: Document[]; pagination: PaginationMeta | null }> {
  return apiGetPage<Document>("/documents", {
    query: { folder_id: folderId, page, page_size: pageSize },
  });
}

export async function getDocument(documentId: string): Promise<Document> {
  return apiGet<Document>(`/documents/${documentId}`);
}

export async function createDocument(
  name: string,
  folderId?: string,
): Promise<Document> {
  return apiSend<Document>("/documents", "POST", { name, folder_id: folderId });
}

export async function renameDocument(
  documentId: string,
  name: string,
): Promise<Document> {
  return apiSend<Document>(`/documents/${documentId}`, "PATCH", { name });
}

export async function deleteDocument(documentId: string): Promise<void> {
  return apiSend<void>(`/documents/${documentId}`, "DELETE");
}

export async function listDocumentVersions(
  documentId: string,
  page = 1,
  pageSize = 50,
): Promise<{ items: DocumentVersion[]; pagination: PaginationMeta | null }> {
  return apiGetPage<DocumentVersion>(`/documents/${documentId}/versions`, {
    query: { page, page_size: pageSize },
  });
}

export async function getVersionMetadata(
  documentId: string,
  versionId: string,
): Promise<DocumentMetadata> {
  return apiGet<DocumentMetadata>(
    `/documents/${documentId}/versions/${versionId}/metadata`,
  );
}

export async function getVersionChunks(
  documentId: string,
  versionId: string,
): Promise<Chunk[]> {
  return apiGet<Chunk[]>(
    `/documents/${documentId}/versions/${versionId}/chunks`,
  );
}

export async function getVersionProgress(
  documentId: string,
  versionId: string,
): Promise<PipelineProgress> {
  return apiGet<PipelineProgress>(
    `/documents/${documentId}/versions/${versionId}/progress`,
  );
}

export async function getVersionProcessingJobs(
  documentId: string,
  versionId: string,
): Promise<ProcessingJob[]> {
  return apiGet<ProcessingJob[]>(
    `/documents/${documentId}/versions/${versionId}/processing-jobs`,
  );
}

export async function getVersionDownloadUrl(
  documentId: string,
  versionId: string,
): Promise<{ url: string; expires_in_seconds: number }> {
  return apiGet<{ url: string; expires_in_seconds: number }>(
    `/documents/${documentId}/versions/${versionId}/download-url`,
  );
}

/** Multipart upload creates a new version on an existing document. Callers
 * create the document first via {@link createDocument}. */
export async function uploadDocumentVersion(
  documentId: string,
  file: File,
): Promise<DocumentVersion> {
  const form = new FormData();
  form.append("file", file);
  return apiSend<DocumentVersion>(
    `/documents/${documentId}/upload`,
    "POST",
    form,
  );
}
