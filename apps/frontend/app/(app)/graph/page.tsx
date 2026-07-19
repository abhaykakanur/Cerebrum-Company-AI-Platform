"use client";

import * as React from "react";
import { Share2 } from "lucide-react";

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { GraphToolbar } from "@/features/graph/graph-toolbar";
import { GraphCanvas, type GraphMode } from "@/features/graph/graph-canvas";
import { GraphContextPanel } from "@/features/graph/graph-context-panel";
import { useEntityNeighbors, useEntityRelationships } from "@/services/graph";

export default function GraphPage() {
  const [rootEntityId, setRootEntityId] = React.useState<string | null>(null);
  const [rootEntityName, setRootEntityName] = React.useState<string | null>(
    null,
  );
  const [selectedEntityId, setSelectedEntityId] = React.useState<string | null>(
    null,
  );
  const [mode, setMode] = React.useState<GraphMode>("explore");
  const [depth, setDepth] = React.useState(2);

  const { data: neighbors, isLoading } = useEntityNeighbors(
    rootEntityId,
    depth,
  );
  const { data: rootRelationships } = useEntityRelationships(rootEntityId);

  const nodes = React.useMemo(() => {
    if (!rootEntityId || !neighbors) return [];
    const hasRoot = neighbors.some((n) => n.id === rootEntityId);
    if (hasRoot) return neighbors;
    return [
      {
        id: rootEntityId,
        workspace_id: "",
        entity_type: "custom",
        canonical_name: rootEntityName ?? "Selected entity",
        aliases: [],
        confidence: 1,
      },
      ...neighbors,
    ];
  }, [rootEntityId, rootEntityName, neighbors]);

  const relationships = rootRelationships?.items ?? [];

  return (
    <div className="flex h-[calc(100vh-9rem)] flex-col gap-4">
      <div>
        <h1 className="text-h1 font-semibold">Knowledge Graph</h1>
        <p className="text-sm text-foreground-muted">
          Explore entities and relationships across your workspace.
        </p>
      </div>
      <GraphToolbar
        mode={mode}
        onModeChange={setMode}
        depth={depth}
        onDepthChange={setDepth}
        onSelectEntity={(id, name) => {
          setRootEntityId(id);
          setRootEntityName(name);
          setSelectedEntityId(id);
        }}
      />
      <ResizablePanelGroup
        direction="horizontal"
        className="flex-1 rounded-lg border border-border"
      >
        <ResizablePanel defaultSize={75} minSize={50}>
          {!rootEntityId ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
              <Share2 className="h-icon-xl w-icon-xl text-foreground-muted" />
              <p className="text-foreground-muted">
                Search for an entity above to visualize its graph.
              </p>
            </div>
          ) : isLoading ? (
            <div className="flex h-full items-center justify-center text-sm text-foreground-muted">
              Loading graph...
            </div>
          ) : (
            <GraphCanvas
              nodes={nodes}
              relationships={relationships}
              rootEntityId={rootEntityId}
              mode={mode}
              onSelectNode={setSelectedEntityId}
            />
          )}
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={25} minSize={20}>
          <GraphContextPanel entityId={selectedEntityId} />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
