## Context

The dudu plugin runs VC due-diligence on a single deal at a time. The foundation change `split-background-and-pmf-layers` carved the chain into a cheap public-source Layer 1 (`background-check`) and a deep persona-simulation Layer 2 (`pmf-signal`), with `customer-debrief` standalone. With those layers in place, the next blocker is fleet scale: a VC reviewing a batch wants to triage 20–40 startups quickly, then concentrate the expensive PMF simulation on the survivors.

Today, scaling means manual loops. There is no concurrency control, no per-deal failure isolation, no fleet-level state, and no cross-deal view. Per-deal HTML reports answer "how is *this* startup doing" — they cannot answer "which 5 of these 30 are worth a partner meeting next week."

This change introduces:

1. A `fleet-run` orchestrator skill that composes the foundation's layers across many deals.
2. A `render-dashboard.py` script that produces a sortable HTML matrix of fleet results.
3. A reserved `deals/_fleet/` directory holding fleet state and rendered output.

It does *not* introduce automation for customer-debrief at fleet scale (debrief is async and per-deal), MEMO stitching across deals, or any algorithmic change to the underlying skills.

## Goals / Non-Goals

**Goals:**

- One command to run L1 across N deals with a sensible concurrency cap.
- Default behavior makes the expensive layer (PMF) opt-in. The user picks which deals graduate from L1 to L2.
- Per-deal failure isolation: a single bad deck does not abort the fleet.
- A single rendered HTML view that lets a VC sort/filter the fleet by signal vectors and click through to per-deal reports.
- Backward compatibility with single-deal usage: `fleet-run --slug foo` is equivalent to a layered call on `foo`.
- Fleet state stored in exactly one place (`deals/_fleet/`) so the per-deal directories stay clean and uncoupled.

**Non-Goals:**

- No new persona-simulation, claim-ledger, or scoring logic. Fleet-run composes existing skills as black boxes.
- No automatic customer-debrief or MEMO stitching across the fleet. The dashboard tolerates partial state and renders "pending" cells.
- No new external dependencies. `render-dashboard.py` is stdlib Python; `fleet-run` is a SKILL.md plus the same Python harness used by the foundation.
- No customization layer for the dashboard (column order, theming, custom signal vectors). Fixed columns now; configurability is a later change if asked for.
- No retroactive fleet rendering of `deals/ledgerloop`, `deals/callagent`, `deals/tiny`. The dashboard works on whatever is on disk; nothing is migrated.

## Decisions

### Decision 1: Default mode is gate-then-deepen, not end-to-end

`fleet-run` runs `background-check` on every queued slug by default. PMF is **not** invoked unless the user explicitly opts in — either with `--all` (PMF on every deal) or by re-invoking `fleet-run --pmf <slug-list>` after reviewing the L1 dashboard.

**Why**: PMF is "the heaviest budget in the plugin" (`skills/pmf-signal/SKILL.md`). Running it across every deal in a 30-deal batch is a budget footgun — the user pays for deep simulation on companies they would have killed after reading the founder dossier. Gate-then-deepen mirrors how a VC actually triages: cheap public-source pass first, expensive simulation only on survivors.

**Alternative considered**: default to `--all` and let users add `--l1-only` to skip PMF. Rejected — the safe default for an expensive operation is "off." Power users can pass `--all` once they trust the budget.

**Alternative considered**: a "rolling" mode that runs L2 on a deal as soon as its L1 finishes, in parallel. Rejected — it removes the human gate, which is the whole point of the default. A future change can add this if there's demand.

### Decision 2: Concurrency cap is the primary budget control, token cap is secondary

`--concurrency N` (default `3`) controls how many sub-skill invocations run in parallel. `--max-tokens N` is an optional secondary cap that aborts the fleet when consumed tokens exceed the threshold.

**Why concurrency over tokens**: token consumption per deal varies wildly (a deal with a 2-page deck and one founder vs. a deal with a 40-page deck and four founders). Estimating token budget upfront is a guessing game. Concurrency is what users actually want to express: "run up to 3 at a time, never blow up my LLM bill." It maps directly to the rate-limit behavior they care about.

**Default of 3**: empirically picked. 1 is too slow for a 30-deal batch; 10 risks rate-limit thrash on a typical Claude API tier. 3 is the "obviously safe" middle that most users won't need to override. Documented in SKILL.md.

