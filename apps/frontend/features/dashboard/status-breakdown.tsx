import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { statusVariant, formatStatusLabel } from "@/utils/status";

export function StatusBreakdown({
  title,
  href,
  items,
  loading,
  emptyMessage,
}: {
  title: string;
  href: string;
  items: { status: string }[] | undefined;
  loading: boolean;
  emptyMessage: string;
}) {
  const counts = (items ?? []).reduce<Record<string, number>>((acc, item) => {
    acc[item.status] = (acc[item.status] ?? 0) + 1;
    return acc;
  }, {});
  const entries = Object.entries(counts);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>{title}</CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href={href}>View all</Link>
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-full" />
          </div>
        ) : entries.length === 0 ? (
          <p className="text-sm text-foreground-muted">{emptyMessage}</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {entries.map(([status, count]) => (
              <Badge key={status} variant={statusVariant(status)}>
                {formatStatusLabel(status)}: {count}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
