import { ParsedPersona } from "../persona/parse.js";
import { JsonSchema } from "../schema/load.js";
import { VapiProvider } from "./vapi.js";

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
