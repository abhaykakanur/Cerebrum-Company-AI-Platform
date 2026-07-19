import type { LucideIcon } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

// Marks a nav destination whose route exists (so the Sidebar/Command
// Palette/Breadcrumbs work end to end) but whose feature area hasn't been
// built yet in this "one feature area at a time" build-out — see the CIS
// Phase 5 Prompt 4 todo list. Each page importing this is replaced with
// its real implementation when that feature area's turn comes.
export function FeaturePlaceholder({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <Card className="mx-auto max-w-xl">
      <CardHeader className="items-center text-center">
        <Icon className="h-icon-xl w-icon-xl text-foreground-muted" />
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="text-center text-sm text-foreground-muted">
        This feature area is being built next in the implementation sequence.
      </CardContent>
    </Card>
  );
}
