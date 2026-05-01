## 1. Skill input layer

- [x] 1.1 Add a "## Input shapes" section to `skills/place-call/SKILL.md` that documents both the structured form (existing fields preserved verbatim) and the freeform form (single comma-separated string with embedded E.164)
- [x] 1.2 Add a "## Pre-flight Step 0 — Normalize input" subsection that defines the freeform parse rule (split by commas, identify E.164 segment as `target.phone`, first segment as `slug`, second as `target.name`, remaining concatenated as `topic`) and the canonical-input representation both shapes resolve into
- [x] 1.3 Add explicit refusal cases for malformed freeform input (missing slug, missing name, missing or unparseable E.164), each with the verbatim error message the skill emits

## 2. Topic-to-purpose inference

- [x] 2.1 Add a "## Topic inference" subsection to `skills/place-call/SKILL.md` documenting the case-insensitive substring rules: `reference` → `reference-check`; `pmf|pain|discovery|interview` → `screener`; otherwise → `custom`
- [x] 2.2 Specify precedence: `reference-check` wins if both `reference` and a screener keyword appear (covers edge cases like "reference about pmf signal")
- [x] 2.3 Specify that the inference table only applies when the freeform form was used; the structured form's explicit `purpose` always takes precedence

## 3. Custom-purpose auto-authoring

- [x] 3.1 Replace the existing hard-exit branch for `purpose: custom` (currently: `For purpose=custom, supply --task-path. The skill does not author custom briefs.`) with an auto-authoring branch in Step 1 of `skills/place-call/SKILL.md`
- [x] 3.2 Document the deal-artifact priority order: read `pmf-signal.md` first, then `personas/` cluster signatures, then any `founder-*.md`; concatenate context for brief synthesis
- [x] 3.3 Document the brief structure for auto-authored custom briefs: same frontmatter as prefab purposes; topic seeds the task statement; deal artifacts seed methodology and hard-rules; output path is `deals/<slug>/calls/task-custom-<kebab(target.name)>.md`
- [x] 3.4 Preserve the explicit-`--task-path` precedence: when supplied, the skill skips auto-authoring (matches current behavior for prefab purposes)
- [x] 3.5 Add the new refusal case for custom auto-authoring with no usable deal artifacts: instruct operator to supply `--task-path` or run `dudu:background-check`

## 4. Tiered consent gate

- [x] 4.1 Replace the current Pre-flight Step 3 ("Consent gate") in `skills/place-call/SKILL.md` with a tiered version that branches on default-allowlist membership of `target.phone`
- [x] 4.2 Document the inline tier rule: when `target.phone` is on callagent's default allowlist AND operator omitted consent fields, synthesize `consent.token = "inline-<iso-date>-<kebab(target.name)>"`, set `consent.opted_in = true`, and proceed
- [x] 4.3 Document the explicit tier rule: when `target.phone` is NOT on the default allowlist AND `consent.token` was not supplied, refuse with the message naming both possible remedies (supply token; export `CALLAGENT_ALLOWED_NUMBERS` if also needed)
- [x] 4.4 Document the explicit-tier relaxation: when an explicit `consent.token` is supplied, `consent.opted_in: true` is no longer required (the token is the assertion)
- [x] 4.5 Document the operator-token-wins rule: any operator-supplied non-empty `consent.token` is used verbatim regardless of tier
- [x] 4.6 Specify how the skill resolves the active default allowlist (read `CALLAGENT_ALLOWED_NUMBERS` env if set, else use callagent's hardcoded default of three Australian numbers — agreeing with callagent's own resolution)

## 5. Consent provenance tagging

- [x] 5.1 Update Step 5 ("Place the call") in `skills/place-call/SKILL.md` to thread a `consent_provenance` value (`"inline"` for synthesized tokens, `"explicit"` for operator-supplied) through to the result file and audit log
- [x] 5.2 Document that the result JSON written at `<result_path>` includes a top-level `"consent_provenance"` field
- [x] 5.3 Document that the audit-log entry in `consent-log.jsonl` includes a `"consent_provenance"` field
- [x] 5.4 Document the absence-means-explicit convention for downstream consumers reading entries that predate this change

## 6. Demo-mode interaction

- [x] 6.1 Update the `--demo` documentation in `skills/place-call/SKILL.md` to clarify it composes with the freeform form: parsed `target.phone` is recorded in the audit log for traceability but routing still goes to the first allowlist entry
- [x] 6.2 Specify that `--demo` invocations are tagged `consent_provenance: "inline"` (consistent with the inline-tier rule, since `--demo` skips explicit consent)

## 7. Backwards-compatibility verification

- [x] 7.1 Walk through each upstream caller (`dudu:auto-diligence`, `dudu:founder-check`, `dudu:pmf-signal`) and confirm their structured-form invocations continue to behave identically — document the verification in the change's commit message
- [x] 7.2 Add a "## Migration notes" subsection to `skills/place-call/SKILL.md` summarizing what changed for operators (freeform form now accepted; consent fields auto-defaulted on default-allowlist numbers) and what did not change (structured form contract, callagent gate, allowlist enforcement)

## 8. Smoke test

- [x] 8.1 Run a `--demo` smoke from the freeform form against an existing deal: `"dimely, Desmond, pmf question, +61459529124"` plus `--demo`. Confirm parse → inference → simulate (optional) → place → result file lands at `deals/dimely/calls/screener-desmond.json` with `consent_provenance: "inline"` and `demo: true`
- [x] 8.2 Run a `--demo` smoke that exercises the new custom auto-authoring path: a topic string like `"how they handle X"` that does not trigger `reference-check` or `screener` keywords. Confirm `task-custom-<kebab>.md` is authored from `pmf-signal.md` content and the brief reads naturally
- [x] 8.3 Run a refusal-path smoke: invoke with a non-default-allowlist number (using a fictional E.164 not on the allowlist) and no `consent.token` — confirm the skill exits with the explicit-tier refusal message and writes nothing
