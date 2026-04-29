## ADDED Requirements

### Requirement: Background-check orchestrates the four cheap sub-skills
The system SHALL provide a `background-check` skill that, when invoked on a deal slug, runs `founder-check`, `market-context`, `competitive-landscape`, and `market-sizing` to completion. It SHALL NOT invoke `pmf-signal`, `customer-debrief`, or any persona-simulation step.

#### Scenario: Successful run on a fresh deal
- **WHEN** `dudu:background-check` is invoked with `--slug <slug>` for a deal whose `deals/<slug>/manifest.json` exists and the four sub-skill artifacts do not yet exist
- **THEN** the four sub-skills run in sequence
- **AND** each writes its artifact to `deals/<slug>/`
- **AND** the manifest's `skills_completed` is updated with non-null timestamps for `founder-check`, `market-context`, `competitive-landscape`, and `market-sizing`
- **AND** no file is written under `deals/<slug>/personas/`

#### Scenario: Re-invocation skips completed sub-skills
- **WHEN** `dudu:background-check` is invoked on a deal where `founder-*.md`, `market-context.md`, and `competitive-landscape.md` already exist but `market-sizing.md` does not
- **THEN** only `market-sizing` runs
- **AND** the existing artifacts are not overwritten
- **AND** the manifest's existing timestamps are preserved

#### Scenario: Force flag re-runs all sub-skills
- **WHEN** `dudu:background-check --slug <slug> --force` is invoked
- **THEN** all four sub-skills are re-run regardless of existing artifacts
- **AND** the prior artifacts are replaced

### Requirement: Background-check produces an L1 sentinel bundle
The system SHALL write `deals/<slug>/background.md` as a single sentinel file at the end of a successful background-check run. This file is the contract by which downstream layers (notably `pmf-signal`) recognize that L1 is complete.

#### Scenario: Sentinel is written on success
- **WHEN** `dudu:background-check` completes successfully
- **THEN** `deals/<slug>/background.md` exists
- **AND** its contents include short summaries of each sub-skill's output and pointers to the per-skill artifact files

#### Scenario: Sentinel is not written on partial completion
- **WHEN** `dudu:background-check` runs but one sub-skill fails
- **THEN** `background.md` is not written
- **AND** the manifest reflects only the sub-skills that completed
- **AND** the user is told which sub-skill failed and how to resume

### Requirement: Background-check refuses to write persona artifacts
The system SHALL NOT, under any code path inside `background-check` or its sub-skills, create files under `deals/<slug>/personas/`. The persona namespace is owned exclusively by `pmf-signal`.

#### Scenario: No persona files appear after L1 run
- **WHEN** `dudu:background-check` completes
- **THEN** `deals/<slug>/personas/` either does not exist or contains no files

## ADDED Requirements

### Requirement: Background-check input contract
The system SHALL accept the following inputs and reject runs that do not satisfy them: deal slug (kebab-case), company name, founder names (one or more), one-line pitch, and either a deck file under `deals/<slug>/inputs/deck.<ext>` or pasted pitch text written to `deals/<slug>/inputs/deck.md` before the run starts.

#### Scenario: Run is rejected when deck input is missing
- **WHEN** `dudu:background-check` is invoked on a deal whose `inputs/` directory contains no `deck.*` file
- **THEN** the skill exits with a clear error pointing the user at how to supply a deck

#### Scenario: Run is rejected when slug is missing or invalid
- **WHEN** `dudu:background-check` is invoked without a slug, or with a slug that is not kebab-case
- **THEN** the skill exits with a clear error
