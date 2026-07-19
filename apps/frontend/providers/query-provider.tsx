"use client";

import * as React from "react";
import {
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
        // Only surfaces a toast for a *first-load* failure (no cached
        // data to fall back on) — a background refetch failing while
        // stale data is still on screen (e.g. the 5s sync-history/
        // workflow-run polling) stays silent rather than spamming a
        // toast on every transient blip.
        queryCache: new QueryCache({
          onError: (error, query) => {
            if (query.state.data !== undefined) return;
            toast.error(
              error instanceof ApiError
                ? error.message
                : "Failed to load data.",
            );
          },
        }),
      }),
  );

  return (
    <QueryClientProvider client={client}>
      {children}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
