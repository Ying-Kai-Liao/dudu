## ADDED Requirements

### Requirement: Renderer reads pmf-signal yaml artifacts as the canonical structural input
The system SHALL load `deals/<slug>/pitch.yaml`, `deals/<slug>/personas/verdicts.yaml`, `deals/<slug>/personas/aggregates.yaml`, and `deals/<slug>/outreach.md` as the canonical input for the per-deal HTML report's headline structure. The system SHALL also load `deals/<slug>/manifest.json` for skill-completion metadata. The renderer SHALL NOT parse `pmf-signal.md` markdown to recover structured ledger data when the yaml artifacts are present. `MEMO.md` SHALL contribute only the recommendation ribbon and a cross-artifact synthesis drill-down section, not the report's section ordering.

#### Scenario: Renderer prefers yaml over markdown when both exist
- **WHEN** `scripts/render-report.py --slug <slug>` runs on a deal that has `pitch.yaml`, `verdicts.yaml`, `aggregates.yaml`, AND `pmf-signal.md`
- **THEN** the rendered HTML's headline ★ sections are sourced from the yaml artifacts
- **AND** `pmf-signal.md` is not parsed for ledger data
- **AND** the rendered HTML lists `pmf-signal.md` only in the "Source artifacts" section as a link

#### Scenario: Renderer ignores MEMO sections that duplicate per-artifact files
- **WHEN** the renderer runs on a deal where MEMO.md contains `## TL;DR`, `## Founders`, `## Problem and Product`, `## Customer Signal`, `## Competitive Landscape`, `## Market Sizing`, `## Cross-artifact Synthesis`, and `## Recommendation`
- **THEN** the rendered HTML uses MEMO only for the recommendation ribbon and the cross-artifact synthesis drill-down
- **AND** the other MEMO sections are not rendered as their own report sections
- **AND** the per-artifact files (`founder-*.md`, `market-problem.md` or `market-context.md`, `customer-discovery.md`, `competitive-landscape.md`, `market-sizing.md`) drive the corresponding drill-down sections

### Requirement: Report layout leads with the calibrated claim ledger × verdict matrix
The system SHALL render the per-deal HTML in this top-to-bottom order when `pitch.yaml` and `verdicts.yaml` are both present: (1) header with company name and generated timestamp, (2) recommendation ribbon, (3) ★ claim ledger × verdict matrix, (4) ★ cross-artifact contradictions, (5) ★ warm-path outreach top-N, (6) drill-down (collapsed by default), (7) source artifacts. The drill-down SHALL contain founders, problem & product, customer signal, competitive landscape, market sizing, personas, and cross-artifact synthesis sub-sections, in that order.

#### Scenario: Full PMF input renders ★-led layout
- **WHEN** the renderer runs on a deal with `pitch.yaml`, `verdicts.yaml`, `aggregates.yaml`, `outreach.md`, and the legacy artifact files all present
- **THEN** the rendered HTML's first major section after the header and recommendation ribbon is the claim ledger × verdict matrix
- **AND** cross-artifact contradictions appears second
- **AND** warm-path outreach top-N appears third
- **AND** drill-down sections (founders, problem & product, customer signal, competitive landscape, market sizing, personas, cross-artifact synthesis) appear after the ★ sections
- **AND** drill-down sections render as `<details>` elements without the `open` attribute

#### Scenario: Drill-down sections are collapsed by default
- **WHEN** the rendered HTML is opened in a browser
- **THEN** every drill-down sub-section (founders, problem & product, customer signal, competitive landscape, market sizing, personas, cross-artifact synthesis) is collapsed
- **AND** no `<details>` element under the drill-down has the `open` attribute set
- **AND** the persona group's individual persona collapsibles are also closed by default

### Requirement: Claim ledger orders rows worst-news-first
The system SHALL sort claim-ledger rows by verdict severity, with `contradicts` first, then `partial` and `no-evidence` (interleaved by claim category), then `supports`, then `pending` last. Within each verdict group the system SHALL sort by claim category in the order founder → product → market → traction → ask, then by `claim_id` ascending as a stable tie-break.

#### Scenario: Contradicts rows render above supports rows
- **WHEN** the renderer runs on a deal whose `verdicts.yaml` contains both `contradicts` and `supports` rows
- **THEN** every `contradicts` row appears above every `supports` row in the rendered ledger table
- **AND** within the `contradicts` group, rows are ordered by claim category (founder before product before market before traction before ask)
- **AND** within a single verdict-and-category group, rows are ordered by `claim_id` ascending

#### Scenario: Pending rows render last under their own group header
- **WHEN** the renderer runs on a deal where some rows have verdict `pending` (because `verdicts.yaml` is missing or partial)
- **THEN** all `pending` rows render below all rows that have a real verdict
- **AND** an italic group header reading "Verdicts pending" precedes the pending rows

