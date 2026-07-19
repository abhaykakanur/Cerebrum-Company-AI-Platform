"use client";

import { FileText, MoreVertical, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { statusVariant, formatStatusLabel } from "@/utils/status";
import type { Document } from "@/lib/api/documents";

export function DocumentTable({
  documents,
  isLoading,
  onOpen,
  onDelete,
}: {
  documents: Document[];
  isLoading: boolean;
  onOpen: (document: Document) => void;
  onDelete: (document: Document) => void;
}) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-foreground-muted">
        No documents in this folder.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Version</TableHead>
          <TableHead>Updated</TableHead>
          <TableHead className="w-10" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {documents.map((document) => (
          <TableRow
            key={document.id}
            className="cursor-pointer"
            onClick={() => onOpen(document)}
          >
            <TableCell className="flex items-center gap-2 font-medium">
              <FileText className="h-icon-sm w-icon-sm text-foreground-muted" />
              {document.name}
            </TableCell>
            <TableCell>
              <Badge variant={statusVariant(document.status)}>
                {formatStatusLabel(document.status)}
              </Badge>
            </TableCell>
            <TableCell>v{document.version}</TableCell>
            <TableCell className="text-foreground-muted">
              {new Date(document.updated_at).toLocaleDateString()}
            </TableCell>
            <TableCell onClick={(e) => e.stopPropagation()}>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-7 w-7">
                    <MoreVertical className="h-icon-xs w-icon-xs" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    destructive
                    onSelect={() => onDelete(document)}
                  >
                    <Trash2 className="h-icon-xs w-icon-xs" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
