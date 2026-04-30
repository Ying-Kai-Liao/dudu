import { describe, it, expect } from "vitest";
import { validateAllowedNumber, ALLOWED_NUMBERS, AllowlistError } from "../src/allowlist.js";

describe("allowlist", () => {
  it("ALLOWED_NUMBERS exposes exactly the three privacy-allowed numbers", () => {
    expect([...ALLOWED_NUMBERS]).toEqual([
      "+61423366127",
      "+61405244282",
      "+61459529124",
    ]);
  });

  it.each(ALLOWED_NUMBERS)("validateAllowedNumber accepts allowlisted %s", (n) => {
    expect(() => validateAllowedNumber(n)).not.toThrow();
  });

  it("validateAllowedNumber rejects an unknown number with exit code 2", () => {
    try {
      validateAllowedNumber("+15551234567");
      throw new Error("should have thrown");
    } catch (e: any) {
      expect(e).toBeInstanceOf(AllowlistError);
      expect(e.exitCode).toBe(2);
      expect(e.message).toContain("not in the callagent allowlist");
      expect(e.message).toContain("+15551234567");
      for (const n of ALLOWED_NUMBERS) expect(e.message).toContain(n);
    }
  });

  it("validateAllowedNumber rejects empty/undefined --to", () => {
    expect(() => validateAllowedNumber(undefined)).toThrow(AllowlistError);
    expect(() => validateAllowedNumber("")).toThrow(AllowlistError);
  });

  it("CALLAGENT_ALLOWED_NUMBERS env var has no effect — list is hardcoded", () => {
    const prev = process.env.CALLAGENT_ALLOWED_NUMBERS;
    process.env.CALLAGENT_ALLOWED_NUMBERS = "+15551234567";
    try {
      expect(() => validateAllowedNumber("+15551234567")).toThrow(AllowlistError);
    } finally {
      if (prev === undefined) delete process.env.CALLAGENT_ALLOWED_NUMBERS;
      else process.env.CALLAGENT_ALLOWED_NUMBERS = prev;
    }
  });
});
