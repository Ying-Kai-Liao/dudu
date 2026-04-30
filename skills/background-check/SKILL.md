---
name: background-check
description: Layer 1 orchestrator. Runs founder-check, market-context, competitive-landscape, and market-sizing, then writes deals/<slug>/background.md as the L1 sentinel for dudu:pmf-signal. No personas (L2 owns them).
---

# Background check (Layer 1)

Run the public-source half of dudu diligence on one deal. Cheap, parallel-safe, and intentionally shallow — this is the "intern's afternoon" job. Read `lib/deal.md`, `lib/research-protocol.md`, and `lib/playwright-auth.md` before starting.

## What this skill IS and IS NOT

- IS: an orchestrator for the four cheap, public-source sub-skills. The output is context + a claim-ledger seed for Layer 2 (`dudu:pmf-signal`) to verify.
- IS NOT: the unique deliverable. The PMF claim ledger × verdict matrix is produced by `dudu:pmf-signal`. Background-check is the input contract.
- IS NOT: a persona simulation. The orchestrator and every sub-skill it invokes refuse to write under `deals/<slug>/personas/`. That namespace is owned exclusively by `dudu:pmf-signal`.

## Inputs (prompt if missing)

- Deal slug (kebab-case)
- Company name
- Founder names (one or more)
- One-line pitch
- Pitch deck (file path or pasted text), **optional** but strengthens Layer 2's claim ledger. If supplied, saved to `deals/<slug>/inputs/deck.<ext>` (or `deck.md` for pasted text). If not supplied, the manifest's `pitch` one-liner plus the L1 artifacts (founder dossiers, market-context, etc.) carry through to PMF Stage 0.

## Pre-flight

1. If `deals/<slug>/` does not exist, create it. Write `manifest.json` per the schema in `lib/deal.md` — including the `pitch` one-liner field, which is required.
2. If a deck path was supplied, copy it to `deals/<slug>/inputs/deck.<ext>`. If pasted deck text was supplied, write it to `deals/<slug>/inputs/deck.md`. If no deck was supplied, do nothing — that's fine.
3. Idempotency: if `deals/<slug>/background.md` already exists and `--force` was not passed, print "L1 sentinel already exists at deals/<slug>/background.md. Pass --force to re-run all sub-skills." and stop.

## Steps

Run the four sub-skills in order, each as a sub-invocation. After each, confirm the artifact exists before moving on. If `--force` was passed, propagate it to each sub-skill.

1. `dudu:founder-check` — for each founder. Writes `deals/<slug>/founder-<name>.md`.
2. `dudu:market-context` — public-source market and problem context. Writes `deals/<slug>/market-context.md`. **No personas.**
3. `dudu:competitive-landscape` — competitor matrix. Writes `deals/<slug>/competitive-landscape.md`.
4. `dudu:market-sizing` — bottom-up TAM. Writes `deals/<slug>/market-sizing.md`.

### Re-invocation

Each sub-skill checks its own artifact and skips if present (mirrors the existing dudu re-runnability pattern). The orchestrator can therefore be re-run safely; only missing pieces will be filled. `--force` propagates to every sub-skill.

If a sub-skill fails, do not write `background.md`. The manifest reflects only the sub-skills that completed. Tell the user which sub-skill failed and how to resume.

### Persona namespace refusal

Neither this orchestrator nor any of its sub-skills writes under `deals/<slug>/personas/`. If you find yourself wanting to generate persona artifacts here, stop — that is a Layer 2 (`dudu:pmf-signal`) concern. State this distinction in the output if it ever comes up.

## After all sub-skills complete

Write the L1 sentinel file at `deals/<slug>/background.md`:

```markdown
# Background check (Layer 1) — <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>
**Status:** L1 complete — ready for Layer 2 (`dudu:pmf-signal`)

## Founders

[For each founder, 2-3 bullet summary from `founder-<name>.md`. Link to the full dossier.]

- See: founder-<name>.md (one bullet per founder)

## Market & problem context

[3-5 sentences synthesized from `market-context.md` Phase 1 + Phase 3. The strongest pattern. The single most valuable contradiction.]

- See: market-context.md

## Competitive landscape

[Top 3 direct competitors with one-line take. Incumbent threat verdict. Moat verdict.]

- See: competitive-landscape.md

## Market sizing

[Wedge TAM range, expansion TAM range, comparison to founder claim if any.]

- See: market-sizing.md

## Claim ledger seed

[Optional but recommended: a short list of the founder/company's most prominent verifiable claims, drawn from the deck (if supplied) and the founder dossiers + manifest pitch. This is not a full pitch.yaml — Layer 2's stage 0 produces that. The seed is a heads-up for the human reading background.md.]

## What's next

- Layer 2: run `dudu:pmf-signal` to generate the falsifiable claim ledger × verdict matrix and the warm-path outreach list.
- Standalone: each sub-skill's artifact is fully readable on its own — see the per-file links above.

## Source artifacts

- founder-<name>.md (one or more)
- market-context.md
- competitive-landscape.md
- market-sizing.md
- inputs/deck.<ext> (optional)
```

After writing `background.md`:

- Update `manifest.json`'s `skills_completed.background-check` with the current ISO-8601 UTC timestamp.
- Confirm the four sub-skill timestamps (`founder-check`, `market-context`, `competitive-landscape`, `market-sizing`) are all non-null.
- Print: `L1 sentinel written: deals/<slug>/background.md. Ready for dudu:pmf-signal.`

## Re-runnability

The sentinel `background.md` is the L1 contract recognized by downstream layers. It is the cheapest, most reliable signal that L1 finished. If any sub-skill fails or is skipped, `background.md` is not written and downstream layers refuse to start.

`--force` re-runs all four sub-skills and rewrites the sentinel. Without `--force`, missing-only behavior applies.
