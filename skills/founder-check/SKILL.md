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

## Optional: reference calls via `callagent`

Skip this section entirely if `callagent` is not on PATH or if the founder has not provided a reference list.

The founder MUST supply the reference list — do not synthesize references from the dossier. Save the reference list at `deals/<slug>/inputs/founder-<kebab-name>-references.md` with at minimum, per reference:
- Name
- Phone (E.164)
- How the founder knows them (peer / manager / customer / advisor)
- Explicit confirmation that the reference has agreed to be contacted

If any of those fields are missing for a reference, do not call them.

`callagent` enforces a privacy allowlist on `--to` (default: 3 pre-approved test numbers, exit code 2 otherwise). To call real references, the operator must override `CALLAGENT_ALLOWED_NUMBERS` for the session — do not bake real numbers into committed `.env` files. The allowlist is intentional belt-and-suspenders on top of the per-reference opt-in check.

### For each reference

1. Confirm with the VC, per call: "Did <reference> explicitly opt in to this call?" If not, skip.
2. Author a task brief inline for THIS founder and reference. Do not use a fixed template — write the brief based on what the dossier surfaced. The brief should:
   - Open with frontmatter `voice: alloy`, `language: en-US`, `disclosure_required: true`
   - Identify the firm and the founder under evaluation (use `<FIRM>` and `<FOUNDER_NAME>` placeholders for context substitution)
   - Include a verbatim disclosure paragraph under `## Disclosure` that names the founder and references them ("<FOUNDER_NAME> listed you as a reference")
   - Describe how the agent should interview a reference: anchor on specific events the reference can recall, never accept generic praise without an example, politely re-ask once if they say "no concerns", listen for what isn't said (hesitations, refusals to specify), don't push for a yes/no on "would you invest"
   - State the territory of curiosity for THIS reference (working relationship, strengths with examples, growth areas, would-they-work-with-again)
   - List hard rules (don't reveal what other references said, don't share the founder's pitch or what the firm is investing in, end on first request)
3. Write the task brief to `deals/<slug>/calls/task-founder-<kebab-name>-ref-<n>.md` and a context file to `deals/<slug>/calls/founder-<kebab-name>-context.md` (frontmatter with `FIRM:`, `FOUNDER_NAME:`).
4. Author a JSON Schema for end-of-call extraction at `deals/<slug>/calls/founder-reference-schema.json`. Suggested fields, all optional: `relationship_context`, `working_dates`, `strength_examples` (array of specific moments), `concern_examples` (array), `would_work_with_again` (enum: yes/no/qualified/unclear), `would_work_with_again_reason`, `reference_quality` (enum: high/medium/low), `what_was_not_said`, `your_overall_read`. Set `"required": []`.
5. **Iterate first with simulate.** Run `callagent simulate --task <task-path> --context <context-path> --schema deals/<slug>/calls/founder-reference-schema.json`. Play the reference yourself for 2-3 turns. Adjust the brief if the agent feels off — too pushy, too shallow, off-tone.
6. Generate a consent token (e.g., output of `uuidgen`).
7. Place the call:
   ```
   callagent place \
     --to "<reference-phone>" \
     --task deals/<slug>/calls/task-founder-<kebab-name>-ref-<n>.md \
     --context deals/<slug>/calls/founder-<kebab-name>-context.md \
     --schema deals/<slug>/calls/founder-reference-schema.json \
     --consent-token "<uuid>" \
     --output deals/<slug>/calls/founder-<kebab-name>-ref-<n>.json
   ```

### After all reference calls complete

Append a new section to `deals/<slug>/founder-<kebab-name>.md` titled `## Reference checks` that summarizes each call's transcript and `structured_data`. For each reference:
- One paragraph anchored in the verbatim `transcript` (cite exact quotes for any concern)
- The structured fields (would_work_with_again, key strengths, key concerns, what_was_not_said) listed for scanability
- A link to the call result file (`./calls/founder-<kebab-name>-ref-<n>.json`)

Then update `deals/<slug>/manifest.json` with a per-founder `reference_calls_completed_at` ISO timestamp.

If any reference call ended early (`status` other than `ended` in the result JSON), note that in the Reference checks section rather than dropping it silently.
