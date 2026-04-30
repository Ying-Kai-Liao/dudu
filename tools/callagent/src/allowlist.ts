export class AllowlistError extends Error {
  exitCode = 2;
  constructor(msg: string) { super(msg); this.name = "AllowlistError"; }
}

export const ALLOWED_NUMBERS: ReadonlyArray<string> = Object.freeze([
  "+61423366127",
  "+61405244282",
  "+61459529124",
]);

export function validateAllowedNumber(to: string | undefined): void {
  if (!to || !ALLOWED_NUMBERS.includes(to)) {
    throw new AllowlistError(
      `--to "${to ?? ""}" is not in the callagent allowlist. ` +
      `For privacy, callagent only places calls to: ${ALLOWED_NUMBERS.join(", ")}.`,
    );
  }
}
