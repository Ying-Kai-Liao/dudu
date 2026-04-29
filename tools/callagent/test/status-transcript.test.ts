import { describe, it, expect, vi, beforeEach } from "vitest";
import { statusCommand } from "../src/commands/status.js";
import { transcriptCommand } from "../src/commands/transcript.js";

beforeEach(() => {
  process.env.VAPI_API_KEY = "test";
  vi.restoreAllMocks();
});

describe("statusCommand", () => {
  it("prints JSON with the call status fields", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        id: "abc", status: "ended", customer: { number: "+1" },
        artifact: { transcript: "T" }, analysis: { structuredData: {} },
        endedReason: "hangup",
      }), { status: 200 }),
    );
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    await statusCommand("abc");
    const printed = JSON.parse(log.mock.calls[0][0] as string);
    expect(printed.call_id).toBe("abc");
    expect(printed.status).toBe("ended");
  });
});

describe("transcriptCommand", () => {
  it("prints only the transcript", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        id: "abc", status: "ended", customer: { number: "+1" },
        artifact: { transcript: "AI: Hello\nUser: Hi" },
      }), { status: 200 }),
    );
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    await transcriptCommand("abc");
    expect(log.mock.calls[0][0]).toBe("AI: Hello\nUser: Hi");
  });
});
