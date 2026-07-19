import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function sseStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let i = 0;
  return new ReadableStream({
    pull(controller) {
      if (i < chunks.length) {
        controller.enqueue(encoder.encode(chunks[i]));
        i += 1;
      } else {
        controller.close();
      }
    },
  });
}

async function freshAi() {
  vi.resetModules();
  return import("@/lib/api/ai");
}

describe("streamSse", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses complete data frames delivered in a single chunk", async () => {
    const ai = await freshAi();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      new Response(
        sseStream([
          'data: {"type":"progress","stage":"retrieving"}\n\n',
          'data: {"type":"token","token":"Hel"}\n\n',
          'data: {"type":"token","token":"lo"}\n\n',
        ]),
        { status: 200 },
      ),
    );

    const events = [];
    for await (const event of ai.streamSse("/ai/ask/stream", {
      question: "hi",
    })) {
      events.push(event);
    }

    expect(events).toEqual([
      { type: "progress", stage: "retrieving" },
      { type: "token", token: "Hel" },
      { type: "token", token: "lo" },
    ]);
  });

  it("reassembles a data frame split across multiple stream chunks", async () => {
    const ai = await freshAi();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    // The `data: {...}\n\n` frame is deliberately split mid-JSON, the
    // way a real TCP/HTTP chunk boundary would — the parser's buffer
    // must reassemble it before parsing, not JSON.parse a half payload.
    fetchMock.mockResolvedValueOnce(
      new Response(
        sseStream(['data: {"type":"token",', '"token":"world"}\n\n']),
        { status: 200 },
      ),
    );

    const events = [];
    for await (const event of ai.streamSse("/ai/ask/stream", {
      question: "hi",
    })) {
      events.push(event);
    }

    expect(events).toEqual([{ type: "token", token: "world" }]);
  });

  it("throws when the response is not ok", async () => {
    const ai = await freshAi();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 500 }));

    const iterate = async () => {
      // Advancing the generator once is enough to trigger the throw.
      await ai.streamSse("/ai/ask/stream", { question: "hi" }).next();
    };

    await expect(iterate()).rejects.toThrow();
  });
});
