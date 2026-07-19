/** Health API — mirrors apps/backend/src/cerebrum/api/health.py. Root-level
 * (not under /api/v1) and unwrapped (no SuccessResponse envelope). */

import { API_BASE_URL } from "@/lib/api/client";

export type ComponentHealthStatus =
  "healthy" | "degraded" | "unavailable" | "not_configured";

export interface ComponentStatus {
  name: string;
  status: ComponentHealthStatus;
  detail: string | null;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  build_commit: string;
  build_time: string;
  environment: string;
  uptime_seconds: number;
  timestamp: string;
  components: ComponentStatus[];
}

/** Root URL, not `/api/v1` — health.py is mounted at the app root. */
const HEALTH_BASE_URL = API_BASE_URL.replace(/\/api\/v1\/?$/, "");

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${HEALTH_BASE_URL}/health`);
  if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
  return (await response.json()) as HealthResponse;
}
