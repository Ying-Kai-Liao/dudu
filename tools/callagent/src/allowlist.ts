export class AllowlistError extends Error {
  exitCode = 2;
  constructor(msg: string) { super(msg); this.name = "AllowlistError"; }
}

const DEFAULT_ALLOWED_NUMBERS: ReadonlyArray<string> = Object.freeze([
  "+61423366127",
  "+61405244282",
  "+61459529124",
]);

export function getAllowedNumbers(env: NodeJS.ProcessEnv = process.env): string[] {
  const override = env.CALLAGENT_ALLOWED_NUMBERS;
  if (override && override.trim()) {
    return override
      .split(",")
      .map((n) => n.trim())
      .filter((n) => n.length > 0);
  }
  return [...DEFAULT_ALLOWED_NUMBERS];
}

export function validateAllowedNumber(
  to: string | undefined,
  env: NodeJS.ProcessEnv = process.env,
): void {
  const allowed = getAllowedNumbers(env);
  if (!to || !allowed.includes(to)) {
    throw new AllowlistError(
      `--to "${to ?? ""}" is not in the callagent allowlist. ` +
      `For privacy, callagent only places calls to pre-approved numbers. ` +
      `Allowed: ${allowed.join(", ")}. ` +
      `Override the list by setting CALLAGENT_ALLOWED_NUMBERS to a comma-separated list of E.164 numbers.`,
    );
  }
}
