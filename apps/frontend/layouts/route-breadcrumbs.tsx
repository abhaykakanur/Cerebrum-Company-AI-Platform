"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/providers/auth-provider";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { NAV_ITEMS } from "@/layouts/nav-items";

function titleCase(segment: string): string {
  return segment
    .replace(/-/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

// Breadcrumbs — Layout System element reflecting 43_Canonical_Data_Model.md's
// resource hierarchy: Organization -> Workspace -> resource. The first two
// levels come from the active session (org name isn't in the JWT, so the
// workspace is the practical root); everything after is derived from the
// route path, with the first segment resolved against the known nav labels.
export function RouteBreadcrumbs() {
  const pathname = usePathname();
  const { currentWorkspace } = useAuth();
  const segments = (pathname ?? "").split("/").filter(Boolean);

  if (segments.length === 0) return null;

  return (
    <Breadcrumb>
      <BreadcrumbList>
        {currentWorkspace && (
          <>
            <BreadcrumbItem>
              <span className="text-foreground-muted">
                {currentWorkspace.name}
              </span>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
          </>
        )}
        {segments.map((segment, index) => {
          const href = `/${segments.slice(0, index + 1).join("/")}`;
          const isLast = index === segments.length - 1;
          const navLabel = NAV_ITEMS.find((item) => item.href === href)?.label;
          const label = navLabel ?? titleCase(segment);
          return (
            <React.Fragment key={href}>
              <BreadcrumbItem>
                {isLast ? (
                  <BreadcrumbPage>{label}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    <Link href={href}>{label}</Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
              {!isLast && <BreadcrumbSeparator />}
            </React.Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
