## Context

The dudu plugin is a Claude Code plugin that runs VC due-diligence workflows. Today its top-level skill `diligence` orchestrates a fixed seven-step chain:

```
founder-check ▸ market-problem ▸ competitive-landscape ▸ market-sizing
              ▸ pmf-signal ▸ [pause for interviews] ▸ customer-discovery debrief
              ▸ MEMO.md ▸ render-report.py
```

Three structural problems block the next phase of the product (running the workflow across many startups in parallel):

1. **Two persona conventions collide in `personas/`**. `market-problem` writes `_context.md` and `persona-*.md` from Phase 2 self-play. `pmf-signal` writes `rows/p-*.yaml` from a much deeper N=15–200 simulation. Both layers think they own the namespace.
2. **`pmf-signal` preflight is path-coupled to a specific orchestrator**. `scripts/pmf-signal-preflight.py` checks for hard-coded artifact paths produced by the existing diligence chain; it cannot accept an L1 bundle from any other source.
3. **`customer-discovery debrief` is welded into the orchestrator's re-invocation logic** (step 4 of `diligence/SKILL.md`). It can't run on its own when transcripts arrive at an arbitrary time.

This change separates the chain into a Layer 1 (cheap, public-source background check) and a Layer 2 (deep persona simulation), and decouples the debrief. It does not introduce a fleet runner, dashboard, or any new rendering — those are tracked as separate changes.

## Goals / Non-Goals

**Goals:**

- Define a clean Layer 1 ↔ Layer 2 contract: a single L1 bundle path that PMF accepts as input, with no embedded assumptions about *which* skill produced it.
- Move all persona ownership to PMF. L1 produces zero persona artifacts.
- Make `customer-debrief` runnable independently of any orchestrator.
- Preserve backward compatibility for the three existing deals (`deals/ledgerloop`, `deals/callagent`, `deals/tiny`) under their current layout.
- Keep the `diligence` skill working as a thin compatibility wrapper for one release so existing workflows don't break the day this lands.

**Non-Goals:**

- No fleet runner, dashboard renderer, or HTML restructure (separate changes).
- No retroactive migration of `deals/ledgerloop`, `deals/callagent`, `deals/tiny`. They keep their current artifact layout; only renderers that read them gain a tolerant code path.
- No change to the persona simulation algorithm itself, the claim-ledger schema, or the scoring math in PMF stages 0–5.
- No new external dependencies. Everything stays stdlib Python plus the existing `WebFetch` / Playwright tooling.

## Decisions

### Decision 1: L1 produces a single canonical bundle file

Layer 1 writes `deals/<slug>/background.md` plus the existing per-skill artifacts (`founder-*.md`, `market-context.md`, `competitive-landscape.md`, `market-sizing.md`). PMF's preflight checks for `background.md` as the L1-presence sentinel. If it's missing, PMF refuses to start.

**Why a single sentinel**: it lets us swap orchestrators (today's `diligence` wrapper, tomorrow's `fleet-run`, or a hand-written L1 produced by a human) without PMF caring how the bundle got there. The per-skill artifacts remain individually addressable for cross-artifact verification in PMF stage 3b.

**Alternative considered**: a `manifest.json` `skills_completed` flag check. Rejected because it couples PMF to a specific manifest schema; a file-presence sentinel is loose enough to survive future schema changes.

### Decision 2: `market-problem` is renamed to `market-context`, Phase 2 is deleted

The current `market-problem` skill has three phases: (1) web research bundle, (2) persona self-play interviews, (3) synthesis. We delete Phase 2 entirely. The skill keeps phases 1 and 3 and is renamed `market-context` to make its narrowed purpose obvious.

**Why delete rather than gate behind a flag**: the personas Phase 2 produces are shallow by construction (4–8 personas, no must-cover cells, no frame-aware sampling) and conflict in folder layout with the deep PMF simulation. Keeping a flag would preserve a footgun. Personas are a Layer 2 concern, full stop.

**Alternative considered**: keep Phase 2 but write to `personas/legacy/`. Rejected — it doubles the persona-rendering surface area in the renderer for no real benefit, and creates two persona conventions in one tree.

**Migration**: existing deals (`ledgerloop`, etc.) keep `personas/_context.md` and `personas/persona-*.md` files on disk. Renderers that read those paths gain an "if directory contains both legacy and PMF rows, render both" tolerance. Nothing is deleted from disk.

### Decision 3: `customer-debrief` is a sibling skill, not a sub-skill

Extract the debrief half of `customer-discovery` into a new top-level skill `customer-debrief`. Its preflight checks for `deals/<slug>/inputs/` containing at least one transcript file. It does *not* check for `customer-discovery-prep.md` or any orchestrator state.

**Why a sibling**: today the debrief runs only when re-invoked via `diligence`. In the layered model, transcripts can land at any time, on any deal, and the user wants to run the debrief without thinking about which orchestrator state triggered the prep. A standalone skill removes the temporal coupling.