### Requirement: Each ledger row carries a verification-method badge with Stance B disclaimer on persona-reaction rows
The system SHALL render each ledger row with a small badge identifying the verification method as one of `persona-reaction`, `cross-artifact`, or `external`. The system SHALL display a Stance B caption ("Calibrated prior, not signal — see PMF stage 3a" or equivalent) on every `persona-reaction` row. The system SHALL NOT display that caption on `cross-artifact` or `external` rows. The badges SHALL be visually distinct (different color or shape) so the three verification methods can be told apart at a glance, using CSS-only styling defined in the renderer's inline `<style>` block.

#### Scenario: Persona-reaction row carries Stance B caption
- **WHEN** the renderer encounters a row whose `verification: persona-reaction`
- **THEN** the rendered row includes a badge labelled "persona-reaction"
- **AND** an italic caption naming Stance B (calibrated prior, not signal) appears in the row's evidence cell

#### Scenario: Cross-artifact row carries no Stance B caption
- **WHEN** the renderer encounters a row whose `verification: cross-artifact`
- **THEN** the rendered row includes a badge labelled "cross-artifact"
- **AND** the row's evidence cell does not include a Stance B caption
- **AND** the row's evidence cell quotes the cross-artifact verbatim snippet from `verdicts.yaml`'s `evidence.quote`

#### Scenario: External row carries no Stance B caption
- **WHEN** the renderer encounters a row whose `verification: external`
- **THEN** the rendered row includes a badge labelled "external"
- **AND** the row's evidence cell does not include a Stance B caption
- **AND** the row's evidence cell links to the external pointer in `verdicts.yaml`'s `evidence.url` (or quotes the external snippet if no url is present)

### Requirement: Cross-artifact contradictions section quotes verbatim snippets with file pointers
The system SHALL render a "Cross-artifact contradictions" ★ section containing every ledger row whose `verification: cross-artifact` AND whose verdict is `contradicts` or `partial`. Each entry SHALL include the verbatim claim text, the contradicting artifact's filename, the verbatim quote from `verdicts.yaml`'s `evidence.quote` field, and a link `→ <file>` to the source file. The section SHALL be omitted entirely if no rows qualify.

#### Scenario: Contradictions section renders qualifying rows
- **WHEN** the renderer runs on a deal where `verdicts.yaml` contains a `cross-artifact` row with verdict `contradicts` whose claim is "We have 12 paying customers" and whose evidence quotes a customer-discovery line "Three of the named accounts described themselves as pilots, not paid"
- **THEN** the contradictions section includes that row
- **AND** the entry shows the claim text verbatim
- **AND** the entry shows the customer-discovery quote verbatim with a `→ customer-discovery.md` link

#### Scenario: Persona-reaction partial does not appear in contradictions
- **WHEN** the renderer runs on a deal where a `persona-reaction` row has verdict `partial`
- **THEN** that row does not appear in the cross-artifact contradictions section
- **AND** that row continues to appear in the main ledger × verdict matrix with its `persona-reaction` badge

#### Scenario: Empty contradictions section is omitted
- **WHEN** the renderer runs on a deal where no row qualifies (no `cross-artifact` row has `contradicts` or `partial` verdict)
- **THEN** the rendered HTML contains no contradictions section header
- **AND** no empty placeholder is rendered

### Requirement: Warm-path outreach top-N is embedded inline; full list is linked
The system SHALL render a "Warm-path outreach" ★ section containing the first N entries from `outreach.md` in the order they appear in the source file. N SHALL default to 10 (configurable via a module-level constant). Each embedded entry SHALL show the contact's name, company, warm-path source, and the warm-path quote or one-line rationale. The section SHALL include a link to the full `outreach.md` file. The system SHALL NOT re-sort `outreach.md` entries; PMF's emit order (strongest warm-path first) is respected.

#### Scenario: Top 10 entries are embedded
- **WHEN** the renderer runs on a deal whose `outreach.md` contains 24 entries
- **THEN** the warm-path outreach section embeds the first 10 entries in source-file order
- **AND** an "all 24 — see outreach.md" link points to `outreach.md`
- **AND** each embedded entry shows name, company, warm-path source, and the rationale or quote

#### Scenario: Outreach with fewer than N entries renders all
- **WHEN** the renderer runs on a deal whose `outreach.md` contains 3 entries
- **THEN** all 3 entries render inline
- **AND** no "see outreach.md for more" link is added (because the embedded list is complete)

#### Scenario: Missing outreach.md omits the section
- **WHEN** the renderer runs on a deal where `outreach.md` does not exist
- **THEN** the warm-path outreach ★ section is omitted entirely
- **AND** the rendered report still contains the ledger and contradictions sections if their inputs are present

### Requirement: Renderer tolerates partial pmf-signal output via documented fallback branches
The system SHALL detect the input shape and select one of four rendering branches: (1) **full** when both `pitch.yaml` and `verdicts.yaml` exist, (2) **pitch-only** when `pitch.yaml` exists but `verdicts.yaml` does not, (3) **markdown-fallback** when neither yaml exists but `pmf-signal.md` does, (4) **legacy** when none of the three exist. Branches 2 and 3 SHALL emit a stderr warning naming the missing files and the chosen branch. The renderer SHALL never crash when input is partial; it SHALL always degrade to a less-rich branch.

