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
    return 2


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

    ledger_rows = []
    pitch_claims_by_id = {c.get("claim_id"): c for c in (pitch.get("claims") or [])}
    for v in verdicts_doc.get("verdicts") or []:
        cid = v.get("claim_id")
        verdict = v.get("verdict") or "unknown"
        method = v.get("verification_method") or "?"
        pc = pitch_claims_by_id.get(cid, {})
        claim_text = pc.get("claim", "?")
        category = pc.get("category", "?")
        source = pc.get("source", "?")
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

    use = aggregates.get("would_use") or {}
    pay = aggregates.get("willing_to_pay") or {}
    wtp = aggregates.get("wtp_ceiling_zar_per_month") or {}

    def pct(c: dict, key: str, total: int) -> str:
        if total == 0:
            return "—"
        return f"{(c.get(key, 0) / total * 100):.0f}%"

    trigger_counts = aggregates.get("by_trigger_type") or {}

    needs_data_room: list[str] = []
    for v in verdicts_doc.get("verdicts") or []:
        if v.get("verdict") == "requires-data-room" or "requires-data-room" in (v.get("flags") or []):
            needs_data_room.append(v.get("claim_id"))

    frame_breakdown = Counter(r.get("frame_id") for r in rows if r.get("frame_id"))

    seed_trigger_counts = Counter((s.get("trigger_type") for s in (seeds_doc.get("seeds") or [])))
    if seed_trigger_counts:
        top = seed_trigger_counts.most_common(1)[0][1]
        share = top / sum(seed_trigger_counts.values())
        mode_collapse_status = "fail" if share > 0.60 else "pass"
    else:
        mode_collapse_status = "n/a"

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
