## 1. Prerequisite gate

- [ ] 1.1 Confirm `split-background-and-pmf-layers` is archived under `openspec/changes/archive/`
- [ ] 1.2 Confirm `fleet-runner-and-dashboard` is archived
- [ ] 1.3 Confirm `pmf-led-report` is archived
- [ ] 1.4 Confirm at least one release window has passed since the foundation shipped (subjective check; record the release tag in the PR description)
- [ ] 1.5 Confirm no internal stakeholder has flagged a blocker for removal in the past two weeks (post in shared channel before proceeding)

## 2. Audit references in-tree

- [ ] 2.1 `grep -r "dudu:diligence" --exclude-dir=openspec/changes/archive .` and produce a full reference list
- [ ] 2.2 `grep -r "dudu:market-problem" --exclude-dir=openspec/changes/archive .` and produce a full reference list
- [ ] 2.3 `grep -r "dudu:customer-discovery" --exclude-dir=openspec/changes/archive .` and produce a full reference list
- [ ] 2.4 Categorize hits: documentation (rewrite to layered names), test fixtures (rewrite to layered calls), code imports (should be zero — investigate any hits), comments (rewrite or delete)
- [ ] 2.5 Save the audit list as a comment on the PR for review before deletion

## 3. Documentation scrub

- [ ] 3.1 Update `README.md`: remove all references to deprecated names. Replace example invocations with layered calls.
- [ ] 3.2 Update `lib/deal.md`: remove deprecated names from any orchestration discussion.
- [ ] 3.3 Update `lib/research-protocol.md` if it references any deprecated name.
- [ ] 3.4 Update `lib/playwright-auth.md` if it references any deprecated name.
- [ ] 3.5 Update `CLAUDE.md` (if present) to drop references and update the "how to invoke" section.
- [ ] 3.6 Sweep `skills/*/SKILL.md` for any cross-reference to the deprecated names and rewrite.
- [ ] 3.7 Land the documentation scrub as a separate commit (easy review) before any code deletion.

## 4. Plugin manifest updates

- [ ] 4.1 Remove `diligence` skill entry from `.claude-plugin/plugin.json`
- [ ] 4.2 Remove `market-problem` skill entry from `.claude-plugin/plugin.json`
- [ ] 4.3 Remove `customer-discovery` skill entry from `.claude-plugin/plugin.json`
- [ ] 4.4 Repeat 4.1–4.3 for `.codex-plugin/plugin.json`
- [ ] 4.5 Clear any `deprecatedSkills` (or equivalent) field for the three names if present in plugin metadata
- [ ] 4.6 Validate plugin.json schemas (whatever validation step exists today)

## 5. Skill folder deletions

- [ ] 5.1 `git rm -r skills/diligence/`
- [ ] 5.2 `git rm -r skills/market-problem/`
- [ ] 5.3 `git rm -r skills/customer-discovery/`
- [ ] 5.4 Confirm `skills/` directory now contains only `background-check`, `competitive-landscape`, `customer-debrief`, `founder-check`, `idea-validation`, `market-context`, `market-sizing`, `pmf-signal`, `fleet-run`
- [ ] 5.5 Land the skill folder deletions as a single commit, separate from the docs scrub

## 6. Test fixture rewrites

- [ ] 6.1 Identify test files under `tests/` that exercise `dudu:diligence` end-to-end
- [ ] 6.2 Rewrite each as a sequenced layered call: `background-check` → `pmf-signal` → (optional `customer-debrief` if transcripts present) → MEMO + render
- [ ] 6.3 Identify and remove any test that asserts the deprecation wrapper printed a specific notice (those wrappers no longer exist)
- [ ] 6.4 Run the full test suite end-to-end on a fresh fixture deal
- [ ] 6.5 Run `scripts/lint-skills.sh` and confirm no warnings

## 7. Manual verification

- [ ] 7.1 Invoke `dudu:diligence` in a fresh Claude Code session and confirm "skill not found" (or equivalent) error — no resolution to the old wrapper
- [ ] 7.2 Repeat 7.1 for `dudu:market-problem` and `dudu:customer-discovery`
- [ ] 7.3 Run a full layered flow on `deals/ledgerloop` (or a fresh fixture deal) and confirm same outputs as before
- [ ] 7.4 Render `report.html` and `dashboard.html` (if fleet-runner-and-dashboard is in use) and confirm no broken sections

## 8. Release notes and rollout

- [ ] 8.1 Add a "Breaking changes" entry to the changelog: `dudu:diligence`, `dudu:market-problem`, `dudu:customer-discovery` are removed; use the layered skills directly
- [ ] 8.2 List the migration commands in the changelog (one-line each)
- [ ] 8.3 Run `openspec validate deprecate-diligence-orchestrator` and confirm valid
- [ ] 8.4 Tag the release with a version bump that reflects the breaking change
- [ ] 8.5 Post a short heads-up in any team channel where the plugin is used
