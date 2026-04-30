---
name: market-problem
description: DEPRECATED — forwards to dudu:market-context. Persona self-play moved to dudu:pmf-signal. Stub kept for one release window.
---

# market-problem (deprecated)

> ⚠️ **Deprecated.** This skill is a thin compatibility wrapper. Its public-source context phases (1 and 3) live in `dudu:market-context`. Its old persona Phase 2 has been deleted — personas are now owned by `dudu:pmf-signal`. The wrapper will be removed by the `deprecate-diligence-orchestrator` change after one release of overlap.

## What to do when invoked

1. Print this deprecation notice to the user verbatim:

   > `dudu:market-problem` is deprecated. Use `dudu:market-context` for the public-source context bundle, and `dudu:pmf-signal` for the persona simulation. The `market-problem` name will be removed in a future release.

2. Forward the invocation to `dudu:market-context` with the same arguments (slug, company, product description, optional ICP, optional deck text, `--force` if supplied).

3. Do NOT generate persona files (`personas/_context.md`, `personas/persona-*.md`, `personas/round-*.md`). The Phase 2 self-play that produced those is gone. If the user explicitly asks for personas, point them at `dudu:pmf-signal`.

## Migration

| Old | New |
|---|---|
| `dudu:market-problem` (full Phases 1+2+3) | `dudu:market-context` for context + `dudu:pmf-signal` for personas |
| `personas/_context.md`, `persona-K.md`, `round-N.md` | PMF-authored `personas/_context.md`, `frames.yaml`, `seeds.yaml`, `aggregates.yaml`, `verdicts.yaml`, `rows/p-*.yaml` |

Existing deals (`deals/ledgerloop`, `deals/callagent`, `deals/tiny`) keep their legacy persona files on disk; those files are tolerated as read-only inputs by `dudu:pmf-signal`.
