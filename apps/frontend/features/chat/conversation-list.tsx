"use client";

import * as React from "react";
import { Archive, MoreVertical, Pin, Plus, Search, Trash2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  useArchiveConversation,
  useConversationSearch,
  useConversations,
  useCreateConversation,
  useDeleteConversation,
  usePinnedConversations,
  type Conversation,
} from "@/services/chat";

export function ConversationList({
  activeId,
  onSelect,
}: {
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  const [query, setQuery] = React.useState("");
  const conversations = useConversations("active");
  const searchResults = useConversationSearch(query);
  const createConversation = useCreateConversation();
  const archiveConversation = useArchiveConversation();
  const deleteConversation = useDeleteConversation();
  const { pinned, togglePin } = usePinnedConversations();

  const items = query.trim()
    ? (searchResults.data?.items ?? [])
    : (conversations.data?.items ?? []);
  const sorted = [...items].sort((a, b) => {
    const aPinned = pinned.has(a.id) ? 1 : 0;
    const bPinned = pinned.has(b.id) ? 1 : 0;
    if (aPinned !== bPinned) return bPinned - aPinned;
    return (b.last_message_at ?? b.created_at).localeCompare(
      a.last_message_at ?? a.created_at,
    );
  });

  const handleNew = async () => {
    const conversation = await createConversation.mutateAsync(undefined);
    onSelect(conversation.id);
  };

  return (
    <div className="flex h-full flex-col gap-3 border-r border-border p-3">
      <Button
        onClick={handleNew}
        loading={createConversation.isPending}
        className="gap-2"
      >
        <Plus className="h-icon-sm w-icon-sm" />
        New conversation
      </Button>
      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 h-icon-sm w-icon-sm text-foreground-muted" />
        <Input
          placeholder="Search conversations..."
          className="pl-8"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <div className="flex flex-1 flex-col gap-1 overflow-y-auto">
        {(conversations.isLoading ||
          (query.trim() && searchResults.isLoading)) &&
          Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        {!conversations.isLoading &&
          sorted.length === 0 &&
          !(query.trim() && searchResults.isLoading) && (
            <p className="p-2 text-sm text-foreground-muted">
              No conversations yet.
            </p>
          )}
        {sorted.map((conversation) => (
          <ConversationRow
            key={conversation.id}
            conversation={conversation}
            active={conversation.id === activeId}
            pinned={pinned.has(conversation.id)}
            onSelect={() => onSelect(conversation.id)}
            onTogglePin={() => togglePin(conversation.id)}
            onArchive={() => archiveConversation.mutate(conversation.id)}
            onDelete={() => deleteConversation.mutate(conversation.id)}
          />
        ))}
      </div>
    </div>
  );
}

function ConversationRow({
  conversation,
  active,
  pinned,
  onSelect,
  onTogglePin,
  onArchive,
  onDelete,
}: {
  conversation: Conversation;
  active: boolean;
  pinned: boolean;
  onSelect: () => void;
  onTogglePin: () => void;
  onArchive: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className={cn(
        "group flex items-center gap-1 rounded-md px-2 py-2 text-sm",
        active ? "bg-accent text-accent-foreground" : "hover:bg-accent/50",
      )}
    >
      <button
        type="button"
        onClick={onSelect}
        className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
      >
        {pinned && (
          <Pin className="h-icon-xs w-icon-xs shrink-0 text-primary" />
        )}
        <span className="truncate">
          {conversation.title || "Untitled conversation"}
        </span>
      </button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 shrink-0 opacity-0 group-hover:opacity-100"
          >
            <MoreVertical className="h-icon-xs w-icon-xs" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={onTogglePin}>
            <Pin className="h-icon-xs w-icon-xs" />
            {pinned ? "Unpin" : "Pin"}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={onArchive}>
            <Archive className="h-icon-xs w-icon-xs" />
            Archive
          </DropdownMenuItem>
          <DropdownMenuItem destructive onSelect={onDelete}>
            <Trash2 className="h-icon-xs w-icon-xs" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
