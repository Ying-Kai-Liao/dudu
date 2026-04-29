# callagent — design spec

**Status:** draft
**Date:** 2026-04-28
**Owner:** Ying-Kai Liao
**Repo:** lives in this repo at `tools/callagent/` (extractable later)

## TL;DR

`callagent` is a CLI that lets a shell agent (Claude Code, Codex) **delegate a phone call to a voice agent**. The shell agent passes a persona, goal, optional mid-call tools, and an output schema. `callagent` places the call via a voice-AI provider (Vapi in v1), waits for it to end, and returns a JSON object containing the transcript, recording URL, and the structured fields the voice agent extracted.

It is built **specifically for dudu first**: the persona templates, output schemas, and deal-folder integration are tuned for VC customer-discovery screener calls and founder reference checks. The boundary inside the repo is clean enough that the tool can be extracted later as a standalone product.

## Why

The shell agent driving dudu skills cannot be on a phone call in realtime. Voice requires a different agent (low-latency LLM + TTS + ASR + telephony) running autonomously for the duration of the call. The shell agent's only job is to brief that voice agent thoroughly enough that it can run unsupervised, then read the result.

`callagent` is the delegation primitive that crosses that boundary cleanly.

## Positioning inside dudu

Two skills get an **optional** integration:

- **`customer-discovery` (prep)** — after generating the target list and outreach drafts, optionally place screener calls to opted-in candidates. Their transcripts and extracted data feed `customer-discovery` (debrief).
- **`founder-check`** — optionally place reference-check calls to references the founder has explicitly listed. Transcripts feed the founder dossier.

Both skills must continue to work when `callagent` is **not** installed. The skill text describes the optional path conditionally: "If `callagent` is on PATH and the VC has confirmed consent, you may run …".

## Non-goals (v1)

- Hosted service / billing / phone-number pooling — BYO Vapi key only
- Inbound calls
- Multi-turn scheduling, follow-up sequences, voicemail navigation
- Cold-calling targets without prior opt-in (consent gate forbids this)
- Generic-purpose distribution outside dudu (the wrapper interface is generic; the personas, schemas, and skill integration are not)

## The contract

### CLI surface

```
callagent place \
  --to             <E.164 phone number>          # required
  --persona        <path-to-persona-md>          # required
  --goal           <one-sentence string>         # required
  --schema         <path-to-output-schema-json>  # required
  --tools          <path-to-tools-json>          # optional, see "Mid-call tools" — v1 errors if non-empty
  --context        <path-to-context-md>          # optional, injected into system prompt
  --max-duration   <seconds>                     # optional, default 600 (10 min)
  --record         <true|false>                  # optional, default true
  --dry-run                                      # optional, prints the resolved CreateCallDTO and exits
  --output         <path-to-output-json>         # optional, default ./call-<id>.json
  --consent-token  <opaque string>               # required — see "Consent gate"

callagent status <call-id>                       # poll a previously placed call
callagent transcript <call-id>                   # fetch transcript for a completed call
```

Exit codes:
- `0` — call completed and transcript+structured data written to `--output`
- `1` — provider error (network, auth, telephony failure)
- `2` — input validation error (missing persona, bad schema, etc.)
- `3` — consent gate refused (missing/invalid `--consent-token`)
- `4` — call placed but failed before extraction (no-answer, hangup-before-data)

### Input formats

**`persona.md`** — markdown with optional frontmatter:

```markdown
---
voice: alloy           # provider voice ID
language: en-US
disclosure_required: true
---

# Persona: VC customer-discovery screener

You are an AI assistant calling on behalf of <FIRM>. Begin every call with the disclosure
statement below. If the recipient asks to end the call at any point, do so immediately.

## Disclosure
"Hi, I'm an AI assistant calling on behalf of <FIRM>. This call is being recorded for
research purposes. Is now still a good time for a 5-minute conversation?"

## Style
- Conversational, not interview-heavy
- Never sell, never pitch
- One question at a time, listen for ≥3 seconds before following up
```

