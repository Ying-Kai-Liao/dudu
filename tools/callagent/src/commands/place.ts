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
import { VapiProvider } from "../provider/vapi.js";
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
    return new VapiProvider({ apiKey: "stub", fromNumber: "+10000000000" });
  }
}
