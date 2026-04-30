import { getProvider } from "../provider/index.js";

export async function transcriptCommand(callId: string): Promise<void> {
  const provider = getProvider();
  const rec = await provider.getCall(callId);
  console.log(rec.transcript ?? "");
}
