"use client";

import * as React from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";

import { cssVarAsHsl } from "@/utils/design-tokens";
import type { GraphNode } from "@/lib/api/entities";
import type { Relationship } from "@/lib/api/relationships";

let registered = false;
function ensureRegistered() {
  if (!registered) {
    cytoscape.use(coseBilkent);
    registered = true;
  }
}

export type GraphMode = "explore" | "cluster" | "dependency" | "timeline";

const ENTITY_TYPE_COLOR_VAR: Record<string, string> = {
  person: "--primary",
  organization: "--secondary",
  team: "--secondary",
  project: "--info",
  technology: "--success",
  product: "--success",
  document: "--foreground-muted",
  decision: "--warning",
  policy: "--warning",
};

function nodeElement(
  node: GraphNode,
  sourceEntityId: string | null,
): ElementDefinition {
  return {
    data: {
      id: node.id,
      label: node.canonical_name,
      entityType: node.entity_type,
      confidence: node.confidence,
      isRoot: node.id === sourceEntityId,
    },
  };
}

function relationshipElements(
  relationships: Relationship[],
  nodeIds: Set<string>,
): ElementDefinition[] {
  return relationships
    .filter(
      (rel) =>
        nodeIds.has(rel.source_entity_id) && nodeIds.has(rel.target_entity_id),
    )
    .map((rel) => ({
      data: {
        id: rel.id,
        source: rel.source_entity_id,
        target: rel.target_entity_id,
        label: rel.custom_type_name ?? rel.relationship_type,
        relationshipType: rel.relationship_type,
      },
    }));
}

export function GraphCanvas({
  nodes,
  relationships,
  rootEntityId,
  mode,
  onSelectNode,
}: {
  nodes: GraphNode[];
  relationships: Relationship[];
  rootEntityId: string | null;
  mode: GraphMode;
  onSelectNode: (entityId: string) => void;
}) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const cyRef = React.useRef<Core | null>(null);

  React.useEffect(() => {
    ensureRegistered();
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      style: [
        {
          selector: "node",
          style: {
            "background-color": (el) =>
              cssVarAsHsl(
                ENTITY_TYPE_COLOR_VAR[el.data("entityType") as string] ??
                  "--foreground-muted",
              ),
            label: "data(label)",
            color: cssVarAsHsl("--foreground"),
            "font-size": 10,
            "text-valign": "bottom",
            "text-margin-y": 4,
            width: 28,
            height: 28,
            "border-width": (el) => (el.data("isRoot") ? 3 : 0),
            "border-color": cssVarAsHsl("--primary"),
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": cssVarAsHsl("--border-strong"),
            "target-arrow-color": cssVarAsHsl("--border-strong"),
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 8,
            color: cssVarAsHsl("--foreground-muted"),
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": cssVarAsHsl("--secondary"),
          },
        },
      ],
      wheelSensitivity: 0.3,
    });

    cy.on("tap", "node", (event) => {
      onSelectNode(event.target.id());
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const nodeIds = new Set(nodes.map((n) => n.id));
    const elements: ElementDefinition[] = [
      ...nodes.map((n) => nodeElement(n, rootEntityId)),
      ...relationshipElements(
        mode === "dependency"
          ? relationships.filter((r) => r.relationship_type === "dependency")
          : relationships,
        nodeIds,
      ),
    ];

    cy.elements().remove();
    cy.add(elements);

    if (mode === "cluster") {
      cy.layout({
        name: "cose-bilkent",
        animate: false,
        randomize: true,
      } as cytoscape.LayoutOptions).run();
    } else if (mode === "dependency") {
      cy.layout({
        name: "breadthfirst",
        directed: true,
        animate: false,
        spacingFactor: 1.2,
      }).run();
    } else if (mode === "timeline") {
      // Positions nodes left-to-right by creation order (real data —
      // GraphNode has no created_at from Neo4j, so entity insertion order
      // from the API response is used as the ordering proxy).
      const width = containerRef.current?.clientWidth ?? 800;
      cy.layout({
        name: "preset",
        positions: (node: cytoscape.NodeSingular) => {
          const index = nodes.findIndex((n) => n.id === node.id());
          return {
            x: (index / Math.max(nodes.length - 1, 1)) * (width - 80) + 40,
            y: 200 + (index % 3) * 60,
          };
        },
        animate: false,
      } as unknown as cytoscape.LayoutOptions).run();
    } else {
      cy.layout({
        name: "cose",
        animate: false,
      } as cytoscape.LayoutOptions).run();
    }

    cy.fit(undefined, 40);
  }, [nodes, relationships, mode, rootEntityId]);

  return (
    <div
      ref={containerRef}
      className="h-full w-full rounded-lg border border-border bg-background-subtle"
    />
  );
}
