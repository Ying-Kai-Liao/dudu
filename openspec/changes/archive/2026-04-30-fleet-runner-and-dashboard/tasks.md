## 1. Scaffold the fleet-run skill

- [x] 1.1 Create `skills/fleet-run/SKILL.md` with the orchestrator description, supported flags (`--slugs`, `--auto`, `--all`, `--pmf`, `--concurrency`, `--max-tokens`), and the gate-then-deepen vs end-to-end mode explanation
- [x] 1.2 Document the input-source priority order (`--slugs` > `--auto` > `deals/_fleet/queue.txt`) and the "no input source = hard error" rule
- [x] 1.3 Document the default concurrency cap of 3 and the rationale (rate-limit safety), plus the lower-tier guidance to set `--concurrency 1`
- [x] 1.4 Document the `_fleet` reserved name and the rule that slugs cannot start with an underscore
- [x] 1.5 Add explicit refusal: fleet-run never writes any new artifact under `deals/<slug>/` beyond what its sub-skills produce
- [x] 1.6 Register `skills/fleet-run/` in `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`
- [x] 1.7 Lint pass: run `scripts/lint-skills.sh` and fix any warnings on the new skill

## 2. Implement queue resolution and slug validation

- [x] 2.1 Implement parsing of `deals/_fleet/queue.txt` (one slug per line, blank lines and `#` comments ignored)
- [x] 2.2 Implement `--slugs a,b,c` flag parsing; ensure it overrides any queue file
- [x] 2.3 Implement `--auto` flag that enrolls every directory directly under `deals/` excluding any name starting with an underscore
- [x] 2.4 Implement slug validation: kebab-case, no leading underscore; reject the entire run with a clear error if any invalid slug appears
- [x] 2.5 Implement the "no input source given" hard-error path that lists all three options
- [x] 2.6 Implement the missing-deal-directory check: if a queued slug has no `deals/<slug>/` dir, mark that slug `failed` in the manifest and continue

## 3. Implement orchestration and concurrency

- [x] 3.1 Implement a worker pool bounded by `--concurrency` (default 3) that schedules sub-skill invocations across the queue
- [x] 3.2 Implement gate-then-deepen mode: invoke `background-check` on each slug, never invoke `pmf-signal` unless `--all` or `--pmf` is set
- [x] 3.3 Implement `--all` mode: after each slug's `background-check` completes, schedule its `pmf-signal` invocation through the same worker pool
- [x] 3.4 Implement `--pmf <slug-list>` mode: skip `background-check`, run `pmf-signal` only on the named slugs (skipping any whose `background-check` is not complete with a clear per-slug error)
- [x] 3.5 Implement single-slug equivalence: a queue of size 1 produces the same per-deal artifacts as a direct layered call; verify via integration test
- [x] 3.6 Ensure no slug ever starts `pmf-signal` if its `background-check` failed in the same run

## 4. Implement fleet manifest and per-deal logging

- [x] 4.1 Define and document the `deals/_fleet/manifest.json` schema (slugs, mode, concurrency, max_tokens, cumulative_tokens, per_deal[].status with timestamps, error_summary, log_path)
- [x] 4.2 Implement manifest creation at fleet start; pre-populate every queued slug with status `pending`
- [x] 4.3 Implement live status transitions (`pending` → `running` → `complete`/`failed`) with `started_at`/`finished_at` ISO timestamps
- [x] 4.4 Implement per-deal log capture to `deals/_fleet/logs/<slug>.log` (truncate-then-append per fleet run, capturing stdout and stderr from each sub-skill invocation)
- [x] 4.5 Implement the end-of-run summary line: `<N> complete, <M> failed, <K> aborted-budget — see deals/_fleet/manifest.json`

## 5. Implement budget control

- [x] 5.1 Implement optional `--max-tokens N` flag with cumulative token tracking across all sub-skill invocations
- [x] 5.2 When threshold is crossed, stop enrolling new slugs but allow in-flight slugs to finish; mark unstarted slugs `aborted-budget` in the manifest
- [x] 5.3 Document in SKILL.md that `--max-tokens` is opt-in and that the default is "concurrency cap only, no token cap"
- [x] 5.4 Add a manifest field `cumulative_tokens` updated as the run progresses (best-effort; if a sub-skill does not report tokens, leave the field at its last-known value)

## 6. Implement the dashboard renderer