#### Scenario: Pitch-only branch renders ledger with pending verdicts
- **WHEN** the renderer runs on a deal that has `pitch.yaml` but no `verdicts.yaml`
- **THEN** the ledger renders with every row's verdict cell showing a `pending` badge
- **AND** the cross-artifact contradictions section is replaced by a single-line note "PMF run incomplete — verdicts not yet generated"
- **AND** if `outreach.md` exists, the warm-path outreach section still renders normally
- **AND** a stderr warning names `verdicts.yaml` as missing and identifies the branch as pitch-only

#### Scenario: Markdown-fallback branch renders pmf-signal.md content
- **WHEN** the renderer runs on a deal that has `pmf-signal.md` but neither `pitch.yaml` nor `verdicts.yaml`
- **THEN** in place of the three ★ sections, a single section renders the markdown content of `pmf-signal.md`
- **AND** a stderr warning is emitted naming the missing yaml files and identifying the branch as markdown-fallback
- **AND** the drill-down sections still render normally below

#### Scenario: Malformed yaml falls back gracefully
- **WHEN** the renderer encounters a `pitch.yaml` or `verdicts.yaml` that fails to parse
- **THEN** the renderer logs a stderr error naming the file and the parse error
- **AND** the renderer falls back to the next applicable branch (treating the malformed file as absent)
- **AND** the renderer does not crash

### Requirement: Renderer preserves backward compatibility for legacy deals
The system SHALL render legacy deals (deals predating pmf-signal, with no `pitch.yaml`, `verdicts.yaml`, or `pmf-signal.md`) using the legacy artifact-by-artifact layout that matches today's renderer output. The legacy branch SHALL render the existing sections (TL;DR, founders, problem & product, customer signal, competitive landscape, market sizing, cross-artifact synthesis, recommendation, personas, source artifacts) sourced from MEMO.md and per-artifact files, with the same ordering and expansion behavior the renderer produces today. `deals/ledgerloop/`, `deals/callagent/`, and `deals/tiny/` SHALL continue to render under this branch without on-disk modification.

#### Scenario: Legacy deal renders today's layout
- **WHEN** the renderer runs on `deals/ledgerloop/` (which has no pmf-signal artifacts)
- **THEN** the rendered HTML uses the legacy artifact-by-artifact layout
- **AND** no ★ sections appear
- **AND** no recommendation ribbon appears unless MEMO.md provides one
- **AND** the section ordering matches the renderer's prior behavior

#### Scenario: Legacy deal needs no on-disk migration
- **WHEN** the renderer runs on `deals/ledgerloop/`, `deals/callagent/`, or `deals/tiny/`
- **THEN** no file under those deal directories is created, modified, or deleted by the renderer
- **AND** the rendered HTML is produced successfully

### Requirement: Recommendation ribbon is rendered from MEMO.md when present
The system SHALL render a recommendation ribbon (pass / watch / pursue plus a one-line why) immediately under the page header when `MEMO.md` contains a `## Recommendation` section (case-insensitive heading match). The ribbon SHALL be omitted when MEMO.md is absent or contains no recommendation section. The recommendation text SHALL be rendered as inline HTML, not as a separate section.

#### Scenario: MEMO with recommendation produces a ribbon
- **WHEN** MEMO.md contains a `## Recommendation` section whose body is "Pursue. Calibrated prior matches founder claims; warm-path 1st-degree exists."
- **THEN** the rendered HTML shows a ribbon under the header containing that text
- **AND** the ribbon is visually distinct from the page header (e.g., styled callout)

#### Scenario: Missing MEMO recommendation omits the ribbon
- **WHEN** MEMO.md is absent OR contains no recommendation heading
- **THEN** the rendered HTML contains no recommendation ribbon
- **AND** no placeholder is rendered

### Requirement: Renderer output remains self-contained with stdlib + PyYAML only
The system SHALL produce a single self-contained HTML file with all CSS inline in a `<style>` block and no external network assets, no external CSS files, no JS frameworks, and no inline `<script>` blocks beyond what the existing renderer already emits. The renderer SHALL use only Python standard library plus PyYAML (already a transitive dependency of other scripts in this repo) for parsing.

#### Scenario: Rendered HTML is self-contained
- **WHEN** the renderer produces `report.html` for any deal
- **THEN** the HTML file references no external CSS URL
- **AND** the HTML file references no external JavaScript URL
- **AND** the HTML file references no external image URL
- **AND** opening the HTML file with no network access renders identically to opening it online

#### Scenario: Renderer imports only stdlib plus PyYAML
- **WHEN** `scripts/render-report.py` is invoked
- **THEN** the only third-party import is `yaml`
- **AND** all other imports are Python standard library
