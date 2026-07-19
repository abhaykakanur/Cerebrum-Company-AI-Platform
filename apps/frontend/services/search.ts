"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";

import {
  hybridSearch,
  semanticSearch,
  type SearchHit,
} from "@/lib/api/semantic";
import {
  retrieve,
  type RankedResult,
  type RetrievalStrategy,
} from "@/lib/api/retrieval";

export interface SearchFilters {
  strategy: RetrievalStrategy;
  kinds: string[];
  tags: string[];
}

export function useSearchResults(query: string, filters: SearchFilters) {
  return useQuery({
    queryKey: ["search", query, filters],
    queryFn: async (): Promise<{
      hits: SearchHit[];
      ranked: RankedResult[] | null;
    }> => {
      if (filters.strategy === "semantic") {
        return {
          hits: await semanticSearch(query, filters.kinds),
          ranked: null,
        };
      }
      if (filters.strategy === "hybrid") {
        return {
          hits: await hybridSearch(query, {
            kinds: filters.kinds,
            tags: filters.tags,
          }),
          ranked: null,
        };
      }
      // graph/keyword/metadata strategies only exist via /retrieval/retrieve,
      // which returns ranked results with explainable per-factor scoring.
      const ranked = await retrieve(query, { strategy: filters.strategy });
      return { hits: ranked.map((r) => r.hit), ranked };
    },
    enabled: query.trim().length > 0,
  });
}

/** Recent + saved searches are local-only — 90_Search_Experience.md maps
 * Recent to the Search Session entity and Saved to a "new UI-facing
 * capability... Deferred to Architecture," and neither has a persistence
 * endpoint in the implemented backend. Scoped honestly per-browser. */
const RECENT_KEY = "cerebrum.recent_searches";
const SAVED_KEY = "cerebrum.saved_searches";
const MAX_RECENT = 10;

export interface SavedSearch {
  name: string;
  query: string;
  filters: SearchFilters;
}

function readList<T>(key: string): T[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(key);
  return raw ? (JSON.parse(raw) as T[]) : [];
}

export function useRecentSearches() {
  const [recent, setRecent] = React.useState<string[]>([]);

  React.useEffect(() => setRecent(readList<string>(RECENT_KEY)), []);

  const record = React.useCallback((query: string) => {
    setRecent((prev) => {
      const next = [query, ...prev.filter((q) => q !== query)].slice(
        0,
        MAX_RECENT,
      );
      window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  return { recent, record };
}

export function useSavedSearches() {
  const [saved, setSaved] = React.useState<SavedSearch[]>([]);

  React.useEffect(() => setSaved(readList<SavedSearch>(SAVED_KEY)), []);

  const save = React.useCallback((entry: SavedSearch) => {
    setSaved((prev) => {
      const next = [entry, ...prev.filter((s) => s.name !== entry.name)];
      window.localStorage.setItem(SAVED_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const remove = React.useCallback((name: string) => {
    setSaved((prev) => {
      const next = prev.filter((s) => s.name !== name);
      window.localStorage.setItem(SAVED_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  return { saved, save, remove };
}
