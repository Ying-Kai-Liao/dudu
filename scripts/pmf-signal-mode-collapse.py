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
