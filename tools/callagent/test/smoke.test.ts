import { describe, it, expect } from "vitest";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

describe("package layout", () => {
  it("has expected entry files", () => {
    const root = resolve(__dirname, "..");
    for (const f of ["src/cli.ts", "package.json", "tsconfig.json"]) {
      expect(existsSync(resolve(root, f)), f).toBe(true);
    }
  });
});
