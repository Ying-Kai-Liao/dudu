# dudu

VC due diligence skills for Claude Code. Six skills + an orchestrator that produce citation-backed markdown artifacts under a per-deal directory.

## Install

In a Claude Code session:

```
/plugin marketplace add /Users/ykliao/Workspace/dudu
/plugin install dudu@dudu
```

(Substitute the actual path on your machine. Once published, this becomes a git URL.)

## Prerequisites

- The Playwright MCP server must be installed and enabled. Skills that touch LinkedIn or Crunchbase use it to drive *your own* authenticated browser session — they do not store credentials and do not bypass site authentication.
- WebSearch and WebFetch tools must be available (default in Claude Code).

## Skills

| Skill | What it does | Output |
|-------|--------------|--------|
| `dudu:diligence` | Orchestrates the full workflow on one deal | `deals/<slug>/MEMO.md` |
| `dudu:founder-check` | Public-web + LinkedIn dossier per founder | `deals/<slug>/founder-<name>.md` |
| `dudu:market-problem` | Deep context + persona self-play (rehearsal) | `deals/<slug>/market-problem.md` |
| `dudu:customer-discovery` | `prep` builds target list + scripts; `debrief` synthesizes real interviews | `deals/<slug>/customer-discovery*.md` |
| `dudu:competitive-landscape` | Competitor matrix, incumbent threat, moat analysis | `deals/<slug>/competitive-landscape.md` |
| `dudu:market-sizing` | Bottom-up TAM ignoring founder claims | `deals/<slug>/market-sizing.md` |

Each skill can be invoked standalone, or run all together via the orchestrator.

## Typical workflow

1. **Start the diligence:** invoke `dudu:diligence` and answer its prompts (slug, company, founders, pitch, optional deck).
2. **Wait for the prep phase to complete.** Five skills run, taking ~15–45 minutes depending on the deal complexity and your network access.
3. **Read the prep output.** Especially `customer-discovery-prep.md` — the candidate list, outreach templates, and interview script.
4. **Run real customer interviews** (5–10 of them). Save transcripts/notes under `deals/<slug>/inputs/`.
5. **Re-invoke `dudu:diligence`.** The orchestrator detects the inputs, runs `customer-discovery debrief`, and stitches `MEMO.md`.

## What's NOT in v1

- Founder reference checks via your personal network (out of scope — that's a calendar task, not a skill task).
- Paid-API integrations (Crunchbase Pro, PitchBook).
- Auto-generated investment-committee slide decks.
- Multi-tenant deal sharing across a partnership.
- Hybrid VC-in-the-loop persona interviewing (deferred).

## Repository layout

```
.claude-plugin/        plugin and marketplace manifests
skills/                six SKILL.md files
lib/                   shared procedural docs (deal schema, Playwright UX, research protocol)
scripts/lint-skills.sh frontmatter + lib-reference linter
tests/lint/            linter test fixtures and runner
docs/superpowers/      design spec and implementation plan
deals/                 per-deal artifacts (gitignored)
```

## Development

Run the linter before every commit:

```bash
bash scripts/lint-skills.sh
```

Run the linter test suite:

```bash
bash tests/lint/run.sh
```

## License

MIT
