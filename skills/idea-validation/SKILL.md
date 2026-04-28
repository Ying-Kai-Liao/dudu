---
name: idea-validation
description: Idea-stage wedge selection with category-level market mapping. First maps the category — direct + indirect competitors, pricing benchmarks, funding and tailwinds — then compares 2–5 candidate user personas / segments side-by-side on pain, WTP, reachability, competitive fit, and segment size to recommend a wedge or flag that no segment yet justifies building. Pre-product, secondary-research only.
---

# Idea validation

Map the category, then compare candidate ICPs against it, and pick the strongest wedge. Read `lib/research-protocol.md` and `lib/playwright-auth.md` first. Budget: ~15 fetches for the market map + ~6–8 fetches per candidate, ~60 fetches total.

## What this skill IS and IS NOT

- IS: a two-layer analysis at idea stage. Layer 1 maps the category (who plays here, what they charge, who is funding this space). Layer 2 compares 2–5 candidate personas/segments head-to-head against that category map. Output is a wedge recommendation with explicit confidence.
- IS NOT: validation through real customers (that's `dudu:customer-discovery`). IS NOT a deep one-wedge rehearsal (that's `dudu:market-problem`). IS NOT a defensible TAM (that's `dudu:market-sizing`). IS NOT a deep competitor diligence on a chosen company (that's `dudu:competitive-landscape`) — the market layer here is *category-shaping for wedge selection*, not company-vs-company combat analysis.

State these distinctions in the artifact every time. The point of this skill is *which wedge in which category*, not *is there real demand* — only real interviews settle that.

## When to use

- Founder has an idea but hasn't chosen a wedge.
- VC suspects the founder picked the wrong wedge and wants to test alternatives before deep-diving.
- Pre-flight before `dudu:market-problem` when the ICP input would otherwise be a guess.

If the founder already has paying customers or strong customer-discovery signal, skip this and run `dudu:market-problem` directly.

## Inputs

Required (prompt if missing):
- Deal slug
- Company name (or working title for the idea)
- One-line problem statement (what hurts, for whom, when)
- Either:
  - A list of 2–5 candidate personas/segments to compare, OR
  - Permission to generate 3 candidates from the problem statement

Optional:
- Geographic scope (default: global English-speaking)
- Hard constraints (e.g., "must be SMB, not enterprise" / "must not be regulated industries")
- Pitch deck text

## Pre-flight

Idempotency check. Artifact: `deals/<slug>/idea-validation.md`. Candidate profiles live under `deals/<slug>/candidates/`. The market map lives at `deals/<slug>/market-map.md`.

If `deals/<slug>/idea-validation.md` exists and `--force` was not passed, print "Artifact already exists at deals/<slug>/idea-validation.md. Pass --force to overwrite." and stop.

## Method

### Step 1 — Map the category (runs once, before any candidate work)

Goal: understand the market the idea would enter, *independent of which persona it targets*. This is the category-shaping pass. Write `deals/<slug>/market-map.md`. Cap at ~15 fetches across:

1. **Direct competitors** — products solving the same job. Use Product Hunt category search, Crunchbase category, G2/Capterra category. For each, capture: positioning one-liner, pricing tier(s), funding stage, last public activity, primary ICP they target.
2. **Indirect competitors / substitutes** — what people use *today* instead (spreadsheets, agencies, internal tools, the status quo). Pull from Reddit/HN/forum threads where the pain is discussed — what do people say they currently do?
3. **Pricing benchmarks** — concrete ACV anchors across the category: lowest-tier, mid-tier, enterprise. At least 3 data points if the category has them. Note whether the category is freemium-dominant, seat-based, usage-based, or services-priced — this constrains which candidates can support a venture outcome.
4. **Funding and tailwinds** — Crunchbase or news search for the category over the last 18 months: who raised, what stage, what thesis. A funded, growing category is proof of demand; an empty category is a red flag *or* a true greenfield (call which).
5. **Structural shifts** — is something in the world (regulation, AI capability, platform shift, demographic) changing what's possible here? One paragraph with citations, or "no clear shift identified."

