import { describe, it, expect } from "vitest";
import { resolve } from "node:path";
import { parsePersona } from "../src/persona/parse.js";
import { loadSchema } from "../src/schema/load.js";

const ROOT = resolve(__dirname, "..");

describe("bundled assets", () => {
  for (const name of ["cd-screener", "founder-reference"]) {
    it(`persona ${name} parses with disclosure_required true`, async () => {
      const p = await parsePersona(resolve(ROOT, `personas/${name}.md`), {
        FIRM: "Test Capital",
        COMPANY_DOMAIN: "test domain",
        FOUNDER_NAME: "Test Founder",
      });
      expect(p.frontmatter.disclosure_required).toBe(true);
      expect(p.disclosure).toBeTruthy();
      expect(p.body).toContain("Test Capital");
    });

    it(`schema ${name} loads`, async () => {
      const s = await loadSchema(resolve(ROOT, `schemas/${name}.schema.json`));
      expect(s.type).toBe("object");
      expect(Array.isArray(s.required)).toBe(true);
    });
  }
});
