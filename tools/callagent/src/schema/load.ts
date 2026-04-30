import { readFile } from "node:fs/promises";
import Ajv from "ajv";

const ajv = new Ajv({ strict: false });

export type JsonSchema = Record<string, unknown>;

export async function loadSchema(path: string): Promise<JsonSchema> {
  const raw = await readFile(path, "utf8");
  let parsed: JsonSchema;
  try {
    parsed = JSON.parse(raw);
  } catch (e: any) {
    throw new Error(`Failed to parse schema JSON at ${path}: ${e.message}`);
  }
  try {
    ajv.compile(parsed);
  } catch (e: any) {
    throw new Error(`Invalid JSON Schema at ${path}: ${e.message}`);
  }
  return parsed;
}
