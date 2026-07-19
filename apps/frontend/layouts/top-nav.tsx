"use client";

import Link from "next/link";
import { Search } from "lucide-react";

import { WorkspaceSwitcher } from "@/layouts/workspace-switcher";
import { NotificationCenter } from "@/layouts/notification-center";
import { ProfileMenu } from "@/layouts/profile-menu";
import { Button } from "@/components/ui/button";

// Top Navigation — Layout System element. Sticky, hosts the Workspace
// Switcher, the Command Palette's visible entry point, Notification
// Center, and Profile Menu.
export function TopNav() {
  const isMac =
    typeof navigator !== "undefined" && /Mac/.test(navigator.platform);

  return (
    <header className="sticky top-0 z-sticky flex h-14 shrink-0 items-center gap-4 border-b border-border bg-background/95 px-4 backdrop-blur-sm">
      <Link href="/dashboard" className="text-h3 font-semibold tracking-tight">
        Cerebrum
      </Link>
      <WorkspaceSwitcher />
      <Button
        variant="outline"
        size="sm"
        className="ml-auto hidden w-64 justify-between text-foreground-muted sm:flex"
        onClick={() =>
          document.dispatchEvent(
            new KeyboardEvent("keydown", { key: "k", metaKey: true }),
          )
        }
      >
        <span className="flex items-center gap-2">
          <Search className="h-icon-sm w-icon-sm" />
          Search or jump to...
        </span>
        <kbd className="rounded-sm border border-border bg-background-subtle px-1.5 py-0.5 text-xs">
          {isMac ? "⌘K" : "Ctrl K"}
        </kbd>
      </Button>
      <div className="ml-auto flex items-center gap-1 sm:ml-0">
        <NotificationCenter />
        <ProfileMenu />
      </div>
    </header>
  );
}
