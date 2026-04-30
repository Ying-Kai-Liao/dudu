---
name: auto-diligence
description: End-to-end diligence from a company name. Auto-discovers founders + pitch, runs dudu:background-check → dudu:pmf-signal → optional callagent → dudu:customer-debrief, then renders report.html with embedded recordings.
---

# Auto-diligence (full end-to-end)

Single-trigger orchestrator that runs the entire dudu chain on one deal starting from just a company name. Everything else (slug, founders, pitch, deck) is either auto-discovered or filled in from public sources. Read `lib/deal.md`, `lib/research-protocol.md`, and `lib/playwright-auth.md` first.

This skill is the convenience surface for "I have a company name, give me the report.html." For deeper control over each stage, invoke the layered skills directly: `dudu:background-check`, `dudu:pmf-signal`, `dudu:customer-debrief`.

## Inputs

Required:

- Company name (free-form string)

Optional (skips the discovery step when supplied):

- `--slug <kebab>` — explicit deal slug; auto-derived from company name otherwise
- `--website <url>` — company homepage; auto-discovered otherwise
- `--founders "Alice Lin, Bob Chen"` — comma-separated; auto-discovered otherwise
- `--pitch "<one-liner>"` — one-line pitch; auto-derived from website otherwise
- `--deck <path>` — pitch deck file; uses manifest.pitch + L1 artifacts otherwise

Optional flags:

- `--auto-call` — after Layer 2, drive `callagent` against the top-N candidates from `outreach.md` and save results to `deals/<slug>/calls/`. Default off.
- `--call-n <int>` — number of candidates to call when `--auto-call` is set (default 3, max 10)
- `--no-render` — stop after MEMO.md; skip `report.html`
- `--force` — propagate `--force` to every sub-skill, overwriting existing artifacts

## Pre-flight

1. Refuse to run if the working directory is not a dudu repo root (no `lib/deal.md` present).
2. If `--slug` was given, validate it: kebab-case, lowercase, no leading underscore. Reject the run with a clear error otherwise.
3. If `deals/<slug>/report.html` already exists and `--force` was not passed, print `Auto-diligence already complete at deals/<slug>/report.html. Pass --force to re-run.` and stop.

## Stage 1 — Discovery (skip when all overrides supplied)

Goal: produce a `manifest.json` seed with `company`, `slug`, `pitch`, `founders[]`, and optionally `website`.

If `--slug`, `--website`, `--founders`, and `--pitch` are all supplied, skip discovery entirely and proceed to Stage 2.

Otherwise:

1. **Resolve the company.** Web search the company name with the WebSearch tool. Fetch budget: 1 search.
2. **Pick the canonical site.** From the top hits, identify the official domain (prefer `.com`/`.io`/`.ai` apex over LinkedIn / Crunchbase / press articles). If two or more candidates look equally plausible, pause and ask the user to disambiguate — do not guess.
3. **Fetch the homepage.** WebFetch budget: 3 (homepage, /about, /pricing). Extract:
   - The one-line value proposition (becomes `pitch` if `--pitch` not supplied)
   - Founder names from /about or footer (becomes `founders[]` if `--founders` not supplied)
4. **LinkedIn / Crunchbase fallback (only if founders not found on the site).** Authenticated browser via Playwright — see `lib/playwright-auth.md`. Resolve the company's LinkedIn page; read founder names from "People → Founders" or the company "About" block. Fetch budget: 2 navigations.
5. **Slug derivation.** If `--slug` was not supplied, kebab-case the company name (lowercase, ASCII only, drop punctuation, max 30 chars). Examples:
   - "LedgerLoop" → `ledgerloop`
   - "Twenty-Three Capital" → `twenty-three-capital`
   - "Müller & Söhne GmbH" → `muller-sohne`
6. **Confirmation.** Print the resolved seed back to the user (slug, company, founders, pitch, website) and stop only if anything is uncertain — flag specific fields with `?` and ask for confirmation. If everything looks confident, proceed without pausing.

Total Stage-1 budget: ~6 web fetches + 1 search. Pure secondary research; no LLM-heavy synthesis (Layer 2 owns that).

## Stage 2 — Initialize the deal

1. If `deals/<slug>/` does not exist, create it. Write `manifest.json` per the schema in `lib/deal.md`. Include the discovered (or supplied) `website` under a top-level `website` field if known.
2. If `--deck <path>` was supplied, copy the deck to `deals/<slug>/inputs/deck.<ext>`. If the deck is plain text (e.g., pasted), write to `inputs/deck.md`.
3. No deck is required; Stage 0 of `dudu:pmf-signal` falls back to `manifest.pitch` + L1 artifacts.

## Stage 3 — Layer 1 (`dudu:background-check`)

Invoke `dudu:background-check` with the resolved slug and supplied/discovered inputs. Propagate `--force` if supplied. Wait for completion: `deals/<slug>/background.md` must exist on success.

If background-check fails, surface its error verbatim and stop. Do not proceed to Layer 2.

## Stage 4 — Layer 2 (`dudu:pmf-signal`)

Invoke `dudu:pmf-signal` on the same slug. Propagate `--force` if supplied. Wait for completion: `deals/<slug>/pmf-signal.md`, `outreach.md`, and `personas/verdicts.yaml` must all exist on success.

## Stage 5 — Optional automated screener calls

If `--auto-call` was passed:

