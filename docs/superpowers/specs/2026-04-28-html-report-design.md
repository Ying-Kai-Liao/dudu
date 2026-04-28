# dudu — HTML report renderer

**Status:** Approved design
**Date:** 2026-04-28
**Owner:** Ying-Kai Liao
**Type:** Addition to the `dudu:diligence` orchestrator + new helper script

## Goal

Produce a single self-contained `report.html` per deal, generated as the final step of `dudu:diligence`. The HTML serves both discovery (one document to read, no folder hopping) and sharing (a partner can be emailed the file and open it in any browser). All existing markdown artifacts remain the source of truth — the HTML is a renderer over them, regenerated on demand.

## Non-goals

- Replacing `MEMO.md`. Markdown stays canonical; HTML is a derived view.
- A standalone `dudu:report` skill. The renderer is invoked by the orchestrator only.
- Auto-regeneration on every sub-skill. Only `dudu:diligence` calls the renderer.
- Network-loaded fonts, external stylesheets, CDN scripts, or any runtime dependency beyond Python 3 stdlib.
- Interactive features beyond collapsible sections (no popovers, no tabs, no filters in v1).
- Multi-deal index page or cross-deal navigation.

## Architecture

One Python helper script + a single orchestrator step.

- **New file:** `scripts/render-report.py`. Python 3, stdlib only. Reads a deal directory, writes `report.html` next to the artifacts.
- **Invocation:** `python3 scripts/render-report.py deals/<slug>`. Exit 0 on success, non-zero with a clear message on failure.
- **Orchestrator change:** `dudu:diligence` SKILL.md gains a final step (after stitching `MEMO.md`, before printing the path) that runs the script. If the script exits non-zero, the orchestrator surfaces the error but still reports `MEMO.md`'s path.
- **Inputs the script reads** (all optional except `manifest.json`):
  - `manifest.json` — required; if missing, the script aborts with a clear error.
  - `MEMO.md` — drives section ordering and the recommendation pill.
  - `founder-*.md` — one section per file.
  - `market-problem.md`, `competitive-landscape.md`, `market-sizing.md`, `customer-discovery-prep.md`, `customer-discovery.md` — each renders as its own section if present.
  - `personas/_context.md`, `personas/persona-*.md`, `personas/round-*.md` — collapsible group.
  - Anything else under `deals/<slug>/` (including `inputs/`, `deck.*`) is ignored — those are raw research inputs, not report content.
- **Output:** `deals/<slug>/report.html`. Self-contained: embedded CSS in a `<style>` block, embedded JS (only enough for sidebar scrollspy + smooth-scroll), no external assets, no fonts loaded from network.
- **Idempotent:** writes to a temp file (`report.html.tmp`) and renames. Re-running overwrites cleanly.

## Layout

Single page, three regions.

### Header bar (top, full width)

- Company name (H1), deal slug (small caps subtitle), generated timestamp (ISO).
- **Recommendation pill** — Pass / Watch / Pursue. Parsed from MEMO.md's Recommendation section by regex against `**Pass / Watch / Pursue:** <verdict>`. If unparseable or MEMO missing, render "Diligence in progress" instead.
- **Status dots** — six small circles, one per `manifest.json` `skills_completed` key, in fixed order: founder-check, market-problem, customer-discovery-prep, competitive-landscape, market-sizing, customer-discovery-debrief. Green if non-null, gray if null. Tooltip (`title` attr) shows the timestamp on hover.
- **Deal note callout** — yellow banner under the header if `manifest.json` has a `pitch_reframe_note` (or any future top-level note field). Renders the note verbatim. This is how the LedgerLoop pitch/founder mismatch surfaces prominently.

### Sticky left sidebar (240px, sticky on scroll)

Table of contents in the order MEMO uses, plus the personas group:

1. TL;DR
2. Founders (one entry per `founder-*.md`)
3. Problem & Product
4. Customer Signal
5. Competitive Landscape
6. Market Sizing
7. Cross-artifact Synthesis
8. Recommendation
9. Personas (collapsible group, expanded by default in sidebar; entries: `_context`, `persona-1..N`, `round-1..N`)
10. Source artifacts

Each entry is an anchor link. Active section highlights as the user scrolls (small JS scrollspy using IntersectionObserver). On viewports under 900px, sidebar collapses to a top toggle.

### Main content (max 800px column)

Sections appear in MEMO order. Each section's body is the rendered markdown of the corresponding artifact.

