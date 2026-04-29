---
name: customer-discovery
description: Helps the VC do their own customer discovery — without the founder. 'prep' builds a target list and outreach drafts. 'debrief' synthesizes interview transcripts into pain/WTP/objections with quote-level evidence.
---

# Customer discovery

> **Note:** As of pmf-signal v1, the `prep` sub-action is no longer invoked by `dudu:diligence` — `dudu:pmf-signal` stage 5 emits `customer-discovery-prep.md` directly. The `prep` sub-action remains available for standalone use (when running this skill outside the diligence orchestrator chain). `debrief` is unchanged and still part of the orchestrator chain.

Two sub-actions, dispatched by argument: `prep` and `debrief`. Read `lib/research-protocol.md` and `lib/playwright-auth.md` first.

## Dispatch

If the user invokes the skill without specifying:
- If `customer-discovery-prep.md` does not exist → run `prep`.
- If `customer-discovery-prep.md` exists and `customer-discovery.md` does not → run `debrief`.
- Else → ask which they want.

## Inputs (both sub-actions)

Required:
- Deal slug

`prep` additionally:
- Persona profiles from `deals/<slug>/personas/persona-*.md` if available — else prompt for ICP.

`debrief` additionally:
- Interview transcripts or notes (the VC pastes these in or supplies file paths under `deals/<slug>/inputs/`).

## Pre-flight

Idempotency check on the relevant artifact (`deals/<slug>/customer-discovery-prep.md` for prep, `deals/<slug>/customer-discovery.md` for debrief). If the relevant artifact exists and `--force` was not passed, print "Artifact already exists at <path>. Pass --force to overwrite." and stop.

---

## Sub-action: prep

Goal: produce a target list, outreach drafts, and an interview script.

### Steps

1. **Target list.** Search ~20 fetches across the channels below. **Aim for 30 candidates total.** For each, capture: name, channel, link, why-they-fit (one sentence), how-to-reach (DM / email / public post reply).

   - **LinkedIn** (main session only — Playwright with VC session). Filter by job title from the persona profile and by company size. ~5 fetches.
   - **Reddit** — identify ~3 relevant subreddits, surface ~5 candidates each (people posting about the relevant pain). ~5 fetches.
   - **Niche communities** — identify 1-2 relevant Slack/Discord communities (only ones with public membership lists). ~5 fetches.
   - **X** — search for the persona phrasing from the persona profile. ~5 fetches.

   **Parallelization:** dispatch **three worker subagents concurrently** — one for Reddit, one for niche communities, one for X — using your host's parallel-agent dispatch primitive (Claude Code: `Agent` with `subagent_type="general-purpose"`; Codex: `spawn_agent` with `agent_type="worker"`). See `lib/research-protocol.md` § Parallelization for the full cross-platform mapping and message-framing template. Each subagent receives the persona profile, the channel-specific source instructions above, its ~5-fetch cap, the citation rules from `lib/research-protocol.md` (pasted), and a required return shape: a list of candidate rows (`name | link | why-they-fit | how-to-reach`).

   The main session does the LinkedIn pass concurrently with the subagent dispatch (Playwright cannot be delegated). When all return, merge into a single 30-row target list.

2. **Outreach templates.** Drafts cold-outreach message templates (one per channel: LinkedIn DM, Reddit DM, X DM, email) and per-persona variants slotted in for the top candidates.

   Each ~80 words. The persona-N.md profile dictates phrasing variants for the top 3 candidates per channel — slot them in inline.

3. **Interview script.** Anchored on these four questions; expand each with 1-2 follow-ups:
   - Tell me about this problem in your day-to-day.
   - How are you solving it today?
   - What would it be worth to you to solve this properly?
   - Have you looked for solutions? Why didn't they work?

### Artifact: `deals/<slug>/customer-discovery-prep.md`

```markdown
# Customer discovery prep: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## Target list

| # | Name | Channel | Link | Why they fit | How to reach |
|---|------|---------|------|--------------|--------------|
| 1 | ... | LinkedIn | [link] | ... | DM |
| ... |

## Outreach templates

### LinkedIn DM (template)

> [80-word draft]

#### Variant for candidate #<N>

> [tweaked draft]

[Repeat for Reddit DM, X DM, Cold email]

## Interview script

1. **Tell me about this problem in your day-to-day.**
   - Follow-ups: ...

2. **How are you solving it today?**
   - Follow-ups: ...

[etc.]

## Sources

- ...
```

After writing, update manifest `skills_completed["customer-discovery-prep"]`.

---

## Sub-action: debrief

Goal: synthesize the VC's actual interview notes into a research artifact.

### Steps

1. Read transcripts/notes from `deals/<slug>/inputs/` or from VC's pasted text. Each interview becomes one input section.
2. For each interview, extract:
   - Pain intensity (1-10) with quote
   - Current solution with quote
   - WTP signal with quote
   - Failed prior solutions with quote
   - Surprises (anything the VC didn't expect)
3. Cross-reference against `personas/persona-*.md` if they exist. Flag where reality contradicted the persona. **Contradictions are the most valuable signal.**

### Artifact: `deals/<slug>/customer-discovery.md`

```markdown
# Customer discovery: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>
**Interviews:** <N>

## Pain intensity

| Interviewee | Score (1-10) | Verbatim |
|-------------|--------------|----------|
| C1 | ... | "..." |
| ... |

**Aggregate read:** [1-2 sentences]

## Current solutions

[Per-interviewee with verbatim quotes]

## Willingness to pay

[Per-interviewee with verbatim quotes. Surface explicit numbers ONLY when the interviewee gave one. Never extrapolate.]

## Failed prior solutions

[Per-interviewee with verbatim quotes. This is the most actionable insight for the founder.]

## Persona contradictions

[Where reality diverged from `persona-N.md`. For each, name the persona, the assumption, and the contradicting quote.]

## Aggregate verdict

- **Pain real?** Yes / No / Mixed — explain in 2 sentences.
- **Buyers willing to pay?** Yes / No / Insufficient signal — explain.
- **Wedge clear after talking to real people?** Yes / No / Partial — explain.

## Sources

- inputs/interview-1.md
- ...
```

After writing, update manifest `skills_completed["customer-discovery-debrief"]`.
