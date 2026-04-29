# Deal directory

A "deal" is one company being evaluated. Every dudu skill writes its output under `deals/<slug>/` in the user's current working directory, never anywhere else.

## Slug

Kebab-case, lowercase, derived from the company name.
- "Acme Corp" → `acme`
- "Twenty-Three Capital" → `twenty-three`

The slug is supplied once by an orchestrator (e.g. `dudu:background-check` or the deprecated `dudu:diligence` wrapper) and reused by every sub-skill in that deal.

## Layered architecture

The plugin is organized as two cleanly composable layers plus a standalone debrief skill:

- **Layer 1 — `dudu:background-check`** (cheap, public-source): orchestrates `founder-check`, `market-context`, `competitive-landscape`, `market-sizing`. Writes the L1 sentinel `background.md` on completion. Produces ZERO files under `personas/`.
- **Layer 2 — `dudu:pmf-signal`** (the unique deliverable): owns the `personas/` namespace exclusively. Writes the calibrated claim ledger × verdict matrix, the warm-path outreach list, and the legacy-shape `customer-discovery-prep.md` as a side effect.
- **Standalone — `dudu:customer-debrief`**: synthesizes real interview transcripts into `customer-discovery.md`. Runs whenever transcripts exist under `inputs/`; no orchestrator coupling.

The deprecated `dudu:diligence` wrapper still runs the full chain end-to-end for backward compatibility, but the layered skills are the canonical surface.

## Directory layout

```
deals/<slug>/
├── manifest.json
├── inputs/                       # artifacts the VC supplied (deck, notes, transcripts)
├── background.md                 # L1 sentinel — written by dudu:background-check
├── founder-<name>.md             # one per founder; <name> is kebab-case of the founder name
├── idea-validation.md            # optional; written by dudu:idea-validation
├── candidates/                   # optional; one file per candidate persona/segment
│   ├── candidate-1.md
│   └── candidate-2.md
├── market-context.md             # written by dudu:market-context
├── personas/                     # owned exclusively by dudu:pmf-signal
│   ├── _context.md               # PMF-derived L1 context bundle
│   ├── frames.yaml
│   ├── seeds.yaml
│   ├── aggregates.yaml
│   ├── verdicts.yaml
│   └── rows/
│       └── p-<id>.yaml           # one per synthetic persona
├── competitive-landscape.md
├── market-sizing.md
├── pmf-signal.md                 # the calibrated claim-ledger × verdict matrix
├── outreach.md                   # warm-path outreach list
├── customer-discovery-prep.md    # convenience artifact (Stage 5 side effect of pmf-signal)
├── customer-discovery.md         # written by dudu:customer-debrief from real transcripts
├── pitch.yaml                    # claim ledger seed/verified ledger
└── MEMO.md                       # optional; written by the diligence wrapper
```

### Legacy layout tolerance

Existing deals (e.g. `deals/ledgerloop`, `deals/callagent`, `deals/tiny`) were created before the layered split and have a slightly different shape:

- No `background.md` sentinel
- `market-problem.md` instead of `market-context.md`
- `personas/_context.md`, `persona-*.md`, `round-*.md` written by the old `market-problem` Phase 2

These deals continue to render. The renderer detects layout shape and tolerates either:

- **New (post-split)**: `background.md` present, no `persona-*.md` / `round-*.md`, `market-context.md` is the context file.
- **Legacy (pre-split)**: no `background.md`, `market-problem.md` present, possibly `persona-*.md` / `round-*.md`.

Skills that read these directories (`dudu:pmf-signal` Stage 0b, `dudu:customer-debrief` for prior contradictions) treat any persona files they find as read-only inputs and never overwrite them.

## `manifest.json` schema

```json
{
  "slug": "acme",
  "company": "Acme",
  "founders": ["Alice Founder", "Bob Cofounder"],
  "pitch": "One-line pitch.",
  "created_at": "2026-04-28T10:30:00Z",
  "skills_completed": {
    "background-check": null,
    "founder-check": null,
    "market-context": null,
    "competitive-landscape": null,
    "market-sizing": null,
    "pmf-signal": null,
    "customer-debrief": null
  }
}
```

Every skill that produces an artifact MUST update `skills_completed[<skill-key>]` with the current ISO-8601 UTC timestamp. If the skill aborts, it leaves the value as `null`.

The `background-check` orchestrator key is set when the L1 sentinel is written (i.e. all four sub-skills succeeded).

Optional skills (e.g. `idea-validation`) may add their own key on completion. The deprecated wrappers (`diligence`, `market-problem`, `customer-discovery`) do not add their own keys — they update the underlying layered skill's key.

### Legacy manifest tolerance

Legacy manifests under `deals/ledgerloop/`, `deals/callagent/`, `deals/tiny/` use the older key set: `market-problem`, `customer-discovery-prep`, `customer-discovery-debrief`. Renderers and analysis tools tolerate both schemas. Do not retroactively rewrite legacy manifests.

## Idempotency

When invoked, a skill checks whether its artifact already exists.
- If yes and `--force` was NOT passed: print `Artifact already exists at <path>. Pass --force to overwrite.` and exit.
- If `--force` was passed: overwrite the artifact and re-update the manifest timestamp.

For `dudu:pmf-signal`, `--force` overwrites PMF-authored files but never touches legacy `personas/persona-*.md` or `personas/round-*.md` files.

## Reading prior artifacts

Later skills MAY read earlier artifacts. For example, `dudu:customer-debrief` reads `personas/verdicts.yaml` (PMF-authored) for prior contradictions; if absent, it falls back to legacy `personas/persona-*.md`; if both absent, the contradictions section is omitted. Always check existence before reading; never crash if a prior step was skipped.
