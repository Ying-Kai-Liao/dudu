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

Sequential web fetching is the slow path. Default to parallel. Two layers:

### Layer 1 — Batch independent fetches together

Whenever you have N URLs and none of them depends on another's result (e.g., reading 5 search-result pages for the same founder, fetching 6 review sites for adjacent products), issue all the fetch calls **together in one turn** rather than one-by-one. Sequential fetches are only justified when the next URL is chosen based on the previous fetch's content.

Host behaviour varies — Claude Code runs concurrent tool calls in one message in parallel; some other hosts may serialize them. **If your host serializes tool calls within a turn, treat Layer 1 as best-effort and rely on Layer 2 for guaranteed parallelism.**

### Layer 2 — Fan out to subagents when the work has N independent units

When a skill's research naturally splits into N independent units (one per founder, one per competitor, one per candidate persona, one per outreach channel, one per source category), dispatch **one worker subagent per unit, all in a single turn** so they run concurrently. Each subagent:

- Gets a self-contained prompt: the unit's identity, the per-unit fetch budget, the citation and source-honesty rules from this protocol (paste them, don't reference — subagents don't auto-load this file), and the exact output shape it must return.
- Does its own batched parallel fetches (Layer 1) inside its context.
- Returns a compact summary in the schema the caller asked for — not raw page contents.

This keeps the main session context clean for synthesis while N units of research happen at once. **This is the layer that delivers reliable parallelism across hosts.**

### Cross-platform tool mapping

The "dispatch a worker subagent" instruction above maps to different primitives per host. Pick the row for your host:

| Host | Tool to dispatch a subagent | Required setup | Message framing |
|------|------------------------------|----------------|-----------------|
| **Claude Code** | `Agent` tool with `subagent_type="general-purpose"` | None | Plain prompt; multiple `Agent` calls in one assistant message run in parallel. |
| **Codex (OpenAI)** | `spawn_agent` with `agent_type="worker"`, then `wait` for results | `multi_agent = true` in `~/.codex/config.toml` under `[features]`. Confirm with `cat ~/.codex/config.toml \| grep multi_agent`. | Wrap instructions in XML tags and use task-delegation framing — see template below. Issue all `spawn_agent` calls in one turn, then `wait` for them. |
| **Other LLM CLIs** | The host's parallel-agent dispatch primitive | Whatever the host requires | Match the host's expected message framing. |

**Codex message framing template** (per the superpowers `codex-tools.md` reference):

```
Your task is to perform the following. Follow the instructions below exactly.

<agent-instructions>
[unit identity, per-unit fetch budget, citation rules from this protocol pasted in,
required return shape]
</agent-instructions>

Execute this now. Output ONLY the structured response following the format specified
in the instructions above.
```

If you do not know whether the host supports multi-agent dispatch, ask the user before falling back to sequential per-unit work — sequential is the slow path the user is actively trying to avoid.

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
