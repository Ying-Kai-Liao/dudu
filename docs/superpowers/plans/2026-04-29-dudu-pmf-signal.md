# dudu:pmf-signal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `dudu:pmf-signal` skill — a calibrated population-PMF and warm-path-outreach layer that runs after the existing dudu diligence chain, validating every founder/company claim through three parallel verification paths and producing a Stance-B claim ledger plus cluster-stratified outreach roster.

**Architecture:** New skill at `skills/pmf-signal/SKILL.md` orchestrates six pipeline stages (pre-flight → claim ingestion → frame definition → 5W population synthesis → 3-path verification → PMF report → network scan). Deterministic logic lives in stdlib-only Python helpers under `scripts/pmf-signal-*.py`. Tests are bash golden-file tests under `tests/pmf-signal/` following the existing `tests/lint/` pattern. The `dudu:diligence` orchestrator is updated to call `pmf-signal` and to drop `customer-discovery prep` from its chain (pmf-signal stage 5 emits the legacy-shape `customer-discovery-prep.md`).

**Tech Stack:** Python 3 stdlib only (matches `scripts/render-report.py` precedent); bash for tests; Markdown for skill content; YAML for structured artifacts.

**Spec source-of-truth:** `docs/superpowers/specs/2026-04-29-dudu-pmf-signal-design.md` (commit `784a308`). Read this fully before starting.

---

## File Structure

**New skill files:**
- `skills/pmf-signal/SKILL.md` — main playbook for Claude.

**New helper scripts (stdlib only):**
- `scripts/pmf-signal-preflight.py` — verify upstream artifacts exist, print loading ledger.
- `scripts/pmf-signal-validate-pitch.py` — sanity-check `pitch.yaml` shape after Stage 0.
- `scripts/pmf-signal-mode-collapse.py` — heuristic check on scenario-seed diversity (top-1 share threshold).
- `scripts/pmf-signal-aggregate.py` — Stance-B aggregations over `personas/reactions/*.yaml` (counts, percentages, σ).
- `scripts/pmf-signal-consolidate-verdicts.py` — merge stage 3a/3b/3c outputs → `personas/verdicts.yaml`.
- `scripts/pmf-signal-render-report.py` — assemble `pmf-signal.md` from `pitch.yaml`, aggregates, verdicts, refusals.
- `scripts/pmf-signal-render-outreach.py` — assemble `outreach.md` and the legacy-shape `customer-discovery-prep.md`.
- `scripts/pmf-signal-recipes/__init__.py`
- `scripts/pmf-signal-recipes/customer_list.py` — external-evidence recipe.
- `scripts/pmf-signal-recipes/testimonial_count.py` — external-evidence recipe.
- `scripts/pmf-signal-recipes/wayback_history.py` — external-evidence recipe.

**Modified files:**
- `skills/diligence/SKILL.md` — re-order sub-skill chain: founder-check → market-problem → competitive-landscape → market-sizing → pmf-signal; remove `customer-discovery prep` from chain; update `MEMO.md` template; update manifest verification list.
- `skills/customer-discovery/SKILL.md` — note that `prep` is no longer called by orchestrator (still works standalone).
- `lib/deal.md` — manifest schema gets `skills_completed["pmf-signal"]`.

**New test files:**
- `tests/pmf-signal/run.sh` — entrypoint runner, mirrors `tests/lint/run.sh`.
- `tests/pmf-signal/fixtures/<case>/...` — input deals.
- `tests/pmf-signal/expected/<case>.txt` — expected stdout/stderr golden files.
- `tests/pmf-signal/fixtures-yaml/...` — small YAML fixtures for unit-style tests of helper scripts.

**Test deal:** `test/ledgerloop` is the integration ground truth. The final task runs the full pipeline against it and inspects outputs manually.

---

## Task 0: Read the spec end-to-end

**Files:**
- Read: `docs/superpowers/specs/2026-04-29-dudu-pmf-signal-design.md`
- Read: `skills/diligence/SKILL.md`
- Read: `skills/market-problem/SKILL.md`
- Read: `skills/customer-discovery/SKILL.md`
- Read: `lib/deal.md`
- Read: `lib/research-protocol.md`
- Read: `lib/playwright-auth.md`
- Read: `scripts/render-report.py` (for stdlib Python conventions)
- Read: `tests/lint/run.sh` and one fixture-expected pair (for bash test conventions)

- [ ] **Step 1: Read all listed files in order; do not start writing yet.** The spec defines schemas and prompts that you will reference repeatedly. The skill files show the existing dudu Markdown style. The lib files define citation rules and orchestration primitives that pmf-signal must follow.

- [ ] **Step 2: Create a one-line note in your scratch space confirming you understand:** (a) Stance B (calibrated prior, not signal); (b) the three verification methods (persona-reaction / cross-artifact / external-evidence); (c) the 5W strict-construction rule; (d) the Prerequisites hard gate.

---

## Task 1: Skill scaffold

**Files:**
- Create: `skills/pmf-signal/SKILL.md`

- [ ] **Step 1: Create the skill file with the standard dudu front-matter + section skeleton.**

```markdown
---
name: pmf-signal
description: Calibrated PMF signal + claim verification + warm-path outreach. Layered on top of completed dudu diligence. Ingests every founder/company claim into a structured ledger, verifies via three parallel paths (persona pitch-reaction over an N=10–200 5W-grounded synthetic population, cross-artifact triangulation against prior dudu artifacts, bounded external-evidence web checks), then runs a cluster-stratified network scan with authed-LinkedIn warm-path inference.
---

# PMF signal & warm-path outreach

Run after the full dudu diligence chain. Read `lib/deal.md`, `lib/research-protocol.md`, and `lib/playwright-auth.md` first. Heaviest budget in the plugin: stage 3a is the largest LLM spend; stage 3c carries a 30-fetch web budget.

## What this skill IS and IS NOT

- IS: a layered enrichment that produces the unique-value section of the diligence memo. Operates on prior artifacts; refuses to start without them.
- IS NOT: a replacement for any prior dudu skill. All five upstream skills keep their full scope.
- IS NOT: signal. Stance B applies — every persona-reaction aggregate is a calibrated prior to falsify in real interviews. State this in every output.

## Inputs

(Filled in subsequent tasks.)

## Pre-flight

(Filled in Task 4.)

## Stage 0 — Claim ledger ingestion

(Filled in Task 6.)

## Stage 1 — Frame definition

(Filled in Task 8.)

## Stage 2 — Population synthesis

(Filled in Tasks 9–11.)

## Stage 3 — Claim verification

(Filled in Tasks 12–15.)

## Stage 4 — PMF signal report

(Filled in Task 17.)

## Stage 5 — Network scan & outreach

(Filled in Tasks 18–20.)

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["pmf-signal"]`.
```

- [ ] **Step 2: Commit.**

```bash
git add skills/pmf-signal/SKILL.md
git commit -m "Scaffold dudu:pmf-signal skill"
```

---

## Task 2: Manifest schema update

**Files:**
- Modify: `lib/deal.md`

- [ ] **Step 1: Read `lib/deal.md` to find the `skills_completed` schema definition.**

```bash
grep -n "skills_completed" lib/deal.md
```

- [ ] **Step 2: Add the `pmf-signal` key in the same style as the existing keys.** Locate the list of skill keys (likely a JSON-shape example with `founder-check`, `market-problem`, `customer-discovery-prep`, `customer-discovery-debrief`, `competitive-landscape`, `market-sizing`). Append `"pmf-signal": null` in the same style. If the file documents keys narratively, also add a one-sentence note explaining what populates this key.

The key is set by `dudu:pmf-signal` after stage 5 completes. Same convention as every other skill.

- [ ] **Step 3: Commit.**

```bash
git add lib/deal.md
git commit -m "Add pmf-signal key to manifest schema"
```

---

## Task 3: Pre-flight script (TDD)

**Files:**
- Create: `scripts/pmf-signal-preflight.py`
- Create: `tests/pmf-signal/run.sh`
- Create: `tests/pmf-signal/fixtures/preflight-good/<full minimal deal>`
- Create: `tests/pmf-signal/fixtures/preflight-missing/<deal with founder-*.md absent>`
- Create: `tests/pmf-signal/fixtures/preflight-already-done/<deal with pmf-signal.md present>`
- Create: `tests/pmf-signal/expected/preflight-good.txt`
- Create: `tests/pmf-signal/expected/preflight-missing.txt`
- Create: `tests/pmf-signal/expected/preflight-already-done.txt`

- [ ] **Step 1: Create the test runner skeleton.** Mirror `tests/lint/run.sh`.

```bash
#!/usr/bin/env bash
set -u
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fail=0

run_preflight_case() {
    local name="$1"
    local extra_args="${2:-}"
    local fixture="$script_dir/fixtures/$name"
    local expected="$script_dir/expected/$name.txt"
    local actual
    actual="$(python3 "$script_dir/../../scripts/pmf-signal-preflight.py" "$fixture" $extra_args 2>&1; echo "EXIT=$?")"
    local expected_contents
    expected_contents="$(cat "$expected")"
    if [[ "$actual" == "$expected_contents" ]]; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        echo "--- expected ---"
        echo "$expected_contents"
        echo "--- actual ---"
        echo "$actual"
        echo "--- end ---"
        fail=1
    fi
}

run_preflight_case preflight-good
run_preflight_case preflight-missing
run_preflight_case preflight-already-done

exit "$fail"
```

Make it executable:

```bash
chmod +x tests/pmf-signal/run.sh
```

- [ ] **Step 2: Create the `preflight-good` fixture — a minimal deal with every required artifact.**

Directory structure (each file can be a single placeholder line — content is not what's being tested, only presence):

```
tests/pmf-signal/fixtures/preflight-good/
├── manifest.json                # contents: {"slug":"preflight-good","skills_completed":{"founder-check":"...","market-problem":"...","competitive-landscape":"...","market-sizing":"..."}}
├── inputs/deck.md               # contents: "# Deck\nplaceholder"
├── personas/_context.md         # contents: "# Context bundle\nplaceholder"
├── market-problem.md            # contents: "# Market-problem\nplaceholder"
├── founder-jane-doe.md          # contents: "# Jane Doe\nplaceholder"
├── competitive-landscape.md     # contents: "# Competitive\nplaceholder"
└── market-sizing.md             # contents: "# Market sizing\nplaceholder"
```

- [ ] **Step 3: Create `preflight-missing` fixture — same as good but without `founder-*.md` and without `competitive-landscape.md`.**

- [ ] **Step 4: Create `preflight-already-done` fixture — same as good but with `pmf-signal.md` already present (single line "# PMF signal\nalready done").**

- [ ] **Step 5: Create expected golden files.**

`tests/pmf-signal/expected/preflight-good.txt`:

```
Loading prior diligence for preflight-good:
  ✓ founder-check: 1 founder(s) (founder-jane-doe.md)
  ✓ market-problem: _context.md present, market-problem.md present
  ✓ competitive-landscape: present
  ✓ market-sizing: present
  ✓ pitch sources: inputs/deck.md
EXIT=0
```

`tests/pmf-signal/expected/preflight-missing.txt`:

```
pmf-signal cannot start — upstream diligence is incomplete for deal "preflight-missing":
  ✗ deals/preflight-missing/founder-*.md (run: dudu:founder-check)
  ✗ deals/preflight-missing/competitive-landscape.md (run: dudu:competitive-landscape)
The simplest path is to run dudu:diligence, which orchestrates the full chain.
EXIT=2
```

`tests/pmf-signal/expected/preflight-already-done.txt`:

```
Artifact already exists at deals/preflight-already-done/pmf-signal.md. Pass --force to overwrite.
EXIT=3
```

- [ ] **Step 6: Run the test — expect failures (script doesn't exist).**

```bash
bash tests/pmf-signal/run.sh
```

Expected: `FAIL: preflight-good`, `FAIL: preflight-missing`, `FAIL: preflight-already-done` — preflight script not yet implemented.

- [ ] **Step 7: Implement `scripts/pmf-signal-preflight.py`.**

```python
#!/usr/bin/env python3
"""Pre-flight check for dudu:pmf-signal.

Usage: python3 scripts/pmf-signal-preflight.py <deal-dir> [--force]

Verifies every required upstream artifact exists. Prints either a
loading ledger (exit 0) or a missing-artifact failure (exit 2).
If pmf-signal.md already exists and --force was not passed, prints
the idempotency message and exits 3.

Stdlib only.
"""

from __future__ import annotations

import sys
from pathlib import Path


def fail_missing(slug: str, missing: list[tuple[str, str]]) -> int:
    print(f'pmf-signal cannot start — upstream diligence is incomplete for deal "{slug}":')
    for path, hint in missing:
        print(f"  ✗ {path} (run: {hint})")
    print("The simplest path is to run dudu:diligence, which orchestrates the full chain.")
    return 2


def fail_already_done(deal_dir: Path) -> int:
    rel = f"deals/{deal_dir.name}/pmf-signal.md"
    print(f"Artifact already exists at {rel}. Pass --force to overwrite.")
    return 3


def loading_ledger(deal_dir: Path, founders: list[Path], pitch_sources: list[str]) -> int:
    slug = deal_dir.name
    print(f"Loading prior diligence for {slug}:")
    names = ", ".join(p.name for p in founders)
    print(f"  ✓ founder-check: {len(founders)} founder(s) ({names})")
    print(f"  ✓ market-problem: _context.md present, market-problem.md present")
    print(f"  ✓ competitive-landscape: present")
    print(f"  ✓ market-sizing: present")
    print(f"  ✓ pitch sources: {', '.join(pitch_sources)}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: pmf-signal-preflight.py <deal-dir> [--force]", file=sys.stderr)
        return 64
    deal_dir = Path(argv[1])
    force = "--force" in argv[2:]
    if not deal_dir.is_dir():
        print(f"deal directory not found: {deal_dir}", file=sys.stderr)
        return 64
    slug = deal_dir.name

    # Idempotency
    pmf_artifact = deal_dir / "pmf-signal.md"
    if pmf_artifact.exists() and not force:
        return fail_already_done(deal_dir)

    # Required artifact discovery
    missing: list[tuple[str, str]] = []

    pitch_candidates = sorted((deal_dir / "inputs").glob("deck.*")) if (deal_dir / "inputs").is_dir() else []
    if not pitch_candidates:
        missing.append((f"deals/{slug}/inputs/deck.<ext>", "place the founder's deck under inputs/"))

    if not (deal_dir / "personas" / "_context.md").exists():
        missing.append((f"deals/{slug}/personas/_context.md", "dudu:market-problem"))

    if not (deal_dir / "market-problem.md").exists():
        missing.append((f"deals/{slug}/market-problem.md", "dudu:market-problem"))

    founders = sorted(deal_dir.glob("founder-*.md"))
    if not founders:
        missing.append((f"deals/{slug}/founder-*.md", "dudu:founder-check"))

    if not (deal_dir / "competitive-landscape.md").exists():
        missing.append((f"deals/{slug}/competitive-landscape.md", "dudu:competitive-landscape"))

    if not (deal_dir / "market-sizing.md").exists():
        missing.append((f"deals/{slug}/market-sizing.md", "dudu:market-sizing"))

    if missing:
        return fail_missing(slug, missing)

    pitch_sources = [f"inputs/{p.name}" for p in pitch_candidates]
    return loading_ledger(deal_dir, founders, pitch_sources)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

Make it executable:

```bash
chmod +x scripts/pmf-signal-preflight.py
```

- [ ] **Step 8: Run the test — expect PASS on all three cases.**

```bash
bash tests/pmf-signal/run.sh
```

If a case still fails, diff expected vs actual, fix the message in the script (the expected file is the contract — match it exactly).

- [ ] **Step 9: Commit.**

```bash
git add scripts/pmf-signal-preflight.py tests/pmf-signal/
git commit -m "Add pmf-signal pre-flight script with golden-file tests"
```

---

## Task 4: Pre-flight section in SKILL.md

**Files:**
- Modify: `skills/pmf-signal/SKILL.md`

