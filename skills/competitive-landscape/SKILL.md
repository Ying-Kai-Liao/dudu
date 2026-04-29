---
name: competitive-landscape
description: Map direct and indirect competitors, assess incumbent threat, and analyze moat durability. Produces a competitor matrix with citations.
---

# Competitive landscape

Map every direct and indirect competitor for the deal. Read `lib/research-protocol.md` and `lib/playwright-auth.md` before starting. Cap at ~5 fetches per competitor and ~30 competitors.

## Inputs

Required (prompt if missing):
- Deal slug
- Company name
- One-line product description
- Target customer (ICP) if known

## Pre-flight

Same idempotency check as other skills (read `lib/deal.md`). Artifact path: `deals/<slug>/competitive-landscape.md`. If it exists and `--force` was not passed, print "Artifact already exists at deals/<slug>/competitive-landscape.md. Pass --force to overwrite." and stop.

## Sources

1. **Product Hunt** — search the product category. Pull launch posts, traction signals, comments.
2. **Crunchbase** — Playwright with VC session. Funding history, headcount, last raise.
3. **GitHub** — search the category for open-source competitors. Star counts, commit cadence (active vs abandoned).
4. **Public job boards** — search incumbents for roles in this product area. Hiring signals indicate seriousness.
5. **Google Patents** — search the core technique or product noun. Filed-and-granted vs filed-and-abandoned matters.
6. **News and tech press** — search the category for the last 18 months.

## Parallelization (Layer 2 — per competitor)

Competitor research splits cleanly per competitor. Run this skill in two stages:

**Stage A — discovery (main session, ~10 fetches).** Identify the candidate competitor list via batched parallel `WebFetch` (Layer 1) across Product Hunt, GitHub category search, and news/tech-press for the category. Output: a list of up to ~30 competitors with names + one-line positioning each.

**Stage B — per-competitor deep dive (fan out).** For the discovered list, dispatch **one `general-purpose` subagent per competitor in a single message**. See `lib/research-protocol.md` § Parallelization.

Each subagent prompt MUST include:

- Competitor name, one-line positioning, and the deal's product description (so the subagent can judge direct vs indirect).
- A **per-competitor budget of ~4 public-web fetches** (reserve ~1 for main-session Crunchbase work).
- The citation and source-honesty rules from `lib/research-protocol.md` (paste, don't reference).
- Sources to consult: items **1, 3, 4, 5, 6** above. **Skip item 2 (Crunchbase)** — Playwright with VC session is main-session only.
- Required return shape: a single row each for the Direct-competitors table and (if applicable) the Indirect-competitors table from the artifact, plus any moat-relevant evidence quotes with sources, plus an `Activity verdict` (Active / Abandoned / Unknown) with last-commit or last-news date.

For incumbents specifically, the subagent additionally returns: shipping evidence link, hiring-signal count + link, public-statement quotes with sources.

After all subagents return, in the **main session**:

1. For each competitor that warrants it, do Crunchbase Playwright lookups (item 2) to fill funding/headcount/last-raise.
2. Merge subagent summaries + Crunchbase data into the artifact tables and the moat analysis.

If the discovered competitor list has fewer than 3 entries, skip fan-out and use Layer 1 inline.

## Artifact template

```markdown
# Competitive landscape: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## Direct competitors

| Competitor | Positioning | Traction | Last funding | Moat type | Last activity | Source |
|------------|-------------|----------|--------------|-----------|---------------|--------|
| ... | ... | ... | ... | ... | ... | [link] |

## Indirect competitors

| Competitor | Why indirect | Risk it becomes direct | Source |
|------------|--------------|------------------------|--------|
| ... | ... | ... | [link] |

## Incumbent threat assessment

For each incumbent who could plausibly crush a startup in this space:

### <Incumbent name>

- **Currently shipping in this area?** Yes / No / Building. Evidence: [link]
- **Hiring signal?** [count of job postings tagged with the relevant keywords, with link]
- **Public statements?** [quotes from earnings calls, blog posts, conference talks, with sources]
- **Verdict:** Sleeping / Watching / Building / Already shipping.

## Moat analysis

For each candidate moat type, with evidence:

- **Network effects:** [analysis with evidence, or "Not applicable"]
- **Proprietary data:** [analysis with evidence, or "Not applicable"]
- **Switching costs:** [analysis with evidence, or "Not applicable"]
- **Brand:** [analysis with evidence, or "Not applicable"]

## Sources

- ...

## Open questions

- ...
```

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["competitive-landscape"]` to the current ISO-8601 UTC timestamp.
