"use client";

import * as React from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import type { Document } from "@/lib/api/documents";
import { useContextDrawer } from "@/layouts/context-drawer";
import {
  FolderBrowser,
  type FolderPathEntry,
} from "@/features/documents/folder-browser";
import { DocumentTable } from "@/features/documents/document-table";
import { UploadDialog } from "@/features/documents/upload-dialog";
import { DocumentDetail } from "@/features/documents/document-detail";
import { useDeleteDocument, useDocuments } from "@/services/documents";

export default function DocumentsPage() {
  const [path, setPath] = React.useState<FolderPathEntry[]>([
    { id: undefined, name: "Documents" },
  ]);
  const currentFolder = path[path.length - 1];
  const { data, isLoading } = useDocuments(currentFolder?.id);
  const deleteDocument = useDeleteDocument(currentFolder?.id);
  const drawer = useContextDrawer();

  const openDocument = (document: Document) => {
    drawer.open({
      title: document.name,
      content: <DocumentDetail document={document} />,
    });
  };

  const handleDelete = async (document: Document) => {
    try {
      await deleteDocument.mutateAsync(document.id);
      toast.success(`"${document.name}" deleted.`);
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to delete document.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 font-semibold">Document Explorer</h1>
          <p className="text-sm text-foreground-muted">
            Browse, upload, and inspect your workspace&apos;s documents.
          </p>
        </div>
        <UploadDialog folderId={currentFolder?.id} />
      </div>

      <FolderBrowser path={path} onNavigate={setPath} />

      <DocumentTable
        documents={data?.items ?? []}
        isLoading={isLoading}
        onOpen={openDocument}
        onDelete={handleDelete}
      />
    </div>
  );
}
