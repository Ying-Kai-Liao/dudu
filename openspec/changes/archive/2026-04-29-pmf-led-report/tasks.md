## 1. Input loading and branch detection

- [x] 1.1 Add yaml import at the top of `scripts/render-report.py`; confirm PyYAML is available in the plugin's environment and is acceptable as the renderer's only third-party dep
- [x] 1.2 Implement `load_pmf_inputs(deal_dir)` returning a dataclass with `pitch`, `verdicts`, `aggregates`, `outreach`, plus per-file load status (`present | missing | malformed`)
- [x] 1.3 Wrap each yaml read in `try/except yaml.YAMLError`; on parse failure, log a stderr message naming the file and treat the file as absent
- [x] 1.4 Implement `detect_branch(inputs, deal_dir)` returning one of `"full" | "pitch-only" | "markdown-fallback" | "legacy"` per the Decision 5 detection order in design.md
- [x] 1.5 Emit a stderr warning naming the missing files when the chosen branch is `pitch-only` or `markdown-fallback`

## 2. Claim ledger × verdict matrix

- [x] 2.1 Define a verdict severity rank: `contradicts`=0, `partial`=1, `no-evidence`=2, `supports`=3, `pending`=4
- [x] 2.2 Define a claim-category order: founder→product→market→traction→ask, with unknown categories sorted last alphabetically
- [x] 2.3 Implement `sort_ledger_rows(pitch, verdicts)` that joins on `claim_id`, applies severity rank, then category order, then `claim_id` ascending as tie-break
- [x] 2.4 Implement `render_ledger_row(row)` producing the table row HTML with columns: claim, category, source, verification method (badge), verdict (badge), evidence
- [x] 2.5 Add CSS for three verification-method badge variants (`persona-reaction` grey-outline-italic, `cross-artifact` solid blue, `external` solid green) and four verdict badge variants (red/yellow/green/grey-italic) inline in the existing `<style>` block
- [x] 2.6 Add an italic Stance B caption ("Calibrated prior, not signal — see PMF stage 3a") rendered inside the evidence cell when and only when `verification == persona-reaction`
- [x] 2.7 Render an italic group header "Verdicts pending" before any `pending` rows (used in the pitch-only branch)
- [x] 2.8 Render the verdict-counts strip in the section header (e.g. `contradicts: 3 | partial: 5 | no-evidence: 2 | supports: 9`) as a styled flex row of pill badges; include a one-line caption "worst-news first" + a one-line legend describing the three verification methods

## 3. Cross-artifact contradictions section

- [x] 3.1 Implement `select_contradiction_rows(verdicts)` returning rows where `verification == cross-artifact` AND verdict in `{contradicts, partial}`
- [x] 3.2 Implement `render_contradiction_entry(row)` showing claim text verbatim, the contradicting filename, the verbatim quote from `evidence.quote`, and a `→ <file>` link
- [x] 3.3 Omit the entire section (no header, no placeholder) when `select_contradiction_rows` returns an empty list
- [x] 3.4 Confirm a `persona-reaction` row with `partial` verdict does NOT appear in this section; add a unit-style fixture covering this

## 4. Warm-path outreach top-N

- [x] 4.1 Add module-level constant `OUTREACH_TOP_N = 10` near the top of the renderer
- [x] 4.2 Implement `parse_outreach(outreach_md_text)` extracting an ordered list of entries with fields name, company, warm-path source, rationale/quote — preserving source-file order, no re-sort
- [x] 4.3 Implement `render_outreach_section(entries)` embedding the first `OUTREACH_TOP_N` entries inline as a styled table; if total > `OUTREACH_TOP_N`, append "all <total> — see outreach.md" link; if total ≤ `OUTREACH_TOP_N`, omit the "see more" link and embed all entries
- [x] 4.4 Omit the section entirely when `outreach.md` does not exist; omit the section entirely when the file exists but parses to zero entries

