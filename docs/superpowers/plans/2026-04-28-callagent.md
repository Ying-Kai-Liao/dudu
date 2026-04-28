# callagent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `callagent`, a CLI under `tools/callagent/` that lets a shell agent delegate a phone call to a voice agent (Vapi v1) and receive back a transcript + structured data; optionally integrate it into dudu's `customer-discovery` and `founder-check` skills.

**Architecture:** Single-binary TypeScript CLI. `cli.ts` dispatches to three subcommands (`place`, `status`, `transcript`). `place` parses persona/schema/context inputs, runs the consent gate, asks the Provider to assemble a `CreateCallDTO`, posts it via the Provider's network layer, polls until terminal, and writes a JSON result file. Provider interface has one v1 implementation: Vapi.

**Tech Stack:** Node 20+, TypeScript, `commander` (CLI parsing), `gray-matter` (persona frontmatter), `ajv` (JSON Schema validation), native `fetch`, `tsup` (bundle), `vitest` (test).

---

## File Structure

```
tools/callagent/
├── package.json
├── tsconfig.json
├── tsup.config.ts
├── vitest.config.ts
├── README.md
├── src/
│   ├── cli.ts                        # entry, commander dispatch
│   ├── commands/
│   │   ├── place.ts                  # `place` flow: parse → consent → DTO → POST → poll → write
│   │   ├── status.ts                 # `status` flow: GET call → print
│   │   └── transcript.ts             # `transcript` flow: GET call → print transcript only
│   ├── persona/
│   │   └── parse.ts                  # parsePersona(path, context) → { frontmatter, body }
│   ├── schema/
│   │   └── load.ts                   # loadSchema(path) → ajv-validated JSON Schema
│   ├── consent.ts                    # validateConsentToken, appendAuditLog, emitBannerAndSleep
│   ├── provider/
│   │   ├── index.ts                  # Provider interface + getProvider()
│   │   └── vapi.ts                   # VapiProvider: assembleDTO, placeCall, getCall, pollUntilTerminal
│   └── output.ts                     # writeCallResult(path, record)
├── personas/
│   ├── cd-screener.md
│   └── founder-reference.md
├── schemas/
│   ├── cd-screener.schema.json
│   └── founder-reference.schema.json
└── test/
    ├── persona.test.ts
    ├── schema.test.ts
    ├── consent.test.ts
    ├── vapi-dto.test.ts
    └── fixtures/
        ├── persona-basic.md
        └── schema-basic.json
```

Plus skill edits:
- Modify `skills/customer-discovery/SKILL.md` (add optional callagent steps in prep + debrief)
- Modify `skills/founder-check/SKILL.md` (add optional reference-call step)

---

## Task 1: Scaffold the `tools/callagent/` package

**Files:**
- Create: `tools/callagent/package.json`
- Create: `tools/callagent/tsconfig.json`
- Create: `tools/callagent/tsup.config.ts`
- Create: `tools/callagent/vitest.config.ts`
- Create: `tools/callagent/.gitignore`
- Create: `tools/callagent/src/cli.ts` (placeholder)
- Create: `tools/callagent/test/smoke.test.ts`

- [ ] **Step 1: Create the directory and write `package.json`**

```bash
mkdir -p tools/callagent/src/commands tools/callagent/src/persona tools/callagent/src/schema tools/callagent/src/provider tools/callagent/personas tools/callagent/schemas tools/callagent/test/fixtures
```

`tools/callagent/package.json`:

```json
{
  "name": "callagent",
  "version": "0.1.0",
  "description": "Delegate a phone call to a voice agent and get a structured transcript back.",
  "bin": { "callagent": "./dist/cli.cjs" },
  "main": "./dist/cli.cjs",
  "scripts": {
    "build": "tsup",
    "dev": "tsx src/cli.ts",
    "test": "vitest run",
    "test:watch": "vitest",
    "typecheck": "tsc --noEmit"
  },
  "engines": { "node": ">=20" },
  "dependencies": {
    "ajv": "^8.17.1",
    "commander": "^12.1.0",
    "gray-matter": "^4.0.3"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "tsup": "^8.3.0",
    "tsx": "^4.19.0",
    "typescript": "^5.6.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Write `tsconfig.json`, `tsup.config.ts`, `vitest.config.ts`, `.gitignore`**

`tools/callagent/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "outDir": "dist",
    "declaration": false
  },
  "include": ["src/**/*", "test/**/*"]
}
```

`tools/callagent/tsup.config.ts`:

```ts
import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/cli.ts"],
  format: ["cjs"],
  outDir: "dist",
  clean: true,
  banner: { js: "#!/usr/bin/env node" },
  target: "node20",
});
```

`tools/callagent/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: { include: ["test/**/*.test.ts"], environment: "node" },
});
```

`tools/callagent/.gitignore`:

```
node_modules/
dist/
*.log
.env
```

- [ ] **Step 3: Write a placeholder `src/cli.ts` so the package builds**

`tools/callagent/src/cli.ts`:

```ts
console.log("callagent v0.1.0 — placeholder");
```

- [ ] **Step 4: Write a smoke test that asserts the package layout**

`tools/callagent/test/smoke.test.ts`:

```ts
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
```

- [ ] **Step 5: Install deps, run typecheck and tests**

```bash
cd tools/callagent && npm install && npm run typecheck && npm test
```

Expected: typecheck passes, smoke test passes.

- [ ] **Step 6: Commit**

```bash
git add tools/callagent/ -- ':!tools/callagent/node_modules'
git commit -m "Scaffold tools/callagent TypeScript package"
```

---

## Task 2: CLI skeleton with subcommand dispatch

**Files:**
- Modify: `tools/callagent/src/cli.ts`
- Create: `tools/callagent/src/commands/place.ts`
- Create: `tools/callagent/src/commands/status.ts`
- Create: `tools/callagent/src/commands/transcript.ts`
- Create: `tools/callagent/test/cli.test.ts`

- [ ] **Step 1: Write the failing test for `--version` and `place --help`**

`tools/callagent/test/cli.test.ts`:

```ts
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
    for (const flag of ["--to", "--persona", "--goal", "--schema", "--consent-token"]) {
      expect(out).toContain(flag);
    }
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd tools/callagent && npm test -- cli.test.ts
```

Expected: FAIL — `--version` not implemented.

- [ ] **Step 3: Write the three command stubs**

`tools/callagent/src/commands/place.ts`:

```ts
export interface PlaceOptions {
  to: string;
  persona: string;
  goal: string;
  schema: string;
  tools?: string;
  context?: string;
  maxDuration: number;
  record: boolean;
  dryRun: boolean;
  output?: string;
  consentToken: string;
}

export async function placeCommand(_opts: PlaceOptions): Promise<void> {
  throw new Error("place not yet implemented");
}
```

`tools/callagent/src/commands/status.ts`:

```ts
export async function statusCommand(_callId: string): Promise<void> {
  throw new Error("status not yet implemented");
}
```

`tools/callagent/src/commands/transcript.ts`:

```ts
export async function transcriptCommand(_callId: string): Promise<void> {
  throw new Error("transcript not yet implemented");
}
```

- [ ] **Step 4: Wire commander in `src/cli.ts`**

`tools/callagent/src/cli.ts`:

```ts
import { Command } from "commander";
import { placeCommand } from "./commands/place.js";
import { statusCommand } from "./commands/status.js";
import { transcriptCommand } from "./commands/transcript.js";

