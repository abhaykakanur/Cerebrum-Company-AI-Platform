"use client";

import { Bell } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

// Notification Center — Layout System element. 93_Notification_Architecture.md
// specifies this surface, but no notification-emitting backend endpoint
// exists yet in the implemented API (CIS Phase 1-5.3's 130 routes have no
// `/notifications` resource) — per the Thin Frontend rule, this renders
// its honest empty state rather than fabricating notification data.
// Swapping in `lib/api/notifications.ts` once that backend capability
// ships is a drop-in change to this one component.
export function NotificationCenter() {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="h-icon-md w-icon-md" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80">
        <p className="text-sm font-medium">Notifications</p>
        <p className="mt-2 text-sm text-foreground-muted">
          You&apos;re all caught up. No new notifications.
        </p>
      </PopoverContent>
    </Popover>
  );
}
