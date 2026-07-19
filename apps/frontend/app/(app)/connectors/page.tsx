"use client";

import { Plug } from "lucide-react";

import { useContextDrawer } from "@/layouts/context-drawer";
import { ResponsiveGrid } from "@/components/ui/responsive-grid";
import { Skeleton } from "@/components/ui/skeleton";
import { RegisterConnectorDialog } from "@/features/connectors/register-connector-dialog";
import { ConnectorCard } from "@/features/connectors/connector-card";
import { SyncHistoryPanel } from "@/features/connectors/sync-history-panel";
import { useConnectors } from "@/services/connectors";

export default function ConnectorsPage() {
  const { data, isLoading } = useConnectors();
  const drawer = useContextDrawer();

  const openHistory = (connectorId: string, name: string) => {
    drawer.open({
      title: `${name} — Sync History`,
      content: <SyncHistoryPanel connectorId={connectorId} />,
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 font-semibold">Connectors</h1>
          <p className="text-sm text-foreground-muted">
            Manage source system connections and sync activity.
          </p>
        </div>
        <RegisterConnectorDialog />
      </div>

      {isLoading && (
        <ResponsiveGrid cols={3}>
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </ResponsiveGrid>
      )}

      {!isLoading && data?.items.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-16 text-center">
          <Plug className="h-icon-xl w-icon-xl text-foreground-muted" />
          <p className="text-foreground-muted">No connectors registered yet.</p>
        </div>
      )}

      <ResponsiveGrid cols={3}>
        {data?.items.map((connector) => (
          <ConnectorCard
            key={connector.id}
            connector={connector}
            onOpenHistory={() => openHistory(connector.id, connector.name)}
          />
        ))}
      </ResponsiveGrid>
    </div>
  );
}
