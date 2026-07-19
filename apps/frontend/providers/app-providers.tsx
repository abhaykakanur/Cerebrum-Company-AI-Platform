"use client";

import * as React from "react";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/providers/auth-provider";
import { QueryProvider } from "@/providers/query-provider";
import { ThemeProvider } from "@/providers/theme-provider";

/** The single composition root for every cross-cutting React context
 * this app needs — kept as one component so app/layout.tsx stays a
 * plain server component apart from this one client boundary. */
export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <QueryProvider>
        <TooltipProvider delayDuration={200}>
          <AuthProvider>
            {children}
            <Toaster position="bottom-right" richColors closeButton />
          </AuthProvider>
        </TooltipProvider>
      </QueryProvider>
    </ThemeProvider>
  );
}