const program = new Command();
program
  .name("callagent")
  .description("Delegate a phone call to a voice agent.")
  .version("0.1.0");

program
  .command("place")
  .description("Place an outbound call and return a structured transcript.")
  .requiredOption("--to <e164>", "phone number in E.164 format")
  .requiredOption("--persona <path>", "path to persona markdown file")
  .requiredOption("--goal <string>", "one-sentence call goal")
  .requiredOption("--schema <path>", "path to JSON Schema for structured extraction")
  .requiredOption("--consent-token <token>", "opaque consent token from caller")
  .option("--tools <path>", "path to tools JSON (v1 errors if non-empty)")
  .option("--context <path>", "path to context markdown injected into the system prompt")
  .option("--max-duration <seconds>", "max call duration", (v) => parseInt(v, 10), 600)
  .option("--record <bool>", "record the call", (v) => v !== "false", true)
  .option("--dry-run", "print the resolved CreateCallDTO and exit", false)
  .option("--output <path>", "where to write the result JSON")
  .action(async (opts) => {
    try { await placeCommand(opts); }
    catch (e: any) { console.error(e.message); process.exit(e.exitCode ?? 1); }
  });

program
  .command("status <callId>")
  .description("Fetch current status of a previously placed call.")
  .action(async (callId) => {
    try { await statusCommand(callId); }
    catch (e: any) { console.error(e.message); process.exit(e.exitCode ?? 1); }
  });

program
  .command("transcript <callId>")
  .description("Fetch transcript of a completed call.")
  .action(async (callId) => {
    try { await transcriptCommand(callId); }
    catch (e: any) { console.error(e.message); process.exit(e.exitCode ?? 1); }
  });

program.parseAsync();
```

- [ ] **Step 5: Run test, verify it passes**

```bash
cd tools/callagent && npm test -- cli.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/callagent/src tools/callagent/test/cli.test.ts
git commit -m "Add callagent CLI skeleton with subcommand dispatch"
```

---

## Task 3: Persona parser with variable substitution

**Files:**
- Create: `tools/callagent/src/persona/parse.ts`
- Create: `tools/callagent/test/persona.test.ts`
- Create: `tools/callagent/test/fixtures/persona-basic.md`

- [ ] **Step 1: Write the fixture persona**

`tools/callagent/test/fixtures/persona-basic.md`:

```markdown
---
voice: alloy
language: en-US
disclosure_required: true
---

# Persona: VC screener

You are an AI assistant calling on behalf of <FIRM>. Disclose first.

## Disclosure
"Hi, I'm an AI assistant calling on behalf of <FIRM>. Recorded for research. Good time?"

## Style
- One question at a time
```

- [ ] **Step 2: Write the failing test**

`tools/callagent/test/persona.test.ts`:

```ts
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
```

- [ ] **Step 3: Run test, verify it fails**

```bash
cd tools/callagent && npm test -- persona.test.ts
```

Expected: FAIL — `parsePersona` does not exist.

- [ ] **Step 4: Implement the parser**

`tools/callagent/src/persona/parse.ts`:

```ts
import { readFile } from "node:fs/promises";
import matter from "gray-matter";

export interface PersonaFrontmatter {
  voice?: string;
  language?: string;
  disclosure_required?: boolean;
}

export interface ParsedPersona {
  frontmatter: PersonaFrontmatter;
  body: string;
  disclosure: string | null;
}

export async function parsePersona(
  path: string,
  context: Record<string, string>,
): Promise<ParsedPersona> {
  const raw = await readFile(path, "utf8");
  const { data, content } = matter(raw);
  const body = substitute(content, context);
  const fm = data as PersonaFrontmatter;
  const disclosure = fm.disclosure_required ? extractDisclosure(body) : null;
  return { frontmatter: fm, body, disclosure };
}

function substitute(s: string, ctx: Record<string, string>): string {
  return s.replace(/<([A-Z_][A-Z0-9_]*)>/g, (m, key) =>
    Object.prototype.hasOwnProperty.call(ctx, key) ? ctx[key] : m,
  );
}

function extractDisclosure(body: string): string {
  const m = body.match(/##\s+Disclosure\s*\n+(.+?)(?:\n##|\n*$)/s);
  if (!m) return "";
  return m[1].trim().replace(/^"|"$/g, "");
}
```

- [ ] **Step 5: Run test, verify it passes**

```bash
cd tools/callagent && npm test -- persona.test.ts
```

Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add tools/callagent/src/persona tools/callagent/test/persona.test.ts tools/callagent/test/fixtures/persona-basic.md
git commit -m "Add persona parser with frontmatter and variable substitution"
```

---

## Task 4: Schema loader

**Files:**
- Create: `tools/callagent/src/schema/load.ts`
- Create: `tools/callagent/test/schema.test.ts`
- Create: `tools/callagent/test/fixtures/schema-basic.json`

- [ ] **Step 1: Write the fixture schema**

`tools/callagent/test/fixtures/schema-basic.json`:

```json
{
  "type": "object",
  "properties": {
    "pain_intensity": { "type": "integer", "minimum": 1, "maximum": 10 },
    "pain_quote": { "type": "string" }
  },
  "required": ["pain_intensity", "pain_quote"]
}
```

- [ ] **Step 2: Write the failing test**

`tools/callagent/test/schema.test.ts`:

```ts
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
```

- [ ] **Step 3: Run test, verify it fails**

```bash
cd tools/callagent && npm test -- schema.test.ts
```

Expected: FAIL — `loadSchema` not defined.

- [ ] **Step 4: Implement the loader**

`tools/callagent/src/schema/load.ts`:

```ts
import { readFile } from "node:fs/promises";
import Ajv from "ajv";

const ajv = new Ajv({ strict: false });

export type JsonSchema = Record<string, unknown>;

export async function loadSchema(path: string): Promise<JsonSchema> {
  const raw = await readFile(path, "utf8");
  let parsed: JsonSchema;
  try {
    parsed = JSON.parse(raw);
  } catch (e: any) {
    throw new Error(`Failed to parse schema JSON at ${path}: ${e.message}`);
  }
  try {
    ajv.compile(parsed);
  } catch (e: any) {
    throw new Error(`Invalid JSON Schema at ${path}: ${e.message}`);
  }
  return parsed;
}
```

- [ ] **Step 5: Run test, verify it passes**

```bash
cd tools/callagent && npm test -- schema.test.ts
```

Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add tools/callagent/src/schema tools/callagent/test/schema.test.ts tools/callagent/test/fixtures/schema-basic.json
git commit -m "Add JSON Schema loader with ajv validation"
```

---

## Task 5: Consent gate (validation, audit log, banner)

**Files:**
- Create: `tools/callagent/src/consent.ts`
- Create: `tools/callagent/test/consent.test.ts`

- [ ] **Step 1: Write the failing test**

`tools/callagent/test/consent.test.ts`:

```ts
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
      persona_path: "personas/cd-screener.md",
      placed_at: "2026-04-28T15:00:00Z",
    });
    expect(existsSync(path)).toBe(true);
    const lines = readFileSync(path, "utf8").trim().split("\n");
    expect(lines).toHaveLength(1);
    const entry = JSON.parse(lines[0]);
    expect(entry.consent_token).toBe("tok-1");
    expect(entry.to).toBe("+15551234567");
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd tools/callagent && npm test -- consent.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement consent module**