1. Read the top `--call-n` (default 3) candidates from `deals/<slug>/outreach.md` (sorted by warm-path quality).
2. For each candidate, follow the callagent recipe documented in `skills/pmf-signal/SKILL.md` Stage 5: write `task-screener-<id>.md`, `context.md`, and `screener-schema.json` under `deals/<slug>/calls/`.
3. Iterate once with `callagent simulate` against each task to sanity-check the brief; abort the auto-call stage if any simulate run produces a bad transcript. Surface the issue and let the user adjust manually.
4. Run `callagent run` for each candidate. Save audio recordings to `deals/<slug>/calls/<id>.<ext>` (callagent's native output) and result JSON to `deals/<slug>/calls/<id>.json`.
5. If callagent is not on PATH, print `callagent not found — skipping auto-call. Install callagent or run real interviews and save transcripts to deals/<slug>/inputs/.` and continue to Stage 6 with whatever calls/ already contains.

If `--auto-call` was not passed: skip this stage. The user is expected to either run their own interviews and save transcripts to `deals/<slug>/inputs/`, or invoke this skill again later with `--auto-call`.

## Stage 6 — Customer debrief (when material exists)

Check whether interview material is present:

- `deals/<slug>/inputs/` contains any `*.md`, `*.txt`, or `*.vtt` file beyond `deck.*`, OR
- `deals/<slug>/calls/` contains any `*.json` callagent result file

If yes: invoke `dudu:customer-debrief` on the slug. It writes `customer-discovery.md`. Propagate `--force`.

If no: skip this stage. The downstream MEMO will note that the customer-discovery section is pending.

## Stage 7 — Stitch `MEMO.md`

Read every artifact under `deals/<slug>/` and produce `deals/<slug>/MEMO.md` using the same shape as the deprecated `dudu:diligence` wrapper:

```markdown
# Investment memo: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## Founder background

[For each founder, summarize from `founder-<name>.md` in 3-5 bullets. Include prior managers, coworkers, collaborators, co-founders, board members, or senior operating partners when publicly identified. Show only intentionally public professional/social contact links such as LinkedIn, X/Twitter, GitHub, personal site, or company bio. Do not include private emails, phone numbers, or inferred/private relationship data. Link to the full dossier.]

## Problem and product

[Summary from `market-context.md` (4-6 sentences) + the strongest pattern + the most valuable contradiction. Link to the full file.]

## PMF signal & claim verification (calibrated prior + cross-artifact + external)

[Headline read from `pmf-signal.md`. Top 5 rows of the consolidated claim ledger (worst-news-first ordering). The 1 strongest cluster pattern. Explicit Stance B disclaimer for the persona-reaction rows; cross-artifact and external-evidence rows do not need the same disclaimer because they triangulate against actual evidence. List of `requires-data-room` flags for the VC to follow up on.]

## Customer signal

[Summary from `customer-discovery.md` if present; otherwise note "Pending — no interviews recorded yet." Quote 2-3 strongest verbatims when present. Flag any persona contradictions explicitly.]

## Competitive landscape

[Summary from `competitive-landscape.md`. Top 3 direct competitors. Incumbent verdict. Moat verdict.]

## Market sizing

[Wedge TAM range, expansion TAM range, comparison to founder claim.]

## Cross-artifact synthesis

[Surfaces contradictions ACROSS artifacts. e.g.: "Founder claims engineering teams are the buyer (deck p.3), but customer interviews showed product managers driving the purchase (interview-2)."]

## Recommendation

- **Pass / Watch / Pursue:** <verdict>
- **Why:** [3 sentences]
- **What would change my mind:** [2-3 specific things to verify]

## Source artifacts

- founder-<name>.md
- market-context.md
- pmf-signal.md
- outreach.md
- customer-discovery.md (if present)
- competitive-landscape.md
- market-sizing.md
```

## Stage 8 — Render `report.html`

Unless `--no-render` was passed:

1. Run `python3 scripts/render-report.py deals/<slug>`.
2. The renderer auto-discovers any `deals/<slug>/calls/*.{mp3,wav,m4a,webm,ogg}` and `deals/<slug>/inputs/*.{mp3,wav,m4a,webm,ogg}` files and embeds them as `<audio controls>` tags inside the Customer Signal section. Audio uses relative paths — `report.html` and the `calls/` / `inputs/` subdirectories must travel together.
3. If the script exits non-zero, surface the stderr but do not block — `MEMO.md` is still useful on its own.
4. If `python3` is not on PATH, print `report.html skipped — install Python 3 or run python3 scripts/render-report.py deals/<slug> manually.`

## Stage 9 — Print final paths

Print:

```
Auto-diligence complete.

  deals/<slug>/MEMO.md
  deals/<slug>/report.html   (if rendered)

Layered artifacts:
  deals/<slug>/background.md
  deals/<slug>/pmf-signal.md
  deals/<slug>/outreach.md
  deals/<slug>/customer-discovery.md   (if interviews ran)
```

If any sub-skill was skipped or failed, list the missing artifact and the recommended next command (`dudu:customer-debrief`, etc.).

## Re-runnability

Each underlying skill checks its own artifacts and skips when they exist (unless `--force`). Re-running auto-diligence after adding transcripts to `inputs/` or audio to `calls/` will:

- Skip Stages 3–4 (already done, unless `--force`)
- Run Stage 6 if `customer-discovery.md` is missing and material is now present
- Re-stitch `MEMO.md` and re-render `report.html`

## What this skill does NOT do

- Does not write any per-deal artifact directly. Every file under `deals/<slug>/` comes from a sub-skill or the renderer.
- Does not emit personas — that namespace is owned exclusively by `dudu:pmf-signal`.
- Does not bypass `dudu:pmf-signal`'s preflight gate. If Layer 1 is incomplete, Layer 2 will refuse and this skill stops.
- Does not run real human interviews. `--auto-call` drives `callagent` (a separate tool); for real interviews the VC saves transcripts to `inputs/` and re-invokes.
