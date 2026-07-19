"use client";

import { useParams } from "next/navigation";

import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Timeline, type TimelineItem } from "@/components/ui/timeline";
import { ProfilePanel } from "@/features/capsules/profile-panel";
import { InsightList } from "@/features/capsules/insight-list";
import { SuccessorPlanPanel } from "@/features/capsules/successor-plan-panel";
import { AICapsulePanel } from "@/features/capsules/ai-capsule-panel";
import { ComparePanel } from "@/features/capsules/compare-panel";
import { useCapsule, useCapsuleTimeline } from "@/services/capsules";

function CapsuleTimelinePanel({ capsuleId }: { capsuleId: string }) {
  const { data, isLoading } = useCapsuleTimeline(capsuleId);
  if (isLoading) return <Skeleton className="h-64 w-full" />;

  const items: TimelineItem[] = (data?.items ?? []).map((event) => ({
    id: event.id,
    title: event.title,
    description: event.description,
    timestamp: new Date(event.occurred_at).toLocaleDateString(),
  }));

  return <Timeline items={items} />;
}

export default function CapsuleDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: capsule, isLoading } = useCapsule(params.id);

  if (isLoading || !capsule) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-h1 font-semibold">
          {capsule.organizational_role ?? "Employee Knowledge Capsule"}
        </h1>
        <p className="text-sm text-foreground-muted">
          Digital organizational twin — evidence-backed insights only.
        </p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList className="flex-wrap">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="expertise">Expertise</TabsTrigger>
          <TabsTrigger value="ownership">Ownership</TabsTrigger>
          <TabsTrigger value="collaboration">Collaboration</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="successor">Successor Plan</TabsTrigger>
          <TabsTrigger value="ai-capsule">AI Capsule</TabsTrigger>
          <TabsTrigger value="compare">Compare</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <ProfilePanel capsule={capsule} />
        </TabsContent>
        <TabsContent value="expertise">
          <InsightList
            entries={capsule.expertise_map}
            metric="score"
            emptyMessage="No expertise areas detected yet."
          />
        </TabsContent>
        <TabsContent value="ownership">
          <InsightList
            entries={capsule.ownership_map}
            metric="share"
            emptyMessage="No ownership detected yet."
          />
        </TabsContent>
        <TabsContent value="collaboration">
          <InsightList
            entries={capsule.collaboration_network}
            metric="strength"
            emptyMessage="No collaboration signal detected yet."
          />
        </TabsContent>
        <TabsContent value="timeline">
          <CapsuleTimelinePanel capsuleId={capsule.id} />
        </TabsContent>
        <TabsContent value="successor">
          <SuccessorPlanPanel capsuleId={capsule.id} />
        </TabsContent>
        <TabsContent value="ai-capsule">
          <AICapsulePanel capsuleId={capsule.id} />
        </TabsContent>
        <TabsContent value="compare">
          <ComparePanel current={capsule} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
