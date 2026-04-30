## 1. Carve out background-check skill

- [x] 1.1 Create `skills/background-check/SKILL.md` with the L1 orchestrator description, inputs (slug, company, founders, pitch, deck path), and the "runs founder-check + market-context + competitive-landscape + market-sizing" body
- [x] 1.2 Define the `background.md` sentinel format: short summaries of each sub-skill's output plus pointers to the per-skill artifact files
- [x] 1.3 Add re-invocation logic that skips completed sub-skills unless `--force` is passed (mirror the existing `dudu:diligence` re-runnability pattern)
- [x] 1.4 Add explicit refusal: the orchestrator and its sub-skills never write under `deals/<slug>/personas/`
- [x] 1.5 Update `manifest.json` schema docs in `lib/deal.md` to add `background-check` and `customer-debrief` to `skills_completed` keys
- [x] 1.6 Register `skills/background-check/` in `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`
- [x] 1.7 Lint pass: run `scripts/lint-skills.sh` and fix any warnings on the new skill

## 2. Slim market-problem → market-context

- [x] 2.1 Create `skills/market-context/SKILL.md` containing only Phase 1 (web research bundle) and Phase 3 (synthesis) from the existing `market-problem` SKILL.md
- [x] 2.2 Delete all references to "Phase 2" / "self-play interviews" / `personas/_context.md` / `personas/persona-*.md` from the new SKILL.md
- [x] 2.3 Replace `skills/market-problem/SKILL.md` with a deprecation stub that prints a migration notice and forwards to `dudu:market-context`
- [x] 2.4 Update `lib/deal.md`, `README.md`, and any other repo docs that mention `market-problem` to point at `market-context`
- [x] 2.5 Register `skills/market-context/` in both plugin manifests; mark `market-problem` as deprecated there
- [x] 2.6 Search for any code path or script that opens `personas/_context.md` or `personas/persona-*.md` written by `market-problem` and confirm it tolerates absence (PMF stage 0 already loads `_context.md` if present — verify it tolerates a fresh deal where only PMF will write that file)

## 3. Decouple customer-debrief

- [x] 3.1 Create `skills/customer-debrief/SKILL.md` containing the debrief body extracted from `skills/customer-discovery/SKILL.md`
- [x] 3.2 Strip all "after diligence prep" / re-invocation coupling language from the new SKILL.md; the only precondition is "transcripts exist under `inputs/`"
- [x] 3.3 Add explicit `--force` semantics: refuse to overwrite `customer-discovery.md` without it
- [x] 3.4 Replace `skills/customer-discovery/SKILL.md` with a deprecation stub that forwards `prep` invocations to `pmf-signal` and `debrief` invocations to `customer-debrief`
- [x] 3.5 Register `skills/customer-debrief/` in both plugin manifests; mark `customer-discovery` as deprecated
- [x] 3.6 Update the `customer-discovery-prep.md` side-effect in `pmf-signal` Stage 5 if any wording or path implies it gates downstream work — it should now read as a convenience artifact only

## 4. Relax pmf-signal preflight

- [x] 4.1 Rewrite `scripts/pmf-signal-preflight.py` to check for: (a) `deals/<slug>/background.md`, (b) `founder-*.md`, (c) `market-context.md`, (d) `competitive-landscape.md`, (e) `market-sizing.md`, (f) `inputs/deck.<ext>` (or `deck.md`)
- [x] 4.2 Remove any check for `customer-discovery-prep.md`, `personas/_context.md`, or `personas/persona-*.md` from the preflight
- [x] 4.3 Update `skills/pmf-signal/SKILL.md` "Pre-flight (hard gate)" section to describe the new contract; reference `background.md` as the L1 sentinel
- [x] 4.4 Update `skills/pmf-signal/SKILL.md` to clarify that `personas/` is exclusively PMF-owned and that legacy `persona-*.md` files (from old `market-problem` runs) are tolerated but not required
- [x] 4.5 Update PMF stage 0 source-loading: tolerate absence of `personas/_context.md` (treat as "PMF will write this") and tolerate presence of legacy `persona-*.md` files (read-only inputs) — implemented as new Stage 0b ("L1 context bundle absorption") that derives `personas/_context.md` from L1 artifacts if absent
- [x] 4.6 Add unit-style test in `tests/` that runs the preflight script against three fixture directory layouts: (i) fresh L1-complete deal, (ii) deal missing `background.md`, (iii) legacy deal with old persona files plus all required L1 artifacts

