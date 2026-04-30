---
name: fleet-run
description: Fleet-scale orchestrator. Runs dudu:background-check across many deals (concurrency-capped, default 3, per-deal failure isolated). dudu:pmf-signal runs only with --all or --pmf. State under deals/_fleet/.
---

# Fleet runner

Run the layered diligence chain across many deals at once. Default mode is **gate-then-deepen**: Layer 1 (`dudu:background-check`) on every queued slug, then a human picks which deals graduate to Layer 2 (`dudu:pmf-signal`) via a re-invocation. Read `lib/deal.md` first — fleet-run treats per-deal directories exactly as the layered skills do, and writes nothing else under them.

## What this skill IS and IS NOT

- IS: an orchestrator that composes `background-check` and (optionally) `pmf-signal` as black boxes across an N-deal queue, with bounded concurrency and per-deal failure isolation.
- IS: the sole owner of the `deals/_fleet/` namespace. All fleet state — manifest, logs, dashboard — lives there.
- IS NOT: a replacement for the layered single-deal skills. A queue of size 1 is observably identical to a direct layered call; the orchestrator adds nothing per-deal.
- IS NOT: an automation layer for `customer-debrief` or MEMO stitching. Those stay per-deal and async.
- IS NOT: an artifact author under `deals/<slug>/`. Fleet-run **never** writes any file under a per-deal directory beyond what its sub-skills (`background-check`, `pmf-signal`) already produce. If you ever feel tempted to drop a fleet-id, run-id, or status file inside `deals/<slug>/`, stop — it belongs in `deals/_fleet/manifest.json`.

## Inputs (one of three; in priority order)

1. `--slugs a,b,c` — explicit comma-separated slug list. **Highest priority.** Overrides everything else.
2. `--auto` — enroll every directory directly under `deals/` whose name does not start with an underscore (so `_fleet`, `_archive`, etc. are excluded).
3. `deals/_fleet/queue.txt` — one slug per line, blank lines and `#`-prefixed lines ignored. **Used only if neither `--slugs` nor `--auto` is passed.**

If none of the three is provided, the run is a hard error — the user must pick an input source explicitly.

### Modes

- **gate-then-deepen (default)**: run `background-check` on every queued slug. **Do not** run `pmf-signal` on any slug.
- `--all`: run `background-check` on every queued slug; for each slug whose `background-check` completed, run `pmf-signal` on it.
- `--pmf <slug-list>`: skip `background-check`; run `pmf-signal` only on the named slugs. Each slug must already have a complete L1 bundle (i.e. `background.md` exists). Slugs missing L1 are skipped with a per-slug error in the manifest.

`--all` and `--pmf` are mutually exclusive.

### Other flags

- `--concurrency N` — max parallel sub-skill invocations. Default `3`. On lower-tier API plans pass `--concurrency 1` to serialize.
- `--max-tokens N` — **opt-in** cumulative token cap across the whole fleet run. When the threshold is crossed, in-flight slugs finish but no new slug starts; unstarted slugs are marked `aborted-budget` in the manifest. Default behavior (no flag) is "concurrency cap only, no token cap."
- `--force` — propagate to every sub-skill invocation. Without `--force`, sub-skills skip slugs whose artifacts already exist.

### Why concurrency 3 by default

Empirically picked. `1` is too slow on a 30-deal batch; `10` risks rate-limit thrash on a typical Claude API tier. `3` is the "obviously safe" middle that most users won't need to override. Tighten to `1` on a starter tier; loosen to `5+` if you've validated your rate limits.

## Pre-flight (hard gate)

Run `python3 scripts/fleet-run.py init` with the resolved input source to:

1. Resolve the queue (from `--slugs` / `--auto` / `queue.txt` per priority above).
2. Validate every slug: kebab-case (lowercase, digits, hyphens), no leading underscore, non-empty. Any invalid slug **rejects the entire run** before any sub-skill is invoked.
3. For every queued slug, check `deals/<slug>/` exists. Slugs whose directory is missing are recorded as `failed` with a clear error in the manifest; the rest of the queue still runs.
4. Refuse to start if the resolved queue is empty (e.g. `--auto` in a workspace with no valid slug directories).
5. Create `deals/_fleet/manifest.json` with every queued slug pre-populated as `pending`. Truncate `deals/_fleet/logs/<slug>.log` for each queued slug.

Examples:

```bash
# Resolve from --slugs (highest priority)
python3 scripts/fleet-run.py init --slugs alpha,beta,gamma --concurrency 3 --mode gate

# Resolve from --auto
python3 scripts/fleet-run.py init --auto --concurrency 2 --mode all

# Resolve from queue file (default)
python3 scripts/fleet-run.py init --concurrency 3 --mode gate

# PMF-only re-invocation
python3 scripts/fleet-run.py init --slugs ledgerloop --concurrency 1 --mode pmf-only

# With opt-in token cap
python3 scripts/fleet-run.py init --slugs a,b,c --concurrency 2 --max-tokens 500000 --mode gate
```

