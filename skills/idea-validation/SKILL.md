---
name: idea-validation
description: Idea-stage wedge selection. Compares 2–5 candidate user personas / market segments side-by-side on pain, willingness-to-pay, reachability, competition, and segment size to recommend a wedge — or flag that no segment yet justifies building. Pre-product, secondary-research only.
---

# Idea validation

Compare multiple candidate ICPs for a pre-product idea and pick the strongest wedge. Read `lib/research-protocol.md` and `lib/playwright-auth.md` first. Cap at ~10 fetches per candidate persona, ~50 fetches total.

## What this skill IS and IS NOT

- IS: a head-to-head comparison of 2–5 candidate personas/segments at idea stage, using only secondary signal (reviews, forums, adjacent product pricing, public population data). Output is a wedge recommendation with explicit confidence.
- IS NOT: validation through real customers (that's `dudu:customer-discovery`). IS NOT a deep one-wedge rehearsal (that's `dudu:market-problem`). IS NOT a defensible TAM (that's `dudu:market-sizing`).

State this distinction in the artifact every time. The point of this skill is *which wedge*, not *is there real demand* — only real interviews settle that.

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

Idempotency check. Artifact: `deals/<slug>/idea-validation.md`. Candidate profiles live under `deals/<slug>/candidates/`.

If `deals/<slug>/idea-validation.md` exists and `--force` was not passed, print "Artifact already exists at deals/<slug>/idea-validation.md. Pass --force to overwrite." and stop.

## Method

### Step 1 — Generate or accept candidates

If candidates were supplied, write each to `deals/<slug>/candidates/candidate-K.md` using the profile template below. If not supplied, generate 3 candidates that span meaningfully different axes — e.g., different company size, different job-to-be-done, different industry — not three flavors of the same buyer.

Candidate profile template (`candidates/candidate-K.md`):

```markdown
# Candidate <K>: <short label>

**Segment:** <industry / company size / role band>
**Buyer role:** <job title that signs the contract>
**User role:** <job title that uses the product daily — may be the same>
**Buying trigger:** <the moment that makes them shop>
**Why this candidate is plausible:** <one sentence>
**How this differs from the other candidates:** <one sentence — must be a real difference, not a synonym>
```

Hard rule: each candidate must differ from the others on at least one of {industry, company-size band, buyer role, buying trigger}. If two candidates collapse onto the same axis, merge them.

### Step 2 — Research each candidate (parallel)

For each candidate, spend up to ~10 fetches across:

1. **Adjacent-product reviews** — G2, Capterra, Trustpilot. Search for products this segment already buys; pull pain quotes and pricing.
2. **Reddit / HN / niche forums** — search the segment's actual phrasing of the pain. Quote complaints verbatim.
3. **Adjacent product pricing pages** — capture concrete ACV anchors (annual price, seat price, tier).
4. **Population sources** — LinkedIn search counts via Playwright, BLS/Eurostat, industry-association membership counts. One credible number is enough at this stage.
5. **Competitive density** — Product Hunt search of the category, GitHub if open-source, count of funded startups via Crunchbase.

Apply `lib/research-protocol.md` citation rules. If a dimension can't be sourced for a candidate, write **"Not found in public sources"** — never invent.

### Step 3 — Score each candidate on the rubric

Score every candidate on the same six dimensions, 1–5, with a one-line evidence-anchored rationale per score. Refuse to score without a citation; mark as `?` if the evidence is missing and explain in the rationale.

| Dimension | What scores high (5) | What scores low (1) |
|-----------|----------------------|---------------------|
| **Pain severity** | Multiple verbatim complaints calling it urgent/critical/blocker | Pain only inferred from product marketing |
| **Pain frequency** | Daily/weekly recurring | Annual or one-off |
| **WTP proxy** | Segment already pays >$X for adjacent tools; explicit price quotes | No comparable spending pattern; free tools dominate |
| **Reachability** | Public lists, identifiable channels, named communities | Diffuse, no clear way to find or contact 100 of them |
| **Competition density** | Crowded enough to prove demand, not so crowded that a new entrant has no room | Empty (no proof of demand) OR saturated (no room) |
| **Segment size** | Reachable population large enough that a wedge of it sustains a startup | Too small to support a venture outcome |

Notes on the rubric:
- "Competition density" is non-monotonic — both empty and saturated score low. Flag which side a low score lands on.
- A `?` (insufficient evidence) is more honest than a guessed score. Multiple `?`s on the same candidate is itself a finding: "we can't tell yet."

### Step 4 — Cross-candidate comparison

Build the head-to-head matrix. Then write the comparison narrative: where do candidates agree, where do they diverge, and which dimensions carried the most weight?

### Step 5 — Wedge recommendation

Pick one of:
- **Lead candidate identified** — name it, justify in 3 sentences referencing the rubric, list the 3 strongest evidence quotes from that candidate's research, and state confidence (Low / Medium / High).
- **Tie / too close to call** — name the top 2, explain what evidence would break the tie, and propose the next research step.
- **No viable wedge yet** — state the binding constraint (e.g., "no candidate showed WTP signal above $X") and what the founder would need to discover to make this idea pursuable.

Confidence floor: if 3+ dimensions are `?` for the lead candidate, confidence cannot exceed Low. Say so.

## Artifact template

```markdown
# Idea validation: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

> ⚠️ Idea-stage analysis from secondary sources only. This skill picks *which wedge looks strongest on paper* — it does not validate that real customers will buy. Real signal comes from `dudu:customer-discovery`.

## Problem statement

> [One sentence the VC/founder gave us]

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
| Competition density | ... | ... | ... |
| Segment size | ... | ... | ... |
| **Composite** | <sum / mean, with `?` count> | ... | ... |

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
- **Recommended next step:** [Run `dudu:market-problem` against Candidate <K> / Run `dudu:customer-discovery prep` for Candidate <K> / Pivot the idea — see open questions]

## Open questions

[5–10 questions the next research step needs to answer. Each rooted in a `?` cell or a divergence call-out, not generic.]

## Sources

- [Title](url) — which candidate(s) and which dimension(s) it informed
- ...
```

## After writing

1. Update `deals/<slug>/manifest.json` `skills_completed["idea-validation"]` to the current ISO-8601 UTC timestamp. Add the key if it doesn't exist; this skill is optional and not part of the six required by the `dudu:diligence` orchestrator.
2. Print the path to the artifact.
3. If a lead candidate was identified, print a one-line suggestion: `Next: dudu:market-problem (ICP = Candidate <K>)`.

## Handoff to other skills

The lead candidate profile (`candidates/candidate-<K>.md`) is structured to be pasted directly as the ICP input for downstream skills:

- `dudu:market-problem` — when prompted for ICP, supply the lead candidate.
- `dudu:market-sizing` — same; the lead candidate's segment + buyer role + buying trigger are exactly the wedge-ICP shape that skill expects.
- `dudu:customer-discovery prep` — the lead candidate's segment characteristics seed the target list when persona profiles don't yet exist.
