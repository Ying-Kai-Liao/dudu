# callagent — Manual Smoke-Test Runbook

Run this before tagging any release. It is not automated. A human must execute
each phase and verify the expected outcomes. Budget ~5 minutes for simulate +
dry-run, plus the duration of one real call for the place phase.

---

## 1. Prerequisites

- **Node 20+** — `node --version`
- **Built CLI** — `npm run build` inside `tools/callagent/`. Binary at `dist/cli.cjs`.
- **OpenAI account** — needed for Phase 1 (simulate). Free-tier works.
- **Vapi account** — needed for Phases 2–4. A provisioned outbound phone number
  (`VAPI_PHONE_NUMBER_ID`) must exist in the Vapi dashboard (Phone Numbers page — copy the UUID).
- **A test phone you control** — the number that receives the real call in Phase 3.
  Do not use a number you do not own. The default privacy allowlist only permits:
  `+61423366127`, `+61405244282`, `+61459529124`. To smoke a different number,
  export `CALLAGENT_ALLOWED_NUMBERS=<your-e164>` for the session, or run from a
  shell where `.env` sets it. The shortcut for end-to-end demos is `--demo`,
  which auto-routes the call to the first allowlisted number and tags the
  result + audit-log entry with `demo:true`.

All commands below assume `tools/callagent/` as the working directory.

```bash
cd tools/callagent
```

---

## 2. .env Setup

Create `tools/callagent/.env` (already gitignored). Populate both blocks:

```dotenv
# Phase 1 — simulate (OpenAI text REPL)
OPENAI_API_KEY=sk-...

# Phases 2–4 — place (Vapi real call)
VAPI_API_KEY=...
VAPI_PHONE_NUMBER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx   # UUID from Vapi dashboard → Phone Numbers
```

Confirm the file is loaded:

```bash
node -e "require('dotenv/config'); console.log('OPENAI_API_KEY set:', !!process.env.OPENAI_API_KEY)"
```

---

## 3. Smoke Task and Schema

Write the following two files. They are used in every phase. Use heredoc to
create them without a bundled fixture:

```bash
cat > /tmp/smoke-task.md << 'EOF'
---
voice: alloy
language: en-US
disclosure_required: true
---

# Task

You are an AI assistant calling on behalf of Acme Corp to conduct a brief
customer satisfaction survey about a recent support interaction. Keep it short
— two questions maximum. Be polite and conversational.

## Disclosure
"Hi, I'm an AI assistant calling on behalf of Acme Corp. This is a quick
two-question satisfaction survey about your recent support experience. The call
may be recorded. Is now a good time?"

## Questions
1. On a scale of 1–10, how would you rate the support you received?
2. Is there anything specific the support team could have done better?

## Hard rules
- Do not collect personal or payment information.
- If the recipient declines or asks to be removed, thank them and end the call.
EOF
```

```bash
cat > /tmp/smoke-schema.json << 'EOF'
{
  "type": "object",
  "properties": {
    "satisfaction_score": { "type": "integer", "minimum": 1, "maximum": 10 },
    "improvement_note": { "type": "string" }
  },
  "required": ["satisfaction_score", "improvement_note"]
}
EOF
```

---

## 4. Phase 1 — Simulate

Simulates the full agent conversation over a text REPL using OpenAI. Free. No
phone required. Validates: system prompt construction, disclosure handling,
schema extraction on `/end`.

```bash
node dist/cli.cjs simulate \
  --task /tmp/smoke-task.md \
  --schema /tmp/smoke-schema.json
```

**What to do:**

1. The agent prints its first turn automatically. Verify it leads with the
   disclosure sentence verbatim: `"Hi, I'm an AI assistant calling on behalf of
   Acme Corp..."`. This confirms `disclosure_required: true` is wired correctly.
2. Reply as the call recipient — type `[You] Sure, go ahead.` and press Enter.
3. The agent should ask the satisfaction score question. Reply with a number,
   e.g. `[You] I'd say an 8.`
4. The agent should ask the improvement question. Reply, e.g.
   `[You] Response time could be faster.`
5. Type `/end` to end the simulated call.

**Verify after `/end`:**

- Extraction output appears. It should be valid JSON matching the schema, for
  example:
  ```json
  {
    "satisfaction_score": 8,
    "improvement_note": "Response time could be faster."
  }
  ```
- No `"satisfaction_score": null` or missing `required` fields.
- Exit code 0 (`echo $?` should print `0`).

**Failure modes:**

- `Error: OPENAI_API_KEY is not set` — check `.env` and dotenv loading.
- Agent does not lead with disclosure — check that `disclosure_required: true`
  is in the task frontmatter and the `## Disclosure` section is present.

---

## 5. Phase 2 — Dry-Run

Validates the Vapi `CreateCallDTO` shape without making any network call or
incurring telephony cost. Run this before every real call.

```bash
node dist/cli.cjs place \
  --to +15559876543 \
  --task /tmp/smoke-task.md \
  --consent-token "smoke-test-$(date +%Y%m%d)" \
  --schema /tmp/smoke-schema.json \
  --dry-run
```

