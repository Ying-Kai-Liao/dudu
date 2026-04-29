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
