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
