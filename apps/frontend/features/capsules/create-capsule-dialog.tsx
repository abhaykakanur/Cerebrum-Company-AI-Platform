"use client";

import * as React from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { getCurrentUser } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateCapsule } from "@/services/capsules";

/** No `GET /users` endpoint exists anywhere in the backend, so there is
 * no directory to pick a person from — the field is pre-filled with the
 * caller's own user ID (`GET /auth/me`) as the common case, with the
 * UUID left directly editable for the org-admin case of creating a
 * capsule on behalf of someone else whose ID they already know. */
export function CreateCapsuleDialog() {
  const [open, setOpen] = React.useState(false);
  const [userId, setUserId] = React.useState("");
  const createCapsule = useCreateCapsule();

  React.useEffect(() => {
    if (open && !userId) {
      getCurrentUser()
        .then((user) => setUserId(user.id))
        .catch(() => {});
    }
  }, [open, userId]);

  const handleCreate = async () => {
    try {
      await createCapsule.mutateAsync(userId.trim());
      toast.success("Capsule created.");
      setOpen(false);
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to create capsule.",
      );
    }
  };

  return (
    <>
      <Button className="gap-1.5" onClick={() => setOpen(true)}>
        <Plus className="h-icon-sm w-icon-sm" />
        New capsule
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Knowledge Capsule</DialogTitle>
            <DialogDescription>
              Pre-filled with your own user ID. Change it to create a capsule
              for someone else if you know their user ID.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor="capsule-user-id">User ID</Label>
            <Input
              id="capsule-user-id"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button
              onClick={handleCreate}
              loading={createCapsule.isPending}
              disabled={!userId.trim()}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