The persona file is the system prompt for the voice agent. Variables in `<ANGLE_BRACKETS>` are filled from `--context` (or stay literal if no context provided).

**`schema.json`** — JSON Schema describing the fields the voice agent must extract before hanging up. This becomes Vapi's `analysisPlan.structuredDataSchema`. Example for a CD screener:

```json
{
  "type": "object",
  "properties": {
    "pain_intensity": {"type": "integer", "minimum": 1, "maximum": 10},
    "pain_quote": {"type": "string"},
    "current_solution": {"type": "string"},
    "wtp_signal": {"type": "string"},
    "willing_to_meet_vc": {"type": "boolean"}
  },
  "required": ["pain_intensity", "pain_quote", "current_solution", "wtp_signal", "willing_to_meet_vc"]
}
```

**`tools.json`** *(v1.1 — see Mid-call tools)* — array of Vapi-shaped tool definitions.

**`context.md`** — markdown injected after the persona system prompt, describing deal-specific context the voice agent needs (company name, ICP, what the firm does).

### Output format

`call-<id>.json`:

```json
{
  "call_id": "vapi_abc123",
  "status": "completed",
  "ended_reason": "hangup",
  "started_at": "2026-04-28T15:00:00Z",
  "ended_at": "2026-04-28T15:05:42Z",
  "duration_seconds": 342,
  "to": "+15551234567",
  "transcript": "AI: Hi, this is ... User: Sure, ...",
  "messages": [
    {"role": "assistant", "message": "Hi, ...", "time": 0.0},
    {"role": "user", "message": "Sure, ...", "time": 4.2}
  ],
  "recording_url": "https://storage.vapi.ai/.../recording.mp3",
  "structured_data": { /* matches the input schema */ },
  "tool_calls": [],
  "provider": "vapi",
  "consent_token": "..."
}
```

The shell agent reads this file and feeds it to the appropriate dudu skill.

## Mid-call tools — what v1 ships

v1 **disables** custom mid-call tools. Reason: they require a publicly-reachable webhook server to receive Vapi's tool-call POSTs, and standing one up reliably from a CLI is the messy part of the build (tunnel setup, lifecycle, auth). Persona + structured extraction at end-of-call covers the dudu use cases without it.

**v1 behavior:** if `--tools` is supplied and non-empty, error with exit code 2 and message: "Mid-call tools are not supported in callagent v1. See docs/callagent/v1.1-tools.md for the v1.1 plan."

**v1.1 plan (deferred):** support **pre-registered tools by ID** — the user registers a tool once via `callagent tool create`, supplying a public webhook URL they host (their own service, their own auth). `callagent place --tools` then accepts a list of tool IDs to attach. The CLI never hosts webhooks itself.

## Provider abstraction

v1 ships **Vapi only**. The provider is selected by `CALLAGENT_PROVIDER` env var (default `vapi`). The internal interface is a single `Provider` class with three methods: `placeCall(spec) → callId`, `getCall(callId) → callRecord`, `pollUntilTerminal(callId, timeout)`. Adding Bland or Retell later means writing one more class, no contract change.

Auth: `VAPI_API_KEY` env var. The CLI errors with a clear message if missing.

## Consent gate

`--consent-token` is **required**. It is an opaque string the dudu skill writes to a per-deal log when the VC explicitly confirms consent for a specific call. The CLI does not interpret the token's contents; it only requires that it be non-empty and present. The token's *purpose* is to make the dudu skill text say:

> "Before placing this call, confirm with the VC: (1) the target opted in to this call, (2) the disclosure language is appropriate for the target's jurisdiction, (3) the recording is acceptable. On 'yes', generate a consent token and pass it to callagent."

This is a **soft gate** — the CLI cannot verify the VC actually got consent — but it makes consent a first-class artifact of every call placement. The token + persona + target + timestamp are appended to a JSONL audit log. The CLI resolves the audit-log path in this order: `CALLAGENT_AUDIT_LOG` env var → `--output`'s parent directory + `consent-log.jsonl` → `./consent-log.jsonl` in cwd. So when dudu invokes with `--output deals/<slug>/calls/cand-1.json`, the audit log lands at `deals/<slug>/calls/consent-log.jsonl` automatically.

