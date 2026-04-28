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
