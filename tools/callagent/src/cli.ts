import { Command } from "commander";
import { placeCommand } from "./commands/place.js";
import { statusCommand } from "./commands/status.js";
import { transcriptCommand } from "./commands/transcript.js";

const program = new Command();
program
  .name("callagent")
  .description("Delegate a phone call to a voice agent.")
  .version("0.1.0");

program
  .command("place")
  .description("Place an outbound call and return a structured transcript.")
  .requiredOption("--to <e164>", "phone number in E.164 format")
  .requiredOption("--persona <path>", "path to persona markdown file")
  .requiredOption("--goal <string>", "one-sentence call goal")
  .requiredOption("--schema <path>", "path to JSON Schema for structured extraction")
  .requiredOption("--consent-token <token>", "opaque consent token from caller")
  .option("--tools <path>", "path to tools JSON (v1 errors if non-empty)")
  .option("--context <path>", "path to context markdown injected into the system prompt")
  .option("--max-duration <seconds>", "max call duration", (v) => parseInt(v, 10), 600)
  .option("--record <bool>", "record the call", (v) => v !== "false", true)
  .option("--dry-run", "print the resolved CreateCallDTO and exit", false)
  .option("--output <path>", "where to write the result JSON")
  .action(async (opts) => {
    try { await placeCommand(opts); }
    catch (e: any) { console.error(e.message); process.exit(e.exitCode ?? 1); }
  });

program
  .command("status <callId>")
  .description("Fetch current status of a previously placed call.")
  .action(async (callId) => {
    try { await statusCommand(callId); }
    catch (e: any) { console.error(e.message); process.exit(e.exitCode ?? 1); }
  });

program
  .command("transcript <callId>")
  .description("Fetch transcript of a completed call.")
  .action(async (callId) => {
    try { await transcriptCommand(callId); }
    catch (e: any) { console.error(e.message); process.exit(e.exitCode ?? 1); }
  });

program.parseAsync();
