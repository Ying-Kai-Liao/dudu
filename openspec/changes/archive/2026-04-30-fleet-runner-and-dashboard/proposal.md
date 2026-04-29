## Why

The foundation change `split-background-and-pmf-layers` makes the diligence chain composable, but the plugin still operates one deal at a time. A VC reviewing a batch of 10–40 startups today has to invoke the layered skills slug-by-slug and then mentally diff per-deal HTML reports to compare them. Two problems block the next phase:

1. **No fleet-scale orchestration.** Running L1 (`background-check`) across many slugs needs a concurrency cap and per-deal failure isolation. PMF (`pmf-signal`) is "the heaviest budget in the plugin" and must not silently fan out across every deal — it has to be opt-in.
2. **No cross-deal view.** Per-deal `report.html` files render single-deal context but tell you nothing about how 20 startups compare on founder credibility, claim verdict counts, or recommendation tilt. Triage requires a sortable matrix.

This change adds a fleet runner that composes the foundation's layers across N deals, plus a derived dashboard view.

## What Changes

- **NEW capability `fleet-run`**: an orchestrator skill that runs `background-check` across a list of deal slugs in parallel (default mode = "gate-then-deepen" — L1 on all deals, user picks subset for L2; alternative mode `--all` runs L1+L2 on every slug). Concurrency cap (`--concurrency N`, default 3) and optional token cap (`--max-tokens N`).
- **NEW**: `scripts/render-dashboard.py` produces `deals/_fleet/dashboard.html`. Rows = deals, columns = signal vectors (founder credibility, claim verdict counts, contradiction count, market size band, recommendation tilt, interview status). Sortable by column, click-row drills into the per-deal `report.html`. Self-contained HTML, stdlib Python only.
- **NEW**: `deals/_fleet/manifest.json` tracks fleet-run state — which slugs, which mode, concurrency, budget consumed, per-deal status (`pending` / `running` / `complete` / `failed`).
- **NON-BREAKING for single-deal flow**: `dudu:fleet-run --slug foo` on a single slug behaves identically to a layered call from the foundation change.
- **Per-deal failure is non-fatal**: a failed deal is marked `failed` in the fleet manifest with the error captured; the rest of the fleet continues.
- **Dashboard is a derived view**: it reads per-deal artifacts and stores no truth of its own. Re-runnable any time without state migration.
- **Fleet runner does not own customer-debrief**: debrief stays per-deal and async. The dashboard renders `interview status: pending` for deals with no `customer-discovery.md`.

## Capabilities

### New Capabilities

- `fleet-run`: Fleet-scale orchestrator that composes `background-check` and (optionally) `pmf-signal` across many deals with concurrency control, per-deal failure isolation, fleet-state tracking under `deals/_fleet/`, and a derived dashboard view.

### Modified Capabilities

None — `openspec/specs/` is currently empty, so every capability spec in this change is net-new.

## Impact

- **Skills affected**: new `skills/fleet-run/SKILL.md`. No edits to `background-check`, `pmf-signal`, or `customer-debrief` — fleet-run composes them as black boxes.
- **Scripts affected**: new `scripts/render-dashboard.py`. No edits to existing renderers (`render-report.py`, etc.).
- **Plugin metadata**: `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` register `fleet-run`.
- **Filesystem footprint**: new top-level directory `deals/_fleet/` containing `manifest.json`, `queue.txt` (optional input), and `dashboard.html` (rendered output). Per-deal directories are unchanged — the fleet runner writes nothing under `deals/<slug>/` beyond what its sub-skills already produce.
- **Documentation**: `README.md` gains a "Running a fleet" section. `lib/deal.md` documents the `_fleet/` reserved name.
- **Out of scope** (separate changes): customer-debrief automation across the fleet, MEMO.md stitching at fleet scale, dashboard customization beyond the fixed signal-vector columns, deletion of the `diligence` wrapper (tracked separately).
