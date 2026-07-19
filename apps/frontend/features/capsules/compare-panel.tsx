"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useCapsules, useCompareCapsules } from "@/services/capsules";
import type { Capsule } from "@/lib/api/capsules";

function TagGroup({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-foreground-muted">
        {title}
      </p>
      {items.length === 0 ? (
        <p className="text-xs text-foreground-muted">None</p>
      ) : (
        <div className="flex flex-wrap gap-1">
          {items.map((item) => (
            <Badge key={item} variant="outline">
              {item}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

export function ComparePanel({ current }: { current: Capsule }) {
  const { data: capsules } = useCapsules();
  const [otherUserId, setOtherUserId] = React.useState<string | null>(null);
  const { data: comparison, isLoading } = useCompareCapsules(
    current.user_id,
    otherUserId,
  );

  const others =
    capsules?.items.filter((c) => c.user_id !== current.user_id) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <Select value={otherUserId ?? undefined} onValueChange={setOtherUserId}>
        <SelectTrigger className="w-64">
          <SelectValue placeholder="Compare with..." />
        </SelectTrigger>
        <SelectContent>
          {others.map((capsule) => (
            <SelectItem key={capsule.user_id} value={capsule.user_id}>
              {capsule.organizational_role ?? capsule.user_id}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {isLoading && <Skeleton className="h-48 w-full" />}

      {comparison && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <TagGroup
            title="Shared expertise"
            items={comparison.shared_expertise}
          />
          <TagGroup
            title="This person only"
            items={comparison.unique_expertise_a}
          />
          <TagGroup
            title="Other person only"
            items={comparison.unique_expertise_b}
          />
          <TagGroup
            title="Shared ownership"
            items={comparison.shared_ownership}
          />
          <TagGroup
            title="This person only"
            items={comparison.unique_ownership_a}
          />
          <TagGroup
            title="Other person only"
            items={comparison.unique_ownership_b}
          />
        </div>
      )}
    </div>
  );
}