- [ ] **Step 1: Replace the `## Pre-flight` placeholder with the following content.**

```markdown
## Inputs

Required (all from prior dudu skills — see Pre-flight hard gate):

- Deal slug
- `deals/<slug>/inputs/deck.<ext>` (or pasted pitch text)
- `deals/<slug>/personas/_context.md`
- `deals/<slug>/market-problem.md`
- `deals/<slug>/founder-*.md` (one or more)
- `deals/<slug>/competitive-landscape.md`
- `deals/<slug>/market-sizing.md`

Optional:
- Company website URL (homepage + pricing + about) for stage 0 enrichment.
- Public statements list (URLs to interviews / podcasts / blog posts).
- `--n <int>` total personas (default 60; min 15; max 200).
- `--frames <comma-list>` restrict to enabled frames.
- `--no-network` skip stage 5.
- `--public-only` stage 5 without authed LinkedIn.
- `--force` overwrite existing artifacts.

## Pre-flight (hard gate)

Run `python3 scripts/pmf-signal-preflight.py deals/<slug>` first. The script verifies every upstream artifact exists, prints the loading ledger on success, or lists missing artifacts and exits non-zero on failure.

- Exit 0: prior diligence complete; print the loading ledger to the user, then proceed to Stage 0.
- Exit 2: upstream missing. Surface the script's stdout to the user verbatim and stop. Do not auto-trigger upstream skills — the user controls heavy spend.
- Exit 3: pmf-signal already done. Surface the message and stop. The user must pass `--force` to overwrite.

After exit 0, also confirm:
- A pitch source exists (`inputs/deck.<ext>` is required; a website URL is optional and is fetched live in Stage 0).
- The user passed any optional flags (`--n`, `--frames`, `--no-network`, `--public-only`).
```

- [ ] **Step 2: Commit.**

```bash
git add skills/pmf-signal/SKILL.md
git commit -m "Add pre-flight section to pmf-signal SKILL.md"
```

---

## Task 5: Stage 0 — Claim ledger ingestion (SKILL.md prose)

**Files:**
- Modify: `skills/pmf-signal/SKILL.md`

- [ ] **Step 1: Replace the `## Stage 0` placeholder with the full claim-ingestion playbook.** Use the spec's Stage 0 section verbatim, adapted to be actionable instructions for Claude.

Insert this exact content under `## Stage 0 — Claim ledger ingestion`:

````markdown
## Stage 0 — Claim ledger ingestion

Goal: produce `deals/<slug>/pitch.yaml` — a structured ledger of every claim the founder/company makes, with a verification method per claim.

### Sources

1. The deck at `inputs/deck.<ext>` (always — required by pre-flight).
2. The company website if a URL was provided — fetch homepage, pricing page, about page (3 fetches max).
3. Each `founder-*.md` (already on disk from `dudu:founder-check`).
4. Public statements list if provided — fetch each URL with the WebFetch tool, max 5 fetches total.

Total stage-0 fetch budget: 8.

### Extraction

Read every source and extract claims into the schema below. Each claim is a discrete row with mandatory `source` provenance and `verification_method`.

```yaml
product:
  name: <string>
  one_liner: <string>
  category: <string>

target_market:
  stated_icp: <founder's exact words>
  stated_segments: [<string>]

claims:
  - claim_id: c-001
    claim: "<verbatim claim text>"
    category: <pain | wtp | urgency | trigger | switching | gtm-distribution | gtm-channel | traction | revenue | customer-count | growth-rate | retention | nps | founder-background | founder-prior-venture | founder-credentials | market-size | tam | sam | competitive | unique-advantage | moat-claim>
    source: "<file + page/section/URL>"
    verification_method: <persona-reaction | cross-artifact | external-evidence>
    # ... category-specific extras (see below)

unstated_assumptions:
  - assumption: "<inferred unstated belief>"
    derived_from: "<source(s)>"
    promoted_to_claim: <claim_id if already a claim, else null>
```

### Auto-classification rules

Assign `verification_method` automatically by category:

- `pain | wtp | urgency | trigger | switching | gtm-distribution | gtm-channel` → `persona-reaction`
- `founder-background | founder-prior-venture | founder-credentials` → `cross-artifact`, `cross_artifact: founder-check`, `cross_artifact_target: founder-<slug>.md`
- `market-size | tam | sam` → `cross-artifact`, `cross_artifact: market-sizing`, `cross_artifact_target: market-sizing.md`
- `competitive | unique-advantage | moat-claim` → `cross-artifact`, `cross_artifact: competitive-landscape`, `cross_artifact_target: competitive-landscape.md`
- `traction | revenue | customer-count | growth-rate | retention | nps` → `external-evidence`, populate `external_check: [<recipe-slugs>]` from the table below
- Anything else: emit the claim with `verification_method: persona-reaction` and a `flag: classifier-uncertain` field; surface for user confirmation.

External-evidence recipe defaults by category:

| Category | Default recipes |
|---|---|
| `customer-count` | `customer-list-on-website`, `testimonial-count` |
| `revenue` | `wayback-machine-claim-history` (mark `flag_if_unverifiable: requires-data-room`) |
| `growth-rate` | `wayback-machine-claim-history` (mark `flag_if_unverifiable: requires-data-room`) |
| `retention | nps` | (none in v1) — emit with `flag_if_unverifiable: requires-data-room` |
| `traction` (generic) | `customer-list-on-website`, `testimonial-count` |

### User confirmation gate

After writing `pitch.yaml`, print a one-screen summary listing each claim with its assigned verification method, and ask:

> Confirmed claim ledger above. Reply with `ok` to proceed, or list claim IDs to re-classify (e.g. `c-007:cross-artifact:competitive-landscape`).

Block on user response. Apply re-classifications in place, then proceed to Stage 1.

### Validation

Run `python3 scripts/pmf-signal-validate-pitch.py deals/<slug>/pitch.yaml`. Implementation in Task 7 — for now, ensure every claim has all four required fields (`claim_id`, `claim`, `category`, `source`, `verification_method`).

### Parallelization

Sources 1–4 are independent. Dispatch worker subagents per source category if all four are present; otherwise run inline. See `lib/research-protocol.md` § Parallelization.
````

- [ ] **Step 2: Commit.**

```bash
git add skills/pmf-signal/SKILL.md
git commit -m "Add Stage 0 claim ingestion playbook to pmf-signal SKILL.md"
```

---

## Task 6: pitch.yaml validator (TDD)

**Files:**
- Create: `scripts/pmf-signal-validate-pitch.py`
- Create: `tests/pmf-signal/fixtures-yaml/pitch-good.yaml`
- Create: `tests/pmf-signal/fixtures-yaml/pitch-missing-fields.yaml`
- Create: `tests/pmf-signal/fixtures-yaml/pitch-bad-method.yaml`
- Create: `tests/pmf-signal/expected/validate-pitch-good.txt`
- Create: `tests/pmf-signal/expected/validate-pitch-missing.txt`
- Create: `tests/pmf-signal/expected/validate-pitch-bad-method.txt`
- Modify: `tests/pmf-signal/run.sh`

- [ ] **Step 1: Create the three pitch.yaml fixtures.**

`tests/pmf-signal/fixtures-yaml/pitch-good.yaml`:

```yaml
product:
  name: ExampleCo
  one_liner: tax automation for SA freelancers
  category: fintech
target_market:
  stated_icp: SA freelance designers near VAT threshold
  stated_segments: [freelance-creatives]
claims:
  - claim_id: c-001
    claim: "SA freelancers lose 2 days/quarter to SARS"
    category: pain
    source: "deck p.3"
    verification_method: persona-reaction
  - claim_id: c-010
    claim: "200 paying customers"
    category: customer-count
    source: "deck p.4"
    verification_method: external-evidence
    external_check: ["customer-list-on-website", "testimonial-count"]
unstated_assumptions: []
```

`tests/pmf-signal/fixtures-yaml/pitch-missing-fields.yaml`:

```yaml
product:
  name: ExampleCo
target_market:
  stated_icp: SA freelancers
claims:
  - claim_id: c-001
    claim: "missing source field"
    category: pain
    verification_method: persona-reaction
```

`tests/pmf-signal/fixtures-yaml/pitch-bad-method.yaml`:

```yaml
product:
  name: ExampleCo
target_market:
  stated_icp: x
claims:
  - claim_id: c-001
    claim: "x"
    category: pain
    source: "deck p.1"
    verification_method: telepathy
```

- [ ] **Step 2: Create expected golden files.**

`tests/pmf-signal/expected/validate-pitch-good.txt`:

```
pitch.yaml OK: 2 claim(s); methods used: persona-reaction(1), external-evidence(1)
EXIT=0
```

`tests/pmf-signal/expected/validate-pitch-missing.txt`:

```
pitch.yaml validation failed:
  claim c-001: missing required field 'source'
EXIT=4
```

`tests/pmf-signal/expected/validate-pitch-bad-method.txt`:

```
pitch.yaml validation failed:
  claim c-001: verification_method 'telepathy' is not one of {persona-reaction, cross-artifact, external-evidence}
EXIT=4
```

- [ ] **Step 3: Append three new test cases to `tests/pmf-signal/run.sh`.** Add a second helper that takes a YAML path:

```bash
run_yaml_case() {
    local name="$1"
    local script="$2"
    local fixture="$script_dir/fixtures-yaml/$name.yaml"
    local expected="$script_dir/expected/$script-$name.txt"
    local actual
    actual="$(python3 "$script_dir/../../scripts/pmf-signal-$script.py" "$fixture" 2>&1; echo "EXIT=$?")"
    local expected_contents
    expected_contents="$(cat "$expected")"
    if [[ "$actual" == "$expected_contents" ]]; then
        echo "PASS: $script-$name"
    else
        echo "FAIL: $script-$name"
        echo "--- expected ---"
        echo "$expected_contents"
        echo "--- actual ---"
        echo "$actual"
        echo "--- end ---"
        fail=1
    fi
}

run_yaml_case pitch-good validate-pitch
run_yaml_case pitch-missing-fields validate-pitch
run_yaml_case pitch-bad-method validate-pitch
```

- [ ] **Step 4: Run tests — expect FAIL on validator cases (script not yet written).**

```bash
bash tests/pmf-signal/run.sh
```

- [ ] **Step 5: Implement `scripts/pmf-signal-validate-pitch.py`.** Stdlib only — use a tiny YAML subset parser since we cannot rely on PyYAML.

Use a vendored minimal YAML parser approach: since stdlib does not include YAML, and prior dudu scripts are stdlib-only, write a permissive line-based parser that handles only the subset our schema uses (mappings, lists, scalars; no anchors, flow style only for inline lists).

```python
#!/usr/bin/env python3
"""Validate the shape of pitch.yaml.

Usage: python3 scripts/pmf-signal-validate-pitch.py <path-to-pitch.yaml>

Stdlib only. Uses a small line-based parser for the YAML subset
emitted by Stage 0.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_METHODS = {"persona-reaction", "cross-artifact", "external-evidence"}
REQUIRED_CLAIM_FIELDS = ("claim_id", "claim", "category", "source", "verification_method")


def parse_yaml_subset(text: str) -> dict:
    """Parse the Stage-0 YAML subset into a dict.

    Supports: top-level mappings, nested mappings (2-space indent),
    list-of-mappings under a key, scalar values, double-quoted strings,
    inline flow lists like [a, b, c]. Comments after '#' are stripped.
    Does NOT support anchors, multiline strings, complex flows.
    """
    root: dict = {}
    stack: list[tuple[int, object]] = [(-1, root)]

    def strip_comment(s: str) -> str:
        in_quote = False
        for i, ch in enumerate(s):
            if ch == '"':
                in_quote = not in_quote
            elif ch == "#" and not in_quote:
                return s[:i].rstrip()
        return s.rstrip()

    def parse_scalar(v: str):
        v = v.strip()
        if v == "":
            return None
        if v.startswith('"') and v.endswith('"'):
            return v[1:-1]
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            if not inner:
                return []
            parts = [p.strip().strip('"') for p in inner.split(",")]
            return parts
        if v in ("null", "~"):
            return None
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            pass
        return v

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = strip_comment(raw)
        if not line.strip():
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        # Pop stack until parent indent < current
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]

        if content.startswith("- "):
            # list item
            item_body = content[2:]
            if isinstance(parent, list):
                if ":" in item_body and not item_body.startswith('"'):
                    new_map: dict = {}
                    parent.append(new_map)
                    stack.append((indent, new_map))
                    # process the rest of this line as a key:value in new_map
                    key, _, val = item_body.partition(":")
                    new_map[key.strip()] = parse_scalar(val) if val.strip() else {}
                    if not val.strip():
                        # nested mapping starts on next line
                        stack.append((indent + 2, new_map[key.strip()] if isinstance(new_map[key.strip()], dict) else new_map))
                else:
                    parent.append(parse_scalar(item_body))
            else:
                raise ValueError(f"unexpected list item under non-list at line {i+1}")
        elif ":" in content:
            key, _, val = content.partition(":")
            key = key.strip()
            val = val.strip()
            if isinstance(parent, dict):
                if val == "":
                    # peek next line to decide list vs map
                    j = i + 1
                    while j < len(lines) and not strip_comment(lines[j]).strip():
                        j += 1
                    if j < len(lines):
                        nxt = strip_comment(lines[j])
                        nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                        if nxt_indent > indent and nxt.strip().startswith("- "):
                            parent[key] = []
                            stack.append((indent, parent[key]))
                        else:
                            parent[key] = {}
                            stack.append((indent, parent[key]))
                    else:
                        parent[key] = None
                else:
                    parent[key] = parse_scalar(val)
            else:
                raise ValueError(f"unexpected mapping key under non-dict at line {i+1}")
        else:
            raise ValueError(f"could not parse line {i+1}: {raw!r}")
        i += 1

    return root


def validate(doc: dict) -> list[str]:
    errs: list[str] = []
    claims = doc.get("claims") or []
    if not isinstance(claims, list):
        errs.append("top-level 'claims' must be a list")
        return errs
    for c in claims:
        if not isinstance(c, dict):
            errs.append("each claim must be a mapping")
            continue
        cid = c.get("claim_id", "<unknown>")
        for f in REQUIRED_CLAIM_FIELDS:
            if f not in c or c.get(f) in (None, ""):
                errs.append(f"claim {cid}: missing required field '{f}'")
        m = c.get("verification_method")
        if m and m not in ALLOWED_METHODS:
            allowed = "{" + ", ".join(sorted(ALLOWED_METHODS)) + "}"
            errs.append(f"claim {cid}: verification_method '{m}' is not one of {allowed}")
    return errs


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: pmf-signal-validate-pitch.py <pitch.yaml>", file=sys.stderr)
        return 64
    path = Path(argv[1])
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        return 64
    text = path.read_text(encoding="utf-8")
    try:
        doc = parse_yaml_subset(text)
    except ValueError as e:
        print(f"pitch.yaml parse error: {e}")
        return 4
    errs = validate(doc)
    if errs:
        print("pitch.yaml validation failed:")
        for e in errs:
            print(f"  {e}")
        return 4
    method_counts: dict[str, int] = {}
    for c in doc.get("claims") or []:
        m = c.get("verification_method")
        if m:
            method_counts[m] = method_counts.get(m, 0) + 1
    method_str = ", ".join(f"{k}({v})" for k, v in sorted(method_counts.items()))
    print(f"pitch.yaml OK: {len(doc.get('claims') or [])} claim(s); methods used: {method_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

```bash
chmod +x scripts/pmf-signal-validate-pitch.py
```

- [ ] **Step 6: Run tests — expect PASS on all three validator cases.**

```bash
bash tests/pmf-signal/run.sh
```

If the YAML parser blows up on edge cases in the fixtures, simplify the fixtures rather than over-extending the parser. The parser only needs to handle the subset Stage 0 emits.

- [ ] **Step 7: Commit.**

```bash
git add scripts/pmf-signal-validate-pitch.py tests/pmf-signal/fixtures-yaml/ tests/pmf-signal/expected/validate-pitch-*.txt tests/pmf-signal/run.sh
git commit -m "Add pitch.yaml validator with golden tests"
```

---

## Task 7: Stage 1 — Frame definition (SKILL.md prose)

**Files:**
- Modify: `skills/pmf-signal/SKILL.md`

- [ ] **Step 1: Replace the `## Stage 1` placeholder with the full content.**

