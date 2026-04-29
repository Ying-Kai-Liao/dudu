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
