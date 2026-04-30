# market-context Specification

## Purpose
TBD - created by archiving change split-background-and-pmf-layers. Update Purpose after archive.
## Requirements
### Requirement: Market-context produces public-source context only
The system SHALL provide a `market-context` skill that produces a market and problem context bundle from public web sources. It SHALL NOT produce personas, persona interviews, or any artifact under `deals/<slug>/personas/`.

#### Scenario: Successful run writes context artifact
- **WHEN** `dudu:market-context --slug <slug>` is invoked
- **THEN** `deals/<slug>/market-context.md` is written
- **AND** no file is written under `deals/<slug>/personas/`
- **AND** the manifest's `skills_completed.market-context` is set to a non-null ISO timestamp

#### Scenario: Output structure
- **WHEN** `market-context.md` is inspected after a successful run
- **THEN** it contains a Phase 1 section (web research bundle: market shape, problem severity signals, adjacent categories) and a Phase 3 section (synthesis: surfaced patterns and contradictions)
- **AND** it does NOT contain any "Phase 2" or "self-play interview" content

### Requirement: Market-context replaces market-problem
The system SHALL recognize `market-context` as the successor capability to the deprecated `market-problem` skill. Existing references to `market-problem` in plugin metadata, README, and `lib/deal.md` SHALL be updated to point at `market-context`.

#### Scenario: market-problem invocation prints deprecation
- **WHEN** a user invokes `dudu:market-problem`
- **THEN** the skill prints a deprecation notice that points to `dudu:market-context`
- **AND** it forwards the invocation to `market-context` for one release window
- **AND** the deprecation message names the change that will remove the wrapper

#### Scenario: market-problem skill is removable in a follow-up release
- **WHEN** the deprecation window expires (tracked in a separate change)
- **THEN** `skills/market-problem/` can be deleted with no remaining callers
- **AND** the test suite continues to pass

### Requirement: Existing personas under deals/<slug>/personas/ are preserved on disk
The system SHALL NOT delete, rewrite, or move any existing files under `deals/<slug>/personas/` on existing deals (`deals/ledgerloop/`, `deals/callagent/`, `deals/tiny/`) when the new `market-context` skill runs. Renderers handle both legacy (`market-problem`-authored) and new (`pmf-signal`-authored) layouts.

#### Scenario: Re-running market-context on a legacy deal
- **WHEN** `dudu:market-context --slug ledgerloop --force` is invoked on a deal that has legacy persona files at `deals/ledgerloop/personas/persona-*.md`
- **THEN** `deals/ledgerloop/market-context.md` is rewritten
- **AND** `deals/ledgerloop/personas/` is unchanged

