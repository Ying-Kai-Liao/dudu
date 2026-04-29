import { describe, it, expect, vi, beforeEach } from "vitest";
import { mkdtempSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { placeCommand } from "../src/commands/place.js";

const PERSONA = resolve(__dirname, "fixtures/persona-basic.md");
const SCHEMA = resolve(__dirname, "fixtures/schema-basic.json");

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(`${tmpdir()}/callagent-place-`);
  process.env.VAPI_API_KEY = "test";
  process.env.VAPI_FROM_NUMBER = "+15550000000";
});

describe("placeCommand", () => {
  it("dry-run writes the resolved DTO to stdout, no network call", async () => {
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    await placeCommand({
      to: "+15551234567",
      persona: PERSONA,
      goal: "screener",
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

  it("rejects empty consent token with exit code 3", async () => {
    await expect(placeCommand({
      to: "+15551234567",
      persona: PERSONA,
      goal: "g",
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
      persona: PERSONA,
      goal: "g",
      schema: SCHEMA,
      consentToken: "tok-1",
      tools: toolsPath,
      maxDuration: 60,
      record: true,
      dryRun: true,
    } as any)).rejects.toMatchObject({ exitCode: 2 });
  });
});
