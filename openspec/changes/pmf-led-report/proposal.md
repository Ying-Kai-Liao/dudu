## Why

The dudu plugin's unique deliverable — the calibrated claim ledger × verdict matrix produced by `pmf-signal` — never appears in the per-deal HTML report. Today's `scripts/render-report.py` renders `MEMO.md` plus six artifact-by-artifact sections (founders, problem, customer signal, competitive landscape, market sizing, personas), all expanded by default. A VC opening `report.html` sees the same artifact dump they could get from any LLM-driven research pass; the falsifiable claims, the verdicts, the cross-artifact contradictions, and the warm-path outreach (the four things that justify running PMF) are invisible. The report buries the lede on the only thing this plugin produces that a partner can't reproduce in an afternoon.

## What Changes

- **NEW capability `pmf-led-report`**: restructures the per-deal HTML to lead with three ★ sections — claim ledger × verdict matrix, cross-artifact contradictions, warm-path outreach top-N — sourced directly from `pitch.yaml`, `personas/verdicts.yaml`, `personas/aggregates.yaml`, and `outreach.md`. The existing artifact dump becomes a collapsed drill-down.
- **NEW**: worst-news-first verdict ordering (`contradicts` > `partial` / `no-evidence` > `supports`) inside the ledger.
- **NEW**: per-row verification-method badge (persona-reaction / cross-artifact / external) so VCs can tell calibrated priors from real signal at a glance. Stance B disclaimer remains on persona-reaction rows.
- **NEW**: cross-artifact contradictions section pulling quoted snippets and file pointers from prior dudu artifacts (founder claims vs customer interviews vs market data).
- **NEW**: warm-path outreach top-N (default 10) embedded inline with names + warm-path source quotes; full list linked to `outreach.md`.
- **MODIFIED**: `MEMO.md` is no longer the canonical input. It contributes only the recommendation ribbon and the cross-artifact synthesis sub-section; the headline structure pulls from `pitch.yaml` + `verdicts.yaml`.
- **MODIFIED**: drill-down sections (founders, problem, customer signal, competitive landscape, market sizing, personas, synthesis) start collapsed instead of expanded.
- **NEW**: partial-input tolerance — if `pitch.yaml` exists but `verdicts.yaml` is missing (PMF crashed mid-run), render the ledger with verdicts as `pending`. If `pmf-signal.md` exists but `verdicts.yaml` is missing, render `pmf-signal.md` markdown as a fallback section and log a stderr warning. If neither yaml exists (legacy pre-pmf-signal deal), fall back to the old artifact-by-artifact view with no ★ sections.
- **NEW**: backward compatibility for `deals/ledgerloop/`, `deals/callagent/`, `deals/tiny/` is non-negotiable — those deals must continue to render under the new code.
- **CONSTRAINT**: same as today — self-contained HTML, stdlib Python only, no network assets, no external CSS, no JS frameworks.

## Capabilities

### New Capabilities

- `pmf-led-report`: Per-deal HTML report renderer that leads with the calibrated claim ledger × verdict matrix, cross-artifact contradictions, and warm-path outreach top-N, with the legacy artifact dump demoted to collapsed drill-downs and graceful degradation when PMF artifacts are partial or absent.

### Modified Capabilities

None — `openspec/specs/` is currently empty, so the `pmf-led-report` capability is new.

## Impact

- **Scripts affected**: `scripts/render-report.py` is the primary surface. The renderer gains new readers for `pitch.yaml`, `personas/verdicts.yaml`, `personas/aggregates.yaml`, and `outreach.md`, a new ordering function for verdicts, and a new HTML scaffold (header → recommendation → ledger → contradictions → outreach → drill-down → source artifacts).
- **Artifacts read**: `pitch.yaml`, `personas/verdicts.yaml`, `personas/aggregates.yaml`, `outreach.md`, `manifest.json`, `pmf-signal.md` (fallback only). Existing reads of `MEMO.md`, `founder-*.md`, `market-problem.md` / `market-context.md`, `customer-discovery.md`, `competitive-landscape.md`, `market-sizing.md`, `personas/*.md` are preserved for the drill-down sections.
- **Artifacts NOT touched**: this change does not add, modify, or move any deal-on-disk artifacts. PMF still writes the same files; this change only reads them differently.
- **Existing deals**: `deals/ledgerloop/`, `deals/callagent/`, `deals/tiny/` keep their on-disk layout. The renderer detects whether `pitch.yaml` + `verdicts.yaml` exist and routes between the new ★-led layout and the legacy artifact-dump layout accordingly. No data migration.
- **Documentation**: `README.md` (or equivalent) gains a short note describing what the new report looks like. `lib/deal.md` is unchanged because the on-disk contract is unchanged.
- **Independent of other changes**: this change can ship before, alongside, or after `split-background-and-pmf-layers` (the L1/L2 split) and `fleet-runner-and-dashboard` (cross-deal dashboard). It does not depend on either and is not depended on by either.
- **Out of scope** (separate changes): the cross-deal fleet dashboard, any change to PMF stage outputs, any change to `MEMO.md` schema, SVG/charting visualizations of verdict counts (deferred — see design.md).