Write `market-map.md` with these sections:

```markdown
# Market map: <Category>

**Generated:** <ISO timestamp>

## Category boundary
[1–2 sentences: what's in scope, what's out. Name the category in the founder's language and in analyst language if they differ.]

## Direct competitors

| Product | Positioning | Pricing | Stage / last raise | Primary ICP | Source |
|---------|-------------|---------|--------------------|-------------|--------|
| ... | ... | ... | ... | ... | [link] |

## Indirect competitors / status quo

| Substitute | Why people use it today | Why it's inadequate (verbatim quotes if available) | Source |
|------------|--------------------------|----------------------------------------------------|--------|
| ... | ... | ... | [link] |

## Pricing benchmarks

- Low tier: $X/seat/mo or $X/yr — [product, link]
- Mid tier: ...
- Enterprise: ...
- **Pricing model dominant in this category:** freemium / seat / usage / services
- **Implication for WTP:** [one sentence]

## Funding and tailwinds (last 18 months)

[3–6 bullet points with citations: who raised, what they pitched, what stage]

## Structural shifts

[One paragraph with citations, or "no clear shift identified."]

## Category verdict

Pick one and justify in one sentence:
- **Empty** — no commercial precedent. New category bet.
- **Forming** — early funded entrants, no clear leader.
- **Contested** — multiple funded players, room for differentiation.
- **Saturated** — clear leader(s) own the category; differentiation must be sharp.

## Sources
- ...
```

### Step 2 — Generate or accept candidates

If candidates were supplied, write each to `deals/<slug>/candidates/candidate-K.md` using the profile template below. If not supplied, generate 3 candidates that span meaningfully different axes — e.g., different company size, different job-to-be-done, different industry — not three flavors of the same buyer.

Use `market-map.md` to inform candidate generation: candidates should target *underserved or differently-served* slices of the category, not the slice every direct competitor already owns.

Candidate profile template (`candidates/candidate-K.md`):

```markdown
# Candidate <K>: <short label>

**Segment:** <industry / company size / role band>
**Buyer role:** <job title that signs the contract>
**User role:** <job title that uses the product daily — may be the same>
**Buying trigger:** <the moment that makes them shop>
**Why this candidate is plausible:** <one sentence>
**How this differs from the other candidates:** <one sentence — must be a real difference, not a synonym>
**Which competitors from the market map already serve this candidate:** <list, or "none identified">
**Which substitutes/status-quo from the market map this candidate uses today:** <list>
```

Hard rule: each candidate must differ from the others on at least one of {industry, company-size band, buyer role, buying trigger}. If two candidates collapse onto the same axis, merge them.

### Step 3 — Research each candidate (parallel, ~6–8 fetches each)

The category-level research from Step 1 is shared across candidates, so per-candidate work focuses on what's *specific* to this slice. For each candidate, spend up to ~6–8 fetches across:

1. **Persona-specific pain quotes** — Reddit / HN / niche forums and segment-specific subreddits or trade-association forums. Quote complaints verbatim. Look for the segment's *own* phrasing of the pain.
2. **Persona-specific WTP signal** — does this segment already buy adjacent tools? At what price? Reviews where price is mentioned, segment-targeted product pricing pages, vendor case studies that quote contract sizes.
3. **Reachability** — can you actually find 100 of these people? Public lists, named communities, conferences, professional associations, industry directories, LinkedIn search counts via Playwright.
4. **Population / segment size** — BLS/Eurostat occupational counts, industry-association membership counts, LinkedIn filtered counts. One credible number is enough at this stage.
5. **Competitor overlap with this candidate** — of the direct competitors in the market map, which ones target *this* candidate vs. a different one? Read their landing pages, customer-logo walls, case studies, ICP statements. A competitor that loudly targets enterprise leaves the SMB candidate more open.

