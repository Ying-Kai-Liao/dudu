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
| `dudu:auto-diligence` | full e2e | One trigger from a company name: auto-discovers founders + pitch, then runs L1 → L2 → optional callagent → debrief → MEMO + report.html (audio recordings embedded) | `deals/<slug>/report.html` |
| `dudu:background-check` | L1 orchestrator | Runs the four cheap sub-skills + writes the L1 sentinel | `deals/<slug>/background.md` |
| `dudu:founder-check` | L1 sub-skill | Public-web + LinkedIn dossier per founder | `founder-<name>.md` |
| `dudu:market-context` | L1 sub-skill | Public-source market & problem context (no personas) | `market-context.md` |
| `dudu:competitive-landscape` | L1 sub-skill | Competitor matrix, incumbent threat, moat analysis | `competitive-landscape.md` |
| `dudu:market-sizing` | L1 sub-skill | Bottom-up TAM ignoring founder claims | `market-sizing.md` |
| `dudu:pmf-signal` | **L2 (unique)** | Claim ledger × verdict matrix from N=15–200 persona simulation + cross-artifact + external evidence + warm-path outreach | `pmf-signal.md` + `outreach.md` + `personas/*` |
| `dudu:customer-debrief` | standalone | Synthesizes real interview transcripts into pain/WTP/objections | `customer-discovery.md` |
| `dudu:idea-validation` | optional | Compare 2–5 candidate ICPs head-to-head, recommend a wedge (idea-stage only) | `idea-validation.md` |
| `dudu:fleet-run` | fleet orchestrator | Compose L1 (and optionally L2) across many deals at once with concurrency cap, per-deal failure isolation, and a sortable HTML dashboard | `deals/_fleet/manifest.json` + `dashboard.html` |
| `dudu:diligence` | deprecated wrapper | Backward-compat: runs L1 + L2 + debrief + stitch + render | `MEMO.md` + `report.html` |
| `dudu:market-problem` | deprecated stub | Forwards to `dudu:market-context` for one release window | (forwards) |
| `dudu:customer-discovery` | deprecated stub | Forwards `prep` → pmf-signal, `debrief` → customer-debrief | (forwards) |

## Quick start: one trigger from a company name

```
dudu:auto-diligence on <Company Name>
```

`auto-diligence` resolves the slug, founders, and pitch from public sources, then runs the full chain (L1 → L2 → optional `callagent` screener calls → `customer-debrief` if interview material exists → MEMO + `report.html`). Pass `--auto-call` to drive the top-N warm-path candidates through `callagent` automatically; recordings under `deals/<slug>/calls/` are embedded as `<audio>` tags in `report.html`'s Customer Signal section. For deeper control, use the layered call below.

## Typical workflow (recommended layered call)

1. **Layer 1:** invoke `dudu:background-check` and answer prompts (slug, company, founders, pitch, optional deck). Produces the four L1 artifacts and `background.md` in ~10–25 minutes.
2. **Layer 2:** invoke `dudu:pmf-signal`. Reads the L1 bundle, runs the N=60 persona simulation by default, emits `pmf-signal.md` (claim ledger × verdict matrix), `outreach.md` (warm-path-prioritized candidates), and the legacy-shape `customer-discovery-prep.md`. ~20–60 minutes depending on `--n`.
3. **Real interviews:** read `pmf-signal.md` for the calibrated prior. Reach out to candidates from `outreach.md`. Run 5–10 real interviews. Save transcripts under `deals/<slug>/inputs/`.
4. **Debrief:** invoke `dudu:customer-debrief`. Synthesizes the transcripts into `customer-discovery.md` with pain/WTP/objections and contradictions vs. the calibrated prior.

Each skill can be invoked standalone. `idea-validation` is optional and not part of the orchestrated flow — use it before `market-context` when the wedge ICP is unclear.

### Migration note for users of `dudu:diligence`

The legacy `dudu:diligence` invocation still works — it runs the full chain end-to-end and stitches `MEMO.md` plus renders `report.html`. The wrapper prints a deprecation notice on every invocation and will be removed by the `deprecate-diligence-orchestrator` change. To migrate, use the layered call above and stitch the memo manually if you still want one. The render step (`python3 scripts/render-report.py deals/<slug>`) works on either layout.

## Running a fleet

When you're triaging a batch of startups (a YC AI-day list, a tagged inbox, a partner's referral pile), `dudu:fleet-run` composes Layer 1 across all of them at once and lets you pick which ones graduate to Layer 2. State lives entirely under `deals/_fleet/` — per-deal directories stay clean.

