# dudu

> Built for the **Lyra Codex hackathon**. Instead of just research and gather data, it adds quantitative value on top of it with grounded ICP test and real customer interview flow.

A layered VC due-diligence plugin. Layer 1 (`dudu:background-check`) gives you the cheap public-source bundle every VC could produce in an afternoon. Layer 2 (`dudu:pmf-signal`) is the unique deliverable: every founder/company claim verified against a grounded N=15–200 persona simulation, cross-artifact triangulation, and bounded external evidence — emitted as a falsifiable claim ledger × verdict matrix.

## Layered architecture

```
┌──────────────────────────── Layer 1: BACKGROUND CHECK ─────────────────────────┐
│ Cheap. Public sources. Parallel-safe. Produces the L1 sentinel and the         │
│ context bundle that Layer 2 verifies against.                                  │
│                                                                                │
│ dudu:background-check                                                          │
│   ├─ dudu:founder-check                                                        │
│   ├─ dudu:market-context                                                       │
│   ├─ dudu:competitive-landscape                                                │
│   └─ dudu:market-sizing                                                        │
│ Output: deals/<slug>/background.md  (sentinel) + per-skill artifacts.          │
│ NO personas — that namespace is owned by Layer 2.                              │
└────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────── Layer 2: PMF SIGNAL ───────────────────────────────┐
│ Expensive. Simulation + cross-artifact + external. The unique value.           │
│                                                                                │
│ dudu:pmf-signal                                                                │
│ Output: pmf-signal.md (claim ledger × verdict), outreach.md (warm-path),       │
│         personas/*.yaml (the simulation), customer-discovery-prep.md           │
│         (legacy-shape convenience artifact, Stage 5 side effect).              │
└────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────── Standalone: CUSTOMER DEBRIEF ──────────────────────────┐
│ Runs whenever real interview transcripts exist under deals/<slug>/inputs/.     │
│ No orchestrator coupling.                                                      │
│                                                                                │
│ dudu:customer-debrief                                                          │
│ Output: customer-discovery.md                                                  │
└────────────────────────────────────────────────────────────────────────────────┘
```

For backward compatibility, the deprecated `dudu:diligence` wrapper still runs the full chain end-to-end. It will be removed in a future release.

## Install for Codex

Clone the repo and symlink the skills directory:

```bash
git clone https://github.com/Ying-Kai-Liao/dudu.git ~/.codex/dudu
mkdir -p ~/.agents/skills
ln -s ~/.codex/dudu/skills ~/.agents/skills/dudu
```

Restart Codex to discover the skills. Full Codex install guide (Windows junction variant, troubleshooting, updating) is in `.codex/INSTALL.md`.

## Demo

`test/ledgerloop/` contains a complete dudu run against a real Cape Town company (LedgerLoop, founder Dylan Martens), produced from a Codex session under the legacy (pre-split) layout.

What's in there:

- `founder-dylan-martens.md` — public-web + LinkedIn dossier
- `personas/` — context bundle + 3 personas + 6 self-play conversation rounds (legacy `market-problem` Phase 2 output; under the layered architecture this namespace is now owned by `dudu:pmf-signal`)
- `market-problem.md` — cross-round synthesis (legacy filename; the new equivalent is `market-context.md`)
- `competitive-landscape.md` — direct/indirect competitors + incumbent threat verdict + moat analysis
- `market-sizing.md` — bottom-up TAM, anchored on a defined ICP and reachable population
- `customer-discovery-prep.md` — target list, outreach templates, interview script
- `MEMO.md` — final stitched investment memo with a Pass verdict and conditional path to Watch
- `report.html` — single-file rendered version, openable in any browser, safe to share by email
- `manifest.json` — legacy schema with `market-problem` and `customer-discovery-*` keys

The renderer tolerates both legacy and new layouts; legacy demo deals continue to work unchanged.

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

