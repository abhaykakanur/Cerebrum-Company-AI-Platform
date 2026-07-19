"use client";

import * as React from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/providers/auth-provider";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useAdminCreateWorkspace,
  useAdminDeleteWorkspace,
  useAdminRenameWorkspace,
  useAdminWorkspaces,
  useOrganization,
  useRenameOrganization,
} from "@/services/admin";

function OrganizationSettings() {
  const { data: org, isLoading } = useOrganization();
  const rename = useRenameOrganization();
  const [name, setName] = React.useState("");

  React.useEffect(() => {
    if (org) setName(org.name);
  }, [org]);

  const handleSave = async () => {
    try {
      await rename.mutateAsync(name.trim());
      toast.success("Organization renamed.");
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to rename organization.",
      );
    }
  };

  if (isLoading || !org) return <Skeleton className="h-32 w-full max-w-md" />;

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle>Organization</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-2">
          <Label htmlFor="org-name">Name</Label>
          <Input
            id="org-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="text-xs text-foreground-muted">Slug: {org.slug}</div>
        <Button
          className="w-fit"
          onClick={handleSave}
          loading={rename.isPending}
          disabled={!name.trim()}
        >
          Save
        </Button>
      </CardContent>
    </Card>
  );
}

function WorkspaceManagement() {
  const { data: workspaces, isLoading } = useAdminWorkspaces();
  const createWorkspace = useAdminCreateWorkspace();
  const renameWorkspace = useAdminRenameWorkspace();
  const deleteWorkspace = useAdminDeleteWorkspace();
  const { refreshWorkspaces } = useAuth();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [slug, setSlug] = React.useState("");
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editingName, setEditingName] = React.useState("");

  const handleCreate = async () => {
    try {
      await createWorkspace.mutateAsync({
        name: name.trim(),
        slug: slug.trim(),
      });
      await refreshWorkspaces();
      toast.success("Workspace created.");
      setCreateOpen(false);
      setName("");
      setSlug("");
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to create workspace.",
      );
    }
  };

  const handleRename = async (id: string) => {
    try {
      await renameWorkspace.mutateAsync({ id, name: editingName.trim() });
      await refreshWorkspaces();
      toast.success("Workspace renamed.");
      setEditingId(null);
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to rename workspace.",
      );
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteWorkspace.mutateAsync(id);
      await refreshWorkspaces();
      toast.success("Workspace deleted.");
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to delete workspace.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button className="gap-1.5" onClick={() => setCreateOpen(true)}>
          <Plus className="h-icon-sm w-icon-sm" />
          New workspace
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-24" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {workspaces?.map((workspace) => (
              <TableRow key={workspace.id}>
                <TableCell>
                  {editingId === workspace.id ? (
                    <Input
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      onKeyDown={(e) =>
                        e.key === "Enter" && handleRename(workspace.id)
                      }
                      autoFocus
                    />
                  ) : (
                    <button
                      type="button"
                      className="hover:underline"
                      onClick={() => {
                        setEditingId(workspace.id);
                        setEditingName(workspace.name);
                      }}
                    >
                      {workspace.name}
                    </button>
                  )}
                </TableCell>
                <TableCell className="font-mono text-xs text-foreground-muted">
                  {workspace.slug}
                </TableCell>
                <TableCell className="text-foreground-muted">
                  {new Date(workspace.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => handleDelete(workspace.id)}
                  >
                    <Trash2 className="h-icon-xs w-icon-xs text-danger" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New workspace</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="new-ws-name">Name</Label>
              <Input
                id="new-ws-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="new-ws-slug">Slug</Label>
              <Input
                id="new-ws-slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={handleCreate}
              loading={createWorkspace.isPending}
              disabled={!name.trim() || !slug.trim()}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/**
 * Scoped to what the backend actually exposes: organization settings and
 * workspace management. There is no `/roles`, `/users`, or `/audit-log`
 * endpoint anywhere in the implemented API (CIS Phase 1-5.3's 130
 * routes) — user/role/audit-log administration UI would have nothing
 * real to call, so it isn't built here.
 */
export default function AdminPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-h1 font-semibold">Administration</h1>
        <p className="text-sm text-foreground-muted">
          Organization and workspace management.
        </p>
      </div>

      <Tabs defaultValue="organization">
        <TabsList>
          <TabsTrigger value="organization">Organization</TabsTrigger>
          <TabsTrigger value="workspaces">Workspaces</TabsTrigger>
        </TabsList>
        <TabsContent value="organization">
          <OrganizationSettings />
        </TabsContent>
        <TabsContent value="workspaces">
          <WorkspaceManagement />
        </TabsContent>
      </Tabs>
    </div>
  );
}