`tools/callagent/src/consent.ts`:

```ts
import { mkdir, appendFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";

export class ConsentError extends Error {
  exitCode = 3;
  constructor(msg: string) { super(msg); this.name = "ConsentError"; }
}

export function validateConsentToken(token: string | undefined): void {
  if (!token || !token.trim()) {
    throw new ConsentError(
      "Missing or empty --consent-token. The caller must collect explicit opt-in before placing a call. " +
      "See callagent's README §Consent for the audit-log convention.",
    );
  }
}

export interface AuditLogEntry {
  consent_token: string;
  to: string;
  persona_path: string;
  placed_at: string;
}

export async function appendAuditLog(path: string, entry: AuditLogEntry): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  await appendFile(path, JSON.stringify(entry) + "\n", "utf8");
}

export function resolveAuditLogPath(opts: {
  env: string | undefined;
  outputPath: string | undefined;
}): string {
  if (opts.env) return opts.env;
  if (opts.outputPath) return resolve(dirname(opts.outputPath), "consent-log.jsonl");
  return resolve(process.cwd(), "consent-log.jsonl");
}

export async function emitBannerAndSleep(opts: {
  to: string;
  personaName: string;
  consentTokenHash: string;
  auditLogPath: string;
  abortSeconds: number;
}): Promise<void> {
  const redactedTo = opts.to.replace(/\d(?=\d{4})/g, "*");
  process.stderr.write(
    `[callagent] Placing call to ${redactedTo} with persona ${opts.personaName}.\n` +
    `[callagent] Consent token: ${opts.consentTokenHash}. Audit log: ${opts.auditLogPath}.\n` +
    `[callagent] If you do not have explicit opt-in from this target, abort now (Ctrl+C).\n` +
    `[callagent] Sleeping ${opts.abortSeconds}s before placing call.\n`,
  );
  await sleep(opts.abortSeconds * 1000);
}

export function hashToken(token: string): string {
  let h = 0;
  for (let i = 0; i < token.length; i++) {
    h = (h * 31 + token.charCodeAt(i)) | 0;
  }
  return Math.abs(h).toString(16).padStart(8, "0");
}
```

- [ ] **Step 4: Run test, verify it passes**

```bash
cd tools/callagent && npm test -- consent.test.ts
```

Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/callagent/src/consent.ts tools/callagent/test/consent.test.ts
git commit -m "Add consent gate, audit log append, and abort-window banner"
```

---

## Task 6: Provider interface + Vapi DTO assembler (no network)

**Files:**
- Create: `tools/callagent/src/provider/index.ts`
- Create: `tools/callagent/src/provider/vapi.ts`
- Create: `tools/callagent/test/vapi-dto.test.ts`

- [ ] **Step 1: Write the failing test for `assembleDTO`**

`tools/callagent/test/vapi-dto.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { VapiProvider } from "../src/provider/vapi.js";

const provider = new VapiProvider({ apiKey: "test", fromNumber: "+15550000000" });