| Skill | Layer | What it does | Output |
|-------|-------|--------------|--------|
| `dudu:background-check` | L1 orchestrator | Runs the four cheap sub-skills + writes the L1 sentinel | `deals/<slug>/background.md` |
| `dudu:founder-check` | L1 sub-skill | Public-web + LinkedIn dossier per founder | `founder-<name>.md` |
| `dudu:market-context` | L1 sub-skill | Public-source market & problem context (no personas) | `market-context.md` |
| `dudu:competitive-landscape` | L1 sub-skill | Competitor matrix, incumbent threat, moat analysis | `competitive-landscape.md` |
| `dudu:market-sizing` | L1 sub-skill | Bottom-up TAM ignoring founder claims | `market-sizing.md` |
| `dudu:pmf-signal` | **L2 (unique)** | Claim ledger × verdict matrix from N=15–200 persona simulation + cross-artifact + external evidence + warm-path outreach | `pmf-signal.md` + `outreach.md` + `personas/*` |
| `dudu:customer-debrief` | standalone | Synthesizes real interview transcripts into pain/WTP/objections | `customer-discovery.md` |
| `dudu:idea-validation` | optional | Compare 2–5 candidate ICPs head-to-head, recommend a wedge (idea-stage only) | `idea-validation.md` |
| `dudu:diligence` | deprecated wrapper | Backward-compat: runs L1 + L2 + debrief + stitch + render | `MEMO.md` + `report.html` |
| `dudu:market-problem` | deprecated stub | Forwards to `dudu:market-context` for one release window | (forwards) |
| `dudu:customer-discovery` | deprecated stub | Forwards `prep` → pmf-signal, `debrief` → customer-debrief | (forwards) |

## Typical workflow (recommended layered call)

1. **Layer 1:** invoke `dudu:background-check` and answer prompts (slug, company, founders, pitch, optional deck). Produces the four L1 artifacts and `background.md` in ~10–25 minutes.
2. **Layer 2:** invoke `dudu:pmf-signal`. Reads the L1 bundle, runs the N=60 persona simulation by default, emits `pmf-signal.md` (claim ledger × verdict matrix), `outreach.md` (warm-path-prioritized candidates), and the legacy-shape `customer-discovery-prep.md`. ~20–60 minutes depending on `--n`.
3. **Real interviews:** read `pmf-signal.md` for the calibrated prior. Reach out to candidates from `outreach.md`. Run 5–10 real interviews. Save transcripts under `deals/<slug>/inputs/`.
4. **Debrief:** invoke `dudu:customer-debrief`. Synthesizes the transcripts into `customer-discovery.md` with pain/WTP/objections and contradictions vs. the calibrated prior.

Each skill can be invoked standalone. `idea-validation` is optional and not part of the orchestrated flow — use it before `market-context` when the wedge ICP is unclear.

### Migration note for users of `dudu:diligence`

The legacy `dudu:diligence` invocation still works — it runs the full chain end-to-end and stitches `MEMO.md` plus renders `report.html`. The wrapper prints a deprecation notice on every invocation and will be removed by the `deprecate-diligence-orchestrator` change. To migrate, use the layered call above and stitch the memo manually if you still want one. The render step (`python3 scripts/render-report.py deals/<slug>`) works on either layout.

## What's NOT in v1

- Founder reference checks via your personal network (out of scope — that's a calendar task, not a skill task).
- Paid-API integrations (Crunchbase Pro, PitchBook).
- Auto-generated investment-committee slide decks.
- Multi-tenant deal sharing across a partnership.
- Hybrid VC-in-the-loop persona interviewing (deferred).
- A fleet runner for analyzing N startups in parallel (tracked in `openspec/changes/fleet-runner-and-dashboard`).
- A PMF-led report restructure (tracked in `openspec/changes/pmf-led-report`).

## Repository layout

```
.claude-plugin/        Claude Code plugin + marketplace manifests
.codex-plugin/         Codex plugin manifest
.codex/INSTALL.md      Codex install guide (clone + symlink)
skills/                SKILL.md files (read by both harnesses)
lib/                   shared procedural docs (deal schema, Playwright UX, research protocol)
scripts/lint-skills.sh frontmatter + lib-reference linter (also runs render-report smoke test)
scripts/render-report.py renders deals/<slug>/report.html from MEMO + artifacts (stdlib-only)
tests/lint/            linter test fixtures and runner
tests/pmf-signal/      pmf-signal preflight + helpers test fixtures
test/ledgerloop/       hackathon demo run (committed; legacy layout — see Demo section)
docs/superpowers/      design spec and implementation plan
deals/                 per-deal artifacts (gitignored)
openspec/              spec-driven change proposals (proposal/design/specs/tasks)
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

Run the pmf-signal preflight test suite:

```bash
bash tests/pmf-signal/run.sh
```

## License

MIT
