"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronsLeft, ChevronsRight } from "lucide-react";

import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/layouts/nav-items";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";

// Left Sidebar — Layout System element. Collapses to an icon rail (persisted
// in localStorage) so it stays usable across the Laptop device class, per
// 85_Frontend_Architecture.md's Responsive Design requirement.
const COLLAPSED_KEY = "cerebrum.sidebar_collapsed";

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = React.useState(false);

  React.useEffect(() => {
    setCollapsed(window.localStorage.getItem(COLLAPSED_KEY) === "1");
  }, []);

  const toggle = () => {
    setCollapsed((prev) => {
      const next = !prev;
      window.localStorage.setItem(COLLAPSED_KEY, next ? "1" : "0");
      return next;
    });
  };

  return (
    <TooltipProvider delayDuration={200}>
      <aside
        className={cn(
          "hidden shrink-0 flex-col border-r border-border bg-background-subtle transition-all duration-default md:flex",
          collapsed ? "w-16" : "w-60",
        )}
      >
        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
          {NAV_ITEMS.map((item) => {
            const active =
              pathname === item.href || pathname?.startsWith(`${item.href}/`);
            const link = (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-fast",
                  "hover:bg-accent hover:text-accent-foreground",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-foreground-muted",
                  collapsed && "justify-center px-0",
                )}
              >
                <item.icon className="h-icon-md w-icon-md shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            );
            if (!collapsed) return link;
            return (
              <Tooltip key={item.href}>
                <TooltipTrigger asChild>{link}</TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            );
          })}
        </nav>
        <button
          type="button"
          onClick={toggle}
          className="flex items-center justify-center gap-2 border-t border-border p-3 text-foreground-muted transition-colors duration-fast hover:text-foreground"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronsRight className="h-icon-sm w-icon-sm" />
          ) : (
            <ChevronsLeft className="h-icon-sm w-icon-sm" />
          )}
        </button>
      </aside>
    </TooltipProvider>
  );
}
