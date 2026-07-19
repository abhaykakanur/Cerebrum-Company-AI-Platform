"use client";

import * as React from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import { useCreateDocument } from "@/services/documents";

export function UploadDialog({ folderId }: { folderId: string | undefined }) {
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const createDocument = useCreateDocument(folderId);

  const handleUpload = async () => {
    try {
      await createDocument.mutateAsync({
        name: name.trim() || file?.name || "Untitled",
        file: file ?? undefined,
      });
      toast.success("Document uploaded.");
      setOpen(false);
      setName("");
      setFile(null);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Upload failed.");
    }
  };

  return (
    <>
      <Button className="gap-1.5" onClick={() => setOpen(true)}>
        <Upload className="h-icon-sm w-icon-sm" />
        Upload
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload document</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="doc-file">File</Label>
              <Input
                id="doc-file"
                type="file"
                onChange={(e) => {
                  const selected = e.target.files?.[0] ?? null;
                  setFile(selected);
                  if (selected && !name) setName(selected.name);
                }}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="doc-name">Name</Label>
              <Input
                id="doc-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={handleUpload}
              loading={createDocument.isPending}
              disabled={!file}
            >
              Upload
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
