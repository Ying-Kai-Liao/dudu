# background-check Specification

## Purpose
TBD - created by archiving change split-background-and-pmf-layers. Update Purpose after archive.
## Requirements
### Requirement: Background-check input contract
The system SHALL accept the following inputs and reject runs that do not satisfy them: deal slug (kebab-case), company name, founder names (one or more), and a one-line pitch (recorded in `manifest.json`'s `pitch` field). A deck file under `deals/<slug>/inputs/deck.<ext>` (or pasted deck text written to `deals/<slug>/inputs/deck.md`) is OPTIONAL — when supplied it strengthens the Layer 2 claim ledger; when absent the manifest pitch and L1 artifacts carry through to PMF Stage 0.

#### Scenario: Run accepts a deal with no deck
- **WHEN** `dudu:background-check` is invoked on a deal whose `inputs/` directory contains no `deck.*` file but `manifest.json` has a non-empty `pitch` field
- **THEN** the skill proceeds normally and writes `background.md` on success

#### Scenario: Run is rejected when slug is missing or invalid
- **WHEN** `dudu:background-check` is invoked without a slug, or with a slug that is not kebab-case
- **THEN** the skill exits with a clear error

#### Scenario: Run is rejected when manifest pitch is empty
- **WHEN** `dudu:background-check` is invoked on a deal whose `manifest.json` has an empty `pitch` field AND no `inputs/deck.*` file
- **THEN** the skill exits with a clear error pointing the user at the missing pitch source

