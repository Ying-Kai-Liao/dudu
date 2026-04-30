# dudu — `report.html` dashboard redesign

**Status:** Approved design
**Date:** 2026-04-30
**Owner:** Ying-Kai Liao
**Type:** Addition to `scripts/render-report.py`; no skill or orchestrator changes

## Goal

Add a 5-card executive dashboard to the top of `report.html` that mirrors the partner-meeting "AI Due Diligence Report" mockup style. Each card summarises one stage of the dudu pipeline with a number, a status pill, and a "Read more" link to the existing detailed section. The current detailed report (claim ledger, contradictions, outreach, drill-downs, personas, source artifacts) is preserved verbatim but moves below the dashboard and is collapsed by default — a Wikipedia-style references region.

The mockup is a **style reference**, not a content contract. We adapt the cards so each one maps to a real dudu artifact; we do not invent fields like "Stage of Startup" that no artifact captures today.

## Non-goals

- Replacing the long-form report. Existing sections render unchanged below the dashboard.
- New authored fields in `manifest.json` (`stage`, `industry`, etc.). Everything is derived from existing artifacts.
- Founder photos / LinkedIn scraping. Initials avatars only.
- Changes to `dudu:diligence`, `dudu:auto-diligence`, or any skill. Renderer-only change.
- Touching `scripts/render-dashboard.py` (different tool — fleet-level summary, not per-deal).
- A new HTML branch. The dashboard is shared across `full`, `pitch-only`, `markdown-fallback`, and `legacy` branches.
- Multi-deal navigation, cross-deal aggregation, or printable PDF tuning.

## Architecture

Single function, called from each existing render branch.

- **New function:** `render_dashboard(deal_dir, manifest, memo_sections, inputs) -> str`. Returns an HTML string for the 5-card grid, or empty string if no card has data.
- **Call sites:** `render_pmf_led` (covers `full` and `pitch-only`), `render_legacy`, `render_markdown_fallback`. Each one inserts the dashboard HTML into `pre_main_html` immediately after the recommendation ribbon.
- **Each card is its own helper** (`_card_founders`, `_card_personas`, `_card_calls`, `_card_market`, `_card_competitors`). A card returns either an HTML string or `None`. The dispatcher renders only cards that returned a string and slots them into the grid in fixed order.
- **No new branch logic.** If a card's data source is missing the card is dropped, matching the existing "render only what exists" pattern.
- **Dashboard CSS** lives in a new constant `DASHBOARD_CSS` appended to the `<style>` block in `_build_html_skeleton`. Existing CSS is untouched.
- **JS:** one new client-side dependency, `wavesurfer.js` (~30 KB), embedded inline in the report so the file stays self-contained per the original report spec ("no external assets, no fonts loaded from network"). Loaded only if the calls card is present.
- **Audio download:** new helper `_ensure_local_recording(call_json_path) -> Path | None` reads `recording_url` from a `calls/demo-*.json`, downloads the WAV to `calls/recordings/<call-id>.wav` if not already cached, returns the local path. Network failure → returns `None` and the card falls back to streaming the Vapi URL directly.

## Card specifications

The dashboard renders up to five cards in a CSS grid. Order is fixed (matches the pipeline). Cards drop silently when data is unavailable.

### Card 1 — Founders' Background

- **Source:** `founder-*.md` files in the deal directory.
- **Visible content per founder:** initials in a coloured circle (deterministic colour from name hash), name, four green-check badges:
  - **LinkedIn** — present if `founder-*.md` contains a `linkedin.com/in/` URL.
  - **Experience** — present if any `## Experience` / `## Background` / `## Career` heading exists.
  - **Track Record** — present if `## Prior ventures` or `## Prior partner contacts` heading exists.
  - **Connections** — present if any `## Network` / `## References` / `## Prior partner contacts` heading exists.
- **Risk Level pill:** `LOW` / `MED` / `HIGH`. Derived: count `## Risks`, `## Open questions`, `## Controversies` bullet items across all founders. `0` → LOW, `1–3` → MED, `4+` → HIGH.
- **Card hidden if** no `founder-*.md` files exist.
- **Read more →** anchors to `#founder-<slug>` for the first founder.

### Card 2 — PMF Personas

