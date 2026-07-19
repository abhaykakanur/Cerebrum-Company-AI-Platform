"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/providers/auth-provider";
import { TopNav } from "@/layouts/top-nav";
import { Sidebar } from "@/layouts/sidebar";
import { RouteBreadcrumbs } from "@/layouts/route-breadcrumbs";
import { CommandPalette } from "@/layouts/command-palette";
import { ContextDrawerProvider } from "@/layouts/context-drawer";
import { Skeleton } from "@/components/ui/skeleton";

// The authenticated application shell — assembles all ten Layout System
// elements (85_Frontend_Architecture.md) around every `(app)` route.
// Redirects to /login when the session isn't authenticated, since every
// page under this shell assumes CurrentUserDep succeeded server-side too.
export function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, workspaces } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Skeleton className="h-8 w-40" />
      </div>
    );
  }

  if (workspaces.length === 0) {
    router.replace("/workspaces/new");
    return null;
  }

  return (
    <ContextDrawerProvider>
      <div className="flex h-screen flex-col">
        <TopNav />
        <div className="flex min-h-0 flex-1">
          <Sidebar />
          <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
            <div className="border-b border-border px-6 py-3">
              <RouteBreadcrumbs />
            </div>
            <div className="flex-1 p-6">{children}</div>
          </main>
        </div>
        <CommandPalette />
      </div>
    </ContextDrawerProvider>
  );
}