The CLI also writes a banner to stderr on every `place`:

```
[callagent] Placing call to <REDACTED> with persona <name>.
[callagent] Consent token: <hash>. Audit log: deals/<slug>/calls/consent-log.jsonl.
[callagent] If you do not have explicit opt-in from this target, abort now (Ctrl+C).
[callagent] Sleeping 5s before placing call.
```

Five-second abort window before the API call goes out.

## Repository layout

```
tools/callagent/
├── package.json
├── tsconfig.json
├── README.md                    # standalone — does NOT mention dudu
├── src/
│   ├── cli.ts                   # entry, arg parsing, dispatch
│   ├── place.ts                 # `place` subcommand
│   ├── status.ts                # `status` subcommand
│   ├── transcript.ts            # `transcript` subcommand
│   ├── consent.ts               # consent token validation, audit-log append
│   ├── provider/
│   │   ├── index.ts             # Provider interface + factory
│   │   └── vapi.ts              # Vapi implementation
│   └── persona/
│       └── parse.ts             # parse persona.md frontmatter + body
├── personas/                    # dudu-tuned defaults
│   ├── cd-screener.md
│   └── founder-reference.md
├── schemas/                     # dudu-tuned default output schemas
│   ├── cd-screener.schema.json
│   └── founder-reference.schema.json
└── test/
    ├── place.test.ts
    └── fixtures/
```

`tools/callagent/` has its own `package.json` and is build-able / runnable independently of the rest of the repo. It does **not** import from `skills/` or `lib/`. The only repo-coupling: the default audit-log path (`deals/<slug>/calls/consent-log.jsonl`) follows dudu's deal-folder convention. That coupling is encoded as a documented default that callers can override via `CALLAGENT_AUDIT_LOG` env var.

## Build choices

- **Language:** TypeScript / Node 20+
- **Bundler:** `tsup` to a single CommonJS file in `dist/`
- **Bin:** `callagent` published as a `bin` entry in `package.json`
- **Local install during dev:** `npm install -g ./tools/callagent` so `callagent` is on PATH when running dudu skills locally
- **Test runner:** `vitest`
- **HTTP client:** `fetch` (Node 20+ native)
- **Schema validation:** `ajv` for `--schema` JSON Schema validation against the structured-data response

## dudu skill integration

### `customer-discovery` (prep) — additive optional step

After Step 3 (interview script), add a new optional Step 4: "Place screener calls". Conditional on:
1. `callagent` is on PATH
2. The VC explicitly enabled call placement for this deal
3. At least one candidate in the target list has marker `opted_in: true`

For each opted-in candidate:
1. Confirm consent with the VC (per-call)
2. Generate consent token (UUID)
3. Run `callagent place --to ... --persona personas/cd-screener.md --schema schemas/cd-screener.schema.json --context <deal-context.md> --consent-token <token> --output deals/<slug>/calls/<candidate-id>.json`
4. Append the call result file to a list passed to the debrief sub-action

The skill text says clearly: "Skip this step if `callagent` is not installed or if you have not collected opt-ins."

### `customer-discovery` (debrief) — additive input source

The debrief step already reads `deals/<slug>/inputs/`. Extend it to also read `deals/<slug>/calls/*.json`. Each call's `transcript` becomes one interview section; the `structured_data` pre-fills the pain/WTP/current-solution rows in the debrief artifact (the agent still cross-references with quotes and writes the verdict).

### `founder-check` — additive optional step

After the dossier is written, optional reference-call step:
1. The founder must have provided a reference list (separate input, not synthesized).
2. For each reference: VC confirms reference opted in to a 5-minute call.
3. `callagent place --persona personas/founder-reference.md --schema schemas/founder-reference.schema.json …`
4. Reference-call results saved under `deals/<slug>/calls/founder-<name>-ref-<n>.json` and folded into the dossier under a new "Reference checks" section.

