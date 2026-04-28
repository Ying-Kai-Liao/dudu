# dudu — VC Due Diligence Plugin for Claude Code

**Status:** Approved design
**Date:** 2026-04-28
**Owner:** Ying-Kai Liao
**Type:** Claude Code plugin (skills only)

## Goal

Build a Claude Code plugin that helps a VC do early-stage due diligence on a deal. The plugin packages five focused skills plus an orchestrator, each producing a citation-backed markdown artifact under a per-deal directory. Skills combine deep web research (where public) with Playwright-driven access to login-walled sources using the VC's own authenticated browser session.

## Non-goals

- Founder reference checks via the VC's personal network (calendar/email task, not a skill task).
- Paid-API integrations (Crunchbase Pro, PitchBook) in v1.
- Auto-generated slide decks for investment committee.
- Multi-tenant deal sharing across a partnership — git/Drive handles sharing.
- Hybrid VC-in-the-loop persona interviewing — defer until self-play has shown its limits.

## Plugin layout

```
dudu/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/
│   ├── diligence/                    # orchestrator
│   ├── founder-check/
│   ├── market-problem/               # persona self-play
│   ├── customer-discovery/
│   ├── competitive-landscape/
│   └── market-sizing/
├── lib/
│   ├── deal.md                       # what is a deal directory, manifest schema
│   ├── playwright-auth.md            # log-in-once UX, session reuse, rate limiting
│   └── research-protocol.md          # citation rules, source honesty, "not found" handling
├── README.md
└── docs/superpowers/specs/
```

Plugin namespace is `dudu`. Skills are invoked via `/dudu:<name>` (e.g. `/dudu:diligence`, `/dudu:founder-check`). Each skill is a standard Claude Code skill: a Markdown file with YAML frontmatter (`name`, `description`) and a body that instructs the assistant.

## Skills

### `dudu:diligence` — orchestrator

**Trigger:** the VC starts a new deal.

**Inputs (prompted if missing):**
- Deal slug (kebab-case, becomes the directory name)
- Company name
- Founder names (one or more)
- One-line pitch
- Pitch deck (file path or pasted text), if available

**Behavior:**
1. Creates `deals/<slug>/` and writes `manifest.json` capturing inputs and timestamps.
2. Runs sub-skills in this order: `founder-check` → `market-problem` → `customer-discovery prep` → `competitive-landscape` → `market-sizing`. Then pauses and prompts the VC to actually go run the customer interviews and return for `customer-discovery debrief`. Debrief is the final step before stitching the memo.
3. After debrief, stitches every artifact into `deals/<slug>/MEMO.md` — a structured investment memo with sections corresponding to each skill's output, plus a synthesis section flagging contradictions across artifacts.
4. Idempotent: re-running skips steps whose artifacts exist unless `--force` is passed.

**Outputs:** `deals/<slug>/manifest.json`, `deals/<slug>/MEMO.md`.

### `dudu:founder-check`

**Trigger:** the VC wants a public-web dossier on each founder.

**Sources:**
- Open web: Google search, news, personal blogs, podcast appearances, conference talks
- GitHub (commit cadence, owned repos, contribution graph)
- Twitter/X (positions, network density, controversies)
- LinkedIn — via Playwright with the VC's authenticated browser session
- Crunchbase founder pages — via Playwright with the VC's authenticated browser session

**Output sections (per founder, in `deals/<slug>/founder-<name>.md`):**
- Career timeline (companies, roles, dates, outcomes)
- Domain credibility (what makes them credible to ship this product)
- Prior ventures: outcomes, scale reached, public exits or shutdowns
- Public controversies / litigation hits
- Communication style (sample of public writing/speaking)
- Network density (notable co-founders, advisors, employer alumni)
- Open questions a partner would ask after reading this

**Honesty rules:**
- Every claim has a citation (URL or "VC-supplied").
- Empty fields are explicit: "Not found in public sources." Never fabricated.

