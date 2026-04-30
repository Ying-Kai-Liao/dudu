import { describe, it, expect } from "vitest";
import { validateAllowedNumber, getAllowedNumbers, AllowlistError } from "../src/allowlist.js";

const DEFAULTS = ["+61423366127", "+61405244282", "+61459529124"];

describe("allowlist", () => {
  it("getAllowedNumbers returns the three privacy-allowed defaults when env is empty", () => {
    expect(getAllowedNumbers({})).toEqual(DEFAULTS);
  });

  it("getAllowedNumbers respects CALLAGENT_ALLOWED_NUMBERS override", () => {
    expect(
      getAllowedNumbers({ CALLAGENT_ALLOWED_NUMBERS: "+15551234567,+15557654321" }),
    ).toEqual(["+15551234567", "+15557654321"]);
  });

  it("getAllowedNumbers tolerates whitespace and empty entries in override", () => {
    expect(
      getAllowedNumbers({ CALLAGENT_ALLOWED_NUMBERS: " +15551234567 , , +15557654321 " }),
    ).toEqual(["+15551234567", "+15557654321"]);
  });

  it("getAllowedNumbers falls back to defaults when override is whitespace-only", () => {
    expect(getAllowedNumbers({ CALLAGENT_ALLOWED_NUMBERS: "   " })).toEqual(DEFAULTS);
  });

  it.each(DEFAULTS)("validateAllowedNumber accepts default-allowed %s", (n) => {
    expect(() => validateAllowedNumber(n, {})).not.toThrow();
  });

  it("validateAllowedNumber rejects an unknown number with exit code 2", () => {
    try {
      validateAllowedNumber("+15551234567", {});
      throw new Error("should have thrown");
    } catch (e: any) {
      expect(e).toBeInstanceOf(AllowlistError);
      expect(e.exitCode).toBe(2);
      expect(e.message).toContain("not in the callagent allowlist");
      expect(e.message).toContain("+15551234567");
      // The error should also enumerate the allowed list, so the user can self-diagnose
      for (const n of DEFAULTS) expect(e.message).toContain(n);
    }
  });

  it("validateAllowedNumber rejects empty/undefined --to", () => {
    expect(() => validateAllowedNumber(undefined, {})).toThrow(AllowlistError);
    expect(() => validateAllowedNumber("", {})).toThrow(AllowlistError);
  });

  it("validateAllowedNumber respects an env override that excludes the defaults", () => {
    const env = { CALLAGENT_ALLOWED_NUMBERS: "+15551234567" };
    expect(() => validateAllowedNumber("+15551234567", env)).not.toThrow();
    expect(() => validateAllowedNumber("+61423366127", env)).toThrow(AllowlistError);
  });
});