Apply `lib/research-protocol.md` citation rules. If a dimension can't be sourced for a candidate, write **"Not found in public sources"** — never invent. Do not re-fetch category-level data already in `market-map.md`; cite it.

### Step 4 — Score each candidate on the rubric

Score every candidate on the same seven dimensions, 1–5, with a one-line evidence-anchored rationale per score. Refuse to score without a citation; mark as `?` if the evidence is missing and explain in the rationale.

| Dimension | What scores high (5) | What scores low (1) |
|-----------|----------------------|---------------------|
| **Pain severity** | Multiple verbatim complaints calling it urgent/critical/blocker | Pain only inferred from product marketing |
| **Pain frequency** | Daily/weekly recurring | Annual or one-off |
| **WTP proxy** | Segment already pays >$X for adjacent tools; explicit price quotes; category pricing supports venture economics | No comparable spending pattern; free tools dominate; category pricing is structurally low |
| **Reachability** | Public lists, identifiable channels, named communities | Diffuse, no clear way to find or contact 100 of them |
| **Category proof** | Funded startups + paying users in the broader category (from market map) | No commercial precedent; category is inert or dead |
| **Competitive room for this candidate** | No incumbent loudly owns this candidate's slice; room to land a wedge | A clear leader already serves this exact candidate well |
| **Segment size** | Reachable population large enough that a wedge of it sustains a startup | Too small to support a venture outcome |

Notes on the rubric:
- **Category proof** comes from `market-map.md` and is the same value for every candidate of a given idea. It's the "is anyone making money in this category at all?" check.
- **Competitive room** is per-candidate and answers "is *this slice* taken?" — a saturated category can still have an underserved candidate.
- A `?` (insufficient evidence) is more honest than a guessed score. Multiple `?`s on the same candidate is itself a finding: "we can't tell yet."

### Step 5 — Cross-candidate comparison

Build the head-to-head matrix. Then write the comparison narrative: where do candidates agree, where do they diverge, and which dimensions carried the most weight? Explicitly call out where the market map made a candidate look better or worse than it would have looked in isolation.

### Step 6 — Wedge recommendation

Pick one of:
- **Lead candidate identified** — name it, justify in 3 sentences referencing the rubric, list the 3 strongest evidence quotes from that candidate's research, and state confidence (Low / Medium / High).
- **Tie / too close to call** — name the top 2, explain what evidence would break the tie, and propose the next research step.
- **No viable wedge yet** — state the binding constraint (e.g., "no candidate showed WTP signal above $X") and what the founder would need to discover to make this idea pursuable.

Confidence floor: if 3+ dimensions are `?` for the lead candidate, confidence cannot exceed Low. Also: if the market map's category verdict is **Empty** and there is no candidate with concrete WTP evidence, confidence cannot exceed Low regardless of other scores.

## Artifact template

