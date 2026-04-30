---
name: place-call
description: Place one outbound voice call via callagent for a deal under evaluation. Authors the task brief from the deal context, optionally simulates first, dials, and writes the result + audit-log entry to deals/<slug>/calls/. Privacy allowlist enforced. Pass --demo to route to the test allowlist for end-to-end smoke without an opted-in target.
---

# Place call

One outbound voice call delegated to `callagent`. Read `lib/research-protocol.md` for source-honesty rules and `tools/callagent/README.md` for `callagent`'s flag surface before starting.

## What this skill IS and IS NOT

- IS: a single-call orchestrator. One invocation = one outbound call. Authors the task brief inline from the deal context, simulates if asked, places the call, and writes the result file.
- IS NOT: a campaign manager. Looping across a candidate or reference list is the caller's job (`dudu:founder-check`, `dudu:pmf-signal`). Run this skill once per person.
- IS NOT: a synthesis step. The transcript is read by `dudu:customer-debrief` (screener calls) or appended to the founder dossier (reference calls). This skill writes the JSON; downstream skills read it.
- IS NOT: a CLI replacement. `callagent` runs underneath; this skill exists so callers don't reproduce the seven-step author/simulate/place dance every invocation.

## Inputs

Required:
- `slug` — deal directory under `deals/`
- `purpose` — one of `reference-check`, `screener`, `custom`
- `target.name` — string used to derive the result-file kebab slug
- `target.phone` — E.164 number (`+…`); ignored when `--demo` is set
- `consent.opted_in` — must be `true` to proceed unless `--demo`
- `consent.token` — opaque string proving opt-in (e.g. `uuidgen` output, a calendar invite ID, anything stable). callagent rejects an empty token with exit 3 and writes the token to the audit log.

Optional:
- `--demo` — route the call to the first allowlisted number; tags the result and audit-log entry with `demo:true`. Skips the `consent.opted_in` check (the allowlist is the consent gate).
- `--task-path <path>` — pre-authored brief. The skill skips brief-authoring (Step 1) when this is supplied.
- `--schema-path <path>` — JSON Schema for end-of-call structured extraction. The skill skips schema-authoring (Step 3) when this is supplied.
- `--simulate-first` — run `callagent simulate` and pause for VC review before placing the real call.
- `--max-duration <seconds>` — passed through to callagent (default 600).
- `--force` — overwrite an existing result file at the derived path.

## Pre-flight

1. **`callagent` on PATH.** Run `command -v callagent`. If absent, exit with: `callagent not on PATH. Build it: cd tools/callagent && npm install && npm run build, then add dist/cli.cjs to PATH or invoke as 'node tools/callagent/dist/cli.cjs'.`
2. **Deal exists.** `deals/<slug>/manifest.json` must exist. If not, exit: `Deal not found at deals/<slug>/. Create it via dudu:background-check or dudu:auto-diligence first.`
3. **Consent gate (skipped under `--demo`).** `consent.opted_in` must be `true`. If not, exit: `Consent gate: target has not opted in. Re-confirm with the VC, or pass --demo to smoke the pipeline against the privacy allowlist instead.`
4. **Calls directory.** Ensure `deals/<slug>/calls/` exists.
5. **Idempotency.** Derive `result_path = deals/<slug>/calls/<purpose>-<kebab(target.name)>.json`. If it exists and `--force` was not passed, exit: `Call result already exists at <result_path>. Pass --force to retry.`

## Steps

### Step 1 — Author or accept the task brief

If `--task-path` was supplied, use it as-is and skip to Step 2.

Otherwise, author the brief inline based on `purpose`. Open all briefs with frontmatter:

```yaml
---
voice: alloy
language: en-US
disclosure_required: true
---
```

The `## Disclosure` section is verbatim — `callagent` extracts it and uses it as the agent's `firstMessage`, so the agent always leads with disclosure before the LLM takes over.

- **`reference-check`** — read `deals/<slug>/founder-<kebab>.md` for the founder under evaluation. Body should:
  - Identify the firm (`<FIRM>` placeholder) and the founder (`<FOUNDER_NAME>` placeholder).
  - Include a verbatim disclosure paragraph that names the founder ("`<FOUNDER_NAME>` listed you as a reference").
  - Methodology: anchor on specific events the reference can recall, never accept generic praise without an example, politely re-ask once if they say "no concerns", listen for what isn't said (hesitations, refusals to specify), don't push for a yes/no on "would you invest".
  - Territory of curiosity: working relationship, strengths with examples, growth areas, would-they-work-with-again.
  - Hard rules: don't reveal what other references said, don't share the founder's pitch or what the firm is investing in, end on first request.
  - Write to `deals/<slug>/calls/task-reference-<kebab(target.name)>.md`.

- **`screener`** — read the cluster signature in `deals/<slug>/personas/` (or fall back to `customer-discovery-prep.md` if present). Body should:
  - Identify the firm (`<FIRM>` placeholder) and its research domain (`<COMPANY_DOMAIN>` placeholder).
  - Include a verbatim disclosure paragraph.
  - Methodology: Mom-Test style — anchor on past concrete behavior, follow tangents, use silence, treat "I'd pay" as a yellow flag.
  - Topic of curiosity: drawn from the candidate's `match_evidence` and cluster `(trigger_type, frame_id)` signature.
  - Hard rules: no portfolio company name, no pitching, end on first request.
  - Write to `deals/<slug>/calls/task-screener-<kebab(target.name)>.md`.

