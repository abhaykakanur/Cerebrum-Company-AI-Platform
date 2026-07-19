"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search as SearchIcon } from "lucide-react";

import { Input } from "@/components/ui/input";
import { SearchFiltersBar } from "@/features/search/search-filters";
import { SearchResults } from "@/features/search/search-results";
import { RecentSavedSearches } from "@/features/search/recent-saved-searches";
import {
  useRecentSearches,
  useSearchResults,
  type SearchFilters,
} from "@/services/search";

const DEFAULT_FILTERS: SearchFilters = {
  strategy: "hybrid",
  kinds: [],
  tags: [],
};

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";

  const [query, setQuery] = React.useState(initialQuery);
  const [submittedQuery, setSubmittedQuery] = React.useState(initialQuery);
  const [filters, setFilters] = React.useState<SearchFilters>(DEFAULT_FILTERS);
  const { record } = useRecentSearches();

  const { data, isLoading } = useSearchResults(submittedQuery, filters);

  React.useEffect(() => {
    const urlQuery = searchParams.get("q") ?? "";
    if (urlQuery && urlQuery !== submittedQuery) {
      setQuery(urlQuery);
      setSubmittedQuery(urlQuery);
      record(urlQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const runSearch = (
    nextQuery: string,
    nextFilters: SearchFilters = filters,
  ) => {
    setQuery(nextQuery);
    setSubmittedQuery(nextQuery);
    setFilters(nextFilters);
    if (nextQuery.trim()) {
      record(nextQuery.trim());
      router.replace(`/search?q=${encodeURIComponent(nextQuery.trim())}`);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_280px]">
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-h1 font-semibold">Enterprise Search</h1>
          <p className="text-sm text-foreground-muted">
            Hybrid, semantic, keyword, and graph search across your
            workspace&apos;s knowledge.
          </p>
        </div>
        <div className="relative">
          <SearchIcon className="absolute left-3 top-3 h-icon-sm w-icon-sm text-foreground-muted" />
          <Input
            autoFocus
            className="h-11 pl-10 text-base"
            placeholder="Search documents, entities, and chunks..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") runSearch(query);
            }}
          />
        </div>
        <SearchFiltersBar
          filters={filters}
          onChange={(next) => runSearch(submittedQuery, next)}
        />
        <SearchResults
          hits={data?.hits ?? []}
          ranked={data?.ranked ?? null}
          isLoading={isLoading}
          hasQuery={submittedQuery.trim().length > 0}
        />
      </div>
      <RecentSavedSearches
        currentQuery={submittedQuery}
        currentFilters={filters}
        onSelect={runSearch}
      />
    </div>
  );
}