### `dudu:market-problem` — persona self-play

**Phase 1: Deep context engineering.** Heavy research before any persona exists.
- Web research on the problem space, target ICP, adjacent products, customer reviews on G2/Capterra/Trustpilot, Reddit/HN/forum threads, industry reports, podcast transcripts where relevant.
- Output: a structured context bundle written to `deals/<slug>/personas/_context.md` listing what was learned, what's contested, what's missing.

**Phase 2: Self-play.**
- Auto-generates 2–3 distinct personas grounded in the context bundle. Each persona profile is saved to `deals/<slug>/personas/persona-N.md` (role, demographics, current workflow, pain intensity, willingness-to-pay anchor).
- Runs a default of 6 simulated interviews (configurable), distributed across the personas (e.g. 3 personas × 2 rounds each). The agent plays both an interviewer (using Mom-Test-style questions) and the persona, in separate roles within the conversation. Each round is recorded to `deals/<slug>/personas/round-N.md`, with the persona ID noted at the top.

**Phase 3: Cross-round analysis.** Scans every round, surfaces:
- Patterns (consistent pains, consistent objections)
- Contradictions (where personas disagree — these are the most valuable surfaces)
- Open questions for real customer interviews

**Output:** `deals/<slug>/market-problem.md` (final synthesis), `deals/<slug>/personas/` (raw rounds + persona profiles + context bundle).

**Self-play caveat:** The skill explicitly states in its body that self-play surfaces possibility space, not signal. Real signal comes from `customer-discovery`. The skill is for rehearsal and idea pressure-testing, not validation.

### `dudu:customer-discovery`

Two sub-actions in one skill, dispatched by argument.

**`prep`:**
- Reads `personas/persona-N.md` if it exists; otherwise prompts the VC for the target ICP.
- Builds a target list: search LinkedIn (Playwright), Reddit (specific subreddits inferred from the persona), niche Slack/Discord communities, X. Outputs ~30 candidates with rationale.
- Drafts cold-outreach message templates (one per channel: LinkedIn DM, Reddit DM, X DM, email) and per-persona variants slotted in for the top candidates.
- Produces an interview script anchored on the four core questions:
  1. Tell me about this problem in your day-to-day.
  2. How are you solving it today?
  3. What would it be worth to you to solve this properly?
  4. Have you looked for solutions? Why didn't they work?
- Writes to `deals/<slug>/customer-discovery-prep.md`.

**`debrief`:**
- VC pastes in transcripts/notes from the interviews they actually ran.
- Cross-references quotes against the personas built earlier.
- Synthesizes pain intensity, willingness to pay, current solutions, common objections — quote-level evidence cited inline.
- Flags where reality contradicted persona assumptions (very valuable signal).
- Writes final `deals/<slug>/customer-discovery.md`.

### `dudu:competitive-landscape`

**Sources:**
- Product Hunt (launches, traction, comments)
- Crunchbase (Playwright with VC session — funding history, headcount)
- GitHub (open-source competitors, commit cadence, star counts)
- Public job boards / company careers pages (incumbent hiring signals — are they staffing this area up?)
- Google Patents
- News and tech press

**Output (`deals/<slug>/competitive-landscape.md`):**
- Competitor matrix: positioning, traction, funding, moat type, last activity. Direct and indirect competitors clearly separated.
- Incumbent-threat assessment: are the incumbents sleeping on this, or are they about to ship something that crushes a startup? Evidence-based, not vibes.
- Moat analysis: which of network effects / proprietary data / switching costs / brand applies, and how durable each is.

### `dudu:market-sizing`

**Approach:** bottom-up only. Does not anchor on the founder's TAM number.

