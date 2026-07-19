"use client";

import * as React from "react";
import { Folder, FolderPlus, Home } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import type { Folder as FolderType } from "@/lib/api/folders";
import { useCreateFolder, useFolders } from "@/services/documents";

export interface FolderPathEntry {
  id: string | undefined;
  name: string;
}

export function FolderBrowser({
  path,
  onNavigate,
}: {
  path: FolderPathEntry[];
  onNavigate: (path: FolderPathEntry[]) => void;
}) {
  const currentFolder = path[path.length - 1];
  const { data, isLoading } = useFolders(currentFolder?.id);
  const createFolder = useCreateFolder(currentFolder?.id);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [name, setName] = React.useState("");

  const handleCreate = async () => {
    try {
      await createFolder.mutateAsync(name.trim());
      setCreateOpen(false);
      setName("");
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to create folder.",
      );
    }
  };

  const openFolder = (folder: FolderType) =>
    onNavigate([...path, { id: folder.id, name: folder.name }]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <Breadcrumb>
          <BreadcrumbList>
            {path.map((entry, index) => {
              const isLast = index === path.length - 1;
              return (
                <React.Fragment key={entry.id ?? "root"}>
                  <BreadcrumbItem>
                    {isLast ? (
                      <BreadcrumbPage className="flex items-center gap-1">
                        {index === 0 && (
                          <Home className="h-icon-xs w-icon-xs" />
                        )}
                        {entry.name}
                      </BreadcrumbPage>
                    ) : (
                      <BreadcrumbLink asChild>
                        <button
                          type="button"
                          onClick={() => onNavigate(path.slice(0, index + 1))}
                        >
                          {entry.name}
                        </button>
                      </BreadcrumbLink>
                    )}
                  </BreadcrumbItem>
                  {!isLast && <BreadcrumbSeparator />}
                </React.Fragment>
              );
            })}
          </BreadcrumbList>
        </Breadcrumb>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() => setCreateOpen(true)}
        >
          <FolderPlus className="h-icon-sm w-icon-sm" />
          New folder
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {isLoading && <Skeleton className="h-9 w-32" />}
        {data?.items.map((folder) => (
          <button
            key={folder.id}
            type="button"
            onClick={() => openFolder(folder)}
            className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm transition-colors duration-fast hover:bg-accent"
          >
            <Folder className="h-icon-sm w-icon-sm text-foreground-muted" />
            {folder.name}
          </button>
        ))}
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New folder</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor="folder-name">Name</Label>
            <Input
              id="folder-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button
              onClick={handleCreate}
              loading={createFolder.isPending}
              disabled={!name.trim()}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