- **Source:** `personas/aggregates.yaml` + `personas/verdicts.yaml` (both optional).
- **Persona-trigger pills:** keys of `aggregates.yaml.by_trigger_type`, ordered by descending count, max 3 visible.
- **Top Pain Points bars:** the three highest-count `by_trigger_type` entries; bar length proportional to count / max(count).
- **Fit Score (out of 10):** `(would_use.yes + 0.5 * would_use["yes-with-caveats"]) / would_use.n × 10`, formatted to one decimal. Hidden if `would_use` block is missing.
- **PMF Consensus pill:**
  - Count verdicts in `verdicts.yaml` by status.
  - `supports >= 2 × contradicts AND fit_score >= 7` → `HIGH`
  - `supports >= contradicts` → `MED`
  - else → `LOW`
  - If `verdicts.yaml` is missing entirely → omit the pill.
- **Card hidden if** neither `aggregates.yaml` nor `verdicts.yaml` exists.
- **Read more →** anchors to `#ledger`.

### Card 3 — Real Call Insights

- **Source:** `calls/demo-*.json` (excluding files matching `*-rerun-*`) + `calls/demo-validation.md`.
- **Hero row:** waveform canvas (`wavesurfer.js`) + audio controls. Audio source is the first call's local `.wav` file (downloaded from `recording_url` to `calls/recordings/<call-id>.wav` at render time, cached on second run). On download failure, falls back to the remote `recording_url` directly.
- **Metrics:**
  - **Calls Completed** = count of non-rerun `demo-*.json` files.
  - **Positive Signal %** = share of those calls whose `structured_data` has a non-empty positive-pain field. Specifically: any of `pain_described`, `current_solution_friction`, or `wtp_signal` present and truthy. Formula: `round(positive / total × 100)`.
- **Pull-quote:** the longest single-line summary from the `Read` column of the markdown table in `demo-validation.md`. Truncated to 180 chars with ellipsis.
- **Card hidden if** zero `demo-*.json` files exist (so deals that never ran callagent get no card).
- **Read more →** anchors to `#demo-call-validation`.

### Card 4 — Market Sizing

- **Source:** `market-sizing.md`. Reuses existing `parse_market_sizing` + `_market_chart_svg` helpers.
- **Industry tag:** parsed from the first occurrence of `**Industry:**`, `**Sector:**`, or `## Industry` in `market-sizing.md` or MEMO. Fallback: empty.
- **Market Size (TAM):** the upper end of the `Total addressable` range from `parse_market_sizing`, formatted as `$X.YB` (or `$XM`).
- **Growth Rate:** first regex match of `(\d+(?:\.\d+)?)\s*%\s*CAGR` in `market-sizing.md`. Hidden if no match.
- **Mini sparkline:** small inline SVG of the TAM/SAM/SOM funnel using existing `_market_chart_svg` data, scaled down to ~120×40 px.
- **Card hidden if** `market-sizing.md` does not exist or `parse_market_sizing` returns no usable ranges.
- **Read more →** anchors to `#market-sizing`.

### Card 5 — Competitive Landscape

- **Source:** `competitive-landscape.md`.
- **Top 3 competitors:** parsed by:
  1. First, look for a markdown table with a `Competitor` column → take the first three names from rows.
  2. If no table, look for `## ` H2 headings whose text is a single proper noun → first three.
  3. If neither, scan the first paragraph for capitalised words ≥3 chars (heuristic fallback).
- **Threat-strength bars:** rank-based for v1 — first competitor 100%, second 75%, third 50%. We do not attempt to score threat from text in v1.
- **Market Opportunity pill:** `HIGH` / `MED` / `LOW`, taken from the existing recommendation ribbon's `Recommendation` line if it parses to one of those values, else `MED`.
- **Card hidden if** no `competitive-landscape.md`.
- **Read more →** anchors to `#competitive-landscape`.

## "Wikipedia-style" references region

The existing detailed sections — claim ledger, contradictions, outreach, drill-downs, personas, source artifacts — already exist in the renderer and stay structurally unchanged. The change is a framing one:

- The detailed sections sit below the dashboard and remain **expanded by default**, exactly as today. The Wikipedia analogy is: dashboard = lead/infobox, detailed sections = body, TOC = sidebar — not collapsed-drawers. The existing drill-down `<details>` blocks (founders, problem, market-sizing, etc.) keep their current open/closed defaults set by the existing renderer; we do not re-wrap them.
- The recommendation ribbon and TOC are unchanged.
- Each dashboard card's `Read more →` link is a plain anchor (`<a href="#ledger">`). Existing scroll-spy behaviour in the report's inline JS already highlights the right TOC entry. No new JS is needed for navigation.
- The existing TOC remains the navigation index; we do not duplicate it as a "References" list.

