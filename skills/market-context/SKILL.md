---
name: market-context
description: Two-phase public-source market context. Phase 1 builds a context bundle from web research; Phase 2 synthesizes patterns and contradictions into open questions for customer discovery. No personas (dudu:pmf-signal owns them).
---

# Market / problem context

Run a public-source exploration of the problem space. Read `lib/research-protocol.md` and `lib/playwright-auth.md` first. Heavier fetch budget than other L1 skills: ~50 fetches in phase 1.

## What this skill IS and IS NOT

- IS: a context-building skill. Possibility-space research and synthesis from public sources.
- IS NOT: validation. Public reading does not produce signal — only patterns to test against reality. Real signal comes from real customer interviews; the calibrated prior comes from `dudu:pmf-signal`'s persona simulation.
- IS NOT: a persona generator. The deprecated `dudu:market-problem` skill ran a Phase 2 of self-play interviews; that is gone. Personas live in `dudu:pmf-signal`. This skill never writes under `deals/<slug>/personas/`.

State the public-reading-vs-real-signal distinction in your output every time. VCs misread context-bundle findings if you don't.

## Inputs

Required:
- Deal slug
- Company name
- Product description
- Target ICP if known (else surface as an open question)

Optional:
- Pitch deck text (helps phase 1 source seeding)

## Pre-flight

Idempotency check. Artifact: `deals/<slug>/market-context.md`.

If it exists and `--force` was not passed, print `Artifact already exists at deals/<slug>/market-context.md. Pass --force to overwrite.` and stop.

This skill never writes under `deals/<slug>/personas/`. If a legacy `personas/_context.md` exists from the deprecated `market-problem` skill, leave it on disk untouched — it is read-only context for `dudu:pmf-signal` if it later runs.

## Phase 1: Deep context engineering

Goal: produce `deals/<slug>/market-context.md`'s **Context bundle** section — a structured snapshot of what's known about the problem space from public sources.

Sources (cap at ~50 total):
1. The product's own home page and any public docs.
2. Adjacent products' marketing pages — what jobs do they claim to do?
3. Customer reviews on G2, Capterra, Trustpilot for adjacent products.
4. Reddit threads on the problem (search the relevant subreddits).
5. Hacker News threads — search for the product category and the pain point words.
6. Niche forum threads (industry-specific Slacks/Discords/forums when public).
7. Industry analyst reports if findable (often paywalled — note when blocked).
8. Podcast transcripts where relevant.

### Phase 1 parallelization (per source category)

Phase 1 is the heaviest fetch load in any dudu skill (~50 fetches). Source categories are independent. Dispatch **one worker subagent per source category**, all concurrently in a single turn, then synthesize. See `lib/research-protocol.md` § Parallelization for the cross-platform mapping (Claude Code: `Agent` with `subagent_type="general-purpose"`; Codex: `spawn_agent` with `agent_type="worker"` and `multi_agent = true` in config).

Group the 8 sources into 4 subagent batches to keep dispatch tractable:

- **Subagent A — Product & adjacent marketing** (sources 1, 2): ~8 fetches.
- **Subagent B — Reviews** (source 3, G2/Capterra/Trustpilot): ~12 fetches.
- **Subagent C — Community sentiment** (sources 4, 5, 6, Reddit/HN/niche forums): ~18 fetches.
- **Subagent D — Analyst & podcast** (sources 7, 8): ~12 fetches.

Each subagent prompt MUST include:

- The deal's product description, the rough product category, and the pain-point keywords to search.
- The fetch cap for that batch.
- The citation and source-honesty rules from `lib/research-protocol.md` (paste, don't reference).
- Required return shape: bullet findings under the same five context headings (What is the problem, Who has it, How are they solving it today, What's contested, What we couldn't find), plus a `Sources` list. Verbatim quotes only when source rules require them.

In the **main session** after all four subagents return: cross-reference, dedupe sources, surface contradictions across subagent reports under "What's contested," then proceed to Phase 2 synthesis.

## Phase 2: Cross-source synthesis

After Phase 1 finishes, write `deals/<slug>/market-context.md`:

```markdown
# Market / problem context: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

> Public-reading context only. This is rehearsal material — possibility-space exploration, not signal. The falsifiable PMF prior comes from `dudu:pmf-signal`. Real signal requires running `dudu:customer-debrief` against real interview transcripts.

## Context bundle

### What is the problem?

[3-4 sentences synthesized across sources, with citations]

### Who has it?

[The market segments where this pain shows up, with evidence]

### How are they solving it today?

[The current workarounds and competing products. Cite reviews.]

### What's contested?

[Disagreements across sources — e.g. one camp says this matters, another says it doesn't]

### What we couldn't find

[Be honest. "No public data on willingness-to-pay for this category."]

## Patterns from public sources

[3-6 things that came up in multiple independent sources, with source citations]

## Contradictions to investigate

[2-4 places sources disagreed — these are the most valuable surfaces for L2 persona simulation and real interviews]

## Open questions for L2 + real interviews

[5-10 specific questions, each rooted in a contradiction or weak-coverage area. Format: "Q: ... — root: ..."]

## Sources

- ...
```

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["market-context"]`.

## Migration from market-problem

The legacy `market-problem` skill produced personas under `deals/<slug>/personas/` as Phase 2 self-play. That phase is gone. If a deal directory contains legacy `personas/_context.md` and `personas/persona-*.md` files, leave them on disk — they are read-only inputs for `dudu:pmf-signal`. If a deal directory has no such files, `dudu:pmf-signal` will create the persona namespace from scratch when it runs.

The old `dudu:market-problem` invocation forwards to `dudu:market-context` for one release window before being removed.
