import { describe, it, expect } from "vitest";
import { resolve } from "node:path";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { loadSchema } from "../src/schema/load.js";

const VALID = resolve(__dirname, "fixtures/schema-basic.json");

describe("loadSchema", () => {
  it("loads a valid JSON Schema", async () => {
    const s = await loadSchema(VALID);
    expect(s.type).toBe("object");
    expect(s.required).toContain("pain_intensity");
  });

  it("throws on malformed JSON", async () => {
    const dir = mkdtempSync(`${tmpdir()}/callagent-`);
    const p = `${dir}/bad.json`;
    writeFileSync(p, "{ not json");
    await expect(loadSchema(p)).rejects.toThrow(/parse/i);
  });

  it("throws on schema that is not a valid JSON Schema", async () => {
    const dir = mkdtempSync(`${tmpdir()}/callagent-`);
    const p = `${dir}/bad-schema.json`;
    writeFileSync(p, JSON.stringify({ type: "not-a-real-type" }));
    await expect(loadSchema(p)).rejects.toThrow(/schema/i);
  });
});