Replace `+15559876543` with your test phone number. The `--to` value is not
dialed — it only appears in the printed DTO.

**Verify:**

- Stdout is valid JSON (pipe to `| python3 -m json.tool` to confirm).
- `assistant.model.messages[0].role` is `"system"` and its `content` contains
  the task body text (`"You are an AI assistant calling on behalf of Acme Corp"`).
- `assistant.firstMessage` equals the disclosure string from the task.
- `assistant.analysisPlan.structuredDataSchema` matches the schema you provided.
- `customer.number` equals `+15559876543`.
- No network request was made (no Vapi call charge, no audit log written).

**Failure modes:**

- Dry-run does NOT require Vapi credentials. The CLI falls back to a stub provider when the env vars aren't set, so the printed `phoneNumberId` will be `<stub>` or similar. Real `place` (without `--dry-run`) requires `VAPI_API_KEY` and `VAPI_PHONE_NUMBER_ID`.
- `firstMessage` absent — `disclosure_required: true` may be missing from the
  task frontmatter, or the `## Disclosure` section is malformed.

---

## 6. Phase 3 — Real Call

Places one outbound call to a phone you control. Costs approximately $0.10.
Have the test phone ready.

```bash
node dist/cli.cjs place \
  --to +15559876543 \
  --task /tmp/smoke-task.md \
  --consent-token "smoke-test-$(date +%Y%m%d)" \
  --schema /tmp/smoke-schema.json \
  --output /tmp/smoke-call.json
```

Replace `+15559876543` with your real test phone number.

**What to expect on stderr (immediately after running):**

```
[callagent] Placing call to +1555****543 with task smoke-task.md.
[callagent] Consent token: <8-char hex hash>. Audit log: /tmp/consent-log.jsonl.
[callagent] If you do not have explicit opt-in from this target, abort now (Ctrl+C).
[callagent] Sleeping 5s before placing call.
```

You have 5 seconds to press Ctrl+C if anything looks wrong.

**Verify (before the call ends):**

- Phone number on banner is redacted (all digits except last four replaced with
  `*`).
- Consent token is shown as a hash, not the raw token string.
- Audit log path is printed.
- After the 5-second sleep, the test phone rings.
- The AI agent answers and leads with the disclosure sentence.

**Answer the call and play the role of the recipient:**

1. Confirm you hear the disclosure. Say "Sure, go ahead."
2. Answer the satisfaction score question (say a number, e.g. "seven").
3. Answer the improvement question (say anything brief).
4. Hang up, or let the agent close the call.

**Verify after the call ends (stdout + filesystem):**

- `/tmp/smoke-call.json` is written. Check key fields:
  ```bash
  node -e "const r = require('/tmp/smoke-call.json'); console.log(r.status, r.transcript ? 'has transcript' : 'NO TRANSCRIPT', r.structured_data)"
  ```
  Expected: `ended has transcript { satisfaction_score: <n>, improvement_note: '...' }`
- `structured_data` is not `null` and both required fields are populated.
- Audit log has a new JSONL line:
  ```bash
  tail -1 /tmp/consent-log.jsonl
  ```
  Expected shape: `{"consent_token":"smoke-test-...","to":"+15559876543","task_path":"...","placed_at":"..."}`

**Failure modes:**

- Phone does not ring within 30 seconds — check `VAPI_API_KEY` validity and
  that `VAPI_PHONE_NUMBER_ID` is provisioned and active in the Vapi dashboard.
- `structured_data: null` — Vapi did not return an extraction result. Check
  that the schema was included in the DTO (rerun Phase 2 dry-run and inspect
  `analysisPlan.structuredDataSchema`).

---

## 7. Phase 4 — Status and Transcript Subcommands

Use the `call_id` from the output file written in Phase 3.

```bash
CALL_ID=$(node -e "console.log(require('/tmp/smoke-call.json').call_id)")
echo "Using call_id: $CALL_ID"
```

**Status:**

```bash
node dist/cli.cjs status "$CALL_ID"
```

Verify: JSON printed to stdout with `call_id`, `status: "ended"`, and
`transcript` field populated.

**Transcript:**

```bash
node dist/cli.cjs transcript "$CALL_ID"
```

Verify: Plain transcript text printed to stdout (not JSON). Should contain both
agent and recipient turns.

**Failure modes:**

- `404` from Vapi — the call ID is wrong or Vapi has not finished indexing the
  call. Wait 30 seconds and retry.
- `VAPI_API_KEY` missing — both subcommands require it in env.

---

## 8. Cleanup

```bash
rm /tmp/smoke-task.md /tmp/smoke-schema.json /tmp/smoke-call.json
# consent-log.jsonl is an audit artifact — keep it or remove intentionally:
rm /tmp/consent-log.jsonl
```

---

## 9. Go/No-Go

All four phases must pass without manual intervention before tagging a release.
If any phase fails:

1. Fix the root cause in the relevant source file.
2. Run `npm test` to confirm the 37 unit tests still pass.
3. Re-run the affected phase and all subsequent phases from that point.

Do not tag if Phase 3 produces `structured_data: null` — schema extraction is
load-bearing for callers who depend on it.
