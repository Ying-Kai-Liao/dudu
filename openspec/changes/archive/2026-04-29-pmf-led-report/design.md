## Context

`scripts/render-report.py` is the per-deal HTML renderer. Today it pulls `MEMO.md` and a fixed list of artifact files and emits a single-page HTML with TOC, all sections expanded by default, and personas as collapsibles. Every section is a flat dump of the underlying markdown.

The plugin's actual unique value lives in three artifacts the renderer never reads:

- `pitch.yaml` — the structured claim ledger emitted by `pmf-signal` Stage 0. One row per claim, with `category`, `source`, `verification` method, and the verbatim claim text.
- `personas/verdicts.yaml` — the verdict per claim, produced by PMF Stages 3a (persona-reaction), 3b (cross-artifact triangulation), and 3c (external-evidence web check). Verdict ∈ `{contradicts, partial, no-evidence, supports}` with evidence pointers.
- `personas/aggregates.yaml` — the calibrated population summary, used to drive verdict counts and confidence bands.

Plus `outreach.md` from PMF Stage 5 — the warm-path outreach list, ranked by warm-path quality (LinkedIn 1st-degree, alumni, prior-co overlap, etc.).

The result: a VC opens `report.html` and sees a long markdown dump that an LLM could have produced in any research workflow. The pmf-signal output — the part that actually justifies running this plugin — is invisible.

This change restructures the renderer's output so the unique value is the lede, with graceful degradation for deals that haven't run pmf-signal (or where pmf-signal crashed mid-run).

## Goals / Non-Goals

**Goals:**

- Lead the rendered HTML with three ★ sections sourced from `pitch.yaml`, `verdicts.yaml`, `aggregates.yaml`, and `outreach.md`: the claim ledger × verdict matrix (worst-news first), cross-artifact contradictions, and warm-path outreach top-N.
- Demote the existing artifact dump to collapsed drill-down sections.
- Preserve the calibrated-prior nuance: persona-reaction verdicts must visually carry the Stance B disclaimer (a calibrated prior, not signal); cross-artifact and external rows must not.
- Keep the renderer self-contained — stdlib Python only, no network assets, no external CSS, no JS frameworks.
- Tolerate every realistic input shape: full pmf-signal run (new layout), pmf-signal crashed after `pitch.yaml` (verdicts pending), pmf-signal crashed after markdown but not yaml (markdown fallback), legacy deal pre-pmf-signal (full legacy layout, no ★ sections).
- Maintain backward compatibility for `deals/ledgerloop/`, `deals/callagent/`, `deals/tiny/`.

**Non-Goals:**

- No SVG charts or interactive visualizations of verdict counts in v1 (deferred — recommendation in Decision 4).
- No change to any deal-on-disk artifact. The renderer reads what PMF already writes.
- No change to `MEMO.md` schema or how PMF emits `pitch.yaml` / `verdicts.yaml`.
- No cross-deal dashboard view. That's `fleet-runner-and-dashboard`.
- No change to the renderer's existing markdown→HTML helpers, escape rules, or section-heading-offset logic. Those are battle-tested and we leave them alone.
- No new external dependencies. PyYAML is already required by other scripts in the repo; the renderer can import it.

## Decisions

### Decision 1: Read `pitch.yaml` and `verdicts.yaml` directly; do not rebuild the ledger from `pmf-signal.md`

The renderer loads the structured yaml artifacts and joins them on `claim_id`. We do not parse `pmf-signal.md` markdown to recover the ledger.

**Why**: yaml is the canonical schema. Markdown is a derived view. Parsing markdown to recover structured data is fragile and re-introduces coupling that PMF's yaml-first design exists to avoid. The only time the renderer touches `pmf-signal.md` is the partial-input fallback (Decision 5).

**Alternative considered**: parse `pmf-signal.md` because it exists in older runs. Rejected — pmf-signal is new enough that yaml has always been the structured source; legacy deals predate pmf-signal entirely and don't have either file.

### Decision 2: Worst-news-first verdict ordering inside the ledger

