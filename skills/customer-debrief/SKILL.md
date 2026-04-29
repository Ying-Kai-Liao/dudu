---
name: customer-debrief
description: Standalone skill that synthesizes real customer interview transcripts into a pain/WTP/objections artifact with quote-level evidence. Runs independently of any orchestrator — the only precondition is that transcripts exist under deals/<slug>/inputs/.
---

# Customer debrief

Synthesize the VC's actual interview notes into a research artifact. Read `lib/research-protocol.md` first.

## What this skill IS and IS NOT

- IS: a synthesis step over real-customer transcripts. Quote-grounded, contradiction-surfacing, opinionated.
- IS NOT: a prep tool. The target list, outreach templates, and interview script are now produced as a Stage-5 side effect of `dudu:pmf-signal` (legacy filename `customer-discovery-prep.md`). This skill never writes a prep artifact.
- IS NOT: orchestrator-coupled. This skill has no precondition on prior diligence, no re-invocation handshake, no pause-for-interviews state. It runs whenever transcripts are present.

## Inputs

Required:
- Deal slug
- At least one transcript file under `deals/<slug>/inputs/` — `.md`, `.txt`, or `.vtt` accepted

Optional:
- Pasted transcript text (the skill writes it to `deals/<slug>/inputs/transcript-<N>.md` before processing)

## Pre-flight

1. Confirm `deals/<slug>/inputs/` exists and contains at least one transcript file (`.md`, `.txt`, `.vtt`). If not, exit with: `No transcripts found under deals/<slug>/inputs/. Save interview transcripts there (.md, .txt, or .vtt) and re-run.`
2. Idempotency: if `deals/<slug>/customer-discovery.md` exists and `--force` was not passed, print `Artifact already exists at deals/<slug>/customer-discovery.md. Pass --force to overwrite.` and stop.

There is no other precondition. Specifically:

- No check for `customer-discovery-prep.md` — it may or may not exist; it is a convenience artifact, not a gate.
- No check for any prior orchestrator state (no `manifest.json` `skills_completed` lookups, no `pmf-signal.md` requirement, no `background.md` requirement).
- No check for `personas/`. This skill works on a deal with only a `manifest.json` and `inputs/transcript-*.md` if that's all the user has.

## Steps

1. Read every transcript under `deals/<slug>/inputs/` matching `*.md`, `*.txt`, `*.vtt`. Each becomes one input section. If filenames suggest interview names (e.g., `transcript-pm-acme.md`), use the suggestive part as the interviewee label; otherwise use `C1`, `C2`, etc.
2. For each interview, extract:
   - Pain intensity (1-10) with verbatim quote
   - Current solution with quote
   - WTP signal with quote (only when the interviewee gave an explicit number — never extrapolate)
   - Failed prior solutions with quote
   - Surprises (anything the VC didn't expect)
3. **Cross-reference against persona priors if they exist.** If `deals/<slug>/personas/verdicts.yaml` (PMF-authored) exists, flag interview findings that contradict the calibrated prior. If only legacy `personas/persona-*.md` files exist, fall back to comparing against those. If no persona files exist at all, skip the contradictions section.
4. **Contradictions are the most valuable signal.** Surface them prominently.

## Artifact: `deals/<slug>/customer-discovery.md`

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

## Persona / prior contradictions

[Where reality diverged from the prior. For each, name the source of the prior (PMF verdicts, legacy persona, or "no prior available"), the assumption, and the contradicting interview quote.]

## Aggregate verdict

- **Pain real?** Yes / No / Mixed — explain in 2 sentences.
- **Buyers willing to pay?** Yes / No / Insufficient signal — explain.
- **Wedge clear after talking to real people?** Yes / No / Partial — explain.

## Sources

- inputs/<transcript-1>.md
- ...
```

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["customer-debrief"]` with the current ISO-8601 UTC timestamp.

## Re-runnability

Re-running drops a fresh `customer-discovery.md` only when `--force` is supplied. Adding a new transcript and re-running with `--force` will incorporate the new interview into the synthesis.
