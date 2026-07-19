"use client";

import * as React from "react";
import { Search } from "lucide-react";

import { formatStatusLabel, statusVariant } from "@/utils/status";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ResponsiveGrid } from "@/components/ui/responsive-grid";
import { Skeleton } from "@/components/ui/skeleton";
import { useEntitySearch } from "@/services/graph";
import {
  useBusFactor,
  useCoverageReport,
  useCriticalDependencies,
  useOrganizationalKnowledgeMap,
} from "@/services/capsules";
import type { BusFactor } from "@/lib/api/capsules";

function BusFactorCard({ result }: { result: BusFactor }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">{result.canonical_name}</CardTitle>
        <Badge variant={statusVariant(result.risk_level)}>
          {formatStatusLabel(result.risk_level)} risk
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <p className="text-sm">
          Bus factor: <span className="font-semibold">{result.bus_factor}</span>
        </p>
        <div className="flex flex-col gap-1">
          {result.owners.map((owner) => (
            <div
              key={owner.person_entity_id}
              className="flex items-center justify-between text-xs"
            >
              <span>{owner.canonical_name}</span>
              <span className="text-foreground-muted">
                {Math.round(owner.share * 100)}%
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function BusFactorLookup() {
  const [query, setQuery] = React.useState("");
  const { data: entities } = useEntitySearch(query);
  const [entityId, setEntityId] = React.useState<string | null>(null);
  const { data: busFactor, isLoading } = useBusFactor(entityId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bus Factor Lookup</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Popover open={query.trim().length > 1}>
          <PopoverTrigger asChild>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-icon-sm w-icon-sm text-foreground-muted" />
              <Input
                className="pl-8"
                placeholder="Search a resource entity..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-72 p-1">
            {entities?.items.map((entity) => (
              <button
                key={entity.id}
                type="button"
                className="flex w-full flex-col rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent"
                onClick={() => {
                  setEntityId(entity.id);
                  setQuery(entity.canonical_name);
                }}
              >
                {entity.canonical_name}
              </button>
            ))}
          </PopoverContent>
        </Popover>
        {isLoading && <Skeleton className="h-24 w-full" />}
        {busFactor && <BusFactorCard result={busFactor} />}
      </CardContent>
    </Card>
  );
}

export function OrganizationalRiskPanel() {
  const { data: coverage, isLoading: coverageLoading } = useCoverageReport();
  const { data: criticalDeps, isLoading: depsLoading } =
    useCriticalDependencies();
  const { data: orgMap, isLoading: orgMapLoading } =
    useOrganizationalKnowledgeMap();

  return (
    <div className="flex flex-col gap-6">
      <ResponsiveGrid cols={3}>
        <Card glass>
          <CardHeader>
            <CardTitle className="text-sm text-foreground-muted">
              Ownership Coverage
            </CardTitle>
          </CardHeader>
          <CardContent>
            {coverageLoading || !coverage ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <>
                <p className="text-h2 font-semibold">
                  {Math.round(coverage.coverage_score * 100)}%
                </p>
                <p className="text-xs text-foreground-muted">
                  {coverage.covered_entities} of {coverage.total_owned_entities}{" "}
                  entities covered
                </p>
              </>
            )}
          </CardContent>
        </Card>
        <Card glass>
          <CardHeader>
            <CardTitle className="text-sm text-foreground-muted">
              Single-Owner Entities
            </CardTitle>
          </CardHeader>
          <CardContent>
            {coverageLoading || !coverage ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <p className="text-h2 font-semibold">
                {coverage.single_owner_entities.length}
              </p>
            )}
          </CardContent>
        </Card>
        <Card glass>
          <CardHeader>
            <CardTitle className="text-sm text-foreground-muted">
              Critical Dependencies
            </CardTitle>
          </CardHeader>
          <CardContent>
            {depsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <p className="text-h2 font-semibold">
                {criticalDeps?.length ?? 0}
              </p>
            )}
          </CardContent>
        </Card>
      </ResponsiveGrid>

      <BusFactorLookup />

      <Card>
        <CardHeader>
          <CardTitle>Critical Dependencies</CardTitle>
        </CardHeader>
        <CardContent>
          {depsLoading && <Skeleton className="h-24 w-full" />}
          {!depsLoading && criticalDeps?.length === 0 && (
            <p className="text-sm text-foreground-muted">
              No critical dependencies detected.
            </p>
          )}
          <ResponsiveGrid cols={2}>
            {criticalDeps?.map((dep) => (
              <BusFactorCard key={dep.entity_id} result={dep} />
            ))}
          </ResponsiveGrid>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Organizational Knowledge Map</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {orgMapLoading && <Skeleton className="h-32 w-full" />}
          {!orgMapLoading && orgMap?.length === 0 && (
            <p className="text-sm text-foreground-muted">
              No capsules to map yet.
            </p>
          )}
          {orgMap?.map((entry) => (
            <div
              key={entry.capsule_id}
              className="flex items-center justify-between rounded-md border border-border p-2 text-sm"
            >
              <div>
                <p>{entry.organizational_role ?? "Unassigned role"}</p>
                <p className="text-xs text-foreground-muted">
                  {entry.top_expertise.length} expertise ·{" "}
                  {entry.top_ownership.length} ownership
                </p>
              </div>
              {entry.is_stale && <Badge variant="warning">Stale</Badge>}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
