import Link from "next/link";
import { AlertTriangle, UserSquare2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Capsule } from "@/lib/api/capsules";

export function CapsuleCard({ capsule }: { capsule: Capsule }) {
  return (
    <Link href={`/capsules/${capsule.id}`}>
      <Card className="transition-colors duration-fast hover:bg-accent/50">
        <CardHeader className="flex-row items-start justify-between space-y-0">
          <div className="flex items-center gap-2">
            <UserSquare2 className="h-icon-md w-icon-md text-foreground-muted" />
            <div>
              <CardTitle className="text-base">
                {capsule.organizational_role ?? "Unassigned role"}
              </CardTitle>
              <p className="text-xs text-foreground-muted">
                {capsule.person_entity_id ? "Linked" : "Unlinked"}
              </p>
            </div>
          </div>
          {capsule.is_stale && (
            <Badge variant="warning" className="gap-1">
              <AlertTriangle className="h-icon-xs w-icon-xs" />
              Stale
            </Badge>
          )}
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 text-xs text-foreground-muted">
          <span>{capsule.expertise_map.length} expertise areas</span>
          <span>{capsule.ownership_map.length} owned resources</span>
          <span>{capsule.collaboration_network.length} collaborators</span>
        </CardContent>
      </Card>
    </Link>
  );
}