describe("VapiProvider.assembleDTO", () => {
  const baseSpec = {
    to: "+15551234567",
    persona: {
      frontmatter: { voice: "alloy", language: "en-US", disclosure_required: true },
      body: "You are an AI assistant calling on behalf of Acme.",
      disclosure: "Hi, I'm an AI assistant calling on behalf of Acme. Recorded for research.",
    },
    goal: "5-minute pain/WTP screener",
    schema: {
      type: "object",
      properties: { pain_intensity: { type: "integer" } },
      required: ["pain_intensity"],
    },
    context: undefined,
    maxDurationSeconds: 600,
    record: true,
  };

  it("includes the persona body in model.messages", () => {
    const dto = provider.assembleDTO(baseSpec);
    expect(dto.assistant.model.messages[0].role).toBe("system");
    expect(dto.assistant.model.messages[0].content).toContain(baseSpec.persona.body);
  });

  it("appends the goal to the system message", () => {
    const dto = provider.assembleDTO(baseSpec);
    expect(dto.assistant.model.messages[0].content).toContain(baseSpec.goal);
  });

  it("sets firstMessage to the disclosure when disclosure_required is true", () => {
    const dto = provider.assembleDTO(baseSpec);
    expect(dto.assistant.firstMessage).toBe(baseSpec.persona.disclosure);
  });

  it("omits firstMessage when disclosure_required is false", () => {
    const spec = {
      ...baseSpec,
      persona: { ...baseSpec.persona, frontmatter: { ...baseSpec.persona.frontmatter, disclosure_required: false }, disclosure: null },
    };
    const dto = provider.assembleDTO(spec);
    expect(dto.assistant.firstMessage).toBeUndefined();
  });

  it("attaches the schema as analysisPlan.structuredDataSchema", () => {
    const dto = provider.assembleDTO(baseSpec);
    expect(dto.assistant.analysisPlan.structuredDataSchema).toEqual(baseSpec.schema);
  });

  it("sets the from-number, to-number, and recording flag", () => {
    const dto = provider.assembleDTO(baseSpec);
    expect(dto.phoneNumber.twilioPhoneNumber).toBe("+15550000000");
    expect(dto.customer.number).toBe("+15551234567");
    expect(dto.assistant.recordingEnabled).toBe(true);
    expect(dto.assistant.maxDurationSeconds).toBe(600);
  });

  it("includes context as a second system message when provided", () => {
    const spec = { ...baseSpec, context: "Company: Acme. ICP: SMB accountants." };
    const dto = provider.assembleDTO(spec);
    expect(dto.assistant.model.messages.length).toBe(2);
    expect(dto.assistant.model.messages[1].content).toContain("Acme");
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd tools/callagent && npm test -- vapi-dto.test.ts
```

Expected: FAIL — `VapiProvider` not found.

- [ ] **Step 3: Write the Provider interface**

`tools/callagent/src/provider/index.ts`:

```ts
import { ParsedPersona } from "../persona/parse.js";
import { JsonSchema } from "../schema/load.js";

export interface CallSpec {
  to: string;
  persona: ParsedPersona;
  goal: string;
  schema: JsonSchema;
  context: string | undefined;
  maxDurationSeconds: number;
  record: boolean;
}

export interface CallRecord {
  call_id: string;
  status: "queued" | "ringing" | "in-progress" | "ended" | "failed";
  ended_reason?: string;
  started_at?: string;
  ended_at?: string;
  duration_seconds?: number;
  to: string;
  transcript?: string;
  messages?: Array<{ role: string; message: string; time?: number }>;
  recording_url?: string;
  structured_data?: Record<string, unknown> | null;
  tool_calls?: unknown[];
  provider: string;
}

export interface Provider {
  assembleDTO(spec: CallSpec): unknown;
  placeCall(spec: CallSpec): Promise<string>;
  getCall(callId: string): Promise<CallRecord>;
  pollUntilTerminal(callId: string, timeoutMs: number): Promise<CallRecord>;
}

export function getProvider(): Provider {
  const name = process.env.CALLAGENT_PROVIDER ?? "vapi";
  if (name === "vapi") {
    const { VapiProvider } = require("./vapi.js");
    return new VapiProvider({
      apiKey: requireEnv("VAPI_API_KEY"),
      fromNumber: requireEnv("VAPI_FROM_NUMBER"),
    });
  }
  throw new Error(`Unknown CALLAGENT_PROVIDER: ${name}`);
}

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} is not set in env.`);
  return v;
}
```

- [ ] **Step 4: Implement `VapiProvider.assembleDTO` (network methods stubbed)**

`tools/callagent/src/provider/vapi.ts`:

```ts
import { CallRecord, CallSpec, Provider } from "./index.js";

export interface VapiOptions {
  apiKey: string;
  fromNumber: string;
}

export class VapiProvider implements Provider {
  constructor(private opts: VapiOptions) {}

  assembleDTO(spec: CallSpec): any {
    const systemMessage =
      spec.persona.body.trim() +
      "\n\n## Goal for this call\n" +
      spec.goal;

    const messages: Array<{ role: string; content: string }> = [
      { role: "system", content: systemMessage },
    ];
    if (spec.context) {
      messages.push({ role: "system", content: spec.context });
    }

    const assistant: any = {
      model: {
        provider: "openai",
        model: "gpt-4o",
        messages,
      },
      voice: {
        provider: "openai",
        voiceId: spec.persona.frontmatter.voice ?? "alloy",
      },
      analysisPlan: {
        structuredDataSchema: spec.schema,
      },
      recordingEnabled: spec.record,
      maxDurationSeconds: spec.maxDurationSeconds,
    };

    if (spec.persona.frontmatter.disclosure_required && spec.persona.disclosure) {
      assistant.firstMessage = spec.persona.disclosure;
    }

    return {
      assistant,
      customer: { number: spec.to },
      phoneNumber: { twilioPhoneNumber: this.opts.fromNumber },
    };
  }

  async placeCall(_spec: CallSpec): Promise<string> {
    throw new Error("placeCall network not yet implemented");
  }

  async getCall(_callId: string): Promise<CallRecord> {
    throw new Error("getCall network not yet implemented");
  }

  async pollUntilTerminal(_callId: string, _timeoutMs: number): Promise<CallRecord> {
    throw new Error("pollUntilTerminal not yet implemented");
  }
}
```

- [ ] **Step 5: Run test, verify it passes**

```bash
cd tools/callagent && npm test -- vapi-dto.test.ts
```

Expected: PASS (7 tests).

- [ ] **Step 6: Commit**

```bash
git add tools/callagent/src/provider tools/callagent/test/vapi-dto.test.ts
git commit -m "Add Provider interface and VapiProvider.assembleDTO (no network)"
```

---

## Task 7: Vapi network layer (place / get / poll)

**Files:**
- Modify: `tools/callagent/src/provider/vapi.ts`
- Create: `tools/callagent/test/vapi-network.test.ts`

- [ ] **Step 1: Write the failing test using a stubbed `fetch`**

`tools/callagent/test/vapi-network.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { VapiProvider } from "../src/provider/vapi.js";

const fakeSpec = {
  to: "+15551234567",
  persona: { frontmatter: { disclosure_required: false }, body: "B", disclosure: null },
  goal: "G",
  schema: { type: "object" } as Record<string, unknown>,
  context: undefined,
  maxDurationSeconds: 60,
  record: true,
};

describe("VapiProvider network", () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it("placeCall POSTs to /call and returns the id", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "call-abc" }), { status: 201 }),
    );
    const p = new VapiProvider({ apiKey: "k", fromNumber: "+1" });
    const id = await p.placeCall(fakeSpec as any);
    expect(id).toBe("call-abc");
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://api.vapi.ai/call");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer k");
    expect(init.method).toBe("POST");
  });

  it("placeCall throws on non-2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("nope", { status: 401 }),
    );
    const p = new VapiProvider({ apiKey: "k", fromNumber: "+1" });
    await expect(p.placeCall(fakeSpec as any)).rejects.toThrow(/401/);
  });

  it("getCall GETs /call/:id and maps the response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        id: "call-abc",
        status: "ended",
        endedReason: "hangup",
        startedAt: "2026-04-28T15:00:00Z",
        endedAt: "2026-04-28T15:05:00Z",
        artifact: { transcript: "AI: hi", recording: { stereoUrl: "https://r/" }, messages: [] },
        analysis: { structuredData: { pain_intensity: 7 } },
        customer: { number: "+15551234567" },
      }), { status: 200 }),
    );
    const p = new VapiProvider({ apiKey: "k", fromNumber: "+1" });
    const rec = await p.getCall("call-abc");
    expect(rec.call_id).toBe("call-abc");
    expect(rec.status).toBe("ended");
    expect(rec.transcript).toBe("AI: hi");
    expect(rec.recording_url).toBe("https://r/");
    expect(rec.structured_data).toEqual({ pain_intensity: 7 });
  });

  it("pollUntilTerminal returns once status is terminal", async () => {
    let n = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
      n++;
      const status = n < 2 ? "in-progress" : "ended";
      return new Response(JSON.stringify({
        id: "call-abc",
        status,
        endedReason: status === "ended" ? "hangup" : undefined,
        artifact: status === "ended" ? { transcript: "T", recording: { stereoUrl: "u" } } : undefined,
        analysis: status === "ended" ? { structuredData: {} } : undefined,
        customer: { number: "+15551234567" },
      }), { status: 200 });
    });
    const p = new VapiProvider({ apiKey: "k", fromNumber: "+1", pollIntervalMs: 5 });
    const rec = await p.pollUntilTerminal("call-abc", 1000);
    expect(rec.status).toBe("ended");
    expect(n).toBeGreaterThanOrEqual(2);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd tools/callagent && npm test -- vapi-network.test.ts
```

Expected: FAIL — methods throw "not yet implemented".

- [ ] **Step 3: Implement the network methods**

Replace `tools/callagent/src/provider/vapi.ts` with:

```ts
import { CallRecord, CallSpec, Provider } from "./index.js";

const VAPI_BASE = "https://api.vapi.ai";

export interface VapiOptions {
  apiKey: string;
  fromNumber: string;
  pollIntervalMs?: number;
}

export class VapiProvider implements Provider {
  constructor(private opts: VapiOptions) {}

  assembleDTO(spec: CallSpec): any {
    const systemMessage =
      spec.persona.body.trim() +
      "\n\n## Goal for this call\n" +
      spec.goal;

    const messages: Array<{ role: string; content: string }> = [
      { role: "system", content: systemMessage },
    ];
    if (spec.context) {
      messages.push({ role: "system", content: spec.context });
    }

    const assistant: any = {
      model: { provider: "openai", model: "gpt-4o", messages },
      voice: {
        provider: "openai",
        voiceId: spec.persona.frontmatter.voice ?? "alloy",
      },
      analysisPlan: { structuredDataSchema: spec.schema },
      recordingEnabled: spec.record,
      maxDurationSeconds: spec.maxDurationSeconds,
    };

    if (spec.persona.frontmatter.disclosure_required && spec.persona.disclosure) {
      assistant.firstMessage = spec.persona.disclosure;
    }

    return {
      assistant,
      customer: { number: spec.to },
      phoneNumber: { twilioPhoneNumber: this.opts.fromNumber },
    };
  }

  async placeCall(spec: CallSpec): Promise<string> {
    const dto = this.assembleDTO(spec);
    const res = await fetch(`${VAPI_BASE}/call`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.opts.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(dto),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Vapi POST /call failed (${res.status}): ${text}`);
    }
    const data = (await res.json()) as { id: string };
    return data.id;
  }

  async getCall(callId: string): Promise<CallRecord> {
    const res = await fetch(`${VAPI_BASE}/call/${callId}`, {
      headers: { Authorization: `Bearer ${this.opts.apiKey}` },
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Vapi GET /call/${callId} failed (${res.status}): ${text}`);
    }
    const v = await res.json() as any;
    return {
      call_id: v.id,
      status: this.mapStatus(v.status),
      ended_reason: v.endedReason,
      started_at: v.startedAt,
      ended_at: v.endedAt,
      duration_seconds:
        v.startedAt && v.endedAt
          ? Math.round((Date.parse(v.endedAt) - Date.parse(v.startedAt)) / 1000)
          : undefined,
      to: v.customer?.number,
      transcript: v.artifact?.transcript,
      messages: v.artifact?.messages,
      recording_url: v.artifact?.recording?.stereoUrl ?? v.artifact?.recording?.url,
      structured_data: v.analysis?.structuredData ?? null,
      tool_calls: [],
      provider: "vapi",
    };
  }

  async pollUntilTerminal(callId: string, timeoutMs: number): Promise<CallRecord> {
    const interval = this.opts.pollIntervalMs ?? 5000;
    const deadline = Date.now() + timeoutMs;
    while (true) {
      const rec = await this.getCall(callId);
      if (rec.status === "ended" || rec.status === "failed") return rec;
      if (Date.now() > deadline) {
        const e = new Error(`Polling timed out after ${timeoutMs}ms; last status ${rec.status}`);
        (e as any).exitCode = 4;
        throw e;
      }
      await new Promise((r) => setTimeout(r, interval));
    }
  }

  private mapStatus(s: string): CallRecord["status"] {
    if (s === "ended") return "ended";
    if (s === "in-progress") return "in-progress";
    if (s === "ringing") return "ringing";
    if (s === "queued" || s === "scheduled") return "queued";
    if (s === "failed") return "failed";
    return "in-progress";
  }
}
```

- [ ] **Step 4: Run all tests, verify they pass**

```bash
cd tools/callagent && npm test
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add tools/callagent/src/provider/vapi.ts tools/callagent/test/vapi-network.test.ts
git commit -m "Add Vapi network layer: placeCall, getCall, pollUntilTerminal"
```

---

## Task 8: Wire `place` command end-to-end

**Files:**
- Modify: `tools/callagent/src/commands/place.ts`
- Create: `tools/callagent/src/output.ts`
- Create: `tools/callagent/test/place.test.ts`

- [ ] **Step 1: Write `output.ts` (no test — pure file write)**

`tools/callagent/src/output.ts`:

```ts
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { CallRecord } from "./provider/index.js";

export async function writeCallResult(
  path: string,
  record: CallRecord & { consent_token: string },
): Promise<void> {
  const abs = resolve(path);
  await mkdir(dirname(abs), { recursive: true });
  await writeFile(abs, JSON.stringify(record, null, 2), "utf8");
}
```

- [ ] **Step 2: Write the failing dry-run test**

`tools/callagent/test/place.test.ts`:

```ts
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
```

- [ ] **Step 3: Run test, verify it fails**

```bash
cd tools/callagent && npm test -- place.test.ts
```

Expected: FAIL — `placeCommand` throws "place not yet implemented".

- [ ] **Step 4: Implement `placeCommand`**

`tools/callagent/src/commands/place.ts`:

```ts
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { parsePersona } from "../persona/parse.js";
import { loadSchema } from "../schema/load.js";
import {
  validateConsentToken,
  appendAuditLog,
  resolveAuditLogPath,
  emitBannerAndSleep,
  hashToken,
} from "../consent.js";
import { getProvider } from "../provider/index.js";
import { writeCallResult } from "../output.js";

export interface PlaceOptions {
  to: string;
  persona: string;
  goal: string;
  schema: string;
  tools?: string;
  context?: string;
  maxDuration: number;
  record: boolean;
  dryRun: boolean;
  output?: string;
  consentToken: string;
}

const ABORT_WINDOW_SECONDS = 5;

export async function placeCommand(opts: PlaceOptions): Promise<void> {
  validateConsentToken(opts.consentToken);

  if (opts.tools) {
    const raw = await readFile(opts.tools, "utf8");
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      const e: any = new Error(
        "Mid-call tools are not supported in callagent v1. " +
        "See docs/callagent/v1.1-tools.md for the v1.1 plan.",
      );
      e.exitCode = 2;
      throw e;
    }
  }

  const contextStr = opts.context ? await readFile(opts.context, "utf8") : undefined;
  const ctxVars = parseContextVars(contextStr);
  const persona = await parsePersona(opts.persona, ctxVars);
  const schema = await loadSchema(opts.schema);

  const spec = {
    to: opts.to,
    persona,
    goal: opts.goal,
    schema,
    context: contextStr,
    maxDurationSeconds: opts.maxDuration,
    record: opts.record,
  };

  const outputPath = opts.output ?? `./call-pending.json`;

  if (opts.dryRun) {
    const provider = tryGetProviderOrStub();
    const dto = provider.assembleDTO(spec);
    console.log(JSON.stringify(dto, null, 2));
    return;
  }

  const auditLogPath = resolveAuditLogPath({
    env: process.env.CALLAGENT_AUDIT_LOG,
    outputPath,
  });
  const placedAt = new Date().toISOString();
  await appendAuditLog(auditLogPath, {
    consent_token: opts.consentToken,
    to: opts.to,
    persona_path: resolve(opts.persona),
    placed_at: placedAt,
  });

  await emitBannerAndSleep({
    to: opts.to,
    personaName: opts.persona.split("/").pop() ?? opts.persona,
    consentTokenHash: hashToken(opts.consentToken),
    auditLogPath,
    abortSeconds: ABORT_WINDOW_SECONDS,
  });

  const provider = getProvider();
  const callId = await provider.placeCall(spec);
  const finalRec = await provider.pollUntilTerminal(callId, opts.maxDuration * 1000 + 60_000);
  const finalPath = opts.output ?? `./call-${callId}.json`;
  await writeCallResult(finalPath, { ...finalRec, consent_token: opts.consentToken });
  process.stderr.write(`[callagent] Wrote ${finalPath}\n`);
}

function parseContextVars(ctx: string | undefined): Record<string, string> {
  if (!ctx) return {};
  const out: Record<string, string> = {};
  const m = ctx.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return out;
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^([A-Z_][A-Z0-9_]*):\s*(.+)$/);
    if (kv) out[kv[1]] = kv[2].trim();
  }
  return out;
}

function tryGetProviderOrStub() {
  try { return getProvider(); }
  catch {
    const { VapiProvider } = require("../provider/vapi.js");
    return new VapiProvider({ apiKey: "stub", fromNumber: "+10000000000" });
  }
}
```

- [ ] **Step 5: Run test, verify it passes**

```bash
cd tools/callagent && npm test -- place.test.ts
```

Expected: PASS (3 tests).

- [ ] **Step 6: Run the full suite**

```bash
cd tools/callagent && npm test
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add tools/callagent/src/commands/place.ts tools/callagent/src/output.ts tools/callagent/test/place.test.ts
git commit -m "Wire callagent place: parse → consent → DTO → place → poll → write"
```

---

## Task 9: Implement `status` and `transcript` commands

**Files:**
- Modify: `tools/callagent/src/commands/status.ts`
- Modify: `tools/callagent/src/commands/transcript.ts`
- Create: `tools/callagent/test/status-transcript.test.ts`

- [ ] **Step 1: Write the failing test**

`tools/callagent/test/status-transcript.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { statusCommand } from "../src/commands/status.js";
import { transcriptCommand } from "../src/commands/transcript.js";

beforeEach(() => {
  process.env.VAPI_API_KEY = "test";
  process.env.VAPI_FROM_NUMBER = "+15550000000";
  vi.restoreAllMocks();
});

describe("statusCommand", () => {
  it("prints JSON with the call status fields", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        id: "abc", status: "ended", customer: { number: "+1" },
        artifact: { transcript: "T" }, analysis: { structuredData: {} },
        endedReason: "hangup",
      }), { status: 200 }),
    );
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    await statusCommand("abc");
    const printed = JSON.parse(log.mock.calls[0][0] as string);
    expect(printed.call_id).toBe("abc");
    expect(printed.status).toBe("ended");
  });
});

describe("transcriptCommand", () => {
  it("prints only the transcript", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        id: "abc", status: "ended", customer: { number: "+1" },
        artifact: { transcript: "AI: Hello\nUser: Hi" },
      }), { status: 200 }),
    );
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    await transcriptCommand("abc");
    expect(log.mock.calls[0][0]).toBe("AI: Hello\nUser: Hi");
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd tools/callagent && npm test -- status-transcript.test.ts
```

Expected: FAIL — commands throw "not yet implemented".

- [ ] **Step 3: Implement status and transcript**

`tools/callagent/src/commands/status.ts`:

```ts
import { getProvider } from "../provider/index.js";

export async function statusCommand(callId: string): Promise<void> {
  const provider = getProvider();
  const rec = await provider.getCall(callId);
  console.log(JSON.stringify(rec, null, 2));
}
```

`tools/callagent/src/commands/transcript.ts`:

```ts
import { getProvider } from "../provider/index.js";

export async function transcriptCommand(callId: string): Promise<void> {
  const provider = getProvider();
  const rec = await provider.getCall(callId);
  console.log(rec.transcript ?? "");
}
```

- [ ] **Step 4: Run test, verify it passes**

```bash
cd tools/callagent && npm test
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add tools/callagent/src/commands tools/callagent/test/status-transcript.test.ts
git commit -m "Implement callagent status and transcript subcommands"
```

---

## Task 10: Bundled personas + schemas

**Files:**
- Create: `tools/callagent/personas/cd-screener.md`
- Create: `tools/callagent/personas/founder-reference.md`
- Create: `tools/callagent/schemas/cd-screener.schema.json`
- Create: `tools/callagent/schemas/founder-reference.schema.json`
- Create: `tools/callagent/test/bundled.test.ts`

- [ ] **Step 1: Write `cd-screener.md`**

`tools/callagent/personas/cd-screener.md`:

```markdown
---
voice: alloy
language: en-US
disclosure_required: true
---

# Persona: customer-discovery screener

You are an AI assistant calling on behalf of <FIRM>, an investment firm doing
research on <COMPANY_DOMAIN>. Your job is a 5-minute screener call to learn
about the recipient's experience with the relevant problem. You are NOT here
to sell, NOT here to pitch any company, and NOT here to schedule anything
beyond a possible follow-up with a human researcher.

## Disclosure
"Hi, I'm an AI assistant calling on behalf of <FIRM>. This call is being
recorded for research purposes. Is now still a good time for a five-minute
conversation?"

## Style
- Conversational. One question at a time.
- After they speak, pause for at least three seconds before following up.
- Never argue, never sell, never share opinions about competitors.
- If they ask to end the call at any time, end immediately and thank them.

## Goals (in order)
1. Confirm consent and recording.
2. Understand the problem in their day-to-day. Get a verbatim story.
3. Understand how they solve it today (vendor, tool, manual workaround).
4. Probe willingness to pay — only accept numbers they volunteer.
5. Ask if they'd be willing to talk to a human researcher for 30 minutes.
6. Thank them and end the call.

## Hard rules
- Do not name the portfolio company under evaluation.
- Do not pitch any product.
- If asked who the firm is investing in, say "I can't share that — I'm just
  collecting market research."
- Hang up on first request. End the call cleanly with a thank-you.
```

- [ ] **Step 2: Write `cd-screener.schema.json`**

`tools/callagent/schemas/cd-screener.schema.json`:

```json
{
  "type": "object",
  "properties": {
    "consent_confirmed": { "type": "boolean" },
    "pain_intensity": { "type": "integer", "minimum": 1, "maximum": 10 },
    "pain_quote": { "type": "string", "description": "Verbatim quote describing the pain." },
    "current_solution": { "type": "string", "description": "What they use today, vendor or workaround." },
    "wtp_signal": { "type": "string", "description": "Verbatim WTP statement, or 'none' if not given." },
    "willing_to_meet_vc": { "type": "boolean" },
    "top_objection": { "type": "string", "description": "If they pushed back, the strongest objection. Empty if none." }
  },
  "required": ["consent_confirmed", "pain_intensity", "pain_quote", "current_solution", "wtp_signal", "willing_to_meet_vc", "top_objection"]
}
```

- [ ] **Step 3: Write `founder-reference.md`**

`tools/callagent/personas/founder-reference.md`:

```markdown
---
voice: alloy
language: en-US
disclosure_required: true
---

# Persona: founder reference call

You are an AI assistant calling on behalf of <FIRM>, an investment firm
evaluating <FOUNDER_NAME>. <FOUNDER_NAME> listed you as a reference. Your job
is a 5-minute call asking about your working relationship and your honest
assessment.

## Disclosure
"Hi, I'm an AI assistant calling on behalf of <FIRM>. <FOUNDER_NAME> listed
you as a reference. This call is being recorded for our internal records. Do
you have five minutes?"

## Style
- Warm and brief. Reference calls should feel respectful of the reference's time.
- Open-ended questions. Pause and listen.
- Never reveal what other references said, never share <FOUNDER_NAME>'s pitch.

## Goals (in order)
1. Confirm consent and recording.
2. Working-relationship context — how they know <FOUNDER_NAME>, dates, role.
3. Two or three concrete strengths, with specific examples.
4. One or two concerns or growth areas, with specific examples.
5. Would they work with <FOUNDER_NAME> again? Yes / no / qualified — and why.
6. Thank them and end.

## Hard rules
- If the reference is uncomfortable answering anything, move on immediately.
- Never push for a yes/no on "would you invest in this person". That's the
  firm's job, not the reference's.
- End the call on first request.
```

- [ ] **Step 4: Write `founder-reference.schema.json`**

`tools/callagent/schemas/founder-reference.schema.json`:

```json
{
  "type": "object",
  "properties": {
    "consent_confirmed": { "type": "boolean" },
    "relationship_context": { "type": "string" },
    "working_dates": { "type": "string", "description": "Approximate dates, e.g. '2019-2022'." },
    "key_strengths": { "type": "array", "items": { "type": "string" }, "maxItems": 3 },
    "key_concerns": { "type": "array", "items": { "type": "string" }, "maxItems": 3 },
    "would_work_with_again": { "enum": ["yes", "no", "qualified"] },
    "would_work_with_again_reason": { "type": "string" },
    "reference_quality": { "enum": ["high", "medium", "low"], "description": "High if they gave specific examples; low if vague." }
  },
  "required": ["consent_confirmed", "relationship_context", "working_dates", "key_strengths", "key_concerns", "would_work_with_again", "would_work_with_again_reason", "reference_quality"]
}
```

- [ ] **Step 5: Write a smoke test that asserts each bundled file parses cleanly**

`tools/callagent/test/bundled.test.ts`:

```ts
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
```

- [ ] **Step 6: Run test, verify it passes**

```bash
cd tools/callagent && npm test -- bundled.test.ts
```

Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add tools/callagent/personas tools/callagent/schemas tools/callagent/test/bundled.test.ts
git commit -m "Add bundled CD-screener and founder-reference personas + schemas"
```

---

## Task 11: README for `tools/callagent/`

**Files:**
- Create: `tools/callagent/README.md`

- [ ] **Step 1: Write the README**

`tools/callagent/README.md`:

````markdown
# callagent

A CLI that lets a shell agent (Claude Code, Codex, any LLM with a Bash tool)
delegate a phone call to a voice agent and receive back a structured transcript.

## Why

A shell agent cannot run a live phone call — voice requires a low-latency LLM
+ TTS + ASR + telephony loop. `callagent` is the delegation primitive: you
give it a persona, a goal, an output schema, and a phone number; it places the
call via a voice-AI provider, waits for it to end, and writes a JSON file
containing the transcript, recording URL, and the structured fields the voice
agent extracted.

## Install

```bash
git clone <repo>
cd tools/callagent
npm install
npm run build
npm install -g .
```

## Provider setup (Vapi v1)

```bash
export VAPI_API_KEY=...
export VAPI_FROM_NUMBER=+15550000000   # provisioned in the Vapi dashboard
```

## Place a call

```bash
callagent place \
  --to "+15551234567" \
  --persona ./personas/cd-screener.md \
  --goal "5-minute screener on accounts-payable pain" \
  --schema ./schemas/cd-screener.schema.json \
  --context ./deal-context.md \
  --consent-token "$(uuidgen)" \
  --output ./calls/run-1.json
```

`callagent` will:
1. Parse the persona, schema, context. Substitute `<VAR>` placeholders with
   keys from your context file's frontmatter.
2. Append the consent token + target + persona + timestamp to a per-output-dir
   JSONL audit log (`<output-dir>/consent-log.jsonl`).
3. Print a banner to stderr and sleep 5 seconds — abort with Ctrl+C if you do
   not have explicit opt-in from the target.
4. POST the assembled `CreateCallDTO` to Vapi.
5. Poll for terminal status, then write the result JSON to `--output`.

## Consent

`--consent-token` is required. The CLI does not interpret its contents — it
only requires that it be non-empty and that you log when you collected it. The
token, target phone number, persona path, and timestamp are appended to a
JSONL audit log on every call placement. If you do not have explicit opt-in
from the target, do not pass a consent token.

`callagent` cannot verify consent on your behalf. The audit log exists so you
have a defensible paper trail if asked.

## Dry-run

```bash
callagent place ... --dry-run
```

Prints the resolved Vapi `CreateCallDTO` to stdout and exits without placing
a call. Use this to inspect the persona, schema, and context interpolation.

## Output shape

```json
{
  "call_id": "vapi_abc123",
  "status": "ended",
  "ended_reason": "hangup",
  "started_at": "2026-04-28T15:00:00Z",
  "ended_at": "2026-04-28T15:05:42Z",
  "duration_seconds": 342,
  "to": "+15551234567",
  "transcript": "AI: Hi, this is ... User: Sure, ...",
  "messages": [{"role": "assistant", "message": "Hi, ...", "time": 0}],
  "recording_url": "https://storage.vapi.ai/.../recording.mp3",
  "structured_data": {"pain_intensity": 7, "pain_quote": "..."},
  "tool_calls": [],
  "provider": "vapi",
  "consent_token": "tok-..."
}
```

## Exit codes

- `0` — call completed; output written
- `1` — provider/network error
- `2` — input validation error (missing/malformed persona, schema, etc.)
- `3` — consent gate refused (missing/empty `--consent-token`)
- `4` — call placed but ended before extraction or polling timeout

## Subcommands

- `callagent place ...` — place an outbound call
- `callagent status <call-id>` — fetch current status as JSON
- `callagent transcript <call-id>` — fetch transcript text only

## Persona file format

Markdown with frontmatter:

```markdown
---
voice: alloy
language: en-US
disclosure_required: true
---

# Persona: <name>

System prompt body. Use `<VAR>` placeholders for context substitution.

## Disclosure
"Hi, I'm an AI assistant calling on behalf of <FIRM>. ..."
```

When `disclosure_required: true`, the disclosure paragraph is set as the
voice agent's `firstMessage`, so it leads the call.

## Output schema

A standard JSON Schema. Becomes the voice agent's structured-extraction
target — the agent must fill these fields before hanging up. Example:

```json
{
  "type": "object",
  "properties": {
    "pain_intensity": { "type": "integer", "minimum": 1, "maximum": 10 },
    "pain_quote": { "type": "string" }
  },
  "required": ["pain_intensity", "pain_quote"]
}
```

## What's deferred

- Mid-call tools (function-calling during the call) — v1 errors if `--tools`
  is supplied; v1.1 will support pre-registered tool IDs via webhook URLs you
  host.
- Inbound calls.
- Multi-language disclosure variants.
- Hosted service / billing — BYO Vapi key only.

## License

MIT
````

- [ ] **Step 2: Commit**

```bash
git add tools/callagent/README.md
git commit -m "Add callagent README"
```

---

## Task 12: Integrate callagent into `customer-discovery` skill

**Files:**
- Modify: `skills/customer-discovery/SKILL.md`

- [ ] **Step 1: Read the current SKILL.md**

```bash
cat skills/customer-discovery/SKILL.md
```

- [ ] **Step 2: Add an optional Step 4 in the `prep` sub-action and an additive input source in the `debrief` sub-action**

In `skills/customer-discovery/SKILL.md`, after the existing Step 3 (Interview script) inside `## Sub-action: prep` and before `### Artifact:`, insert:

```markdown
4. **Optional: place screener calls.** Skip this step entirely if `callagent`
   is not on PATH or if no candidate has explicit opt-in.

   For each candidate in the target list with `opted_in: true`:

   1. Confirm with the VC, per call: "Did <candidate> explicitly opt in to
      this call?" If no, skip.
   2. Generate a consent token (e.g., `uuidgen`).
   3. Run:

      ```bash
      callagent place \
        --to "<candidate-phone>" \
        --persona "$CALLAGENT_HOME/personas/cd-screener.md" \
        --goal "5-minute pain/WTP screener for <ICP segment>" \
        --schema "$CALLAGENT_HOME/schemas/cd-screener.schema.json" \
        --context "deals/<slug>/calls/context.md" \
        --consent-token "<uuid>" \
        --output "deals/<slug>/calls/<candidate-id>.json"
      ```

   `$CALLAGENT_HOME` is the path to the installed `tools/callagent/` (or wherever
   the user installed `callagent`).

   The `context.md` should include frontmatter with `FIRM:`, `COMPANY_DOMAIN:`,
   etc. — these substitute into the persona's `<FIRM>`, `<COMPANY_DOMAIN>`
   placeholders.

   Save each result file under `deals/<slug>/calls/`. The `debrief` sub-action
   will pick them up automatically.
```

In `## Sub-action: debrief` Step 1, change:

```
1. Read transcripts/notes from `deals/<slug>/inputs/` or from VC's pasted text. Each interview becomes one input section.
```

to:

```
1. Read interview material from two sources, treating each as one interview section:
   a. Files under `deals/<slug>/inputs/` (transcripts/notes the VC pasted in)
   b. Files under `deals/<slug>/calls/*.json` (callagent screener-call results, if present)

   For (b), the JSON's `transcript` field provides the conversation text; the
   `structured_data` field pre-fills pain_intensity, pain_quote, current_solution,
   wtp_signal — but you must still cross-reference quotes and write the verdict.
```

- [ ] **Step 3: Run the linter**

```bash
bash scripts/lint-skills.sh
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add skills/customer-discovery/SKILL.md
git commit -m "Add optional callagent integration to customer-discovery skill"
```

---

## Task 13: Integrate callagent into `founder-check` skill

**Files:**
- Modify: `skills/founder-check/SKILL.md`

- [ ] **Step 1: Add an "Optional: reference calls" section after `## After writing`**

Append to `skills/founder-check/SKILL.md`:

```markdown
## Optional: reference calls via `callagent`

Skip this section entirely if `callagent` is not on PATH or if the founder has
not provided a reference list.

The founder MUST supply the reference list — do not synthesize references from
the dossier. Save the reference list at `deals/<slug>/inputs/founder-<name>-references.md`
with at minimum: name, phone (E.164), how the founder knows them, and an
explicit note that the reference has agreed to be contacted.

For each reference:

1. Confirm with the VC: "Did <reference> explicitly opt in to this call?" If
   no, skip.
2. Generate a consent token.
3. Run:

   ```bash
   callagent place \
     --to "<reference-phone>" \
     --persona "$CALLAGENT_HOME/personas/founder-reference.md" \
     --goal "5-minute reference check for <founder name>" \
     --schema "$CALLAGENT_HOME/schemas/founder-reference.schema.json" \
     --context "deals/<slug>/calls/founder-<name>-context.md" \
     --consent-token "<uuid>" \
     --output "deals/<slug>/calls/founder-<name>-ref-<n>.json"
   ```

After all reference calls complete, append a new section to
`deals/<slug>/founder-<name>.md` titled `## Reference checks` that summarizes
each call's `structured_data` (would_work_with_again, key_strengths,
key_concerns) and links to the call result file. Cite the reference's verbatim
quotes from the transcript when stating concerns.

Update `deals/<slug>/manifest.json` with a per-founder
`reference_calls_completed_at` timestamp.
```

- [ ] **Step 2: Run the linter**

```bash
bash scripts/lint-skills.sh
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add skills/founder-check/SKILL.md
git commit -m "Add optional callagent reference-call integration to founder-check skill"
```

---

## Task 14: Manual smoke-test runbook

**Files:**
- Create: `tools/callagent/SMOKE.md`

- [ ] **Step 1: Write the runbook**

`tools/callagent/SMOKE.md`:

````markdown
# callagent smoke test

Run before tagging a release. Not run in CI — this places a real phone call
and costs money.

## Prerequisites

- Vapi account with API key and a provisioned phone number
- A test phone you control
- Yourself, available to answer the test phone

## Steps

1. Set env vars:

   ```bash
   export VAPI_API_KEY=...
   export VAPI_FROM_NUMBER=+1...
   ```

2. From the repo root, build and link:

   ```bash
   cd tools/callagent && npm run build && npm install -g .
   ```

3. Dry-run first to inspect the DTO:

   ```bash
   callagent place \
     --to "+1<your-test-phone>" \
     --persona ./personas/cd-screener.md \
     --goal "smoke test" \
     --schema ./schemas/cd-screener.schema.json \
     --consent-token "smoke-$(date +%s)" \
     --dry-run
   ```

   Expect: JSON CreateCallDTO with persona body in `assistant.model.messages[0].content`,
   schema in `assistant.analysisPlan.structuredDataSchema`, disclosure in `assistant.firstMessage`.

4. Place a real call:

   ```bash
   callagent place \
     --to "+1<your-test-phone>" \
     --persona ./personas/cd-screener.md \
     --goal "smoke test" \
     --schema ./schemas/cd-screener.schema.json \
     --consent-token "smoke-$(date +%s)" \
     --output ./smoke-result.json
   ```

   Expect:
   - Stderr banner with redacted phone, consent hash, audit-log path, 5-second sleep
   - Audit log appears at `./consent-log.jsonl`
   - Phone rings; AI agent leads with the disclosure paragraph
   - When you hang up, polling completes and `smoke-result.json` is written

5. Inspect the result:

   ```bash
   cat smoke-result.json | jq .
   ```

   Expect: status="ended", non-empty transcript, recording_url, structured_data
   matching the schema.

6. Clean up:

   ```bash
   rm smoke-result.json consent-log.jsonl
   ```
````

- [ ] **Step 2: Commit**

```bash
git add tools/callagent/SMOKE.md
git commit -m "Add callagent manual smoke-test runbook"
```

---

## Self-review checklist (verified)

- **Spec coverage:** All seven acceptance criteria from the spec have a task: AC1 (Task 1), AC2 dry-run DTO (Task 6+8), AC3 real call (Task 14), AC4 customer-discovery integration (Task 12), AC5 founder-check integration (Task 13), AC6 README (Task 11), AC7 consent gate (Task 5+8).
- **Placeholder scan:** No "TODO/TBD" in plan tasks; every step has the actual code or command.
- **Type consistency:** `ParsedPersona`, `JsonSchema`, `CallSpec`, `CallRecord`, `Provider` defined once and referenced consistently. `assembleDTO` signature in Task 6 matches the call site in Task 8.
- **Mid-call tools:** Plan ships v1 with `--tools` rejected (Task 8 test asserts exit code 2), matching spec.
- **Consent path resolution:** Task 5 tests cover all three branches (env / output-dir / cwd) the spec requires.
