---
name: customer-discovery
description: Helps the VC do their own customer discovery — without the founder. 'prep' builds a target list and outreach drafts. 'debrief' synthesizes interview transcripts into pain/WTP/objections with quote-level evidence.
---

# Customer discovery

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

1. **Target list.** Search ~20 fetches across:
   - LinkedIn — Playwright with VC session. Filter by job title from the persona profile and by company size.
   - Reddit — identify ~3 relevant subreddits, surface ~5 candidates each (people posting about the relevant pain).
   - Niche communities — identify 1-2 relevant Slack/Discord communities (only ones with public membership lists).
   - X — search for the persona phrasing from the persona profile.

   Aim for 30 candidates total. For each, capture: name, channel, link, why-they-fit (one sentence), how-to-reach (DM / email / public post reply).

2. **Outreach templates.** Drafts cold-outreach message templates (one per channel: LinkedIn DM, Reddit DM, X DM, email) and per-persona variants slotted in for the top candidates.

   Each ~80 words. The persona-N.md profile dictates phrasing variants for the top 3 candidates per channel — slot them in inline.

3. **Interview script.** Anchored on these four questions; expand each with 1-2 follow-ups:
   - Tell me about this problem in your day-to-day.
   - How are you solving it today?
   - What would it be worth to you to solve this properly?
   - Have you looked for solutions? Why didn't they work?

4. **Optional: place screener calls via `callagent`.** Skip this step entirely if `callagent` is not on PATH or if no candidate has explicit opt-in.

   For each candidate in the target list with explicit opt-in (i.e. they responded to outreach and agreed to a 5-minute screener):

   1. Confirm with the VC, per call: "Did <candidate> explicitly opt in to this call?" If not, skip.
   2. Generate a task brief inline based on this deal's specifics — do not use a fixed template. Author the markdown yourself, drawing on the deal context (company, ICP from `personas/persona-*.md`, the wedge under evaluation) and the interview methodology you established in Step 3. The brief should:
      - Open with frontmatter `voice: alloy`, `language: en-US`, `disclosure_required: true`
      - Identify the firm and its research domain (use `<FIRM>` and `<COMPANY_DOMAIN>` placeholders for context substitution)
      - Include a verbatim disclosure paragraph under `## Disclosure`
      - Describe how the agent should interview (anchor on past concrete behavior, follow tangents, use silence, treat "I'd pay" as a yellow flag — Mom Test–style methodology)
      - Capture the specific topic of curiosity for THIS deal in the body
      - List hard rules (no portfolio company name, no pitching, end on first request)
   3. Write the task brief to `deals/<slug>/calls/task-cd-screener.md` and a context file to `deals/<slug>/calls/context.md` (frontmatter with `FIRM:`, `COMPANY_DOMAIN:`, etc.).
   4. **Iterate first with simulate.** Run `callagent simulate --task deals/<slug>/calls/task-cd-screener.md --context deals/<slug>/calls/context.md --schema deals/<slug>/calls/cd-schema.json` (author the schema inline too — fields like `specific_story_captured`, `pain_evidence`, `current_solution`, `wtp_signal`, `interesting_tangent`, `your_overall_read`, all optional). Play the recipient yourself for 2-3 turns. Adjust the brief if the agent feels off.
   5. Generate a consent token (e.g., output of `uuidgen`).
   6. Place the real call:
      ```
      callagent place \
        --to "<candidate-phone>" \
        --task deals/<slug>/calls/task-cd-screener.md \
        --context deals/<slug>/calls/context.md \
        --schema deals/<slug>/calls/cd-schema.json \
        --consent-token "<uuid>" \
        --output deals/<slug>/calls/<candidate-id>.json
      ```

   The result file (transcript + structured data) feeds the `debrief` sub-action.

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

1. Read interview material from two sources, treating each as one interview section:
   a. Files under `deals/<slug>/inputs/` — transcripts and notes the VC pasted in
   b. Files under `deals/<slug>/calls/*.json` — `callagent` screener-call results, if present (skip if the dir doesn't exist)

   For (b), the JSON's `transcript` field is the conversation text; the `structured_data` field pre-fills pain/WTP/current-solution rows in the debrief — but you must still cross-reference quotes from the transcript and write the verdict in your own words. The structured fields are agent-extracted, not authoritative.
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
