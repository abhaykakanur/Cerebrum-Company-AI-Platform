"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useAuth } from "@/providers/auth-provider";
import { createWorkspace } from "@/lib/api/workspaces";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// Workspace selector — reached when an authenticated user belongs to no
// workspace yet (FR-OR-002 Multi-Workspace Organization Structure). Lives
// outside the `(app)` route group deliberately: that group's AppShell
// redirects here precisely because it requires at least one workspace to
// render, so this page must not be wrapped by it.
export default function NewWorkspacePage() {
  const {
    isAuthenticated,
    isLoading,
    workspaces,
    selectWorkspace,
    refreshWorkspaces,
  } = useAuth();
  const router = useRouter();
  const [name, setName] = React.useState("");
  const [slug, setSlug] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/login");
    else if (!isLoading && workspaces.length > 0) router.replace("/dashboard");
  }, [isLoading, isAuthenticated, workspaces.length, router]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const workspace = await createWorkspace(name.trim(), slug.trim());
      await refreshWorkspaces();
      selectWorkspace(workspace.id);
      router.replace("/dashboard");
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to create workspace.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Create your first workspace</CardTitle>
          <CardDescription>
            Workspaces organize your organization&apos;s knowledge and access.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="slug">Slug</Label>
              <Input
                id="slug"
                required
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
              />
            </div>
            <Button type="submit" loading={submitting} className="mt-2">
              Create workspace
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
