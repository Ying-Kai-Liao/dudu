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

## Parallelization (Layer 2 — per founder)

Founders are independent research units. With **2 or more** founders, dispatch **one `general-purpose` subagent per founder in a single message** so they run concurrently. See `lib/research-protocol.md` § Parallelization.

Each subagent prompt MUST include:

- The founder's name, company name, and any disambiguator (e.g., LinkedIn URL if supplied).
- A **per-founder budget of ~25 public-web fetches** (reserve ~5 for main-session Playwright work below).
- The full citation and source-honesty rules from `lib/research-protocol.md` (paste, don't reference — subagents don't auto-load it).
- Sources to consult: items **1–7 and 10** from the list above. **Skip items 8 (LinkedIn) and 9 (Crunchbase)** — those require the VC's authenticated session and cannot be delegated.
- Required return shape: a markdown summary with sections matching the artifact template (Career timeline, Domain credibility, Prior ventures, Public controversies, Communication style with one verbatim quote, Open questions) plus a `Sources` list. **Do not let the subagent write to `deals/`** — it returns text only.

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
