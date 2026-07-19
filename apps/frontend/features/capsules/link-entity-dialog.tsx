"use client";

import * as React from "react";
import { Link2, Search } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useEntitySearch } from "@/services/graph";
import { useLinkPersonEntity } from "@/services/capsules";

/**
 * Identity linkage is explicit and human-confirmed, never automatic
 * name-matching (extracted PERSON entities from document text are
 * unreliable) — the user searches and picks the real graph entity
 * themselves.
 */
export function LinkEntityDialog({ capsuleId }: { capsuleId: string }) {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const { data: entities, isLoading } = useEntitySearch(query);
  const linkEntity = useLinkPersonEntity(capsuleId);

  const handleLink = async (entityId: string) => {
    try {
      await linkEntity.mutateAsync(entityId);
      toast.success("Person entity linked.");
      setOpen(false);
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to link entity.",
      );
    }
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="gap-1.5"
        onClick={() => setOpen(true)}
      >
        <Link2 className="h-icon-xs w-icon-xs" />
        Link person entity
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Link person entity</DialogTitle>
            <DialogDescription>
              Search the knowledge graph for the real Person entity this capsule
              represents.
            </DialogDescription>
          </DialogHeader>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-icon-sm w-icon-sm text-foreground-muted" />
            <Input
              className="pl-8"
              placeholder="Search entities..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
          </div>
          <div className="flex max-h-64 flex-col gap-1 overflow-y-auto">
            {isLoading && (
              <p className="p-2 text-xs text-foreground-muted">Searching...</p>
            )}
            {entities?.items.map((entity) => (
              <button
                key={entity.id}
                type="button"
                className="flex items-center justify-between rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                onClick={() => handleLink(entity.id)}
                disabled={linkEntity.isPending}
              >
                <span>{entity.canonical_name}</span>
                <span className="text-xs capitalize text-foreground-muted">
                  {entity.entity_type}
                </span>
              </button>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
