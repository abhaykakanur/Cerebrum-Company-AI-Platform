import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  MessageSquare,
  Search,
  Share2,
  FileText,
  Plug,
  Workflow,
  UserSquare2,
  ShieldCheck,
  Activity,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  shortcut?: string;
}

// The Sidebar's primary navigation — one entry per feature area this
// frontend implements against real backend capability (Employee
// Knowledge Capsule, Connectors, Workflows, Administration, Monitoring
// are all backed by CIS Phase 1-5.3 endpoints; nothing here is aspirational).
export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "AI Chat", href: "/chat", icon: MessageSquare },
  { label: "Search", href: "/search", icon: Search },
  { label: "Knowledge Graph", href: "/graph", icon: Share2 },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Connectors", href: "/connectors", icon: Plug },
  { label: "Workflows", href: "/workflows", icon: Workflow },
  { label: "Knowledge Capsules", href: "/capsules", icon: UserSquare2 },
  { label: "Administration", href: "/admin", icon: ShieldCheck },
  { label: "Monitoring", href: "/monitoring", icon: Activity },
];
