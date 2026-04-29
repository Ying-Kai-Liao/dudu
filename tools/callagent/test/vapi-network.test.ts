import { describe, it, expect, vi, beforeEach } from "vitest";
import { VapiProvider } from "../src/provider/vapi.js";

const fakeSpec = {
  to: "+15551234567",
  task: { frontmatter: { disclosure_required: false }, body: "B", disclosure: null },
  schema: { type: "object" } as Record<string, unknown>,
  context: undefined,
  maxDurationSeconds: 60,
  record: true,
};

describe("VapiProvider network", () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it("placeCall POSTs to /call and returns the id", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "call-abc" }), { status: 201 }),
    );
    const p = new VapiProvider({ apiKey: "k", fromNumber: "+1" });
    const id = await p.placeCall(fakeSpec as any);
    expect(id).toBe("call-abc");
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://api.vapi.ai/call");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer k");
    expect(init.method).toBe("POST");
  });

  it("placeCall throws on non-2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("nope", { status: 401 }),
    );
    const p = new VapiProvider({ apiKey: "k", fromNumber: "+1" });
    await expect(p.placeCall(fakeSpec as any)).rejects.toThrow(/401/);
  });

  it("getCall GETs /call/:id and maps the response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        id: "call-abc",
        status: "ended",
        endedReason: "hangup",
        startedAt: "2026-04-28T15:00:00Z",
        endedAt: "2026-04-28T15:05:00Z",
        artifact: { transcript: "AI: hi", recording: { stereoUrl: "https://r/" }, messages: [] },
        analysis: { structuredData: { pain_intensity: 7 } },
        customer: { number: "+15551234567" },
      }), { status: 200 }),
    );
    const p = new VapiProvider({ apiKey: "k", fromNumber: "+1" });
    const rec = await p.getCall("call-abc");
    expect(rec.call_id).toBe("call-abc");
    expect(rec.status).toBe("ended");
    expect(rec.transcript).toBe("AI: hi");
    expect(rec.recording_url).toBe("https://r/");
    expect(rec.structured_data).toEqual({ pain_intensity: 7 });
  });

  it("pollUntilTerminal returns once status is terminal", async () => {
    let n = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
      n++;
      const status = n < 2 ? "in-progress" : "ended";
      return new Response(JSON.stringify({
        id: "call-abc",
        status,
        endedReason: status === "ended" ? "hangup" : undefined,
        artifact: status === "ended" ? { transcript: "T", recording: { stereoUrl: "u" } } : undefined,
        analysis: status === "ended" ? { structuredData: {} } : undefined,
        customer: { number: "+15551234567" },
      }), { status: 200 });
    });
    const p = new VapiProvider({ apiKey: "k", fromNumber: "+1", pollIntervalMs: 5 });
    const rec = await p.pollUntilTerminal("call-abc", 1000);
    expect(rec.status).toBe("ended");
    expect(n).toBeGreaterThanOrEqual(2);
  });
});
