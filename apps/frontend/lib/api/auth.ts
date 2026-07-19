/**
 * Auth API — mirrors apps/backend/src/cerebrum/api/v1/auth.py exactly.
 * `login` alone bypasses {@link apiRequest} because the backend's OAuth2
 * Password Flow route expects `application/x-www-form-urlencoded`, not
 * JSON, and every route in this module returns an unwrapped shape (not
 * {@link SuccessEnvelope}) — see that backend module's own docstring.
 */

import { API_BASE_URL, apiRequest, ApiError } from "@/lib/api/client";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface CurrentUser {
  id: string;
  email: string;
  organization_id: string;
  is_active: boolean;
  is_verified: boolean;
}

export async function login(
  email: string,
  password: string,
): Promise<TokenPair> {
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = payload as { message?: string; error_code?: string } | null;
    throw new ApiError(
      error?.message ?? "Login failed.",
      response.status,
      error?.error_code ?? "login_failed",
      null,
      false,
    );
  }
  return payload as TokenPair;
}

export async function refreshTokens(refreshToken: string): Promise<TokenPair> {
  return apiRequest<TokenPair>("/auth/refresh", {
    method: "POST",
    body: { refresh_token: refreshToken },
    skipAuth: true,
    skipWorkspace: true,
  });
}

export async function logout(refreshToken: string): Promise<void> {
  await apiRequest<void>("/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
    skipWorkspace: true,
  });
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/auth/me", { skipWorkspace: true });
}
