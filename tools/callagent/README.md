# callagent

Delegate a phone call to a voice agent. Hand it a task brief, get back a structured transcript.

callagent is the calling rails, not the agent. You write a `task.md` that tells the voice agent what to do — the same way you would brief any capable assistant — and the underlying LLM figures out execution. callagent handles the Vapi plumbing, the consent gate, polling until the call ends, and writing the output JSON.

---

## Why

Most outbound call workflows require you to pre-configure personas, slot schemas, and call scripts inside a provider dashboard. callagent inverts this: the task brief is a plain markdown file you version-control alongside your code. Iterate on it with `simulate` (text REPL, no phone, costs cents) until the agent behaves correctly, then `place` to dial a real number.

---

## Install

Requires Node 20+.

```bash
cd tools/callagent
npm install
npm run build
```

After building, the binary is at `dist/cli.cjs`. Add it to your PATH or invoke it directly:

```bash
node dist/cli.cjs --help
# or, if linked:
callagent --help
```

---

## .env setup

Create `tools/callagent/.env` (already gitignored). Variables are loaded automatically via dotenv.

```dotenv
# Required for `simulate`
OPENAI_API_KEY=sk-...

# Required for `place`
VAPI_API_KEY=...
VAPI_FROM_NUMBER=+15550001234    # E.164 format, must be provisioned in Vapi
```

Optional:

```dotenv
CALLAGENT_AUDIT_LOG=/var/log/callagent/consent.jsonl   # override audit log location
CALLAGENT_PROVIDER=vapi                                 # default; only vapi is supported in v1
```

---

## Quick start: simulate first (recommended)

`simulate` runs an interactive text-mode REPL against OpenAI using the same task brief that `place` will send to Vapi. You play the call recipient. There is no phone, no Vapi account needed, and each session costs a fraction of a real call.

