import { BookOpen, Users2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { InsightList } from "@/features/capsules/insight-list";
import { useSuccessorPlan } from "@/services/capsules";

export function SuccessorPlanPanel({ capsuleId }: { capsuleId: string }) {
  const { data: plan, isLoading } = useSuccessorPlan(capsuleId);

  if (isLoading || !plan) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {plan.immediate_priorities.length > 0 && (
        <div className="rounded-md border border-warning/40 bg-warning/10 p-3">
          <p className="mb-2 text-sm font-medium">Immediate priorities</p>
          <ul className="list-inside list-disc space-y-1 text-sm">
            {plan.immediate_priorities.map((priority, i) => (
              <li key={i}>{priority}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <p className="mb-2 text-sm font-medium">
          Critical repositories &amp; resources to hand off
        </p>
        <InsightList
          entries={plan.critical_repositories}
          metric="share"
          emptyMessage="No critical ownership to hand off."
        />
      </div>

      <div>
        <p className="mb-2 flex items-center gap-1.5 text-sm font-medium">
          <Users2 className="h-icon-sm w-icon-sm" />
          Key collaborators to loop in
        </p>
        <InsightList
          entries={plan.key_collaborators}
          metric="strength"
          emptyMessage="No known collaborators."
        />
      </div>

      <div>
        <p className="mb-2 text-sm font-medium">Suggested learning sequence</p>
        <InsightList
          entries={plan.learning_sequence}
          metric="score"
          emptyMessage="No learning sequence available."
        />
      </div>

      <div>
        <p className="mb-2 flex items-center gap-1.5 text-sm font-medium">
          <BookOpen className="h-icon-sm w-icon-sm" />
          Recommended reading
        </p>
        {plan.recommended_reading.length === 0 && (
          <p className="text-sm text-foreground-muted">
            No source documents linked to these insights yet.
          </p>
        )}
        <div className="flex flex-col gap-2">
          {plan.recommended_reading.map((item, i) => (
            <div
              key={i}
              className="rounded-md border border-border p-2 text-sm"
            >
              <p>
                {item.description ?? item.insight_key ?? "Untitled reference"}
              </p>
              {item.external_url && (
                <a
                  href={item.external_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-primary underline"
                >
                  {item.external_url}
                </a>
              )}
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium">Open work</p>
        {plan.open_work.length === 0 && (
          <p className="text-sm text-foreground-muted">No recent open work.</p>
        )}
        <div className="flex flex-col gap-1.5">
          {plan.open_work.map((event, i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <span>{event.title}</span>
              <Badge variant="outline">{event.event_type}</Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