**Steps:**
1. Define the initial wedge (the ICP from `market-problem` if available, else prompt).
2. Count the reachable population using public data sources (industry directories, government statistics, association membership lists, LinkedIn search counts where Playwright permits).
3. Apply a defensible ACV range with citations for each anchor point.
4. Write out the math transparently — every assumption labelled with its source.
5. Answer two questions explicitly:
   - Is the initial wedge clearly defined and reachable?
   - Is there a credible expansion story beyond the wedge, with named adjacent segments?

**Output:** `deals/<slug>/market-sizing.md` with a markdown calculator the VC can edit by hand to flex assumptions.

## Per-deal directory layout

```
deals/<slug>/
├── manifest.json              # deal metadata, sources, completion state
├── inputs/                    # deck, founder bios, anything VC supplies
├── founder-<name>.md          # one per founder
├── market-problem.md
├── personas/
│   ├── _context.md            # phase 1 context bundle
│   ├── persona-1.md
│   ├── persona-2.md
│   ├── persona-3.md
│   ├── round-1.md
│   ├── ...
│   └── round-6.md
├── competitive-landscape.md
├── market-sizing.md
├── customer-discovery-prep.md
├── customer-discovery.md
└── MEMO.md                    # stitched at end by orchestrator
```

`manifest.json` schema (illustrative):

```json
{
  "slug": "acme",
  "company": "Acme",
  "founders": ["Alice Founder", "Bob Cofounder"],
  "pitch": "One-line pitch.",
  "created_at": "2026-04-28T...",
  "skills_completed": {
    "founder-check": "2026-04-28T...",
    "market-problem": null
  }
}
```

## Cross-cutting concerns

### Playwright auth (`lib/playwright-auth.md`)

- Skills that need login-walled sources check whether the relevant session is active. If not, they instruct the VC to log in once via `mcp__playwright__browser_navigate` and confirm.
- Pace requests at human speed (a small delay between actions). No fan-out, no parallel browser sessions.
- Respect site ToS: skills explicitly note that automated browsing of these sites with the VC's own session is for personal research; skills must not initiate scraping campaigns.
- If a session expires mid-run, the skill pauses and re-prompts the VC to log in rather than failing the run.

### Source honesty (`lib/research-protocol.md`)

- Every factual claim in every artifact has a citation. Format: `[claim](source URL)` or `[claim] (VC-supplied: <input>)`.
- Empty cells are explicit. "Not found in public sources" is the default for any missing data point. Never invent.
- When sources contradict, surface the contradiction rather than picking a winner.

### Idempotency

- Every skill overwrites its own artifact when re-run. No appending.
- The orchestrator skips steps with existing artifacts unless `--force`.

### Cost and time discipline

- The skill bodies note that deep research is token-heavy. Skills that use WebSearch/WebFetch budget themselves: e.g., founder-check caps at ~30 fetches per founder, market-problem caps at ~50 fetches in phase 1.
- Default persona loop count is 6, configurable via argument.

## Build sequence

1. Plugin scaffolding: `.claude-plugin/plugin.json`, `marketplace.json`, README.
2. Shared lib docs: `lib/deal.md`, `lib/playwright-auth.md`, `lib/research-protocol.md`.
3. `dudu:founder-check` (smallest scope, exercises Playwright auth pattern first).
4. `dudu:competitive-landscape` (similar shape, validates research-protocol.md).
5. `dudu:market-sizing` (more analytical, less Playwright).
6. `dudu:market-problem` (most complex — three phases, persona generation, self-play).
7. `dudu:customer-discovery` (prep + debrief sub-actions).
8. `dudu:diligence` (orchestrator — wires everything together).
9. README + minimal usage walkthrough.

## Open questions deferred to implementation

- Whether self-play conversation rounds are best implemented as a single long prompt with role tags, or as a multi-turn loop driven by the skill body. Plan stage will pick.
- Whether `manifest.json` is updated by skills directly or only by the orchestrator. Plan stage will pick.
- Exact LinkedIn / Crunchbase Playwright selectors — will be discovered during implementation; skills must be resilient to selector breakage and prompt the VC to assist when stuck.
