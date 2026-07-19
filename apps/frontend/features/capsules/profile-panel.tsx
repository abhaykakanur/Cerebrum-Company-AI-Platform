"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import type { Capsule } from "@/lib/api/capsules";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { LinkEntityDialog } from "@/features/capsules/link-entity-dialog";
import {
  useDeleteCapsule,
  useRefreshCapsule,
  useUpdateCapsuleProfile,
} from "@/services/capsules";

export function ProfilePanel({ capsule }: { capsule: Capsule }) {
  const router = useRouter();
  const [role, setRole] = React.useState(capsule.organizational_role ?? "");
  const [responsibilities, setResponsibilities] = React.useState(
    capsule.responsibilities.join("\n"),
  );
  const updateProfile = useUpdateCapsuleProfile(capsule.id);
  const refresh = useRefreshCapsule(capsule.id);
  const deleteCapsule = useDeleteCapsule();

  const handleSaveProfile = async () => {
    try {
      await updateProfile.mutateAsync({
        organizational_role: role.trim() || null,
        responsibilities: responsibilities
          .split("\n")
          .map((r) => r.trim())
          .filter(Boolean),
      });
      toast.success("Profile updated.");
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to update profile.",
      );
    }
  };

  const handleRefresh = async () => {
    try {
      await refresh.mutateAsync();
      toast.success("Capsule refreshed from the latest knowledge graph.");
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to refresh capsule.",
      );
    }
  };

  const handleDelete = async () => {
    try {
      await deleteCapsule.mutateAsync(capsule.id);
      toast.success("Capsule deleted.");
      router.push("/capsules");
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to delete capsule.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        {capsule.is_stale && (
          <Badge variant="warning" className="gap-1">
            <AlertTriangle className="h-icon-xs w-icon-xs" />
            {capsule.stale_reason ?? "Stale — refresh recommended"}
          </Badge>
        )}
        <span className="text-xs text-foreground-muted">
          Last refreshed:{" "}
          {capsule.last_refreshed_at
            ? new Date(capsule.last_refreshed_at).toLocaleString()
            : "Never"}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {!capsule.person_entity_id && (
          <LinkEntityDialog capsuleId={capsule.id} />
        )}
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={handleRefresh}
          loading={refresh.isPending}
        >
          <RefreshCw className="h-icon-xs w-icon-xs" />
          Refresh
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="ml-auto gap-1.5"
          onClick={handleDelete}
        >
          <Trash2 className="h-icon-xs w-icon-xs text-danger" />
          Delete capsule
        </Button>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="org-role">Organizational role</Label>
        <Input
          id="org-role"
          value={role}
          onChange={(e) => setRole(e.target.value)}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="responsibilities">
          Responsibilities (one per line)
        </Label>
        <Textarea
          id="responsibilities"
          value={responsibilities}
          onChange={(e) => setResponsibilities(e.target.value)}
          className="min-h-24"
        />
      </div>
      <Button
        className="w-fit"
        onClick={handleSaveProfile}
        loading={updateProfile.isPending}
      >
        Save profile
      </Button>
    </div>
  );
}
