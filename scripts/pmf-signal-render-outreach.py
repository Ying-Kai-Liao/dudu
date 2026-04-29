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
import sys
from collections import defaultdict
from pathlib import Path

WARM_PATH_RANK = {
    1: 0,
    2: 1,
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

    by_cluster: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        by_cluster[c.get("cluster_id") or "unclustered"].append(c)
    for cluster in by_cluster:
        by_cluster[cluster].sort(key=candidate_priority)

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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
                degree = wp.get("degree")
                suffix = "st" if degree == 1 else "nd"
                warm_desc = f"{degree}{suffix}-degree via {wp.get('bridge_name', '')}"
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
