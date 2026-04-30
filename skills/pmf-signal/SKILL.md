---
name: pmf-signal
description: Calibrated PMF signal + claim verification + warm-path outreach (Layer 2). Verifies founder claims via persona pitch-reaction (N=10–200), cross-artifact triangulation, and bounded web checks; adds an authed-LinkedIn warm-path scan.
---

# PMF signal & warm-path outreach

Run as Layer 2 on top of a completed Layer 1 bundle (produced by `dudu:background-check`, or by any orchestrator that writes the L1 sentinel `deals/<slug>/background.md`). Read `lib/deal.md`, `lib/research-protocol.md`, and `lib/playwright-auth.md` first. Heaviest budget in the plugin: stage 3a is the largest LLM spend; stage 3c carries a 30-fetch web budget.

## What this skill IS and IS NOT

- IS: the unique-value layer of the dudu plugin. Produces the falsifiable claim ledger × verdict matrix and the warm-path outreach list.
- IS: the sole owner of the `personas/` namespace. All persona simulation files (`_context.md`, `frames.yaml`, `seeds.yaml`, `aggregates.yaml`, `verdicts.yaml`, `rows/p-*.yaml`) are written by this skill.
- IS NOT: a replacement for the L1 background-check skills. They produce context; this layer verifies claims against that context plus a deep persona simulation plus external evidence.
- IS NOT: signal. Stance B applies — every persona-reaction aggregate is a calibrated prior to falsify in real interviews. State this in every output.

## Inputs

Required (the L1 contract — verified by the preflight gate):