- **`custom`** — exit with: `For purpose=custom, supply --task-path. The skill does not author custom briefs.`

### Step 2 — Author or accept the context file

If `deals/<slug>/calls/context.md` already exists (a previous call in this deal authored it), reuse it.

Otherwise create it:

```markdown
---
FIRM: <firm name from manifest.json or VC prompt>
FOUNDER_NAME: <only for reference-check; from founder-<kebab>.md>
COMPANY_DOMAIN: <only for screener; from web research / pitch>
---
```

Frontmatter only — no body. callagent reads `<TOKEN>` placeholders from the task brief and substitutes from this file's frontmatter at call time.

### Step 3 — Author or accept the JSON Schema

If `--schema-path` was supplied, use it.

Otherwise, write a default to `deals/<slug>/calls/<purpose>-schema.json`. Set `"required": []` so partial extractions still land in `structured_data`.

- **`reference-check`** suggested fields (all optional):
  ```json
  {
    "type": "object",
    "properties": {
      "relationship_context": { "type": "string" },
      "working_dates": { "type": "string" },
      "strength_examples": { "type": "array", "items": { "type": "string" } },
      "concern_examples": { "type": "array", "items": { "type": "string" } },
      "would_work_with_again": { "type": "string", "enum": ["yes","no","qualified","unclear"] },
      "would_work_with_again_reason": { "type": "string" },
      "reference_quality": { "type": "string", "enum": ["high","medium","low"] },
      "what_was_not_said": { "type": "string" },
      "your_overall_read": { "type": "string" }
    },
    "required": []
  }
  ```

- **`screener`** suggested fields (all optional):
  ```json
  {
    "type": "object",
    "properties": {
      "specific_story_captured": { "type": "string" },
      "pain_evidence": { "type": "string" },
      "current_solution": { "type": "string" },
      "wtp_signal": { "type": "string" },
      "interesting_tangent": { "type": "string" },
      "your_overall_read": { "type": "string" }
    },
    "required": []
  }
  ```

### Step 4 — Simulate (only if `--simulate-first`)

Run:

```
callagent simulate \
  --task <task-path> \
  --context deals/<slug>/calls/context.md \
  --schema <schema-path>
```

Play the recipient yourself for 2-3 turns. If the agent feels off (too pushy, too shallow, off-tone, missing disclosure), edit the task brief in place and re-run. Continue to Step 5 only after the simulation reads as natural.

### Step 5 — Place the call

```
callagent place \
  --task <task-path> \
  --context deals/<slug>/calls/context.md \
  --schema <schema-path> \
  --consent-token "<consent.token>" \
  --output <result_path> \
  --max-duration <max-duration> \
  [ --to <target.phone> | --demo ]
```

Routing rules:

- If `--demo`: pass `--demo` and omit `--to`. The call goes to the first entry in callagent's resolved allowlist (default `+61423366127`, or the first entry of `CALLAGENT_ALLOWED_NUMBERS` if set).
- Otherwise: pass `--to <target.phone>`. callagent rejects any number not on the allowlist with exit 2 and prints the active list. To dial a real number outside the default allowlist, the operator must export `CALLAGENT_ALLOWED_NUMBERS=<comma-separated E.164>` for the session. Do not commit real numbers to `.env`.

callagent prints a `[callagent] [DEMO MODE] …` banner (when `--demo`) or a plain `[callagent] …` banner to stderr with the redacted target, the consent-token hash, and the audit-log path, then sleeps 5 seconds before dialing. Watch the banner — Ctrl+C aborts the call before it goes out.

### Step 6 — Hand back

Read `<result_path>` and surface to the caller:

- `result_path` (string).
- `call_id`, `status` (`ended` | `failed`), `duration_seconds`, `recording_url` (or `null`).
- `demo` (`true` only when `--demo` was used).
- A one-line summary: `Wrote <purpose> call result for <target.name> to <result_path> (status=<status>, duration=<duration>s).`

Do **not** synthesize an interpretation of the transcript. Downstream:
- For `screener`: `dudu:customer-debrief` ingests `deals/<slug>/calls/*.json` automatically alongside `inputs/` transcripts.
- For `reference-check`: the caller (`dudu:founder-check`) appends a `## Reference checks` section to the founder dossier citing each transcript.

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["place-call:<purpose>:<kebab(target.name)>"]` with the current ISO-8601 UTC timestamp. Each call is a separate manifest entry — re-running with `--force` updates the timestamp.

## Re-runnability

Idempotent on `<result_path>`. Re-running with the same target on the same purpose exits without dialing unless `--force` is passed. Pass `--force` to re-dial (e.g. when the prior call ended `failed` or the recipient dropped).

## Failure modes

- **callagent exit 1** (provider/network) — Vapi or network failure. Result file may not be written; the caller should retry after diagnosing.
- **callagent exit 2** (allowlist or input) — surface the message verbatim. The most common cause is a real number outside the default allowlist; instruct the operator to export `CALLAGENT_ALLOWED_NUMBERS` for the session.
- **callagent exit 3** (consent) — empty consent token. Re-supply.
- **callagent exit 4** (`failed` status or polling timeout) — the result file is still written. Surface it to the caller with `status=failed` and the `ended_reason`. Do not retry automatically.
