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
  task_path: string;
  placed_at: string;
  call_id?: string;
  demo?: boolean;
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
  taskName: string;
  consentTokenHash: string;
  auditLogPath: string;
  abortSeconds: number;
  demo?: boolean;
}): Promise<void> {
  const redactedTo = opts.to.replace(/\d(?=\d{4})/g, "*");
  const demoTag = opts.demo ? "[DEMO MODE] " : "";
  process.stderr.write(
    `[callagent] ${demoTag}Placing call to ${redactedTo} with task ${opts.taskName}.\n` +
    `[callagent] Consent token: ${opts.consentTokenHash}. Audit log: ${opts.auditLogPath}.\n` +
    `[callagent] ${demoTag}If you do not have explicit opt-in from this target, abort now (Ctrl+C).\n` +
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
