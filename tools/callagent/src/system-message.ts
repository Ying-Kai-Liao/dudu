import { CallSpec } from "./provider/index.js";

/**
 * Build the system message string fed to the underlying LLM, same
 * shape used for both real Vapi calls and local simulate-mode REPL.
 */
export function buildSystemMessage(spec: CallSpec): string {
  return spec.task.body.trim();
}
