---
name: pmf-signal
description: Calibrated PMF signal + claim verification + warm-path outreach. Layered on top of completed dudu diligence. Ingests every founder/company claim into a structured ledger, verifies via three parallel paths (persona pitch-reaction over an N=10–200 5W-grounded synthetic population, cross-artifact triangulation against prior dudu artifacts, bounded external-evidence web checks), then runs a cluster-stratified network scan with authed-LinkedIn warm-path inference.
---

# PMF signal & warm-path outreach

Run after the full dudu diligence chain. Read `lib/deal.md`, `lib/research-protocol.md`, and `lib/playwright-auth.md` first. Heaviest budget in the plugin: stage 3a is the largest LLM spend; stage 3c carries a 30-fetch web budget.

## What this skill IS and IS NOT

- IS: a layered enrichment that produces the unique-value section of the diligence memo. Operates on prior artifacts; refuses to start without them.
- IS NOT: a replacement for any prior dudu skill. All five upstream skills keep their full scope.
- IS NOT: signal. Stance B applies — every persona-reaction aggregate is a calibrated prior to falsify in real interviews. State this in every output.

## Inputs

Required (all from prior dudu skills — see Pre-flight hard gate):

- Deal slug
- `deals/<slug>/inputs/deck.<ext>` (or pasted pitch text)
- `deals/<slug>/personas/_context.md`
- `deals/<slug>/market-problem.md`
- `deals/<slug>/founder-*.md` (one or more)
- `deals/<slug>/competitive-landscape.md`
- `deals/<slug>/market-sizing.md`

Optional:
- Company website URL (homepage + pricing + about) for stage 0 enrichment.
- Public statements list (URLs to interviews / podcasts / blog posts).
- `--n <int>` total personas (default 60; min 15; max 200).
- `--frames <comma-list>` restrict to enabled frames.
- `--no-network` skip stage 5.
- `--public-only` stage 5 without authed LinkedIn.
- `--force` overwrite existing artifacts.

## Pre-flight (hard gate)

Run `python3 scripts/pmf-signal-preflight.py deals/<slug>` first. The script verifies every upstream artifact exists, prints the loading ledger on success, or lists missing artifacts and exits non-zero on failure.

- Exit 0: prior diligence complete; print the loading ledger to the user, then proceed to Stage 0.
- Exit 2: upstream missing. Surface the script's stdout to the user verbatim and stop. Do not auto-trigger upstream skills — the user controls heavy spend.
- Exit 3: pmf-signal already done. Surface the message and stop. The user must pass `--force` to overwrite.

After exit 0, also confirm:
- A pitch source exists (`inputs/deck.<ext>` is required; a website URL is optional and is fetched live in Stage 0).
- The user passed any optional flags (`--n`, `--frames`, `--no-network`, `--public-only`).

## Stage 0 — Claim ledger ingestion

(Filled in Task 6.)

## Stage 1 — Frame definition

(Filled in Task 8.)

## Stage 2 — Population synthesis

(Filled in Tasks 9–11.)

## Stage 3 — Claim verification

(Filled in Tasks 12–15.)

## Stage 4 — PMF signal report

(Filled in Task 17.)

## Stage 5 — Network scan & outreach

(Filled in Tasks 18–20.)

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["pmf-signal"]`.