**Alternative considered**: no concurrency cap, rely on user to chunk the queue. Rejected — users will forget and fan out 30 calls in parallel. The cap belongs in the orchestrator, not in user discipline.

### Decision 3: Fleet input is `deals/_fleet/queue.txt`, with `--slugs` and auto-detect as overrides

The default input is a `deals/_fleet/queue.txt` file: one slug per line, blank lines and `#` comments ignored. If `--slugs a,b,c` is passed, that overrides the queue file. If neither is given and `--auto` is passed, every directory directly under `deals/` (excluding `_fleet` and any name starting with `_`) is enrolled.

**Why a file by default**: a queue file is editable, version-controllable, and survives shell history. CLI `--slugs` is convenient for a one-shot run but loses the record of "which fleet did I run last Tuesday."

**Why `_fleet` is reserved**: any directory beginning with `_` under `deals/` is reserved for fleet/system use. This keeps the namespace simple — slugs are kebab-case, system dirs are underscore-prefixed. Documented in `lib/deal.md` as part of this change.

**Why `--auto` is opt-in, not default**: a user who has 50 historical deals on disk but wants to run a fleet on the 8 new ones should not get 50 by default. Explicit > implicit when the cost is real money.

**Alternative considered**: a YAML config (`fleet.yml`) with per-deal options. Rejected — over-engineered for the v1 use case. A flat slug list does the job; per-deal overrides can be a flag pattern (`--pmf a,b` after the L1 pass).

### Decision 4: Dashboard is a derived view, not a stored truth

`render-dashboard.py` reads the fleet manifest plus per-deal artifacts (`founder-*.md`, `claim-ledger.yaml`, `market-sizing.md`, `MEMO.md` if present) and emits `deals/_fleet/dashboard.html`. The script is idempotent and re-runnable any time. It does not write any data file.

**Why derived**: the only "truth" is the per-deal artifacts. If we cache aggregated signals in a JSON, we now have two sources that can drift. A regenerable view is simpler.

**Tolerance for partial state**: when MEMO.md is missing for a deal, the recommendation-tilt column shows `pending`. When `claim-ledger.yaml` is missing, the verdict-count columns show `—`. The dashboard never errors on partial state; it shows what's there.

**Alternative considered**: emit a JSON sidecar alongside the HTML so other tools can consume the aggregated view. Rejected for now — YAGNI. Easy to add later if a real consumer appears.

### Decision 5: Per-deal failure is non-fatal and recorded in the fleet manifest

When a sub-skill invocation fails on deal `X`, fleet-run:

1. Captures stdout/stderr to `deals/_fleet/logs/<slug>.log` (per-deal, append-only).
2. Sets `deals/_fleet/manifest.json` `per_deal[X].status = "failed"` with `error_summary` and a pointer to the log path.
3. Does not propagate the failure. Other deals continue.
4. At fleet end, prints a summary: `28 complete, 2 failed: see _fleet/manifest.json`.

**Why non-fatal**: a single deal failing because someone uploaded a corrupted PDF should not waste the work already done on the other 29 deals. The user can re-run failed deals individually after fixing the input.

**Why a per-deal log file**: surfacing the right error message per slug at fleet end is hard to do well via stdout alone (interleaved output is unreadable). A log file per slug is the cleanest "drill into what went wrong" affordance.

**Alternative considered**: a single combined log with deal-tagged lines. Rejected — too noisy at concurrency 3+. Per-deal files mirror how the dashboard organizes the data.

### Decision 6: Single-slug behavior is identical to a layered call

`fleet-run --slug foo` (or a `queue.txt` with one line) runs exactly `background-check` on `foo`, then exits unless `--all` is passed. It is observably identical to invoking `dudu:background-check --slug foo` directly.

**Why this matters**: users should not need to mentally maintain two code paths ("for one deal use X, for many use Y"). One entry point, one mental model. The fleet runner happens to also work on a fleet of one.

**Implementation note**: there's no special-cased "single-slug" branch. Concurrency 3 with a 1-element queue is the same behavior as concurrency 3 with a 30-element queue.

### Decision 7: Dashboard columns are fixed and minimal

The v1 dashboard has these columns, in order:

1. **Slug** (link to per-deal `report.html`)
2. **Company name** (from manifest)
3. **Founder credibility** (max-of-founder-scores from `founder-*.md` "credibility:" front-matter, or `—` if missing)
4. **Claim ledger counts** (one cell with three small numbers: `S / C / P` for supports/contradicts/partial; pulled from `claim-ledger.yaml` verdict tallies)
5. **Contradictions** (count of red-flag rows from claim ledger)
6. **Market size band** (`small` / `medium` / `large` / `—` derived from `market-sizing.md` total)
7. **Recommendation tilt** (`pass` / `track` / `pursue` / `pending` from MEMO.md or `pending` if absent)
8. **Interview status** (`done` if `customer-discovery.md` exists, else `pending`)
9. **Last run** (timestamp from fleet manifest)

Sort by clicking column headers. No filtering, no per-cell drill-down beyond the slug link.

**Why fixed**: configurability is a tar pit. Pick the right defaults; let configurability be a later change if anyone asks. Every column maps to a concrete artifact field; nothing requires LLM inference at render time.

## Risks / Trade-offs

- **[Risk] Concurrency 3 might still rate-limit on lower API tiers.** → Mitigation: SKILL.md documents that users on lower tiers should pass `--concurrency 1`. The default is "safe-ish for most," not "safe for all."
- **[Risk] Per-deal failure logs accumulate without rotation.** → Mitigation: each fleet-run truncates logs from the previous run for slugs in the new queue (a rerun clears the old log). Cross-fleet log rotation is out of scope.
- **[Risk] Dashboard renders stale data if read while a fleet-run is mid-flight.** → Mitigation: dashboard reads only deals whose manifest status is `complete` or `failed`. Deals with status `running` or `pending` show `running…` / `—` and the dashboard footer notes "fleet in progress."
- **[Risk] `_fleet` reserved name collides with someone's actual deal slug.** → Mitigation: slugs are validated as kebab-case (no leading underscore). Documented in `lib/deal.md`. The fleet manifest creation refuses if any underscore-prefixed slug appears in the queue.
- **[Risk] Token cap is hard to estimate, so users will set it wrong and abort fleets early.** → Mitigation: `--max-tokens` is opt-in, not default. The default is "no token cap, only concurrency." The cap is for users who explicitly want a budget circuit-breaker.
- **[Trade-off] No "rolling" mode where L2 starts as soon as L1 finishes per deal.** Accepted: it would defeat the human gate. Re-evaluate if usage data shows users always pass `--all` anyway.
- **[Trade-off] No streaming dashboard updates during a run — the user must re-run the renderer to see fresh data.** Accepted: streaming HTML is significant complexity for a v1 view. Re-running `render-dashboard.py` is one command.

## Migration Plan

This change is additive. It introduces new files and a new top-level skill but modifies nothing about how `background-check`, `pmf-signal`, or `customer-debrief` work on a single deal. There is nothing to migrate.

1. Land this change with `fleet-run` registered in both plugin manifests and the dashboard renderer in `scripts/`.
2. README gains a "Running a fleet" section pointing at `dudu:fleet-run` with a typical invocation.
3. `lib/deal.md` documents the `_fleet` reserved directory and the kebab-case-no-leading-underscore slug rule.
4. Existing single-deal flows are unaffected. Users who never run a fleet see no change.

**Rollback**: delete `skills/fleet-run/`, `scripts/render-dashboard.py`, the `_fleet` entries in plugin manifests, and the README/lib doc additions. No data migration to undo because no per-deal artifact format changed.

## Open Questions

- **How is the queue specified when both `queue.txt` and `--slugs` exist?** Resolved: `--slugs` overrides; `--auto` overrides both; absence of all three is a hard error pointing the user at the three options. No silent defaults.
- **What does the recommendation-tilt column show before MEMO is stitched?** Resolved: `pending`. The dashboard tolerates partial state by design (Decision 4) — the renderer never errors on a missing artifact, it just shows the `pending` / `—` placeholder.
- **Does fleet-run write any per-deal artifact?** Resolved: no. Fleet state lives only in `deals/_fleet/`. Per-deal directories contain only what the sub-skills produce. This keeps deal directories portable and uncoupled from fleet runs (a deal can be moved or shared without dragging fleet metadata along).
- **Should the dashboard show a column for token spend per deal?** Punted to a later change. Token telemetry per sub-skill is not currently emitted in a structured way; adding it is a separate concern.
- **What happens if a slug in the queue has no `deals/<slug>/` directory yet?** Resolved: fleet-run treats this as a fatal-for-that-slug input error — manifest status `failed`, error message points the user at how to scaffold the deal directory. Other slugs continue.
