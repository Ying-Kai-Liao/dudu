---
name: founder-check
description: Build a public-web + authenticated-browser dossier on each founder of a deal under evaluation. Surfaces career, prior ventures, controversies, and open questions a partner would ask.
---

# Founder check

Produce a citation-backed dossier on each founder named in the deal. Read `lib/research-protocol.md` and `lib/playwright-auth.md` before starting and follow them strictly.

## Inputs

Required (prompt the VC if missing):
- Deal slug (kebab-case directory name under `deals/`)
- Founder names (one or more)

Optional (use if available):
- Founder LinkedIn URLs (skip the LinkedIn search step if supplied)
- Pitch deck or company website URL (helps disambiguate the right person)

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
