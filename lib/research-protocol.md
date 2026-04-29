# Research protocol

Every dudu skill that gathers information follows these rules. They are non-negotiable: VCs make money decisions on what these artifacts say, and a fabricated claim is worse than no claim.

## Citation format

Every factual claim has a source. Two formats:

- **Public web** — inline link: `[Acme raised $4M Seed in 2024](https://techcrunch.com/...)`
- **VC-supplied** — parenthetical: `Founder claims TAM is $20B (VC-supplied: deck slide 14)`
- **Authenticated browser session** — domain plus public equivalent if one exists: `Headcount: 47 employees (linkedin.com, authenticated session; public equivalent: https://www.crunchbase.com/...)`

## Source honesty

- If a fact cannot be sourced, write **"Not found in public sources."** Never invent.
- If two sources contradict, surface both with citations and label the contradiction. Do not silently pick a winner.
- Estimates are explicit: `~50–200 (range; no precise public source)` — never a single fabricated number.
- Never paraphrase a quote into something the source did not say. If quoting, reproduce verbatim.

## Search budgeting

Deep research is token-heavy. Each skill declares a per-run budget in its body. Default budgets:

- founder-check: ~30 fetches per founder
- market-problem phase 1: ~50 fetches total
- competitive-landscape: ~5 fetches per competitor, ~30 competitors max
- market-sizing: ~30 fetches total
- customer-discovery prep: ~20 fetches total

If a skill hits its budget, it stops, writes what it has, and notes the truncation in the artifact.

## Parallelization

Sequential `WebFetch` is the slow path. Default to parallel. Two layers:

### Layer 1 — Batch independent fetches in a single message

Whenever you have N URLs and none of them depends on another's result (e.g., reading 5 search-result pages for the same founder, fetching 6 review sites for adjacent products), issue all the `WebFetch` calls in **one** message. The tool runs them concurrently. Sequential fetches are only justified when the next URL is chosen based on the previous fetch's content.

This applies inside the main session and inside any subagent.

### Layer 2 — Fan out to subagents when the work has N independent units

When a skill's research naturally splits into N independent units (one per founder, one per competitor, one per candidate persona, one per outreach channel, one per source category), dispatch **one `general-purpose` subagent per unit, in a single message** so they run concurrently. Each subagent:

- Gets a self-contained prompt: the unit's identity, the per-unit fetch budget, the citation and source-honesty rules from this protocol, and the exact output shape it must return.
- Does its own batched parallel `WebFetch` (Layer 1) inside its context.
- Returns a compact summary in the schema the caller asked for — not raw page contents.

This keeps the main session context clean for synthesis while N units of research happen at once.

### What NOT to delegate to subagents

- **Authenticated Playwright sessions** (LinkedIn, Crunchbase, etc., per `lib/playwright-auth.md`) — auth state lives in the main session. Do these in main, then optionally hand the result to a subagent for further public-web follow-up.
- **VC-facing prompts and confirmations** (e.g., the founder-discovery confirmation step in `founder-check`, dispatch decisions in `customer-discovery`) — only the main session talks to the user.
- **Final artifact writes** — synthesize and write artifacts in the main session using subagent summaries as inputs. Never have a subagent write into `deals/<slug>/`.

### Budget accounting under fan-out

The budgets above are total per skill run, not per subagent. Divide explicitly in each dispatch prompt: e.g., `competitive-landscape` with 12 competitors → 12 subagents × ~5 fetches each = ~60 total. State the per-unit cap in the prompt so each subagent self-limits.

### When NOT to fan out

- Fewer than 2 independent units (a single founder, a single candidate) — overhead isn't worth it; just use Layer 1.
- Local file synthesis (e.g., `customer-discovery debrief` reading transcripts) — no fetches, no fan-out.
- Pure orchestrator skills like `dudu:diligence` — they parallelize at the *sub-skill* level if at all, not the fetch level, and only when the sub-skills are truly independent.

## Ordering of sources

Prefer in roughly this order:
1. Primary sources (filings, patents, the company's own blog, founder's own writing)
2. Reputable secondary (industry analysts, established trade press)
3. Aggregators (Crunchbase, Product Hunt)
4. User-generated (Reddit, HN, forums) — useful for sentiment, weak for facts
5. AI-summarized content — never as a primary source

## Output structure

Every research artifact ends with two sections:

```markdown
## Sources

- [Title](url) — brief description
- [Title](url) — brief description

## Open questions

- Question the next step in due diligence should answer
- Question the next step in due diligence should answer
```
