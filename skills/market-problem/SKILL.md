---
name: market-problem
description: Three-phase market/product/problem analysis. Phase 1 builds a deep context bundle from web research. Phase 2 auto-generates personas and runs self-play interviews. Phase 3 synthesizes patterns and contradictions to surface questions for real customer discovery.
---

# Market / product / problem

Run a three-phase exploration of the problem space. Read `lib/research-protocol.md` and `lib/playwright-auth.md` first. Heavier budget than other skills: ~50 fetches in phase 1.

## What this skill IS and IS NOT

- IS: a rehearsal tool. Possibility-space exploration before real customer interviews.
- IS NOT: validation. Self-play does not produce signal — only patterns to test against reality. Real signal comes from `dudu:customer-discovery`.

State this distinction in your output every time. VCs misuse persona output if you don't.

## Inputs

Required:
- Deal slug
- Company name
- Product description
- Target ICP if known (else generate during persona phase)

Optional:
- Loop count (default 6)
- Persona count (default 3)
- Pitch deck text (helps phase 1)

## Pre-flight

Idempotency check. Artifact: `deals/<slug>/market-problem.md`. Personas live under `deals/<slug>/personas/`.

If it exists and `--force` was not passed, print "Artifact already exists at deals/<slug>/market-problem.md. Pass --force to overwrite." and stop.

## Phase 1: Deep context engineering

Goal: produce `deals/<slug>/personas/_context.md` — a structured snapshot of what's known about the problem space before constructing any persona.

Sources (cap at ~50 total):
1. The product's own home page and any public docs.
2. Adjacent products' marketing pages — what jobs do they claim to do?
3. Customer reviews on G2, Capterra, Trustpilot for adjacent products.
4. Reddit threads on the problem (search the relevant subreddits).
5. Hacker News threads — search for the product category and the pain point words.
6. Niche forum threads (industry-specific Slacks/Discords/forums when public).
7. Industry analyst reports if findable (often paywalled — note when blocked).
8. Podcast transcripts where relevant.

### Phase 1 parallelization (Layer 2 — per source category)

Phase 1 is the heaviest fetch load in any dudu skill (~50 fetches). Source categories are independent. Dispatch **one `general-purpose` subagent per source category in a single message**, then synthesize. See `lib/research-protocol.md` § Parallelization.

Group the 8 sources into 4 subagent batches to keep dispatch tractable:

- **Subagent A — Product & adjacent marketing** (sources 1, 2): ~8 fetches.
- **Subagent B — Reviews** (source 3, G2/Capterra/Trustpilot): ~12 fetches.
- **Subagent C — Community sentiment** (sources 4, 5, 6, Reddit/HN/niche forums): ~18 fetches.
- **Subagent D — Analyst & podcast** (sources 7, 8): ~12 fetches.

Each subagent prompt MUST include:

- The deal's product description, the rough product category, and the pain-point keywords to search.
- The fetch cap for that batch.
- The citation and source-honesty rules from `lib/research-protocol.md` (paste, don't reference).
- Required return shape: bullet findings under the same five `_context.md` headings (What is the problem, Who has it, How are they solving it today, What's contested, What we couldn't find), plus a `Sources` list. Verbatim quotes only when source rules require them.

In the **main session** after all four subagents return: cross-reference, dedupe sources, surface contradictions across subagent reports under "What's contested," then write `personas/_context.md`.

Write `personas/_context.md` with these sections:

```markdown
# Problem-space context bundle

**Generated:** <ISO timestamp>

## What is the problem?

[3-4 sentences synthesized across sources, with citations]

## Who has it?

[The market segments where this pain shows up, with evidence]

## How are they solving it today?

[The current workarounds and competing products. Cite reviews.]

## What's contested?

[Disagreements across sources — e.g. one camp says this matters, another says it doesn't]

## What we couldn't find

[Be honest. "No public data on willingness-to-pay for this category."]

## Sources

- ...
```

## Phase 2: Persona generation + self-play

1. Using `_context.md` only (not your prior knowledge), generate N personas (default 3). Save each to `personas/persona-K.md`:

```markdown
# Persona <K>: <short label>

**Role:** <job title>
**Demographics:** <relevant context>
**Current workflow:** <how they handle this today>
**Pain intensity (1-10):** <number with justification>
**Willingness-to-pay anchor:** $<range> annually, justified by <reference>
**Voice / phrasing:** <how this person actually talks — sample phrases>
```

2. Distribute the loop count across the personas (e.g. 3 personas × 2 rounds each). Default: 6 rounds = 3 personas × 2 rounds each. Loop variable assignment goes in the artifact: persona-1 gets rounds 1 and 2, persona-2 gets rounds 3 and 4, persona-3 gets rounds 5 and 6.

3. For each round R, write `personas/round-R.md`:

```markdown
# Round <R> — Persona <K>

**Generated:** <ISO timestamp>

## Conversation

**Interviewer:** Tell me about this problem in your day-to-day.
**Persona <K>:** [in-character response, drawing only on persona profile + context bundle]

**Interviewer:** [Mom-Test follow-up rooted in the persona's last response]
**Persona <K>:** [in-character response]

[continue for ~6-10 exchanges; cover: current workflow, pain triggers, prior solution attempts, willingness to pay, what would make them switch]

## Round notes

- What surprised the interviewer
- What contradicted the persona profile (the persona "discovered" something)
- What questions came up that aren't answerable from context
```

The interviewer asks Mom-Test-style questions (about current behavior, never about hypothetical future behavior or vague preferences). The persona stays grounded in the persona profile and `_context.md`; if either is silent on a topic, the persona says so rather than fabricating.

### Phase 2 parallelization (per persona)

Self-play rounds for different personas are independent. Dispatch **one `general-purpose` subagent per persona in a single message**, where each subagent runs all of that persona's assigned rounds. The subagent prompt must include the full `_context.md` text, the `persona-K.md` profile, the round numbers it owns, and the round template above. Subagents return round-file contents as text; the main session writes `personas/round-R.md` files.

## Phase 3: Cross-round analysis

After all rounds complete, write `deals/<slug>/market-problem.md`:

```markdown
# Market / product / problem: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

> ⚠️ This analysis is based on simulated personas. It is for rehearsal and possibility-space exploration only. Real signal requires running `dudu:customer-discovery` with real people.

## Patterns across rounds

[3-6 things multiple personas agreed on, with round citations: round-1.md, round-3.md, etc.]

## Contradictions across rounds

[2-4 places personas disagreed — these are the most valuable surfaces]

## Strongest pain signals

[Rank-ordered list of pains by intensity × frequency across rounds]

## Weakest assumptions

[2-4 places where the persona felt thin / had to fabricate / where context was missing]

## Questions to bring to real customer interviews

[5-10 specific questions, each rooted in a contradiction or weak assumption. Format: "Q: ... — root: ..."]

## Source artifacts

- personas/_context.md
- personas/persona-1.md
- ...
- personas/round-1.md
- ...
```

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["market-problem"]`.
