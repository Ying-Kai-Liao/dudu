---
name: diligence
description: DEPRECATED — thin compatibility wrapper. Calls dudu:background-check (Layer 1), dudu:pmf-signal (Layer 2), then dudu:customer-debrief on re-invocation if transcripts exist, then stitches MEMO.md and renders report.html. The layered skills are the canonical entry points; this wrapper exists for one release window and will be removed by the deprecate-diligence-orchestrator change.
---

# Diligence orchestrator (deprecated)

> ⚠️ **Deprecated.** This skill is now a thin pass-through over the layered skills. Prefer invoking the layers directly:
>
> ```
> dudu:background-check     # Layer 1: founder + market context + competitive + sizing
> dudu:pmf-signal           # Layer 2: claim ledger × verdict matrix + warm-path outreach
> dudu:customer-debrief     # standalone, runs whenever transcripts exist under inputs/
> ```
>
> The wrapper will be removed by the `deprecate-diligence-orchestrator` change after one release of overlap.

Read `lib/deal.md`, `lib/playwright-auth.md`, and `lib/research-protocol.md` before starting.

## Inputs (prompt if missing)

- Deal slug (kebab-case)
- Company name
- Founder names (one or more)
- One-line pitch
- Pitch deck (file path or pasted text), strongly preferred

## Steps

1. **Print deprecation notice** (the block above) before doing anything else, so users see the layered alternative on every invocation.

2. **Initialize deal directory.** If `deals/<slug>/` does not exist, create it. Write `manifest.json` per the schema in `lib/deal.md`. If a deck was supplied, save it to `deals/<slug>/inputs/`.

3. **Run Layer 1: `dudu:background-check`** with the same arguments. Propagate `--force` if supplied. This produces `founder-*.md`, `market-context.md`, `competitive-landscape.md`, `market-sizing.md`, and the L1 sentinel `background.md`.

4. **Run Layer 2: `dudu:pmf-signal`**. Propagate `--force` if supplied. This produces `pmf-signal.md`, `outreach.md`, and the legacy-shape `customer-discovery-prep.md` (Stage 5 side effect).

5. **Pause for real interviews.** After Layer 2, print:

   > Prep complete. The next step is yours: read `deals/<slug>/pmf-signal.md` for the calibrated PMF signal and consolidated claim ledger, then reach out to the candidates in `deals/<slug>/outreach.md` (sorted by warm-path quality) and run 5–10 real interviews. Save transcripts under `deals/<slug>/inputs/`. When done, re-invoke (either `dudu:diligence` to continue here, or `dudu:customer-debrief` directly — the layered call is the recommended path).

   Stop. Do not proceed.

6. **On re-invocation**, detect whether the debrief should run:
   - If `deals/<slug>/inputs/` contains transcript files (anything beyond `deck.*`) AND `customer-discovery.md` does not exist → invoke `dudu:customer-debrief`, then continue to step 7.
   - If `customer-discovery.md` exists → skip straight to step 7.

7. **Stitch `MEMO.md`.** Read every artifact under `deals/<slug>/` and produce `deals/<slug>/MEMO.md`:

```markdown
# Investment memo: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## TL;DR

[3-5 sentences. Founder credibility, problem severity, market size, competitive position, recommendation tilt.]

## Founders

[For each founder, summarize from `founder-<name>.md` in 3-5 bullets. Link to the full dossier.]

## Problem and product

[Summary from `market-context.md` (4-6 sentences) + the strongest pattern + the most valuable contradiction. Link to the full file.]

## PMF signal & claim verification (calibrated prior + cross-artifact + external)

[Headline read from `pmf-signal.md`. The top 5 rows of the consolidated claim ledger (worst-news-first ordering). The 1 strongest cluster pattern. Explicit Stance B disclaimer for the persona-reaction rows; cross-artifact and external-evidence rows do not need the same disclaimer because they triangulate against actual evidence. List of `requires-data-room` flags for the VC to follow up on.]

## Customer signal

[Summary from `customer-discovery.md`. Quote 2-3 strongest verbatims. Flag any persona contradictions explicitly.]

## Competitive landscape

[Summary from `competitive-landscape.md`. Top 3 direct competitors. Incumbent verdict. Moat verdict.]

## Market sizing

[Wedge TAM range, expansion TAM range, comparison to founder claim.]

## Cross-artifact synthesis

[Surfaces contradictions ACROSS artifacts. e.g.: "Founder claims engineering teams are the buyer (deck p.3), but customer interviews showed product managers driving the purchase (interview-2)." This is where the orchestrator earns its keep.]

## Recommendation

- **Pass / Watch / Pursue:** <verdict>
- **Why:** [3 sentences]
- **What would change my mind:** [2-3 specific things to verify]

## Source artifacts

- founder-<name>.md
- market-context.md
- pmf-signal.md
- outreach.md
- customer-discovery.md
- competitive-landscape.md
- market-sizing.md
```

8. **Render `report.html`.** Run `python3 scripts/render-report.py deals/<slug>`. The script reads `MEMO.md` and the artifacts and writes a single self-contained `deals/<slug>/report.html` — embedded CSS/JS, no network assets. Markdown stays canonical; HTML is a derived view.

   - If the script exits non-zero (missing `manifest.json`, parse error), surface the stderr message but **do not** block — `MEMO.md` is still useful on its own.
   - If `python3` isn't on PATH, print: `report.html skipped — install Python 3 or run python3 scripts/render-report.py deals/<slug> manually.`

9. **Print** the paths to `MEMO.md` and (if rendered) `report.html`.

## Re-runnability

The layered skills below this wrapper each check their own artifacts and skip if present (unless `--force`). The wrapper therefore inherits re-runnability for free. To re-run: invoke this skill again; only missing pieces will be filled.

## Migration to layered skills

Drop-in replacement for users with `dudu:diligence` muscle memory:

```bash
# Old, single-call (still works for now)
dudu:diligence

# New, layered (recommended — the canonical surface)
dudu:background-check                 # produces L1 bundle
dudu:pmf-signal                       # produces the unique value
# ... run real interviews, save transcripts to deals/<slug>/inputs/ ...
dudu:customer-debrief                 # synthesizes transcripts
# ... then stitch MEMO + render manually, OR re-invoke dudu:diligence which handles those steps ...
```
