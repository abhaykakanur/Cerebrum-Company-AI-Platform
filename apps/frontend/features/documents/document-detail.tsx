"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { statusVariant, formatStatusLabel } from "@/utils/status";
import type { Document, DocumentVersion } from "@/lib/api/documents";
import {
  useDocumentVersions,
  useVersionChunks,
  useVersionMetadata,
  useVersionProcessingJobs,
  useVersionProgress,
} from "@/services/documents";

function bytesToReadable(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentDetail({ document }: { document: Document }) {
  const { data: versions, isLoading: versionsLoading } = useDocumentVersions(
    document.id,
  );
  const currentVersion =
    versions?.items.find((v) => v.is_current) ?? versions?.items[0] ?? null;
  const versionId = currentVersion?.id ?? null;

  const { data: metadata } = useVersionMetadata(document.id, versionId);
  const { data: progress } = useVersionProgress(document.id, versionId);
  const { data: chunks, isLoading: chunksLoading } = useVersionChunks(
    document.id,
    versionId,
  );
  const { data: jobs } = useVersionProcessingJobs(document.id, versionId);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Badge variant={statusVariant(document.status)}>
          {formatStatusLabel(document.status)}
        </Badge>
        <span className="text-xs text-foreground-muted">
          Version {document.version}
        </span>
      </div>

      {progress && progress.overall_progress_percent < 100 && (
        <div className="flex flex-col gap-1">
          <div className="flex justify-between text-xs text-foreground-muted">
            <span>Processing</span>
            <span>{progress.overall_progress_percent}%</span>
          </div>
          <Progress value={progress.overall_progress_percent} />
        </div>
      )}

      <Tabs defaultValue="metadata">
        <TabsList>
          <TabsTrigger value="metadata">Metadata</TabsTrigger>
          <TabsTrigger value="versions">Versions</TabsTrigger>
          <TabsTrigger value="chunks">Chunks</TabsTrigger>
          <TabsTrigger value="processing">Processing</TabsTrigger>
        </TabsList>

        <TabsContent value="metadata" className="flex flex-col gap-2 text-sm">
          {metadata ? (
            <>
              <Row
                label="Original filename"
                value={metadata.original_filename}
              />
              <Row label="MIME type" value={metadata.mime_type} />
              <Row
                label="File size"
                value={bytesToReadable(metadata.file_size_bytes)}
              />
              <Row
                label="SHA-256"
                value={metadata.sha256_checksum.slice(0, 16) + "..."}
              />
              <Row
                label="Quarantine status"
                value={formatStatusLabel(metadata.quarantine_status)}
              />
              <Row
                label="Uploaded"
                value={new Date(metadata.uploaded_at).toLocaleString()}
              />
            </>
          ) : (
            <Skeleton className="h-24 w-full" />
          )}
        </TabsContent>

        <TabsContent value="versions" className="flex flex-col gap-2">
          {versionsLoading && <Skeleton className="h-16 w-full" />}
          {versions?.items.map((version) => (
            <VersionRow key={version.id} version={version} />
          ))}
        </TabsContent>

        <TabsContent value="chunks" className="flex flex-col gap-2">
          {chunksLoading && <Skeleton className="h-16 w-full" />}
          {chunks?.length === 0 && (
            <p className="text-sm text-foreground-muted">No chunks yet.</p>
          )}
          {chunks?.map((chunk) => (
            <div
              key={chunk.id}
              className="rounded-md border border-border p-2 text-xs"
            >
              <div className="mb-1 flex justify-between text-foreground-muted">
                <span>Chunk #{chunk.chunk_index}</span>
                <span>{chunk.character_count} chars</span>
              </div>
              <p className="line-clamp-3">{chunk.text}</p>
            </div>
          ))}
        </TabsContent>

        <TabsContent value="processing" className="flex flex-col gap-2">
          {jobs?.length === 0 && (
            <p className="text-sm text-foreground-muted">No processing jobs.</p>
          )}
          {jobs?.map((job) => (
            <div
              key={job.id}
              className="flex items-center justify-between rounded-md border border-border p-2 text-xs"
            >
              <span className="capitalize">{job.job_type}</span>
              <div className="flex items-center gap-2">
                {job.status === "running" && (
                  <span>{job.progress_percent}%</span>
                )}
                <Badge variant={statusVariant(job.status)}>
                  {formatStatusLabel(job.status)}
                </Badge>
              </div>
            </div>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border py-1.5">
      <span className="text-foreground-muted">{label}</span>
      <span className="max-w-[60%] truncate text-right font-mono text-xs">
        {value}
      </span>
    </div>
  );
}

function VersionRow({ version }: { version: DocumentVersion }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border p-2 text-sm">
      <div>
        <p>
          v{version.version_number}
          {version.is_current && (
            <Badge variant="info" className="ml-2">
              Current
            </Badge>
          )}
        </p>
        <p className="text-xs text-foreground-muted">
          {new Date(version.created_at).toLocaleString()}
        </p>
      </div>
      <Badge variant={statusVariant(version.upload_status)}>
        {formatStatusLabel(version.upload_status)}
      </Badge>
    </div>
  );
}
