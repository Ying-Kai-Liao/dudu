---
name: founder-check
description: Build a public-web + authenticated-browser dossier on each founder of a deal under evaluation. Surfaces career, prior ventures, controversies, and open questions a partner would ask.
---

# Founder check

Produce a citation-backed dossier on each founder named in the deal. Read `lib/research-protocol.md` and `lib/playwright-auth.md` before starting and follow them strictly.

## Inputs

Required:
- Deal slug (kebab-case directory name under `deals/`). Prompt the VC if missing.
- Company name. Prompt the VC if missing.
- Founder names — one or more. **If not supplied, run the Discovery step below before continuing.**

Optional (use if available):
- Founder LinkedIn URLs (skip the LinkedIn search step if supplied)
- Pitch deck or company website URL (helps disambiguate the right person and seeds Discovery)

## Discovery (when founder names are not supplied)

If founder names were not supplied, attempt to discover them before doing dossier work. Cap at ~5 fetches for this step.

Sources, in priority order:

1. **Pitch deck / company website** — if supplied or findable, fetch the `/about`, `/team`, or `/leadership` page.
2. **Crunchbase company page** — Playwright with the VC's authenticated session (per `lib/playwright-auth.md`). "Key People" / "Founders" section.
3. **LinkedIn company page** — Playwright with the VC's authenticated session (per `lib/playwright-auth.md`). Navigate to `https://www.linkedin.com/company/<slug>/people/`, filter the People section by titles "Founder", "Co-founder", "CEO", "CTO". If the company slug isn't known, search LinkedIn for the company name first and follow the profile link.
4. **Google search** — `"<company name>" founder OR co-founder OR CEO`. Read the top 5 results.
5. **News** — recent press releases or funding announcements often name founders explicitly.

Compile the candidate list with one source per name, then ask the VC to confirm before proceeding:

> "I found these likely founders for <company>: <list with one source each>. Should I run founder-check on all of them? Reply with adjustments (add / remove / rename) or 'proceed'."

Wait for the VC's response. Once confirmed, write the final list into `deals/<slug>/manifest.json` `founders` (creating the manifest first if needed), then continue to Pre-flight.

If Discovery returns no candidates after the budget is spent, stop and ask: "I couldn't find any founders for <company> in public sources. Please supply at least one founder name."

## Pre-flight

1. If `deals/<slug>/manifest.json` does not exist, create it with the schema in `lib/deal.md`. If the founder is not in the manifest yet, add them.
2. For each founder, the artifact path is `deals/<slug>/founder-<kebab-name>.md`. If it exists and `--force` was not passed, print "Artifact already exists at deals/<slug>/founder-<kebab-name>.md. Pass --force to overwrite." and stop.

## Sources to consult (per founder)

In rough priority order, capping at ~30 fetches per founder:

1. **Google web search** for the founder's name + their company name (disambiguates from same-named people).
2. **Personal site / blog** if findable.
3. **GitHub** profile: owned repos, contribution graph, language mix, recent activity.
4. **Twitter/X** profile: bio, pinned tweet, last ~50 posts. Look for stated positions, networks, controversies.
5. **News search** (Google News, TechCrunch, sector trade press) for the founder's name in quotes.
6. **Podcast appearances** — search "<founder name> podcast" — listen to short intro/bio segments only.
7. **Conference talks** — search "<founder name> talk OR keynote OR slides".
8. **LinkedIn** — Playwright with the VC's authenticated session. Career timeline, current role, notable connections (only count, not names, in the artifact). Follow `lib/playwright-auth.md` exactly.
9. **Crunchbase founder page** — Playwright. Prior ventures with funding/exit data.
10. **Court records / litigation** — search "<founder name> lawsuit OR litigation OR settled" with the company name as additional context. Only include results clearly tied to this person.
11. **Prior managers / partners / co-founders** — identify publicly visible previous managers, direct collaborators, co-founders, board members, or senior operating partners from LinkedIn, company pages, press releases, GitHub orgs, and prior-venture pages. Capture only professional/public social contact links (LinkedIn, X/Twitter, GitHub, personal site, company bio). Do not infer private contact details, scrape emails/phone numbers, or expose non-public relationship data.

## Parallelization (Layer 2 — per founder)

Founders are independent research units. With **2 or more** founders, dispatch **one worker subagent per founder**, all concurrently in a single turn. See `lib/research-protocol.md` § Parallelization for the cross-platform mapping (Claude Code: `Agent` with `subagent_type="general-purpose"`; Codex: `spawn_agent` with `agent_type="worker"` and `multi_agent = true` in config).

Each subagent prompt MUST include:

- The founder's name, company name, and any disambiguator (e.g., LinkedIn URL if supplied).
- A **per-founder budget of ~25 public-web fetches** (reserve ~5 for main-session Playwright work below).
- The full citation and source-honesty rules from `lib/research-protocol.md` (paste, don't reference — subagents don't auto-load it).
- Sources to consult: items **1–7, 10, and the public-web portions of 11** from the list above. **Skip items 8 (LinkedIn) and 9 (Crunchbase)** — those require the VC's authenticated session and cannot be delegated.
- Required return shape: a markdown summary with sections matching the artifact template (Career timeline, Domain credibility, Prior ventures, Public controversies, Communication style with one verbatim quote, Open questions) plus a `Sources` list. **Do not let the subagent write to `deals/`** — it returns text only.
- Include a `Prior managers / partners` section when public sources identify credible previous managers, direct collaborators, co-founders, board members, or senior operating partners. For each person, return name, role/relationship, shared company or project, visible timeframe if known, and public professional/social profile links. Exclude private emails, phone numbers, and anything not intentionally public.

After all subagents return, in the **main session**:

1. For each founder, do the LinkedIn + Crunchbase Playwright work (items 8, 9). Authenticated browsers cannot run in subagents.
2. Merge the subagent summary + Playwright findings into the artifact and write `deals/<slug>/founder-<kebab-name>.md`.

With a single founder, skip fan-out and run inline using Layer 1 (batch parallel fetches in a single message).

## Artifact template

Write to `deals/<slug>/founder-<kebab-name>.md`:

```markdown
# Founder check: <Full Name>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## Career timeline

| Years | Company | Role | Outcome |
|-------|---------|------|---------|
| ... | ... | ... | ... |

## Domain credibility

[2-4 sentences on what makes them credible — or not — to ship this product. Cite specific evidence.]

## Prior ventures

- **<Company>** (<years>) — <one-paragraph summary, including outcome: acquired / shut down / still operating>. Source: [link]

## Public controversies / litigation

[Either bulleted findings with sources, or "Not found in public sources."]

## Communication style

[2-3 sentences with a representative quote and source.]

## Network density

[Notable co-founders, advisors, or employer alumni. Count of LinkedIn connections if available. Source.]

## Prior managers / partners

| Person | Relationship | Shared company/project | Timeframe | Public social/professional links | Source |
|--------|--------------|------------------------|-----------|----------------------------------|--------|
| ... | Previous manager / co-founder / board member / operating partner / collaborator | ... | ... | LinkedIn / X / GitHub / personal site / company bio | [link] |

If no credible public contacts are found, write: "No previous managers, partners, or direct collaborators with public professional/social profiles were confidently identified."

## Open questions a partner would ask

- [Specific question grounded in something above]
- [Another]

## Sources

- [Title](url) — brief description
- ...
```

## After writing

1. Update `deals/<slug>/manifest.json` `skills_completed["founder-check"]` to the current ISO-8601 UTC timestamp.
2. Print a one-line summary: `Wrote founder-check for N founder(s) to deals/<slug>/`.

## Optional: reference calls via `dudu:place-call`

Skip this section entirely if `callagent` is not on PATH or if the founder has not provided a reference list.

The founder MUST supply the reference list — do not synthesize references from the dossier. Save the reference list at `deals/<slug>/inputs/founder-<kebab-name>-references.md` with, per reference:
- Name
- Phone (E.164)
- How the founder knows them (peer / manager / customer / advisor)
- Explicit confirmation that the reference has agreed to be contacted

If any of those fields are missing for a reference, do not call them.

For each opted-in reference, invoke `dudu:place-call` with:

- `slug` = this deal
- `purpose = reference-check`
- `target.name` = reference name
- `target.phone` = reference phone (E.164)
- `consent.opted_in = true`
- `consent.token` = a fresh `uuidgen` value (one per call)
- Optionally `--simulate-first` for the first reference of a deal so the brief can be tuned before real calls go out
- Pass `--demo` to smoke the pipeline end-to-end before any real reference exists — it routes to the privacy allowlist and tags the result `demo:true`

`dudu:place-call` authors the reference-check brief from this founder's dossier, writes it to `deals/<slug>/calls/`, simulates if asked, dials, and writes a result JSON. callagent enforces a privacy allowlist on `--to`; to call real references the operator must export `CALLAGENT_ALLOWED_NUMBERS` for the session — do not bake real numbers into committed `.env` files.

### After all reference calls complete

Append a new section to `deals/<slug>/founder-<kebab-name>.md` titled `## Reference checks` that summarizes each call. For each reference:
- One paragraph anchored in the verbatim `transcript` from the result JSON (cite exact quotes for any concern)
- The structured fields (`would_work_with_again`, key strengths, key concerns, `what_was_not_said`) listed for scanability
- A link to the call result file under `./calls/`

Then update `deals/<slug>/manifest.json` with a per-founder `reference_calls_completed_at` ISO timestamp.

If any reference call ended early (`status` other than `ended` in the result JSON), note that in the Reference checks section rather than dropping it silently.