The script prints the resolved queue, the mode, the concurrency cap, and the token cap (if set), then exits 0. Exit code 2 means the input was invalid (no input source, invalid slug, empty queue, missing directory for a `--pmf` slug whose L1 isn't complete) and you should surface stdout verbatim and stop.

## Worker pool and per-slug execution

Once `init` succeeds, walk the manifest's `per_deal` entries with status `pending` and dispatch sub-skill invocations under a worker pool bounded by `--concurrency N`. Concrete loop, per-slug:

1. **Budget check.** Run `python3 scripts/fleet-run.py budget-check`. Exit code 0 means OK; exit code 1 means the token cap has been crossed. On exit 1, mark every still-pending slug `aborted-budget` (`mark <slug> aborted-budget --error "fleet token cap exceeded"`) and break out of enrollment. Slugs already running continue; new slugs are not started.
2. **Mark `running`.** `python3 scripts/fleet-run.py mark <slug> running` — sets status and `started_at`.
3. **Invoke the sub-skill.** Either `dudu:background-check --slug <slug>` (gate / all modes) or `dudu:pmf-signal --slug <slug>` (all mode after L1 complete; pmf-only mode). Capture **all** stdout and stderr to `deals/_fleet/logs/<slug>.log` (truncate-then-append within a single fleet run; one log file per slug per run). Propagate `--force` if the user passed it.
4. **On success** (sub-skill exits clean and produces its sentinel artifact — `background.md` for L1, `pmf-signal.md` for L2): `python3 scripts/fleet-run.py mark <slug> complete`.
5. **On failure** (sub-skill error, missing input, exception): `python3 scripts/fleet-run.py mark <slug> failed --error "<short error summary>" --log-path "deals/_fleet/logs/<slug>.log"`. **Do not propagate the failure** — the rest of the queue continues.
6. **Record token usage** if the sub-skill reported it (best-effort): `python3 scripts/fleet-run.py add-tokens <count>`. If the sub-skill did not report tokens, do not call this.

### `--all` mode chaining

After every `background-check` completes for slug `X` (status `complete`), schedule `pmf-signal` on `X` through the same worker pool. **Do not** schedule `pmf-signal` on a slug whose `background-check` failed in this same run — that slug stays `failed` and is not retried at L2.

In `--all` mode the fleet manifest tracks two phases per slug under `per_deal[X]`: `background-check.status` and `pmf-signal.status`. The `mark` subcommand takes a `--phase` flag (`background-check` or `pmf-signal`) to disambiguate; default phase is `background-check`. See the manifest schema below.

### `--pmf <slug-list>` mode

`background-check` is not invoked. Each slug in `<slug-list>` is checked against `deals/<slug>/background.md`:
- Present → invoke `pmf-signal --slug <slug>`. Mark `pmf-signal` phase status as the run progresses.
- Absent → mark slug failed with error message `"L1 sentinel deals/<slug>/background.md not found — run dudu:background-check first."` Do not abort the rest of the queue.

### Single-slug equivalence

A queue of size 1 produces exactly the same per-deal artifacts as a direct layered call. The fleet runner adds **no** per-deal artifacts — only the entries in `deals/_fleet/manifest.json` and `deals/_fleet/logs/<slug>.log`. Test: compare `deals/foo/` output of `dudu:fleet-run --slugs foo` vs `dudu:background-check --slug foo` (and likewise for `--all` vs the L1+L2 layered call).

## Fleet manifest schema

`deals/_fleet/manifest.json`:

```json
{
  "fleet_run_id": "<ISO timestamp at init>",
  "started_at": "<ISO>",
  "finished_at": "<ISO or null>",
  "mode": "gate | all | pmf-only",
  "concurrency": 3,
  "max_tokens": null,
  "cumulative_tokens": 0,
  "input_source": "slugs | auto | queue-file",
  "queue": ["alpha", "beta", "gamma"],
  "per_deal": {
    "alpha": {
      "status": "pending | running | complete | failed | aborted-budget",
      "started_at": "<ISO or null>",
      "finished_at": "<ISO or null>",
      "error_summary": null,
      "log_path": "deals/_fleet/logs/alpha.log",
      "phases": {
        "background-check": {
          "status": "pending | running | complete | failed",
          "started_at": "<ISO or null>",
          "finished_at": "<ISO or null>"
        },
        "pmf-signal": {
          "status": "pending | running | complete | failed | skipped",
          "started_at": "<ISO or null>",
          "finished_at": "<ISO or null>"
        }
      }
    }
  }
}
```

The top-level `per_deal[X].status` reflects the **terminal** state across both phases: `complete` only if every applicable phase is complete; `failed` if any required phase failed; `aborted-budget` if the token cap stopped enrollment before this slug ran. `phases` is populated lazily — only the phases the run actually scheduled appear.

## End-of-run summary

After the worker pool drains, set `finished_at` and print a single summary line:

```
<N> complete, <M> failed, <K> aborted-budget — see deals/_fleet/manifest.json
```

Use `python3 scripts/fleet-run.py summary` to format this line consistently.

## Reserved namespace

`deals/_fleet/` is reserved for fleet state. Any directory under `deals/` whose name starts with `_` is not a valid deal slug. The pre-flight rejects any `_`-prefixed slug. See `lib/deal.md` for the canonical slug rules.

## Re-runnability

Fleet runs are not idempotent in aggregate (re-invoking schedules new sub-skill calls), but every individual sub-skill it invokes **is** idempotent under the existing `--force`-or-skip pattern. Practical consequence: re-running `dudu:fleet-run --slugs a,b,c` after a partial fleet does no harm — completed slugs are skipped at the sub-skill level (no `--force`), and only the previously-failed slugs run again. This is the simplest way to retry failed slugs after fixing their inputs.

## Dashboard render

After a fleet completes (or partway through, to monitor progress), run:

```bash
python3 scripts/render-dashboard.py
```

Writes `deals/_fleet/dashboard.html` — a sortable cross-deal HTML view with one row per enrolled slug. Self-contained (no network assets), idempotent, never mutates the manifest or any per-deal artifact. Tolerates partial state — slugs in `running` or `pending` show their lifecycle state instead of signal-vector data, and missing per-deal artifacts render as `pending` or `—`.

The dashboard is a **derived view**. The truth lives in per-deal artifacts and `deals/_fleet/manifest.json`; the HTML is regenerable any time.
