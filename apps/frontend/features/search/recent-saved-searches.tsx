"use client";

import * as React from "react";
import { Bookmark, Clock, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useRecentSearches,
  useSavedSearches,
  type SearchFilters,
} from "@/services/search";

export function RecentSavedSearches({
  currentQuery,
  currentFilters,
  onSelect,
}: {
  currentQuery: string;
  currentFilters: SearchFilters;
  onSelect: (query: string, filters: SearchFilters) => void;
}) {
  const { recent } = useRecentSearches();
  const { saved, save, remove } = useSavedSearches();
  const [saveOpen, setSaveOpen] = React.useState(false);
  const [name, setName] = React.useState("");

  const handleSave = () => {
    if (!name.trim() || !currentQuery.trim()) return;
    save({ name: name.trim(), query: currentQuery, filters: currentFilters });
    setSaveOpen(false);
    setName("");
  };

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="flex items-center gap-1.5 text-sm">
            <Bookmark className="h-icon-sm w-icon-sm" />
            Saved searches
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            disabled={!currentQuery.trim()}
            onClick={() => setSaveOpen(true)}
          >
            Save current
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-1">
          {saved.length === 0 && (
            <p className="text-xs text-foreground-muted">
              No saved searches yet.
            </p>
          )}
          {saved.map((s) => (
            <div
              key={s.name}
              className="flex items-center justify-between gap-2"
            >
              <button
                type="button"
                className="min-w-0 flex-1 truncate text-left text-sm hover:underline"
                onClick={() => onSelect(s.query, s.filters)}
              >
                {s.name}
              </button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => remove(s.name)}
              >
                <Trash2 className="h-icon-xs w-icon-xs" />
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5 text-sm">
            <Clock className="h-icon-sm w-icon-sm" />
            Recent searches
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-1">
          {recent.length === 0 && (
            <p className="text-xs text-foreground-muted">No recent searches.</p>
          )}
          {recent.map((query) => (
            <button
              key={query}
              type="button"
              className="truncate text-left text-sm hover:underline"
              onClick={() => onSelect(query, currentFilters)}
            >
              {query}
            </button>
          ))}
        </CardContent>
      </Card>

      <Dialog open={saveOpen} onOpenChange={setSaveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save search</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor="search-name">Name</Label>
            <Input
              id="search-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button onClick={handleSave} disabled={!name.trim()}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