```bash
# 1. Gate-then-deepen (default): Layer 1 across every queued slug, no PMF yet.
dudu:fleet-run --slugs alpha,beta,gamma --concurrency 3

# 2. Render the cross-deal dashboard.
python3 scripts/render-dashboard.py
open deals/_fleet/dashboard.html

# 3. Pick the survivors and run Layer 2 only on them.
dudu:fleet-run --pmf alpha,gamma --concurrency 2

# 4. Re-render to see PMF columns fill in for those slugs.
python3 scripts/render-dashboard.py
```

Input options (priority order): `--slugs a,b,c` > `--auto` (every non-underscore directory under `deals/`) > `deals/_fleet/queue.txt` (one slug per line). If none is given, the run aborts with a clear error. Template: `docs/fleet-run/queue.txt.example` — copy to `deals/_fleet/queue.txt` and edit.

Other flags: `--all` runs L1+L2 in one pass (skip the gate); `--concurrency N` caps parallel sub-skill invocations (default 3, tighten to 1 on a starter API tier); `--max-tokens N` is an opt-in cumulative budget cap that stops enrolling new slugs when crossed (in-flight slugs finish; unstarted ones are marked `aborted-budget`).

Per-deal failure is non-fatal: a single bad deck does not abort the fleet. Failed slugs land with `status: failed` plus a per-slug log at `deals/_fleet/logs/<slug>.log`. Re-invoke fleet-run after fixing the input — completed slugs are skipped at the sub-skill level.

## What's NOT in v1

- Founder reference checks via your personal network (out of scope — that's a calendar task, not a skill task).
- Paid-API integrations (Crunchbase Pro, PitchBook).
- Auto-generated investment-committee slide decks.
- Multi-tenant deal sharing across a partnership.
- Hybrid VC-in-the-loop persona interviewing (deferred).
- Streaming dashboard updates during a fleet run — the renderer is one command, not a daemon.
- Customer-debrief automation across a fleet (debrief stays per-deal and async; the dashboard tolerates `interview: pending`).

## Repository layout

```
.claude-plugin/        Claude Code plugin + marketplace manifests
.codex-plugin/         Codex plugin manifest
.codex/INSTALL.md      Codex install guide (clone + symlink)
skills/                SKILL.md files (read by both harnesses)
lib/                   shared procedural docs (deal schema, Playwright UX, research protocol)
scripts/lint-skills.sh frontmatter + lib-reference linter (also runs render-report smoke test)
scripts/render-report.py renders deals/<slug>/report.html from PMF artifacts + MEMO (stdlib + PyYAML)
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

Run the renderer branch test suite:

```bash
bash tests/fixtures/pmf-led-report/run.sh
```

Run the fleet-run integration tests:

```bash
bash tests/fleet-run/run.sh
```

## Report layout

`scripts/render-report.py deals/<slug>` writes `<slug>/report.html`. The
renderer auto-detects which pmf-signal artifacts exist and picks one of
four layouts in priority order:

1. **full** — `pitch.yaml` + `personas/verdicts.yaml` both present.
   Leads with three ★ sections sourced from PMF: the calibrated claim
   ledger × verdict matrix (worst-news first), cross-artifact
   contradictions (verbatim quotes + file pointers), and the warm-path
   outreach top-10. Per-artifact files become collapsed drill-downs.
2. **pitch-only** — `pitch.yaml` exists but `verdicts.yaml` does not
   (PMF crashed mid-run). Renders the ledger with every verdict cell
   marked `pending`; replaces the contradictions section with a
   one-line "PMF run incomplete" note.
3. **markdown-fallback** — neither yaml is present, but `pmf-signal.md`
   is. Renders the markdown as a single ★ section in place of the
   structured layout. Stderr emits a warning naming the missing yaml.
4. **legacy** — none of the three exist. Renders the prior
   artifact-by-artifact layout (`MEMO.md` + per-skill files), unchanged
   from the pre-PMF behavior. `test/ledgerloop/` and any legacy demo
   deal continue to render under this branch.

Across all four layouts, the renderer auto-discovers audio files
under `deals/<slug>/calls/` (callagent recordings) and
`deals/<slug>/inputs/` (real-interview recordings) and embeds them as
`<audio controls>` tags in the Customer Signal section. Supported
extensions: `.mp3`, `.wav`, `.m4a`, `.webm`, `.ogg`. Audio uses
relative paths — `report.html` and the deal directory must travel
together.

## License

MIT
