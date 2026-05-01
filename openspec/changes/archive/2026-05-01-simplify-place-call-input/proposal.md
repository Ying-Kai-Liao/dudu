## Why

`dudu:place-call` requires a six-field structured input bundle (`slug`, `purpose`, `target.name`, `target.phone`, `consent.opted_in`, `consent.token`) before it will dial. For routine internal testing against the default-allowlisted dev numbers — which is the most common reason the skill is invoked during development — this ceremony is friction without forensic value, because the auto-generated tokens those calls produce don't trace back to a real consent artifact anyway. Operators want to type something closer to `"dimely, Desmond, ask pmf question, +61459529124"` and have the skill figure the rest out.

## What Changes

- Accept a **freeform invocation form** alongside the existing structured form: a single string with comma-separated `slug`, `target.name`, `topic`, and an embedded E.164 number. The structured form continues to work unchanged (additive, non-breaking).
- Add a **topic-to-purpose inference table**: topics containing `reference` map to `reference-check`; topics containing `pmf`/`pain`/`discovery`/`interview` map to `screener`; everything else maps to `custom`.
- Extend the **`custom` purpose** to auto-author a brief from the `topic` string + relevant deal artifacts (`pmf-signal.md`, `personas/`, founder dossiers), instead of hard-exiting as it does today. Hand-authored briefs via `--task-path` continue to take precedence.
- Replace the binary consent gate with a **tiered consent gate**:
  - When `target.phone` is on callagent's default allowlist (the three dev/test numbers), auto-default `consent.opted_in: true` and synthesize `consent.token = "inline-<iso-date>-<kebab(target.name)>"`.
  - When `target.phone` requires `CALLAGENT_ALLOWED_NUMBERS` to be exported (any non-default-allowlist number), continue to require explicit `consent.token` and refuse with a clear message if missing. Explicit `consent.opted_in` is no longer required even here — supplying a token *is* the assertion.
- Tag every result file and audit-log entry with a new field `consent_provenance: "inline" | "explicit"` so forensics can distinguish casual test calls from real outbound calls.

## Capabilities

### New Capabilities
- `place-call`: Outbound voice-call orchestration over `callagent` for deals under evaluation, including input parsing, brief authoring, consent gating, dialing, and result capture.

### Modified Capabilities
<!-- None — this change introduces the place-call capability spec for the first time. -->

## Impact

- **Code**: `skills/place-call/SKILL.md` — input parsing, pre-flight tier logic, custom-purpose authoring branch, audit-log field addition. No changes to `tools/callagent/` (callagent's own consent gate remains as-is; the skill is the only layer that changes).
- **Callers**: `dudu:auto-diligence`, `dudu:founder-check`, `dudu:pmf-signal` — unaffected, since the structured form remains valid. Verified by leaving the structured-form contract identical.
- **Audit log shape**: `consent-log.jsonl` entries gain a `consent_provenance` field. Existing entries (without the field) remain readable; downstream consumers should treat absence as `"explicit"`.
- **Result file shape**: `deals/<slug>/calls/*.json` gains a top-level `consent_provenance` field. `dudu:customer-debrief` and the founder-dossier reference-check appender currently ignore unknown fields, so additive only.
- **Risk**: Auto-authored `custom` briefs are the highest-risk surface; quality depends on topic-string clarity and deal-context completeness. Mitigation: require a `--demo` smoke run on a non-trivial topic before relying on the new path for real calls.
