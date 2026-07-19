import type { BadgeProps } from "@/components/ui/badge";

/** Maps the many backend status/health enums (connector status, workflow
 * status, sync run status, processing job status, health component
 * status) onto the Design System's five Badge variants. Every backend
 * enum value seen across the API is covered; unrecognized values fall
 * back to "outline" rather than guessing a color. */
const STATUS_VARIANT_MAP: Record<string, NonNullable<BadgeProps["variant"]>> = {
  active: "success",
  healthy: "success",
  completed: "success",
  ready: "success",
  clean: "success",
  alive: "success",
  succeeded: "success",

  degraded: "warning",
  paused: "warning",
  pending: "warning",
  running: "info",
  draft: "outline",
  quarantined: "danger",

  error: "danger",
  failed: "danger",
  unhealthy: "danger",
  unavailable: "danger",
  cancelled: "outline",
  archived: "outline",
  disabled: "outline",
  not_configured: "outline",
};

export function statusVariant(
  status: string,
): NonNullable<BadgeProps["variant"]> {
  return STATUS_VARIANT_MAP[status.toLowerCase()] ?? "outline";
}

export function formatStatusLabel(status: string): string {
  return status
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
