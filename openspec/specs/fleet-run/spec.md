# fleet-run Specification

## Purpose
Fleet-scale orchestrator that composes `background-check` (Layer 1) and optionally `pmf-signal` (Layer 2) across many deals at once. Provides bounded concurrency, per-deal failure isolation, opt-in token budget, and a derived sortable HTML dashboard. Default mode is gate-then-deepen (L1 only) so the heaviest layer never silently fans out across a 30-deal batch — the user picks which deals graduate to L2 by re-invoking with `--pmf <slug-list>`. Fleet state lives entirely under the reserved `deals/_fleet/` directory; per-deal directories stay portable and uncoupled from any specific fleet run.

## Requirements

### Requirement: Fleet-run orchestrates background-check across many deals
The system SHALL provide a `fleet-run` skill that, when invoked with a list of deal slugs, runs `background-check` on each slug to completion. By default it SHALL NOT invoke `pmf-signal` or `customer-debrief`. Each enrolled slug MUST correspond to an existing `deals/<slug>/` directory.

#### Scenario: Default run on a multi-slug queue
- **WHEN** `dudu:fleet-run` is invoked with three valid slugs queued in `deals/_fleet/queue.txt`
- **THEN** `background-check` runs on each slug
- **AND** `pmf-signal` is not invoked on any slug
- **AND** each slug ends with `deals/<slug>/background.md` written
- **AND** the fleet manifest records each slug's status as `complete`

#### Scenario: Slug with no deal directory is rejected as failed
- **WHEN** `dudu:fleet-run` is invoked with a queue containing a slug whose `deals/<slug>/` directory does not exist
- **THEN** that slug's status is recorded as `failed` in the fleet manifest
- **AND** an error message pointing the user at how to scaffold the deal directory is captured
- **AND** the rest of the queue continues to run

### Requirement: Fleet-run supports gate-then-deepen and end-to-end modes
The system SHALL default to gate-then-deepen mode, where only `background-check` runs across the queue. The user SHALL be able to opt into end-to-end mode with `--all`, which causes `pmf-signal` to run on every slug after its `background-check` completes. The user SHALL also be able to re-invoke `fleet-run --pmf <slug-list>` to run `pmf-signal` on a chosen subset after reviewing the L1 dashboard.

#### Scenario: Gate-then-deepen is the default
- **WHEN** `dudu:fleet-run` is invoked without `--all` or `--pmf`
- **THEN** only `background-check` runs on each slug
- **AND** no `personas/` files are written by the fleet runner

#### Scenario: --all runs pmf-signal on every slug
- **WHEN** `dudu:fleet-run --all` is invoked with a multi-slug queue
- **THEN** `background-check` runs on each slug
- **AND** for each slug whose `background-check` completed, `pmf-signal` is invoked
- **AND** failed `background-check` slugs do not have `pmf-signal` invoked on them

#### Scenario: --pmf runs pmf-signal on a chosen subset after L1
- **WHEN** the user has previously run `dudu:fleet-run` to completion and now invokes `dudu:fleet-run --pmf a,b`
- **THEN** `pmf-signal` is invoked only on slugs `a` and `b`
- **AND** `background-check` is not re-run on any slug
- **AND** the fleet manifest is updated with PMF status for `a` and `b`

### Requirement: Fleet-run enforces a concurrency cap as the primary budget control
The system SHALL accept a `--concurrency N` flag (default `3`) that bounds the number of sub-skill invocations running in parallel at any moment. This SHALL apply uniformly across `background-check` and `pmf-signal` invocations.

#### Scenario: Default concurrency is 3
- **WHEN** `dudu:fleet-run` is invoked on a 10-slug queue without `--concurrency`
- **THEN** at no point are more than 3 sub-skill invocations running in parallel

#### Scenario: User-specified concurrency overrides the default
- **WHEN** `dudu:fleet-run --concurrency 1` is invoked on a multi-slug queue
- **THEN** sub-skill invocations run strictly serially
- **AND** the next slug starts only after the previous one finishes

### Requirement: Fleet-run supports an optional token budget cap
The system SHALL accept an optional `--max-tokens N` flag. When set, the fleet runner SHALL track cumulative token consumption and abort enrollment of new slugs once the threshold is exceeded. Slugs already running SHALL be allowed to finish. Slugs not yet started SHALL be marked `aborted-budget` in the fleet manifest.

#### Scenario: --max-tokens is opt-in
- **WHEN** `dudu:fleet-run` is invoked without `--max-tokens`
- **THEN** no token cap is enforced
- **AND** the fleet runs to completion regardless of total tokens consumed

