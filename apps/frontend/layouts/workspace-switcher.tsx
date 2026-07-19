"use client";

import * as React from "react";
import { Check, ChevronsUpDown, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useAuth } from "@/providers/auth-provider";
import { createWorkspace } from "@/lib/api/workspaces";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// Workspace Switcher — Layout System element surfacing FR-OR-002
// Multi-Workspace Organization Structure.
export function WorkspaceSwitcher() {
  const { workspaces, currentWorkspace, selectWorkspace, refreshWorkspaces } =
    useAuth();
  const router = useRouter();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [slug, setSlug] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  const handleSelect = (workspaceId: string) => {
    if (workspaceId === currentWorkspace?.id) return;
    selectWorkspace(workspaceId);
    router.refresh();
  };

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const workspace = await createWorkspace(name.trim(), slug.trim());
      await refreshWorkspaces();
      selectWorkspace(workspace.id);
      setCreateOpen(false);
      setName("");
      setSlug("");
      toast.success(`Workspace "${workspace.name}" created`);
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to create workspace",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="max-w-48 justify-between gap-2"
          >
            <span className="truncate">
              {currentWorkspace?.name ?? "Select workspace"}
            </span>
            <ChevronsUpDown className="h-icon-xs w-icon-xs shrink-0 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {workspaces.map((workspace) => (
            <DropdownMenuItem
              key={workspace.id}
              onSelect={() => handleSelect(workspace.id)}
            >
              <Check
                className={cn(
                  "h-icon-xs w-icon-xs",
                  workspace.id === currentWorkspace?.id
                    ? "opacity-100"
                    : "opacity-0",
                )}
              />
              <span className="truncate">{workspace.name}</span>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setCreateOpen(true)}>
            <Plus className="h-icon-xs w-icon-xs" />
            New workspace
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create workspace</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="workspace-name">Name</Label>
              <Input
                id="workspace-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="workspace-slug">Slug</Label>
              <Input
                id="workspace-slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                required
              />
            </div>
            <DialogFooter>
              <Button type="submit" loading={submitting}>
                Create
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
