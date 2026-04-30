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
                        item_prefix = " " * (indent + 2)
                        item_key_prefix = " " * (indent + 4)
                        for item in v:
                            if isinstance(item, dict):
                                first = True
                                for ik, iv in item.items():
                                    if first:
                                        if isinstance(iv, (dict, list)):
                                            lines.append(f"{item_prefix}- {ik}:")
                                            emit(iv, indent + 6)
                                        else:
                                            lines.append(f"{item_prefix}- {ik}: {fmt_scalar(iv)}")
                                        first = False
                                    else:
                                        if isinstance(iv, (dict, list)):
                                            lines.append(f"{item_key_prefix}{ik}:")
                                            emit(iv, indent + 6)
                                        else:
                                            lines.append(f"{item_key_prefix}{ik}: {fmt_scalar(iv)}")
                            else:
                                lines.append(f"{item_prefix}- {fmt_scalar(item)}")
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
