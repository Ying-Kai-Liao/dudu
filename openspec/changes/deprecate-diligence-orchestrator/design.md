## Context

After the foundation change `split-background-and-pmf-layers` lands, three skills exist purely to keep old habits working:

| Skill | What it does after the foundation lands | Why it exists |
|---|---|---|
| `dudu:diligence` | Thin pass-through: calls `background-check` → `pmf-signal` → `customer-debrief` (when transcripts present) → MEMO + render | One-call entry point for users who don't want to compose layers |
| `dudu:market-problem` | Forwards to `dudu:market-context` after printing a deprecation notice | Old name in habits, README, and CLAUDE.md |
| `dudu:customer-discovery` | Forwards `prep` → `pmf-signal`, `debrief` → `customer-debrief` after deprecation notice | Old name; behavior was split between two skills in the foundation |

These three were always temporary. The foundation change explicitly named this follow-up as the change that would remove them. This is that change.

The work itself is mechanical (delete three folders, scrub docs, drop manifest entries). The interesting question is *when*, not *how* — see the prerequisite gate below.

## Goals / Non-Goals

**Goals:**

- Remove all three deprecation surfaces so the plugin presents a single coherent skill graph.
- Force any remaining consumers onto the layered skills via a clear breaking-change boundary.
- Keep on-disk deal artifacts untouched. Removing wrappers must not require any deal-data migration.

**Non-Goals:**

- No further restructuring of the layered skills themselves (`background-check`, `pmf-signal`, `customer-debrief`, `market-context`).
- No changes to the rendering pipeline (`render-report.py`, `render-dashboard.py`).
- No new specs. This change does not add or modify capability requirements.
- No "soft" removal (e.g., keeping wrappers but printing louder warnings). The whole point is hard removal.

## Decisions

### Decision 1: Hard removal, not soft deprecation

Delete the three skill folders outright. Do not replace them with louder warnings, error stubs, or anything that pretends the names still resolve.

**Why**: a deprecation cycle that doesn't end is a permanent maintenance tax. The foundation change *was* the soft cycle. This change is the hard cut. Leaving "error stubs" creates a third state ("the skill exists but always fails") which is worse than "the skill doesn't exist."

**Alternative considered**: keep skill folders with a SKILL.md that contains only an error message pointing at the new name. Rejected — it inflates the plugin's skill count in `/help`, confuses LLM agents that try to invoke deprecated names, and never gets cleaned up.

### Decision 2: Prerequisite gate is enforced via task checklist, not tooling

Before any deletion task runs, the implementer MUST verify:

1. `split-background-and-pmf-layers` is archived (in `openspec/changes/archive/`).
2. `fleet-runner-and-dashboard` is archived.
3. `pmf-led-report` is archived.
4. At least one release window has passed since the foundation shipped.

The check is the first task in `tasks.md`. There is no automation gate (e.g., a script that refuses to run if prerequisites aren't met) — adding one would be over-engineering for a four-step manual check.

**Why**: this change is not urgent and runs once. Building a prerequisite-checker script for one execution is more code than the change itself.

**Alternative considered**: a `scripts/check-deprecation-readiness.sh` that verifies archive state. Rejected — only useful once.

### Decision 3: No spec deltas

`openspec/specs/` does not (and will not) contain entries for `diligence`, `market-problem`, or `customer-discovery`. The foundation change introduced specs only for the *new* layered skills. The deprecated skills were never specced.

Consequence: this change has no `specs/` directory in its OpenSpec change folder. The change is structured as proposal + design + tasks only.

**Why**: there are no requirements to remove because there were never any requirements written. The OpenSpec workflow tolerates spec-less changes when the work is purely about file removal and documentation hygiene.

**Alternative considered**: write retroactive removal-only spec deltas just to have something in `specs/`. Rejected as ceremony with no information content.

### Decision 4: Documentation scrub is exhaustive, not minimal

The tasks artifact lists every file known to mention the deprecated names: `README.md`, `lib/deal.md`, `lib/research-protocol.md`, `lib/playwright-auth.md`, `CLAUDE.md` (if present), and a grep sweep over `skills/*/SKILL.md` for cross-references. The goal is zero remaining mentions of `dudu:diligence`, `dudu:market-problem`, or `dudu:customer-discovery` in the repo after this change lands.

**Why**: leaving even one stale reference creates the "but the README says I can use it!" support question. Better to scrub once thoroughly.

## Risks / Trade-offs

- **[Risk] A user has scripts/automation calling `dudu:diligence` directly.** → Mitigation: the foundation change's deprecation wrappers printed migration messages on every invocation for one full release window. Anyone running the wrapper saw the new commands at least once. We accept that this still breaks unattended CI scripts that nobody read the output of.
- **[Risk] An LLM agent (e.g., another Claude Code session) has memorized `dudu:diligence` and tries to invoke it.** → Mitigation: skill name will resolve to "skill not found" after deletion, which is a clean failure. The agent can re-read the plugin's skill list.
- **[Risk] An existing test fixture references the deprecated names.** → Mitigation: tasks include a grep sweep over `tests/` to find and rewrite or delete affected fixtures.
- **[Risk] A future onboarding doc someone wrote out-of-tree (a Notion page, a Slack message) still says "run dudu:diligence".** → Out of scope. Can't scrub everything outside the repo. Documented as a known limitation.
- **[Trade-off] Hard removal is uncompromising. Some users will be annoyed on the day they upgrade.** Acceptable: the alternative is permanent dual-API surface area, which is worse over the long run.

## Migration Plan

1. Verify all three prerequisite changes are archived.
2. Search the repo for every reference to the three deprecated names — produce a full list before any deletion.
3. Scrub documentation references first (no removal of skill code yet). Land docs as a separate commit so they're easy to review.
4. Delete the three skill folders. Update plugin manifests in the same commit.
5. Rewrite or delete affected tests.
6. Run the lint script and the full test suite.
7. Manually invoke `dudu:diligence` on a fixture deal — confirm it resolves to "skill not found" cleanly.
8. Update the changelog/release notes with the breaking-change boundary clearly called out.

**Rollback**: `git revert` of the deletion commit. Nothing on disk in any deal directory was touched, so a revert restores full functionality with no data migration.

## Open Questions

- **Should this change ship with a "final reminder" release that prints an even louder warning before this PR merges?** Resolved: no. The foundation change already printed deprecation notices for an entire release window. Doubling down with a second warning release is process theater.
- **Does the README need a "deprecated skills" section explaining the historical naming?** Resolved: no. Once the wrappers are gone, the README points at the layered skills and that's the canonical surface. Old git history is the source of truth for what was deprecated when.
- **What about the dudu plugin's own skill index page (if any)?** Resolved: handled by the documentation scrub task. There's no dedicated skill index file beyond plugin.json.