#### Scenario: Token budget exhausted mid-fleet
- **WHEN** `dudu:fleet-run --max-tokens 500000` is invoked and consumption crosses 500000 partway through a 20-slug queue
- **THEN** any in-flight slug is allowed to complete
- **AND** no new slug is started after the threshold is crossed
- **AND** unstarted slugs are recorded as `aborted-budget` in the fleet manifest

### Requirement: Per-deal failure is non-fatal to the fleet
The system SHALL isolate per-deal failures: when a sub-skill invocation fails on slug `X`, the fleet runner SHALL record `per_deal[X].status = "failed"` in the fleet manifest with an error summary and a per-slug log path, then continue running other slugs. The fleet SHALL NOT abort on a single-slug failure.

#### Scenario: One slug fails, others continue
- **WHEN** `dudu:fleet-run` runs on a 5-slug queue and the third slug's `background-check` raises an error
- **THEN** the third slug's status becomes `failed`
- **AND** an error summary and `deals/_fleet/logs/<slug>.log` path are captured in the manifest
- **AND** the fourth and fifth slugs continue to run
- **AND** the fleet end summary reports `4 complete, 1 failed`

#### Scenario: Per-slug log captures stdout and stderr
- **WHEN** a slug fails during fleet-run
- **THEN** the file `deals/_fleet/logs/<slug>.log` exists
- **AND** it contains the captured stdout and stderr from that slug's sub-skill invocation

### Requirement: Fleet input is specified via queue file, --slugs flag, or --auto
The system SHALL accept fleet input from one of three sources, in priority order: (1) the `--slugs a,b,c` CLI flag, (2) the `--auto` flag which enrolls every directory under `deals/` excluding any name starting with an underscore, (3) the file `deals/_fleet/queue.txt` (one slug per line, blank lines and `#` comments ignored). If none of the three is specified, the system SHALL exit with a clear error explaining all three options.

#### Scenario: --slugs takes priority over queue file
- **WHEN** both `deals/_fleet/queue.txt` exists with slugs `a, b, c` and `dudu:fleet-run --slugs x,y` is invoked
- **THEN** only `x` and `y` are enrolled
- **AND** the queue file is ignored for this run

#### Scenario: --auto enrolls every non-underscore directory
- **WHEN** `deals/` contains directories `alpha`, `beta`, `_fleet`, `_archive`
- **AND** `dudu:fleet-run --auto` is invoked
- **THEN** the enrolled queue is `alpha, beta`
- **AND** `_fleet` and `_archive` are not enrolled

#### Scenario: No input source given errors out
- **WHEN** `dudu:fleet-run` is invoked with no `--slugs`, no `--auto`, and no `deals/_fleet/queue.txt`
- **THEN** the skill exits with an error listing all three input options

### Requirement: Fleet state lives exclusively under deals/_fleet/
The system SHALL write all fleet-level state to `deals/_fleet/` and SHALL NOT write any new artifact under per-deal directories beyond what the sub-skills (`background-check`, `pmf-signal`) already produce. The `deals/_fleet/` directory is reserved; slugs starting with an underscore are not valid deal names.

#### Scenario: Fleet state is contained
- **WHEN** `dudu:fleet-run` completes a run on slugs `alpha` and `beta`
- **THEN** `deals/_fleet/manifest.json` and `deals/_fleet/logs/` exist
- **AND** the only files written under `deals/alpha/` and `deals/beta/` are those produced by `background-check` (and `pmf-signal` if invoked)
- **AND** no file under `deals/alpha/` or `deals/beta/` references the fleet manifest

#### Scenario: Underscore-prefixed slug is rejected
- **WHEN** `dudu:fleet-run --slugs _archive,beta` is invoked
- **THEN** the skill exits with an error stating that slugs cannot start with an underscore
- **AND** no run is started

### Requirement: Fleet manifest tracks per-deal status, mode, concurrency, and budget
The system SHALL maintain `deals/_fleet/manifest.json` with at minimum: list of enrolled slugs, mode (`gate` / `all` / `pmf-only`), concurrency cap, optional max-tokens cap, cumulative token consumption (if tracked), and a per-deal entry containing slug, status (`pending` / `running` / `complete` / `failed` / `aborted-budget`), timestamps for `started_at` and `finished_at`, error summary if any, and log path if any.

#### Scenario: Manifest reflects mode and caps
- **WHEN** `dudu:fleet-run --concurrency 2 --max-tokens 250000` is invoked
- **THEN** `deals/_fleet/manifest.json` records `mode`, `concurrency: 2`, `max_tokens: 250000`

