# background-check Specification

## Purpose
TBD - created by archiving change split-background-and-pmf-layers. Update Purpose after archive.
## Requirements
### Requirement: Background-check input contract
The system SHALL accept the following inputs and reject runs that do not satisfy them: deal slug (kebab-case), company name, founder names (one or more), one-line pitch, and either a deck file under `deals/<slug>/inputs/deck.<ext>` or pasted pitch text written to `deals/<slug>/inputs/deck.md` before the run starts.

#### Scenario: Run is rejected when deck input is missing
- **WHEN** `dudu:background-check` is invoked on a deal whose `inputs/` directory contains no `deck.*` file
- **THEN** the skill exits with a clear error pointing the user at how to supply a deck

#### Scenario: Run is rejected when slug is missing or invalid
- **WHEN** `dudu:background-check` is invoked without a slug, or with a slug that is not kebab-case
- **THEN** the skill exits with a clear error