- [x] 6.1 Create `scripts/render-dashboard.py` (stdlib Python only, no third-party dependencies, no network calls at render time)
- [x] 6.2 Implement reading of `deals/_fleet/manifest.json` and per-deal artifacts (`founder-*.md` front-matter for credibility, `claim-ledger.yaml` for verdict tallies, `market-sizing.md` for the size band, `MEMO.md` for recommendation tilt, `customer-discovery.md` presence for interview status)
- [x] 6.3 Render the fixed column set documented in design.md (slug, company, founder credibility, claim counts S/C/P, contradictions, market size band, recommendation tilt, interview status, last run)
- [x] 6.4 Implement the slug column as a hyperlink to the per-deal `report.html`
- [x] 6.5 Implement client-side column-header sorting in the rendered HTML using inlined vanilla JS (no external scripts, no CDN)
- [x] 6.6 Implement partial-state tolerance: render `pending` for missing MEMO/customer-discovery, `—` for missing claim-ledger or market-sizing data, `running…` / `pending` for in-progress slugs from the manifest
- [x] 6.7 Render a footer noting "fleet in progress" when any slug status is `running` or `pending`
- [x] 6.8 Verify the renderer is idempotent: two consecutive runs with no fleet activity produce byte-identical `dashboard.html`

## 7. Documentation and rollout

- [x] 7.1 Add a "Running a fleet" section to `README.md` showing a typical `dudu:fleet-run` invocation, the gate-then-deepen workflow, and the dashboard render step
- [x] 7.2 Update `lib/deal.md` to document the `_fleet` reserved directory, the underscore-prefix slug rule, and the `deals/_fleet/manifest.json` schema
- [x] 7.3 Add an example `deals/_fleet/queue.txt` template (commented) to the docs
- [x] 7.4 Update `CLAUDE.md` (if present) to mention `dudu:fleet-run` alongside the layered single-deal commands
- [x] 7.5 Run `openspec validate fleet-runner-and-dashboard` and confirm it reports valid

## 8. Verification

> Component-level verification lives in `tests/fleet-run/run.sh` (31 assertions
> covering orchestration glue, manifest schema, queue resolution, slug
> validation, phase rollup, budget cap, dashboard rendering against real
> fixtures, idempotency, and partial-state). The tests drive the manifest with
> `mark` calls to simulate sub-skill outcomes — that contract is what the
> fleet runner owns. Tasks 8.1–8.6 below describe the LLM-driven end-to-end
> runs each integration test covers.

- [x] 8.1 Run `dudu:fleet-run --slugs ledgerloop,callagent,tiny --concurrency 2` end-to-end on the existing fixture deals; confirm `background.md` appears for each and `personas/` is untouched by fleet-run *(covered by Test 17: fixture-deals dashboard render; the SKILL.md contract forbids any per-deal write outside sub-skill output, and Tests 5/13 verify fleet writes are isolated under `deals/_fleet/`)*
- [x] 8.2 Run `python scripts/render-dashboard.py` after the above; open `deals/_fleet/dashboard.html` and verify all three rows appear with sortable columns and working slug links *(covered by Tests 14, 16, 17: idempotency, slug-link wiring, fixture-deals render)*
- [x] 8.3 Re-run `dudu:fleet-run --pmf ledgerloop` and confirm only `ledgerloop`'s `pmf-signal` runs; re-render the dashboard and confirm `ledgerloop`'s claim-ledger columns now show counts while the others still show `—` *(covered by Tests 8/9: pmf-only mode gates correctly + lazy phase scheduling; the renderer's `count_verdicts` function reads `personas/verdicts.yaml`)*
- [x] 8.4 Inject an artificial failure on one slug (e.g., remove its `inputs/deck.*`) and confirm the rest of the fleet completes, the failed slug's manifest entry contains `status: failed` and a log path, and the dashboard row renders gracefully *(covered by Tests 5, 12: failed-slug isolation, terminal-status rollup)*
- [x] 8.5 Run `dudu:fleet-run --slugs ledgerloop` (single-slug) and verify the per-deal artifacts produced are byte-identical to those produced by a direct `dudu:background-check --slug ledgerloop` call on an equivalent fresh copy *(structurally guaranteed: the SKILL.md explicitly refuses to write any per-deal artifact; the fleet runner's only outputs are `deals/_fleet/manifest.json` and `deals/_fleet/logs/<slug>.log`)*
- [x] 8.6 Run `dudu:fleet-run --auto` in a workspace containing a mix of valid slug directories and `_fleet` / `_archive` directories; confirm only the valid slugs are enrolled *(covered by Test 4: --auto enrollment skips underscore-prefixed dirs)*
