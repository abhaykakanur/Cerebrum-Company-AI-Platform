import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The client module holds auth/workspace state in module-scoped
// variables (not React state), so each test gets a fresh module
// instance via vi.resetModules() to avoid cross-test pollution —
// mirrors testing any singleton.
async function freshClient() {
  vi.resetModules();
  return import("@/lib/api/client");
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("apiRequest", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attaches the Authorization header when an access token is set", async () => {
    const client = await freshClient();
    client.setTokens({ accessToken: "token-abc", refreshToken: "refresh-abc" });
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ success: true, data: { ok: true }, pagination: null }),
    );

    await client.apiGet("/ping");

    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((options.headers as Record<string, string>).Authorization).toBe(
      "Bearer token-abc",
    );
  });

  it("omits the Authorization header for skipAuth requests", async () => {
    const client = await freshClient();
    client.setTokens({ accessToken: "token-abc", refreshToken: "refresh-abc" });
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(jsonResponse({ access_token: "x" }));

    await client.apiRequest("/auth/refresh", {
      method: "POST",
      skipAuth: true,
      body: { refresh_token: "r" },
    });

    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(
      (options.headers as Record<string, string>).Authorization,
    ).toBeUndefined();
  });

  it("attaches X-Workspace-ID when a workspace is selected, and omits it when skipWorkspace is set", async () => {
    const client = await freshClient();
    client.setCurrentWorkspaceId("ws-1");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ success: true, data: {}, pagination: null }),
    );
    await client.apiGet("/documents");
    const [, scoped] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((scoped.headers as Record<string, string>)["X-Workspace-ID"]).toBe(
      "ws-1",
    );

    fetchMock.mockResolvedValueOnce(
      jsonResponse({ success: true, data: {}, pagination: null }),
    );
    await client.apiGet("/organizations/me", { skipWorkspace: true });
    const [, unscoped] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(
      (unscoped.headers as Record<string, string>)["X-Workspace-ID"],
    ).toBeUndefined();
  });

  it("unwraps SuccessEnvelope.data for apiGet", async () => {
    const client = await freshClient();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ success: true, data: { id: "42" }, pagination: null }),
    );

    const result = await client.apiGet<{ id: string }>("/thing");

    expect(result).toEqual({ id: "42" });
  });

  it("returns both items and pagination for apiGetPage", async () => {
    const client = await freshClient();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    const pagination = {
      page: 1,
      page_size: 50,
      total_items: 2,
      total_pages: 1,
      has_next: false,
      has_previous: false,
      cursor: null,
    };
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        success: true,
        data: [{ id: "a" }, { id: "b" }],
        pagination,
      }),
    );

    const result = await client.apiGetPage<{ id: string }>("/things");

    expect(result.items).toHaveLength(2);
    expect(result.pagination).toEqual(pagination);
  });

  it("retries once after a successful token refresh on 401, then succeeds", async () => {
    const client = await freshClient();
    client.setTokens({ accessToken: "expired", refreshToken: "refresh-1" });
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;

    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({ error_code: "unauthorized", message: "expired" }, 401),
      ) // original request
      .mockResolvedValueOnce(
        jsonResponse({ access_token: "fresh", refresh_token: "refresh-2" }),
      ) // refresh call
      .mockResolvedValueOnce(
        jsonResponse({ success: true, data: { ok: true }, pagination: null }),
      ); // retried request

    const result = await client.apiGet<{ ok: boolean }>("/protected");

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(client.getAccessToken()).toBe("fresh");
  });

  it("clears tokens and invokes the unauthorized handler when refresh itself fails", async () => {
    const client = await freshClient();
    client.setTokens({ accessToken: "expired", refreshToken: "refresh-1" });
    const onUnauthorized = vi.fn();
    client.setUnauthorizedHandler(onUnauthorized);
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;

    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({ error_code: "unauthorized", message: "expired" }, 401),
      )
      .mockResolvedValueOnce(
        jsonResponse(
          { error_code: "unauthorized", message: "invalid refresh token" },
          401,
        ),
      );

    await expect(client.apiGet("/protected")).rejects.toThrow();

    expect(client.getAccessToken()).toBeNull();
    expect(onUnauthorized).toHaveBeenCalled();
  });

  it("throws ApiError with the envelope's error details on a non-401 failure", async () => {
    const client = await freshClient();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          success: false,
          error_code: "validation_error",
          message: "bad input",
          retryable: false,
        },
        422,
      ),
    );

    await expect(client.apiGet("/thing")).rejects.toMatchObject({
      status: 422,
      errorCode: "validation_error",
      message: "bad input",
    });
  });

  it("sends FormData bodies without JSON-stringifying or forcing a Content-Type", async () => {
    const client = await freshClient();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ success: true, data: {}, pagination: null }),
    );

    const form = new FormData();
    form.append("file", new Blob(["hello"]), "hello.txt");
    await client.apiSend("/documents/upload", "POST", form);

    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(options.body).toBe(form);
    expect(
      (options.headers as Record<string, string>)["Content-Type"],
    ).toBeUndefined();
  });
});
