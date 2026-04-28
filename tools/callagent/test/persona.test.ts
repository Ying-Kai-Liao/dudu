import { describe, it, expect } from "vitest";
import { resolve } from "node:path";
import { parsePersona } from "../src/persona/parse.js";

const FIXTURE = resolve(__dirname, "fixtures/persona-basic.md");

describe("parsePersona", () => {
  it("parses frontmatter", async () => {
    const p = await parsePersona(FIXTURE, {});
    expect(p.frontmatter.voice).toBe("alloy");
    expect(p.frontmatter.language).toBe("en-US");
    expect(p.frontmatter.disclosure_required).toBe(true);
  });

  it("extracts disclosure when disclosure_required is true", async () => {
    const p = await parsePersona(FIXTURE, {});
    expect(p.disclosure).toContain("AI assistant calling on behalf of");
  });

  it("substitutes <FIRM> from context", async () => {
    const p = await parsePersona(FIXTURE, { FIRM: "Acme Capital" });
    expect(p.body).toContain("Acme Capital");
    expect(p.body).not.toContain("<FIRM>");
    expect(p.disclosure).toContain("Acme Capital");
  });

  it("leaves unknown placeholders intact", async () => {
    const p = await parsePersona(FIXTURE, {});
    expect(p.body).toContain("<FIRM>");
  });
});
