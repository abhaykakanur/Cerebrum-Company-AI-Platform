"use client";

import { Share2, Search, MessageSquare, FileText } from "lucide-react";

import { useDashboardData } from "@/services/dashboard";
import { ResponsiveGrid } from "@/components/ui/responsive-grid";
import { StatCard } from "@/features/dashboard/stat-card";
import { HealthPanel } from "@/features/dashboard/health-panel";
import { StatusBreakdown } from "@/features/dashboard/status-breakdown";

export default function DashboardPage() {
  const {
    health,
    graphStats,
    retrievalStats,
    aiStats,
    connectors,
    workflows,
    documents,
  } = useDashboardData();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-h1 font-semibold">Dashboard</h1>
        <p className="text-sm text-foreground-muted">
          Your workspace at a glance.
        </p>
      </div>

      <ResponsiveGrid cols={4} maxColsUltrawide={4}>
        <StatCard
          icon={FileText}
          label="Documents"
          value={documents.data?.pagination?.total_items ?? 0}
          loading={documents.isLoading}
        />
        <StatCard
          icon={Share2}
          label="Knowledge Graph Entities"
          value={graphStats.data?.entity_count ?? 0}
          loading={graphStats.isLoading}
        />
        <StatCard
          icon={Search}
          label="Indexed Documents"
          value={retrievalStats.data?.indexed_document_count ?? 0}
          loading={retrievalStats.isLoading}
        />
        <StatCard
          icon={MessageSquare}
          label="AI Questions Asked"
          value={aiStats.data?.question_count ?? 0}
          loading={aiStats.isLoading}
        />
      </ResponsiveGrid>

      <ResponsiveGrid cols={3} maxColsUltrawide={4}>
        <HealthPanel health={health.data} loading={health.isLoading} />
        <StatusBreakdown
          title="Connectors"
          href="/connectors"
          items={connectors.data?.items}
          loading={connectors.isLoading}
          emptyMessage="No connectors registered yet."
        />
        <StatusBreakdown
          title="Workflows"
          href="/workflows"
          items={workflows.data?.items}
          loading={workflows.isLoading}
          emptyMessage="No workflows created yet."
        />
      </ResponsiveGrid>
    </div>
  );
}
