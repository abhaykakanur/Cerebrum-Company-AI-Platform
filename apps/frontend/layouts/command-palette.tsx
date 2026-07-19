"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { NAV_ITEMS } from "@/layouts/nav-items";
import { autocomplete } from "@/lib/api/semantic";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

// Command Palette — Layout System element backing 90_Search_Experience.md's
// Ctrl+K global entry point. Navigation commands are always shown; typed
// text also debounces against `GET /search/autocomplete` for real
// suggestions, each of which jumps to the full Enterprise Search page
// (results themselves render there, not inline, since the palette has no
// room for citations/confidence/filters).
export function CommandPalette() {
  const [open, setOpen] = React.useState(false);
  const [value, setValue] = React.useState("");
  const [suggestions, setSuggestions] = React.useState<string[]>([]);
  const router = useRouter();

  React.useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  React.useEffect(() => {
    const query = value.trim();
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }
    const timeout = setTimeout(() => {
      autocomplete(query)
        .then(setSuggestions)
        .catch(() => setSuggestions([]));
    }, 200);
    return () => clearTimeout(timeout);
  }, [value]);

  const go = (href: string) => {
    setOpen(false);
    setValue("");
    router.push(href);
  };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput
        placeholder="Jump to, or search your knowledge..."
        value={value}
        onValueChange={setValue}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        {value.trim() && (
          <CommandGroup heading="Search">
            <CommandItem
              onSelect={() =>
                go(`/search?q=${encodeURIComponent(value.trim())}`)
              }
            >
              <Search className="h-icon-sm w-icon-sm" />
              Search for &ldquo;{value.trim()}&rdquo;
            </CommandItem>
            {suggestions.map((suggestion) => (
              <CommandItem
                key={suggestion}
                onSelect={() =>
                  go(`/search?q=${encodeURIComponent(suggestion)}`)
                }
              >
                <Search className="h-icon-sm w-icon-sm opacity-50" />
                {suggestion}
              </CommandItem>
            ))}
          </CommandGroup>
        )}
        <CommandGroup heading="Navigate">
          {NAV_ITEMS.map((item) => (
            <CommandItem key={item.href} onSelect={() => go(item.href)}>
              <item.icon className="h-icon-sm w-icon-sm" />
              {item.label}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
