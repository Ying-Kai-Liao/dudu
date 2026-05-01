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

## Input shapes

The skill accepts invocation in either of two forms. Both shapes resolve to the same canonical-input representation in Pre-flight Step 0; everything from Step 1 onward is form-agnostic.

### Structured form (used by pipeline callers)

A bundle of named fields — see [Inputs](#inputs) below. This is the form `dudu:auto-diligence`, `dudu:founder-check`, and `dudu:pmf-signal` invoke with. Every field is explicit, no inference. Use this when you have full information and want zero magic.

### Freeform form (used by direct operator invocation)

A single comma-separated string with an embedded E.164 number, e.g.:

```
dimely, Desmond, ask pmf question, +61459529124
```

The skill parses the segments into `slug`, `target.name`, `topic`, and `target.phone`, then applies the [topic inference](#topic-inference) rules to derive `purpose`. Optional flags (`--demo`, `--simulate-first`, `--task-path`, `--schema-path`, `--max-duration`, `--force`, `--consent-token`) MAY be appended after the freeform string. When `target.phone` lands on callagent's default allowlist, consent fields are auto-defaulted (see Pre-flight Step 3 — Tiered consent gate). Use this for routine internal testing where the structured form's ceremony has no forensic value.

## Inputs

Required (structured form):
- `slug` — deal directory under `deals/`
- `purpose` — one of `reference-check`, `screener`, `custom`
- `target.name` — string used to derive the result-file kebab slug
- `target.phone` — E.164 number (`+…`); ignored when `--demo` is set
- `consent.opted_in` — must be `true` to proceed unless `--demo`
- `consent.token` — opaque string proving opt-in (e.g. `uuidgen` output, a calendar invite ID, anything stable). callagent rejects an empty token with exit 3 and writes the token to the audit log.

Optional:
- `--demo` — route the call to the first allowlisted number; tags the result and audit-log entry with `demo:true`. Skips the explicit-tier consent check (the allowlist is the consent gate). Calls invoked with `--demo` are tagged `consent_provenance: "inline"`.
- `--task-path <path>` — pre-authored brief. The skill skips brief-authoring (Step 1) when this is supplied.
- `--schema-path <path>` — JSON Schema for end-of-call structured extraction. The skill skips schema-authoring (Step 3) when this is supplied.
- `--simulate-first` — run `callagent simulate` and pause for VC review before placing the real call.
- `--max-duration <seconds>` — passed through to callagent (default 600).
- `--force` — overwrite an existing result file at the derived path.

Required (freeform form): a single comma-separated string containing `slug`, `target.name`, `topic`, and an E.164 phone number. The skill derives `purpose` from `topic` per the [Topic inference](#topic-inference) table. `consent.opted_in` and `consent.token` are NOT required when `target.phone` is on the default allowlist; they ARE required (token only) for any other number — see Pre-flight Step 3.

## Topic inference

Applied only when the freeform form is used. The structured form's explicit `purpose` always takes precedence; this table is never consulted in that path.

The skill matches the topic string (case-insensitive) against the rules in priority order:

| Priority | Rule (substring match in topic) | Resolved `purpose` |
|---|---|---|
| 1 | contains `reference` | `reference-check` |
| 2 | contains any of `pmf`, `pain`, `discovery`, `interview` | `screener` |
| 3 | otherwise | `custom` |

Priority 1 wins over priority 2: a topic like `"reference about pmf signal"` resolves to `reference-check`, not `screener`. This is intentional — reference checks have stricter hard rules than screeners, and accidentally treating one as the other has worse failure modes than vice versa.

When the resolved `purpose` is `custom`, the skill auto-authors the brief from `topic` plus the available deal artifacts (see Step 1 below). The skill no longer hard-exits on `purpose: custom` without `--task-path`.

## Pre-flight

0. **Normalize input.** Resolve the invocation to a canonical-input record with the fields `slug`, `purpose`, `target.name`, `target.phone`, `consent.opted_in`, `consent.token`, plus all optional flags. Apply the rules below in order:

   - **If the structured form was used**, copy fields verbatim. Skip the freeform parse rules. Do not consult the topic-inference table — the explicit `purpose` always wins.
   - **If the freeform form was used**, parse the comma-separated string:
     - Split by `,` and trim each segment.
     - Identify the segment that matches the E.164 pattern `^\+\d{8,15}$` (after trimming) as `target.phone`. The phone segment MAY appear in any position, not only last.
     - The first non-phone segment is `slug`.
     - The second non-phone segment is `target.name`.
     - All remaining non-phone segments, concatenated with a space in original order, become `topic`.
     - Apply the [Topic inference](#topic-inference) table to derive `purpose` from `topic`.
   - **Refusal cases for malformed freeform input** (each writes nothing and exits non-zero with the exact message):
     - Missing slug (no non-phone segment): `Freeform input missing slug. Expected: "<slug>, <target.name>, <topic>, +<E.164>".`
     - Missing target.name (only one non-phone segment): `Freeform input missing target.name. Expected: "<slug>, <target.name>, <topic>, +<E.164>".`
     - Missing or unparseable phone (no segment matches E.164): `Freeform input missing or unparseable E.164 phone number. Expected: "<slug>, <target.name>, <topic>, +<E.164>".`
   - **Topic-elision sentinel.** If `topic` is empty after parsing (i.e. exactly three non-phone segments where the third is empty), `purpose` resolves to `custom` with an empty topic; the auto-authoring branch in Step 1 handles the empty-topic case as if the operator had said "open-ended interview".

1. **`callagent` on PATH.** Run `command -v callagent`. If absent, exit with: `callagent not on PATH. Build it: cd tools/callagent && npm install && npm run build, then add dist/cli.cjs to PATH or invoke as 'node tools/callagent/dist/cli.cjs'.`
2. **Deal exists.** `deals/<slug>/manifest.json` must exist. If not, exit: `Deal not found at deals/<slug>/. Create it via dudu:background-check or dudu:auto-diligence first.`
3. **Tiered consent gate (skipped under `--demo`, which always proceeds as if the inline tier resolved).**

   The skill resolves the active default allowlist by reading `CALLAGENT_ALLOWED_NUMBERS` from the environment when set (comma-separated E.164), and otherwise falling back to callagent's hardcoded default of three Australian numbers (`+61423366127`, `+61405244282`, `+61459529124`). This is the same resolution callagent itself uses — the skill's tier decision agrees with what callagent will actually accept.

   - **Inline tier.** When `target.phone` is on the active default allowlist AND the operator did not supply `consent.opted_in` or `consent.token`: synthesize `consent.token = "inline-<iso-date>-<kebab(target.name)>"` (e.g. `inline-2026-05-01-desmond`), set `consent.opted_in = true`, set `consent_provenance = "inline"`, and proceed.
   - **Explicit tier.** When `target.phone` is NOT on the active default allowlist: an explicit `consent.token` MUST be supplied. If absent, exit: `Consent gate: target.phone is not on the default allowlist; supply consent.token to assert opt-in. If you also need to dial this number, export CALLAGENT_ALLOWED_NUMBERS first.` An explicit `consent.opted_in: true` boolean is no longer required — the presence of a non-empty token IS the assertion. Set `consent_provenance = "explicit"`.
   - **Operator-token-wins.** Any operator-supplied non-empty `consent.token` (whether in structured or freeform form, whether or not `--consent-token` was passed) is used verbatim regardless of tier, and the call is tagged `consent_provenance = "explicit"`.

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

**Cross-cutting constraints — apply to every auto-authored brief regardless of purpose:**

- Address the recipient as the actual person picking up the phone, by their real name. Do **not** ask them to roleplay, "answer as if you were", "imagine you are", or pretend to be a specific persona — even when the deal context describes that persona in detail, even when `target.phone` is on the default allowlist. The allowlist gates consent, not call purpose; an allowlisted recipient is still a real human and is treated as one.
- Do **not** assume the recipient is an internal tester or stand-in. They may be a smoke-testing collaborator, a real prospect on the allowlist by deliberate operator action, or someone in between — the brief cannot tell, and should not try. Assume real.
- Frame methodology and probes around the recipient's actual past behavior in their actual role. If the deal's `personas/` describe a target persona that the recipient may not match, the brief should ask what the recipient has actually done, not coach them into the persona's vocabulary.
- Treat persona descriptions in `pmf-signal.md` and `personas/` as **operator-facing context** (helping the brief decide which probes are sharp), not as **recipient-facing instructions** (telling the recipient who to be). Vocabulary, examples, and trigger language from those artifacts MAY appear in the brief's "How to handle this" section as cues for the agent, but MUST NOT appear as expectations placed on the recipient.

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

- **`custom`** — author the brief from `topic` plus the available deal artifacts. If `--task-path` was supplied, use it as-is and skip auto-authoring (matches the precedence rule for prefab purposes).

  Read deal artifacts in this priority order, including each one that exists:
  1. `deals/<slug>/pmf-signal.md` — primary source for the problem framing and persona language. If present, anchor methodology and hard-rules on its content.
  2. `deals/<slug>/personas/` cluster signatures (`personas/aggregates.yaml`, `personas/_context.md`) — secondary, for who the recipient resembles.
  3. `deals/<slug>/founder-*.md` — tertiary, for what the firm is evaluating. Include just enough to ground `<FIRM>` framing; do not surface founder-specific material to the recipient.

  If none of the three artifacts exist (a fresh deal with only `manifest.json`), exit: `Cannot auto-author a custom brief: no usable deal artifacts under deals/<slug>/. Supply --task-path with a hand-written brief, or run dudu:background-check first to populate the deal.`

  The auto-authored brief uses the same frontmatter as prefab purposes (`voice: alloy`, `language: en-US`, `disclosure_required: true`). The `topic` string seeds the `# Task` body; deal artifacts seed methodology and hard-rules. Include a `<FIRM>` placeholder (and `<COMPANY_DOMAIN>` if `pmf-signal.md` exists) so context-file substitution still applies. If `topic` is empty (the topic-elision sentinel from Step 0), frame the body as an open-ended interview anchored on the deal's pmf-signal questions; the agent's task statement should explicitly invite the recipient to speak about whatever is currently on their mind in the relevant workflow.

  Standard hard rules for auto-authored custom briefs (always include): no portfolio company name, no pitching, end on first request. Add purpose-specific rules only when topic clearly demands them.

  Write to `deals/<slug>/calls/task-custom-<kebab(target.name)>.md`.

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

- If `--demo`: pass `--demo` and omit `--to`. The call goes to the first entry in callagent's resolved allowlist (default `+61423366127`, or the first entry of `CALLAGENT_ALLOWED_NUMBERS` if set). When the freeform form was used with `--demo`, the parsed `target.phone` does NOT affect routing but IS still recorded in the audit-log entry under a `parsed_phone` field for traceability.
- Otherwise: pass `--to <target.phone>`. callagent rejects any number not on the allowlist with exit 2 and prints the active list. To dial a real number outside the default allowlist, the operator must export `CALLAGENT_ALLOWED_NUMBERS=<comma-separated E.164>` for the session. Do not commit real numbers to `.env`.

callagent prints a `[callagent] [DEMO MODE] …` banner (when `--demo`) or a plain `[callagent] …` banner to stderr with the redacted target, the consent-token hash, and the audit-log path, then sleeps 5 seconds before dialing. Watch the banner — Ctrl+C aborts the call before it goes out.

After callagent returns, **patch `consent_provenance` into both artifacts** (callagent itself does not know which tier produced the call; the skill is the only layer that does):

- **Result file** (`<result_path>`): read the JSON callagent wrote, add a top-level `"consent_provenance": "<inline|explicit>"` field (use the value resolved in Pre-flight Step 3), and re-write the file. When `--demo` was used, the value is always `"inline"`.
- **Audit log** (`consent-log.jsonl` next to `<result_path>`, or `CALLAGENT_AUDIT_LOG` if set): append a sibling JSONL line — `{"consent_token":"<token>","consent_provenance":"<inline|explicit>","placed_at":"<iso>"}` — keyed to the same `consent_token` callagent already logged. Do not modify callagent's existing entry; append a follow-up entry. Downstream consumers reading old audit-log entries that predate this change should treat absence of `consent_provenance` as `"explicit"` (the safer assumption — no false-negative forensic claims).

### Step 6 — Hand back

Read `<result_path>` and surface to the caller:

- `result_path` (string).
- `call_id`, `status` (`ended` | `failed`), `duration_seconds`, `recording_url` (or `null`).
- `demo` (`true` only when `--demo` was used).
- `consent_provenance` (`"inline"` | `"explicit"`).
- A one-line summary: `Wrote <purpose> call result for <target.name> to <result_path> (status=<status>, duration=<duration>s, consent=<consent_provenance>).`

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

## Migration notes

**What changed:**

- The skill now accepts a freeform invocation form (`"<slug>, <target.name>, <topic>, +<E.164>"`) in addition to the structured form. See [Input shapes](#input-shapes).
- `purpose: custom` no longer hard-exits without `--task-path`; it auto-authors a brief from `topic` and the deal's artifacts (`pmf-signal.md`, `personas/`, founder dossiers).
- Calls to numbers on the default allowlist (callagent's three pre-approved dev/test numbers, or whatever `CALLAGENT_ALLOWED_NUMBERS` overrides them with) no longer require `consent.opted_in: true` or `consent.token` to be supplied — the skill synthesizes `consent.token = "inline-<iso-date>-<kebab(target.name)>"` and tags the call `consent_provenance: "inline"`.
- Calls to non-default-allowlist numbers still require an explicit `consent.token`, but no longer require `consent.opted_in: true` separately (the token is the assertion). These calls are tagged `consent_provenance: "explicit"`.
- Result JSON and audit-log entries now carry a `consent_provenance` field. Downstream consumers reading old entries should treat absence as `"explicit"`.

**What did not change:**

- The structured form's contract: `dudu:auto-diligence`, `dudu:founder-check`, and `dudu:pmf-signal` continue to work without modification — they all supply explicit `consent.token` plus `consent.opted_in: true`, which routes through the explicit tier exactly as before.
- callagent's own consent gate: every `place` invocation still requires `--consent-token` to be non-empty. The skill is the only layer that synthesizes tokens; callagent treats every token the same way.
- callagent's privacy allowlist enforcement: the allowlist remains the hard wall for which numbers are dialable at all. The skill's tier decision agrees with callagent's allowlist resolution but does not relax it.
- `--demo` semantics: still routes to the first allowlist entry, still skips explicit consent. Now also tags the call `consent_provenance: "inline"`.
