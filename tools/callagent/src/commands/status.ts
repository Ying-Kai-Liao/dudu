import { getProvider } from "../provider/index.js";

export async function statusCommand(callId: string): Promise<void> {
  const provider = getProvider();
  const rec = await provider.getCall(callId);
  console.log(JSON.stringify(rec, null, 2));
}