**1. Write a task brief** (see [Task brief format](#task-brief-format) below for the full spec):

```markdown
# tasks/reference-check.md
---
voice: alloy
language: en-US
disclosure_required: true
---

# Task

You are an AI assistant calling on behalf of <FIRM> to do a professional reference check
for <CANDIDATE>. You want to understand their working style, strengths, and any areas
for growth. Be conversational, not interrogative.

## Disclosure
"Hi, I'm an AI assistant calling on behalf of <FIRM>. This is a reference check for
<CANDIDATE>. The call may be recorded. Is now a good time?"

## How to handle this
- Start with open-ended questions
- Probe for specific examples, not generalities
- End by asking if there is anything else the reference would want to share

## Hard rules
- Do not ask for salary history
- Do not ask about protected characteristics
- If the reference declines, thank them and end the call
```

**2. Write a context file** (provides variable substitution):

```markdown
# contexts/acme-candidate.md
---
FIRM: Acme Corp
CANDIDATE: Jane Smith
---
```

**3. Run simulate:**

```bash
callagent simulate \
  --task tasks/reference-check.md \
  --context contexts/acme-candidate.md
```

Slash commands available during the REPL:

| Command | Effect |
|---|---|
| `/end` | End the call and run schema extraction (if `--schema` given) |
| `/quit` | Abort without extraction |
| `/show-system` | Print the system prompt the agent received |
| `/show-history` | Print the full message history |

**4. Optionally add a schema** to test structured extraction:

```bash
callagent simulate \
  --task tasks/reference-check.md \
  --context contexts/acme-candidate.md \
  --schema schemas/reference-check.json
```

Type `/end` when the simulated call is done. callagent will run extraction against the transcript and print the structured result.

---

## Place a real call

Once simulate behaves the way you want, replace `simulate` with `place`:

```bash
callagent place \
  --to +15559876543 \
  --task tasks/reference-check.md \
  --context contexts/acme-candidate.md \
  --consent-token "ref-check-jane-smith-2026-04-28" \
  --schema schemas/reference-check.json \
  --output ./results/call-jane-smith.json
```

`place` will:

1. Validate the consent token (non-empty required).
2. Append an audit log entry to `consent-log.jsonl` (same directory as `--output`, or `CALLAGENT_AUDIT_LOG`).
3. Print a five-second abort banner to stderr — press Ctrl+C to cancel before the call goes out.
4. Place the call via Vapi and poll until it ends.
5. Write the result JSON to `--output` (defaults to `./call-<id>.json`).

**Dry-run** to inspect the Vapi `CreateCallDTO` without making a network call:

```bash
callagent place \
  --to +15559876543 \
  --task tasks/reference-check.md \
  --consent-token "preview" \
  --dry-run
```

---

## Task brief format

Task briefs are markdown files with optional YAML frontmatter. There are no required sections and no bundled templates — write whatever the agent needs to know.

```markdown
---
voice: alloy          # OpenAI voice ID (default: alloy)
language: en-US       # BCP-47 language tag (default: en-US)
disclosure_required: true   # if true, agent leads with the Disclosure section verbatim
---

# Task

You are calling on behalf of <FIRM>... [free-form brief]

## Disclosure
"Hi, I'm an AI assistant calling on behalf of <FIRM>. [rest of disclosure]"

## How to handle this
[methodology, tone, probing technique]

## Hard rules
[non-negotiables — things the agent must never do]
```

### Variable substitution

Uppercase tokens in `<ANGLE_BRACKETS>` are replaced from the YAML frontmatter of the `--context` file:

```markdown
# contexts/my-context.md
---
FIRM: Acme Corp
CANDIDATE: Jane Smith
TARGET_ROLE: Senior Engineer
---
```

Any `<FIRM>`, `<CANDIDATE>`, or `<TARGET_ROLE>` in the task body is replaced before the brief is sent to the agent. Tokens with no matching key are left as-is.

### Disclosure handling

If `disclosure_required: true`, callagent extracts the content of the `## Disclosure` section and:

- In `simulate`: prints it as the agent's first turn before the REPL starts.
- In `place` (Vapi): sets it as `assistant.firstMessage`, so the agent always leads with disclosure before the LLM takes over.

---

## Output format

`place` writes a JSON file on success. Shape:

```json
{
  "call_id": "abc-123",
  "status": "ended",
  "ended_reason": "customer-ended-call",
  "started_at": "2026-04-28T12:00:00.000Z",
  "ended_at": "2026-04-28T12:07:32.000Z",
  "duration_seconds": 452,
  "to": "+15559876543",
  "transcript": "Agent: Hi, I'm an AI...\nRecipient: ...",
  "messages": [
    { "role": "assistant", "message": "Hi, I'm an AI...", "time": 0 }
  ],
  "recording_url": "https://...",
  "structured_data": {
    "pain_intensity": 8,
    "pain_quote": "We spend two days a week on this."
  },
  "tool_calls": [],
  "provider": "vapi",
  "consent_token": "ref-check-jane-smith-2026-04-28"
}
```

`structured_data` is `null` if no `--schema` was given or if Vapi did not return an extraction result. `recording_url` is `null` if `--record false` was passed.

---

## Subcommand reference

### `callagent place`

Places an outbound call via Vapi and polls until it ends.

| Flag | Required | Default | Description |
|---|---|---|---|
| `--to <e164>` | yes | — | Destination phone number in E.164 format |
| `--task <path>` | yes | — | Path to task markdown briefing |
| `--consent-token <token>` | yes | — | Opaque token proving caller has opt-in |
| `--context <path>` | no | — | Context markdown; frontmatter supplies substitution variables |
| `--schema <path>` | no | — | JSON Schema for end-of-call structured extraction |
| `--max-duration <seconds>` | no | `600` | Maximum call duration |
| `--record <bool>` | no | `true` | Whether to record the call |
| `--dry-run` | no | `false` | Print the Vapi DTO and exit without placing the call |
| `--output <path>` | no | `./call-<id>.json` | Where to write the result JSON |
| `--tools <path>` | no | — | Not supported in v1 (see [What's not in v1](#whats-not-in-v1)) |

### `callagent status <call-id>`

Fetches the current status of a previously placed call. Prints the full `CallRecord` JSON to stdout.

```bash
callagent status abc-123
```

Requires `VAPI_API_KEY` in env.

### `callagent transcript <call-id>`

Fetches the transcript of a completed call. Prints the transcript string to stdout (empty string if not yet available).

```bash
callagent transcript abc-123
```

Requires `VAPI_API_KEY` in env.

### `callagent simulate`

Runs an interactive text-mode REPL against OpenAI using the task brief.

| Flag | Required | Default | Description |
|---|---|---|---|
| `--task <path>` | yes | — | Path to task markdown briefing |
| `--context <path>` | no | — | Context markdown for variable substitution |
| `--schema <path>` | no | — | JSON Schema; extraction runs when you type `/end` |
| `--model <id>` | no | `gpt-4o` | OpenAI model ID |

Requires `OPENAI_API_KEY` in env.

---

## Consent gate

Every `place` call requires `--consent-token`. The token is opaque — callagent does not interpret it. It is your responsibility to ensure the call recipient has given informed consent before you run `place`.

What callagent does with the token:

1. Rejects the command if the token is missing or empty (exit code 3).
2. Appends a JSONL line to the audit log before the call is placed:

```json
{"consent_token":"ref-check-jane-smith-2026-04-28","to":"+15559876543","task_path":"/abs/path/tasks/reference-check.md","placed_at":"2026-04-28T12:00:00.000Z"}
```

3. Prints a five-second abort banner to stderr (to and consent token hash are shown; the raw token is not logged to stderr).

The audit log location resolves as:

- `CALLAGENT_AUDIT_LOG` env var if set.
- Otherwise `consent-log.jsonl` in the same directory as `--output`.
- Otherwise `./consent-log.jsonl` in the current working directory.

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Provider or network error |
| `2` | Input validation error (bad flag, missing env var, unsupported feature) |
| `3` | Consent gate refused (missing or empty `--consent-token`) |
| `4` | Call ended without extraction, or polling timed out |

---

## What's not in v1

**Mid-call tools** — `--tools` is accepted as a flag but errors if the file contains a non-empty array. The v1.1 design is documented in `docs/callagent/v1.1-tools.md`.

**Hosted service** — callagent is a local CLI. There is no API server, webhook endpoint, or queue in v1.

**Multi-language disclosure** — the `language` frontmatter field is passed to Vapi but callagent does not validate or translate the disclosure text. That is the task author's responsibility.

**Bundled task templates** — v1 ships zero domain content. All task briefs are authored by the caller.

---

## License

MIT