```markdown
# Idea validation: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

> ⚠️ Idea-stage analysis from secondary sources only. This skill picks *which wedge looks strongest on paper* — it does not validate that real customers will buy. Real signal comes from `dudu:customer-discovery`. Deep competitor combat analysis comes from `dudu:competitive-landscape`.

## Problem statement

> [One sentence the VC/founder gave us]

## Market map (summary)

Full map: `market-map.md`.

- **Category boundary:** [one line]
- **Category verdict:** Empty / Forming / Contested / Saturated
- **Direct competitors counted:** N (top 3: ..., ..., ...)
- **Pricing range observed:** $X–$Y (model: freemium / seat / usage / services)
- **Funding signal (last 18mo):** [one line — e.g., "4 Seed/A rounds totaling $X in this category" or "no funding activity found"]
- **Structural shift:** [one line, or "none identified"]
- **Implication for wedge selection:** [one sentence — e.g., "Saturated at enterprise, open at SMB" / "Empty category — burden of proof on demand evidence"]

## Candidates

| # | Segment | Buyer role | Buying trigger | Differs from others on |
|---|---------|------------|----------------|------------------------|
| 1 | ... | ... | ... | ... |
| 2 | ... | ... | ... | ... |
| 3 | ... | ... | ... | ... |

Full profiles: `candidates/candidate-1.md`, `candidates/candidate-2.md`, `candidates/candidate-3.md`.

## Comparison matrix

| Dimension | Candidate 1 | Candidate 2 | Candidate 3 |
|-----------|-------------|-------------|-------------|
| Pain severity | <1–5 or ?> — <evidence> | ... | ... |
| Pain frequency | ... | ... | ... |
| WTP proxy | ... | ... | ... |
| Reachability | ... | ... | ... |
| Category proof | <same value for all candidates — from market map> | <same> | <same> |
| Competitive room for this candidate | ... | ... | ... |
| Segment size | ... | ... | ... |
| **Composite** | <sum / mean, with `?` count> | ... | ... |

## Competitor overlap by candidate

| Direct competitor | Targets candidate 1? | Targets candidate 2? | Targets candidate 3? | Evidence |
|-------------------|----------------------|----------------------|----------------------|----------|
| ... | yes/no/partial | ... | ... | [link] |

[Use this to make the "Competitive room" scores defensible. A candidate with no competitor overlap rows is either greenfield or invisible — the narrative should say which.]

## Where candidates diverge

[2–4 dimensions where the candidates produced meaningfully different scores. These are the decision-driving dimensions — call them out.]

## Where candidates agree

[Any dimension where all candidates scored similarly. Often this means the dimension isn't decision-relevant for *this* idea; useful to retire from further analysis.]

## Strongest evidence per candidate

### Candidate 1
- [Verbatim quote or stat] — [link]
- [Verbatim quote or stat] — [link]
- [Verbatim quote or stat] — [link]

### Candidate 2
[same shape]

### Candidate 3
[same shape]

## Wedge recommendation

- **Verdict:** Lead candidate identified / Tie / No viable wedge yet
- **Lead (if any):** Candidate <K>
- **Confidence:** Low / Medium / High
- **Why:** [3 sentences anchored on the rubric]
- **What would change my mind:** [2–3 specific things that, if discovered, would flip the recommendation]
- **Recommended next step:** [Run `dudu:market-problem` against Candidate <K> / Run `dudu:competitive-landscape` for the lead candidate's slice / Run `dudu:customer-discovery prep` for Candidate <K> / Pivot the idea — see open questions]

## Open questions

[5–10 questions the next research step needs to answer. Each rooted in a `?` cell, a divergence call-out, or a gap in the market map — not generic.]

## Sources

- [Title](url) — which layer (market map / candidate K) and which dimension(s) it informed
- ...
```

## After writing

1. Update `deals/<slug>/manifest.json` `skills_completed["idea-validation"]` to the current ISO-8601 UTC timestamp. Add the key if it doesn't exist; this skill is optional and not part of the six required by the `dudu:diligence` orchestrator.
2. Print the path to the artifact and the path to `market-map.md`.
3. If a lead candidate was identified, print a one-line suggestion: `Next: dudu:market-problem (ICP = Candidate <K>)`.

## Handoff to other skills

Two artifacts are designed to feed downstream skills:

- `market-map.md` — the category landscape. Hand it to `dudu:competitive-landscape` as starting context so it doesn't re-discover the same competitors; that skill goes deeper on the chosen company's combat position.
- `candidates/candidate-<K>.md` — the lead candidate profile. Structured to be pasted directly as the ICP input for downstream skills:
  - `dudu:market-problem` — when prompted for ICP, supply the lead candidate; pass `market-map.md` as additional context to skip re-research of the category.
  - `dudu:market-sizing` — the lead candidate's segment + buyer role + buying trigger are exactly the wedge-ICP shape that skill expects.
  - `dudu:customer-discovery prep` — the lead candidate's segment characteristics seed the target list when persona profiles don't yet exist.