This makes the top-of-page view dramatically more legible without disturbing the analyst's existing scrollable-and-readable workflow.

## Visual style

Embedded in the existing `<style>` block.

- **Page background:** `#fafbff` (very pale violet).
- **Card surface:** `#ffffff`, `border-radius: 16px`, `box-shadow: 0 1px 2px rgba(15,23,42,0.06), 0 8px 24px rgba(80,72,229,0.06)`.
- **Card chip:** `1.4rem` square, `#7c5cff` background, white digit, `border-radius: 8px`, top-left.
- **Status pills:** reuse existing dudu pill colours (green `--ok`, amber `--watch`, red `--risk`) — we do not introduce a new palette.
- **Layout:** `display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;` for row 1; row 2 spans 3 cols with `grid-template-columns: 2fr 1fr` (Market wide, Competitors narrow — closer to the mockup's bottom row proportion). Single column under `800px`.
- **Dashboard wrapper:** `padding: 1.5rem 2rem; border: 1px solid var(--line); border-radius: 20px; background: linear-gradient(180deg, #ffffff, #fbfbff);` to match the mockup's enclosing card.

## Audio download (new helper)

```python
def _ensure_local_recording(deal_dir: Path, call_json_path: Path) -> Path | None:
    """Download recording_url from a call JSON to calls/recordings/<call-id>.wav.

    Returns the local path on success, None on any failure.
    Idempotent: if the local file already exists with non-zero size, return it.
    """
```

- Reads `recording_url` from the JSON.
- Derives `call-id` from the JSON filename stem (e.g., `demo-billing-reconciliation`).
- Local target: `deal_dir / "calls" / "recordings" / f"{call_id}.wav"`.
- Creates the parent dir if missing.
- Uses `urllib.request.urlopen` with a 30 s timeout; writes to `<target>.tmp` then renames.
- On any exception (network, disk, missing field), logs to stderr and returns `None`.
- The function is called only by Card 3.

## Wavesurfer.js embedding

- Vendored as `scripts/vendor/wavesurfer-7.x.min.js`, loaded into a Python string constant at render time via `Path.read_text()`.
- Embedded inline as `<script>...</script>` in the report — only when Card 3 renders.
- Initialised against the card's `<div id="waveform-{call-id}">` after `DOMContentLoaded`.
- One waveform per card (the hero call). The Drill-down section keeps its existing simple `<audio>` controls list — no waveforms there.

## Graceful degradation

- All five cards are independent. The dashboard renders whatever cards have data; the others are dropped without leaving an empty grid cell (the grid uses `grid-auto-flow: dense`).
- If zero cards have data, `render_dashboard` returns `""` and the report renders identically to today (no dashboard wrapper, no leftover styling).
- The `legacy` branch (no `pitch.yaml`) gets the same dashboard logic — Cards 1, 4, 5 still render based on per-artifact files.
- The `markdown-fallback` and `pitch-only` branches likewise get whichever cards have data.
- No new failure modes: every card helper catches its own parse errors and returns `None` on any exception.

## Testing

- **Manual:** re-render `deals/dimely/report.html` (full branch, has all five sources) and `deals/callagent/report.html` (idea-validation branch, may have zero cards) and visually verify.
- **Render-time idempotence:** running the script twice in a row must produce the same `report.html` modulo timestamp lines, and must not re-download already-cached recordings.
- **Empty-data fixture:** add a tiny test deal under `tests/fixtures/empty-deal/` with only `manifest.json`. The renderer must produce a valid HTML with no dashboard wrapper.

## Backwards compatibility

- The output filename and location are unchanged (`deals/<slug>/report.html`).
- The recommendation ribbon, TOC, drill-down sections, and source artifacts list are byte-equivalent to today (modulo their being wrapped in `<details>`).
- The new `calls/recordings/` directory is created lazily; if a deal doesn't have callagent calls, no new directory appears.
- The added file size from `wavesurfer.js` (~30 KB) is paid only when Card 3 is present.

## Out of scope (explicitly deferred)

- Real waveform pre-computation server-side (we use client-side wavesurfer instead).
- Authoring fields in `manifest.json` for stage/industry/photo URL.
- Founder photo fetching.
- Per-call waveforms in the drill-down (only the hero call gets a waveform).
- Threat-scoring competitors from text content.
- Multi-deal index page.
