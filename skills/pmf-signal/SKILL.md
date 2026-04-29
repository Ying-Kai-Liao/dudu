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

Goal: produce `deals/<slug>/pitch.yaml` — a structured ledger of every claim the founder/company makes, with a verification method per claim.

### Sources

1. The deck at `inputs/deck.<ext>` (always — required by pre-flight).
2. The company website if a URL was provided — fetch homepage, pricing page, about page (3 fetches max).
3. Each `founder-*.md` (already on disk from `dudu:founder-check`).
4. Public statements list if provided — fetch each URL with the WebFetch tool, max 5 fetches total.

Total stage-0 fetch budget: 8.

### Extraction

Read every source and extract claims into the schema below. Each claim is a discrete row with mandatory `source` provenance and `verification_method`.

```yaml
product:
  name: <string>
  one_liner: <string>
  category: <string>

target_market:
  stated_icp: <founder's exact words>
  stated_segments: [<string>]

claims:
  - claim_id: c-001
    claim: "<verbatim claim text>"
    category: <pain | wtp | urgency | trigger | switching | gtm-distribution | gtm-channel | traction | revenue | customer-count | growth-rate | retention | nps | founder-background | founder-prior-venture | founder-credentials | market-size | tam | sam | competitive | unique-advantage | moat-claim>
    source: "<file + page/section/URL>"
    verification_method: <persona-reaction | cross-artifact | external-evidence>
    # ... category-specific extras (see below)

unstated_assumptions:
  - assumption: "<inferred unstated belief>"
    derived_from: "<source(s)>"
    promoted_to_claim: <claim_id if already a claim, else null>
```

### Auto-classification rules

Assign `verification_method` automatically by category:

- `pain | wtp | urgency | trigger | switching | gtm-distribution | gtm-channel` → `persona-reaction`
- `founder-background | founder-prior-venture | founder-credentials` → `cross-artifact`, `cross_artifact: founder-check`, `cross_artifact_target: founder-<slug>.md`
- `market-size | tam | sam` → `cross-artifact`, `cross_artifact: market-sizing`, `cross_artifact_target: market-sizing.md`
- `competitive | unique-advantage | moat-claim` → `cross-artifact`, `cross_artifact: competitive-landscape`, `cross_artifact_target: competitive-landscape.md`
- `traction | revenue | customer-count | growth-rate | retention | nps` → `external-evidence`, populate `external_check: [<recipe-slugs>]` from the table below
- Anything else: emit the claim with `verification_method: persona-reaction` and a `flag: classifier-uncertain` field; surface for user confirmation.

External-evidence recipe defaults by category:

| Category | Default recipes |
|---|---|
| `customer-count` | `customer-list-on-website`, `testimonial-count` |
| `revenue` | `wayback-machine-claim-history` (mark `flag_if_unverifiable: requires-data-room`) |
| `growth-rate` | `wayback-machine-claim-history` (mark `flag_if_unverifiable: requires-data-room`) |
| `retention | nps` | (none in v1) — emit with `flag_if_unverifiable: requires-data-room` |
| `traction` (generic) | `customer-list-on-website`, `testimonial-count` |

### User confirmation gate

After writing `pitch.yaml`, print a one-screen summary listing each claim with its assigned verification method, and ask:

> Confirmed claim ledger above. Reply with `ok` to proceed, or list claim IDs to re-classify (e.g. `c-007:cross-artifact:competitive-landscape`).

Block on user response. Apply re-classifications in place, then proceed to Stage 1.

### Validation

Run `python3 scripts/pmf-signal-validate-pitch.py deals/<slug>/pitch.yaml`. Implementation in Task 7 — for now, ensure every claim has all four required fields (`claim_id`, `claim`, `category`, `source`, `verification_method`).

### Parallelization

Sources 1–4 are independent. Dispatch worker subagents per source category if all four are present; otherwise run inline. See `lib/research-protocol.md` § Parallelization.

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
