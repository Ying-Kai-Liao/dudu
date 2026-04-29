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