Rank order for ledger rows: `contradicts` (red) > `partial` / `no-evidence` (yellow, ranked together) > `supports` (green). Within each group, sort by claim category (founder → product → market → traction → ask) to match how a partner reads.

**Why**: VCs are pattern-matching for red flags. The first thing they want to see is "what claims got knocked over." Putting supports at the top would bury the actual decision-relevant content.

**Alternative considered**: keep PMF's emit order (typically claim-category order). Rejected — that order serves PMF's internal pipeline, not the report reader. Keeping it would default to the boring rows on top.

**Tie-break**: if two rows have the same verdict and category, sort by `claim_id` ascending for stability.

### Decision 3: Verification-method badge per row, Stance B disclaimer only on persona-reaction rows

Each ledger row carries a small badge identifying its verification method:

- `persona-reaction` (calibrated prior — Stance B disclaimer applies)
- `cross-artifact` (real signal from prior dudu artifacts)
- `external` (real signal from bounded web checks)

Persona-reaction rows render the Stance B note inline (small italic caption: "Calibrated prior, not signal — see PMF stage 3a"). Cross-artifact and external rows render no such caption.

**Why**: this is the single most important nuance to communicate. PMF's persona-reaction is a calibrated prior — useful for ranking what to verify next, dangerous if mistaken for signal. The renderer must not let visual uniformity collapse that distinction.

**Alternative considered**: put all three into one badge style and only differentiate with text. Rejected — at-a-glance scanability is the whole point. Color and shape differentiation matters.

**Visual implementation**: three CSS-only badge variants (no images, no JS). Persona-reaction = grey outline + italic label; cross-artifact = solid blue; external = solid green. Defined in the same `<style>` block already inlined by `render-report.py`.

### Decision 4: Verdict counts as a styled table for v1; defer charting

The header gets a small "verdict summary" strip showing counts: `contradicts: N | partial: N | no-evidence: N | supports: N`. v1 renders this as a styled table or flex row of pill badges. SVG charts are not in this change.

**Why**: the charting decision (donut? stacked bar? heatmap by category?) deserves its own design pass and would balloon this change. A styled table communicates the same numbers and lets us ship.

**Alternative considered**: inline an SVG donut chart sized to the content. Deferred — the existing `_market_chart_svg` in `render-report.py` is a precedent for stdlib SVG, but verdict-count visualization has more design surface (categories × verdicts is a 2D space). Track as a follow-up.

### Decision 5: Partial-input tolerance — three branches, not flags

The renderer detects which of these three shapes it has and branches:

1. **Full** — `pitch.yaml` and `verdicts.yaml` both present. Render the full ★-led layout: header, recommendation, ledger, contradictions, outreach top-N, drill-down (collapsed), source artifacts.
2. **Pitch-only** — `pitch.yaml` present, `verdicts.yaml` absent. Render the ledger with every row's verdict cell as `pending` (italic grey badge). All other ★ sections that need verdicts (e.g., contradictions sourced from cross-artifact rows) are hidden with a single line: "PMF run incomplete — verdicts not yet generated." Outreach top-N still renders if `outreach.md` exists.
3. **Pmf-md-only** — neither yaml file is present, but `pmf-signal.md` is. Render `pmf-signal.md` markdown as a single fallback section in place of the three ★ sections. Log a stderr warning: "pmf-signal.md found but yaml artifacts missing; rendering markdown fallback."
4. **Legacy** — none of `pitch.yaml`, `verdicts.yaml`, or `pmf-signal.md` is present. Render the legacy artifact-by-artifact layout, all sections expanded (matches today's behavior). No ★ sections, no recommendation ribbon (unless MEMO has one).

**Why three branches plus legacy, not flags**: each branch corresponds to a real failure mode (pmf crashed mid-stage / yaml-emit step crashed but markdown survived / pre-pmf legacy deal). Encoding them in code paths gives clear error messages and stable rendering. A `--mode=full|partial|legacy` flag would push the detection responsibility onto the caller and break the "just run the renderer, it figures it out" workflow.

**Detection order**: check `pitch.yaml` and `verdicts.yaml` together first. If only `pitch.yaml`, branch 2. If neither yaml, check `pmf-signal.md` for branch 3. Otherwise branch 4 (legacy).

**No silent failures**: branches 2 and 3 emit a stderr warning naming the missing files and the chosen branch.

### Decision 6: MEMO.md is no longer the canonical structural input

Today the renderer drives section ordering off `MEMO.md`'s `## ` headings. After this change, the structural skeleton comes from `pitch.yaml` + `verdicts.yaml` (the ★ sections), and MEMO contributes only:

- **Recommendation**: pulled from `MEMO.md` `## Recommendation` (or whatever heading variant) → renders as the recommendation ribbon under the header.
- **Cross-artifact synthesis**: pulled from `MEMO.md` `## Cross-artifact Synthesis` → renders as the last drill-down section before "Source artifacts."

Other MEMO sections (TL;DR, Founders, Problem and Product, Customer Signal, Competitive Landscape, Market Sizing) are no longer used as renderer input — those drill-downs always come from the per-artifact files (`founder-*.md`, `market-problem.md` / `market-context.md`, `customer-discovery.md`, `competitive-landscape.md`, `market-sizing.md`). MEMO's section-by-section dump is duplicative with the artifacts and we drop it from the rendered output.

**Why**: MEMO is a cross-artifact synthesis document. Treating it as the renderer's structural skeleton was an artifact of the era when the renderer needed *some* table-of-contents source. Now that pitch.yaml + verdicts.yaml provide that, MEMO can return to being a synthesis document with two specific contributions (recommendation, synthesis) rather than the canonical structure.

**Alternative considered**: keep MEMO as a parallel TOC source for backward compat. Rejected — this would mean some users see MEMO sections rendered alongside artifact sections rendering the same content, doubling the report length for no reader benefit.

### Decision 7: Drill-down sections start collapsed

All drill-down sections (founders, problem, customer signal, competitive landscape, market sizing, personas, synthesis) render as `<details>` elements without the `open` attribute. Today they render as expanded `<section>`s (except personas, which is a hybrid).

**Why**: the entire point of the redesign is "lead with unique signal, drill down only if asked." Expanded by default contradicts that thesis.

**Persona collapsibles**: today, `personas/_context.md` is rendered with `open` and the rest closed. Under the new layout, all personas remain closed by default. The persona group itself is one of the drill-down sections, also closed.

**Alternative considered**: leave personas alone since they're already collapsibles. Rejected — being inside a collapsed parent section is fine; today's `_context.md` open-by-default is no longer aligned with "drill down only if asked."

### Decision 8: Outreach top-N — embed first 10, link the full list

The outreach section embeds the top-N (default 10) outreach targets inline as a styled table (name, company, warm-path source, warm-path quote / one-line rationale). The full list is linked as `outreach.md` in the source-artifacts section.

**Why**: 10 is enough to act on (a VC's first-week outreach plan) without overwhelming the report. Linking the full list keeps the rest accessible.

**Alternative considered**: link only, no embed. Rejected — the warm-path quote is the most decision-relevant artifact in the file. Forcing the reader to click through to a separate markdown file undermines the "unique value front-and-center" thesis.

**Source order**: `outreach.md` is parsed for its top-level list ordered by warm-path quality. Today's PMF outreach sorts strongest warm-path first (LinkedIn 1st-degree → alumni → prior-co overlap → 2nd-degree → cold). The renderer respects file order; it does not re-sort.

**N is configurable**: a constant `OUTREACH_TOP_N = 10` near the top of the renderer. Users who want more can edit it; we don't add a CLI flag in this change.

### Decision 9: Cross-artifact contradictions = the verdicts.yaml rows whose cross-artifact verification flags a conflict

A row qualifies for the contradictions section when:

- Its verification method is `cross-artifact`, AND
- Its verdict is `contradicts` or `partial`.

For each qualifying row, render: claim text (verbatim), the contradicting artifact and quoted snippet (from `verdicts.yaml`'s `evidence` field, which carries `{file, quote, line_hint}`), and a small `→ <file>` link.

**Why**: this is the section that "earns its keep" — founder-claim-vs-customer-interview-vs-market-data, surfaced with verbatim quotes. It's the most defensible section a VC can put in front of a partner.

**Alternative considered**: derive contradictions independently by re-scanning artifacts. Rejected — that's PMF stage 3b's job; the renderer should not re-do it.

**Empty-state**: if no rows qualify, the contradictions section is omitted entirely (no header, no placeholder).

## Risks / Trade-offs

- **[Risk] Reading yaml at render time changes failure modes.** Today the renderer survives any markdown shape; a malformed yaml could crash it. → Mitigation: wrap each yaml read in `try/except yaml.YAMLError`; on failure, log to stderr and fall back to the next branch (full → pitch-only → markdown-fallback → legacy). Never crash the renderer. Tasks add a fixture test for malformed yaml.
- **[Risk] Worst-news-first ordering is opinionated and might surprise users who expect alphabetical or category-grouped order.** → Mitigation: this is the intentional opinion of the change. Document it in the report's verdict-summary strip ("worst-news first") so the reader understands the order isn't arbitrary.
- **[Risk] Persona-reaction Stance B disclaimer is the kind of subtlety readers gloss over.** A small italic caption per row is easy to miss. → Mitigation: also add a one-line footer under the verdict-summary strip that explains the three verification methods. Small redundancy here is acceptable because the cost of a reader treating a calibrated prior as signal is high.
- **[Risk] The legacy branch is a maintenance burden.** Two rendering paths means two test suites. → Mitigation: the legacy branch is exactly today's renderer behavior; we keep it as a single function `render_legacy(deal_dir)` and don't touch it. The new branch is `render_pmf_led(deal_dir, pitch, verdicts, ...)`. Each is testable independently.
- **[Trade-off] We accept that MEMO.md sections (TL;DR, Founders, etc.) are no longer rendered.** Users who rely on those sections in MEMO will see them disappear. Acceptable because (a) the per-artifact files render the same content, (b) MEMO's role narrows to synthesis + recommendation, which is the right scope for that file.
- **[Trade-off] Embedding outreach top-10 inline grows the report by ~10 table rows.** Acceptable — that's a tiny addition compared to the existing artifact dump and the warm-path quotes are decision-relevant.
- **[Trade-off] No charting in v1.** A styled verdict-count strip is less impactful than a donut/heatmap. Accepted as a v1 cost; a follow-up change can add charts without redoing the layout.

## Migration Plan

1. Land this change with both rendering branches in place (new layout + legacy fallback). All four input shapes work on day one.
2. Run the renderer against `deals/ledgerloop`, `deals/callagent`, `deals/tiny` to confirm the legacy branch matches today's output (or close enough that no VC complains). Capture diffs in tasks.
3. Run the renderer against any deal that has completed `pmf-signal` (or a fixture deal under `tests/fixtures/`) to confirm the new ★-led layout renders correctly.
4. Update `README.md` with a short note: "report.html now leads with the calibrated claim ledger; legacy deals continue to render in the old layout."
5. **Rollback**: this change touches one file (`scripts/render-report.py`). If the new layout has a critical bug, revert the script to its prior state from git history. No data migration to undo.

## Open Questions

- **Should a `pending` verdict row in branch 2 (pitch-only) still appear in the worst-news-first ordering, or should it be its own group at the bottom?** Leaning toward its own group at the bottom — `pending` is not a verdict and shouldn't compete with real verdicts for top-of-report attention. Resolved: `pending` rows render after `supports`, sorted by claim_id, with a single italic group header "Verdicts pending."
- **What about claims whose `verification: persona-reaction` came back with verdict `partial` — does that count for the contradictions section?** No. The contradictions section is only for cross-artifact verification (Decision 9). Persona-reaction `partial` is a calibrated prior, not a contradiction. Resolved.
- **Does the recommendation ribbon need a graceful degradation when MEMO is missing or has no `## Recommendation`?** Yes — if MEMO is absent or lacks the section, the ribbon is omitted entirely (no placeholder). Resolved: code reads MEMO recommendation defensively; missing → no ribbon.
- **Should `outreach.md` parsing tolerate the absence of the file?** Yes — outreach is optional. If `outreach.md` doesn't exist, the warm-path section is omitted. Resolved.
