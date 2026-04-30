## Why

Today's `diligence` skill orchestrates seven sub-skills end-to-end on a single deal. Two problems block where we want to go:

1. **The unique value is buried.** PMF simulation (the falsifiable claim ledger and persona-grounded verdicts) is the only deliverable a VC can't reproduce in an afternoon, but it's step 5 of 7 inside the orchestrator and never surfaces in the rendered HTML.
2. **The chain isn't fleet-safe.** Personas are produced shallowly in `market-problem` (Phase 2 self-play) and deeply in `pmf-signal` (N=15–200 simulation), with both writing into `deals/<slug>/personas/`. The `customer-discovery debrief` step is welded into the orchestrator's re-invocation logic. Neither the layers nor the schedule decompose cleanly when we want to run N startups in parallel.

This change separates the chain into two cleanly composable layers and decouples customer-debrief, so a future fleet runner can compose them without inheriting today's monolith.

## What Changes

- **NEW capability `background-check`**: a Layer 1 orchestrator that runs founder-check, market-context, competitive-landscape, and market-sizing. Cheap, public-source, parallel-safe. Produces a context bundle plus a claim-ledger seed.
- **NEW capability `market-context`**: a slimmed replacement for `market-problem`'s context-producing role. **BREAKING**: stops generating personas (`personas/_context.md`, `personas/persona-*.md`, Phase 2 self-play interviews). Phase 1 (web research bundle) and Phase 3 (synthesis) survive; Phase 2 is removed.
- **NEW capability `pmf-signal`** (codifies existing skill, with relaxed preflight): becomes the sole owner of the `personas/` namespace. Preflight gate switches from "every legacy artifact at every legacy path" to "Layer 1 bundle present" — independent of which orchestrator (or none) produced it.
- **NEW capability `customer-debrief`**: extracted from `diligence` step 4. Standalone, runnable any time transcripts exist under `deals/<slug>/inputs/`. Not gated on prep status.
- **BREAKING for orchestration**: `dudu:diligence` keeps working as a thin compatibility wrapper for one release — it now calls `background-check` then `pmf-signal` then waits for debrief — but the orchestration moves out of its SKILL.md. Removed in a later change.
- **Backward compatibility for existing deals**: `deals/ledgerloop/`, `deals/callagent/`, `deals/tiny/` keep their current artifact layout. Renderers detect both the old layout (mp.md owns personas) and the new layout (pmf-signal owns personas) and tolerate either.

## Capabilities

### New Capabilities

- `background-check`: Layer 1 orchestrator. Runs the cheap public-source diligence sub-skills and produces a context bundle and claim-ledger seed for downstream layers.
- `market-context`: Public-source market and problem context only. Replaces the context half of the old `market-problem` skill. No personas.
- `pmf-signal`: Layer 2 deep simulation. Codifies the existing skill's contract under a relaxed preflight rule and explicit ownership of the persona namespace.
- `customer-debrief`: Standalone debrief skill that synthesizes real interview transcripts into pain/WTP/objections artifacts. Independent of any orchestrator.

### Modified Capabilities

None — `openspec/specs/` is currently empty, so every capability spec in this change is new.

## Impact

- **Skills affected**: `skills/diligence/` (becomes a thin wrapper), `skills/market-problem/` (renamed/replaced by `skills/market-context/`, personas stripped), `skills/customer-discovery/` (debrief half extracted to `skills/customer-debrief/`), `skills/pmf-signal/` (preflight script relaxed). New skill: `skills/background-check/`.
- **Scripts affected**: `scripts/pmf-signal-preflight.py` (relaxed contract). New: none in this change. Renderers (`render-report.py`, etc.) untouched here — that's a separate change.
- **Plugin metadata**: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` updated to register new skills and mark `diligence` deprecated.
- **Existing deals**: backward-compat detection in any code that reads `deals/<slug>/personas/` so old (`market-problem`-authored) and new (`pmf-signal`-authored) layouts both render. No data migration of `deals/ledgerloop`, `deals/callagent`, `deals/tiny`.
- **Documentation**: `README.md`, `lib/deal.md` updated to describe the layer split. Old `diligence` SKILL.md kept for one release with deprecation notice.
- **Out of scope** (separate changes): fleet runner, dashboard renderer, PMF-led report.html, full removal of the `diligence` wrapper.
