# dudu

> Built for the **Lyra Codex hackathon**. Instead of just research and gather data, it adds quantitative value on top of it with grounded ICP test and real customer interview flow. 

Six skills + an orchestrator that take a one-line pitch and produce a citation-backed investment memo. Founder dossiers, persona self-play interviews, your-own customer discovery, competitive landscape, and bottom-up market sizing — every claim cited, every gap explicit.

## Install for Codex

Clone the repo and symlink the skills directory:

```bash
git clone https://github.com/Ying-Kai-Liao/dudu.git ~/.codex/dudu
mkdir -p ~/.agents/skills
ln -s ~/.codex/dudu/skills ~/.agents/skills/dudu
```

Restart Codex to discover the skills. Full Codex install guide (Windows junction variant, troubleshooting, updating) is in `.codex/INSTALL.md`.

## Demo

`test/ledgerloop/` contains a complete dudu run against a real Cape Town company (LedgerLoop, founder Dylan Martens), produced from a Codex session.

What's in there:

- `founder-dylan-martens.md` — public-web + LinkedIn dossier
- `personas/` — context bundle + 3 personas + 6 self-play conversation rounds
- `market-problem.md` — cross-round synthesis with patterns, contradictions, and questions for real interviews
- `competitive-landscape.md` — direct/indirect competitors + incumbent threat verdict + moat analysis
- `market-sizing.md` — bottom-up TAM, anchored on a defined ICP and reachable population
- `customer-discovery-prep.md` — target list (LinkedIn searches in `inputs/`), outreach templates, interview script
- `MEMO.md` — final stitched investment memo with a Pass verdict and conditional path to Watch
- `report.html` — single-file rendered version of the run, openable in any browser, safe to share by email
- `manifest.json` — five of six skills completed; `customer-discovery-debrief` is null because no real interviews were run for the demo

Notable moment: founder-check caught a pitch/footprint mismatch — the supplied pitch said "embedded working capital for Southeast Asian wholesalers" but the founder's actual public footprint is a South African accounting practice. The VC reframed the deal mid-run rather than continuing on a wrong premise. See `manifest.json` `pitch_reframe_note`.

## Install for Claude Code

In a Claude Code session, add the marketplace from the public GitHub repo and install the plugin:

```
/plugin marketplace add Ying-Kai-Liao/dudu
/plugin install dudu@dudu
```

To install from a local clone instead (for development), substitute the path:

```
/plugin marketplace add /path/to/dudu
/plugin install dudu@dudu
```

## Prerequisites

- The Playwright MCP server must be installed and enabled. Skills that touch LinkedIn or Crunchbase use it to drive *your own* authenticated browser session — they do not store credentials and do not bypass site authentication.
- WebSearch and WebFetch tools must be available (default in Claude Code).

## Skills

| Skill | What it does | Output |
|-------|--------------|--------|
| `dudu:diligence` | Orchestrates the full workflow on one deal | `deals/<slug>/MEMO.md` + `report.html` |
| `dudu:founder-check` | Public-web + LinkedIn dossier per founder | `deals/<slug>/founder-<name>.md` |
| `dudu:idea-validation` | Compare 2–5 candidate ICPs head-to-head, recommend a wedge (optional, idea-stage only) | `deals/<slug>/idea-validation.md` |
| `dudu:market-problem` | Deep context + persona self-play (rehearsal) | `deals/<slug>/market-problem.md` |
| `dudu:customer-discovery` | `prep` builds target list + scripts; `debrief` synthesizes real interviews | `deals/<slug>/customer-discovery*.md` |
| `dudu:competitive-landscape` | Competitor matrix, incumbent threat, moat analysis | `deals/<slug>/competitive-landscape.md` |
| `dudu:market-sizing` | Bottom-up TAM ignoring founder claims | `deals/<slug>/market-sizing.md` |

Each skill can be invoked standalone, or run all together via the orchestrator. `idea-validation` is optional and not part of the orchestrated flow — use it before `market-problem` when the wedge ICP is unclear.

## Typical workflow

1. **Start the diligence:** invoke `dudu:diligence` and answer its prompts (slug, company, founders, pitch, optional deck).
2. **Wait for the prep phase to complete.** Five skills run, taking ~15–45 minutes depending on the deal complexity and your network access.
3. **Read the prep output.** Especially `customer-discovery-prep.md` — the candidate list, outreach templates, and interview script.
4. **Run real customer interviews** (5–10 of them). Save transcripts/notes under `deals/<slug>/inputs/`.
5. **Re-invoke `dudu:diligence`.** The orchestrator detects the inputs, runs `customer-discovery debrief`, stitches `MEMO.md`, and renders `report.html` — a single self-contained file (embedded CSS/JS, no network assets) that you can email to a partner or open offline.

## What's NOT in v1

- Founder reference checks via your personal network (out of scope — that's a calendar task, not a skill task).
- Paid-API integrations (Crunchbase Pro, PitchBook).
- Auto-generated investment-committee slide decks.
- Multi-tenant deal sharing across a partnership.
- Hybrid VC-in-the-loop persona interviewing (deferred).

## Repository layout

```
.claude-plugin/        Claude Code plugin + marketplace manifests
.codex-plugin/         Codex plugin manifest
.codex/INSTALL.md      Codex install guide (clone + symlink)
skills/                six SKILL.md files (read by both harnesses)
lib/                   shared procedural docs (deal schema, Playwright UX, research protocol)
scripts/lint-skills.sh frontmatter + lib-reference linter (also runs render-report smoke test)
scripts/render-report.py renders deals/<slug>/report.html from MEMO + artifacts (stdlib-only)
tests/lint/            linter test fixtures and runner
test/ledgerloop/       hackathon demo run (committed; see Demo section)
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
