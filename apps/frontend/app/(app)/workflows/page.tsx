"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Workflow as WorkflowIcon } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { ResponsiveGrid } from "@/components/ui/responsive-grid";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { WorkflowCard } from "@/features/workflows/workflow-card";
import {
  useCreateWorkflow,
  useWorkflowTemplates,
  useWorkflows,
} from "@/services/workflows";
import type { Workflow } from "@/lib/api/workflows";

export default function WorkflowsPage() {
  const workflows = useWorkflows();
  const templates = useWorkflowTemplates();
  const createFromTemplate = useCreateWorkflow();
  const router = useRouter();

  const handleUseTemplate = async (template: Workflow) => {
    try {
      const created = await createFromTemplate.mutateAsync({
        name: `${template.name} (copy)`,
        description: template.description ?? undefined,
        trigger_type: "manual",
        steps: [],
      });
      toast.success("Workflow created from template.");
      router.push(`/workflows/${created.id}`);
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to create from template.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 font-semibold">Workflows</h1>
          <p className="text-sm text-foreground-muted">
            Automate actions across your workspace.
          </p>
        </div>
        <Button asChild className="gap-1.5">
          <Link href="/workflows/new">
            <Plus className="h-icon-sm w-icon-sm" />
            New workflow
          </Link>
        </Button>
      </div>

      <Tabs defaultValue="workflows">
        <TabsList>
          <TabsTrigger value="workflows">My Workflows</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
        </TabsList>

        <TabsContent value="workflows">
          {workflows.isLoading && (
            <ResponsiveGrid cols={3}>
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-36 w-full" />
              ))}
            </ResponsiveGrid>
          )}
          {!workflows.isLoading && workflows.data?.items.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-16 text-center">
              <WorkflowIcon className="h-icon-xl w-icon-xl text-foreground-muted" />
              <p className="text-foreground-muted">No workflows yet.</p>
            </div>
          )}
          <ResponsiveGrid cols={3}>
            {workflows.data?.items.map((workflow) => (
              <WorkflowCard key={workflow.id} workflow={workflow} />
            ))}
          </ResponsiveGrid>
        </TabsContent>

        <TabsContent value="templates">
          {templates.isLoading && <Skeleton className="h-36 w-full" />}
          {!templates.isLoading && templates.data?.items.length === 0 && (
            <p className="py-8 text-center text-sm text-foreground-muted">
              No templates available.
            </p>
          )}
          <ResponsiveGrid cols={3}>
            {templates.data?.items.map((template) => (
              <div
                key={template.id}
                className="flex flex-col gap-2 rounded-lg border border-border p-4"
              >
                <p className="font-medium">{template.name}</p>
                {template.description && (
                  <p className="text-xs text-foreground-muted">
                    {template.description}
                  </p>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleUseTemplate(template)}
                >
                  Use template
                </Button>
              </div>
            ))}
          </ResponsiveGrid>
        </TabsContent>
      </Tabs>
    </div>
  );
}
