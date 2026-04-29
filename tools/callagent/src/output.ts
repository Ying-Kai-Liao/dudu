import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { CallRecord } from "./provider/index.js";

export async function writeCallResult(
  path: string,
  record: CallRecord & { consent_token: string },
): Promise<void> {
  const abs = resolve(path);
  await mkdir(dirname(abs), { recursive: true });
  await writeFile(abs, JSON.stringify(record, null, 2), "utf8");
}
