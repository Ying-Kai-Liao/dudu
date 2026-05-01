# place-call Specification

## Purpose
TBD - created by sync from change simplify-place-call-input. Update Purpose after archive.

## Requirements
### Requirement: Polymorphic Input Acceptance

The skill SHALL accept invocation in either a structured form (a bundle of named fields: `slug`, `purpose`, `target.name`, `target.phone`, `consent.opted_in`, `consent.token`, plus optional flags) or a freeform form (a single comma-separated string containing `slug`, `target.name`, `topic`, and an embedded E.164 number). The structured form is preserved unchanged for backwards compatibility with existing callers.

#### Scenario: Structured invocation continues to work
- **WHEN** an operator invokes the skill with the existing six-field structured input bundle
- **THEN** the skill behaves identically to its prior contract, with no inferred values and no consent-tier carve-out

#### Scenario: Freeform invocation parses fields
- **WHEN** an operator invokes the skill with a freeform string such as `"dimely, Desmond, ask pmf question, +61459529124"`
- **THEN** the skill SHALL parse `slug` from the first comma-segment, `target.name` from the second, `topic` from the segment(s) between the name and the phone number, and `target.phone` from the embedded E.164 token (which MAY appear in any position)

#### Scenario: Freeform input missing slug or name or phone
- **WHEN** the freeform string omits any of `slug`, `target.name`, or a recognizable E.164 phone number
- **THEN** the skill SHALL exit with a clear message naming the missing field, and SHALL NOT dial

### Requirement: Topic-to-Purpose Inference

When invoked via the freeform form, the skill SHALL derive `purpose` from the `topic` string using a deterministic inference table, and SHALL apply the inferred purpose's brief-authoring branch from the existing skill flow.

#### Scenario: Topic implies reference-check
- **WHEN** the topic string contains the substring `reference` (case-insensitive)
- **THEN** `purpose` SHALL be set to `reference-check`

#### Scenario: Topic implies screener
- **WHEN** the topic string contains any of the substrings `pmf`, `pain`, `discovery`, or `interview` (case-insensitive)
- **AND** the topic does not also imply `reference-check`
- **THEN** `purpose` SHALL be set to `screener`

#### Scenario: Topic implies custom
- **WHEN** the topic string matches none of the inference rules above
- **THEN** `purpose` SHALL be set to `custom`

### Requirement: Custom Purpose Auto-Authoring

When `purpose` resolves to `custom` AND `--task-path` was not supplied, the skill SHALL auto-author a task brief from the `topic` string and the deal artifacts available under `deals/<slug>/`, instead of refusing to proceed. A hand-authored brief supplied via `--task-path` continues to take precedence over auto-authoring.

#### Scenario: Custom auto-author from deal context
- **WHEN** purpose is `custom`, `--task-path` is not supplied, and `deals/<slug>/` contains at least one of `pmf-signal.md`, `personas/`, or a founder dossier
- **THEN** the skill SHALL synthesize a task brief that frames the recipient interview around the topic string, anchored on facts drawn from the available deal artifacts, and write it to `deals/<slug>/calls/task-custom-<kebab(target.name)>.md`

#### Scenario: Custom auto-author lacks deal context
- **WHEN** purpose is `custom`, `--task-path` is not supplied, and no usable deal artifacts exist under `deals/<slug>/`
- **THEN** the skill SHALL exit with a message instructing the operator to supply `--task-path` or to first run `dudu:background-check`

#### Scenario: Explicit task path overrides auto-authoring
- **WHEN** `--task-path` is supplied for `purpose: custom`
- **THEN** the skill SHALL use the supplied brief as-is and SHALL NOT auto-author

### Requirement: Tiered Consent Gate

The skill SHALL apply a two-tier consent gate based on whether `target.phone` is on callagent's default privacy allowlist. Calls to default-allowlisted numbers MAY proceed with auto-defaulted consent fields; calls to any other number SHALL require an explicit `consent.token`.

#### Scenario: Default-allowlist number with no explicit consent fields
- **WHEN** `target.phone` matches an entry in callagent's default allowlist (the three pre-approved dev/test numbers) AND the operator did not supply `consent.opted_in` or `consent.token`
- **THEN** the skill SHALL set `consent.opted_in = true` and `consent.token = "inline-<iso-date>-<kebab(target.name)>"` automatically, and proceed to dial

#### Scenario: Non-default-allowlist number without explicit consent token
- **WHEN** `target.phone` is NOT on callagent's default allowlist AND the operator did not supply `consent.token`
- **THEN** the skill SHALL exit with a refusal message instructing the operator to supply an explicit `consent.token` (and, if applicable, to export `CALLAGENT_ALLOWED_NUMBERS`), and SHALL NOT dial

#### Scenario: Non-default-allowlist number with explicit consent token
- **WHEN** `target.phone` is NOT on callagent's default allowlist AND the operator supplied a non-empty `consent.token`
- **THEN** the skill SHALL proceed to dial without requiring an explicit `consent.opted_in: true` (the presence of the token is the assertion)

#### Scenario: Operator-supplied explicit token always wins
- **WHEN** the operator supplies a non-empty `consent.token`
- **THEN** the skill SHALL use the supplied token verbatim, regardless of which tier the phone number falls into

### Requirement: Consent Provenance Tagging

The skill SHALL record a `consent_provenance` field on every result file and audit-log entry, distinguishing calls whose consent fields were operator-supplied from calls whose consent fields were synthesized inline.

#### Scenario: Operator-supplied consent token
- **WHEN** the consent token used for the call was supplied by the operator (whether in structured or freeform form)
- **THEN** the result JSON at `<result_path>` and the audit-log entry in `consent-log.jsonl` SHALL include `"consent_provenance": "explicit"`

#### Scenario: Inline-synthesized consent token
- **WHEN** the consent token used for the call was synthesized by the skill under the default-allowlist tier
- **THEN** the result JSON at `<result_path>` and the audit-log entry in `consent-log.jsonl` SHALL include `"consent_provenance": "inline"`

### Requirement: Demo Mode Compatibility

The existing `--demo` flag SHALL continue to function unchanged: it routes the call to the first entry of callagent's resolved allowlist, skips the explicit consent check, and tags the result and audit-log entry with `demo: true`. When `--demo` is used with the freeform form, parsed `target.phone` is preserved in the audit log for traceability but does not affect routing.

#### Scenario: Demo flag with freeform invocation
- **WHEN** an operator invokes the skill with a freeform string and `--demo`
- **THEN** the skill SHALL parse all fields as usual, route the dialed call to the first allowlist entry, set `demo: true` on the result and audit-log entry, and set `consent_provenance: "inline"`
