## Why

`split-background-and-pmf-layers` introduced three deprecation wrappers — `dudu:diligence`, `dudu:market-problem`, and `dudu:customer-discovery` — to give users one release of overlap between the old monolithic flow and the new layered shape. After the foundation, fleet runner, and PMF-led report changes have all shipped and the new shape has had real-world use, the wrappers earn their cost only in habit-preservation. They also actively confuse the surface area: two ways to do the same thing is the standard recipe for "which one is the canonical entry point?" support questions.

This change removes the wrappers, leaving the layered skills (`background-check`, `pmf-signal`, `customer-debrief`) as the only entry points.

## What Changes

- **REMOVED** `skills/diligence/` directory entirely. The thin compatibility wrapper introduced in the foundation change is deleted.
- **REMOVED** `skills/market-problem/` deprecation stub. (The original `market-problem` skill was already gutted in the foundation change; this removes the stub.)
- **REMOVED** `skills/customer-discovery/` deprecation stub. (Same: original was extracted to `customer-debrief` and `pmf-signal` Stage 5 in the foundation change; this removes the stub.)
- **BREAKING** for any user invoking `dudu:diligence`, `dudu:market-problem`, or `dudu:customer-discovery` — they must switch to the layered skills. Migration paths were already printed by the deprecation wrappers in the prior release.
- Plugin manifests (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`) drop the three skill registrations.
- Plugin metadata's `deprecatedSkills` field (or equivalent visible-in-`/help` flag) is cleared for the three names.
- README, `lib/deal.md`, and any other repo docs that still mention the deprecated names are scrubbed.
- Test fixtures and integration tests that drove the wrappers end-to-end are removed or rewritten to call the layered skills directly.

## Capabilities

### New Capabilities

None — this change is removal-only.

### Modified Capabilities

The foundation change `split-background-and-pmf-layers` specced not only the new layered skills but also the deprecation wrapper behavior on top of them. When that change is archived, the wrapper requirements become part of the main specs at `openspec/specs/`. This change removes those wrapper requirements.

- `market-context`: REMOVE the "Market-context replaces market-problem" requirement (the deprecation-wrapper contract). The core capability — public-source context production, persona-free output — remains intact.
- `customer-debrief`: REMOVE the "customer-discovery skill becomes a deprecation stub" requirement. The standalone-skill and no-orchestrator-coupling requirements remain intact.

The `dudu:diligence` thin wrapper has no corresponding spec entry in the foundation (it was always documented as transitional in `design.md`, not specced as a stable behavior), so its deletion has no spec delta.

## Impact

- **Skills affected**: `skills/diligence/` deleted; `skills/market-problem/` deleted; `skills/customer-discovery/` deleted. No new skill folders.
- **Plugin manifests**: three skill entries removed from each.
- **Scripts**: none affected directly. Verify no script unconditionally imports a deprecated skill name.
- **Documentation**: scrub `README.md`, `lib/deal.md`, `lib/research-protocol.md`, `CLAUDE.md`, and any session-level docs of references to the deprecated names. Update example invocations.
- **Existing deals**: zero impact on `deals/<slug>/` artifacts. The deprecation cycle didn't change artifact paths.
- **Test fixtures**: any test that asserts `dudu:diligence` works end-to-end is rewritten as a layered call (`background-check` then `pmf-signal` then `customer-debrief`) or removed.
- **Prerequisites**: this change MUST NOT ship until `split-background-and-pmf-layers`, `fleet-runner-and-dashboard`, and `pmf-led-report` have all merged and had at least one release window of soak time. Tasks include explicit prerequisite checks before any deletion.
- **Rollback**: trivially `git revert`. No data migration; no on-disk artifact changes; restoring the wrappers is a pure file restore.