- Deal slug
- `deals/<slug>/background.md` (the L1 sentinel — produced by `dudu:background-check`)
- `deals/<slug>/founder-*.md` (one or more)
- `deals/<slug>/market-context.md`
- `deals/<slug>/competitive-landscape.md`
- `deals/<slug>/market-sizing.md`
- `deals/<slug>/manifest.json` with a non-empty `pitch` field (always produced by `dudu:background-check`'s init step)

Optional (improves Stage 0 claim ledger quality but not required):

- `deals/<slug>/inputs/deck.<ext>` (or pasted deck text written to `deck.md`) — when present, source #1 for Stage 0 claim ingestion. When absent, Stage 0 falls back to manifest.pitch + founder dossiers + market-context + the optional company-website fetch.

Optional inputs the skill tolerates if present (read-only):

- `deals/<slug>/personas/_context.md` — legacy artifact authored by the deprecated `market-problem` skill. If present, used as additional Stage-0 context. If absent, this skill writes its own `personas/_context.md` during Stage 1.
- `deals/<slug>/personas/persona-*.md` and `personas/round-*.md` — legacy persona files from `market-problem` Phase 2. Tolerated but not required, and never overwritten by this skill.

Optional flags:
- Company website URL (homepage + pricing + about) for stage 0 enrichment.
- Public statements list (URLs to interviews / podcasts / blog posts).
- `--n <int>` total personas (default 60; min 15; max 200).
- `--frames <comma-list>` restrict to enabled frames.
- `--no-network` skip stage 5.
- `--public-only` stage 5 without authed LinkedIn.
- `--force` overwrite existing PMF artifacts (does NOT touch legacy persona files).

## Pre-flight (hard gate)

Run `python3 scripts/pmf-signal-preflight.py deals/<slug>` first. The script verifies the L1 bundle is present (regardless of which orchestrator produced it) and prints either a loading ledger or a missing-artifact failure.

- Exit 0: L1 bundle complete; print the loading ledger to the user, then proceed to Stage 0.
- Exit 2: L1 bundle incomplete. Surface the script's stdout verbatim and stop. Tell the user to run `dudu:background-check`. Do not auto-trigger upstream skills — the user controls heavy spend.
- Exit 3: pmf-signal already done. Surface the message and stop. The user must pass `--force` to overwrite.

The preflight checks for: `background.md` (L1 sentinel), `founder-*.md`, `market-context.md`, `competitive-landscape.md`, `market-sizing.md`. It does NOT require `inputs/deck.<ext>` (deck is optional — see Stage 0). It does NOT check for `customer-discovery-prep.md`, `personas/_context.md`, or any legacy `personas/persona-*.md` — those couplings are gone.

After exit 0, also confirm:
- A pitch source: `manifest.pitch` is always present (set by `dudu:background-check`'s init); `inputs/deck.<ext>` is optional and only fetched in Stage 0 if present; a website URL is optional and is fetched live in Stage 0.
- The user passed any optional flags (`--n`, `--frames`, `--no-network`, `--public-only`).

## Stage 0 — Claim ledger ingestion

Goal: produce `deals/<slug>/pitch.yaml` — a structured ledger of every claim the founder/company makes, with a verification method per claim.

### Sources

1. The deck at `inputs/deck.<ext>` if present (optional). When absent, fall through to the manifest's `pitch` one-liner (always present) plus sources 2–5 below.
2. The company website if a URL was provided — fetch homepage, pricing page, about page (3 fetches max).
3. Each `founder-*.md` (already on disk from `dudu:founder-check`).
4. Public statements list if provided — fetch each URL with the WebFetch tool, max 5 fetches total.
5. The L1 context bundle: `market-context.md`, `competitive-landscape.md`, `market-sizing.md` — always present as part of the L1 contract. Used as supplementary claim sources especially when no deck is supplied.

Total stage-0 fetch budget: 8. (Sources 3 and 5 are local-file reads, no fetches.)

If no deck is present AND no website was provided AND no public statements were supplied, Stage 0 produces a thinner `pitch.yaml` drawn from `manifest.pitch` + the L1 artifacts. Mark such runs in the artifact's preamble: `**Pitch sources:** manifest.pitch + L1 artifacts only (no deck supplied)`. The downstream stages run normally — claim verdicts will be sparser and that's the honest result.

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

## Stage 0b — L1 context bundle absorption

Goal: ensure `deals/<slug>/personas/_context.md` exists before Stage 1, regardless of which orchestrator produced L1.

The downstream stages (frame definition, scenario-seed mining, persona synthesis) read `personas/_context.md` as the canonical context bundle. Two cases:

1. **`personas/_context.md` already exists** — leave it untouched (it may have been authored by the deprecated `dudu:market-problem` Phase 1, which produced this file directly; or by a prior PMF run). Use it as-is.
2. **`personas/_context.md` does not exist** — derive it from the L1 bundle. This is the new path under the layered architecture: `dudu:market-context` writes `market-context.md` (not `personas/_context.md`), so PMF synthesizes `personas/_context.md` itself before frame definition.

When deriving (case 2), build `personas/_context.md` with this shape:

```markdown
# Problem-space context bundle

**Generated:** <ISO timestamp>
**Source:** synthesized by dudu:pmf-signal Stage 0b from L1 artifacts

## What is the problem?

[Lift verbatim or near-verbatim from market-context.md's "What is the problem?" section.]

## Who has it?

[Lift from market-context.md's "Who has it?" section.]

## How are they solving it today?

[Lift from market-context.md's "How are they solving it today?" section, augmented with competitive-landscape.md's competitor list.]

## What's contested?

[Lift from market-context.md's "What's contested?" section, augmented with cross-artifact contradictions across founder-*.md, market-sizing.md, and competitive-landscape.md.]

## What we couldn't find

[Lift from market-context.md, plus any "requires-data-room" flags surfaced in pitch.yaml.]

## Sources

- market-context.md
- founder-<name>.md (one per founder)
- competitive-landscape.md
- market-sizing.md
- inputs/deck.<ext>
```

This stage is idempotent: skip entirely if `personas/_context.md` already exists, regardless of who wrote it. `--force` re-derives it from the current L1 bundle (legacy `market-problem`-authored copies are overwritten only when `--force` is set).

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
**Implication:** context bundle gap; re-run `dudu:market-context --force` with sources covering <X> (the deprecated `dudu:market-problem` invocation also forwards there)
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

## Stage 3 — Claim verification (3a + 3b + 3c, parallel)

Stage 3 fans the claim ledger out into three independent verification paths. Run all three concurrently. Each emits per-claim verdicts. Stage 3 ends with `scripts/pmf-signal-consolidate-verdicts.py` merging them into `personas/verdicts.yaml`.

### Stage 3a — Persona pitch-reaction

For each persona row, run one structured reaction interview against the pitch + the persona-reaction-bound subset of `pitch.yaml.claims`.

#### Interview prompt (dispatched to persona subagent)

> You are persona [persona_id]: [render persona row's scenario.trigger, attributes, voice]. Stay in character. Use phrases from your `voice.pain_phrases` and `voice.objections` where natural.
>
> Here is the pitch you are being shown:
>
> [render `pitch.yaml.product`, `pitch.yaml.target_market`, and the full pitch text]
>
> React honestly:
>
> 1. Would you use this? Why or why not? Answer `yes`, `no`, or `yes-with-caveats`, then 1–2 sentences in your voice.
> 2. What is your single biggest hesitation? Answer in your voice.
> 3. Would you pay for this? Answer `yes`, `no`, or `maybe`. If yes, name a price ceiling above which you'd say no.
> 4. What would make you say no immediately? Answer in your voice (this is your kill_switch).
> 5. For each of the following founder claims, give a verdict (`agree | partial | disagree`) AND a verbatim quote from yourself supporting that verdict:
>
>    [render the persona-reaction-bound claims from pitch.yaml — id + claim text]

#### Output schema (stored at `personas/reactions/p-<id>.yaml`)

```yaml
persona_id: p-007
reaction_at: <ISO timestamp>
schema_version: 1
would_use: <yes | no | yes-with-caveats>
biggest_hesitation: "<verbatim>"
willing_to_pay: <yes | no | maybe>
wtp_ceiling_zar_per_month: <int or null>
kill_switch: "<verbatim>"
claim_responses:
  - claim_id: c-001
    verdict: <agree | partial | disagree>
    verbatim: "<verbatim>"
  - # ...
provenance:
  voice_phrases_used: [<phrase>]
  context_grounding: [<_context.md ref>]
```

#### Parallelization

Dispatch worker subagents in batches of 20 personas per subagent. Each subagent owns its batch's reactions and returns the YAML files as text. Main session writes them to disk.

### Stage 3b — Cross-artifact verification

For each claim with `verification_method: cross-artifact`, verify against the named existing dudu artifact. Do **not** re-fetch external evidence — pmf-signal reads the artifact already produced by the prior dudu skill.

#### Per-claim procedure

1. Open `deals/<slug>/<cross_artifact_target>` (read-only).
2. Find passages relevant to the claim (LLM judgement, anchored on claim text + category + keywords).
3. Emit a verdict + supporting and/or contradicting verbatim quotes from the artifact, with line references.

#### Verdict shape (one file per claim, stored at `personas/verdicts-3b/<claim_id>.yaml`)

```yaml
claim_id: c-020
claim: "<verbatim claim text>"
verification_method: cross-artifact
cross_artifact: <founder-check | market-sizing | competitive-landscape>
cross_artifact_target: <filename>
verdict: <supports | partial | contradicts | no-evidence>
supporting_quotes:
  - {quote: "<verbatim>", location: "<file>:L<line>"}
contradicting_quotes:
  - {quote: "<verbatim>", location: "<file>:L<line>"}
verdict_rationale: "<1-3 sentences explaining the verdict>"
```

#### Parallelization

Group claims by `cross_artifact` (founder-check / market-sizing / competitive-landscape). Dispatch one worker subagent per group; each subagent receives the full text of its target artifact plus the claim list it owns.

### Stage 3c — External-evidence verification

For each claim with `verification_method: external-evidence`, run a bounded targeted web check.

**Budget caps:** 5 fetches per claim; 30 fetches total across stage 3c.

**Architecture:** Claude fetches URLs with WebFetch and saves raw HTML to `deals/<slug>/.tmp/3c/<claim_id>/<recipe>/<seq>.html`. Then for each claim, Claude calls the recipe Python module on the saved HTML files. The recipe returns a finding string; Claude composes the verdict.

#### Recipe library (v1)

| Recipe slug | URLs to fetch | Module | What it returns |
|---|---|---|---|
| `customer-list-on-website` | homepage + `/customers` + `/case-studies` (max 3) | `pmf-signal-recipes/customer_list.py` | "homepage shows N named logo(s); M detailed case stud(ies)" |
| `testimonial-count` | homepage + `/about` + `/testimonials` (max 3) | `pmf-signal-recipes/testimonial_count.py` | "X testimonial(s) with named attribution; Y unattributed quote(s)" |
| `wayback-machine-claim-history` | 3–5 Wayback snapshots of the relevant page | `pmf-signal-recipes/wayback_history.py` | "N snapshot(s); claim numbers found: [...]; trajectory: a → b → c" |

If a claim's category needs a recipe that's not in v1 (e.g. SEO ranking, G2 presence), emit the verdict with `flag_if_unverifiable: requires-data-room` and `verdict: requires-data-room`.

#### Calling a recipe

The recipe modules are loaded via `importlib.util.spec_from_file_location` (the package directory `pmf-signal-recipes/` contains hyphens, which Python's regular import system can't handle). Use this template:

```bash
python3 -c "
import importlib.util
from pathlib import Path
recipes = Path('scripts/pmf-signal-recipes')
spec = importlib.util.spec_from_file_location('_pmf_recipe_customer_list', recipes / 'customer_list.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
htmls = [p.read_text(encoding='utf-8') for p in sorted(Path('deals/<slug>/.tmp/3c/<claim_id>/customer-list-on-website').glob('*.html'))]
print(mod.run(htmls))
"
```

The recipe-slug-to-module mapping replaces hyphens with underscores: `customer-list-on-website` → `customer_list.py`, `testimonial-count` → `testimonial_count.py`, `wayback-machine-claim-history` → `wayback_history.py`.

#### Verdict shape (one file per claim, stored at `personas/verdicts-3c/<claim_id>.yaml`)

```yaml
claim_id: c-010
claim: "<verbatim claim text>"
verification_method: external-evidence
external_check_results:
  - recipe: customer-list-on-website
    finding: "homepage shows 18 named logo(s); 7 detailed case stud(ies)"
    fetched: ["<url>", "<url>"]
  - recipe: testimonial-count
    finding: "12 testimonial(s) with named attribution; 0 unattributed quote(s)"
    fetched: ["<url>"]
verdict: <supports | partial | contradicts | insufficient-evidence-for-<X> | requires-data-room>
verdict_rationale: "<1-3 sentences synthesizing across recipes>"
flags: [<requires-data-room | classifier-uncertain | ...>]
```

#### Parallelization

Dispatch one worker subagent per claim. Concurrency cap: 5. Each subagent owns its 5-fetch budget for one claim.

## Stage 4 — PMF signal report

After stage 3 finishes, run aggregation and rendering:

```bash
python3 scripts/pmf-signal-aggregate.py deals/<slug>
python3 scripts/pmf-signal-render-report.py deals/<slug>
```

The renderer emits `deals/<slug>/pmf-signal.md`. The output contains FILL-ME placeholders in three narrative sections (`Headline read`, `Strongest contradictions`, `Weakest assumptions in the founder's pitch`). After the renderer runs, complete those sections by reading the consolidated claim ledger and cluster patterns and writing 1–3 paragraphs each. The mechanical structure (claim ledger table, aggregates table, cluster headings, audit) is fixed by the renderer; the narrative is yours.

## Stage 5 — Network scan & warm-path outreach

Goal: produce `deals/<slug>/outreach.md` (cluster-stratified, warm-path-prioritized) AND a legacy-shape `deals/<slug>/customer-discovery-prep.md` (a convenience artifact for the VC — readable on its own; not a precondition for any downstream step).

If `--no-network` was passed, skip this stage entirely.

### 5a. Match — find real humans per cluster

A cluster is any (`trigger_type`, `frame_id`) pair with ≥5 personas in `personas/rows/*.yaml`. List clusters before fetching anything; cap the candidate output at 30 across the deal (matching the legacy `customer-discovery-prep` ceiling).

For each cluster, generate targeted searches from the union of `discoverability_signals.{job_titles, communities, post_patterns, query_strings}` across that cluster's personas.

Channels and per-cluster fetch budgets:

- **LinkedIn (authed Playwright, main session only)** — ~5 fetches per cluster, filtered by job title and geography. Skip under `--public-only`.
- **Reddit** — ~5 candidates per cluster from `post_patterns` queries.
- **Niche communities** — Slack/Discord with public membership lists, 1–2 per cluster, ~5 candidates.
- **X** — search `voice.pain_phrases` + geography filter, ~5 candidates.

Total fetch budget: 20 × cluster_count, hard-capped at 80. If clusters × budget exceeds 80, halve per-cluster budgets.

Each candidate row anchors to a `match_evidence` quote: a public post or profile snippet that ties this candidate to the cluster's signature. **Drop candidates without match evidence.**

#### Parallelization

Dispatch one worker subagent per (cluster × non-LinkedIn channel) combination. LinkedIn runs in main session only (Playwright cannot delegate). See `lib/playwright-auth.md` for the authed-session protocol.

### 5b. Network understanding

For each surviving candidate, enrich with:

1. **Warm-path inference (authed LinkedIn).** Check VC's 1st and 2nd-degree network. Stop at 2nd. Name the bridge if one exists. Skipped under `--public-only`.
2. **Broker identification.** For each candidate's primary community, surface the named moderator/manager/chair. One per community is sufficient.
3. **Channel-fit prior.** Per channel, label `expected_response: low | medium | high` and `risk: low | medium-spam | high-ban`, **conditioned on the specific community** (not the channel-in-the-abstract).
4. **Post hooks.** A recent (≤30 days) post by the candidate that anchors the outreach. "Saw your post about X" outperforms generic DMs.

### Stage 5 row schema

```yaml
candidate_id: c-014
cluster_id: <trigger_type>__<frame_id>
match_evidence:
  url: "<URL>"
  quote: "<verbatim quote>"
  date: <ISO date>
person:
  name: "<name>"
  handle_or_link: "<URL>"
  role_inferred: "<string>"
  geography_inferred: "<string>"
warm_path:
  exists: <true | false>
  degree: <1 | 2 | null>
  bridge_name: "<name (degree-1 connection)>"
  confidence: <high | medium | low>
brokers:
  - {community: "<name>", role: "<role>", contact: "<URL>"}
channel_fit_ranked:
  - {channel: warm-intro-via-<bridge>, expected_response: high, risk: low}
  - {channel: linkedin-dm, expected_response: medium, risk: low}
  - {channel: reddit-dm-public-thread-reply-first, expected_response: medium, risk: medium-spam}
  - {channel: cold-email, expected_response: low, risk: low, note: "<...>"}
post_hooks:
  - {url: "<URL>", date: <ISO>, summary: "<short>"}
recommended_outreach:
  channel: <chosen channel slug>
  draft: "<80-word draft referencing bridge + post hook + research framing>"
```

Save to `deals/<slug>/personas/candidates/<candidate_id>.yaml`.

### 5c. Render outreach artifacts

Run:

```bash
python3 scripts/pmf-signal-render-outreach.py deals/<slug>
```

This emits `outreach.md` (cluster-stratified, prioritized by warm-path quality) and a legacy-shape `customer-discovery-prep.md` (target list + channel templates + interview script auto-generated from cluster patterns + strongest contradictions in `pmf-signal.md`). The prep file is a convenience artifact for the VC — it is no longer a precondition for `dudu:customer-debrief`, which now runs whenever transcripts are present.

### 5d. Optional — place screener calls via `dudu:place-call`

Skip this step entirely if `callagent` is not on PATH or if no candidate has explicit opt-in.

For each candidate from Stage 5b that has explicit opt-in (i.e. they responded to outreach and agreed to a 5-minute screener), invoke `dudu:place-call` with:

- `slug` = this deal
- `purpose = screener`
- `target.name` = candidate handle/name (derives the result-file kebab slug)
- `target.phone` = candidate phone (E.164)
- `consent.opted_in = true`
- `consent.token` = a fresh `uuidgen` value (one per call)
- Optionally `--simulate-first` for the first candidate of a cluster so the brief can be tuned before real calls go out
- Pass `--demo` to smoke the pipeline end-to-end without an opted-in candidate — it routes to the privacy allowlist and tags the result `demo:true`

`dudu:place-call` authors the screener brief from this deal's cluster signature and candidate `match_evidence`, writes it to `deals/<slug>/calls/`, simulates if asked, dials, and writes a result JSON. callagent enforces a privacy allowlist on `--to`; to dial real candidates the operator must export `CALLAGENT_ALLOWED_NUMBERS` for the session — do not commit real numbers to `.env`.

The result files feed `dudu:customer-debrief`, which auto-ingests `deals/<slug>/calls/*.json` alongside transcripts under `inputs/`.

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["pmf-signal"]`.