````markdown
## Stage 1 — Frame definition

Goal: produce `deals/<slug>/personas/frames.yaml` — 1–4 frames that drive the rest of the pipeline.

### Frame purposes (v1)

| Frame purpose | Asking lens | Captured per persona in stage 3a |
|---|---|---|
| `pmf-validation` | "Would you use this? What makes you say no?" | use intent, top hesitation, would-pay (Y/N + band), kill-switch reason |
| `founder-claim-validation` | Per `pitch.yaml` persona-reaction claim → agree/partial/disagree + verbatim | per-claim verdict + contradicting quote |
| `jtbd-discovery` | JTBD: job, forces, anxieties, progress | pain triggers, switching forces, current solution |
| `bant-qualification` | BANT: budget, authority, need, timeline | budget band, authority level, urgency, timeline |

Default v1 enabled: `pmf-validation`, `founder-claim-validation`, `jtbd-discovery`. `bant-qualification` ships built-in but disabled by default.

### Per-frame definition

For each enabled frame, derive:

1. **Segments** — 1–3 customer types this frame applies to. Source from `pitch.yaml.target_market.stated_segments` and `_context.md`'s segment evidence. Total segments across all frames cap at 5.
2. **Must-cover cells** — 8–12 attribute combinations per segment that the population MUST cover. The founder's stated ICP center is always one of these. Use Layer 1 attribute axes (role, geography, stage, vertical, team_size, revenue_band, buying_authority) to enumerate.
3. **Distribution sampling profile** — weighted distributions for the remaining persona slots. Example: `role: {founder-ceo: 0.6, cofounder-cto: 0.2, ops-manager: 0.15, other: 0.05}`.

### Output: frames.yaml

```yaml
frames:
  - frame_id: <slug>.pmf-validation
    purpose: pmf-validation
    enabled: true
    segments:
      - segment_id: cape-town-saas-founder
        must_cover:
          - {role: founder-ceo, geography: ZA-Western-Cape, stage: pre-seed, vertical: b2b-saas, team_size: 3, revenue_band_mrr_zar: [150000, 300000], buying_authority: sole}
          - # ... 7-11 more cells
        distribution:
          role: {founder-ceo: 0.6, cofounder-cto: 0.2, ops-manager: 0.15, other: 0.05}
          # ... other axes
  - frame_id: <slug>.founder-claim-validation
    # ...
  - frame_id: <slug>.jtbd-discovery
    # ...
```

### Budget allocation across frames

Default total N=60. Allocate:

- 50% to `pmf-validation` (broad)
- 30% to `founder-claim-validation` (focused on the founder's stated ICP center)
- 20% to `jtbd-discovery` (pain-shape exploration)

Adjust if `--n` was passed.
````

- [ ] **Step 2: Commit.**

```bash
git add skills/pmf-signal/SKILL.md
git commit -m "Add Stage 1 frame-definition playbook"
```

---

## Task 8: Stage 2 — Population synthesis (SKILL.md prose, parts 1 & 2)

**Files:**
- Modify: `skills/pmf-signal/SKILL.md`

- [ ] **Step 1: Replace the `## Stage 2` placeholder with the seed-mining and 5W construction sections.** Use the spec's Stage 2 content.

Insert this exact content under `## Stage 2 — Population synthesis`:

````markdown
## Stage 2 — Population synthesis (5W scenario-driven)

Goal: produce `deals/<slug>/personas/rows/p-<id>.yaml` × N — a structured population built by causal reasoning from scenario seeds, never by attribute fill.

### 2.1 Scenario-seed mining

Read `_context.md` and extract scenario seeds — specific triggering moments grounded in cited evidence. Examples: a Reddit complaint quote, a regulatory event date, a growth milestone described in an interview, a switching event mentioned in a review.

Each seed:

```yaml
seed_id: s-014
trigger: "hit VAT threshold mid-fundraise, mid-Q3"
trigger_type: <regulatory-growth-collision | switching-cost | onboarding-friction | scaling-stress | exit-prep | onboarding-trust | other>
source_quote: "<verbatim quote from _context.md>"
source_ref: "_context.md L<line>"
implied_attributes:
  stage: [<list of plausible stages>]
  geography: <free-text region>
  vertical: <free-text vertical hint>
```

Aim for 30–60 seeds total. Each must have a verbatim source quote. If you can't find a seed for a particular trigger type, that's evidence of a context-bundle gap — note it for the refusals report.

Save seeds to `deals/<slug>/personas/seeds.yaml`.

### 2.2 Mode-collapse pre-check

Run `python3 scripts/pmf-signal-mode-collapse.py deals/<slug>/personas/seeds.yaml` (implementation in Task 10).

If the script reports `MODE-COLLAPSE` (top-1 trigger_type share > 0.6), surface to user:

> Scenario-seed pool is heavily concentrated in `<trigger_type>` (X% of seeds). The synthetic population will inherit this bias. Options: (a) extend `_context.md` with sources covering other triggers, then re-run; (b) proceed knowing the population will be biased. Reply `proceed` or `extend`.

Block on user response. If `proceed`, continue but flag in `refusals.md` and the final report.

### 2.3 5W persona construction (strict)

For each persona slot, walk the 5W chain in order. **All five must be filled and traceable, or generation fails for that slot** — the failure goes to `refusals.md`, which is itself diligence signal.

1. **Why (now)** — sample a scenario seed from `seeds.yaml`. The seed becomes Layer 0.
2. **When** — temporal shape: `quarterly | continuous | trigger-only | one-time-haunting`.
3. **Who** — derived from the scenario; do not pre-decide. Role, stage, demographics, authority must follow causally from the seed + frame's must-cover cell (if generating for a must-cover slot).
4. **Where** — physical + channel context (e.g. "kitchen table 11pm, fundraise data room open in next tab").
5. **What** — verbatim phrasing of how this persona talks and acts. This is the Layer 3 voice fuel.

Layer 1 attributes (clustering) and Layer 2 framework-specific fields are OUTPUTS of this chain.

### 2.4 Persona row schema

Each persona is one structured record at `deals/<slug>/personas/rows/p-<id>.yaml`. Schema:

```yaml
persona_id: p-007
schema_version: 1
frame_id: <frame_id>
segment: <segment_id>
generated_at: <ISO timestamp>

scenario:                            # Layer 0 — provenance unit
  trigger: "<seed.trigger>"
  trigger_type: "<seed.trigger_type>"
  source_seed: <seed_id>
  source_ref: "<seed.source_ref>"
  when: <quarterly | continuous | trigger-only | one-time-haunting>
  where: "<physical + channel context>"
  why_unsolved: "<why current solutions don't address this>"

attributes:                          # Layer 1 — clustering dimensions
  role: <string>
  geography: <string>
  stage: <string>
  vertical: <string>
  team_size: <int>
  revenue_band_mrr_zar: [<low>, <high>]
  buying_authority: <sole | shared | committee>

# Layer 2 — pick the right block for the frame_id's purpose:
framework_jtbd:                       # only present if frame_id ends with .jtbd-discovery
  pain_intensity: <1-10>
  pain_frequency: <quarterly | continuous | trigger-only>
  current_solution: <string>
  switching_forces:
    push: <string>
    pull: <string>
    anxiety: <string>
    habit: <string>
  progress_blockers: [<string>]

framework_bant:                       # only if frame_id ends with .bant-qualification
  budget_band_annual_usd: [<low>, <high>]
  authority_level: <sole | influencer | blocker | none>
  need_urgency: <1-10>
  timeline_to_purchase: <quarter | half | year | longer>

framework_pmf_validation:             # only if frame_id ends with .pmf-validation
  use_intent_prior: <high | medium | low>
  primary_anxiety_axis: <cost | trust | switching | integration | other>

framework_founder_claim:              # only if frame_id ends with .founder-claim-validation
  centered_on_claim: <claim_id>       # the one claim this row most pressures

voice:                                # Layer 3 — NLP / matching fuel (every frame)
  pain_phrases: [<string>]            # 3-5
  objections: [<string>]              # 2-3
  purchase_trigger: <string>

discoverability_signals:
  job_titles: [<string>]
  communities: [<string>]
  post_patterns: [<string>]
  query_strings: [<string>]

context_grounding:
  - {claim: <string>, source: <_context.md ref>}
fabrication_flags: [<string>]         # populated when LLM had to extrapolate
```

### 2.5 Generation strategy (stratified hybrid)

1. Enumerate must-cover cells across all enabled frames (≈10–12 per frame). Generate 1–3 personas per cell. The founder's stated ICP center is always a must-cover cell — those rows feed founder-claim-validation directly.
2. Distribution-sample the remaining slots up to N (default 60), weighted by the frame budget allocation in Stage 1.
3. **Refuse** any slot where the 5W chain cannot be grounded in `_context.md`. Append to `personas/refusals.md`:

```markdown
# Population synthesis refusals

## Refusal 1
**Slot:** frame=<frame_id>, must_cover=<cell>
**Reason:** could not ground 5W chain — no seed in `_context.md` covers <trigger description>
**Implication:** context bundle gap; re-run `dudu:market-problem` with sources covering <X>
```

### 2.6 Parallelization

Population synthesis is embarrassingly parallel per frame. Dispatch one worker subagent per enabled frame using your host's parallel-agent dispatch primitive (see `lib/research-protocol.md` § Parallelization).

Each subagent receives:
- Full `_context.md` text
- Full `pitch.yaml`
- The frame's `frames.yaml` entry
- The seed pool (full `seeds.yaml`)
- This row schema

Returns: row YAML files as text. Main session writes them to `personas/rows/p-<id>.yaml` (assigning `persona_id` sequentially) and the `refusals.md` accumulator.
````

- [ ] **Step 2: Commit.**

```bash
git add skills/pmf-signal/SKILL.md
git commit -m "Add Stage 2 population-synthesis playbook"
```

---

## Task 9: Mode-collapse heuristic (TDD)

**Files:**
- Create: `scripts/pmf-signal-mode-collapse.py`
- Create: `tests/pmf-signal/fixtures-yaml/seeds-good.yaml`
- Create: `tests/pmf-signal/fixtures-yaml/seeds-collapsed.yaml`
- Create: `tests/pmf-signal/expected/mode-collapse-seeds-good.txt`
- Create: `tests/pmf-signal/expected/mode-collapse-seeds-collapsed.txt`
- Modify: `tests/pmf-signal/run.sh`

- [ ] **Step 1: Create seed fixtures.**

`tests/pmf-signal/fixtures-yaml/seeds-good.yaml`:

```yaml
seeds:
  - {seed_id: s-1, trigger_type: regulatory-growth-collision}
  - {seed_id: s-2, trigger_type: switching-cost}
  - {seed_id: s-3, trigger_type: onboarding-friction}
  - {seed_id: s-4, trigger_type: regulatory-growth-collision}
  - {seed_id: s-5, trigger_type: scaling-stress}
  - {seed_id: s-6, trigger_type: exit-prep}
  - {seed_id: s-7, trigger_type: switching-cost}
  - {seed_id: s-8, trigger_type: onboarding-trust}
  - {seed_id: s-9, trigger_type: scaling-stress}
  - {seed_id: s-10, trigger_type: switching-cost}
```

`tests/pmf-signal/fixtures-yaml/seeds-collapsed.yaml`:

```yaml
seeds:
  - {seed_id: s-1, trigger_type: regulatory-growth-collision}
  - {seed_id: s-2, trigger_type: regulatory-growth-collision}
  - {seed_id: s-3, trigger_type: regulatory-growth-collision}
  - {seed_id: s-4, trigger_type: regulatory-growth-collision}
  - {seed_id: s-5, trigger_type: regulatory-growth-collision}
  - {seed_id: s-6, trigger_type: regulatory-growth-collision}
  - {seed_id: s-7, trigger_type: regulatory-growth-collision}
  - {seed_id: s-8, trigger_type: switching-cost}
  - {seed_id: s-9, trigger_type: regulatory-growth-collision}
  - {seed_id: s-10, trigger_type: regulatory-growth-collision}
```

- [ ] **Step 2: Create expected golden files.**

`tests/pmf-signal/expected/mode-collapse-seeds-good.txt`:

```
seed pool OK: 10 seed(s) across 6 trigger_type(s); top-1 share = 0.30
EXIT=0
```

`tests/pmf-signal/expected/mode-collapse-seeds-collapsed.txt`:

```
MODE-COLLAPSE: 10 seed(s) across 2 trigger_type(s); top-1 share = 0.90 (threshold 0.60)
EXIT=5
```

- [ ] **Step 3: Add test runner cases.**

```bash
run_yaml_case seeds-good mode-collapse
run_yaml_case seeds-collapsed mode-collapse
```

- [ ] **Step 4: Run — expect FAIL (script not yet written).**

- [ ] **Step 5: Implement the script.**

```python
#!/usr/bin/env python3
"""Mode-collapse pre-check for the seed pool.

Usage: python3 scripts/pmf-signal-mode-collapse.py <path-to-seeds.yaml>

Computes the top-1 trigger_type share. If > 0.60, prints MODE-COLLAPSE
and exits 5; otherwise prints OK and exits 0.

Stdlib only. Reuses the YAML parser from validate-pitch by importing
the file directly.
"""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

THRESHOLD = 0.60


def _load_parser():
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "_pmf_validate", here / "pmf-signal-validate-pitch.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load YAML parser from pmf-signal-validate-pitch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse_yaml_subset


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: pmf-signal-mode-collapse.py <seeds.yaml>", file=sys.stderr)
        return 64
    parse = _load_parser()
    text = Path(argv[1]).read_text(encoding="utf-8")
    doc = parse(text)
    seeds = doc.get("seeds") or []
    if not seeds:
        print("seed pool empty")
        return 5
    counts = Counter(s.get("trigger_type") for s in seeds)
    n = len(seeds)
    distinct = len(counts)
    top = counts.most_common(1)[0][1]
    share = top / n
    if share > THRESHOLD:
        print(
            f"MODE-COLLAPSE: {n} seed(s) across {distinct} trigger_type(s); "
            f"top-1 share = {share:.2f} (threshold {THRESHOLD:.2f})"
        )
        return 5
    print(
        f"seed pool OK: {n} seed(s) across {distinct} trigger_type(s); "
        f"top-1 share = {share:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

```bash
chmod +x scripts/pmf-signal-mode-collapse.py
```

- [ ] **Step 6: Run — expect PASS on both cases.**

```bash
bash tests/pmf-signal/run.sh
```

- [ ] **Step 7: Commit.**

```bash
git add scripts/pmf-signal-mode-collapse.py tests/pmf-signal/fixtures-yaml/seeds-*.yaml tests/pmf-signal/expected/mode-collapse-*.txt tests/pmf-signal/run.sh
git commit -m "Add seed-pool mode-collapse heuristic"
```

---

## Task 10: Stage 3a — Persona pitch-reaction (SKILL.md prose)

**Files:**
- Modify: `skills/pmf-signal/SKILL.md`

- [ ] **Step 1: Replace the `## Stage 3 — Claim verification` placeholder with a parent header and 3a content.**

````markdown
## Stage 3 — Claim verification (3a + 3b + 3c, parallel)

Stage 3 fans the claim ledger out into three independent verification paths. Run all three concurrently. Each emits per-claim verdicts. Stage 3 ends with `scripts/pmf-signal-consolidate-verdicts.py` merging them into `personas/verdicts.yaml`.

### Stage 3a — Persona pitch-reaction

For each persona row, run one structured reaction interview against the pitch + the persona-reaction-bound subset of `pitch.yaml.claims`.

#### Interview prompt (dispatched to persona subagent)

> You are persona [persona_id]: [render persona row's scenario.trigger, attributes, voice]. Stay in character. Use phrases from your `voice.pain_phrases` and `voice.objections` where natural.
>
> Here is the pitch you are being shown:
>
> [render `pitch.yaml.product`, `pitch.yaml.target_market`, and the full pitch text]
>
> React honestly:
>
> 1. Would you use this? Why or why not? Answer `yes`, `no`, or `yes-with-caveats`, then 1–2 sentences in your voice.
> 2. What is your single biggest hesitation? Answer in your voice.
> 3. Would you pay for this? Answer `yes`, `no`, or `maybe`. If yes, name a price ceiling above which you'd say no.
> 4. What would make you say no immediately? Answer in your voice (this is your kill_switch).
> 5. For each of the following founder claims, give a verdict (`agree | partial | disagree`) AND a verbatim quote from yourself supporting that verdict:
>
>    [render the persona-reaction-bound claims from pitch.yaml — id + claim text]

#### Output schema (stored at `personas/reactions/p-<id>.yaml`)

```yaml
persona_id: p-007
reaction_at: <ISO timestamp>
schema_version: 1
would_use: <yes | no | yes-with-caveats>
biggest_hesitation: "<verbatim>"
willing_to_pay: <yes | no | maybe>
wtp_ceiling_zar_per_month: <int or null>
kill_switch: "<verbatim>"
claim_responses:
  - claim_id: c-001
    verdict: <agree | partial | disagree>
    verbatim: "<verbatim>"
  - # ...
provenance:
  voice_phrases_used: [<phrase>]
  context_grounding: [<_context.md ref>]
```

#### Parallelization

Dispatch worker subagents in batches of 20 personas per subagent. Each subagent owns its batch's reactions and returns the YAML files as text. Main session writes them to disk.
````

- [ ] **Step 2: Commit.**

```bash
git add skills/pmf-signal/SKILL.md
git commit -m "Add Stage 3a persona pitch-reaction playbook"
```

---

## Task 11: Stage 3b — Cross-artifact verification (SKILL.md prose)

**Files:**
- Modify: `skills/pmf-signal/SKILL.md`

- [ ] **Step 1: Append the 3b section directly after 3a in `## Stage 3`.**

````markdown
### Stage 3b — Cross-artifact verification

For each claim with `verification_method: cross-artifact`, verify against the named existing dudu artifact. Do **not** re-fetch external evidence — pmf-signal reads the artifact already produced by the prior dudu skill.

#### Per-claim procedure

1. Open `deals/<slug>/<cross_artifact_target>` (read-only).
2. Find passages relevant to the claim (LLM judgement, anchored on claim text + category + keywords).
3. Emit a verdict + supporting and/or contradicting verbatim quotes from the artifact, with line references.

#### Verdict shape (one file per claim, stored at `personas/verdicts-3b/<claim_id>.yaml`)

```yaml
claim_id: c-020
claim: "<verbatim claim text>"
verification_method: cross-artifact
cross_artifact: <founder-check | market-sizing | competitive-landscape>
cross_artifact_target: <filename>
verdict: <supports | partial | contradicts | no-evidence>
supporting_quotes:
  - {quote: "<verbatim>", location: "<file>:L<line>"}
contradicting_quotes:
  - {quote: "<verbatim>", location: "<file>:L<line>"}
verdict_rationale: "<1-3 sentences explaining the verdict>"
```

#### Parallelization

Group claims by `cross_artifact` (founder-check / market-sizing / competitive-landscape). Dispatch one worker subagent per group; each subagent receives the full text of its target artifact plus the claim list it owns.
````

- [ ] **Step 2: Commit.**

```bash
git add skills/pmf-signal/SKILL.md
git commit -m "Add Stage 3b cross-artifact verification playbook"
```

---

## Task 12: External-evidence recipes — customer_list and testimonial_count (TDD)

**Files:**
- Create: `scripts/pmf-signal-recipes/__init__.py`
- Create: `scripts/pmf-signal-recipes/customer_list.py`
- Create: `scripts/pmf-signal-recipes/testimonial_count.py`
- Create: `tests/pmf-signal/fixtures-recipes/customer-list-html-good/index.html`
- Create: `tests/pmf-signal/fixtures-recipes/testimonial-count-html-good/about.html`
- Create: `tests/pmf-signal/expected/recipe-customer-list-good.txt`
- Create: `tests/pmf-signal/expected/recipe-testimonial-count-good.txt`
- Modify: `tests/pmf-signal/run.sh`

**Note on architecture:** Recipes don't fetch URLs themselves — Claude does that with the WebFetch tool and saves the raw HTML to a known location. The recipes are pure functions: HTML in → finding string out. This keeps them testable.

- [ ] **Step 1: Create the package init.**

`scripts/pmf-signal-recipes/__init__.py`:

```python
"""External-evidence recipes for dudu:pmf-signal Stage 3c.

Each recipe is a pure function: takes HTML text (or a list of HTML texts),
returns a finding string suitable for embedding in a Stage-3c verdict.
"""
```

- [ ] **Step 2: Create the customer-list HTML fixture.**

`tests/pmf-signal/fixtures-recipes/customer-list-html-good/index.html`:

```html
<!doctype html>
<html><head><title>ExampleCo</title></head><body>
<section class="customers">
  <h2>Trusted by</h2>
  <img alt="Acme Corp logo" src="/logos/acme.svg">
  <img alt="Beta Inc logo" src="/logos/beta.svg">
  <img alt="Gamma Co logo" src="/logos/gamma.svg">
  <img alt="Delta logo" src="/logos/delta.svg">
  <img alt="Epsilon logo" src="/logos/epsilon.svg">
</section>
<section class="case-studies">
  <article><h3>Acme Corp case study</h3><p>...</p></article>
  <article><h3>Beta Inc case study</h3><p>...</p></article>
</section>
</body></html>
```

- [ ] **Step 3: Create expected golden file.**

`tests/pmf-signal/expected/recipe-customer-list-good.txt`:

```
homepage shows 5 named logo(s); 2 detailed case stud(ies)
EXIT=0
```

- [ ] **Step 4: Add a recipe test runner block to `run.sh`.**

```bash
run_recipe_case() {
    local recipe="$1"
    local fixture_name="$2"
    local fixture_dir="$script_dir/fixtures-recipes/$fixture_name"
    local expected="$script_dir/expected/recipe-$recipe-${fixture_name#${recipe}-html-}.txt"
    local actual
    actual="$(python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '$script_dir/../../scripts')
mod = __import__('pmf-signal-recipes.${recipe//-/_}', fromlist=['run'])
htmls = []
for p in sorted(Path('$fixture_dir').glob('*.html')):
    htmls.append(p.read_text(encoding='utf-8'))
print(mod.run(htmls))
" 2>&1; echo "EXIT=$?")"
    local expected_contents
    expected_contents="$(cat "$expected")"
    if [[ "$actual" == "$expected_contents" ]]; then
        echo "PASS: recipe-$recipe-${fixture_name#${recipe}-html-}"
    else
        echo "FAIL: recipe-$recipe-${fixture_name#${recipe}-html-}"
        echo "--- expected ---"
        echo "$expected_contents"
        echo "--- actual ---"
        echo "$actual"
        echo "--- end ---"
        fail=1
    fi
}

run_recipe_case customer-list customer-list-html-good
```

- [ ] **Step 5: Run — expect FAIL (recipe not yet written).**

```bash
bash tests/pmf-signal/run.sh
```

- [ ] **Step 6: Implement the customer_list recipe.**

`scripts/pmf-signal-recipes/customer_list.py`:

```python
"""Recipe: count distinct named customer logos and detailed case studies in HTML."""

from __future__ import annotations

import re

LOGO_ALT = re.compile(r'<img\b[^>]*\balt="([^"]+?)\s+logo"', re.IGNORECASE)
CASE_HEADING = re.compile(r"<h[1-6][^>]*>\s*([^<]+?)\s+case\s+study\s*</h[1-6]>", re.IGNORECASE)


def run(htmls: list[str]) -> str:
    logos: set[str] = set()
    cases = 0
    for html in htmls:
        for m in LOGO_ALT.finditer(html):
            logos.add(m.group(1).strip())
        cases += len(CASE_HEADING.findall(html))
    return f"homepage shows {len(logos)} named logo(s); {cases} detailed case stud(ies)"
```

- [ ] **Step 7: Run — expect PASS.**

- [ ] **Step 8: Create the testimonial fixture.**

`tests/pmf-signal/fixtures-recipes/testimonial-count-html-good/about.html`:

```html
<!doctype html>
<html><body>
<section class="testimonials">
  <blockquote class="testimonial">
    <p>"Best tool we've used."</p>
    <cite>— Jane Doe, Acme</cite>
  </blockquote>
  <blockquote class="testimonial">
    <p>"Saved us hours every week."</p>
    <cite>— John Smith, Beta</cite>
  </blockquote>
  <blockquote class="testimonial">
    <p>"Wouldn't ship without it."</p>
    <cite>— Pat Lee, Gamma</cite>
  </blockquote>
  <blockquote class="testimonial">
    <p>"Anonymous love."</p>
    <!-- no attribution -->
  </blockquote>
</section>
</body></html>
```

- [ ] **Step 9: Expected file.**

`tests/pmf-signal/expected/recipe-testimonial-count-good.txt`:

```
3 testimonial(s) with named attribution; 1 unattributed quote(s)
EXIT=0
```

- [ ] **Step 10: Add the runner case + implement the recipe.**

Append to `run.sh`:

```bash
run_recipe_case testimonial-count testimonial-count-html-good
```

`scripts/pmf-signal-recipes/testimonial_count.py`:

```python
"""Recipe: count testimonial blocks with vs without named attribution."""

from __future__ import annotations

import re

TESTIMONIAL = re.compile(
    r'<blockquote\b[^>]*\bclass="[^"]*testimonial[^"]*"[^>]*>(.*?)</blockquote>',
    re.IGNORECASE | re.DOTALL,
)
CITE = re.compile(r"<cite\b[^>]*>(.*?)</cite>", re.IGNORECASE | re.DOTALL)


def run(htmls: list[str]) -> str:
    named = 0
    unattributed = 0
    for html in htmls:
        for m in TESTIMONIAL.finditer(html):
            block = m.group(1)
            cite = CITE.search(block)
            if cite and cite.group(1).strip():
                named += 1
            else:
                unattributed += 1
    return f"{named} testimonial(s) with named attribution; {unattributed} unattributed quote(s)"
```

- [ ] **Step 11: Run — expect PASS on both recipes.**

```bash
bash tests/pmf-signal/run.sh
```

- [ ] **Step 12: Commit.**

```bash
git add scripts/pmf-signal-recipes/ tests/pmf-signal/fixtures-recipes/ tests/pmf-signal/expected/recipe-*.txt tests/pmf-signal/run.sh
git commit -m "Add customer-list and testimonial-count external-evidence recipes"
```

---

## Task 13: External-evidence recipe — wayback_history (TDD)

**Files:**
- Create: `scripts/pmf-signal-recipes/wayback_history.py`
- Create: `tests/pmf-signal/fixtures-recipes/wayback-history-html-good/snapshot-2025-08.html`
- Create: `tests/pmf-signal/fixtures-recipes/wayback-history-html-good/snapshot-2026-01.html`
- Create: `tests/pmf-signal/fixtures-recipes/wayback-history-html-good/snapshot-2026-04.html`
- Create: `tests/pmf-signal/expected/recipe-wayback-history-good.txt`
- Modify: `tests/pmf-signal/run.sh`

- [ ] **Step 1: Create three snapshot fixtures.**

`snapshot-2025-08.html`:

```html
<!doctype html>
<html><body>
<h1>ExampleCo</h1>
<p>Trusted by 12 companies.</p>
</body></html>
```

`snapshot-2026-01.html`:

```html
<!doctype html>
<html><body>
<h1>ExampleCo</h1>
<p>Trusted by 80 companies.</p>
</body></html>
```

`snapshot-2026-04.html`:

```html
<!doctype html>
<html><body>
<h1>ExampleCo</h1>
<p>Trusted by 200 companies.</p>
</body></html>
```

- [ ] **Step 2: Expected file.**

`tests/pmf-signal/expected/recipe-wayback-history-good.txt`:

```
3 snapshot(s); claim numbers found: [12, 80, 200]; trajectory: 12 → 80 → 200
EXIT=0
```

- [ ] **Step 3: Add runner case.**

```bash
run_recipe_case wayback-history wayback-history-html-good
```

- [ ] **Step 4: Implement the recipe.**

`scripts/pmf-signal-recipes/wayback_history.py`:

```python
"""Recipe: extract numeric claims from a sequence of Wayback snapshots and report the trajectory."""

from __future__ import annotations

import re
from pathlib import Path

NUMBER_NEAR_TRUSTED = re.compile(r"Trusted\s+by\s+([0-9][0-9,]*)\b", re.IGNORECASE)


def run(htmls: list[str]) -> str:
    numbers: list[int] = []
    for html in htmls:
        m = NUMBER_NEAR_TRUSTED.search(html)
        if m:
            numbers.append(int(m.group(1).replace(",", "")))
    if not numbers:
        return f"{len(htmls)} snapshot(s); no claim numbers extractable"
    trajectory = " → ".join(str(n) for n in numbers)
    return (
        f"{len(htmls)} snapshot(s); claim numbers found: {numbers}; "
        f"trajectory: {trajectory}"
    )
```

The runner block in Task 12 sorted the snapshot files lexicographically, so `2025-08 → 2026-01 → 2026-04` is the natural order. If the test fails because of ordering, sort by filename in the runner glob (already implicit via `sorted()`).

- [ ] **Step 5: Run — expect PASS.**

- [ ] **Step 6: Commit.**

```bash
git add scripts/pmf-signal-recipes/wayback_history.py tests/pmf-signal/fixtures-recipes/wayback-history-html-good/ tests/pmf-signal/expected/recipe-wayback-history-good.txt tests/pmf-signal/run.sh
git commit -m "Add wayback-history external-evidence recipe"
```

---

## Task 14: Stage 3c — External-evidence dispatcher (SKILL.md prose)

**Files:**
- Modify: `skills/pmf-signal/SKILL.md`

- [ ] **Step 1: Append the 3c section after 3b in `## Stage 3`.**

````markdown
### Stage 3c — External-evidence verification

For each claim with `verification_method: external-evidence`, run a bounded targeted web check.

**Budget caps:** 5 fetches per claim; 30 fetches total across stage 3c.

**Architecture:** Claude fetches URLs with WebFetch and saves raw HTML to `deals/<slug>/.tmp/3c/<claim_id>/<recipe>/<seq>.html`. Then for each claim, Claude calls the recipe Python module on the saved HTML files. The recipe returns a finding string; Claude composes the verdict.

#### Recipe library (v1)

| Recipe slug | URLs to fetch | Module | What it returns |
|---|---|---|---|
| `customer-list-on-website` | homepage + `/customers` + `/case-studies` (max 3) | `pmf-signal-recipes/customer_list.py` | "homepage shows N named logo(s); M detailed case stud(ies)" |
| `testimonial-count` | homepage + `/about` + `/testimonials` (max 3) | `pmf-signal-recipes/testimonial_count.py` | "X testimonial(s) with named attribution; Y unattributed quote(s)" |
| `wayback-machine-claim-history` | 3–5 Wayback snapshots of the relevant page | `pmf-signal-recipes/wayback_history.py` | "N snapshot(s); claim numbers found: [...]; trajectory: a → b → c" |

If a claim's category needs a recipe that's not in v1 (e.g. SEO ranking, G2 presence), emit the verdict with `flag_if_unverifiable: requires-data-room` and `verdict: requires-data-room`.

#### Calling a recipe (one-liner template)

```bash
python3 -c "import sys; sys.path.insert(0, 'scripts'); from pathlib import Path; \
mod = __import__('pmf-signal-recipes.customer_list', fromlist=['run']); \
htmls = [p.read_text(encoding='utf-8') for p in sorted(Path('deals/<slug>/.tmp/3c/<claim_id>/customer-list-on-website').glob('*.html'))]; \
print(mod.run(htmls))"
```

#### Verdict shape (one file per claim, stored at `personas/verdicts-3c/<claim_id>.yaml`)

```yaml
claim_id: c-010
claim: "<verbatim claim text>"
verification_method: external-evidence
external_check_results:
  - recipe: customer-list-on-website
    finding: "homepage shows 18 named logo(s); 7 detailed case stud(ies)"
    fetched: ["<url>", "<url>"]
  - recipe: testimonial-count
    finding: "12 testimonial(s) with named attribution; 0 unattributed quote(s)"
    fetched: ["<url>"]
verdict: <supports | partial | contradicts | insufficient-evidence-for-<X> | requires-data-room>
verdict_rationale: "<1-3 sentences synthesizing across recipes>"
flags: [<requires-data-room | classifier-uncertain | ...>]
```

#### Parallelization

Dispatch one worker subagent per claim. Concurrency cap: 5. Each subagent owns its 5-fetch budget for one claim.
````

- [ ] **Step 2: Commit.**

```bash
git add skills/pmf-signal/SKILL.md
git commit -m "Add Stage 3c external-evidence dispatcher playbook"
```

---

## Task 15: Verdict consolidation (TDD)

**Files:**
- Create: `scripts/pmf-signal-consolidate-verdicts.py`
- Create: `tests/pmf-signal/fixtures-yaml/consolidate-good/<deal-shaped fixture>`
- Create: `tests/pmf-signal/expected/consolidate-good.txt`
- Modify: `tests/pmf-signal/run.sh`

- [ ] **Step 1: Create the fixture deal directory with verdicts from all three sub-stages.**

```
tests/pmf-signal/fixtures-yaml/consolidate-good/
└── personas/
    ├── reactions/
    │   ├── p-001.yaml
    │   └── p-002.yaml
    ├── verdicts-3b/
    │   └── c-020.yaml
    └── verdicts-3c/
        └── c-010.yaml
```

`personas/reactions/p-001.yaml`:

```yaml
persona_id: p-001
claim_responses:
  - {claim_id: c-001, verdict: agree, verbatim: "yes I agree"}
  - {claim_id: c-003, verdict: disagree, verbatim: "no chance"}
```

`personas/reactions/p-002.yaml`:

```yaml
persona_id: p-002
claim_responses:
  - {claim_id: c-001, verdict: partial, verbatim: "kinda"}
  - {claim_id: c-003, verdict: disagree, verbatim: "no way"}
```

`personas/verdicts-3b/c-020.yaml`:

```yaml
claim_id: c-020
verification_method: cross-artifact
verdict: partial
verdict_rationale: "exit happened but no shareholder return"
```

`personas/verdicts-3c/c-010.yaml`:

```yaml
claim_id: c-010
verification_method: external-evidence
verdict: insufficient-evidence-for-200
verdict_rationale: "public surface area inconsistent with 200"
```

- [ ] **Step 2: Expected output.** This script writes a file (`personas/verdicts.yaml`) AND prints a summary. The expected golden compares the printed summary; the test will additionally assert the output file content.

`tests/pmf-signal/expected/consolidate-good.txt`:

```
consolidated 4 claim(s) → personas/verdicts.yaml
  persona-reaction: 2 claim(s) (c-001, c-003)
  cross-artifact: 1 claim(s) (c-020)
  external-evidence: 1 claim(s) (c-010)
EXIT=0
```

- [ ] **Step 3: Add runner case.** This time the helper takes the fixture as a directory.

```bash
run_consolidate_case() {
    local name="$1"
    local fixture="$script_dir/fixtures-yaml/$name"
    local expected="$script_dir/expected/$name.txt"
    local actual
    actual="$(python3 "$script_dir/../../scripts/pmf-signal-consolidate-verdicts.py" "$fixture" 2>&1; echo "EXIT=$?")"
    local expected_contents
    expected_contents="$(cat "$expected")"
    if [[ "$actual" == "$expected_contents" ]]; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        echo "--- expected ---"
        echo "$expected_contents"
        echo "--- actual ---"
        echo "$actual"
        echo "--- end ---"
        fail=1
    fi
    # cleanup so re-running tests is idempotent
    rm -f "$fixture/personas/verdicts.yaml"
}

run_consolidate_case consolidate-good
```

- [ ] **Step 4: Run — expect FAIL.**

- [ ] **Step 5: Implement the script.**

```python
#!/usr/bin/env python3
"""Consolidate stage-3a/3b/3c verdicts into personas/verdicts.yaml.

Usage: python3 scripts/pmf-signal-consolidate-verdicts.py <deal-dir>

Reads:
  <deal-dir>/personas/reactions/*.yaml          (3a — per-persona, multi-claim)
  <deal-dir>/personas/verdicts-3b/*.yaml        (3b — per-claim)
  <deal-dir>/personas/verdicts-3c/*.yaml        (3c — per-claim)

Writes:
  <deal-dir>/personas/verdicts.yaml             (flat index keyed by claim_id)

For 3a, aggregates per claim_id across all persona reactions:
  - counts of agree/partial/disagree
  - representative verbatims (one per verdict bucket, prefer first encountered)

Stdlib only; reuses the YAML parser.
"""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter, defaultdict
from pathlib import Path


def _load_parser():
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "_pmf_validate", here / "pmf-signal-validate-pitch.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load YAML parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse_yaml_subset


def _yaml_dump(doc: dict) -> str:
    """Emit a stable subset-YAML serialization. Stdlib-only.

    Supports: nested dicts, lists of dicts, lists of scalars, scalars.
    Strings are emitted with double quotes if they contain spaces or
    special characters; otherwise bare.
    """
    lines: list[str] = []

    def needs_quote(s: str) -> bool:
        if not s:
            return True
        if any(c in s for c in ' :#"\n[]{},'):
            return True
        return False

    def fmt_scalar(v) -> str:
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        s = str(v)
        if needs_quote(s):
            return '"' + s.replace('"', '\\"') + '"'
        return s

    def emit(obj, indent: int) -> None:
        prefix = " " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, dict):
                    lines.append(f"{prefix}{k}:")
                    emit(v, indent + 2)
                elif isinstance(v, list):
                    if not v:
                        lines.append(f"{prefix}{k}: []")
                    else:
                        lines.append(f"{prefix}{k}:")
                        for item in v:
                            if isinstance(item, dict):
                                first = True
                                for ik, iv in item.items():
                                    if first:
                                        if isinstance(iv, (dict, list)):
                                            lines.append(f"{prefix}- {ik}:")
                                            emit(iv, indent + 4)
                                        else:
                                            lines.append(f"{prefix}- {ik}: {fmt_scalar(iv)}")
                                        first = False
                                    else:
                                        if isinstance(iv, (dict, list)):
                                            lines.append(f"{prefix}  {ik}:")
                                            emit(iv, indent + 4)
                                        else:
                                            lines.append(f"{prefix}  {ik}: {fmt_scalar(iv)}")
                            else:
                                lines.append(f"{prefix}- {fmt_scalar(item)}")
                else:
                    lines.append(f"{prefix}{k}: {fmt_scalar(v)}")
        else:
            lines.append(f"{prefix}{fmt_scalar(obj)}")

    emit(doc, 0)
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: pmf-signal-consolidate-verdicts.py <deal-dir>", file=sys.stderr)
        return 64
    deal = Path(argv[1])
    parse = _load_parser()

    claims: dict[str, dict] = {}
    persona_reaction_ids: list[str] = []

    # 3a — aggregate over reactions/*.yaml
    aggregates: dict[str, Counter] = defaultdict(Counter)
    verbatims: dict[str, dict[str, str]] = defaultdict(dict)
    reactions_dir = deal / "personas" / "reactions"
    if reactions_dir.is_dir():
        for path in sorted(reactions_dir.glob("p-*.yaml")):
            doc = parse(path.read_text(encoding="utf-8"))
            for resp in doc.get("claim_responses") or []:
                cid = resp.get("claim_id")
                v = resp.get("verdict")
                if not cid or not v:
                    continue
                aggregates[cid][v] += 1
                if v not in verbatims[cid]:
                    verbatims[cid][v] = resp.get("verbatim") or ""
        for cid, counter in aggregates.items():
            claims[cid] = {
                "claim_id": cid,
                "verification_method": "persona-reaction",
                "verdict_counts": dict(sorted(counter.items())),
                "representative_verbatims": dict(sorted(verbatims[cid].items())),
            }
            persona_reaction_ids.append(cid)

    # 3b
    cross_ids: list[str] = []
    v3b_dir = deal / "personas" / "verdicts-3b"
    if v3b_dir.is_dir():
        for path in sorted(v3b_dir.glob("c-*.yaml")):
            doc = parse(path.read_text(encoding="utf-8"))
            cid = doc.get("claim_id") or path.stem
            claims[cid] = doc
            cross_ids.append(cid)

    # 3c
    external_ids: list[str] = []
    v3c_dir = deal / "personas" / "verdicts-3c"
    if v3c_dir.is_dir():
        for path in sorted(v3c_dir.glob("c-*.yaml")):
            doc = parse(path.read_text(encoding="utf-8"))
            cid = doc.get("claim_id") or path.stem
            claims[cid] = doc
            external_ids.append(cid)

    out_path = deal / "personas" / "verdicts.yaml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        _yaml_dump({"verdicts": [claims[k] for k in sorted(claims.keys())]}),
        encoding="utf-8",
    )

    total = len(claims)
    print(f"consolidated {total} claim(s) → personas/verdicts.yaml")
    print(f"  persona-reaction: {len(persona_reaction_ids)} claim(s) ({', '.join(sorted(persona_reaction_ids))})")
    print(f"  cross-artifact: {len(cross_ids)} claim(s) ({', '.join(sorted(cross_ids))})")
    print(f"  external-evidence: {len(external_ids)} claim(s) ({', '.join(sorted(external_ids))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

```bash
chmod +x scripts/pmf-signal-consolidate-verdicts.py
```

- [ ] **Step 6: Run — expect PASS.** If the YAML emitter produces something the parser can't roundtrip, simplify the dump format. The verdicts file is consumed by `render-report` (Task 16) and by humans; both tolerate a minimal subset.

- [ ] **Step 7: Commit.**

```bash
git add scripts/pmf-signal-consolidate-verdicts.py tests/pmf-signal/fixtures-yaml/consolidate-good/ tests/pmf-signal/expected/consolidate-good.txt tests/pmf-signal/run.sh
git commit -m "Add stage-3 verdict consolidation script"
```

---

## Task 16: Stance-B aggregator (TDD)

**Files:**
- Create: `scripts/pmf-signal-aggregate.py`
- Create: `tests/pmf-signal/fixtures-yaml/aggregate-good/<deal>` (10 personas)
- Create: `tests/pmf-signal/expected/aggregate-good.txt`
- Modify: `tests/pmf-signal/run.sh`

**Note:** This computes the Stance-B aggregates that go into `pmf-signal.md` Stage 4. It reads `personas/reactions/*.yaml` and `personas/rows/*.yaml`. Output: `personas/aggregates.yaml` plus a printed summary.

- [ ] **Step 1: Build a 10-persona fixture.** For each persona, create a row + reaction. Use just enough content to compute aggregates.

Skeleton script for fixture generation (run once, then commit the generated files):

```bash
mkdir -p tests/pmf-signal/fixtures-yaml/aggregate-good/personas/{rows,reactions}

for i in $(seq -f "%03g" 1 10); do
  cat > tests/pmf-signal/fixtures-yaml/aggregate-good/personas/rows/p-$i.yaml <<EOF
persona_id: p-$i
frame_id: x.pmf-validation
scenario:
  trigger_type: regulatory-growth-collision
attributes:
  role: founder-ceo
fabrication_flags: []
EOF
done
```

Manually edit the rows so 4 of them have `trigger_type: switching-cost` and 1 has `fabrication_flags: ["wtp"]`. The other 5 stay as-is.

For reactions, vary the responses so aggregates are non-trivial:

```yaml
# p-001.yaml
persona_id: p-001
would_use: yes
willing_to_pay: yes
wtp_ceiling_zar_per_month: 8000
```

```yaml
# p-002.yaml
persona_id: p-002
would_use: yes
willing_to_pay: yes
wtp_ceiling_zar_per_month: 12000
```

(Continue p-003 through p-010 with varied values. Rough target distribution: would_use yes=4, no=3, yes-with-caveats=3; willing_to_pay yes=3, no=5, maybe=2; numeric WTP only on the 3 yes responses.)

- [ ] **Step 2: Compute the expected aggregates by hand and write the golden file.**

`tests/pmf-signal/expected/aggregate-good.txt`:

```
aggregates written → personas/aggregates.yaml
  N=10, grounded=9, fabricated=1
  would_use: yes=4, no=3, yes-with-caveats=3
  willing_to_pay: yes=3, no=5, maybe=2
  wtp_ceiling_zar_per_month: n=3, median=10000, mean=10000.0
  by trigger_type: regulatory-growth-collision=6, switching-cost=4
EXIT=0
```

(Adjust the numeric WTP values in the fixture so median and mean match a clean number — pick `[8000, 10000, 12000]` for the three yes-respondents to land on median=10000 and mean=10000.0.)

- [ ] **Step 3: Add runner case.**

```bash
run_consolidate_case aggregate-good
```

(Reuses the `run_consolidate_case` helper since the script-name pattern is the same.) Adjust the helper to support a script name override if needed:

```bash
run_dir_case() {
    local name="$1"
    local script="$2"
    local fixture="$script_dir/fixtures-yaml/$name"
    local expected="$script_dir/expected/$name.txt"
    local actual
    actual="$(python3 "$script_dir/../../scripts/pmf-signal-$script.py" "$fixture" 2>&1; echo "EXIT=$?")"
    local expected_contents
    expected_contents="$(cat "$expected")"
    if [[ "$actual" == "$expected_contents" ]]; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        echo "--- expected ---"
        echo "$expected_contents"
        echo "--- actual ---"
        echo "$actual"
        echo "--- end ---"
        fail=1
    fi
    rm -f "$fixture/personas/aggregates.yaml" "$fixture/personas/verdicts.yaml"
}

run_dir_case consolidate-good consolidate-verdicts
run_dir_case aggregate-good aggregate
```

- [ ] **Step 4: Run — expect FAIL.**

- [ ] **Step 5: Implement.**

```python
#!/usr/bin/env python3
"""Stance-B aggregator over personas/reactions/*.yaml + rows/*.yaml.

Usage: python3 scripts/pmf-signal-aggregate.py <deal-dir>

Writes <deal-dir>/personas/aggregates.yaml and prints a summary.

Stdlib only.
"""

from __future__ import annotations

import importlib.util
import statistics
import sys
from collections import Counter
from pathlib import Path


def _load_parser():
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "_pmf_validate", here / "pmf-signal-validate-pitch.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.parse_yaml_subset


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: pmf-signal-aggregate.py <deal-dir>", file=sys.stderr)
        return 64
    deal = Path(argv[1])
    parse = _load_parser()

    rows_dir = deal / "personas" / "rows"
    reactions_dir = deal / "personas" / "reactions"
    rows = {}
    for p in sorted(rows_dir.glob("p-*.yaml")):
        rows[p.stem] = parse(p.read_text(encoding="utf-8"))
    reactions = {}
    for p in sorted(reactions_dir.glob("p-*.yaml")):
        reactions[p.stem] = parse(p.read_text(encoding="utf-8"))

    n = len(rows)
    fabricated = sum(1 for r in rows.values() if (r.get("fabrication_flags") or []))
    grounded = n - fabricated

    use_counts: Counter = Counter()
    pay_counts: Counter = Counter()
    wtp_values: list[int] = []
    trigger_counts: Counter = Counter()

    for pid, row in rows.items():
        scenario = row.get("scenario") or {}
        trigger = scenario.get("trigger_type")
        if trigger:
            trigger_counts[trigger] += 1
        rxn = reactions.get(pid)
        if rxn:
            u = rxn.get("would_use")
            if u:
                use_counts[u] += 1
            p = rxn.get("willing_to_pay")
            if p:
                pay_counts[p] += 1
            w = rxn.get("wtp_ceiling_zar_per_month")
            if isinstance(w, (int, float)):
                wtp_values.append(int(w))

    out: dict = {
        "schema_version": 1,
        "n": n,
        "grounded": grounded,
        "fabricated": fabricated,
        "would_use": dict(use_counts),
        "willing_to_pay": dict(pay_counts),
        "wtp_ceiling_zar_per_month": {
            "n": len(wtp_values),
            "median": int(statistics.median(wtp_values)) if wtp_values else None,
            "mean": float(statistics.fmean(wtp_values)) if wtp_values else None,
        },
        "by_trigger_type": dict(trigger_counts),
    }

    # Reuse the YAML emitter from consolidate
    here = Path(__file__).resolve().parent
    consol_spec = importlib.util.spec_from_file_location(
        "_pmf_consol", here / "pmf-signal-consolidate-verdicts.py"
    )
    consol = importlib.util.module_from_spec(consol_spec)
    assert consol_spec and consol_spec.loader
    consol_spec.loader.exec_module(consol)

    out_path = deal / "personas" / "aggregates.yaml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(consol._yaml_dump(out), encoding="utf-8")

    def fmt_counter(c: Counter) -> str:
        return ", ".join(f"{k}={v}" for k, v in sorted(c.items()))

    print(f"aggregates written → personas/aggregates.yaml")
    print(f"  N={n}, grounded={grounded}, fabricated={fabricated}")
    print(f"  would_use: {fmt_counter(use_counts)}")
    print(f"  willing_to_pay: {fmt_counter(pay_counts)}")
    if wtp_values:
        print(
            f"  wtp_ceiling_zar_per_month: n={len(wtp_values)}, "
            f"median={int(statistics.median(wtp_values))}, "
            f"mean={float(statistics.fmean(wtp_values))}"
        )
    else:
        print("  wtp_ceiling_zar_per_month: n=0")
    print(f"  by trigger_type: {fmt_counter(trigger_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 6: Run — expect PASS.** Iterate on either the fixture or the script until they match the golden exactly.

- [ ] **Step 7: Commit.**

```bash
git add scripts/pmf-signal-aggregate.py tests/pmf-signal/fixtures-yaml/aggregate-good/ tests/pmf-signal/expected/aggregate-good.txt tests/pmf-signal/run.sh
git commit -m "Add Stance-B aggregator script"
```

---

## Task 17: PMF report renderer (TDD-lite)

**Files:**
- Create: `scripts/pmf-signal-render-report.py`
- Create: `tests/pmf-signal/fixtures-yaml/render-report-good/<deal>` (uses verdicts + aggregates from previous fixtures)
- Create: `tests/pmf-signal/expected/render-report-good.md` (golden report)
- Modify: `tests/pmf-signal/run.sh`

**Note:** This script is mostly templating — read aggregates.yaml + verdicts.yaml + pitch.yaml + manifest.json, emit a Markdown file matching the spec's Stage 4 schema. The "test" is golden-file diff against an expected `pmf-signal.md`.

- [ ] **Step 1: Build the fixture deal.** Combine the previous Task 15/16 fixtures plus a minimal pitch.yaml.

```
tests/pmf-signal/fixtures-yaml/render-report-good/
├── manifest.json                 # {"slug":"render-report-good"}
├── pitch.yaml                    # 6 claims spanning all three methods (mirrors spec example)
├── personas/
│   ├── aggregates.yaml           # from Task 16's expected output, hand-written
│   ├── verdicts.yaml             # from Task 15's expected output, hand-written
│   ├── refusals.md               # one refusal block (for the audit section)
│   └── seeds.yaml                # 10 seeds across 6 trigger_types (mode-collapse: pass)
```

For pitch.yaml, use the spec's example (Lines 462-469 of the spec — six claims sorted by severity).

- [ ] **Step 2: Hand-write the expected `pmf-signal.md`.** Match the spec's Stage 4 template structure exactly. About 80 lines.

`tests/pmf-signal/expected/render-report-good.md`:

```markdown
# PMF signal: render-report-good

**Deal:** render-report-good
**Generated:** <ISO_TIMESTAMP>
**Population:** N=10 across 1 frames; 9/1 grounded-vs-fabricated split
**Claims tested:** 6 (persona-reaction: 2, cross-artifact: 3, external-evidence: 1)

> ⚠️ This report is a CALIBRATED PRIOR, not signal. Persona-reaction aggregates are LLM aggregates over a structured synthetic population — hypotheses to falsify in real customer interviews. Cross-artifact verdicts triangulate against prior dudu research. External-evidence verdicts are best-effort web checks bounded at 5 fetches per claim — anything forensic is flagged `requires-data-room`. Read the verdict's verification method before drawing conclusions.

## Headline read

[FILL ME — top 3 sentences capturing the strongest pattern, strongest contradiction, largest cluster verdict.]

## Consolidated claim ledger

The full ledger of every claim made by founder/company, sorted by severity (worst news first).

| Claim | Source | Category | Verdict | Verification method | Strongest evidence |
|---|---|---|---|---|---|
| ... |

## Pitch-reaction aggregates

| Metric | Value | n | σ | Grounded n | Notes |
|---|---|---|---|---|---|
| would_use = yes | 40% | 10 | — | 9 | (n=4 of 10) |
| willing_to_pay = yes | 30% | 10 | — | 9 | (n=3 of 10) |
| WTP ceiling (median, ZAR/mo) | 10000 | 3 | — | 3 | (3 personas anchored a number) |

## Cluster patterns (by trigger_type)

[Per cluster with ≥5 personas — for this fixture, only `regulatory-growth-collision` (n=6) qualifies. ...]

## Strongest contradictions

[FILL ME from the contradicts/disagree rows.]

## Weakest assumptions in the founder's pitch

[FILL ME — pull contradicts/partial verdicts from ledger.]

## Verifications that need a data room

[List any claims with `flag_if_unverifiable: requires-data-room` or `verdict: requires-data-room`.]

## Population audit

- Total personas: 10
- By frame: x.pmf-validation=10
- By trigger type: regulatory-growth-collision=6, switching-cost=4
- Refusals (couldn't ground): 1 — see `personas/refusals.md`
- Fabrication flags: 1
- Mode-collapse check: pass

## Source artifacts

- pitch.yaml (claim ledger)
- personas/_context.md
- personas/frames.yaml
- personas/rows/*.yaml
- personas/reactions/*.yaml
- personas/verdicts.yaml
- personas/refusals.md
- (cross-referenced) founder-*.md, market-sizing.md, competitive-landscape.md, market-problem.md
```

The `<ISO_TIMESTAMP>` placeholder is matched leniently by the test (see Step 4 below).

- [ ] **Step 3: Add a runner case that compares output to golden, with timestamp lenience.**

```bash
run_render_report_case() {
    local name="$1"
    local fixture="$script_dir/fixtures-yaml/$name"
    local expected="$script_dir/expected/$name.md"
    python3 "$script_dir/../../scripts/pmf-signal-render-report.py" "$fixture"
    local actual_path="$fixture/pmf-signal.md"
    if [[ ! -f "$actual_path" ]]; then
        echo "FAIL: $name (no output written)"
        fail=1
        return
    fi
    # normalize ISO timestamps in both files for comparison
    local norm_expected norm_actual
    norm_expected="$(sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z?/<ISO_TIMESTAMP>/g; s/<ISO_TIMESTAMP>/<ISO_TIMESTAMP>/g' "$expected")"
    norm_actual="$(sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z?/<ISO_TIMESTAMP>/g' "$actual_path")"
    if [[ "$norm_expected" == "$norm_actual" ]]; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        diff <(echo "$norm_expected") <(echo "$norm_actual") | head -40
        fail=1
    fi
    rm -f "$actual_path"
}

run_render_report_case render-report-good
```

- [ ] **Step 4: Run — expect FAIL.**

- [ ] **Step 5: Implement the renderer.**

```python
#!/usr/bin/env python3
"""Render pmf-signal.md from a deal directory's pmf-signal artifacts.

Usage: python3 scripts/pmf-signal-render-report.py <deal-dir>

Reads:
  pitch.yaml, personas/aggregates.yaml, personas/verdicts.yaml,
  personas/refusals.md (if present), personas/seeds.yaml,
  personas/rows/*.yaml, manifest.json

Writes: <deal-dir>/pmf-signal.md

Stdlib only.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

SEVERITY_RANK = {
    "contradicts": 0,
    "partial": 1,
    "no-evidence": 1,
    "supports": 3,
}


def _load_parser():
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "_pmf_validate", here / "pmf-signal-validate-pitch.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.parse_yaml_subset


def severity_key(verdict: str) -> int:
    if verdict.startswith("insufficient-evidence-for"):
        return 1
    if verdict in SEVERITY_RANK:
        return SEVERITY_RANK[verdict]
    return 2  # unknown verdicts mid-pack


def _safe(d: dict, *path):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: pmf-signal-render-report.py <deal-dir>", file=sys.stderr)
        return 64
    deal = Path(argv[1])
    parse = _load_parser()
    slug = deal.name

    pitch = parse((deal / "pitch.yaml").read_text(encoding="utf-8")) if (deal / "pitch.yaml").exists() else {}
    aggregates = parse((deal / "personas" / "aggregates.yaml").read_text(encoding="utf-8")) if (deal / "personas" / "aggregates.yaml").exists() else {}
    verdicts_doc = parse((deal / "personas" / "verdicts.yaml").read_text(encoding="utf-8")) if (deal / "personas" / "verdicts.yaml").exists() else {"verdicts": []}

    rows_dir = deal / "personas" / "rows"
    rows = []
    if rows_dir.is_dir():
        for p in sorted(rows_dir.glob("p-*.yaml")):
            rows.append(parse(p.read_text(encoding="utf-8")))

    seeds_doc = parse((deal / "personas" / "seeds.yaml").read_text(encoding="utf-8")) if (deal / "personas" / "seeds.yaml").exists() else {"seeds": []}

    has_refusals = (deal / "personas" / "refusals.md").exists()

    # ─── header counts ───
    n = aggregates.get("n", 0)
    grounded = aggregates.get("grounded", 0)
    fabricated = aggregates.get("fabricated", 0)

    method_counts: Counter = Counter()
    for v in verdicts_doc.get("verdicts") or []:
        m = v.get("verification_method")
        if m:
            method_counts[m] += 1
    total_claims = sum(method_counts.values())

    frame_ids = sorted({r.get("frame_id") for r in rows if r.get("frame_id")})
    frame_count = len(frame_ids)

    # ─── ledger sort ───
    ledger_rows = []
    pitch_claims_by_id = {c.get("claim_id"): c for c in (pitch.get("claims") or [])}
    for v in verdicts_doc.get("verdicts") or []:
        cid = v.get("claim_id")
        verdict = v.get("verdict") or "unknown"
        method = v.get("verification_method") or "?"
        # locate the claim text + source from pitch.yaml
        pc = pitch_claims_by_id.get(cid, {})
        claim_text = pc.get("claim", "?")
        category = pc.get("category", "?")
        source = pc.get("source", "?")
        # evidence string
        evidence = ""
        if method == "persona-reaction":
            counts = v.get("verdict_counts") or {}
            verbatims = v.get("representative_verbatims") or {}
            top_verdict = max(counts.items(), key=lambda kv: kv[1])[0] if counts else None
            n_top = counts.get(top_verdict, 0) if top_verdict else 0
            verbatim = verbatims.get(top_verdict, "")
            verdict = top_verdict or verdict
            evidence = f'"{verbatim}" ({n_top}/{n} personas)' if verbatim else f"{n_top}/{n} personas"
        elif method == "cross-artifact":
            sup = v.get("supporting_quotes") or []
            con = v.get("contradicting_quotes") or []
            picked = (con or sup)[:1]
            if picked:
                q = picked[0]
                evidence = f'"{q.get("quote", "")}" ({q.get("location", "")})'
            else:
                evidence = v.get("verdict_rationale", "")
        elif method == "external-evidence":
            evidence = v.get("verdict_rationale", "")
        ledger_rows.append({
            "claim": claim_text,
            "source": source,
            "category": category,
            "verdict": verdict,
            "method": method,
            "evidence": evidence,
        })
    ledger_rows.sort(key=lambda r: severity_key(r["verdict"]))

    # ─── pitch-reaction aggregates (worst-news-first too) ───
    use = aggregates.get("would_use") or {}
    pay = aggregates.get("willing_to_pay") or {}
    wtp = aggregates.get("wtp_ceiling_zar_per_month") or {}

    def pct(c: dict, key: str, total: int) -> str:
        if total == 0:
            return "—"
        return f"{(c.get(key, 0) / total * 100):.0f}%"

    # ─── trigger summary ───
    trigger_counts = aggregates.get("by_trigger_type") or {}

    # ─── data-room flags ───
    needs_data_room: list[str] = []
    for v in verdicts_doc.get("verdicts") or []:
        if v.get("verdict") == "requires-data-room" or "requires-data-room" in (v.get("flags") or []):
            needs_data_room.append(v.get("claim_id"))

    # ─── frame breakdown (rows) ───
    frame_breakdown = Counter(r.get("frame_id") for r in rows if r.get("frame_id"))

    # ─── seeds mode-collapse status ───
    seed_trigger_counts = Counter((s.get("trigger_type") for s in (seeds_doc.get("seeds") or [])))
    if seed_trigger_counts:
        top = seed_trigger_counts.most_common(1)[0][1]
        share = top / sum(seed_trigger_counts.values())
        mode_collapse_status = "fail" if share > 0.60 else "pass"
    else:
        mode_collapse_status = "n/a"

    # ─── compose Markdown ───
    out: list[str] = []
    out.append(f"# PMF signal: {slug}")
    out.append("")
    out.append(f"**Deal:** {slug}")
    out.append(f"**Generated:** {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    out.append(f"**Population:** N={n} across {frame_count} frames; {grounded}/{fabricated} grounded-vs-fabricated split")
    out.append(
        f"**Claims tested:** {total_claims} "
        f"(persona-reaction: {method_counts.get('persona-reaction', 0)}, "
        f"cross-artifact: {method_counts.get('cross-artifact', 0)}, "
        f"external-evidence: {method_counts.get('external-evidence', 0)})"
    )
    out.append("")
    out.append("> ⚠️ This report is a CALIBRATED PRIOR, not signal. Persona-reaction aggregates are LLM aggregates over a structured synthetic population — hypotheses to falsify in real customer interviews. Cross-artifact verdicts triangulate against prior dudu research. External-evidence verdicts are best-effort web checks bounded at 5 fetches per claim — anything forensic is flagged `requires-data-room`. Read the verdict's verification method before drawing conclusions.")
    out.append("")

    out.append("## Headline read")
    out.append("")
    out.append("[FILL ME — top 3 sentences capturing the strongest pattern, strongest contradiction, largest cluster verdict.]")
    out.append("")

    out.append("## Consolidated claim ledger")
    out.append("")
    out.append("The full ledger of every claim made by founder/company, sorted by severity (worst news first).")
    out.append("")
    out.append("| Claim | Source | Category | Verdict | Verification method | Strongest evidence |")
    out.append("|---|---|---|---|---|---|")
    for r in ledger_rows:
        out.append(
            f"| {r['claim']} | {r['source']} | {r['category']} | **{r['verdict']}** | {r['method']} | {r['evidence']} |"
        )
    out.append("")

    out.append("## Pitch-reaction aggregates")
    out.append("")
    out.append("| Metric | Value | n | σ | Grounded n | Notes |")
    out.append("|---|---|---|---|---|---|")
    out.append(
        f"| would_use = yes | {pct(use, 'yes', n)} | {n} | — | {grounded} | (n={use.get('yes', 0)} of {n}) |"
    )
    out.append(
        f"| willing_to_pay = yes | {pct(pay, 'yes', n)} | {n} | — | {grounded} | (n={pay.get('yes', 0)} of {n}) |"
    )
    if wtp.get("n", 0) > 0:
        out.append(
            f"| WTP ceiling (median, ZAR/mo) | {wtp.get('median')} | {wtp.get('n')} | — | {wtp.get('n')} | ({wtp.get('n')} personas anchored a number) |"
        )
    out.append("")

    out.append("## Cluster patterns (by trigger_type)")
    out.append("")
    qualifying = [(t, c) for t, c in sorted(trigger_counts.items(), key=lambda kv: -kv[1]) if c >= 5]
    if not qualifying:
        out.append("[No cluster reached the 5-persona threshold for stratified analysis.]")
    else:
        for t, c in qualifying:
            out.append(f"### Cluster: {t} (n={c})")
            out.append("")
            out.append("[FILL ME — mean pain, dominant phrase, would-pay rate, top objection, top resonance quote with persona_id citation.]")
            out.append("")

    out.append("## Strongest contradictions")
    out.append("")
    out.append("[FILL ME from the contradicts/disagree rows.]")
    out.append("")

    out.append("## Weakest assumptions in the founder's pitch")
    out.append("")
    out.append("[FILL ME — pull contradicts/partial verdicts from ledger above.]")
    out.append("")

    out.append("## Verifications that need a data room")
    out.append("")
    if needs_data_room:
        for cid in needs_data_room:
            out.append(f"- {cid}")
    else:
        out.append("[None flagged.]")
    out.append("")

    out.append("## Population audit")
    out.append("")
    out.append(f"- Total personas: {n}")
    out.append("- By frame: " + ", ".join(f"{k}={v}" for k, v in sorted(frame_breakdown.items())))
    out.append("- By trigger type: " + ", ".join(f"{k}={v}" for k, v in sorted(trigger_counts.items())))
    if has_refusals:
        out.append("- Refusals (couldn't ground): see `personas/refusals.md`")
    else:
        out.append("- Refusals (couldn't ground): 0")
    out.append(f"- Fabrication flags: {fabricated}")
    out.append(f"- Mode-collapse check: {mode_collapse_status}")
    out.append("")

    out.append("## Source artifacts")
    out.append("")
    out.append("- pitch.yaml (claim ledger)")
    out.append("- personas/_context.md")
    out.append("- personas/frames.yaml")
    out.append("- personas/rows/*.yaml")
    out.append("- personas/reactions/*.yaml")
    out.append("- personas/verdicts.yaml")
    if has_refusals:
        out.append("- personas/refusals.md")
    out.append("- (cross-referenced) founder-*.md, market-sizing.md, competitive-landscape.md, market-problem.md")
    out.append("")

    (deal / "pmf-signal.md").write_text("\n".join(out), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

```bash
chmod +x scripts/pmf-signal-render-report.py
```

- [ ] **Step 6: Run.** Iterate the golden file (Step 2) against the actual output until they match — easier than tuning the script. The renderer is mostly faithful to the spec; minor wording differences in the golden are fine to revise.

- [ ] **Step 7: Update SKILL.md Stage 4 section.** Append:

````markdown
## Stage 4 — PMF signal report

After stage 3 finishes, run aggregation and rendering:

```bash
python3 scripts/pmf-signal-aggregate.py deals/<slug>
python3 scripts/pmf-signal-render-report.py deals/<slug>
```

The renderer emits `deals/<slug>/pmf-signal.md`. The output contains FILL-ME placeholders in three narrative sections (`Headline read`, `Strongest contradictions`, `Weakest assumptions`). After the renderer runs, complete those sections by reading the consolidated claim ledger and cluster patterns and writing 1–3 paragraphs each. The mechanical structure is fixed by the renderer; the narrative is yours.
````

- [ ] **Step 8: Commit.**

```bash
git add scripts/pmf-signal-render-report.py tests/pmf-signal/fixtures-yaml/render-report-good/ tests/pmf-signal/expected/render-report-good.md tests/pmf-signal/run.sh skills/pmf-signal/SKILL.md
git commit -m "Add PMF report renderer with golden test"
```

---

## Task 18: Stage 5 — Network scan playbook (SKILL.md prose)

**Files:**
- Modify: `skills/pmf-signal/SKILL.md`

- [ ] **Step 1: Append the Stage 5 section.**

````markdown
## Stage 5 — Network scan & warm-path outreach

Goal: produce `deals/<slug>/outreach.md` (cluster-stratified, warm-path-prioritized) AND a legacy-shape `deals/<slug>/customer-discovery-prep.md` (so downstream `customer-discovery debrief` keeps working).

If `--no-network` was passed, skip this stage entirely.

### 5a. Match — find real humans per cluster

A cluster is any (`trigger_type`, `frame_id`) pair with ≥5 personas in `personas/rows/*.yaml`. List clusters before fetching anything; cap the candidate output at 30 across the deal (matching the legacy `customer-discovery-prep` ceiling).

For each cluster, generate targeted searches from the union of `discoverability_signals.{job_titles, communities, post_patterns, query_strings}` across that cluster's personas.

Channels and per-cluster fetch budgets:

- **LinkedIn (authed Playwright, main session only)** — ~5 fetches per cluster, filtered by job title and geography. Skip under `--public-only`.
- **Reddit** — ~5 candidates per cluster from `post_patterns` queries.
- **Niche communities** — Slack/Discord with public membership lists, 1–2 per cluster, ~5 candidates.
- **X** — search `voice.pain_phrases` + geography filter, ~5 candidates.

Total fetch budget: 20 × cluster_count, hard-capped at 80. If clusters × budget exceeds 80, halve per-cluster budgets.

Each candidate row anchors to a `match_evidence` quote: a public post or profile snippet that ties this candidate to the cluster's signature. **Drop candidates without match evidence.**

#### Parallelization

Dispatch one worker subagent per (cluster × non-LinkedIn channel) combination. LinkedIn runs in main session only (Playwright cannot delegate). See `lib/playwright-auth.md` for the authed-session protocol.

### 5b. Network understanding

For each surviving candidate, enrich with:

1. **Warm-path inference (authed LinkedIn).** Check VC's 1st and 2nd-degree network. Stop at 2nd. Name the bridge if one exists. Skipped under `--public-only`.
2. **Broker identification.** For each candidate's primary community, surface the named moderator/manager/chair. One per community is sufficient.
3. **Channel-fit prior.** Per channel, label `expected_response: low | medium | high` and `risk: low | medium-spam | high-ban`, **conditioned on the specific community** (not the channel-in-the-abstract).
4. **Post hooks.** A recent (≤30 days) post by the candidate that anchors the outreach. "Saw your post about X" outperforms generic DMs.

### Stage 5 row schema

```yaml
candidate_id: c-014
cluster_id: <trigger_type>__<frame_id>
match_evidence:
  url: "<URL>"
  quote: "<verbatim quote>"
  date: <ISO date>
person:
  name: "<name>"
  handle_or_link: "<URL>"
  role_inferred: "<string>"
  geography_inferred: "<string>"
warm_path:
  exists: <true | false>
  degree: <1 | 2 | null>
  bridge_name: "<name (degree-1 connection)>"
  confidence: <high | medium | low>
brokers:
  - {community: "<name>", role: "<role>", contact: "<URL>"}
channel_fit_ranked:
  - {channel: warm-intro-via-<bridge>, expected_response: high, risk: low}
  - {channel: linkedin-dm, expected_response: medium, risk: low}
  - {channel: reddit-dm-public-thread-reply-first, expected_response: medium, risk: medium-spam}
  - {channel: cold-email, expected_response: low, risk: low, note: "<...>"}
post_hooks:
  - {url: "<URL>", date: <ISO>, summary: "<short>"}
recommended_outreach:
  channel: <chosen channel slug>
  draft: "<80-word draft referencing bridge + post hook + research framing>"
```

Save to `deals/<slug>/personas/candidates/<candidate_id>.yaml`.

### 5c. Render outreach artifacts

Run:

```bash
python3 scripts/pmf-signal-render-outreach.py deals/<slug>
```

This emits `outreach.md` (cluster-stratified, prioritized by warm-path quality) and a legacy-shape `customer-discovery-prep.md` (target list + channel templates + interview script auto-generated from cluster patterns + strongest contradictions in `pmf-signal.md`). See Task 19 for the renderer.
````

- [ ] **Step 2: Commit.**

```bash
git add skills/pmf-signal/SKILL.md
git commit -m "Add Stage 5 network-scan playbook"
```

---

## Task 19: Outreach renderer (TDD)

**Files:**
- Create: `scripts/pmf-signal-render-outreach.py`
- Create: `tests/pmf-signal/fixtures-yaml/render-outreach-good/<deal>` (3 candidates across 2 clusters)
- Create: `tests/pmf-signal/expected/render-outreach-good.outreach.md`
- Create: `tests/pmf-signal/expected/render-outreach-good.cdp.md`
- Modify: `tests/pmf-signal/run.sh`

- [ ] **Step 1: Build a 3-candidate fixture.**

```
fixtures-yaml/render-outreach-good/
├── manifest.json                # {"slug":"render-outreach-good"}
├── pmf-signal.md                # minimal — used only to extract cluster patterns + contradictions
└── personas/
    └── candidates/
        ├── c-001.yaml           # cluster: regulatory-growth-collision__pmf-validation, warm 1st-degree
        ├── c-002.yaml           # cluster: regulatory-growth-collision__pmf-validation, broker-mediated
        └── c-003.yaml           # cluster: switching-cost__pmf-validation, no warm path, public DM only
```

Hand-write each candidate YAML using the schema from Task 18.

`pmf-signal.md` minimal stub:

```markdown
# PMF signal: render-outreach-good

## Cluster patterns (by trigger_type)

### Cluster: regulatory-growth-collision (n=6)

[Pattern note for outreach-script generation.]

### Cluster: switching-cost (n=5)

[Pattern note.]

## Strongest contradictions

- "founder claims accountant-referrals; persona disagrees" (p-007)
```

- [ ] **Step 2: Hand-write expected outputs.**

`tests/pmf-signal/expected/render-outreach-good.outreach.md`:

```markdown
# Outreach: render-outreach-good

**Deal:** render-outreach-good
**Generated:** <ISO_TIMESTAMP>
**Candidates:** 3 across 2 cluster(s)

> Stratified by cluster. Within each cluster, candidates are sorted by warm-path quality (warm 1st → 2nd → broker → public-only DM → cold).

## Cluster: regulatory-growth-collision__pmf-validation (n=2)

| # | Name | Channel (recommended) | Warm path | Match evidence | Post hook |
|---|------|------|------|------|------|
| 1 | <name from c-001> | warm-intro-via-<bridge> | 1st-degree via <bridge> | "<quote>" | <post date> — <summary> |
| 2 | <name from c-002> | broker-via-<community> | broker | "<quote>" | <post date> — <summary> |

### Recommended drafts

#### Candidate 1 (warm-intro-via-<bridge>)

> [80-word draft from c-001.yaml]

#### Candidate 2 (broker-via-<community>)

> [80-word draft from c-002.yaml]

## Cluster: switching-cost__pmf-validation (n=1)

| # | Name | Channel (recommended) | Warm path | Match evidence | Post hook |
|---|------|------|------|------|------|
| 3 | <name from c-003> | reddit-dm-public-thread-reply-first | none | "<quote>" | <post date> — <summary> |

### Recommended drafts

#### Candidate 3 (reddit-dm-public-thread-reply-first)

> [80-word draft from c-003.yaml]

## Source artifacts

- personas/candidates/*.yaml
- pmf-signal.md (cluster patterns)
```

`tests/pmf-signal/expected/render-outreach-good.cdp.md` (legacy shape — must match the existing `customer-discovery-prep.md` template enough to keep `customer-discovery debrief` happy):

```markdown
# Customer discovery prep: render-outreach-good

**Deal:** render-outreach-good
**Generated:** <ISO_TIMESTAMP>

> Goal of these interviews: validate (or break) the patterns surfaced in [pmf-signal.md](pmf-signal.md). Aim for 5–10 interviews across the clusters identified.

## Target list

| # | Name | Channel | Link | Why they fit | How to reach |
|---|------|---------|------|--------------|--------------|
| 1 | <c-001 name> | <c-001 channel> | <c-001 link> | regulatory-growth-collision__pmf-validation | <recommended channel> |
| 2 | <c-002 name> | <c-002 channel> | <c-002 link> | regulatory-growth-collision__pmf-validation | <recommended channel> |
| 3 | <c-003 name> | <c-003 channel> | <c-003 link> | switching-cost__pmf-validation | <recommended channel> |

## Outreach templates

### LinkedIn DM (template)

> [auto-generated 80-word template referencing the strongest pattern]

### Reddit DM (template)

> [auto-generated 80-word template]

### X DM (template)

> [auto-generated 80-word template]

### Cold email (template)

> [auto-generated 80-word template]

## Interview script

1. **Tell me about this problem in your day-to-day.**
   - Follow-up: <one follow-up rooted in the strongest cluster pattern>

2. **How are you solving it today?**
   - Follow-up: <one follow-up rooted in a strongest contradiction>

3. **What would it be worth to you to solve this properly?**
   - Follow-up: <follow-up rooted in WTP aggregates>

4. **Have you looked for solutions? Why didn't they work?**
   - Follow-up: <follow-up rooted in a contradiction>

## Sources

- personas/candidates/*.yaml
- pmf-signal.md
```

- [ ] **Step 3: Add a runner case for two outputs.**

```bash
run_outreach_case() {
    local name="$1"
    local fixture="$script_dir/fixtures-yaml/$name"
    local expected_outreach="$script_dir/expected/$name.outreach.md"
    local expected_cdp="$script_dir/expected/$name.cdp.md"
    python3 "$script_dir/../../scripts/pmf-signal-render-outreach.py" "$fixture"
    local fail_local=0
    for pair in "outreach.md:$expected_outreach" "customer-discovery-prep.md:$expected_cdp"; do
        local actual_name="${pair%%:*}"
        local expected_path="${pair#*:}"
        local actual_path="$fixture/$actual_name"
        if [[ ! -f "$actual_path" ]]; then
            echo "FAIL: $name ($actual_name not written)"
            fail_local=1
            continue
        fi
        local norm_expected norm_actual
        norm_expected="$(sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z?/<ISO_TIMESTAMP>/g' "$expected_path")"
        norm_actual="$(sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z?/<ISO_TIMESTAMP>/g' "$actual_path")"
        if [[ "$norm_expected" != "$norm_actual" ]]; then
            echo "FAIL: $name ($actual_name diff)"
            diff <(echo "$norm_expected") <(echo "$norm_actual") | head -40
            fail_local=1
        fi
        rm -f "$actual_path"
    done
    if [[ $fail_local -eq 0 ]]; then
        echo "PASS: $name"
    else
        fail=1
    fi
}

run_outreach_case render-outreach-good
```

- [ ] **Step 4: Run — expect FAIL.**

- [ ] **Step 5: Implement the renderer.** It reads candidate YAMLs, sorts by cluster + warm-path priority, and writes both files. Templating is straightforward Markdown assembly.

```python
#!/usr/bin/env python3
"""Render outreach.md and the legacy customer-discovery-prep.md.

Usage: python3 scripts/pmf-signal-render-outreach.py <deal-dir>

Reads:
  <deal-dir>/personas/candidates/*.yaml
  <deal-dir>/pmf-signal.md (for cluster patterns + contradictions extraction)

Writes:
  <deal-dir>/outreach.md
  <deal-dir>/customer-discovery-prep.md

Stdlib only.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path

WARM_PATH_RANK = {
    1: 0,    # warm 1st-degree
    2: 1,    # warm 2nd-degree
}


def _load_parser():
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "_pmf_validate", here / "pmf-signal-validate-pitch.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.parse_yaml_subset


def candidate_priority(c: dict) -> tuple:
    wp = c.get("warm_path") or {}
    if wp.get("exists"):
        return (WARM_PATH_RANK.get(wp.get("degree"), 99),)
    if c.get("brokers"):
        return (3,)
    return (4,)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: pmf-signal-render-outreach.py <deal-dir>", file=sys.stderr)
        return 64
    deal = Path(argv[1])
    parse = _load_parser()
    slug = deal.name

    cands_dir = deal / "personas" / "candidates"
    candidates: list[dict] = []
    if cands_dir.is_dir():
        for p in sorted(cands_dir.glob("c-*.yaml")):
            candidates.append(parse(p.read_text(encoding="utf-8")))

    # Group by cluster
    by_cluster: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        by_cluster[c.get("cluster_id") or "unclustered"].append(c)
    for cluster in by_cluster:
        by_cluster[cluster].sort(key=candidate_priority)

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ─── outreach.md ───
    out: list[str] = []
    out.append(f"# Outreach: {slug}")
    out.append("")
    out.append(f"**Deal:** {slug}")
    out.append(f"**Generated:** {ts}")
    out.append(f"**Candidates:** {len(candidates)} across {len(by_cluster)} cluster(s)")
    out.append("")
    out.append("> Stratified by cluster. Within each cluster, candidates are sorted by warm-path quality (warm 1st → 2nd → broker → public-only DM → cold).")
    out.append("")
    seq = 0
    for cluster, members in sorted(by_cluster.items()):
        out.append(f"## Cluster: {cluster} (n={len(members)})")
        out.append("")
        out.append("| # | Name | Channel (recommended) | Warm path | Match evidence | Post hook |")
        out.append("|---|------|------|------|------|------|")
        for c in members:
            seq += 1
            person = c.get("person") or {}
            wp = c.get("warm_path") or {}
            ev = c.get("match_evidence") or {}
            hooks = c.get("post_hooks") or []
            hook = hooks[0] if hooks else {}
            rec = c.get("recommended_outreach") or {}
            warm_desc = "none"
            if wp.get("exists"):
                warm_desc = f"{wp.get('degree')}{ 'st' if wp.get('degree') == 1 else 'nd' }-degree via {wp.get('bridge_name', '')}"
            elif c.get("brokers"):
                warm_desc = "broker"
            out.append(
                f"| {seq} | {person.get('name', '')} | {rec.get('channel', '')} | {warm_desc} | "
                f'"{ev.get("quote", "")}" | {hook.get("date", "")} — {hook.get("summary", "")} |'
            )
        out.append("")
        out.append("### Recommended drafts")
        out.append("")
        local_seq = seq - len(members)
        for c in members:
            local_seq += 1
            rec = c.get("recommended_outreach") or {}
            out.append(f"#### Candidate {local_seq} ({rec.get('channel', '')})")
            out.append("")
            out.append(f"> {rec.get('draft', '')}")
            out.append("")
    out.append("## Source artifacts")
    out.append("")
    out.append("- personas/candidates/*.yaml")
    out.append("- pmf-signal.md (cluster patterns)")
    out.append("")
    (deal / "outreach.md").write_text("\n".join(out), encoding="utf-8")

    # ─── customer-discovery-prep.md (legacy shape) ───
    cdp: list[str] = []
    cdp.append(f"# Customer discovery prep: {slug}")
    cdp.append("")
    cdp.append(f"**Deal:** {slug}")
    cdp.append(f"**Generated:** {ts}")
    cdp.append("")
    cdp.append("> Goal of these interviews: validate (or break) the patterns surfaced in [pmf-signal.md](pmf-signal.md). Aim for 5–10 interviews across the clusters identified.")
    cdp.append("")
    cdp.append("## Target list")
    cdp.append("")
    cdp.append("| # | Name | Channel | Link | Why they fit | How to reach |")
    cdp.append("|---|------|---------|------|--------------|--------------|")
    seq = 0
    for cluster, members in sorted(by_cluster.items()):
        for c in members:
            seq += 1
            person = c.get("person") or {}
            rec = c.get("recommended_outreach") or {}
            cdp.append(
                f"| {seq} | {person.get('name', '')} | {rec.get('channel', '')} | "
                f"{person.get('handle_or_link', '')} | {cluster} | {rec.get('channel', '')} |"
            )
    cdp.append("")
    cdp.append("## Outreach templates")
    cdp.append("")
    for ch in ("LinkedIn DM", "Reddit DM", "X DM", "Cold email"):
        cdp.append(f"### {ch} (template)")
        cdp.append("")
        cdp.append("> [auto-generated 80-word template referencing the strongest pattern]")
        cdp.append("")
    cdp.append("## Interview script")
    cdp.append("")
    cdp.append("1. **Tell me about this problem in your day-to-day.**")
    cdp.append("   - Follow-up: <one follow-up rooted in the strongest cluster pattern>")
    cdp.append("")
    cdp.append("2. **How are you solving it today?**")
    cdp.append("   - Follow-up: <one follow-up rooted in a strongest contradiction>")
    cdp.append("")
    cdp.append("3. **What would it be worth to you to solve this properly?**")
    cdp.append("   - Follow-up: <follow-up rooted in WTP aggregates>")
    cdp.append("")
    cdp.append("4. **Have you looked for solutions? Why didn't they work?**")
    cdp.append("   - Follow-up: <follow-up rooted in a contradiction>")
    cdp.append("")
    cdp.append("## Sources")
    cdp.append("")
    cdp.append("- personas/candidates/*.yaml")
    cdp.append("- pmf-signal.md")
    cdp.append("")
    (deal / "customer-discovery-prep.md").write_text("\n".join(cdp), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

```bash
chmod +x scripts/pmf-signal-render-outreach.py
```

- [ ] **Step 6: Run — iterate the golden files until they match the actual output.** As with Task 17, easier to tune the goldens than the script.

- [ ] **Step 7: Commit.**

```bash
git add scripts/pmf-signal-render-outreach.py tests/pmf-signal/fixtures-yaml/render-outreach-good/ tests/pmf-signal/expected/render-outreach-good.* tests/pmf-signal/run.sh
git commit -m "Add outreach + legacy customer-discovery-prep renderer"
```

---

## Task 20: Wire the diligence orchestrator

**Files:**
- Modify: `skills/diligence/SKILL.md`
- Modify: `skills/customer-discovery/SKILL.md`

- [ ] **Step 1: Read the current `skills/diligence/SKILL.md` step 2 sub-skill list.**

```bash
sed -n '15,35p' skills/diligence/SKILL.md
```

- [ ] **Step 2: Replace step 2 sub-skill ordering.** The current list is:

```
1. dudu:founder-check
2. dudu:market-problem
3. dudu:customer-discovery prep
4. dudu:competitive-landscape
5. dudu:market-sizing
```

Change to:

```
1. dudu:founder-check — for each founder
2. dudu:market-problem — full Phases 1+2+3
3. dudu:competitive-landscape
4. dudu:market-sizing
5. dudu:pmf-signal — emits both pmf-signal.md, outreach.md, and the legacy-shape customer-discovery-prep.md as a side effect of stage 5
```

Use the Edit tool to make this exact substitution in `skills/diligence/SKILL.md`.

- [ ] **Step 3: Update step 3 (the pause-for-interviews print).** Change the message to reference `pmf-signal.md` and `outreach.md` instead of just `customer-discovery-prep.md`:

```
> Prep complete. The next step is yours: read deals/<slug>/pmf-signal.md for the calibrated PMF signal and consolidated claim ledger, then reach out to the candidates in deals/<slug>/outreach.md (sorted by warm-path quality) and run 5–10 real interviews. Save transcripts under deals/<slug>/inputs/. When done, re-run dudu:diligence and I'll continue with the debrief and final memo.
```

- [ ] **Step 4: Update step 5 (MEMO.md template).** Insert a new section between **Problem and product** and **Customer signal**:

```markdown
## PMF signal & claim verification (calibrated prior + cross-artifact + external)

[Headline read from `pmf-signal.md`. The top 5 rows of the consolidated claim ledger (worst-news-first ordering). The 1 strongest cluster pattern. Explicit Stance B disclaimer for the persona-reaction rows; cross-artifact and external-evidence rows do not need the same disclaimer because they triangulate against actual evidence. List of `requires-data-room` flags for the VC to follow up on.]
```

- [ ] **Step 5: Update step 6 manifest verification.** Change "All six sub-skill keys" to "All seven sub-skill keys" and add `pmf-signal` to the list:

```
6. Verify manifest completeness. All seven sub-skill keys in `skills_completed` should now be non-null (`founder-check`, `market-problem`, `customer-discovery-prep`, `customer-discovery-debrief`, `competitive-landscape`, `market-sizing`, `pmf-signal`).
```

- [ ] **Step 6: Update `skills/customer-discovery/SKILL.md`.** Add a note near the top:

```markdown
> **Note:** As of pmf-signal v1, the `prep` sub-action is no longer invoked by `dudu:diligence` — `dudu:pmf-signal` stage 5 emits `customer-discovery-prep.md` directly. The `prep` sub-action remains available for standalone use (when running this skill outside the diligence orchestrator chain).
```

- [ ] **Step 7: Commit.**

```bash
git add skills/diligence/SKILL.md skills/customer-discovery/SKILL.md
git commit -m "Wire pmf-signal into diligence orchestrator chain"
```

---

## Task 21: Skill lint pass

**Files:**
- Run: `scripts/lint-skills.sh` (existing tool)

- [ ] **Step 1: Run the existing skill linter.**

```bash
scripts/lint-skills.sh
```

- [ ] **Step 2: Fix any violations.** The linter checks: skill names match folder names, no duplicate names, lib references resolve. If `skills/pmf-signal/SKILL.md` violates anything, fix the SKILL.md inline. Most likely issue: front-matter mismatch.

- [ ] **Step 3: If anything was fixed, commit.**

```bash
git add skills/pmf-signal/SKILL.md
git commit -m "Fix pmf-signal SKILL.md lint violations"
```

---

## Task 22: Run the full test suite

**Files:**
- Run: `tests/pmf-signal/run.sh`
- Run: `tests/lint/run.sh`

- [ ] **Step 1: Run the new test suite.**

```bash
bash tests/pmf-signal/run.sh
```

Expected: every case PASS. If any FAIL, investigate the diff and fix the script (preferred) or update the golden file (acceptable for narrative templates where wording can vary).

- [ ] **Step 2: Run the existing lint suite (regression check).**

```bash
bash tests/lint/run.sh
```

Expected: every case PASS, unchanged from before.

- [ ] **Step 3: If any test failed, fix and re-commit.**

---

## Task 23: Smoke-test against ledgerloop

**Files:**
- Read: `test/ledgerloop/...`

This task validates that the skill produces sensible output on a real deal with real prior dudu artifacts. It is **not** automated — execute the skill manually and inspect the output.

- [ ] **Step 1: Verify ledgerloop has all upstream artifacts.**

```bash
python3 scripts/pmf-signal-preflight.py test/ledgerloop
```

Expected: exit 0, loading ledger printed. If it exits 2 (missing artifacts) or 3 (already done), handle accordingly. Note: `test/ledgerloop` already has a `customer-discovery-prep.md` and `personas/` directory from prior runs — the pre-flight does NOT check for absence of `pmf-signal.md` outputs in the test fixture, so this should pass cleanly unless `pmf-signal.md` already exists.

- [ ] **Step 2: Drive the skill manually.** Open a fresh Claude Code session in this repo and invoke `dudu:pmf-signal` against `test/ledgerloop`. Walk the skill stages in order, dispatching subagents per the SKILL.md instructions. This will take real LLM time — 30–90 minutes depending on N and parallelism.

- [ ] **Step 3: Inspect outputs.** After the run, verify these files exist and look sensible:

```bash
ls -la test/ledgerloop/pmf-signal.md test/ledgerloop/outreach.md test/ledgerloop/customer-discovery-prep.md test/ledgerloop/pitch.yaml test/ledgerloop/personas/aggregates.yaml test/ledgerloop/personas/verdicts.yaml
```

For each, open and check:

- `pitch.yaml` — claim ledger has at least 6 claims; each has all required fields; verification methods are sensibly assigned.
- `pmf-signal.md` — consolidated claim ledger sorted by severity; aggregates have non-zero n; cluster patterns reflect at least one ≥5-persona cluster; FILL-ME placeholders have been replaced with real prose.
- `outreach.md` — at least 10 candidates across ≥1 cluster; warm-path inference shows at least one named bridge OR records "no warm path found" honestly; channel-fit ranks are present.
- `customer-discovery-prep.md` — has the same shape as the prior `test/ledgerloop/customer-discovery-prep.md` (so downstream `customer-discovery debrief` won't break).

- [ ] **Step 4: Diff against the prior `customer-discovery-prep.md`.** This is the back-compat check.

```bash
diff <(git show HEAD~50:test/ledgerloop/customer-discovery-prep.md 2>/dev/null || cat test/ledgerloop/customer-discovery-prep.md) test/ledgerloop/customer-discovery-prep.md | head -40
```

The shapes should match (table, templates, script). The candidate names will differ (different generation run) but the structure must be the same. If structure drifts, fix the renderer.

- [ ] **Step 5: Save a known-good copy as a regression target.**

```bash
cp test/ledgerloop/pmf-signal.md test/ledgerloop/pmf-signal.expected-shape.md
git add test/ledgerloop/pmf-signal.expected-shape.md
git commit -m "Add ledgerloop pmf-signal smoke-test reference output"
```

The `.expected-shape.md` is a snapshot of one good run, kept in the repo for visual comparison on future runs.

---

## Self-Review

**1. Spec coverage:**

- Goals 1, 2, 3 (claim validation / PMF signal / warm-path outreach) — Tasks 5, 10, 11, 14, 17, 18, 19.
- Prerequisites hard gate — Task 3, 4.
- Stage 0 claim ledger with verification methods — Task 5, 6.
- Stage 1 frames — Task 7.
- Stage 2 5W population — Task 8.
- Stage 2 mode-collapse pre-check — Task 9.
- Stage 3a persona pitch-reaction — Task 10.
- Stage 3b cross-artifact verification — Task 11.
- Stage 3c external-evidence + recipes — Tasks 12, 13, 14.
- Stage 4 PMF report (Stance B aggregates + consolidated ledger) — Tasks 15, 16, 17.
- Stage 5 network scan + warm-path — Tasks 18, 19.
- Diligence orchestrator + customer-discovery prep handling — Task 20.
- Manifest schema — Task 2.
- Lint conformance — Task 21.
- Smoke test on ledgerloop — Task 23.

Coverage: complete.

**2. Placeholder scan:**

The plan contains FILL-ME markers in two places — both intentional and called out explicitly (Task 17 Step 7 explains they are part of the rendered output, to be filled by Claude during the live run, not part of the plan that the engineer must complete during implementation). No plan-level placeholders.

**3. Type/name consistency:**

- Helper script naming: `scripts/pmf-signal-<name>.py` — used consistently across Tasks 3, 6, 9, 12, 13, 15, 16, 17, 19.
- Recipe module naming: `pmf-signal-recipes/<name>.py` (snake_case) — Tasks 12, 13, 14. The dispatcher in Task 14 calls them via `__import__('pmf-signal-recipes.<name>', fromlist=['run'])` — consistent with the test runner in Task 12.
- File path conventions: `personas/rows/`, `personas/reactions/`, `personas/verdicts-3b/`, `personas/verdicts-3c/`, `personas/verdicts.yaml`, `personas/aggregates.yaml`, `personas/seeds.yaml`, `personas/refusals.md`, `personas/candidates/` — used consistently across Tasks 8–19.
- Verification method names: `persona-reaction | cross-artifact | external-evidence` — used consistently across Tasks 5, 6, 10, 11, 14, 15.
- Verdict values: `agree | partial | disagree` (3a per-claim), `supports | partial | contradicts | no-evidence` (3b), `supports | partial | contradicts | insufficient-evidence-for-<X> | requires-data-room` (3c). These differ between sub-stages by design (3a is per-persona-per-claim; 3b/3c is per-claim-aggregate). Documented in Tasks 10, 11, 14.
- Cluster ID format: `<trigger_type>__<frame_id>` — Task 18, 19.

Consistency: clean.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-29-dudu-pmf-signal.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Which approach?
