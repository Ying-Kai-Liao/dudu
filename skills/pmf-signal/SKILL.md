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

Goal: produce `deals/<slug>/personas/frames.yaml` — 1–4 frames that drive the rest of the pipeline.

### Frame purposes (v1)

| Frame purpose | Asking lens | Captured per persona in stage 3a |
|---|---|---|
| `pmf-validation` | "Would you use this? What makes you say no?" | use intent, top hesitation, would-pay (Y/N + band), kill-switch reason |
| `founder-claim-validation` | Per `pitch.yaml` persona-reaction claim → agree/partial/disagree + verbatim | per-claim verdict + contradicting quote |
| `jtbd-discovery` | JTBD: job, forces, anxieties, progress | pain triggers, switching forces, current solution |
| `bant-qualification` | BANT: budget, authority, need, timeline | budget band, authority level, urgency, timeline |

Default v1 enabled: `pmf-validation`, `founder-claim-validation`, `jtbd-discovery`. `bant-qualification` ships built-in but disabled by default.

### Per-frame definition

For each enabled frame, derive:

1. **Segments** — 1–3 customer types this frame applies to. Source from `pitch.yaml.target_market.stated_segments` and `_context.md`'s segment evidence. Total segments across all frames cap at 5.
2. **Must-cover cells** — 8–12 attribute combinations per segment that the population MUST cover. The founder's stated ICP center is always one of these. Use Layer 1 attribute axes (role, geography, stage, vertical, team_size, revenue_band, buying_authority) to enumerate.
3. **Distribution sampling profile** — weighted distributions for the remaining persona slots. Example: `role: {founder-ceo: 0.6, cofounder-cto: 0.2, ops-manager: 0.15, other: 0.05}`.

### Output: frames.yaml

```yaml
frames:
  - frame_id: <slug>.pmf-validation
    purpose: pmf-validation
    enabled: true
    segments:
      - segment_id: cape-town-saas-founder
        must_cover:
          - {role: founder-ceo, geography: ZA-Western-Cape, stage: pre-seed, vertical: b2b-saas, team_size: 3, revenue_band_mrr_zar: [150000, 300000], buying_authority: sole}
          - # ... 7-11 more cells
        distribution:
          role: {founder-ceo: 0.6, cofounder-cto: 0.2, ops-manager: 0.15, other: 0.05}
          # ... other axes
  - frame_id: <slug>.founder-claim-validation
    # ...
  - frame_id: <slug>.jtbd-discovery
    # ...
```

### Budget allocation across frames

Default total N=60. Allocate:

- 50% to `pmf-validation` (broad)
- 30% to `founder-claim-validation` (focused on the founder's stated ICP center)
- 20% to `jtbd-discovery` (pain-shape exploration)

Adjust if `--n` was passed.

## Stage 2 — Population synthesis (5W scenario-driven)

Goal: produce `deals/<slug>/personas/rows/p-<id>.yaml` × N — a structured population built by causal reasoning from scenario seeds, never by attribute fill.

### 2.1 Scenario-seed mining

Read `_context.md` and extract scenario seeds — specific triggering moments grounded in cited evidence. Examples: a Reddit complaint quote, a regulatory event date, a growth milestone described in an interview, a switching event mentioned in a review.

Each seed:

```yaml
seed_id: s-014
trigger: "hit VAT threshold mid-fundraise, mid-Q3"
trigger_type: <regulatory-growth-collision | switching-cost | onboarding-friction | scaling-stress | exit-prep | onboarding-trust | other>
source_quote: "<verbatim quote from _context.md>"
source_ref: "_context.md L<line>"
implied_attributes:
  stage: [<list of plausible stages>]
  geography: <free-text region>
  vertical: <free-text vertical hint>
```

Aim for 30–60 seeds total. Each must have a verbatim source quote. If you can't find a seed for a particular trigger type, that's evidence of a context-bundle gap — note it for the refusals report.

Save seeds to `deals/<slug>/personas/seeds.yaml`.

### 2.2 Mode-collapse pre-check

Run `python3 scripts/pmf-signal-mode-collapse.py deals/<slug>/personas/seeds.yaml` (implementation in Task 10).

If the script reports `MODE-COLLAPSE` (top-1 trigger_type share > 0.6), surface to user:

> Scenario-seed pool is heavily concentrated in `<trigger_type>` (X% of seeds). The synthetic population will inherit this bias. Options: (a) extend `_context.md` with sources covering other triggers, then re-run; (b) proceed knowing the population will be biased. Reply `proceed` or `extend`.

Block on user response. If `proceed`, continue but flag in `refusals.md` and the final report.

### 2.3 5W persona construction (strict)

For each persona slot, walk the 5W chain in order. **All five must be filled and traceable, or generation fails for that slot** — the failure goes to `refusals.md`, which is itself diligence signal.

1. **Why (now)** — sample a scenario seed from `seeds.yaml`. The seed becomes Layer 0.
2. **When** — temporal shape: `quarterly | continuous | trigger-only | one-time-haunting`.
3. **Who** — derived from the scenario; do not pre-decide. Role, stage, demographics, authority must follow causally from the seed + frame's must-cover cell (if generating for a must-cover slot).
4. **Where** — physical + channel context (e.g. "kitchen table 11pm, fundraise data room open in next tab").
5. **What** — verbatim phrasing of how this persona talks and acts. This is the Layer 3 voice fuel.

Layer 1 attributes (clustering) and Layer 2 framework-specific fields are OUTPUTS of this chain.

### 2.4 Persona row schema

Each persona is one structured record at `deals/<slug>/personas/rows/p-<id>.yaml`. Schema:

```yaml
persona_id: p-007
schema_version: 1
frame_id: <frame_id>
segment: <segment_id>
generated_at: <ISO timestamp>

scenario:                            # Layer 0 — provenance unit
  trigger: "<seed.trigger>"
  trigger_type: "<seed.trigger_type>"
  source_seed: <seed_id>
  source_ref: "<seed.source_ref>"
  when: <quarterly | continuous | trigger-only | one-time-haunting>
  where: "<physical + channel context>"
  why_unsolved: "<why current solutions don't address this>"

attributes:                          # Layer 1 — clustering dimensions
  role: <string>
  geography: <string>
  stage: <string>
  vertical: <string>
  team_size: <int>
  revenue_band_mrr_zar: [<low>, <high>]
  buying_authority: <sole | shared | committee>

# Layer 2 — pick the right block for the frame_id's purpose:
framework_jtbd:                       # only present if frame_id ends with .jtbd-discovery
  pain_intensity: <1-10>
  pain_frequency: <quarterly | continuous | trigger-only>
  current_solution: <string>
  switching_forces:
    push: <string>
    pull: <string>
    anxiety: <string>
    habit: <string>
  progress_blockers: [<string>]

framework_bant:                       # only if frame_id ends with .bant-qualification
  budget_band_annual_usd: [<low>, <high>]
  authority_level: <sole | influencer | blocker | none>
  need_urgency: <1-10>
  timeline_to_purchase: <quarter | half | year | longer>

framework_pmf_validation:             # only if frame_id ends with .pmf-validation
  use_intent_prior: <high | medium | low>
  primary_anxiety_axis: <cost | trust | switching | integration | other>

framework_founder_claim:              # only if frame_id ends with .founder-claim-validation
  centered_on_claim: <claim_id>       # the one claim this row most pressures

voice:                                # Layer 3 — NLP / matching fuel (every frame)
  pain_phrases: [<string>]            # 3-5
  objections: [<string>]              # 2-3
  purchase_trigger: <string>

discoverability_signals:
  job_titles: [<string>]
  communities: [<string>]
  post_patterns: [<string>]
  query_strings: [<string>]

context_grounding:
  - {claim: <string>, source: <_context.md ref>}
fabrication_flags: [<string>]         # populated when LLM had to extrapolate
```

### 2.5 Generation strategy (stratified hybrid)

1. Enumerate must-cover cells across all enabled frames (≈10–12 per frame). Generate 1–3 personas per cell. The founder's stated ICP center is always a must-cover cell — those rows feed founder-claim-validation directly.
2. Distribution-sample the remaining slots up to N (default 60), weighted by the frame budget allocation in Stage 1.
3. **Refuse** any slot where the 5W chain cannot be grounded in `_context.md`. Append to `personas/refusals.md`:

```markdown
# Population synthesis refusals

## Refusal 1
**Slot:** frame=<frame_id>, must_cover=<cell>
**Reason:** could not ground 5W chain — no seed in `_context.md` covers <trigger description>
**Implication:** context bundle gap; re-run `dudu:market-problem` with sources covering <X>
```

### 2.6 Parallelization

Population synthesis is embarrassingly parallel per frame. Dispatch one worker subagent per enabled frame using your host's parallel-agent dispatch primitive (see `lib/research-protocol.md` § Parallelization).

Each subagent receives:
- Full `_context.md` text
- Full `pitch.yaml`
- The frame's `frames.yaml` entry
- The seed pool (full `seeds.yaml`)
- This row schema

Returns: row YAML files as text. Main session writes them to `personas/rows/p-<id>.yaml` (assigning `persona_id` sequentially) and the `refusals.md` accumulator.

## Stage 3 — Claim verification

(Filled in Tasks 12–15.)

## Stage 4 — PMF signal report

(Filled in Task 17.)

## Stage 5 — Network scan & outreach

(Filled in Tasks 18–20.)

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["pmf-signal"]`.
