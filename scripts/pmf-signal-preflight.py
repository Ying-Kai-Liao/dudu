#!/usr/bin/env python3
"""Pre-flight check for dudu:pmf-signal.

Usage: python3 scripts/pmf-signal-preflight.py <deal-dir> [--force]

Verifies the L1 bundle is present (regardless of which orchestrator
produced it). Prints either a loading ledger (exit 0) or a missing-
artifact failure (exit 2). If pmf-signal.md already exists and --force
was not passed, prints the idempotency message and exits 3.

L1 contract: a `background.md` sentinel in the deal directory PLUS the
four cross-artifact verification targets PMF will triangulate against
in stage 3b. The deck file under `inputs/deck.<ext>` is OPTIONAL — when
present it strengthens Stage 0 claim ingestion, and when absent Stage 0
falls back to manifest.pitch plus the L1 artifacts. We DO NOT check
for `customer-discovery-prep.md`, `personas/_context.md`, or any
artifact owned by a different layer — those couplings were what
blocked fleet-scale composition in v0.

Stdlib only.
"""

from __future__ import annotations

import sys
from pathlib import Path


def fail_missing(slug: str, missing: list[tuple[str, str]]) -> int:
    print(f'pmf-signal cannot start — Layer 1 bundle is incomplete for deal "{slug}":')
    for path, hint in missing:
        print(f"  ✗ {path} ({hint})")
    print()
    print("Run dudu:background-check to produce the L1 bundle, then re-invoke dudu:pmf-signal.")
    return 2


def fail_already_done(deal_dir: Path) -> int:
    rel = f"deals/{deal_dir.name}/pmf-signal.md"
    print(f"Artifact already exists at {rel}. Pass --force to overwrite.")
    return 3


def loading_ledger(deal_dir: Path, founders: list[Path], pitch_sources: list[str]) -> int:
    slug = deal_dir.name
    print(f"Loading L1 bundle for {slug}:")
    print(f"  ✓ background.md (L1 sentinel)")
    names = ", ".join(p.name for p in founders)
    print(f"  ✓ founder-check: {len(founders)} founder(s) ({names})")
    print(f"  ✓ market-context.md")
    print(f"  ✓ competitive-landscape.md")
    print(f"  ✓ market-sizing.md")
    if pitch_sources:
        print(f"  ✓ pitch sources: {', '.join(pitch_sources)}")
    else:
        print(f"  • pitch sources: none (deck optional — Stage 0 will use manifest.pitch + founder/context artifacts)")
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

    pmf_artifact = deal_dir / "pmf-signal.md"
    if pmf_artifact.exists() and not force:
        return fail_already_done(deal_dir)

    missing: list[tuple[str, str]] = []

    if not (deal_dir / "background.md").exists():
        missing.append((f"deals/{slug}/background.md", "the L1 sentinel — produced by dudu:background-check"))

    # Deck is optional. If present it strengthens Stage 0 claim ingestion;
    # if absent, Stage 0 falls back to manifest.pitch + the L1 artifacts.
    pitch_candidates = sorted((deal_dir / "inputs").glob("deck.*")) if (deal_dir / "inputs").is_dir() else []

    founders = sorted(deal_dir.glob("founder-*.md"))
    if not founders:
        missing.append((f"deals/{slug}/founder-*.md", "produced by dudu:founder-check (part of L1)"))

    if not (deal_dir / "market-context.md").exists():
        missing.append((f"deals/{slug}/market-context.md", "produced by dudu:market-context (part of L1)"))

    if not (deal_dir / "competitive-landscape.md").exists():
        missing.append((f"deals/{slug}/competitive-landscape.md", "produced by dudu:competitive-landscape (part of L1)"))

    if not (deal_dir / "market-sizing.md").exists():
        missing.append((f"deals/{slug}/market-sizing.md", "produced by dudu:market-sizing (part of L1)"))

    if missing:
        return fail_missing(slug, missing)

    pitch_sources = [f"inputs/{p.name}" for p in pitch_candidates]
    return loading_ledger(deal_dir, founders, pitch_sources)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
