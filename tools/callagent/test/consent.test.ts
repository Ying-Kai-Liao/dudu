import { describe, it, expect, beforeEach } from "vitest";
import { mkdtempSync, readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import {
  validateConsentToken,
  appendAuditLog,
  resolveAuditLogPath,
  ConsentError,
} from "../src/consent.js";

let tmp: string;
beforeEach(() => { tmp = mkdtempSync(`${tmpdir()}/callagent-`); });

describe("validateConsentToken", () => {
  it("accepts a non-empty string", () => {
    expect(() => validateConsentToken("abc-123")).not.toThrow();
  });
  it("rejects empty string with exit code 3", () => {
    try { validateConsentToken(""); }
    catch (e: any) {
      expect(e).toBeInstanceOf(ConsentError);
      expect(e.exitCode).toBe(3);
      return;
    }
    throw new Error("expected ConsentError");
  });
  it("rejects whitespace-only string", () => {
    expect(() => validateConsentToken("   ")).toThrow(ConsentError);
  });
});

describe("resolveAuditLogPath", () => {
  it("uses CALLAGENT_AUDIT_LOG env var when set", () => {
    const p = resolveAuditLogPath({ env: "/tmp/x.jsonl", outputPath: undefined });
    expect(p).toBe("/tmp/x.jsonl");
  });
  it("uses output dir + consent-log.jsonl when output is set and env is not", () => {
    const p = resolveAuditLogPath({ env: undefined, outputPath: "/foo/bar/run.json" });
    expect(p).toBe("/foo/bar/consent-log.jsonl");
  });
  it("falls back to ./consent-log.jsonl when neither is set", () => {
    const p = resolveAuditLogPath({ env: undefined, outputPath: undefined });
    expect(p).toBe(resolve(process.cwd(), "consent-log.jsonl"));
  });
});

describe("appendAuditLog", () => {
  it("appends a JSONL entry with the expected fields", async () => {
    const path = `${tmp}/audit.jsonl`;
    await appendAuditLog(path, {
      consent_token: "tok-1",
      to: "+15551234567",
      task_path: "tasks/my-task.md",
      placed_at: "2026-04-28T15:00:00Z",
    });
    expect(existsSync(path)).toBe(true);
    const lines = readFileSync(path, "utf8").trim().split("\n");
    expect(lines).toHaveLength(1);
    const entry = JSON.parse(lines[0]);
    expect(entry.consent_token).toBe("tok-1");
    expect(entry.to).toBe("+15551234567");
  });

  it("includes call_id in the entry when supplied", async () => {
    const path = `${tmp}/audit-with-id.jsonl`;
    await appendAuditLog(path, {
      consent_token: "tok-2",
      to: "+15551234567",
      task_path: "tasks/my-task.md",
      placed_at: "2026-04-28T15:00:00Z",
      call_id: "call-abc-123",
    });
    const lines = readFileSync(path, "utf8").trim().split("\n");
    const entry = JSON.parse(lines[0]);
    expect(entry.call_id).toBe("call-abc-123");
  });
});
