import { describe, it, expect } from "vitest";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

const cliEntry = resolve(__dirname, "../src/cli.ts");
function runCli(args: string[]) {
  return execFileSync("npx", ["tsx", cliEntry, ...args], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

describe("cli", () => {
  it("prints version", () => {
    const out = runCli(["--version"]);
    expect(out.trim()).toBe("0.1.0");
  });

  it("place --help mentions all required flags", () => {
    const out = runCli(["place", "--help"]);
    for (const flag of ["--to", "--task", "--consent-token", "--demo"]) {
      expect(out).toContain(flag);
    }
    expect(out).not.toContain("--persona");
    expect(out).not.toContain("--goal");
  });
});
