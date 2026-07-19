"use client";

import { UserSquare2 } from "lucide-react";

import { ResponsiveGrid } from "@/components/ui/responsive-grid";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CapsuleCard } from "@/features/capsules/capsule-card";
import { CreateCapsuleDialog } from "@/features/capsules/create-capsule-dialog";
import { OrganizationalRiskPanel } from "@/features/capsules/organizational-risk-panel";
import { useCapsules } from "@/services/capsules";

export default function CapsulesPage() {
  const { data, isLoading } = useCapsules();

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 font-semibold">Employee Knowledge Capsules</h1>
          <p className="text-sm text-foreground-muted">
            The digital organizational twin — expertise, ownership, and
            succession risk, backed entirely by evidence.
          </p>
        </div>
        <CreateCapsuleDialog />
      </div>

      <Tabs defaultValue="capsules">
        <TabsList>
          <TabsTrigger value="capsules">Capsules</TabsTrigger>
          <TabsTrigger value="risk">Organizational Risk</TabsTrigger>
        </TabsList>

        <TabsContent value="capsules">
          {isLoading && (
            <ResponsiveGrid cols={3}>
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-32 w-full" />
              ))}
            </ResponsiveGrid>
          )}
          {!isLoading && data?.items.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-16 text-center">
              <UserSquare2 className="h-icon-xl w-icon-xl text-foreground-muted" />
              <p className="text-foreground-muted">No capsules yet.</p>
            </div>
          )}
          <ResponsiveGrid cols={3}>
            {data?.items.map((capsule) => (
              <CapsuleCard key={capsule.id} capsule={capsule} />
            ))}
          </ResponsiveGrid>
        </TabsContent>

        <TabsContent value="risk">
          <OrganizationalRiskPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
