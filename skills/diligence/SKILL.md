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
   2. `dudu:market-problem`
   3. `dudu:customer-discovery prep`
   4. `dudu:competitive-landscape`
   5. `dudu:market-sizing`

3. **Pause for real interviews.** After the five sub-skills, print:

   > Prep complete. The next step is yours: reach out to the candidates in `deals/<slug>/customer-discovery-prep.md` and run 5–10 real interviews. Save transcripts under `deals/<slug>/inputs/`. When done, re-run `dudu:diligence` and I'll continue with the debrief and final memo.

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
- customer-discovery.md
- competitive-landscape.md
- market-sizing.md
```

6. **Verify manifest completeness.** All six sub-skill keys in `skills_completed` should now be non-null (`founder-check`, `market-problem`, `customer-discovery-prep`, `customer-discovery-debrief`, `competitive-landscape`, `market-sizing`). Do not invent additional keys; the orchestrator's completion is implicit in those six.

7. **Print** the path to `MEMO.md`.

## Re-runnability

Each sub-skill checks its own artifact and skips if present (unless `--force`). The orchestrator therefore can be re-run safely; only missing pieces will be filled.
