# dudu:pmf-signal — Calibrated Persona PMF Signal & Warm-Path Outreach

**Status:** Approved design
**Date:** 2026-04-29
**Owner:** Ying-Kai Liao
**Type:** New skill in the `dudu` Claude Code plugin
**Companion change:** `dudu:diligence` orchestrator extended; `dudu:customer-discovery prep` largely subsumed

## Goal

Produce the **unique-value layer** of dudu's diligence output — the part a VC cannot easily generate by reading a pitch deck and doing generic Google searches.

Specifically:

1. **Comprehensive claim validation.** Build a structured **claim ledger** from every statement the founder and company make (in the deck, on the website, in public interviews, in the dossier the prior dudu skills already collected). Each claim declares its **verification method** — persona-reaction, cross-artifact (against an existing dudu artifact), or external-evidence (targeted web check). Stage 3 runs all three verification methods in parallel and stage 4 consolidates verdicts into a single auditable ledger.
2. **Calibrated PMF signal.** Run a structured population of 5W-grounded synthetic personas through a pitch reaction, then aggregate responses with provenance into a falsifiable hypothesis report. (This is the persona-reaction subset of #1, plus broader pain/WTP/segment exploration that doesn't trace to a specific founder claim.)
3. **Warm-path outreach.** For each cluster surfaced by the simulation, find real humans who match that signature — and the highest-leverage path to reach each one (named bridge in the VC's LinkedIn graph, broker, or community moderator).

The skill runs *after* the existing background-research phases and **consumes and cross-validates against all of their artifacts** — not just `_context.md`. `founder-*.md` is the source for founders' background claims; `market-sizing.md` is the cross-check for TAM/ICP claims; `competitive-landscape.md` is the cross-check for competitive claims; `market-problem.md` (Phase 1 context bundle and Phase 2/3 rehearsal output) is the source for market-pain triangulation. The full prior pipeline is a hard prerequisite, not an optional supplement.

## Prerequisites (hard gate)

`pmf-signal` is the **last layer** of dudu diligence, not a standalone tool. It will refuse to start until the entire upstream diligence chain has produced its artifacts. It does **not** auto-trigger upstream skills — the user must run them explicitly (typically via `dudu:diligence`) before invoking `pmf-signal`. This keeps token and fetch spend visible and under user control.

Required artifacts (all must exist under `deals/<slug>/`):

| Artifact | Producer | Used for |
|---|---|---|
| `inputs/deck.<ext>` (or pasted pitch) | user input | primary claim source |
| `personas/_context.md` | `dudu:market-problem` Phase 1 | market-reality bundle, scenario seeds |
| `market-problem.md` | `dudu:market-problem` Phase 3 | small-N rehearsal triangulation, prior persona work |
| `founder-*.md` (≥1) | `dudu:founder-check` | founder-background claim cross-check |
| `competitive-landscape.md` | `dudu:competitive-landscape` | competitive claim cross-check |
| `market-sizing.md` | `dudu:market-sizing` | TAM/ICP claim cross-check |

Pre-flight behavior on invocation:

1. Verify each required artifact exists. If any are missing, print a clear failure listing exactly which are missing and the command(s) to produce each, then stop. Example:

   ```
   pmf-signal cannot start — upstream diligence is incomplete for deal "ledgerloop":
     ✗ deals/ledgerloop/founder-jordan-peters.md (run: dudu:founder-check "Jordan Peters")
     ✗ deals/ledgerloop/competitive-landscape.md (run: dudu:competitive-landscape)
   The simplest path is to run dudu:diligence, which orchestrates the full chain.
   ```

2. If all artifacts exist, print the loading ledger so the user can confirm everything is wired up before stage 0 begins:

   ```
   Loading prior diligence for ledgerloop:
     ✓ founder-check: 2 founders (founder-dylan-martens.md, founder-jordan-peters.md)
     ✓ market-problem: _context.md (47 sources), market-problem.md (3 personas, 6 rounds)
     ✓ competitive-landscape: 8 direct, 5 indirect competitors
     ✓ market-sizing: TAM band $12B–$28B
     ✓ pitch sources: inputs/deck.pdf (12 pages); company website not provided (skip stage 0 web fetch)
   ```

3. Idempotency: if `deals/<slug>/pmf-signal.md` already exists and `--force` was not passed, print "Artifact already exists at deals/<slug>/pmf-signal.md. Pass --force to overwrite." and stop. (Same convention as every other dudu skill.)

4. Staleness: not enforced in v1. Any prior artifact, no matter how old, is treated as fresh enough. Defer staleness checks to v2.

## Non-goals

- Substitute for real customer interviews. Stance B (calibrated prior) is the explicit epistemological frame: aggregates appear in the report **as hypotheses with confidence bands**, never as findings. The skill produces structured priors to falsify in real conversations, not signal to act on directly.
- Founder reference-checking through the VC's personal network (out of scope, calendar task).
- 3rd-degree+ LinkedIn graph traversal. Stops at 2nd-degree where warm-intro signal is real.
- Auto-dialing the matched humans (deferred — schema is call-ready but stage 6 is not built in v1).
- Replacing or shrinking the existing dudu skills. All prior skills (`founder-check`, `market-problem` Phase 1+2+3, `competitive-landscape`, `market-sizing`, `customer-discovery debrief`) keep their full scope and remain hard prerequisites. `pmf-signal` adds a layer; it does not subtract from anywhere.
- Forensic-level traction verification (audit-grade revenue/customer-count claims). Stage 3c does best-effort external-evidence checks; numbers that need an actual data room are flagged as `requires-data-room` rather than verified.

## Position in the dudu workflow

```
dudu:diligence (orchestrator, extended)
├── dudu:founder-check                    # background — claims dossier per founder
├── dudu:market-problem                   # background — Phases 1+2+3 retained; both _context.md and market-problem.md feed pmf-signal
├── dudu:competitive-landscape            # background — incumbents, moats
├── dudu:market-sizing                    # background — TAM, ICP definition
├── dudu:pmf-signal           ← NEW SKILL — unique-value layer
│     ├── Stage 0: ingest claim ledger (deck + website + public statements + cross-artifact claims)
│     ├── Stage 1: define frames (purpose-typed segments)
│     ├── Stage 2: synthesize population (5W scenario-driven)
│     ├── Stage 3: claim verification (3a persona-reaction | 3b cross-artifact | 3c external-evidence; parallel)
│     ├── Stage 4: PMF signal report + consolidated claim ledger (Stance B for 3a; triangulated for 3b/3c)
│     └── Stage 5: network scan + warm-path outreach
│
├── [pause for VC's real interviews — same as today]
├── dudu:customer-discovery debrief       # background — synthesizes real interviews
└── stitched MEMO.md                      # foregrounds pmf-signal output as the unique-value section
```

Today's `dudu:customer-discovery prep` becomes a thin wrapper that exports stage 5's outreach roster into the existing `customer-discovery-prep.md` shape (so downstream `debrief` and `MEMO.md` keep working). Eventually the prep sub-action can be removed, but not in v1.

`dudu:market-problem` Phase 2/3 (the 3-persona rehearsal + cross-round analysis) is **retained, not deprecated**. Reason: it's a different lens — small-N, free-form, qualitative — and pmf-signal explicitly *consumes* its `market-problem.md` output as triangulation evidence. The two complement each other (small-N rehearsal builds the VC's gut-feel; large-N structured population produces the falsifiable prior). Both run.

## Inputs

Required artifacts are listed in the Prerequisites section above (all consumed at pre-flight).

Optional secondary sources for stage 0 claim extraction (fetched live during stage 0 if provided):

- Company website URL — homepage + pricing + about pages
- Public statements list — links to interviews, podcasts, press releases, founder blog posts (passed in by user)

Optional flags:

- `--n <int>` — total personas across all frames (default 60; min 15; max 200)
- `--frames <comma-list>` — restrict to specified frame purposes (default: all enabled)
- `--no-network` — skip stage 5 (synthesis only)
- `--public-only` — stage 5 runs without authed LinkedIn (warm-path layer reduced to brokers + community moderators)
- `--force` — overwrite existing artifacts

## Stage 0 — Claim ledger ingestion

Read **every public claim source** the deal has — the deck, the company website (if URL provided), `founder-*.md` (founders' bios and prior-venture claims), and any optional public statements — and extract a single structured `pitch.yaml` that is the **claim ledger**. This is the artifact under test.

Every claim row carries: claim text, source provenance (file + page/section/URL), claim category, and **verification method** that determines how it gets tested in stage 3.

```yaml
product:
  name: <string>
  one_liner: <string>
  category: <string>

target_market:
  stated_icp: <string>           # founder's exact words
  stated_segments: [<string>]    # if multiple

claims:
  # ─── customer/pain/WTP claims → stage 3a (persona-reaction) ───
  - claim_id: c-001
    claim: "SA freelancers lose 2 days/quarter to SARS"
    category: pain
    source: "deck p.3"
    verification_method: persona-reaction

  - claim_id: c-002
    claim: "buyers will pay R6,000–R10,000/month"
    category: wtp
    source: "deck p.7"
    verification_method: persona-reaction

  - claim_id: c-003
    claim: "buyers find us via accountant referrals"
    category: gtm-distribution
    source: "deck p.9"
    verification_method: persona-reaction

  # ─── traction claims → stage 3c (external-evidence) ───
  - claim_id: c-010
    claim: "200 paying customers"
    category: traction
    source: "deck p.4"
    verification_method: external-evidence
    external_check: ["customer-list-on-website", "testimonial-count", "linkedin-employee-count-trend"]

  - claim_id: c-011
    claim: "growing 30% MoM for 6 months"
    category: traction
    source: "deck p.4"
    verification_method: external-evidence
    external_check: ["wayback-machine-claim-history"]
    flag_if_unverifiable: requires-data-room

  # ─── founder background claims → stage 3b (cross-artifact: founder-check) ───
  - claim_id: c-020
    claim: "co-founder previously exited to Stripe"
    category: founder-background
    source: "deck p.2"
    verification_method: cross-artifact
    cross_artifact: founder-check
    cross_artifact_target: founder-dylan-martens.md

  # ─── market size claims → stage 3b (cross-artifact: market-sizing) ───
  - claim_id: c-030
    claim: "addressable market is $50B globally"
    category: market-size
    source: "deck p.5"
    verification_method: cross-artifact
    cross_artifact: market-sizing
    cross_artifact_target: market-sizing.md

  # ─── competitive claims → stage 3b (cross-artifact: competitive-landscape) ───
  - claim_id: c-040
    claim: "no direct competitors in SA"
    category: competitive
    source: "deck p.6"
    verification_method: cross-artifact
    cross_artifact: competitive-landscape
    cross_artifact_target: competitive-landscape.md

unstated_assumptions:            # filled by LLM during stage 0 review
  - assumption: "founder assumes accountants are gatekeepers, not blockers"
    derived_from: "deck p.9 + p.7"
    promoted_to_claim: c-003     # already a claim, this just notes the link
```

### Verification method semantics

- **`persona-reaction`** → claim is tested by stage 3a (every persona reacts to it inside the pitch-reaction; aggregate verdict in stage 4).
- **`cross-artifact`** → claim is tested by stage 3b (programmatic cross-check against the named existing dudu artifact; verdict comes from supporting/contradicting passages found there).
- **`external-evidence`** → claim is tested by stage 3c (targeted live web research with a small fetch budget per claim; flag with `requires-data-room` if forensic-level verification is needed).

### Auto-classification

The classifier defaults are:
- `pain | wtp | urgency | trigger | switching | gtm-distribution | gtm-channel` → `persona-reaction`
- `founder-background | founder-prior-venture | founder-credentials` → `cross-artifact:founder-check`
- `market-size | tam | sam` → `cross-artifact:market-sizing`
- `competitive | unique-advantage | moat-claim` → `cross-artifact:competitive-landscape`
- `traction | revenue | customer-count | growth-rate | retention | nps` → `external-evidence`

Stage 0 surfaces the claim ledger to the user before stage 1 starts. The user can re-classify any claim's `verification_method` if the auto-classifier guessed wrong.

## Stage 1 — Frame definition

A **frame** is a typed segment + purpose pair. The user's frames in v1:

| Frame purpose | Asking lens | What stage 3 captures per persona |
|---|---|---|
| **`pmf-validation`** | "Would you use this? What makes you say no?" | Use intent, top hesitation, would-pay (Y/N + band), kill-switch reason |
| **`founder-claim-validation`** | Per `pitch.yaml` claim → agree/partial/disagree + verbatim | Per-claim verdict + contradicting quote |
| **`jtbd-discovery`** | JTBD: job, forces, anxieties, progress | Pain triggers, switching forces, current solution |
| **`bant-qualification`** | BANT: budget, authority, need, timeline | Budget band, authority level, urgency, timeline |

Default v1 frames enabled: **`pmf-validation`, `founder-claim-validation`, `jtbd-discovery`**. `bant-qualification` ships built-in but disabled-by-default (low marginal value once PMF is established). All other purposes (Van Westendorp WTP, incumbent threat, etc.) are out of scope.

Each frame defines:

- **Segments** — 1–3 customer types this frame applies to (derived from `pitch.yaml.target_market` and `_context.md`'s segment evidence). Total segments across frames cap at 5 to bound population size.
- **Must-cover cells** — typically 8–12 attribute cells per segment that *guarantee* coverage (the founder's stated ICP center is always one). Generation will produce 1–3 personas per must-cover cell.
- **Distribution sampling profile** — weighted distributions over Layer 1 attributes for the remaining persona slots.

Frames are written to `deals/<slug>/personas/frames.yaml`.

## Stage 2 — Population synthesis (5W scenario-driven)

This is the core depth of the skill. **Every persona is constructed by causal reasoning from a scenario seed, not by attribute fill.**

### Scenario-seed mining

Before generating any persona, mine `_context.md` for **scenario seeds**: specific triggering moments grounded in cited evidence (Reddit complaints, forum threads, review quotes, regulatory events, growth milestones described in interviews).

Each seed has:

```yaml
seed_id: s-014
trigger: "hit VAT threshold mid-fundraise, mid-Q3"
trigger_type: regulatory-growth-collision
source_quote: "Just realised I crossed VAT threshold last month and the data room is open..."
source_ref: "_context.md L88 (Reddit r/SouthAfrica thread, Aug 2025)"
implied_attributes:
  stage: [seed, series-a]        # narrow but not single
  geography: ZA-anywhere
  vertical: b2b-saas-likely
```

Cluster seeds by `trigger_type` to detect mode-collapse early — if 90% of seeds are the same trigger, surface that as a context-bundle gap and request expansion before continuing.

### Persona construction (5W chain, strict)

For each persona slot, the LLM walks the 5W chain in order. **All five must be filled and traceable, or generation fails for that slot** — the failure is logged as evidence that `_context.md` has a coverage gap at that cell. This is correct behavior.

1. **Why (now)** — sample a scenario seed from the pool. Layer 0 anchors here.
2. **When** — temporal shape of the pain (`one-time-haunting`, `quarterly`, `continuous`, `trigger-only`).
3. **Who** — derived from the scenario, not pre-decided. Role, stage, demographics, authority.
4. **Where** — physical + channel context ("kitchen table 11pm, fundraise data room open in next tab").
5. **What** — verbatim phrasing of how this persona talks and acts in the moment.

Layer 1 attributes (clustering dimensions) and Layer 2 framework-specific fields are **outputs** of this chain, not inputs.

### Persona row schema

Each persona is one structured record at `deals/<slug>/personas/rows/p-<id>.yaml`, plus an optional human-readable Markdown sidecar at `personas/sidecars/p-<id>.md`. The schema:

```yaml
persona_id: p-007
frame_id: ledgerloop.jtbd-discovery
segment: cape-town-saas-founder
generated_at: 2026-04-29T14:00:00Z

# ─── Layer 0: Scenario (provenance unit) ───
scenario:
  trigger: "hit VAT threshold mid-fundraise, mid-Q3"
  trigger_type: regulatory-growth-collision
  source_seed: s-014
  source_ref: "_context.md L88"
  when: one-time-haunting          # quarterly | continuous | trigger-only | one-time-haunting
  where: "kitchen table 11pm, fundraise data room open in next tab"
  why_unsolved: "CA does year-end only; no real-time threshold monitor"

# ─── Layer 1: Identity & attributes (clustering dimensions) ───
attributes:
  role: founder-ceo
  geography: ZA-Western-Cape
  stage: pre-seed
  vertical: b2b-saas
  team_size: 3
  revenue_band_mrr_zar: [150000, 300000]
  buying_authority: sole

# ─── Layer 2: Framework-specific (varies by frame) ───
framework_jtbd:
  pain_intensity: 8               # 1–10
  pain_frequency: trigger-only
  current_solution: "Xero + receipt-tool + year-end CA"
  switching_forces:
    push: "penalty letter anxiety"
    pull: "promise of one-shot setup"
    anxiety: "vendor lock-in, month-3 abandonment"
    habit: "Xero is fine, why switch the layer above it"
  progress_blockers: ["no real-time threshold monitoring"]

# ─── Layer 3: NLP / matching fuel (every frame) ───
voice:
  pain_phrases:
    - "I just want it handled"
    - "show me the API"
    - "if I solve it once and never think about it again, I'll pay 2x"
  objections:
    - "everyone says AI now"
    - "another monthly subscription"
  purchase_trigger: "next penalty letter"

discoverability_signals:
  job_titles: ["co-founder", "CEO", "CTO"]
  communities:
    - "Silicon Cape Slack #founders"
    - "Founder Institute SA alumni"
  post_patterns:
    - "complaints about SARS provisional tax"
    - "asking which CA handles Delaware C-corp + SA Pty"
  query_strings:
    - 'site:reddit.com "VAT threshold" "fundraise" South Africa'
    - 'site:linkedin.com/in/ "founder" "Cape Town" "SaaS"'

# ─── Provenance ───
context_grounding:
  - {claim: "pain 8/10", source: "_context.md L42, L88"}
  - {claim: "WTP band R6k–R10k/mo", source: "_context.md L156 (Inkle pricing reference)"}
fabrication_flags: []              # populated when LLM had to extrapolate
```

### Generation strategy

Stratified hybrid (option C from brainstorming):

1. Enumerate must-cover cells across all frames (≈10–12 cells); generate 1–3 personas per cell. The founder's stated ICP center is always among them — those rows feed `founder-claim-validation` directly.
2. Distribution-sample the remaining slots up to N (default 60).
3. Refuse persona slots where the 5W chain cannot be grounded in `_context.md`. Log refusals in `personas/refusals.md` as a context-bundle gap report.

### Parallelization

Population synthesis is embarrassingly parallel per frame. Dispatch one worker subagent per frame using the `lib/research-protocol.md` parallelization primitive. Each subagent receives the full `_context.md`, `pitch.yaml`, the frame's `frames.yaml` entry, the scenario seed pool for that frame, and the row schema. Returns: row YAML files as text. Main session writes them to disk and runs the seed-cluster mode-collapse check.

## Stage 3 — Claim verification (three sub-stages, parallel)

Stage 3 fans out the claim ledger into three independent verification paths, run concurrently. Each emits a verdict per claim it owns. Stage 4 consolidates them into a single ledger.

### Stage 3a — Persona pitch-reaction

For each persona, run **one** structured reaction interview against the pitch and the persona-reaction-bound claims.

The interview prompt (per persona):

> You are [persona]. Here is the pitch: [pitch.yaml rendered]. React honestly, in your voice (use phrases from your `voice.pain_phrases` and `voice.objections`).
>
> 1. Would you use this? Why or why not?
> 2. What is your single biggest hesitation?
> 3. Would you pay for this? At roughly what price would you say no?
> 4. What would make you say no immediately?
> 5. For each of these claims the founder is making — agree, partial, or disagree, and quote yourself: [render the subset of `pitch.yaml.claims` where `verification_method == persona-reaction`]

Output at `personas/reactions/p-<id>.yaml`:

```yaml
persona_id: p-007
reaction_at: 2026-04-29T14:30:00Z
would_use: yes-with-caveats          # yes | no | yes-with-caveats
biggest_hesitation: "another monthly subscription on top of Xero"
willing_to_pay: yes
wtp_ceiling_zar_per_month: 12000
kill_switch: "if it can't talk to my US accountant's QBO, it's dead to me"
claim_responses:
  - claim_id: c-001
    verdict: agree
    verbatim: "Two days minimum. Last quarter it was three because the eFiling site went down."
  - claim_id: c-003
    verdict: disagree
    verbatim: "My CA would never recommend a tool that replaces parts of his work."
provenance:
  voice_phrases_used: ["another monthly subscription"]
  context_grounding: ["_context.md L42"]
```

**Parallelization:** dispatch worker subagents in batches of 20 personas each.

### Stage 3b — Cross-artifact verification

For each claim with `verification_method: cross-artifact`, programmatically verify against the named existing dudu artifact. The artifact has already been written by the prior dudu skill in the orchestrator chain — pmf-signal does not re-fetch evidence, it reads the artifact and finds supporting/contradicting passages.

Per-claim procedure:

1. Open the target artifact (`founder-*.md`, `market-sizing.md`, or `competitive-landscape.md`).
2. Search for passages relevant to the claim (LLM judgement, anchored by claim category and keywords).
3. Emit a verdict + verbatim quote from the artifact.

Verdict shape:

```yaml
claim_id: c-020
claim: "co-founder previously exited to Stripe"
verification_method: cross-artifact
cross_artifact: founder-check
cross_artifact_target: founder-dylan-martens.md
verdict: partial                     # supports | partial | contradicts | no-evidence
supporting_quotes:
  - quote: "joined Stripe via acquihire of Acme Co (2019)"
    location: "founder-dylan-martens.md L42"
contradicting_quotes:
  - quote: "Acme Co was an acquihire, not a strategic acquisition; no shareholder return."
    location: "founder-dylan-martens.md L48"
verdict_rationale: "the exit happened but the framing in the deck implies founder liquidity that the founder-check dossier disputes"
```

**Parallelization:** all cross-artifact claims are independent; dispatch one subagent per claim category (founder / market-sizing / competitive) with the relevant artifact full-text. Typical run: ~5–15 claims total across the three categories.

### Stage 3c — External-evidence verification

For each claim with `verification_method: external-evidence`, run a **bounded** targeted web check. Cap: 5 fetches per claim, 30 fetches total across stage 3c.

Each `external_check` slug maps to a verification recipe:

| Recipe | What it does |
|---|---|
| `customer-list-on-website` | Fetch homepage + customers/case-studies pages; count distinct logos and named customers. |
| `testimonial-count` | Fetch homepage + about/customers pages; count testimonial blocks with named attributions. |
| `linkedin-employee-count-trend` | Fetch LinkedIn company page (authed); compare current employee count to historical via Wayback. |
| `wayback-machine-claim-history` | Fetch 3–5 historical snapshots of the relevant page; surface what the claim was N months ago. |
| `seo-ranking-check` | Run targeted Google searches for category keywords; note where the company ranks. |
| `g2-capterra-presence` | Check if listed; note review count and rating. |
| `funding-corroboration` | Check Crunchbase/PitchBook public-tier or news mentions. |

Verdict shape:

```yaml
claim_id: c-010
claim: "200 paying customers"
verification_method: external-evidence
external_check_results:
  - recipe: customer-list-on-website
    finding: "homepage shows 18 named customers; case-studies page lists 7 detailed case studies"
    fetched: ["https://example.com", "https://example.com/customers"]
  - recipe: testimonial-count
    finding: "12 testimonials with named attribution"
    fetched: ["https://example.com/about"]
  - recipe: linkedin-employee-count-trend
    finding: "current employee count 14; Wayback snapshot (Jan 2026) shows 11"
    fetched: ["..."]
verdict: insufficient-evidence-for-200   # supports | partial | contradicts | insufficient-evidence-for-<X> | requires-data-room
verdict_rationale: "public surface area (18 logos, 12 testimonials, 14 employees) is consistent with low-tens-of-customers, not 200"
flags: []                                 # requires-data-room if applicable
```

**Parallelization:** one subagent per claim, dispatched concurrently up to a max-concurrency cap (default 5). Each subagent owns its 5-fetch budget.

### Stage 3 output index

After 3a/3b/3c finish, write `personas/verdicts.yaml` — a flat index of all `claim_id → verdict + provenance + method`. Stage 4 reads from this.

## Stage 4 — PMF signal report (Stance B aggregates + consolidated claim ledger)

Aggregate reactions and verdicts into `deals/<slug>/pmf-signal.md`. **Every aggregate stat carries (n, σ where applicable, grounded-vs-fabricated split, frame breakdown).** Every claim verdict carries its verification method explicitly so the reader knows how strong the evidence is.

Required sections:

```markdown
# PMF signal: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>
**Population:** N=<total> across <frame_count> frames; <grounded>/<fabricated> grounded-vs-fabricated split
**Claims tested:** <total_claims> (persona-reaction: <n>, cross-artifact: <n>, external-evidence: <n>)

> ⚠️ This report is a CALIBRATED PRIOR, not signal. Persona-reaction aggregates are LLM aggregates over a structured synthetic population — hypotheses to falsify in real customer interviews. Cross-artifact verdicts triangulate against prior dudu research. External-evidence verdicts are best-effort web checks bounded at 5 fetches per claim — anything forensic is flagged `requires-data-room`. Read the verdict's verification method before drawing conclusions.

## Headline read

[3 sentences. The strongest pattern, the strongest founder-claim contradiction, the largest cluster's verdict.]

## Consolidated claim ledger

The full ledger of every claim made by founder/company, with verdict and verification method labeled. **Sorted by severity** (contradicts > partial > insufficient-evidence > supports), so the reader sees the worst news first.

| Claim | Source | Category | Verdict | Verification method | Strongest evidence |
|---|---|---|---|---|---|
| "buyers find us via accountant referrals" | deck p.9 | gtm-distribution | **contradicts** (44/60 personas disagree) | persona-reaction | "My CA would never recommend a tool that replaces his work" (p-007) |
| "200 paying customers" | deck p.4 | traction | **insufficient-evidence-for-200** | external-evidence | public surface shows ~18 named logos, 14 employees |
| "no direct competitors in SA" | deck p.6 | competitive | **contradicts** | cross-artifact:competitive-landscape | "Pastel-to-Xero migration firms compete directly on the same buyer" (competitive-landscape.md L88) |
| "co-founder exited to Stripe" | deck p.2 | founder-background | **partial** | cross-artifact:founder-check | acquihire happened but no shareholder return (founder-dylan-martens.md L48) |
| "addressable market is $50B" | deck p.5 | market-size | **partial** | cross-artifact:market-sizing | global TAM band per market-sizing is $12B–$28B (market-sizing.md L102) |
| "SA freelancers lose 2 days/quarter" | deck p.3 | pain | **supports** (38/60 agree) | persona-reaction | "Two days minimum. Last quarter it was three" (p-014) |

## Pitch-reaction aggregates

| Metric | Value | n | σ | Grounded n | Notes |
|---|---|---|---|---|---|
| would_use = yes | 41% | 60 | — | 49 | clusters around regulatory-growth-collision trigger |
| would_pay = yes | 28% | 60 | — | 49 | drops sharply for one-time-haunting trigger |
| WTP ceiling (median, ZAR/mo) | 8500 | 17 | 2400 | 14 | 17 personas gave a number; 11 refused to anchor |

## Cluster patterns (by trigger_type)

[For each cluster (≥5 personas), one section. Includes: trigger type, n, mean pain, dominant pain phrase, would-pay rate, top objection, top resonance quote with persona_id citation.]

## Strongest contradictions

[3–6 places where personas disagreed sharply, OR where founder claims diverged from cross-artifact / external evidence. Each rooted in two contradicting verbatim quotes.]

## Weakest assumptions in the founder's pitch

[3–6 places where founder claims fell hardest. Pull from the consolidated claim ledger above — the contradicts/partial verdicts. For each: the claim, the verification method, the divergence quote.]

## Verifications that need a data room

[List of claims flagged `requires-data-room` — the VC must request these directly from the founder. Typical: revenue numbers, retention/cohort data, cash burn, contract terms.]

## Population audit

- Total personas: <N>
- By frame: [frame_id → n]
- By segment: [segment → n]
- By trigger type: [trigger_type → n]
- Refusals (couldn't ground): <count> — see `personas/refusals.md`
- Fabrication flags: <count> — top fabricated claims listed below
- Mode-collapse check: [pass/fail per seed-cluster diversity heuristic]

## Source artifacts

- pitch.yaml (claim ledger)
- personas/_context.md
- personas/frames.yaml
- personas/rows/*.yaml
- personas/reactions/*.yaml
- personas/verdicts.yaml
- personas/refusals.md
- (cross-referenced) founder-*.md, market-sizing.md, competitive-landscape.md, market-problem.md
```

## Stage 5 — Network scan & warm-path outreach

For each cluster surfaced in stage 4 (≥5 personas with the same `trigger_type` × frame), find real humans matching that signature and the highest-leverage path to reach each.

### 5a. Match

Per cluster, generate targeted searches from the union of the cluster's `discoverability_signals` (job titles ∩ communities ∩ post patterns ∩ query strings).

Channels and budgets:

- **LinkedIn (authed Playwright, main session only)** — ~5 fetches per cluster, filtered by job title and geography from the cluster.
- **Reddit** — surface ~5 candidates per cluster from the cluster's `post_patterns` queries.
- **Niche communities** — Slack/Discord with public membership lists, 1–2 per cluster, ~5 candidates.
- **X** — search the cluster's `voice.pain_phrases` + geography filter, ~5 candidates.

Parallelize: one subagent per cluster × non-LinkedIn channel; LinkedIn runs in main session. Cap total candidates at 30 across the deal (matching today's `customer-discovery prep` ceiling).

Each candidate row is anchored to a **match evidence** quote: a public post or profile snippet that ties the candidate to the cluster's signature. No-evidence candidates are dropped.

### 5b. Network understanding

For each surviving candidate, enrich with:

1. **Warm-path inference (authed LinkedIn 1st/2nd-degree).** Stops at 2nd. Names the bridge if one exists. Skipped under `--public-only`.
2. **Broker identification.** For each candidate's primary community, surface the named moderator/manager/chair (Slack mod, subreddit mod, Vistage chair, accelerator program lead). One broker per community is sufficient.
3. **Channel-fit prior.** Per channel, label expected response and risk:
   - `expected_response`: `low` (≈0.05–0.10) | `medium` (≈0.10–0.25) | `high` (≈0.25+)
   - `risk`: `low` | `medium-spam` | `high-ban` (some communities ban DMs / solicitation)
   - **Conditioned on the specific community**, not the channel-in-the-abstract.
4. **Post hooks.** Recent (≤30 days) post by the candidate that anchors the outreach. Generic DMs underperform; "saw your post about X" outperforms by an order of magnitude.

### Stage 5 row schema

```yaml
candidate_id: c-014
cluster_id: regulatory-growth-collision
match_evidence:
  url: "https://reddit.com/r/SouthAfrica/comments/xyz"
  quote: "just got R45k SARS penalty for missing my first provisional"
  date: 2026-04-12
person:
  name: "Daniel M."
  handle_or_link: "https://www.linkedin.com/in/daniel-marlin-112802b3"
  role_inferred: "founder, B2B SaaS"
  geography_inferred: "Cape Town"
warm_path:
  exists: true
  degree: 2
  bridge_name: "John Doe (VC's 1st degree)"
  confidence: high              # high | medium | low
brokers:
  - {community: "Silicon Cape Slack", role: "moderator", contact: "<URL>"}
channel_fit_ranked:
  - {channel: warm-intro-via-john, expected_response: high, risk: low}
  - {channel: linkedin-dm, expected_response: medium, risk: low}
  - {channel: reddit-dm-public-thread-reply-first, expected_response: medium, risk: medium-spam}
  - {channel: cold-email, expected_response: low, risk: low, note: "no public email found"}
post_hooks:
  - {url: "...", date: 2026-04-12, summary: "VAT penalty rant"}
recommended_outreach:
  channel: warm-intro-via-john
  draft: "[80-word draft referencing John, the candidate's VAT post, and the research framing]"
```

### Output: stage 5 artifact

`deals/<slug>/outreach.md` — replaces the role today's `customer-discovery-prep.md` plays. Cluster-stratified, with the 30-row table prioritized by warm-path quality (warm 1st-degree → 2nd-degree → broker-mediated → public-only DM → cold).

For backwards compatibility with the existing `dudu:customer-discovery debrief` workflow, also emit a slimmed `customer-discovery-prep.md` that has the same shape as today (target list + outreach templates + interview script). The interview script is auto-generated from the cluster patterns + strongest contradictions in `pmf-signal.md`.

## Diligence orchestrator changes

`dudu:diligence` step 2 sub-skill order changes to:

1. `dudu:founder-check` — for each founder (unchanged)
2. `dudu:market-problem` — full Phases 1+2+3 (unchanged)
3. `dudu:competitive-landscape` (unchanged)
4. `dudu:market-sizing` (unchanged)
5. **`dudu:pmf-signal`** ← new (consumes all four prior artifacts; its stage 5 emits both `outreach.md` and the legacy-shape `customer-discovery-prep.md` that downstream `debrief` consumes)

`dudu:customer-discovery prep` is no longer invoked by the orchestrator at the prep phase. It becomes a thin standalone-only skill (for users who want to run it without the full pipeline), and its orchestrator role disappears. `dudu:customer-discovery debrief` keeps its current orchestrator role unchanged at step 4 of the original flow.

`MEMO.md` step 5 gets a new section between **Problem and product** and **Customer signal**:

```markdown
## PMF signal & claim verification (calibrated prior + cross-artifact + external)

[Headline read from `pmf-signal.md`. The top 5 rows of the consolidated claim ledger (worst-news-first ordering). The 1 strongest cluster pattern. Explicit Stance B disclaimer for the persona-reaction rows; cross-artifact and external-evidence rows do not need the same disclaimer because they triangulate against actual evidence. List of `requires-data-room` flags for the VC to follow up on.]
```

This is the unique-value section of `MEMO.md` — what the orchestrator earns its keep on. It's positioned right after Problem so a reader sees the founder's claims tested before any other narrative layer.

## Manifest changes

`deals/<slug>/manifest.json` `skills_completed` adds `"pmf-signal"`. Existing six keys keep their meaning. The orchestrator step 6 verifies all seven are non-null.

## Open implementation questions

These are flagged for the implementation plan to decide; they don't block the design.

1. **N tuning.** Default 60 is a guess. Implementation should run on the existing `ledgerloop` deal at N=30, 60, 120 and surface the cost vs signal-density tradeoff before locking the default.
2. **Reaction-vs-row decoupling.** Whether `personas/rows/*.yaml` and `personas/reactions/*.yaml` should be merged or kept separate. Separate is simpler for re-running stage 3a against a new pitch revision (the rows are stable; reactions invalidate). Lean: keep separate.
3. **Mode-collapse heuristic.** "If 90% of seeds share a `trigger_type`, surface as gap" — exact threshold and metric (entropy? top-1 share?) to be picked during implementation against ledgerloop's seed pool.
4. **Schema versioning.** Persist `schema_version: 1` on every row/reaction/verdict so future schema migrations are tractable.
5. **Token + fetch budget per deal.** Stage 3a (N=60 pitch reactions) is the largest LLM spend; stage 3c (external-evidence) is the largest fetch spend (cap 30 + 5/claim). Benchmark against `ledgerloop` and gate behind a soft warning if estimated cost > $X (X TBD).
6. **Auto-classifier accuracy.** Stage 0's auto-mapping of claim category → verification method may be wrong on edge cases (e.g., "we have product-market fit" — is that a traction claim or a pmf claim?). Decide whether to default-prompt the user to confirm the ledger before stage 1, or assume defaults and only prompt when classifier confidence is low.
7. **External-evidence recipe library.** The `external_check` recipes table in stage 3c is bounded but the recipes themselves need implementation. Decide which subset is in v1 (lean: customer-list-on-website, testimonial-count, wayback-machine-claim-history; defer LinkedIn employee count and SEO ranking).

## Future work (out of v1)

- Stage 6: actual outreach automation (the schema is call-ready; bringing email/DM dispatch in scope is a separate plan).
- WTP frame using Van Westendorp anchoring.
- Incumbent-threat frame using 5-whys.
- Hybrid VC-in-the-loop personas (founder-team-member can voice a persona, mixed with synthetic).
- Multi-platform graph (X follows, GitHub, Substack) for warm-path inference.
- Cross-deal learning: aggregate cluster patterns across deals to surface recurring market signals.
