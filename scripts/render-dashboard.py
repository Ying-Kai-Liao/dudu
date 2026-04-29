#!/usr/bin/env python3
"""Render deals/_fleet/dashboard.html — a sortable cross-deal HTML view.

Reads `deals/_fleet/manifest.json` plus per-deal artifacts and emits a self-
contained HTML table with one row per enrolled slug. No third-party
dependencies, no network calls at render time. Idempotent.

Columns (fixed):
  1. Slug              — link to deals/<slug>/report.html
  2. Company           — from deals/<slug>/manifest.json
  3. Founder cred.     — max of `credibility:` front-matter values across
                         deals/<slug>/founder-*.md, or — if missing
  4. Claim ledger      — three small numbers S/C/P pulled from
                         deals/<slug>/personas/verdicts.yaml
                         (also tries deals/<slug>/claim-ledger.yaml)
  5. Contradictions    — count of `verdict: contradicts` rows
  6. Market size       — small / medium / large derived from largest
                         dollar TAM in market-sizing.md
  7. Recommendation    — pass / watch / pursue / pending from MEMO.md
  8. Interview         — done / pending based on customer-discovery.md
  9. Last run          — finished_at timestamp from fleet manifest

Stdlib only.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

FLEET_DIR = Path("deals/_fleet")
MANIFEST = FLEET_DIR / "manifest.json"
DASHBOARD = FLEET_DIR / "dashboard.html"
DEALS_DIR = Path("deals")


# ---------- minimal YAML reading (front-matter + flat verdict tallies) ------

# We avoid PyYAML to keep stdlib-only; the renderer only needs to (a) read
# `key: value` lines from a markdown front-matter block and (b) count
# top-level verdict rows in personas/verdicts.yaml. Both are within reach
# of a small line-based parser. We never try to handle the full YAML spec.


FRONTMATTER_RE = re.compile(r"^---\s*$")
KV_RE = re.compile(r"^([A-Za-z0-9_\-]+)\s*:\s*(.*?)\s*$")


def read_frontmatter(md_path: Path) -> dict[str, str]:
    """Return key→string-value pairs from a YAML front-matter block.

    Returns {} if the file has no front-matter or cannot be read.
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    lines = text.splitlines()
    if not lines or not FRONTMATTER_RE.match(lines[0]):
        return {}
    out: dict[str, str] = {}
    for line in lines[1:]:
        if FRONTMATTER_RE.match(line):
            break
        m = KV_RE.match(line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def count_verdicts(yaml_path: Path) -> dict[str, int] | None:
    """Count `verdict: <value>` lines under verdicts.yaml.

    Returns dict with supports/contradicts/partial counts, or None if the
    file is unreadable or has no verdict lines.
    """
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError:
        return None
    counts = {"supports": 0, "contradicts": 0, "partial": 0}
    found = False
    # Match lines like:    verdict: contradicts
    # (The spec also has `verdict_counts` blocks for persona-reaction rows;
    # those don't have a single verdict, so they're skipped here.)
    for line in text.splitlines():
        m = re.match(r"\s*verdict\s*:\s*([A-Za-z_-]+)\s*$", line)
        if not m:
            continue
        v = m.group(1).lower()
        if v in counts:
            counts[v] += 1
            found = True
    return counts if found else None


# ---------- per-cell extractors ---------------------------------------------


def founder_credibility(deal_dir: Path) -> str:
    """Max of `credibility:` front-matter across founder-*.md, or '—'."""
    best: float | None = None
    for fp in sorted(deal_dir.glob("founder-*.md")):
        fm = read_frontmatter(fp)
        raw = fm.get("credibility")
        if raw is None:
            continue
        try:
            v = float(raw)
        except ValueError:
            continue
        if best is None or v > best:
            best = v
    return "—" if best is None else _fmt_num(best)


def _fmt_num(v: float) -> str:
    if v == int(v):
        return str(int(v))
    return f"{v:.1f}"


def claim_ledger_counts(deal_dir: Path) -> tuple[str, str]:
    """Return (S/C/P cell text, contradictions cell text). '—' if missing."""
    candidates = [
        deal_dir / "personas" / "verdicts.yaml",
        deal_dir / "claim-ledger.yaml",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        counts = count_verdicts(path)
        if not counts:
            continue
        scp = f"{counts['supports']}/{counts['contradicts']}/{counts['partial']}"
        return scp, str(counts["contradicts"])
    return "—", "—"


# Heuristic: scan market-sizing.md for the largest dollar TAM figure and
# bucket it. Bucket boundaries:
#   small  : < $50m
#   medium : $50m – $1B
#   large  : >= $1B
# If no figure parses, return '—'.

DOLLAR_RE = re.compile(
    r"\$\s*([\d,]+(?:\.\d+)?)\s*(b(?:n|illion)?|m(?:n|illion)?)\b",
    re.IGNORECASE,
)


def market_size_band(deal_dir: Path) -> str:
    path = deal_dir / "market-sizing.md"
    if not path.is_file():
        return "—"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "—"
    largest_usd: float = 0.0
    for m in DOLLAR_RE.finditer(text):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        suffix = m.group(2)[0].lower()  # 'b' or 'm'
        usd = val * (1_000_000_000 if suffix == "b" else 1_000_000)
        if usd > largest_usd:
            largest_usd = usd
    if largest_usd == 0.0:
        return "—"
    if largest_usd < 50_000_000:
        return "small"
    if largest_usd < 1_000_000_000:
        return "medium"
    return "large"


# Recommendation tilt: scan MEMO.md for "Pass / Watch / Pursue: <verdict>"
# pattern, then fall back to the first standalone verdict word.

VERDICTS = ("pursue", "watch", "track", "pass")


def recommendation_tilt(deal_dir: Path) -> str:
    path = deal_dir / "MEMO.md"
    if not path.is_file():
        return "pending"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "pending"
    # Strongest signal: "Pass / Watch / Pursue:** **<verdict>**" or similar.
    m = re.search(
        r"Pass\s*/\s*Watch\s*/\s*Pursue[^\n]*?\*\*\s*([A-Za-z]+)\s*\*\*",
        text,
        re.IGNORECASE,
    )
    if m:
        v = m.group(1).strip().lower()
        if v in VERDICTS:
            return v
    # Fallback: first verdict word in a "Recommendation:" block.
    m = re.search(r"Recommendation[^\n]*?\b(pursue|watch|track|pass)\b", text, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return "pending"


def interview_status(deal_dir: Path) -> str:
    return "done" if (deal_dir / "customer-discovery.md").is_file() else "pending"


def deal_company(deal_dir: Path) -> str:
    mf = deal_dir / "manifest.json"
    if not mf.is_file():
        return "—"
    try:
        d = json.loads(mf.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "—"
    return str(d.get("company", "—"))


# ---------- HTML rendering --------------------------------------------------


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


COLUMNS = [
    ("slug", "Slug"),
    ("company", "Company"),
    ("founder", "Founder cred."),
    ("ledger", "Claims S/C/P"),
    ("contradictions", "Contradictions"),
    ("market", "Market size"),
    ("rec", "Recommendation"),
    ("interview", "Interview"),
    ("last_run", "Last run"),
]


def render_row(slug: str, entry: dict[str, Any]) -> str:
    deal_dir = DEALS_DIR / slug
    status = entry.get("status", "pending")
    finished_at = entry.get("finished_at") or "—"

    # If the slug has not finished, lifecycle state replaces the signal-
    # vector data in cells that depend on completed artifacts.
    if status in ("running", "pending"):
        lifecycle = "running…" if status == "running" else "pending"
        company = deal_company(deal_dir) if deal_dir.is_dir() else "—"
        report_link = (
            f'<a href="../{_esc(slug)}/report.html">{_esc(slug)}</a>'
            if deal_dir.is_dir()
            else _esc(slug)
        )
        cells = [
            report_link,
            _esc(company),
            lifecycle,
            lifecycle,
            lifecycle,
            lifecycle,
            lifecycle,
            lifecycle,
            _esc(finished_at),
        ]
    else:
        if not deal_dir.is_dir():
            cells = [
                _esc(slug),
                "—",
                "—",
                "—",
                "—",
                "—",
                "—",
                "—",
                _esc(finished_at),
            ]
        else:
            scp, contradictions = claim_ledger_counts(deal_dir)
            cells = [
                f'<a href="../{_esc(slug)}/report.html">{_esc(slug)}</a>',
                _esc(deal_company(deal_dir)),
                _esc(founder_credibility(deal_dir)),
                _esc(scp),
                _esc(contradictions),
                _esc(market_size_band(deal_dir)),
                _esc(recommendation_tilt(deal_dir)),
                _esc(interview_status(deal_dir)),
                _esc(finished_at),
            ]
        # Mark failed/aborted in the slug cell so the row's state is visible.
        if status in ("failed", "aborted-budget"):
            err = _esc(entry.get("error_summary") or status)
            cells[0] = f'<span title="{err}" class="state-{status}">{cells[0]} ⚠</span>'

    sort_attrs = " ".join(
        f'data-{key}="{_esc(strip_tags(cells[i]))}"'
        for i, (key, _label) in enumerate(COLUMNS)
    )
    tds = "\n".join(f"    <td>{c}</td>" for c in cells)
    return f'  <tr {sort_attrs}>\n{tds}\n  </tr>'


_TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(s: str) -> str:
    return _TAG_RE.sub("", s)


def render(manifest: dict[str, Any]) -> str:
    queue: list[str] = manifest.get("queue", [])
    per_deal: dict[str, Any] = manifest.get("per_deal", {})

    rows = "\n".join(render_row(slug, per_deal.get(slug, {})) for slug in queue)

    in_progress = any(
        per_deal.get(s, {}).get("status") in ("running", "pending") for s in queue
    )
    footer_note = (
        "<p class='footer-note'>⚠ Fleet in progress — re-run "
        "<code>python3 scripts/render-dashboard.py</code> after it completes "
        "for fresh data.</p>"
        if in_progress
        else ""
    )

    header_html = "".join(
        f'<th data-col="{key}" onclick="sortByColumn(\'{key}\')">{label}</th>'
        for key, label in COLUMNS
    )

    fleet_run_id = manifest.get("fleet_run_id", "—")
    mode = manifest.get("mode", "—")
    concurrency = manifest.get("concurrency", "—")

    return TEMPLATE.format(
        header_row=header_html,
        rows=rows,
        footer_note=footer_note,
        fleet_run_id=_esc(str(fleet_run_id)),
        mode=_esc(str(mode)),
        concurrency=_esc(str(concurrency)),
        slug_count=len(queue),
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>dudu fleet dashboard</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; margin: 24px; color: #1a1a1a; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .meta {{ color: #555; font-size: 13px; margin-bottom: 16px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ padding: 8px 10px; border-bottom: 1px solid #e5e5e5; text-align: left; vertical-align: top; }}
  th {{ background: #f7f7f7; cursor: pointer; user-select: none; position: sticky; top: 0; }}
  th:hover {{ background: #ececec; }}
  tr:hover td {{ background: #fafafa; }}
  td a {{ color: #1a4ed8; text-decoration: none; }}
  td a:hover {{ text-decoration: underline; }}
  .state-failed, .state-aborted-budget {{ color: #b91c1c; }}
  .footer-note {{ color: #b45309; font-size: 13px; margin-top: 16px; }}
  code {{ background: #f3f3f3; padding: 1px 4px; border-radius: 3px; }}
</style>
</head>
<body>
<h1>dudu fleet dashboard</h1>
<div class="meta">
  Fleet run: <code>{fleet_run_id}</code> · Mode: <code>{mode}</code> · Concurrency: <code>{concurrency}</code> · Slugs: <code>{slug_count}</code>
</div>
<table id="fleet">
  <thead><tr>{header_row}</tr></thead>
  <tbody>
{rows}
  </tbody>
</table>
{footer_note}
<script>
(function() {{
  let sortKey = null;
  let sortDir = 1;
  window.sortByColumn = function(key) {{
    const tbody = document.querySelector('#fleet tbody');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    if (sortKey === key) {{ sortDir = -sortDir; }} else {{ sortKey = key; sortDir = 1; }}
    rows.sort(function(a, b) {{
      const av = (a.dataset[key] || '').toLowerCase();
      const bv = (b.dataset[key] || '').toLowerCase();
      const an = parseFloat(av), bn = parseFloat(bv);
      const numeric = !isNaN(an) && !isNaN(bn) && av !== '' && bv !== '';
      if (numeric) return (an - bn) * sortDir;
      if (av < bv) return -1 * sortDir;
      if (av > bv) return 1 * sortDir;
      return 0;
    }});
    rows.forEach(function(r) {{ tbody.appendChild(r); }});
  }};
}})();
</script>
</body>
</html>
"""


def main(argv: list[str]) -> int:
    if not MANIFEST.is_file():
        print(
            f"error: {MANIFEST} not found — run dudu:fleet-run (or "
            "scripts/fleet-run.py init) first.",
            file=sys.stderr,
        )
        return 2
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"error: {MANIFEST} is malformed: {e}", file=sys.stderr)
        return 2
    html_text = render(manifest)
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(html_text, encoding="utf-8")
    print(f"wrote {DASHBOARD}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