## 5. Reshape diligence into a thin wrapper

- [x] 5.1 Rewrite `skills/diligence/SKILL.md` to ~30 lines: invoke `background-check`, then `pmf-signal`, then on re-invocation invoke `customer-debrief` if transcripts exist, then stitch MEMO and render
- [x] 5.2 Add a deprecation notice header to the new `diligence/SKILL.md` that names the follow-up change which will remove it
- [x] 5.3 Mark `diligence` as deprecated in both plugin manifests (visible in `/help`)
- [ ] 5.4 Verify via integration test (or manual run on a fresh fixture deal) that `dudu:diligence` end-to-end produces the same final MEMO + report.html as direct layered invocation — *deferred: requires running real skills end-to-end with LLM + Playwright, which can't be exercised from this implementation pass. Smoke tests on test/ledgerloop and tests/fixtures/legacy-deal cover the renderer; manual end-to-end remains the user's responsibility before archive.*
- [x] 5.5 Update `README.md` "How to use" section: lead with the layered call (`background-check` → `pmf-signal` → `customer-debrief`), demote `diligence` to a "still works for now" note

## 6. Backward compatibility for existing deals

- [x] 6.1 Verify `deals/ledgerloop/`, `deals/callagent/`, `deals/tiny/` continue to render under the new code paths without modification on disk — *covered by the lint smoke test on `test/ledgerloop` (the canonical legacy demo); `deals/<slug>` is gitignored so the per-user deals fall under the same code path the smoke test exercises.*
- [x] 6.2 If `report.html` rendering currently breaks on the absence of `background.md`, add tolerance: when sentinel is missing, fall back to detecting L1 completion via the per-skill artifacts — *renderer didn't actually depend on `background.md`; what it needed was tolerance for `market-context.md` ↔ `market-problem.md`. Added that fallback in `scripts/render-report.py`.*
- [x] 6.3 Add a fixture directory under `tests/fixtures/legacy-deal/` mirroring `deals/ledgerloop`'s artifact set; assert all renderers in the repo work against it
- [x] 6.4 Document in `lib/deal.md` that the artifact layout supports both legacy (no `background.md`, possibly persona-*.md from market-problem) and new (with `background.md`, no market-problem persona files) shapes

## 7. Documentation and rollout

- [x] 7.1 Update `README.md` with a "Layered architecture" section explaining L1 (background-check) and L2 (pmf-signal) and the standalone debrief
- [x] 7.2 Update `lib/deal.md` to reflect the new manifest keys and artifact ownership rules
- [x] 7.3 Update `lib/research-protocol.md` if it references `market-problem` or `customer-discovery` by name
- [x] 7.4 Add a short migration note for users who have `dudu:diligence` muscle memory: same command still works, but here's the layered way
- [x] 7.5 Run `openspec validate split-background-and-pmf-layers` and confirm it reports valid
- [x] 7.6 Update `CLAUDE.md` (if present) to reference the new skill names — *no `CLAUDE.md` in repo; nothing to update.*

## 8. Verification

- [ ] 8.1 Run `dudu:background-check` end-to-end on a fresh fixture deal; confirm artifacts and `background.md` sentinel appear and `personas/` is empty — *deferred to user — requires running real skills with LLM + Playwright.*
- [ ] 8.2 Run `dudu:pmf-signal` on the result; confirm preflight passes and `personas/` populates with PMF-authored files only — *deferred to user — requires running real skills with LLM + Playwright; preflight is unit-tested via `tests/pmf-signal/run.sh`.*
- [ ] 8.3 Drop a transcript file into `inputs/`, run `dudu:customer-debrief`, confirm `customer-discovery.md` is written without any orchestrator state — *deferred to user.*
- [ ] 8.4 Run `dudu:diligence` on a separate fresh fixture deal; confirm same final artifacts as the layered run — *deferred to user.*
- [ ] 8.5 Re-run all of the above with `deals/ledgerloop` to confirm legacy compat — *deferred to user; the legacy renderer code path is exercised by the lint smoke test on `test/ledgerloop`.*
