## Context

`dudu:place-call` is a skill (an instruction document at `skills/place-call/SKILL.md`) that orchestrates outbound voice calls via the local `callagent` CLI. It currently requires a six-field structured input bundle and refuses to dial without explicit `consent.opted_in: true` plus a non-empty `consent.token`. The skill is invoked both by upstream pipeline skills (`dudu:auto-diligence`, `dudu:founder-check`, `dudu:pmf-signal`) and by operators directly during development. The pipeline callers reliably supply structured input; direct operator invocation has been a friction point because the consent fields cannot be inferred and so cannot be omitted.

Operators most frequently invoke the skill directly to dial one of three pre-approved dev/test numbers held in callagent's default privacy allowlist (`+61423366127`, `+61405244282`, `+61459529124`). For these calls the operator generally does not have a real consent artifact to point to — the dev numbers exist precisely so that the consent gate's forensic value is irrelevant. Operators have asked for a one-line invocation form like `"dimely, Desmond, ask pmf question, +61459529124"` for this case.

## Goals / Non-Goals

**Goals:**
- Accept a freeform single-string invocation form alongside the existing structured form, additively.
- Eliminate the consent-fields requirement for calls to default-allowlisted numbers, where the fields cannot meaningfully be supplied.
- Preserve the existing structured form's contract identically, so pipeline callers are unaffected.
- Preserve forensic distinguishability between operator-supplied consent and skill-synthesized consent in the audit log and result files.
- Allow `purpose: custom` to auto-author from deal context when `--task-path` is not supplied, lifting the current hard refusal.

**Non-Goals:**
- Changing `callagent`'s own consent gate (callagent will continue to require a non-empty `--consent-token` and append every call to `consent-log.jsonl`).
- Changing the privacy allowlist or its enforcement (allowlist remains the hard wall for which numbers are dialable at all).
- Adding a new "quick-call" skill — the change lives entirely in `dudu:place-call`.
- Removing `consent.opted_in` from the structured form's accepted inputs (it stays accepted for backwards compatibility; it is just not required when a non-empty token is present).
- Multi-language support, mid-call tools, or any callagent-side feature work.

## Decisions

### Decision: Freeform parsing rule — comma-separated with embedded E.164

The freeform form is parsed as: split by commas; identify the segment that matches an E.164 regex (`^\+\d{8,15}$` after trimming whitespace) as `target.phone`; take the first segment as `slug`; the second segment as `target.name`; concatenate the remaining non-phone segments (in order) as `topic`.

**Alternative considered:** Free-text NLP parsing (let the LLM infer fields). Rejected because the parse must be deterministic — the same string must always produce the same field assignments, and parse failures must be catchable and surfaceable as a refusal rather than a silent best-guess.

**Alternative considered:** A strict positional rule (slug, name, topic, phone in fixed order). Rejected because operators routinely write the phone number first or last; the E.164-detection approach handles both without forcing a convention.

### Decision: Topic-to-purpose inference table is small and deterministic

The inference rules are: substring `reference` → `reference-check`; substring `pmf|pain|discovery|interview` → `screener`; otherwise → `custom`. Case-insensitive. No regex, no scoring, no LLM judgment.

**Why:** The skill's existing prefab purposes are coarse buckets, and a small lookup table is easier to reason about and easier to override than a learned classifier. Operators who want a specific purpose can always use the structured form.

**Alternative considered:** Removing the purpose enum entirely and always taking the freeform `custom` auto-authoring path. Rejected because the prefab `reference-check` and `screener` briefs are well-tuned and pipeline callers depend on them. We want freeform invocation to inherit those when applicable.

### Decision: Tiered consent gate keyed on default allowlist

Two tiers, decided by membership in callagent's default allowlist:

1. **Inline tier** — `target.phone` is on the default allowlist. If the operator did not supply consent fields, synthesize `consent.token = "inline-<iso-date>-<kebab(target.name)>"` and set `consent.opted_in = true`. Tag the call `consent_provenance: "inline"`.
2. **Explicit tier** — `target.phone` is anywhere else (including numbers reachable only via `CALLAGENT_ALLOWED_NUMBERS`). Require `consent.token` to be supplied; refuse if missing. Tag the call `consent_provenance: "explicit"`. Stop requiring an explicit `consent.opted_in: true` boolean — supplying a non-empty token *is* the opt-in assertion.

The default allowlist is a stable property of `callagent` (hardcoded constant in `tools/callagent/src/`). The skill reads the active allowlist via the same resolution callagent uses (the `CALLAGENT_ALLOWED_NUMBERS` env var if set, otherwise the default), so the tier decision agrees with what callagent will actually accept.

