#!/usr/bin/env python3
"""Render a self-contained report.html for a dudu deal directory.

Usage: python3 scripts/render-report.py <deal-dir>

Reads MEMO.md and the standard sub-artifacts, applies a small markdown
subset, and writes <deal-dir>/report.html. Stdlib only.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable


# ---------- markdown subset ----------------------------------------------

INLINE_CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITALIC_STAR = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?!\*)")
ITALIC_UND = re.compile(r"(?<![\w_])_([^_\n]+)_(?!\w)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
PIPE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _inline(text: str) -> str:
    """Apply inline markdown to already-escaped text."""
    # Code first so its contents are not re-formatted.
    placeholders: list[str] = []

    def code_sub(match: "re.Match[str]") -> str:
        placeholders.append(f"<code>{match.group(1)}</code>")
        return f"\x00{len(placeholders) - 1}\x00"

    text = INLINE_CODE.sub(code_sub, text)
    # Italic before bold so `**bold *italic* mix**` renders correctly:
    # the italic regex's lookbehind `(?<![*\w])` skips the `**` boundaries,
    # but matches single-star pairs nested inside; bold then sees a clean
    # `**...**` with no inner asterisks left.
    text = ITALIC_STAR.sub(r"<em>\1</em>", text)
    text = ITALIC_UND.sub(r"<em>\1</em>", text)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = LINK.sub(
        lambda m: f'<a href="{_esc(m.group(2))}" target="_blank" rel="noopener">{m.group(1)}</a>',
        text,
    )

    def restore(match: "re.Match[str]") -> str:
        return placeholders[int(match.group(1))]

    return re.sub(r"\x00(\d+)\x00", restore, text)


def _split_pipe_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [c.strip() for c in stripped.split("|")]


def render_markdown(md: str, heading_offset: int = 0) -> str:
    """Render a markdown string to HTML using the supported subset.

    Strategy: pre-escape, then walk lines as a state machine. Emits one
    HTML block per markdown block. Unsupported constructs degrade to
    paragraphs of escaped text.

    `heading_offset` shifts headers down by N levels (max h6) so artifact
    `## Subhead` can render as <h3> beneath the section's own <h2>.
    """
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    list_stack: list[str] = []  # stack of "ul" / "ol", outermost first

    def close_lists(target_depth: int = 0) -> None:
        while len(list_stack) > target_depth:
            out.append(f"</{list_stack.pop()}>")

    def flush_paragraph(buf: list[str]) -> None:
        if not buf:
            return
        joined = " ".join(line.strip() for line in buf if line.strip())
        if joined:
            out.append(f"<p>{_inline(_esc(joined))}</p>")
        buf.clear()

    para: list[str] = []

    while i < n:
        raw = lines[i]
        stripped = raw.strip()

        # Blank line — close paragraph, keep lists open across one blank line
        if not stripped:
            flush_paragraph(para)
            i += 1
            # If the next non-blank line isn't a list continuation, close lists.
            j = i
            while j < n and not lines[j].strip():
                j += 1
            if j >= n or not _is_list_line(lines[j]):
                close_lists(0)
            continue

        # Fenced code
        if stripped.startswith("```"):
            flush_paragraph(para)
            close_lists(0)
            lang = stripped[3:].strip()
            code: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # skip closing fence (or EOF)
            cls = f' class="lang-{_esc(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>{_esc(chr(10).join(code))}</code></pre>")
            continue

        # Headers
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            flush_paragraph(para)
            close_lists(0)
            level = min(6, len(m.group(1)) + heading_offset)
            content = _inline(_esc(m.group(2).strip()))
            out.append(f"<h{level}>{content}</h{level}>")
            i += 1
            continue

        # Pipe table — needs a header row, separator row, then optional data rows
        if "|" in stripped and i + 1 < n and PIPE_SEP.match(lines[i + 1]):
            flush_paragraph(para)
            close_lists(0)
            header_cells = _split_pipe_row(stripped)
            i += 2  # skip header + separator
            rows: list[list[str]] = []
            while i < n and "|" in lines[i].strip() and lines[i].strip():
                rows.append(_split_pipe_row(lines[i]))
                i += 1
            out.append('<div class="table-wrap"><table>')
            out.append("<thead><tr>")
            for cell in header_cells:
                out.append(f"<th>{_inline(_esc(cell))}</th>")
            out.append("</tr></thead>")
            out.append("<tbody>")
            for row in rows:
                out.append("<tr>")
                for cell in row:
                    out.append(f"<td>{_inline(_esc(cell))}</td>")
                out.append("</tr>")
            out.append("</tbody></table></div>")
            continue

        # Blockquote
        if stripped.startswith(">"):
            flush_paragraph(para)
            close_lists(0)
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].lstrip())
                i += 1
            inner = render_markdown("\n".join(quote), heading_offset=heading_offset)
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        # List item (with up to one level of nesting via 2+ space indent)
        if _is_list_line(raw):
            flush_paragraph(para)
            indent = len(raw) - len(raw.lstrip(" "))
            depth = 1 if indent >= 2 else 0
            kind = _list_kind(raw)
            # Adjust list stack to match (depth, kind)
            while len(list_stack) > depth + 1:
                out.append(f"</{list_stack.pop()}>")
            if len(list_stack) == depth + 1 and list_stack[depth] != kind:
                out.append(f"</{list_stack.pop()}>")
            while len(list_stack) < depth:
                out.append("<ul>")
                list_stack.append("ul")
            if len(list_stack) == depth:
                out.append(f"<{kind}>")
                list_stack.append(kind)
            content = _strip_list_marker(raw)
            out.append(f"<li>{_inline(_esc(content))}</li>")
            i += 1
            continue

        # Plain paragraph line
        para.append(stripped)
        i += 1

    flush_paragraph(para)
    close_lists(0)
    return "\n".join(out)


def _is_list_line(line: str) -> bool:
    s = line.lstrip(" ")
    return bool(re.match(r"(?:[-*]\s+|\d+\.\s+)", s))


def _list_kind(line: str) -> str:
    s = line.lstrip(" ")
    return "ol" if re.match(r"\d+\.\s+", s) else "ul"


def _strip_list_marker(line: str) -> str:
    s = line.lstrip(" ")
    return re.sub(r"^(?:[-*]\s+|\d+\.\s+)", "", s).rstrip()


# ---------- deal-directory parsing ---------------------------------------


SKILL_ORDER = [
    "founder-check",
    "market-problem",
    "customer-discovery-prep",
    "competitive-landscape",
    "market-sizing",
    "customer-discovery-debrief",
]

SKILL_LABELS = {
    "founder-check": "Founder check",
    "market-problem": "Market & problem",
    "customer-discovery-prep": "Discovery prep",
    "competitive-landscape": "Competitive landscape",
    "market-sizing": "Market sizing",
    "customer-discovery-debrief": "Discovery debrief",
}

# (id, title, filename) — discovered conditionally
SECTION_FILES = [
    ("market-problem", "Problem & Product", "market-problem.md"),
    ("customer-discovery", "Customer Signal", "customer-discovery.md"),
    ("customer-discovery-prep", "Customer Discovery Prep", "customer-discovery-prep.md"),
    ("competitive-landscape", "Competitive Landscape", "competitive-landscape.md"),
    ("market-sizing", "Market Sizing", "market-sizing.md"),
]


REC_RE = re.compile(
    r"\*\*Pass\s*/\s*Watch\s*/\s*Pursue:\*\*\s*\*?\*?([A-Za-z]+)",
    re.IGNORECASE,
)


def parse_recommendation(memo: str) -> str | None:
    m = REC_RE.search(memo)
    if not m:
        return None
    verdict = m.group(1).strip().lower()
    if verdict in ("pass", "watch", "pursue"):
        return verdict.capitalize()
    return None


# Strict declarative pattern: a `**Label ...:** ... Rlo m – Rhi m` line.
# Only millions are accepted to avoid mixing units across bars.
def _decl_range(md: str, label_pattern: str) -> tuple[float, float] | None:
    pat = (
        rf"\*\*{label_pattern}[^\n*]*?:\*\*[^\n]*?"
        r"\bR?\s*([\d.]+)\s*m\b\s*[–-]\s*R?\s*([\d.]+)\s*m\b"
    )
    m = re.search(pat, md, re.IGNORECASE)
    if not m:
        return None
    try:
        lo, hi = float(m.group(1)), float(m.group(2))
    except ValueError:
        return None
    if hi < lo or lo < 0:
        return None
    return (lo, hi)


def parse_market_sizing(md: str) -> dict | None:
    """Conservative extraction of wedge / expansion / founder ranges.

    Only matches explicit bold declarations of the form
        **Wedge TAM ...:** ... R<lo>m–R<hi>m ...
    in millions, to keep all bars on a comparable axis. Returns None if no
    ranges parse — the chart is purely additive and must never block the
    report on missing sizing data.
    """
    wedge = _decl_range(md, r"Wedge TAM")
    expansion = _decl_range(md, r"Expansion TAM")
    founder = _decl_range(md, r"Founder claim")
    if not (wedge or expansion or founder):
        return None
    return {"wedge": wedge, "expansion": expansion, "founder": founder}


# ---------- HTML assembly -------------------------------------------------

CSS = """
:root { --accent: #2563eb; --ink: #1a1a1a; --muted: #6b7280; --line: #e5e7eb; --bg: #ffffff; --soft: #f9fafb; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--ink); }
body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; line-height: 1.55; font-size: 16px; }
h1, h2, h3, h4 { font-family: Georgia, "Times New Roman", serif; font-weight: 600; line-height: 1.25; color: var(--ink); }
h1 { font-size: 2rem; margin: 0 0 0.25rem; }
h2 { font-size: 1.5rem; margin: 2rem 0 0.75rem; padding-top: 1rem; border-top: 1px solid var(--line); }
h3 { font-size: 1.2rem; margin: 1.5rem 0 0.5rem; }
h4 { font-size: 1rem; margin: 1rem 0 0.5rem; }
a { color: var(--accent); text-decoration: none; word-break: break-word; }
a:hover { text-decoration: underline; }
p { margin: 0.6rem 0; }
ul, ol { margin: 0.6rem 0 0.6rem 1.25rem; padding-left: 1rem; }
li { margin: 0.2rem 0; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.92em; background: var(--soft); padding: 0.1em 0.35em; border-radius: 3px; }
pre { background: var(--soft); padding: 0.75rem 1rem; border-radius: 6px; overflow-x: auto; border: 1px solid var(--line); }
pre code { background: transparent; padding: 0; }
blockquote { margin: 0.8rem 0; padding: 0.4rem 1rem; border-left: 3px solid var(--accent); background: var(--soft); color: #374151; }
.table-wrap { overflow-x: auto; margin: 1rem 0; border: 1px solid var(--line); border-radius: 4px; }
.table-wrap table { border: none; }
.table-wrap th:first-child, .table-wrap td:first-child { border-left: none; }
.table-wrap th:last-child, .table-wrap td:last-child { border-right: none; }
.table-wrap tr:first-child th { border-top: none; }
.table-wrap tr:last-child td { border-bottom: none; }
table { border-collapse: collapse; width: 100%; min-width: max-content; font-size: 0.92em; }
th, td { border: 1px solid var(--line); padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; min-width: 8ch; }
th { background: var(--soft); font-weight: 600; }

header.report { padding: 1.5rem 2rem 1.25rem; border-bottom: 1px solid var(--line); background: #fafafa; }
header.report .slug { display: block; font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); margin-bottom: 0.4rem; }
header.report .meta { display: flex; flex-wrap: wrap; gap: 1.25rem; align-items: center; margin-top: 0.75rem; font-size: 0.85rem; color: var(--muted); }
header.report time { font-variant-numeric: tabular-nums; }
.pill { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px; font-weight: 600; font-size: 0.85rem; color: #fff; letter-spacing: 0.02em; }
.pill.pass { background: #dc2626; }
.pill.watch { background: #f59e0b; }
.pill.pursue { background: #16a34a; }
.pill.unknown { background: #6b7280; }
.dots { display: inline-flex; gap: 6px; }
.dots .dot { width: 10px; height: 10px; border-radius: 50%; background: #d1d5db; display: inline-block; }
.dots .dot.done { background: #16a34a; }
.callout { margin: 1rem 2rem 0; padding: 0.75rem 1rem; border-left: 4px solid #f59e0b; background: #fffbeb; color: #78350f; border-radius: 4px; font-size: 0.92rem; }

.layout { display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: 0; align-items: start; }
nav.toc { position: sticky; top: 0; align-self: start; max-height: 100vh; overflow-y: auto; padding: 1.5rem 1rem 1.5rem 2rem; border-right: 1px solid var(--line); font-size: 0.9rem; background: #fcfcfc; }
nav.toc h2 { font-family: system-ui, sans-serif; font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin: 0 0 0.5rem; padding: 0; border: none; }
nav.toc ul { list-style: none; margin: 0; padding: 0; }
nav.toc li { margin: 0.15rem 0; }
nav.toc a { color: #374151; display: block; padding: 0.2rem 0.4rem; border-radius: 4px; line-height: 1.35; }
nav.toc a:hover { background: #f3f4f6; text-decoration: none; }
nav.toc a.active { background: #eff6ff; color: var(--accent); font-weight: 600; }
nav.toc ul.group { margin: 0.25rem 0 0.5rem 0.6rem; border-left: 1px solid var(--line); padding-left: 0.6rem; }
nav.toc ul.group a { font-size: 0.85rem; padding: 0.15rem 0.4rem; }
.toc-toggle { display: none; }

main { padding: 2rem 2.5rem; max-width: 800px; }
section.report-section { scroll-margin-top: 1rem; }
details { margin: 0.5rem 0; border: 1px solid var(--line); border-radius: 6px; padding: 0.5rem 0.9rem; background: #fcfcfc; }
details > summary { cursor: pointer; font-weight: 600; color: var(--ink); padding: 0.15rem 0; }
details[open] { background: #fff; }
details[open] > summary { margin-bottom: 0.4rem; }

.chart { margin: 1rem 0; padding: 1rem; border: 1px solid var(--line); border-radius: 6px; background: var(--soft); }
.chart-title { font-weight: 600; margin-bottom: 0.5rem; font-size: 0.95rem; }
.chart-legend { font-size: 0.8rem; color: var(--muted); margin-top: 0.35rem; }

@media (max-width: 900px) {
  .layout { grid-template-columns: minmax(0, 1fr); }
  nav.toc { position: static; max-height: none; border-right: none; border-bottom: 1px solid var(--line); padding: 1rem 1.5rem; display: none; }
  nav.toc.open { display: block; }
  .toc-toggle { display: block; margin: 0.75rem 1.5rem 0; padding: 0.4rem 0.75rem; background: var(--soft); border: 1px solid var(--line); border-radius: 4px; cursor: pointer; }
  main { padding: 1.5rem; max-width: 100%; }
  header.report { padding: 1.25rem 1.5rem; }
  pre, table { max-width: 100%; }
}

@media print {
  nav.toc, .toc-toggle { display: none; }
  .layout { grid-template-columns: 1fr; }
  main { max-width: none; padding: 0 1rem; }
  header.report { background: none; }
  section.report-section { page-break-before: always; }
  section.report-section:first-of-type { page-break-before: auto; }
  a { color: var(--ink); text-decoration: underline; }
}
""".strip()


JS = """
(function () {
  var toggle = document.querySelector('.toc-toggle');
  var toc = document.querySelector('nav.toc');
  if (toggle && toc) {
    toggle.addEventListener('click', function () { toc.classList.toggle('open'); });
  }
  document.querySelectorAll('nav.toc a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = a.getAttribute('href').slice(1);
      var el = document.getElementById(id);
      if (el) {
        e.preventDefault();
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        history.replaceState(null, '', '#' + id);
      }
    });
  });
  if (!('IntersectionObserver' in window)) return;
  var links = {};
  document.querySelectorAll('nav.toc a[href^="#"]').forEach(function (a) {
    links[a.getAttribute('href').slice(1)] = a;
  });
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      var id = entry.target.id;
      var link = links[id];
      if (!link) return;
      if (entry.isIntersecting) {
        Object.keys(links).forEach(function (k) { links[k].classList.remove('active'); });
        link.classList.add('active');
      }
    });
  }, { rootMargin: '-20% 0px -70% 0px', threshold: 0 });
  document.querySelectorAll('section.report-section, [data-toc-target]').forEach(function (sec) {
    observer.observe(sec);
  });
})();
""".strip()


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "section"


def _section(html_id: str, title: str, body_html: str) -> str:
    return (
        f'<section id="{html_id}" class="report-section">'
        f"<h2>{_esc(title)}</h2>{body_html}</section>"
    )


def _split_memo_sections(memo: str) -> dict[str, str]:
    """Split MEMO.md into top-level sections keyed by lowercased H2 title."""
    sections: dict[str, str] = {"_preamble": ""}
    current = "_preamble"
    buf: list[str] = []
    for line in memo.split("\n"):
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            sections[current] = "\n".join(buf).strip("\n")
            current = m.group(1).strip().lower()
            buf = []
        else:
            buf.append(line)
    sections[current] = "\n".join(buf).strip("\n")
    return sections


def _market_chart_svg(data: dict) -> str:
    series: list[tuple[str, tuple[float, float]]] = []
    for label, key in (("Wedge TAM", "wedge"), ("Expansion TAM", "expansion"), ("Founder claim", "founder")):
        rng = data.get(key)
        if rng:
            series.append((label, rng))
    if not series:
        return ""
    max_val = max(hi for _, (_, hi) in series)
    if max_val <= 0:
        return ""
    width = 720
    row_h = 36
    label_w = 140
    bar_x = label_w + 10
    bar_w_max = width - bar_x - 90
    height = row_h * len(series) + 30
    parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="Market sizing comparison" style="max-width:100%;height:auto;">'
    ]
    for idx, (label, (lo, hi)) in enumerate(series):
        y = idx * row_h + 18
        x_lo = bar_x + (lo / max_val) * bar_w_max
        x_hi = bar_x + (hi / max_val) * bar_w_max
        parts.append(
            f'<text x="{label_w}" y="{y + 5}" text-anchor="end" font-family="system-ui,sans-serif" font-size="13" fill="#374151">{_esc(label)}</text>'
        )
        parts.append(
            f'<rect x="{bar_x}" y="{y - 8}" width="{bar_w_max}" height="14" rx="3" fill="#e5e7eb"/>'
        )
        parts.append(
            f'<rect x="{x_lo:.1f}" y="{y - 8}" width="{max(2.0, x_hi - x_lo):.1f}" height="14" rx="3" fill="#2563eb"/>'
        )
        parts.append(
            f'<text x="{x_hi + 6:.1f}" y="{y + 5}" font-family="system-ui,sans-serif" font-size="12" fill="#1a1a1a">{lo:g}–{hi:g}</text>'
        )
    parts.append("</svg>")
    return (
        '<figure class="chart">'
        '<div class="chart-title">Sizing comparison (units as published in market-sizing.md)</div>'
        + "".join(parts)
        + '<div class="chart-legend">Bars show low–high ranges. Founder claim absent if not parseable.</div>'
        + "</figure>"
    )


# ---------- main render ---------------------------------------------------


def _read(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _persona_title(name: str) -> str:
    base = name.removesuffix(".md")
    if base == "_context":
        return "Problem-space context"
    base = base.replace("-", " ")
    return base[:1].upper() + base[1:]


def render_report(deal_dir: Path) -> str:
    manifest_path = deal_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"{manifest_path} not found")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{manifest_path} invalid JSON: {e}") from e

    company = manifest.get("company") or manifest.get("slug", "Untitled deal")
    slug = manifest.get("slug", deal_dir.name)
    skills = manifest.get("skills_completed", {}) or {}
    pitch_note = manifest.get("pitch_reframe_note")

    memo = _read(deal_dir / "MEMO.md")
    memo_sections = _split_memo_sections(memo) if memo else {}
    rec = parse_recommendation(memo) if memo else None

    # ---- header ----
    generated = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pill_label = rec or ("Diligence in progress" if not memo else "Recommendation")
    pill_class = rec.lower() if rec else "unknown"

    dots_html: list[str] = []
    for key in SKILL_ORDER:
        ts = skills.get(key)
        cls = "dot done" if ts else "dot"
        title = f"{SKILL_LABELS[key]}: {ts or 'pending'}"
        dots_html.append(f'<span class="{cls}" title="{_esc(title)}"></span>')

    callout = ""
    if pitch_note:
        callout = f'<div class="callout">{_inline(_esc(pitch_note))}</div>'

    header_html = (
        '<header class="report">'
        f'<span class="slug">{_esc(slug)}</span>'
        f"<h1>{_esc(company)}</h1>"
        '<div class="meta">'
        f'<span class="pill {pill_class}">{_esc(pill_label)}</span>'
        f'<span class="dots" aria-label="Sub-skill status">{"".join(dots_html)}</span>'
        f'<time datetime="{generated}">Generated {generated}</time>'
        "</div></header>"
        + callout
    )

    # ---- sections ----
    sections_html: list[str] = []
    toc: list[tuple[str, str]] = []  # (id, label)

    def add_section(html_id: str, label: str, body_html: str) -> None:
        if not body_html.strip():
            return
        sections_html.append(_section(html_id, label, body_html))
        toc.append((html_id, label))

    # Section bodies render under an <h2> section heading, so demote
    # artifact `## Subhead` → <h3>, etc.
    OFFSET = 1

    # TL;DR (from MEMO)
    if "tl;dr" in memo_sections:
        add_section("tldr", "TL;DR", render_markdown(memo_sections["tl;dr"], heading_offset=OFFSET))

    # Founders — one section per founder-*.md (preferred), fallback to MEMO Founders.
    founder_files = sorted(deal_dir.glob("founder-*.md"))
    if founder_files:
        for fpath in founder_files:
            body = _read(fpath) or ""
            # Strip the file's leading H1 (we use H2 in the report).
            body = re.sub(r"^#\s+.+\n", "", body, count=1)
            html_id = "founder-" + _slug(fpath.stem.removeprefix("founder-"))
            label = "Founder: " + fpath.stem.removeprefix("founder-").replace("-", " ").title()
            add_section(html_id, label, render_markdown(body, heading_offset=OFFSET))
    elif "founders" in memo_sections:
        add_section("founders", "Founders", render_markdown(memo_sections["founders"], heading_offset=OFFSET))

    # Problem & product (prefer artifact, fallback to MEMO)
    mp = _read(deal_dir / "market-problem.md")
    if mp:
        body = re.sub(r"^#\s+.+\n", "", mp, count=1)
        add_section("problem", "Problem & Product", render_markdown(body, heading_offset=OFFSET))
    elif "problem and product" in memo_sections:
        add_section("problem", "Problem & Product", render_markdown(memo_sections["problem and product"], heading_offset=OFFSET))

    # Customer signal (prefer customer-discovery.md, then MEMO summary)
    cd = _read(deal_dir / "customer-discovery.md")
    if cd:
        body = re.sub(r"^#\s+.+\n", "", cd, count=1)
        add_section("customer-signal", "Customer Signal", render_markdown(body, heading_offset=OFFSET))
    elif "customer signal" in memo_sections:
        add_section("customer-signal", "Customer Signal", render_markdown(memo_sections["customer signal"], heading_offset=OFFSET))

    # Customer-discovery prep (only if no debrief)
    if not cd:
        cdp = _read(deal_dir / "customer-discovery-prep.md")
        if cdp:
            body = re.sub(r"^#\s+.+\n", "", cdp, count=1)
            add_section("customer-discovery-prep", "Discovery Prep", render_markdown(body, heading_offset=OFFSET))

    # Competitive landscape
    cl = _read(deal_dir / "competitive-landscape.md")
    if cl:
        body = re.sub(r"^#\s+.+\n", "", cl, count=1)
        add_section("competitive-landscape", "Competitive Landscape", render_markdown(body, heading_offset=OFFSET))
    elif "competitive landscape" in memo_sections:
        add_section("competitive-landscape", "Competitive Landscape", render_markdown(memo_sections["competitive landscape"], heading_offset=OFFSET))

    # Market sizing — prepend SVG chart if parseable
    ms = _read(deal_dir / "market-sizing.md")
    if ms:
        body = re.sub(r"^#\s+.+\n", "", ms, count=1)
        chart = ""
        try:
            data = parse_market_sizing(ms)
            if data:
                chart = _market_chart_svg(data)
        except Exception:
            chart = ""
        add_section("market-sizing", "Market Sizing", chart + render_markdown(body, heading_offset=OFFSET))
    elif "market sizing" in memo_sections:
        add_section("market-sizing", "Market Sizing", render_markdown(memo_sections["market sizing"], heading_offset=OFFSET))

    # Cross-artifact synthesis (MEMO only)
    if "cross-artifact synthesis" in memo_sections:
        add_section("synthesis", "Cross-artifact Synthesis", render_markdown(memo_sections["cross-artifact synthesis"], heading_offset=OFFSET))

    # Recommendation (MEMO only)
    if "recommendation" in memo_sections:
        add_section("recommendation", "Recommendation", render_markdown(memo_sections["recommendation"], heading_offset=OFFSET))

    # Personas — collapsible group
    personas_dir = deal_dir / "personas"
    persona_html = ""
    persona_toc: list[tuple[str, str]] = []
    if personas_dir.is_dir():
        files = sorted(personas_dir.glob("*.md"), key=_persona_sort_key)
        blocks: list[str] = []
        for fpath in files:
            body = _read(fpath) or ""
            body = re.sub(r"^#\s+.+\n", "", body, count=1)
            stem = fpath.stem
            title = _persona_title(fpath.name)
            html_id = "persona-" + _slug(stem)
            persona_toc.append((html_id, title))
            open_attr = " open" if stem == "_context" else ""
            blocks.append(
                f'<details id="{html_id}" data-toc-target{open_attr}>'
                f"<summary>{_esc(title)}</summary>"
                f"{render_markdown(body, heading_offset=2)}"
                "</details>"
            )
        if blocks:
            persona_html = "\n".join(blocks)
            sections_html.append(
                f'<section id="personas" class="report-section"><h2>Personas</h2>{persona_html}</section>'
            )
            toc.append(("personas", "Personas"))

    # Source artifacts
    artifacts: list[str] = []
    for name in [
        "MEMO.md",
        "manifest.json",
        "market-problem.md",
        "competitive-landscape.md",
        "market-sizing.md",
        "customer-discovery-prep.md",
        "customer-discovery.md",
    ]:
        if (deal_dir / name).exists():
            artifacts.append(f'<li><a href="{_esc(name)}">{_esc(name)}</a></li>')
    for fpath in founder_files:
        artifacts.append(f'<li><a href="{_esc(fpath.name)}">{_esc(fpath.name)}</a></li>')
    if personas_dir.is_dir():
        for fpath in sorted(personas_dir.glob("*.md"), key=_persona_sort_key):
            rel = f"personas/{fpath.name}"
            artifacts.append(f'<li><a href="{_esc(rel)}">{_esc(rel)}</a></li>')
    if artifacts:
        body = "<ul>" + "".join(artifacts) + "</ul>"
        sections_html.append(
            f'<section id="artifacts" class="report-section"><h2>Source artifacts</h2>{body}</section>'
        )
        toc.append(("artifacts", "Source artifacts"))

    # ---- TOC HTML ----
    toc_items: list[str] = []
    for html_id, label in toc:
        if html_id == "personas" and persona_toc:
            toc_items.append(
                f'<li><a href="#{html_id}">{_esc(label)}</a>'
                '<ul class="group">'
                + "".join(
                    f'<li><a href="#{pid}">{_esc(plabel)}</a></li>'
                    for pid, plabel in persona_toc
                )
                + "</ul></li>"
            )
        else:
            toc_items.append(f'<li><a href="#{html_id}">{_esc(label)}</a></li>')

    nav_html = (
        '<nav class="toc" aria-label="Table of contents">'
        '<h2>Contents</h2>'
        f'<ul>{"".join(toc_items)}</ul>'
        "</nav>"
    )
    toggle_html = '<button class="toc-toggle" type="button">Contents</button>'

    title = f"{company} — diligence report"
    return (
        "<!doctype html>\n"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_esc(title)}</title>"
        f"<style>{CSS}</style>"
        "</head><body>"
        + header_html
        + toggle_html
        + '<div class="layout">'
        + nav_html
        + "<main>"
        + "\n".join(sections_html)
        + "</main></div>"
        + f"<script>{JS}</script>"
        "</body></html>\n"
    )


def _persona_sort_key(path: Path) -> tuple[int, int, str]:
    stem = path.stem
    if stem == "_context":
        return (0, 0, stem)
    m = re.match(r"persona-(\d+)$", stem)
    if m:
        return (1, int(m.group(1)), stem)
    m = re.match(r"round-(\d+)$", stem)
    if m:
        return (2, int(m.group(1)), stem)
    return (3, 0, stem)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: render-report.py <deal-dir>", file=sys.stderr)
        return 2
    deal_dir = Path(argv[1]).resolve()
    if not deal_dir.is_dir():
        print(f"{deal_dir} is not a directory", file=sys.stderr)
        return 1
    try:
        out = render_report(deal_dir)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 1
    target = deal_dir / "report.html"
    tmp = deal_dir / "report.html.tmp"
    tmp.write_text(out, encoding="utf-8")
    os.replace(tmp, target)
    print(str(target))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
