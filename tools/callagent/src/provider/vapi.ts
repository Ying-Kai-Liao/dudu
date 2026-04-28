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
