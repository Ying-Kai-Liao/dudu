---
name: customer-discovery
description: DEPRECATED — split into two new skills. The 'prep' half is now produced as a Stage-5 side effect of dudu:pmf-signal (still emitted at deals/<slug>/customer-discovery-prep.md). The 'debrief' half is now dudu:customer-debrief, runnable independently of any orchestrator. This stub exists for one release window and will be removed by the deprecate-diligence-orchestrator change.
---

# customer-discovery (deprecated)

> ⚠️ **Deprecated.** This skill split into two pieces in the layered architecture: prep is a side effect of `dudu:pmf-signal`, debrief is `dudu:customer-debrief`. The wrapper will be removed by the `deprecate-diligence-orchestrator` change after one release of overlap.

## What to do when invoked

Dispatch by sub-action argument:

### `prep`

1. Print this deprecation notice verbatim:

   > `dudu:customer-discovery prep` is deprecated. The prep artifact (`customer-discovery-prep.md`) is now produced as a Stage-5 side effect of `dudu:pmf-signal`. Run `dudu:pmf-signal` instead — it will emit the same prep file plus the much richer claim-ledger and warm-path outputs that prep alone never had.

2. If the L1 sentinel `deals/<slug>/background.md` exists, forward to `dudu:pmf-signal` with the same arguments. If it does not, exit with: `Run dudu:background-check first (it produces the L1 bundle that dudu:pmf-signal needs).`

3. Do NOT run the legacy prep flow.

### `debrief`

1. Print this deprecation notice verbatim:

   > `dudu:customer-discovery debrief` is deprecated. Use `dudu:customer-debrief` directly — it has no orchestrator coupling and runs whenever transcripts exist under `deals/<slug>/inputs/`.

2. Forward to `dudu:customer-debrief` with the same arguments (slug, `--force` if supplied).

### No sub-action specified

Ask which the user wants, then dispatch as above. Do NOT auto-detect based on artifact presence — that detection logic was the orchestrator coupling we just removed.

## Migration

| Old | New |
|---|---|
| `dudu:customer-discovery prep` | `dudu:pmf-signal` (prep is a side effect of Stage 5) |
| `dudu:customer-discovery debrief` | `dudu:customer-debrief` (standalone, no preconditions beyond transcripts) |
| `customer-discovery-prep.md` filename | unchanged — still written by `dudu:pmf-signal` |
| `customer-discovery.md` filename | unchanged — now written by `dudu:customer-debrief` |