- **Personas section:** each persona/round file is a `<details>` block, summary = filename-derived title, collapsed by default. The `_context.md` is always rendered open.
- **Competitor matrix:** if `competitive-landscape.md` contains a pipe table, render it as `<table>`. Otherwise pass through as-is.
- **Citations:** markdown links `[text](url)` render as `<a href target="_blank" rel="noopener">`. No popover, no footnote aggregation in v1.
- **Market sizing chart:** small inline SVG bar chart comparing wedge-TAM range, expansion-TAM range, and founder claim. Numbers parsed from `market-sizing.md` by regex against the standard headings the skill produces (`## Wedge TAM`, `## Expansion TAM`, `## Founder claim` or similar). On any parse failure, skip the chart and render the markdown unmodified — never block the report on missing chart data.

### Style

- Typography: serif headings (`Georgia, 'Times New Roman', serif`), sans body (`system-ui, -apple-system, sans-serif`).
- Palette: white background, near-black body text (`#1a1a1a`), single accent color (`#2563eb` blue) for links and the recommendation pill. Subtle border-gray (`#e5e7eb`) for dividers and the sidebar separator.
- Recommendation pill colors: Pass = red-600 bg, Watch = amber-500 bg, Pursue = green-600 bg. White text on all three.
- No animations beyond a 200ms scroll behavior.
- Print stylesheet: hide sidebar, full-width content, page-break before each top-level section.

## Markdown rendering

The script implements a small markdown subset matching what dudu skills actually output. Line-by-line state machine, no nested-grammar parser. Supported:

- Headers `#` through `####` → `<h1>`–`<h4>`.
- Paragraphs (blank-line separated).
- Ordered (`1.`) and unordered (`-`, `*`) lists, one level of nesting.
- Bold (`**...**`), italic (`*...*` or `_..._`), inline code (`` `...` ``).
- Fenced code blocks (` ``` `).
- Blockquotes (`>`).
- Links `[text](url)`.
- Pipe tables (`| a | b |` with separator row).
- HTML escaping: `<`, `>`, `&`, `"` escaped before any markdown processing.

Anything else (HTML pass-through, footnotes, definition lists, images) is escaped and rendered as plain text. We accept that some rare formatting won't render perfectly; the source `.md` is always one click away in the file system.

## Failure modes

| Condition | Behavior |
|-----------|----------|
| `manifest.json` missing | Script exits 1 with `"deals/<slug>/manifest.json not found"`. Orchestrator surfaces error, MEMO.md is still printed. |
| `MEMO.md` missing (partial run) | Render header without recommendation pill ("Diligence in progress" label). Skip TL;DR, Cross-artifact Synthesis, Recommendation sections. Render whatever sub-artifacts exist. |
| Sub-artifact missing | Skip that section silently. Sidebar entry omitted. |
| Market-sizing numbers unparseable | Skip the SVG chart. Render the markdown text only. No error surfaced. |
| Python 3 not on PATH | Orchestrator catches the spawn failure and prints: `"report.html skipped — install Python 3 or run python3 scripts/render-report.py deals/<slug> manually."` MEMO.md is still produced. |
| Re-run | Write to `report.html.tmp`, rename atomically. No partial-write window. |
| Pipe table malformed | Treat as plain paragraph. |

## Testing

- **Manual fixture:** `test/ledgerloop/` is the committed hackathon demo and contains a complete (minus debrief) run. Render against it and inspect the result in a browser. This is the primary acceptance test. The script must accept arbitrary deal directories — `deals/<slug>/` (gitignored, real runs) and `test/ledgerloop/` (committed, demo) work the same way.
- **Lint:** add a render smoke check (new `scripts/check-render.sh` or extension to `scripts/lint-skills.sh`) that runs `python3 scripts/render-report.py test/ledgerloop` and asserts exit 0 plus that `test/ledgerloop/report.html` exists with a non-empty `<body>`. Skip the assertion if `python3` is not on PATH.
- **Unit-level:** none. The script is small enough that the fixture render is sufficient verification.
- **Demo artifact:** commit the rendered `test/ledgerloop/report.html` so reviewers of the hackathon submission can open it directly.

## Files touched

| Path | Change |
|------|--------|
| `scripts/render-report.py` | New. ~200–300 lines. |
| `skills/diligence/SKILL.md` | Insert a new step between current step 6 (verify manifest) and step 7 (print path): invoke `python3 scripts/render-report.py deals/<slug>`, surface errors but don't block, then update the final print to mention `report.html` next to `MEMO.md`. |
| `README.md` | One-line addition to the orchestrator workflow describing `report.html`, plus a Demo-section mention that the rendered HTML is checked in under `test/ledgerloop/`. |
| `test/ledgerloop/report.html` | New, committed. The rendered demo so reviewers can open it without running the renderer. |
| `.gitignore` | No change. `deals/` stays ignored; `test/` stays tracked. |
| `scripts/lint-skills.sh` or new `scripts/check-render.sh` | Add a smoke test that renders `test/ledgerloop/` and asserts the output exists. |

## Open questions

None. The design is ready for implementation.
