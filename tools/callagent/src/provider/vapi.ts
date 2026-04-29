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
    const systemMessage = spec.task.body.trim();

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
        voiceId: spec.task.frontmatter.voice ?? "alloy",
      },
      recordingEnabled: spec.record,
      maxDurationSeconds: spec.maxDurationSeconds,
    };

    if (spec.schema) {
      assistant.analysisPlan = { structuredDataSchema: spec.schema };
    }

    if (spec.task.frontmatter.disclosure_required && spec.task.disclosure) {
      assistant.firstMessage = spec.task.disclosure;
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
