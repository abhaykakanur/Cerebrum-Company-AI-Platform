"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import {
  getCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  type CurrentUser,
} from "@/lib/api/auth";
import {
  getAccessToken,
  getCurrentWorkspaceId,
  getRefreshToken,
  setCurrentWorkspaceId,
  setTokens,
  setUnauthorizedHandler,
} from "@/lib/api/client";
import { listWorkspaces, type Workspace } from "@/lib/api/workspaces";

interface AuthContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  selectWorkspace: (workspaceId: string) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshWorkspaces: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

/** Session bootstrap, workspace selection, and the 401-triggered
 * redirect-to-login path — the one place this app manages
 * authentication state, per the Thin Frontend rule (every permission/
 * identity decision itself still happens server-side; this only tracks
 * "are we logged in, and as whom"). */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = React.useState<CurrentUser | null>(null);
  const [workspaces, setWorkspaces] = React.useState<Workspace[]>([]);
  const [currentWorkspaceId, setCurrentWorkspaceIdState] = React.useState<
    string | null
  >(null);
  const [isLoading, setIsLoading] = React.useState(true);

  const loadWorkspaces = React.useCallback(async (): Promise<Workspace[]> => {
    const list = await listWorkspaces();
    setWorkspaces(list);
    const stored = getCurrentWorkspaceId();
    const selected =
      list.find((workspace) => workspace.id === stored) ?? list[0] ?? null;
    if (selected) {
      setCurrentWorkspaceId(selected.id);
      setCurrentWorkspaceIdState(selected.id);
    }
    return list;
  }, []);

  const bootstrap = React.useCallback(async () => {
    if (!getAccessToken()) {
      setIsLoading(false);
      return;
    }
    try {
      const me = await getCurrentUser();
      setUser(me);
      await loadWorkspaces();
    } catch {
      setTokens(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [loadWorkspaces]);

  React.useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setWorkspaces([]);
      router.push("/login");
    });
    void bootstrap();
    return () => setUnauthorizedHandler(null);
  }, [bootstrap, router]);

  const login = React.useCallback(
    async (email: string, password: string) => {
      const tokens = await apiLogin(email, password);
      setTokens({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      });
      const me = await getCurrentUser();
      setUser(me);
      await loadWorkspaces();
    },
    [loadWorkspaces],
  );

  const logout = React.useCallback(async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await apiLogout(refreshToken);
      } catch {
        // Best-effort server-side revoke — local session state is
        // cleared regardless, since the access token still expires
        // (900s) even if this call fails.
      }
    }
    setTokens(null);
    setCurrentWorkspaceId(null);
    setUser(null);
    setWorkspaces([]);
    setCurrentWorkspaceIdState(null);
    router.push("/login");
  }, [router]);

  const selectWorkspace = React.useCallback((workspaceId: string) => {
    setCurrentWorkspaceId(workspaceId);
    setCurrentWorkspaceIdState(workspaceId);
  }, []);

  const currentWorkspace =
    workspaces.find((workspace) => workspace.id === currentWorkspaceId) ?? null;

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      workspaces,
      currentWorkspace,
      selectWorkspace,
      login,
      logout,
      refreshWorkspaces: async () => {
        await loadWorkspaces();
      },
    }),
    [
      user,
      isLoading,
      workspaces,
      currentWorkspace,
      selectWorkspace,
      login,
      logout,
      loadWorkspaces,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
