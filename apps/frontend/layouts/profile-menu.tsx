"use client";

import { LogOut, Moon, Sun, User } from "lucide-react";
import { useTheme } from "next-themes";

import { useAuth } from "@/providers/auth-provider";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// Profile Menu — Layout System element surfacing the User Management
// Domain (35_Domain_Architecture.md). Only exposes what CurrentUserResponse
// actually returns (email, verification status) plus sign-out — no
// fabricated profile fields (avatar image, display name) the backend
// doesn't provide.
export function ProfileMenu() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  if (!user) return null;

  const isDark = theme !== "light";

  const initials = user.email.slice(0, 2).toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex h-8 w-8 items-center justify-center rounded-full transition-opacity duration-fast hover:opacity-80"
          aria-label="Profile menu"
        >
          <Avatar className="h-8 w-8">
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span className="flex items-center gap-1.5 font-normal text-foreground-muted">
            <User className="h-icon-xs w-icon-xs" />
            Signed in as
          </span>
          <span className="truncate font-medium text-foreground">
            {user.email}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => setTheme(isDark ? "light" : "dark")}>
          {isDark ? (
            <Sun className="h-icon-sm w-icon-sm" />
          ) : (
            <Moon className="h-icon-sm w-icon-sm" />
          )}
          {isDark ? "Light mode" : "Dark mode"}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem destructive onSelect={() => void logout()}>
          <LogOut className="h-icon-sm w-icon-sm" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