### Default personas + schemas (ships with the CLI)

**`personas/cd-screener.md`** — 5-minute pain/WTP/objection screener. Disclosure-first. Hangs up cleanly on objection.

**`schemas/cd-screener.schema.json`** — pain_intensity (1-10), pain_quote, current_solution, wtp_signal, willing_to_meet_vc, top_objection.

**`personas/founder-reference.md`** — reference call: career working-relationship, integrity, judgment-under-pressure, would-they-hire-again. Refuses to share the founder's pitch or pressure the reference.

**`schemas/founder-reference.schema.json`** — relationship_context, working_dates, key_strengths (≤3), key_concerns (≤3), would_work_with_again (yes/no/qualified), reference_quality (high/medium/low based on specificity).

## Test plan

- **Unit tests:** persona parsing, consent-log append, schema validation against fixtures, Vapi DTO assembly (no network)
- **Integration test:** `--dry-run` against a sample call spec; assert the resolved Vapi `CreateCallDTO` matches a snapshot
- **Smoke test:** one real call to a Vapi test number with a tiny persona and schema; assert the response shape end-to-end. Run manually before tagging releases, not in CI.

## Failure modes the design handles

- **No `VAPI_API_KEY`:** exit 2 with clear message
- **Persona / schema file missing or malformed:** exit 2 with line of validation error
- **Mid-call tools requested:** exit 2, point at v1.1 plan
- **Network failure during `place`:** exit 1, no consent log entry written (so retry doesn't double-log)
- **Call placed but ended before extraction:** exit 4, partial output (transcript only, `structured_data: null`)
- **Polling timeout exceeds `--max-duration`:** exit 4 with a status URL the user can hit later
- **Consent token missing / empty:** exit 3

## Open questions for user review

1. **Phone number provisioning.** Vapi requires a registered "from" number. v1 reads `VAPI_FROM_NUMBER` env var (the user provisions this once in the Vapi dashboard). Acceptable, or do you want the CLI to provision automatically on first run?
2. **Recording disclosure language.** v1 ships a US-conservative default ("This call is being recorded …"). Should we ship jurisdiction-aware variants, or punt to v1.1?
3. **Audit log location.** Default `deals/<slug>/calls/consent-log.jsonl` assumes the CLI is invoked from a dudu repo. Override env var: good. Should the CLI also write to a per-user log at `~/.callagent/audit.log` for cross-deal traceability?
4. **Provider abstraction now or later?** The Provider interface exists in the spec, but v1 ships only Vapi. Worth implementing the indirection for one provider, or inline Vapi and refactor when a second provider arrives?

## What this spec deliberately leaves out

- Exact UI text for the consent confirmation prompt in each skill (lives in skill text, drafted alongside implementation)
- The `dist/` packaging and npm-publish flow (out of scope for hackathon-private repo)
- Retry / idempotency keys for partially-failed calls (deferred to v1.1)
- Multi-language support (v1 is English-only)

## Acceptance criteria for v1

1. `callagent --version` prints version
2. `callagent place --dry-run …` with a `--task <path>` and a sample task brief emits a valid Vapi `CreateCallDTO` where: (a) the task body is the system message in `model.messages`, (b) the schema (when supplied via `--schema`) is `analysisPlan.structuredDataSchema`, (c) when `disclosure_required: true` in the task frontmatter, the disclosure paragraph is also set as `firstMessage`
3. With a real `VAPI_API_KEY` and `VAPI_FROM_NUMBER`, a real call to a test number returns a `call-<id>.json` matching the documented output shape
4. `customer-discovery` skill text describes the optional callagent integration and works unchanged when `callagent` is not installed
5. `founder-check` skill text describes the optional reference-call integration and works unchanged when `callagent` is not installed
6. `tools/callagent/README.md` documents standalone usage with no dudu dependency
7. Consent gate: missing/empty `--consent-token` → exit 3 with audit-log-line documentation in the error