**Alternative considered**: keep it inside `customer-discovery` with a sub-command. Rejected — sub-commands inside a skill are a weak boundary; users have to know which sub-command exists, and the orchestrator coupling tends to creep back in. A separate skill is the cleanest version.

### Decision 4: `diligence` becomes a thin wrapper, not deleted in this change

The `diligence` skill keeps its name and entry point, but its SKILL.md is rewritten to be ~30 lines: "call `background-check`, then `pmf-signal`, then if transcripts exist call `customer-debrief`, then stitch MEMO." All the actual workflow text moves into the sub-skills.

**Why not delete now**: there are bookmarks, scripts, and habits referring to `dudu:diligence`. Deleting in the same release that introduces the layered shape would create two simultaneous breaking changes for users. We deprecate first, delete in a follow-up.

**Alternative considered**: delete now and migrate users. Rejected — too disruptive for a refactor that doesn't add user-visible features yet.

### Decision 5: PMF preflight contract — file-presence, not file-path-list

Rewrite `scripts/pmf-signal-preflight.py` to check for the L1 sentinel (`background.md`) plus a minimal set of artifacts PMF actually needs as cross-artifact verification targets (`founder-*.md`, `market-context.md`, `competitive-landscape.md`, `market-sizing.md`). Drop the check for `customer-discovery-prep.md` — that artifact belongs to the debrief layer, not L2.

**Why minimal**: the preflight should fail fast and clearly. Today's preflight conflates "what L1 produces" with "what PMF strictly needs." Separating those keeps PMF runnable on a partial L1 (e.g., a deal where market-sizing was skipped) — PMF stage 0 can mark relevant claims as `flag: requires-data-room` instead of refusing to start.

**Alternative considered**: keep the strict check and add a `--skip-preflight` flag. Rejected — flags-over-fundamentals is exactly how today's coupling accumulated.

## Risks / Trade-offs

- **[Risk] Renaming `market-problem` → `market-context` breaks every CLAUDE.md, README, and habit that mentions the old name.** → Mitigation: keep `skills/market-problem/SKILL.md` as a deprecation stub for one release that simply forwards to `market-context`. Search-and-update README and lib/ docs. Tasks artifact tracks each rename touchpoint.
- **[Risk] Existing deals on disk have `personas/persona-*.md` from the deleted Phase 2.** → Mitigation: leave them. The renderer changes (separate change) handle both layouts. No deal data is rewritten.
- **[Risk] `diligence` wrapper drift — once it's a thin pass-through, behavior diverges if sub-skills evolve and the wrapper isn't updated.** → Mitigation: an integration test in `tests/` runs the wrapper end-to-end on a fixture deal and asserts the same final artifacts as direct invocation. Add as a task.
- **[Risk] PMF preflight relaxation accidentally lets PMF run on a totally empty deal directory.** → Mitigation: the preflight still requires `inputs/deck.<ext>` (or pasted pitch) AND the L1 sentinel `background.md`. Both conditions, not either.
- **[Trade-off] We accept that `customer-debrief` may run on transcripts whose corresponding prep was generated under the old monolithic `diligence` flow.** That's fine — the debrief just reads transcripts and synthesizes. It doesn't depend on prep state.
- **[Trade-off] Three new top-level skills (`background-check`, `market-context`, `customer-debrief`) plus the existing `pmf-signal` means more skills surface area for users to learn.** Acceptable: clearer naming beats fewer skills, and the `diligence` wrapper still gives a one-call entry point for users who don't want to compose layers themselves.

## Migration Plan

1. Land this change with the new skills in place AND the `diligence` wrapper still functional. Nothing breaks for existing users on day one.
2. Update `README.md` and `lib/deal.md` to describe the layered shape and recommend `background-check` + `pmf-signal` directly.
3. Mark `dudu:diligence` and `dudu:market-problem` as deprecated in plugin metadata (visible in `/help`).
4. After one release with no escalations, the follow-up change (`deprecate-diligence-orchestrator`) deletes both wrappers.

**Rollback**: this change adds new skills and rewrites two existing ones. If we need to revert, restore `skills/market-problem/SKILL.md` and `skills/customer-discovery/SKILL.md` from git history, restore the strict preflight script, delete the new skill folders. No data migration to undo because existing deals were never rewritten.

## Open Questions

- **Should `background-check` be a single skill that orchestrates the four sub-skills, or four sibling skills with no L1 orchestrator?** Leaning toward orchestrator — keeps the user's mental model "L1 = one thing" — but a fleet runner might prefer to call the four sub-skills directly. Resolved: ship as orchestrator now; fleet runner can bypass it later if needed.
- **Does `customer-debrief` need a manifest entry, or can it stay free-form?** Leaning toward manifest entry (`skills_completed.customer-debrief: <ISO timestamp>`) for symmetry with the other layers. Resolved in tasks.
- **What happens to the legacy `customer-discovery-prep.md` file?** PMF stage 5 currently emits it as a side effect. We keep that — it's a useful artifact for VCs even outside the orchestrator — but the file is no longer a preflight gate. Resolved: keep emitting, drop the preflight check.