## 5. Layout assembly and drill-down restructure

- [x] 5.1 Implement `render_pmf_led(deal_dir, inputs)` producing the new layout: header → recommendation ribbon → ledger → contradictions → outreach → drill-down → source artifacts
- [x] 5.2 Implement `render_recommendation_ribbon(memo_text)` extracting `## Recommendation` (case-insensitive) from MEMO.md; return empty string if missing or MEMO absent
- [x] 5.3 Move every existing drill-down section render into a `<details>` element WITHOUT the `open` attribute (founders, problem & product, customer signal, competitive landscape, market sizing, personas group, cross-artifact synthesis)
- [x] 5.4 Inside the personas drill-down, also remove the `open` attribute from the `_context.md` collapsible so all personas start closed
- [x] 5.5 Stop rendering MEMO.md sections that duplicate per-artifact files (TL;DR, Founders, Problem and Product, Customer Signal, Competitive Landscape, Market Sizing); keep only the recommendation ribbon and cross-artifact synthesis drill-down sourced from MEMO
- [x] 5.6 Update the source-artifacts list at the bottom to include `pitch.yaml`, `personas/verdicts.yaml`, `personas/aggregates.yaml`, `outreach.md`, and `pmf-signal.md` when present, alongside the existing artifact links

## 6. Branch wiring and legacy fallback

- [x] 6.1 Extract today's renderer body into `render_legacy(deal_dir)` and confirm its output matches the renderer's prior behavior byte-for-byte on a fixture deal
- [x] 6.2 Implement `render_pitch_only(deal_dir, inputs)` reusing `render_pmf_led` but forcing every verdict to `pending` and replacing the contradictions section with the single-line note "PMF run incomplete — verdicts not yet generated"
- [x] 6.3 Implement `render_markdown_fallback(deal_dir, inputs)` reusing `render_pmf_led` but replacing the three ★ sections with one section containing `pmf-signal.md` rendered through the existing `render_markdown` helper
- [x] 6.4 Wire the top-level entry point: detect the branch, dispatch to the correct render function, never crash on partial input

## 7. Backward-compat verification and fixtures

- [x] 7.1 Run the renderer against `deals/ledgerloop/` and confirm the legacy branch is selected and the output matches today's behavior
- [x] 7.2 Run the renderer against `deals/callagent/` and confirm legacy-branch rendering succeeds
- [x] 7.3 Run the renderer against `deals/tiny/` and confirm legacy-branch rendering succeeds
- [x] 7.4 Add a fixture under `tests/fixtures/pmf-led-report/full/` containing minimal `pitch.yaml`, `verdicts.yaml`, `aggregates.yaml`, `outreach.md`, and the legacy artifact files; assert the new layout renders with all three ★ sections
- [x] 7.5 Add a fixture under `tests/fixtures/pmf-led-report/pitch-only/` (only `pitch.yaml`); assert the pitch-only branch is selected and pending rows render
- [x] 7.6 Add a fixture under `tests/fixtures/pmf-led-report/md-fallback/` (only `pmf-signal.md`); assert the markdown-fallback branch is selected and stderr warning is emitted
- [x] 7.7 Add a fixture under `tests/fixtures/pmf-led-report/malformed-yaml/` (invalid yaml); assert renderer logs error, falls back, does not crash

## 8. Documentation and validation

- [x] 8.1 Update `README.md` (or equivalent docs) with a short note describing the new ★-led report layout and the four input-shape branches
- [x] 8.2 Add a comment block at the top of `scripts/render-report.py` summarizing the four branches and the priority order
- [x] 8.3 Confirm `lib/deal.md` still accurately describes the on-disk artifact layout (it should — this change does not modify any artifact)
- [x] 8.4 Run `openspec validate pmf-led-report` and resolve any findings
- [x] 8.5 Manual smoke test: open the rendered HTML for one full-branch deal in a browser with network disabled and confirm the page renders identically (self-contained constraint)
