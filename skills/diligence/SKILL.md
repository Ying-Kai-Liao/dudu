---
name: diligence
description: Orchestrates the full dudu due-diligence workflow for a deal. Runs founder-check, market-problem, customer-discovery prep, competitive-landscape, market-sizing, pauses for the VC's real customer interviews, then runs customer-discovery debrief and stitches the final memo.
---

# Diligence orchestrator

Run the full dudu workflow end-to-end on one deal. Read `lib/deal.md`, `lib/playwright-auth.md`, and `lib/research-protocol.md` before starting.

## Inputs (prompt if missing)

- Deal slug (kebab-case)
- Company name
- Founder names (one or more)
- One-line pitch
- Pitch deck (file path or pasted text), optional but strongly preferred

## Steps

1. **Initialize deal directory.** If `deals/<slug>/` does not exist, create it. Write `manifest.json` per the schema in `lib/deal.md`. If supplied, save the deck to `deals/<slug>/inputs/deck.<ext>` (or `deck.md` if pasted text).

2. **Run sub-skills in this order**, each as a sub-invocation. After each, confirm the artifact exists before moving on. If the user passed `--force`, propagate it to each sub-skill.

   1. `dudu:founder-check` — for each founder
   2. `dudu:market-problem` — full Phases 1+2+3
   3. `dudu:competitive-landscape`
   4. `dudu:market-sizing`
   5. `dudu:pmf-signal` — emits `pmf-signal.md`, `outreach.md`, and the legacy-shape `customer-discovery-prep.md` as a side effect of stage 5

3. **Pause for real interviews.** After the five sub-skills, print:

   > Prep complete. The next step is yours: read `deals/<slug>/pmf-signal.md` for the calibrated PMF signal and consolidated claim ledger, then reach out to the candidates in `deals/<slug>/outreach.md` (sorted by warm-path quality) and run 5–10 real interviews. Save transcripts under `deals/<slug>/inputs/`. When done, re-run `dudu:diligence` and I'll continue with the debrief and final memo.

   Stop. Do not proceed.

4. **On re-invocation**, detect that prep is done and inputs exist:
   - If `customer-discovery-prep.md` exists AND `inputs/` contains at least one file AND `customer-discovery.md` does not exist → run `dudu:customer-discovery debrief`, then continue to step 5.
   - If everything is done → skip straight to step 5.

5. **Stitch `MEMO.md`.** Read every artifact under `deals/<slug>/` and produce `deals/<slug>/MEMO.md`:

```markdown
# Investment memo: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## TL;DR

[3-5 sentences. Founder credibility, problem severity, market size, competitive position, recommendation tilt.]

## Founders

[For each founder, summarize from `founder-<name>.md` in 3-5 bullets. Link to the full dossier.]

## Problem and product

[Summary from `market-problem.md` (4-6 sentences) + the strongest pattern + the most valuable contradiction. Link to the full file.]

## PMF signal & claim verification (calibrated prior + cross-artifact + external)

[Headline read from `pmf-signal.md`. The top 5 rows of the consolidated claim ledger (worst-news-first ordering). The 1 strongest cluster pattern. Explicit Stance B disclaimer for the persona-reaction rows; cross-artifact and external-evidence rows do not need the same disclaimer because they triangulate against actual evidence. List of `requires-data-room` flags for the VC to follow up on.]

## Customer signal

[Summary from `customer-discovery.md`. Quote 2-3 strongest verbatims. Flag any persona contradictions explicitly.]

## Competitive landscape

[Summary from `competitive-landscape.md`. Top 3 direct competitors. Incumbent verdict. Moat verdict.]

## Market sizing

[Wedge TAM range, expansion TAM range, comparison to founder claim.]

## Cross-artifact synthesis

[New section. Surfaces contradictions ACROSS artifacts. e.g.: "Founder claims engineering teams are the buyer (deck p.3), but customer interviews showed product managers driving the purchase (interview-2)." This is where the orchestrator earns its keep.]

## Recommendation

- **Pass / Watch / Pursue:** <verdict>
- **Why:** [3 sentences]
- **What would change my mind:** [2-3 specific things to verify]

## Source artifacts

- founder-<name>.md
- market-problem.md
- pmf-signal.md
- outreach.md
- customer-discovery.md
- competitive-landscape.md
- market-sizing.md
```

6. **Verify manifest completeness.** All seven sub-skill keys in `skills_completed` should now be non-null (`founder-check`, `market-problem`, `customer-discovery-prep`, `customer-discovery-debrief`, `competitive-landscape`, `market-sizing`, `pmf-signal`). Do not invent additional keys; the orchestrator's completion is implicit in those seven.

7. **Render `report.html`.** Run `python3 scripts/render-report.py deals/<slug>`. The script reads `MEMO.md` and the artifacts and writes a single self-contained `deals/<slug>/report.html` — embedded CSS/JS, no network assets, openable in any browser. Markdown stays canonical; HTML is a derived view safe to share as a file.

   - If the script exits non-zero (missing `manifest.json`, parse error), surface the stderr message but **do not** block — `MEMO.md` is still useful on its own.
   - If `python3` isn't on PATH, print: `report.html skipped — install Python 3 or run python3 scripts/render-report.py deals/<slug> manually.`

8. **Print** the paths to `MEMO.md` and (if rendered) `report.html`.

## Re-runnability

Each sub-skill checks its own artifact and skips if present (unless `--force`). The orchestrator therefore can be re-run safely; only missing pieces will be filled.
