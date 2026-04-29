# customer-debrief Specification

## Purpose
TBD - created by archiving change split-background-and-pmf-layers. Update Purpose after archive.
## Requirements
### Requirement: Customer-debrief is a standalone skill
The system SHALL provide a `customer-debrief` skill that synthesizes real-customer interview transcripts into a `customer-discovery.md` artifact. This skill SHALL run independently of any orchestrator, with no dependency on the prior diligence chain's prep state.

#### Scenario: Successful debrief on a deal with transcripts
- **WHEN** `dudu:customer-debrief --slug <slug>` is invoked on a deal where `deals/<slug>/inputs/` contains at least one transcript file (`.md`, `.txt`, or `.vtt`)
- **THEN** `deals/<slug>/customer-discovery.md` is written
- **AND** the manifest's `skills_completed.customer-debrief` is set to a non-null ISO timestamp
- **AND** the run is independent of whether `customer-discovery-prep.md` exists

#### Scenario: Debrief refuses to run without transcripts
- **WHEN** `dudu:customer-debrief` is invoked on a deal whose `inputs/` directory contains no transcript files
- **THEN** the skill exits with a clear error pointing the user at how to add transcripts

#### Scenario: Debrief refuses to overwrite without --force
- **WHEN** `dudu:customer-debrief` is invoked on a deal where `customer-discovery.md` already exists
- **THEN** the skill exits with a message saying the artifact already exists and `--force` is required to overwrite

### Requirement: Customer-debrief has no orchestrator coupling
The system SHALL NOT make `customer-debrief` depend on any specific prior skill having run. It SHALL accept transcripts produced under any flow — including transcripts from a fully manual workflow with no prior `dudu:*` invocations.

#### Scenario: Debrief works on a deal with only a manifest and transcripts
- **WHEN** `dudu:customer-debrief` is invoked on a deal where `manifest.json` and `inputs/transcript-*.md` exist but no other skill has ever run on the deal
- **THEN** the skill runs to completion
- **AND** writes `customer-discovery.md`
- **AND** updates the manifest's `skills_completed.customer-debrief` timestamp

### Requirement: customer-discovery skill becomes a deprecation stub
The system SHALL keep `dudu:customer-discovery` as an invokable name for one release window, but the skill SHALL be a thin deprecation wrapper that prints a migration message and forwards to either `pmf-signal` (for the prep half) or `customer-debrief` (for the debrief half).

#### Scenario: Legacy invocation prints deprecation
- **WHEN** a user invokes `dudu:customer-discovery debrief`
- **THEN** the skill prints a deprecation notice that points to `dudu:customer-debrief`
- **AND** it forwards the invocation to `customer-debrief`

#### Scenario: Legacy prep invocation prints deprecation
- **WHEN** a user invokes `dudu:customer-discovery prep`
- **THEN** the skill prints a deprecation notice noting that prep is now produced as a side effect of `dudu:pmf-signal`
- **AND** it forwards to `pmf-signal` if the L1 bundle is present, or exits with guidance otherwise