**Why two tiers and not "always inline":** The `consent_provenance: "explicit"` audit-log entries are how partners and counsel can later prove a real call was made with a real consent artifact. Eroding this for non-test calls would be a regression in legal posture. The carve-out is justified specifically for the dev numbers because no real consent artifact exists or could exist for them.

**Why not "always explicit":** That's the current state, and it's the friction we're removing for the default-allowlist case where the explicit token is just `"test-2026-05-01"` style noise that supplies no forensic value.

**Alternative considered:** A separate `--inline-consent` flag that operators must pass to opt into the inline tier. Rejected because it re-adds ceremony for the case the change explicitly targets. The phone number IS the signal.

### Decision: Custom auto-authoring uses deal artifacts in priority order

When `purpose` resolves to `custom` and `--task-path` is not supplied, the skill reads from `deals/<slug>/` in this order:

1. `pmf-signal.md` (if present, primary source for problem framing)
2. `personas/` cluster signatures (if present, secondary for who the recipient resembles)
3. Any `founder-*.md` (tertiary, for context on what the firm is evaluating)

Topic string seeds the brief's task statement; deal artifacts seed the methodology and hard-rules sections. The brief is written to `deals/<slug>/calls/task-custom-<kebab(target.name)>.md` (mirroring the existing reference-check/screener naming).

**Why priority order:** `pmf-signal.md` is the most synthesized and most recent artifact when present; falling back to raw personas avoids a hard-empty path. Founder dossiers are last because they are about the founder, not the recipient.

**Alternative considered:** Always include all artifacts. Rejected because briefs become bloated and the LLM's attention dilutes; the skill should curate.

### Decision: `consent_provenance` is a top-level field on result and audit entries

Result JSON gains `"consent_provenance": "inline" | "explicit"` at the top level alongside `"consent_token"`. Audit-log JSONL entries gain the same field. Existing entries that predate this change have no field; consumers should treat absence as `"explicit"` (the safer assumption — no false-negative forensic claims).

**Why a string enum and not a boolean:** Future provenance variants (e.g., `"calendar-invite-id"`, `"signed-form-uuid"`) are plausible. A string keeps the door open without a schema break.

## Risks / Trade-offs

- **Risk: Auto-authored `custom` briefs produce poor-quality interviews.** Topic strings can be vague ("ask pmf question") and deal artifacts may be incomplete on a fresh deal. **Mitigation:** Require operators to run `--demo` once on any new topic-string pattern before relying on it for real calls; the audit-log `consent_provenance: "inline"` field makes these calls easy to grep and review post-hoc.
- **Risk: Operator types the wrong slug or wrong name in a freeform invocation, dialing the right number for the wrong deal.** **Mitigation:** Idempotency check on `<result_path>` already prevents accidental overwrites; the 5-second pre-dial banner shows the redacted target and the deal slug, giving the operator a final abort window. No additional gate.
- **Risk: Default-allowlist composition changes (new dev number added to callagent) silently expand the inline-consent tier.** **Mitigation:** This is intentional and acceptable — adding a number to the default allowlist is itself a deliberate code change. If we later distinguish "test numbers" from "operator allowlist", the tier rule can be tightened.
- **Trade-off: Two input shapes increase the skill's surface area.** Mitigated by keeping the structured form's contract identical (no new fields, no new defaults applied to it) and routing both shapes into a single internal canonical-input representation as the first step of pre-flight.
- **Trade-off: Removing the `consent.opted_in: true` requirement in the explicit tier changes the structured form's contract slightly — callers who previously omitted `consent.token` and relied on `consent.opted_in` alone would have been broken anyway.** Verification: no existing pipeline caller is in this state; all supply both fields. Confirmed by reading the four caller skills (`dudu:auto-diligence`, `dudu:founder-check`, `dudu:pmf-signal`, `dudu:place-call` self-recursive smokes).

## Migration Plan

This is a skill-document edit only — no code, no data, no environment migration. The structured form remains valid, so no caller updates are required.

Rollout:
1. Edit `skills/place-call/SKILL.md` per the tasks document.
2. Run a `--demo` smoke against an existing deal using the new freeform form (e.g., `"dimely, Desmond, pmf question, +61459529124"` with `--demo`) to verify parsing, inference, custom auto-authoring, and audit fields.
3. No rollback artifact needed — reverting the SKILL.md edit fully reverts the change.

## Open Questions

- Should `consent_provenance: "inline"` calls also be excluded from `dudu:customer-debrief`'s default ingestion (so test calls don't pollute synthesis)? Defer until customer-debrief is touched; this change does not modify downstream consumers.
- Should the freeform topic string also feed the `<TOPIC>` placeholder in the auto-authored brief (in addition to seeding the task statement)? Default to yes for `custom`; revisit if any prefab-purpose template gains a similar placeholder.