#### Scenario: Manifest reflects per-deal lifecycle
- **WHEN** a fleet run completes
- **THEN** every enrolled slug has a `per_deal` entry with `status` set to a terminal value (`complete`, `failed`, or `aborted-budget`)
- **AND** entries for completed slugs include both `started_at` and `finished_at` ISO timestamps

### Requirement: Single-slug invocation is observably equivalent to a layered call
The system SHALL behave identically when `fleet-run` is invoked with a single slug as when `background-check` (and optionally `pmf-signal`) is invoked directly on that slug. The fleet runner SHALL NOT add or omit any per-deal artifact relative to the layered call.

#### Scenario: Single-slug L1 run produces the same per-deal artifacts
- **WHEN** `dudu:fleet-run --slugs foo` is invoked on a fresh deal `foo`
- **AND** separately, `dudu:background-check --slug foo` is invoked on an equivalent fresh deal
- **THEN** both runs produce the same set of files under `deals/foo/`
- **AND** the only additional state from the fleet run is under `deals/_fleet/`

#### Scenario: Single-slug --all run produces the same per-deal artifacts as layered L1+L2
- **WHEN** `dudu:fleet-run --slugs foo --all` is invoked
- **AND** separately, `dudu:background-check --slug foo` followed by `dudu:pmf-signal --slug foo` is invoked
- **THEN** both runs produce the same set of files under `deals/foo/`

### Requirement: Dashboard renders a sortable cross-deal HTML view
The system SHALL provide `scripts/render-dashboard.py` that reads `deals/_fleet/manifest.json` and per-deal artifacts, and writes a self-contained HTML file to `deals/_fleet/dashboard.html`. The HTML SHALL contain one row per enrolled slug and SHALL be sortable by clicking column headers. The script SHALL use only Python standard library and SHALL NOT depend on any network call at render time.

#### Scenario: Dashboard contains the fixed columns
- **WHEN** `python scripts/render-dashboard.py` is run after a fleet completes
- **THEN** `deals/_fleet/dashboard.html` exists
- **AND** it contains columns for slug, company name, founder credibility, claim ledger counts (supports/contradicts/partial), contradiction count, market size band, recommendation tilt, interview status, and last run timestamp

#### Scenario: Slug column links to the per-deal report
- **WHEN** the dashboard is rendered
- **THEN** the slug cell in each row is a hyperlink to that slug's `report.html`
- **AND** clicking it opens the per-deal report

#### Scenario: Columns are sortable client-side
- **WHEN** a user clicks a column header in the rendered dashboard
- **THEN** the rows reorder by that column's value
- **AND** no network request is made

### Requirement: Dashboard tolerates partial state
The system SHALL render the dashboard for any combination of present and missing per-deal artifacts. When an artifact required by a column is missing for a deal, the system SHALL render a placeholder (`pending` for downstream-stitch artifacts like MEMO, `—` for missing data) and SHALL NOT raise an error.

#### Scenario: Missing MEMO renders pending recommendation tilt
- **WHEN** the dashboard is rendered for a deal whose `MEMO.md` does not exist
- **THEN** the recommendation-tilt cell shows `pending`
- **AND** the row still renders fully

#### Scenario: Missing claim-ledger renders dash placeholders
- **WHEN** the dashboard is rendered for a deal that completed `background-check` but not `pmf-signal`
- **THEN** the claim-ledger and contradiction-count cells show `—`
- **AND** the row still renders fully

#### Scenario: Missing customer-discovery renders pending interview status
- **WHEN** the dashboard is rendered for a deal whose `customer-discovery.md` does not exist
- **THEN** the interview-status cell shows `pending`

### Requirement: Dashboard is a derived view with no stored truth
The system SHALL treat `deals/_fleet/dashboard.html` as a regenerable artifact. The render script SHALL NOT write any data file beyond the HTML, and SHALL NOT mutate the fleet manifest or any per-deal artifact.

#### Scenario: Re-rendering does not change manifest or per-deal state
- **WHEN** `python scripts/render-dashboard.py` is run twice in succession with no fleet activity in between
- **THEN** the second run rewrites `dashboard.html` with identical content
- **AND** `deals/_fleet/manifest.json` is byte-identical before and after each render
- **AND** no file under any `deals/<slug>/` directory is modified by the renderer

#### Scenario: Renderer runs while fleet is in progress
- **WHEN** the renderer is invoked while a fleet run is mid-flight
- **THEN** rows for slugs whose status is `running` or `pending` show their lifecycle state in place of the signal-vector data
- **AND** the dashboard footer notes that the fleet is in progress
- **AND** the renderer does not block waiting for the fleet to finish
