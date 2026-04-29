# pmf-signal Specification

## Purpose
TBD - created by archiving change split-background-and-pmf-layers. Update Purpose after archive.
## Requirements
### Requirement: PMF-signal preflight uses an L1-bundle contract
The system SHALL gate `pmf-signal` execution on the presence of (a) `deals/<slug>/background.md` (the L1 sentinel) and (b) the four cross-artifact verification targets `founder-*.md`, `market-context.md`, `competitive-landscape.md`, `market-sizing.md`. A deck file at `deals/<slug>/inputs/deck.<ext>` (or `deck.md` for pasted text) is OPTIONAL — when present it strengthens Stage 0 claim ingestion; when absent Stage 0 falls back to `manifest.pitch` plus the L1 artifacts. The preflight SHALL NOT check for `customer-discovery-prep.md`, `personas/_context.md`, or any other artifact owned by a different layer.

#### Scenario: Preflight passes with the L1 contract satisfied (deck present)
- **WHEN** `dudu:pmf-signal --slug <slug>` is invoked on a deal that has `background.md`, the four cross-artifact files, and a deck — but no `customer-discovery-prep.md` and no legacy persona files
- **THEN** preflight exits 0
- **AND** the loading ledger is printed including the pitch source
- **AND** stage 0 begins

#### Scenario: Preflight passes with no deck (manifest.pitch carries the pitch)
- **WHEN** `dudu:pmf-signal --slug <slug>` is invoked on a deal that has `background.md` and the four cross-artifact files but no `inputs/deck.*`
- **THEN** preflight exits 0
- **AND** the loading ledger notes "pitch sources: none (deck optional — Stage 0 will use manifest.pitch + founder/context artifacts)"
- **AND** stage 0 begins, treating manifest.pitch + founder dossiers + market-context as the claim sources

#### Scenario: Preflight fails when L1 sentinel is missing
- **WHEN** `dudu:pmf-signal` is invoked on a deal where every other artifact exists but `background.md` does not
- **THEN** preflight exits non-zero with a message naming the missing sentinel
- **AND** the message tells the user to run `dudu:background-check` first
- **AND** no automatic upstream invocation happens (the user controls heavy spend)

#### Scenario: Preflight ignores customer-discovery-prep.md presence or absence
- **WHEN** `dudu:pmf-signal` is invoked
- **THEN** preflight does not check for `customer-discovery-prep.md`
- **AND** the result is the same regardless of whether that file exists

### Requirement: PMF-signal owns the persona namespace
The system SHALL treat `deals/<slug>/personas/` as owned by `pmf-signal`. PMF-signal SHALL be the only skill that creates new files under that directory. PMF-signal SHALL tolerate pre-existing legacy files (e.g. `personas/_context.md`, `personas/persona-*.md` produced by the deprecated `market-problem` Phase 2) without overwriting or deleting them.

#### Scenario: Fresh deal — no legacy persona files
- **WHEN** `dudu:pmf-signal` runs to completion on a new deal
- **THEN** `deals/<slug>/personas/` contains `_context.md` (now PMF-authored), `frames.yaml`, `seeds.yaml`, `aggregates.yaml`, `verdicts.yaml`, and `rows/p-*.yaml`
- **AND** no other skill is responsible for any of those files

#### Scenario: Legacy deal — pre-existing market-problem persona files
- **WHEN** `dudu:pmf-signal` runs on a legacy deal that already has `personas/_context.md` and `personas/persona-*.md` from the deprecated `market-problem` Phase 2
- **THEN** the legacy `persona-*.md` files are left on disk untouched
- **AND** `personas/_context.md` is overwritten only if `--force` is set; otherwise PMF treats it as input
- **AND** PMF-signal still writes its own `frames.yaml`, `seeds.yaml`, `aggregates.yaml`, `verdicts.yaml`, and `rows/p-*.yaml` alongside

### Requirement: PMF-signal continues to emit the legacy-shape customer-discovery-prep
The system SHALL continue to emit `deals/<slug>/customer-discovery-prep.md` as a side effect of stage 5, for the convenience of VCs who want a prep doc independent of the orchestrator. This file is a *side effect*, not a preflight gate.

#### Scenario: Prep file is written on successful PMF run
- **WHEN** `dudu:pmf-signal` completes successfully
- **THEN** `deals/<slug>/customer-discovery-prep.md` exists
- **AND** its contents follow the legacy schema previously produced by the diligence orchestrator

#### Scenario: Prep file is not used to gate any other skill
- **WHEN** any other skill in the plugin runs
- **THEN** none of them check for `customer-discovery-prep.md` as a precondition

