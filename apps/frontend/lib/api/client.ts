/**
 * The typed HTTP client every `lib/api/*` module and `services/*` hook
 * calls through — the Thin Frontend's one boundary with the backend
 * (docs/architecture/specification/85_Frontend_Architecture.md). No
 * component fetches directly; every request goes through
 * {@link apiRequest} so auth headers, workspace scoping, the response
 * envelope, and 401 refresh-and-retry are handled in exactly one place.
 *
 * Matches the backend's exact envelope
 * (apps/backend/src/cerebrum/api/schemas/envelope.py) — every endpoint
 * except `cerebrum.api.v1.auth` (OAuth2 Password Flow convention) and
 * `cerebrum.api.health` (orchestrator convention) returns
 * {@link SuccessEnvelope}/throws as {@link ErrorEnvelope}.
 */

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  cursor: string | null;
}

export interface SuccessEnvelope<T> {
  success: true;
  message: string | null;
  data: T;
  metadata: Record<string, unknown> | null;
  pagination: PaginationMeta | null;
  timestamp: string;
  request_id: string;
  correlation_id: string | null;
  version: string;
}

export interface ErrorDetail {
  field: string | null;
  message: string;
}

export interface ErrorEnvelope {
  success: false;
  error_code: string;
  message: string;
  details: ErrorDetail[] | null;
  documentation_url: string | null;
  retryable: boolean;
  timestamp: string;
  request_id: string;
  correlation_id: string | null;
  version: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly errorCode: string,
    public readonly details: ErrorDetail[] | null,
    public readonly retryable: boolean,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const ACCESS_TOKEN_KEY = "cerebrum.access_token";
const REFRESH_TOKEN_KEY = "cerebrum.refresh_token";
const WORKSPACE_ID_KEY = "cerebrum.workspace_id";

let accessToken: string | null = null;
let refreshToken: string | null = null;
let currentWorkspaceId: string | null = null;
let onUnauthorized: (() => void) | null = null;

if (typeof window !== "undefined") {
  accessToken = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);
  currentWorkspaceId = window.localStorage.getItem(WORKSPACE_ID_KEY);
}

export function setTokens(
  tokens: { accessToken: string; refreshToken: string } | null,
): void {
  accessToken = tokens?.accessToken ?? null;
  refreshToken = tokens?.refreshToken ?? null;
  if (typeof window === "undefined") return;
  if (tokens) {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  } else {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return refreshToken;
}

export function setCurrentWorkspaceId(workspaceId: string | null): void {
  currentWorkspaceId = workspaceId;
  if (typeof window === "undefined") return;
  if (workspaceId) window.localStorage.setItem(WORKSPACE_ID_KEY, workspaceId);
  else window.localStorage.removeItem(WORKSPACE_ID_KEY);
}

export function getCurrentWorkspaceId(): string | null {
  return currentWorkspaceId;
}

/** Called once by `AuthProvider` — invoked when a request 401s and the
 * refresh attempt itself also fails, so the app can redirect to login. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) return false;
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;
      const payload = (await response.json()) as {
        access_token: string;
        refresh_token: string;
      };
      setTokens({
        accessToken: payload.access_token,
        refreshToken: payload.refresh_token,
      });
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  /** Skips the Authorization header — for the unauthenticated login call. */
  skipAuth?: boolean;
  /** Skips the X-Workspace-ID header — for org-level, not workspace-scoped, endpoints. */
  skipWorkspace?: boolean;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: ApiRequestOptions["query"]): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

/** Raw request — returns the parsed JSON body as-is (caller decides
 * whether that's a {@link SuccessEnvelope} or an unwrapped auth shape). */
export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const url = buildUrl(path, options.query);

  const doFetch = async (): Promise<Response> => {
    const isFormData = options.body instanceof FormData;
    const headers: Record<string, string> = isFormData
      ? {}
      : { "Content-Type": "application/json" };
    if (!options.skipAuth && accessToken)
      headers.Authorization = `Bearer ${accessToken}`;
    if (!options.skipWorkspace && currentWorkspaceId)
      headers["X-Workspace-ID"] = currentWorkspaceId;
    return fetch(url, {
      method: options.method ?? "GET",
      headers,
      body: isFormData
        ? (options.body as FormData)
        : options.body !== undefined
          ? JSON.stringify(options.body)
          : undefined,
      signal: options.signal,
    });
  };

  let response = await doFetch();

  if (response.status === 401 && !options.skipAuth && refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      response = await doFetch();
    } else {
      setTokens(null);
      onUnauthorized?.();
    }
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401) onUnauthorized?.();
    const error = payload as ErrorEnvelope | null;
    throw new ApiError(
      error?.message ?? response.statusText,
      response.status,
      error?.error_code ?? "unknown_error",
      error?.details ?? null,
      error?.retryable ?? false,
    );
  }

  return payload as T;
}

/** The common case: an endpoint wrapped in {@link SuccessEnvelope} —
 * returns just `.data`. */
export async function apiGet<T>(
  path: string,
  options: Omit<ApiRequestOptions, "method"> = {},
): Promise<T> {
  const envelope = await apiRequest<SuccessEnvelope<T>>(path, {
    ...options,
    method: "GET",
  });
  return envelope.data;
}

export async function apiSend<T>(
  path: string,
  method: "POST" | "PATCH" | "PUT" | "DELETE",
  body?: unknown,
  options: Omit<ApiRequestOptions, "method" | "body"> = {},
): Promise<T> {
  const envelope = await apiRequest<SuccessEnvelope<T>>(path, {
    ...options,
    method,
    body,
  });
  return envelope.data;
}

/** For collection endpoints — returns both the items and pagination
 * metadata, since list pages render both. */
export async function apiGetPage<T>(
  path: string,
  options: Omit<ApiRequestOptions, "method"> = {},
): Promise<{ items: T[]; pagination: PaginationMeta | null }> {
  const envelope = await apiRequest<SuccessEnvelope<T[]>>(path, {
    ...options,
    method: "GET",
  });
  return { items: envelope.data, pagination: envelope.pagination };
}
