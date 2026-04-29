import { readFile } from "node:fs/promises";
import { createInterface } from "node:readline/promises";
import { parseTask } from "../task/parse.js";
import { loadSchema } from "../schema/load.js";
import { buildSystemMessage } from "../system-message.js";
import { CallSpec } from "../provider/index.js";

export interface SimulateOptions {
  task: string;
  context?: string;
  schema?: string;
  model: string;
}

interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

const OPENAI_BASE = "https://api.openai.com/v1";

export async function simulateCommand(opts: SimulateOptions): Promise<void> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    const e: any = new Error("OPENAI_API_KEY not set. Add it to tools/callagent/.env or export it.");
    e.exitCode = 2;
    throw e;
  }

  const contextStr = opts.context ? await readFile(opts.context, "utf8") : undefined;
  const ctxVars = parseContextVars(contextStr);
  const task = await parseTask(opts.task, ctxVars);
  const schema = opts.schema ? await loadSchema(opts.schema) : undefined;

  const spec: CallSpec = {
    to: "+10000000000",
    task,
    schema,
    context: contextStr,
    maxDurationSeconds: 600,
    record: false,
  };

  const systemMessage = buildSystemMessage(spec);
  const history: ChatMessage[] = [{ role: "system", content: systemMessage }];
  if (contextStr) history.push({ role: "system", content: contextStr });

  process.stderr.write(
    `[callagent simulate] Text-mode call against ${opts.model}.\n` +
    `[callagent simulate] You play the recipient. Slash commands:\n` +
    `[callagent simulate]   /end           finish and run schema extraction (if --schema given)\n` +
    `[callagent simulate]   /quit          abort without extraction\n` +
    `[callagent simulate]   /show-system   print the system prompt the agent received\n` +
    `[callagent simulate]   /show-history  print the message history so far\n` +
    `\n`,
  );

  // If disclosure_required, agent's first turn is the disclosure verbatim.
  if (task.frontmatter.disclosure_required && task.disclosure) {
    process.stdout.write(`[Agent] ${task.disclosure}\n\n`);
    history.push({ role: "assistant", content: task.disclosure });
  }

  const rl = createInterface({ input: process.stdin, output: process.stdout });

  while (true) {
    const userInput = (await rl.question("[You] ")).trim();
    if (!userInput) continue;

    if (userInput === "/quit") {
      process.stderr.write(`\n[callagent simulate] Aborted. No extraction run.\n`);
      rl.close();
      return;
    }
    if (userInput === "/end") {
      break;
    }
    if (userInput === "/show-system") {
      process.stderr.write(`\n--- system prompt ---\n${systemMessage}\n--- end system ---\n\n`);
      continue;
    }
    if (userInput === "/show-history") {
      process.stderr.write(`\n--- history ---\n${JSON.stringify(history, null, 2)}\n--- end history ---\n\n`);
      continue;
    }

    history.push({ role: "user", content: userInput });
    const reply = await callOpenAI(apiKey, opts.model, history);
    history.push({ role: "assistant", content: reply });
    process.stdout.write(`\n[Agent] ${reply}\n\n`);
  }

  rl.close();

  if (schema) {
    process.stderr.write(`\n[callagent simulate] Running structured extraction…\n`);
    const extracted = await extractStructuredData(apiKey, opts.model, history, schema);
    process.stdout.write(`\n--- extracted ---\n${JSON.stringify(extracted, null, 2)}\n--- end extracted ---\n`);
  } else {
    process.stderr.write(`\n[callagent simulate] No --schema given. Skipping extraction.\n`);
  }

  process.stderr.write(`\n[callagent simulate] Done. ${history.filter(m => m.role !== "system").length} turns.\n`);
}

async function callOpenAI(apiKey: string, model: string, messages: ChatMessage[]): Promise<string> {
  const res = await fetch(`${OPENAI_BASE}/chat/completions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model, messages, temperature: 0.7 }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`OpenAI chat/completions failed (${res.status}): ${text}`);
  }
  const data = (await res.json()) as { choices: Array<{ message: { content: string } }> };
  return data.choices[0].message.content;
}

async function extractStructuredData(
  apiKey: string,
  model: string,
  history: ChatMessage[],
  schema: Record<string, unknown>,
): Promise<unknown> {
  const transcript = history
    .filter((m) => m.role !== "system")
    .map((m) => `${m.role === "assistant" ? "Agent" : "Recipient"}: ${m.content}`)
    .join("\n");

  const extractionMessages: ChatMessage[] = [
    {
      role: "system",
      content:
        "You are extracting structured data from the transcript of a call you just ran. " +
        "Fill in the schema based ONLY on what was actually said. Use null/empty values when " +
        "the transcript does not support a confident value. Do not invent data.",
    },
    { role: "user", content: `Transcript:\n${transcript}` },
  ];

  const res = await fetch(`${OPENAI_BASE}/chat/completions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages: extractionMessages,
      response_format: {
        type: "json_schema",
        json_schema: { name: "extraction", schema, strict: false },
      },
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`OpenAI extraction failed (${res.status}): ${text}`);
  }
  const data = (await res.json()) as { choices: Array<{ message: { content: string } }> };
  return JSON.parse(data.choices[0].message.content);
}

function parseContextVars(ctx: string | undefined): Record<string, string> {
  if (!ctx) return {};
  const out: Record<string, string> = {};
  const m = ctx.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return out;
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^([A-Z_][A-Z0-9_]*):\s*(.+)$/);
    if (kv) out[kv[1]] = kv[2].trim();
  }
  return out;
}
