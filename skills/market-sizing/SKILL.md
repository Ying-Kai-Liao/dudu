---
name: market-sizing
description: Build a bottom-up TAM model from scratch, anchored on a clearly defined ICP and a transparent reachable-population calculation. Does not anchor on the founder's number.
---

# Market sizing

Produce a defensible bottom-up TAM. Read `lib/research-protocol.md` and `lib/playwright-auth.md` first. Cap at ~30 fetches.

## Critical rule

You MUST NOT anchor on any TAM number the founder claimed. Build from zero. Compare to the founder's number only at the end, in a labeled section.

## Inputs

Required:
- Deal slug
- Company name
- Product description
- Target ICP — if missing, read `deals/<slug>/personas/persona-*.md` if available, otherwise prompt the VC.

## Pre-flight

Idempotency check (per `lib/deal.md`). Artifact: `deals/<slug>/market-sizing.md`. If it exists and `--force` was not passed, print "Artifact already exists at deals/<slug>/market-sizing.md. Pass --force to overwrite." and stop.

## Method

This skill does **not** fan out to subagents — its sources are tightly coupled (population, ACV, expansion all reference the same wedge) and several require Playwright. Instead, follow Layer 1 from `lib/research-protocol.md` § Parallelization: when reading multiple population sources, multiple ACV references, or multiple expansion-segment sources, batch those `WebFetch` calls in a single message. Sequential fetches are only justified when the next URL is chosen based on the previous fetch's content.

1. **Define the wedge.** Write a one-sentence ICP that names a job title, a company size band, and a buying trigger.
2. **Count the reachable population.** Use public data:
   - Industry directories (e.g. SIC/NAICS counts, association memberships)
   - Government statistics (BLS, Eurostat, equivalent)
   - LinkedIn-style search counts via Playwright if needed
   - Cite every number.
3. **Anchor the ACV.** Find 3 reference points:
   - What do incumbents in this space charge?
   - What does a comparable adjacent product cost?
   - What did your customer-discovery work (if available) suggest WTP was?
   Pick a range, not a point estimate.
4. **Compute the wedge TAM.** `reachable population × ACV range`. Show your work.
5. **Identify expansion adjacent.** Name 1-3 named adjacent segments the company could expand into. For each, repeat steps 2-4.
6. **Compare to founder claim.** Only now, side-by-side.

## Artifact template

```markdown
# Market sizing: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## Wedge ICP

> [One-sentence ICP definition]

## Reachable population

| Segment | Count | Source |
|---------|-------|--------|
| ... | ... | [link] |

**Total reachable:** [number with range]

## ACV anchors

| Reference | Annual price | Source |
|-----------|--------------|--------|
| ... | ... | [link] |

**Defensible ACV range:** $X–$Y

## Wedge TAM math

```
reachable population × annual ACV range
= <low_count> × $<low_acv> = $<low_tam>
to
  <high_count> × $<high_acv> = $<high_tam>
```

**Wedge TAM:** $<low_tam>–$<high_tam>

## Expansion segments

### <Segment 1>

- Reachable: ... (source)
- ACV: $... (source)
- TAM: $...

### <Segment 2>

[same shape]

## Total addressable (wedge + expansion)

$<low_total>–$<high_total>

## Founder claim comparison

| Source | Number | Method |
|--------|--------|--------|
| Founder | $<founder_tam> | <if disclosed> |
| Bottom-up (this artifact) | $<our_tam> | Bottom-up |
| Delta | <ratio or absolute> | |

## Verdict on wedge

- **Clearly defined?** Yes / No / Partial — explain.
- **Reachable?** Yes / No / Partial — explain. (Specifically: can a small startup actually find and contact this population?)
- **Credible expansion path?** Yes / No / Partial — explain.

## Sources

## Open questions
```

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["market-sizing"]` to the current ISO-8601 UTC timestamp.
