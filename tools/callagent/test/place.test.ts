import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mkdtempSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { placeCommand } from "../src/commands/place.js";

const TASK = resolve(__dirname, "fixtures/task-basic.md");
const SCHEMA = resolve(__dirname, "fixtures/schema-basic.json");

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(`${tmpdir()}/callagent-place-`);
  process.env.VAPI_API_KEY = "test";
  process.env.VAPI_PHONE_NUMBER_ID = "vapi-phone-uuid-test";
  // Tests use the +1555… fake range; widen the privacy allowlist for the suite.
  process.env.CALLAGENT_ALLOWED_NUMBERS = "+15551234567";
});

afterEach(() => {
  vi.restoreAllMocks();
  delete process.env.VAPI_API_KEY;
  delete process.env.VAPI_PHONE_NUMBER_ID;
  delete process.env.CALLAGENT_ALLOWED_NUMBERS;
});

describe("placeCommand", () => {
  it("dry-run writes the resolved DTO to stdout, no network call", async () => {
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    await placeCommand({
      to: "+15551234567",
      task: TASK,
      schema: SCHEMA,
      consentToken: "tok-1",
      maxDuration: 60,
      record: true,
      dryRun: true,
    } as any);
    expect(fetchSpy).not.toHaveBeenCalled();
    const printed = log.mock.calls.map((c) => c[0]).join("\n");
    expect(printed).toContain("structuredDataSchema");
    expect(printed).toContain("+15551234567");
  });

  it("rejects --to that is not on the privacy allowlist with exit code 2", async () => {
    delete process.env.CALLAGENT_ALLOWED_NUMBERS;
    await expect(placeCommand({
      to: "+15551234567",
      task: TASK,
      schema: SCHEMA,
      // Valid consent token — this proves the allowlist gate fires first.
      consentToken: "tok-1",
      maxDuration: 60,
      record: true,
      dryRun: true,
    } as any)).rejects.toMatchObject({
      exitCode: 2,
      message: expect.stringContaining("not in the callagent allowlist"),
    });
  });

  it("accepts a default-allowlisted number without env override", async () => {
    delete process.env.CALLAGENT_ALLOWED_NUMBERS;
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    await placeCommand({
      to: "+61423366127",
      task: TASK,
      consentToken: "tok-1",
      maxDuration: 60,
      record: true,
      dryRun: true,
    } as any);
    const printed = log.mock.calls.map((c) => c[0]).join("\n");
    expect(printed).toContain("+61423366127");
  });

  it("rejects empty consent token with exit code 3", async () => {
    await expect(placeCommand({
      to: "+15551234567",
      task: TASK,
      schema: SCHEMA,
      consentToken: "",
      maxDuration: 60,
      record: true,
      dryRun: true,
    } as any)).rejects.toMatchObject({ exitCode: 3 });
  });

  it("rejects --tools (v1)", async () => {
    const toolsPath = `${tmp}/tools.json`;
    writeFileSync(toolsPath, JSON.stringify([{ type: "function", function: { name: "x" } }]));
    await expect(placeCommand({
      to: "+15551234567",
      task: TASK,
      schema: SCHEMA,
      consentToken: "tok-1",
      tools: toolsPath,
      maxDuration: 60,
      record: true,
      dryRun: true,
    } as any)).rejects.toMatchObject({ exitCode: 2 });
  });

  it("place succeeds without --schema (dry-run)", async () => {
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    await placeCommand({
      to: "+15551234567",
      task: TASK,
      consentToken: "tok-1",
      maxDuration: 60,
      record: true,
      dryRun: true,
    } as any);
    expect(fetchSpy).not.toHaveBeenCalled();
    const printed = log.mock.calls.map((c) => c[0]).join("\n");
    const dto = JSON.parse(printed);
    expect(dto.assistant.analysisPlan).toBeUndefined();
    expect(dto.customer.number).toBe("+15551234567");
  });

  it("throws with exitCode 4 when call status is failed", async () => {
    const failedCallResponse = {
      id: "call-failed-123",
      status: "failed",
      endedReason: "no-answer",
      startedAt: undefined,
      endedAt: undefined,
      artifact: { transcript: "", stereoRecordingUrl: undefined, messages: [] },
      analysis: { structuredData: null },
      customer: { number: "+15551234567" },
    };

    let callCount = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url: any) => {
      callCount++;
      if (callCount === 1) {
        // placeCall POST
        return new Response(JSON.stringify({ id: "call-failed-123" }), { status: 201 });
      }
      // pollUntilTerminal GET
      return new Response(JSON.stringify(failedCallResponse), { status: 200 });
    });

    // Suppress the banner sleep
    vi.spyOn(await import("../src/consent.js"), "emitBannerAndSleep").mockResolvedValue();

    const outputPath = `${tmp}/failed-call.json`;
    await expect(
      placeCommand({
        to: "+15551234567",
        task: TASK,
        consentToken: "tok-failed",
        maxDuration: 60,
        record: false,
        dryRun: false,
        output: outputPath,
      } as any),
    ).rejects.toMatchObject({ exitCode: 4 });

    // The result file should still have been written
    expect(existsSync(outputPath)).toBe(true);
    const result = JSON.parse(readFileSync(outputPath, "utf8"));
    expect(result.status).toBe("failed");
  });
});
