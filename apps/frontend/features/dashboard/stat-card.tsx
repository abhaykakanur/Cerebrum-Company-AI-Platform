import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function StatCard({
  icon: Icon,
  label,
  value,
  loading,
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  loading?: boolean;
}) {
  return (
    <Card glass>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-foreground-muted">
          {label}
        </CardTitle>
        <Icon className="h-icon-md w-icon-md text-foreground-muted" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-20" />
        ) : (
          <p className="text-h2 font-semibold">{value}</p>
        )}
      </CardContent>
    </Card>
  );
}
