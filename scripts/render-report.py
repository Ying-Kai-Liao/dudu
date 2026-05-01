#!/usr/bin/env python3
"""Render a self-contained report.html for a dudu deal directory.

This renderer has four input-shape branches, selected automatically based
on which pmf-signal artifacts exist in the deal directory. They are tried
in priority order; the first matching branch wins:

  1. full              — pitch.yaml AND personas/verdicts.yaml both present.
                         Renders the star-led layout: header →
                         claim ledger × verdict matrix →
                         cross-artifact contradictions → warm-path outreach
                         top-N → drill-down (collapsed) → source artifacts.
  2. pitch-only        — pitch.yaml present, verdicts.yaml absent.
                         Renders the ledger with every verdict cell as
                         "pending"; replaces the contradictions section
                         with a "PMF run incomplete" note.
  3. markdown-fallback — neither yaml present, but pmf-signal.md is.
                         Renders pmf-signal.md as a single section in
                         place of the three structured sections.
  4. legacy            — none of pitch.yaml / verdicts.yaml / pmf-signal.md
                         exist. Renders the prior artifact-by-artifact
                         layout (today's behavior).

Branches 2 and 3 emit a stderr warning naming the missing files.
The renderer never crashes on malformed yaml; on parse failure the file
is treated as absent and the renderer falls back to the next branch.

Usage: python3 scripts/render-report.py <deal-dir>

Stdlib + PyYAML only.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml


OUTREACH_TOP_N = 10


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

# (id, title, filename) — discovered conditionally. Layered architecture
# uses market-context.md; legacy deals use market-problem.md. The renderer
# prefers the new filename and falls back to the legacy one.
SECTION_FILES = [
    ("market-problem", "Problem & Product", "market-context.md"),
    ("market-problem-legacy", "Problem & Product", "market-problem.md"),
    ("customer-discovery", "Customer Signal", "customer-discovery.md"),
    ("customer-discovery-prep", "Customer Discovery Prep", "customer-discovery-prep.md"),
    ("competitive-landscape", "Competitive Landscape", "competitive-landscape.md"),
    ("market-sizing", "Market Sizing", "market-sizing.md"),
]


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


# ---------- pmf-signal yaml inputs ---------------------------------------


@dataclass
class PMFInputs:
    """Bundled view of the pmf-signal artifacts that drive the new layout.

    Each *_status field is one of "present", "missing", or "malformed".
    """

    pitch: dict | None = None
    verdicts: dict | None = None
    aggregates: dict | None = None
    outreach_md: str | None = None
    pmf_signal_md: str | None = None
    pitch_status: str = "missing"
    verdicts_status: str = "missing"
    aggregates_status: str = "missing"
    outreach_status: str = "missing"
    pmf_signal_status: str = "missing"


def _load_yaml(path: Path) -> tuple[dict | None, str]:
    """Load a yaml file; on parse failure, log to stderr and treat as absent."""
    if not path.exists() or not path.is_file():
        return None, "missing"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"warning: could not read {path}: {e}", file=sys.stderr)
        return None, "malformed"
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        print(f"warning: could not parse {path}: {e}", file=sys.stderr)
        return None, "malformed"
    if data is None:
        return {}, "present"
    if not isinstance(data, dict):
        print(
            f"warning: {path} did not parse to a mapping; treating as malformed",
            file=sys.stderr,
        )
        return None, "malformed"
    return data, "present"


def _load_text(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def load_pmf_inputs(deal_dir: Path) -> PMFInputs:
    pitch, pitch_status = _load_yaml(deal_dir / "pitch.yaml")
    verdicts, verdicts_status = _load_yaml(deal_dir / "personas" / "verdicts.yaml")
    aggregates, aggregates_status = _load_yaml(deal_dir / "personas" / "aggregates.yaml")
    outreach_md = _load_text(deal_dir / "outreach.md")
    pmf_signal_md = _load_text(deal_dir / "pmf-signal.md")
    return PMFInputs(
        pitch=pitch,
        verdicts=verdicts,
        aggregates=aggregates,
        outreach_md=outreach_md,
        pmf_signal_md=pmf_signal_md,
        pitch_status=pitch_status,
        verdicts_status=verdicts_status,
        aggregates_status=aggregates_status,
        outreach_status="present" if outreach_md is not None else "missing",
        pmf_signal_status="present" if pmf_signal_md is not None else "missing",
    )


def detect_branch(inputs: PMFInputs, deal_dir: Path) -> str:
    """Return one of 'full', 'pitch-only', 'markdown-fallback', 'legacy'.

    Detection order matches design.md Decision 5:
    - both pitch.yaml + verdicts.yaml present → full
    - pitch.yaml present, verdicts.yaml absent → pitch-only
    - neither yaml present, pmf-signal.md present → markdown-fallback
    - none present → legacy
    """
    pitch_present = inputs.pitch_status == "present"
    verdicts_present = inputs.verdicts_status == "present"
    if pitch_present and verdicts_present:
        return "full"
    if pitch_present:
        print(
            f"warning: pitch.yaml found but verdicts.yaml is missing in {deal_dir}; "
            "rendering pitch-only branch with verdicts as pending",
            file=sys.stderr,
        )
        return "pitch-only"
    if inputs.pmf_signal_status == "present":
        missing = []
        if inputs.pitch_status != "present":
            missing.append("pitch.yaml")
        if inputs.verdicts_status != "present":
            missing.append("personas/verdicts.yaml")
        print(
            f"warning: pmf-signal.md found but yaml artifacts missing in {deal_dir} "
            f"({', '.join(missing)}); rendering markdown-fallback branch",
            file=sys.stderr,
        )
        return "markdown-fallback"
    return "legacy"


# ---------- ledger and verdict matrix ------------------------------------


VERDICT_SEVERITY_RANK = {
    "contradicts": 0,
    "partial": 1,
    "no-evidence": 2,
    "supports": 3,
    "pending": 4,
}

CATEGORY_ORDER = ["founder", "product", "market", "traction", "ask"]

# Map raw category labels (as they appear in pitch.yaml) to canonical buckets
# used by the worst-news-first ordering.
CATEGORY_ALIASES = {
    "founder": "founder",
    "founders": "founder",
    "founder-background": "founder",
    "team": "founder",
    "product": "product",
    "feature": "product",
    "pain": "product",
    "problem": "product",
    "market": "market",
    "market-size": "market",
    "tam": "market",
    "competitive": "market",
    "category": "market",
    "traction": "traction",
    "customer-count": "traction",
    "customers": "traction",
    "growth": "traction",
    "revenue": "traction",
    "metric": "traction",
    "gtm": "traction",
    "gtm-distribution": "traction",
    "ask": "ask",
    "raise": "ask",
    "round": "ask",
}


def canonical_category(category: str | None) -> str | None:
    if not category:
        return None
    cat = category.lower().strip()
    if cat in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[cat]
    for k, v in CATEGORY_ALIASES.items():
        if k in cat:
            return v
    return None


def category_rank(category: str | None) -> tuple[int, str]:
    """Return a sort key: (canonical-rank, raw-lower) so unknowns sort last alpha."""
    canon = canonical_category(category)
    if canon and canon in CATEGORY_ORDER:
        return (CATEGORY_ORDER.index(canon), canon)
    return (len(CATEGORY_ORDER), (category or "").lower())


def _normalize_method(method: str | None) -> str:
    """Map the raw verification_method label to the canonical badge name."""
    if not method:
        return "unknown"
    m = method.lower().strip()
    if m in ("persona-reaction", "persona_reaction"):
        return "persona-reaction"
    if m in ("cross-artifact", "cross_artifact"):
        return "cross-artifact"
    if m in ("external", "external-evidence", "external_evidence"):
        return "external"
    return m


def normalize_verdict(verdict_record: dict | None) -> str:
    """Map a raw verdict record to one of the canonical buckets.

    Buckets: contradicts | partial | no-evidence | supports | pending.
    """
    if verdict_record is None:
        return "pending"
    method = _normalize_method(
        verdict_record.get("verification_method") or verdict_record.get("verification")
    )
    if method == "persona-reaction":
        counts = verdict_record.get("verdict_counts") or {}
        if not counts:
            return "no-evidence"
        # Tie-break alphabetically for stable behavior.
        top_label = max(
            counts.items(), key=lambda kv: (kv[1], -ord(kv[0][:1] or "z"))
        )[0]
        if top_label in ("agree", "supports"):
            return "supports"
        if top_label in ("disagree", "contradicts"):
            return "contradicts"
        if top_label in ("partial",):
            return "partial"
        return "no-evidence"
    explicit = verdict_record.get("verdict")
    if explicit is None:
        return "no-evidence"
    v = str(explicit).lower().strip()
    if v in VERDICT_SEVERITY_RANK:
        return v
    if v.startswith("insufficient-evidence") or v == "requires-data-room":
        return "no-evidence"
    if v in ("agree", "yes"):
        return "supports"
    if v in ("disagree", "no"):
        return "contradicts"
    return "no-evidence"


def _evidence_html(verdict_record: dict | None, method: str, verdict: str) -> str:
    """Build the evidence cell HTML (already-escaped + inline)."""
    if verdict == "pending":
        return '<span class="evidence-pending">awaiting verification</span>'
    if verdict_record is None:
        return ""
    if method == "persona-reaction":
        counts = verdict_record.get("verdict_counts") or {}
        verbatims = verdict_record.get("representative_verbatims") or {}
        n_total = sum(counts.values()) if counts else 0
        if not counts:
            return ""
        top_label = max(counts.items(), key=lambda kv: kv[1])[0]
        n_top = counts.get(top_label, 0)
        verbatim = verbatims.get(top_label, "")
        if verbatim:
            tail = f' ({n_top}/{n_total} personas — "{top_label}")'
            return f"&ldquo;{_esc(verbatim)}&rdquo;{_esc(tail)}"
        return _esc(f"{n_top}/{n_total} personas — {top_label}")
    if method == "cross-artifact":
        contradicting = verdict_record.get("contradicting_quotes") or []
        supporting = verdict_record.get("supporting_quotes") or []
        picked = (contradicting or supporting)[:1]
        if picked:
            q = picked[0] or {}
            quote = q.get("quote", "") if isinstance(q, dict) else str(q)
            location = q.get("location", "") if isinstance(q, dict) else ""
            evidence_field = verdict_record.get("evidence")
            if isinstance(evidence_field, dict):
                # Spec form: {file, quote, line_hint}
                quote = evidence_field.get("quote", quote)
                location = evidence_field.get("file", location)
            html_parts = [f"&ldquo;{_esc(quote)}&rdquo;"]
            if location:
                html_parts.append(f' <span class="evidence-loc">({_esc(location)})</span>')
            return "".join(html_parts)
        evidence_field = verdict_record.get("evidence")
        if isinstance(evidence_field, dict):
            quote = evidence_field.get("quote", "")
            location = evidence_field.get("file", "")
            if quote:
                parts = [f"&ldquo;{_esc(quote)}&rdquo;"]
                if location:
                    parts.append(f' <span class="evidence-loc">({_esc(location)})</span>')
                return "".join(parts)
        rationale = verdict_record.get("verdict_rationale", "")
        return _esc(rationale)
    if method == "external":
        evidence_field = verdict_record.get("evidence")
        if isinstance(evidence_field, dict):
            url = evidence_field.get("url")
            quote = evidence_field.get("quote", "")
            if url:
                return f'<a href="{_esc(url)}" target="_blank" rel="noopener">{_esc(quote or url)}</a>'
            if quote:
                return f"&ldquo;{_esc(quote)}&rdquo;"
        rationale = verdict_record.get("verdict_rationale", "")
        return _esc(rationale)
    return _esc(verdict_record.get("verdict_rationale", ""))


def sort_ledger_rows(
    pitch: dict | None,
    verdicts: dict | None,
    *,
    force_pending: bool = False,
) -> list[dict]:
    """Build a sorted list of ledger rows joining pitch and verdicts on claim_id.

    If `force_pending` is True (pitch-only branch), every row's verdict bucket
    is forced to "pending" regardless of what verdicts.yaml says.
    """
    claims = (pitch or {}).get("claims") or []
    verdicts_list = (verdicts or {}).get("verdicts") or (verdicts or {}).get("claim_verdicts") or []
    verdicts_by_id = {v.get("claim_id"): v for v in verdicts_list if v.get("claim_id")}

    rows: list[dict] = []
    for c in claims:
        if not isinstance(c, dict):
            continue
        cid = c.get("claim_id")
        if not cid:
            continue
        v = verdicts_by_id.get(cid)
        method = _normalize_method(
            c.get("verification_method")
            or (v.get("verification_method") if isinstance(v, dict) else None)
        )
        if force_pending or v is None:
            verdict_bucket = "pending"
            verdict_record = v if not force_pending else None
        else:
            verdict_bucket = normalize_verdict(v)
            verdict_record = v
        rows.append(
            {
                "claim_id": cid,
                "claim": c.get("claim", ""),
                "category": c.get("category", "") or "",
                "source": c.get("source", "") or "",
                "verification": method,
                "verdict": verdict_bucket,
                "verdict_record": verdict_record,
                "claim_record": c,
            }
        )

    rows.sort(
        key=lambda r: (
            VERDICT_SEVERITY_RANK.get(r["verdict"], 99),
            category_rank(r["category"]),
            r["claim_id"],
        )
    )
    return rows


def _method_badge(method: str) -> str:
    label = method if method != "unknown" else "?"
    return f'<span class="method-badge {_esc(method)}">{_esc(label)}</span>'


def _verdict_badge(verdict: str) -> str:
    label = verdict if verdict != "pending" else "pending"
    return f'<span class="verdict-badge {_esc(verdict)}">{_esc(label)}</span>'


def render_ledger_row(row: dict) -> str:
    """Render one <tr> for the ledger table."""
    method = row["verification"]
    verdict = row["verdict"]
    evidence = _evidence_html(row["verdict_record"], method, verdict)
    if method == "persona-reaction" and verdict != "pending":
        evidence += (
            '<span class="stance-b-caption">Calibrated prior, not signal — '
            "see PMF stage 3a</span>"
        )
    return (
        "<tr>"
        f'<td class="claim-cell">{_inline(_esc(row["claim"]))}</td>'
        f'<td>{_esc(row["category"])}</td>'
        f'<td>{_esc(row["source"])}</td>'
        f"<td>{_method_badge(method)}</td>"
        f"<td>{_verdict_badge(verdict)}</td>"
        f'<td class="evidence-cell">{evidence}</td>'
        "</tr>"
    )


def _verdict_counts(rows: list[dict]) -> dict[str, int]:
    counts = {k: 0 for k in VERDICT_SEVERITY_RANK}
    for r in rows:
        v = r.get("verdict", "no-evidence")
        if v in counts:
            counts[v] += 1
    return counts


def _verdict_strip_html(rows: list[dict]) -> str:
    counts = _verdict_counts(rows)
    pills: list[str] = []
    for label in ("contradicts", "partial", "no-evidence", "supports"):
        pills.append(
            f'<span class="vc-pill {label}">{label}: {counts[label]}</span>'
        )
    if counts["pending"]:
        pills.append(
            f'<span class="vc-pill pending">pending: {counts["pending"]}</span>'
        )
    legend = (
        "Verification methods: "
        '<span class="method-badge persona-reaction">persona-reaction</span> '
        "(calibrated prior, not signal) · "
        '<span class="method-badge cross-artifact">cross-artifact</span> '
        "(real signal triangulated against prior dudu artifacts) · "
        '<span class="method-badge external">external</span> '
        "(real signal from bounded web checks)."
    )
    return (
        f'<div class="verdict-strip">{"".join(pills)}</div>'
        '<p class="verdict-strip-caption">Worst-news first.</p>'
        f'<p class="verdict-strip-legend">{legend}</p>'
    )


def render_ledger_section(rows: list[dict]) -> str:
    """Render the ledger × verdict matrix table."""
    if not rows:
        return ""
    body: list[str] = [_verdict_strip_html(rows)]
    body.append('<div class="table-wrap"><table class="ledger-table">')
    body.append(
        "<thead><tr>"
        "<th>Claim</th><th>Category</th><th>Source</th>"
        "<th>Verification</th><th>Verdict</th><th>Evidence</th>"
        "</tr></thead><tbody>"
    )
    pending_header_emitted = False
    for r in rows:
        if r["verdict"] == "pending" and not pending_header_emitted:
            body.append(
                '<tr class="pending-group-row"><td colspan="6">'
                '<span class="pending-group-header">Verdicts pending</span>'
                "</td></tr>"
            )
            pending_header_emitted = True
        body.append(render_ledger_row(r))
    body.append("</tbody></table></div>")
    return "\n".join(body)


# ---------- contradictions section ---------------------------------------


def select_contradiction_rows(rows: list[dict]) -> list[dict]:
    """Return rows where verification == cross-artifact AND verdict in {contradicts, partial}."""
    out: list[dict] = []
    for r in rows:
        if r["verification"] != "cross-artifact":
            continue
        if r["verdict"] in ("contradicts", "partial"):
            out.append(r)
    return out


def render_contradiction_entry(row: dict) -> str:
    """Render one cross-artifact contradiction entry."""
    rec = row["verdict_record"] or {}
    claim_text = row["claim"]
    contradicting = rec.get("contradicting_quotes") or []
    supporting = rec.get("supporting_quotes") or []
    picked_list = contradicting or supporting
    quote = ""
    location = ""
    if picked_list:
        q = picked_list[0]
        if isinstance(q, dict):
            quote = q.get("quote", "") or ""
            location = q.get("location", "") or ""
    evidence_field = rec.get("evidence")
    if isinstance(evidence_field, dict):
        quote = evidence_field.get("quote", quote) or quote
        location = evidence_field.get("file", location) or location
    if not quote:
        quote = rec.get("verdict_rationale", "") or ""

    file_link = ""
    file_path = location
    # location may be like "customer-discovery.md:34" — strip the line hint
    if file_path:
        file_only = re.split(r"[:\s]", file_path, maxsplit=1)[0]
        file_link = (
            f'<span class="file-pointer">→ '
            f'<a href="{_esc(file_only)}">{_esc(file_path)}</a></span>'
        )

    pieces = [
        '<div class="contradiction-entry">',
        f'<div class="claim-text">{_inline(_esc(claim_text))}</div>',
    ]
    if quote:
        pieces.append(
            f"<blockquote>{_inline(_esc(quote))}</blockquote>"
        )
    if file_link:
        pieces.append(file_link)
    pieces.append("</div>")
    return "".join(pieces)


def render_contradictions_section(rows: list[dict]) -> str:
    contradiction_rows = select_contradiction_rows(rows)
    if not contradiction_rows:
        return ""
    return "\n".join(render_contradiction_entry(r) for r in contradiction_rows)


# ---------- warm-path outreach -------------------------------------------


def parse_outreach(outreach_md_text: str | None) -> list[dict]:
    """Extract outreach entries from outreach.md in source-file order.

    Recognizes pipe-table data rows with a numeric first cell. Captures
    `name`, `channel`, `warm_path`, `match_evidence`, `post_hook`, and
    `cluster` (from the most recent `## Cluster: ...` heading).
    """
    if not outreach_md_text:
        return []
    entries: list[dict] = []
    current_cluster: str | None = None
    for raw in outreach_md_text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("## Cluster:"):
            current_cluster = stripped[len("## Cluster:"):].strip()
            continue
        if not stripped or "|" not in stripped:
            continue
        if PIPE_SEP.match(raw):
            continue
        cells = _split_pipe_row(stripped)
        if not cells:
            continue
        # Header row has "#" or "Name" in first cell.
        first = cells[0].lower()
        if first in ("#", "name", "") or any(
            c.lower() in ("name", "channel", "warm path", "match evidence", "post hook")
            for c in cells
        ):
            continue
        # Data row must have a numeric first cell.
        try:
            int(first)
        except ValueError:
            continue
        entries.append(
            {
                "name": cells[1] if len(cells) > 1 else "",
                "channel": cells[2] if len(cells) > 2 else "",
                "warm_path": cells[3] if len(cells) > 3 else "",
                "match_evidence": cells[4] if len(cells) > 4 else "",
                "post_hook": cells[5] if len(cells) > 5 else "",
                "cluster": current_cluster or "",
            }
        )
    return entries


def render_outreach_section(entries: list[dict]) -> str:
    """Render the warm-path outreach top-N table.

    Returns "" if entries is empty.
    """
    if not entries:
        return ""
    embedded = entries[: OUTREACH_TOP_N]
    parts: list[str] = ['<div class="table-wrap"><table class="outreach-table">']
    parts.append(
        "<thead><tr>"
        "<th>#</th><th>Name</th><th>Cluster</th><th>Warm path</th>"
        "<th>Match evidence</th><th>Channel</th>"
        "</tr></thead><tbody>"
    )
    for idx, e in enumerate(embedded, start=1):
        parts.append("<tr>")
        parts.append(f"<td>{idx}</td>")
        parts.append(f"<td>{_inline(_esc(e['name']))}</td>")
        parts.append(f"<td>{_inline(_esc(e['cluster']))}</td>")
        parts.append(f"<td>{_inline(_esc(e['warm_path']))}</td>")
        parts.append(
            f'<td class="warm-quote">{_inline(_esc(e["match_evidence"]))}</td>'
        )
        parts.append(f"<td>{_inline(_esc(e['channel']))}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    if len(entries) > OUTREACH_TOP_N:
        parts.append(
            f'<a class="outreach-more" href="outreach.md">'
            f"all {len(entries)} — see outreach.md</a>"
        )
    return "\n".join(parts)


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

.recordings-block { margin: 0 0 1.25rem; padding: 0.85rem 1rem; border: 1px solid var(--line); border-radius: 6px; background: var(--soft); }
.recordings-block h3 { font-family: system-ui, -apple-system, sans-serif; font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); margin: 0 0 0.6rem; padding: 0; border: none; }
.recordings-list { list-style: none; margin: 0; padding: 0; }
.recordings-list li { margin: 0.4rem 0; }
.recordings-list .recording-label { font-size: 0.85rem; color: var(--muted); margin-bottom: 0.2rem; }
.recordings-list audio { width: 100%; max-width: 480px; }


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

main { padding: 2rem 2.5rem; max-width: 1280px; }
section.report-section, details.report-section { scroll-margin-top: 1rem; }
section.star-section > h2::before { content: "★ "; color: #f59e0b; font-weight: normal; }
details { margin: 0.5rem 0; border: 1px solid var(--line); border-radius: 6px; padding: 0.5rem 0.9rem; background: #fcfcfc; }
details > summary { cursor: pointer; font-weight: 600; color: var(--ink); padding: 0.15rem 0; }
details[open] { background: #fff; }
details[open] > summary { margin-bottom: 0.4rem; }

.dashboard-shell { margin: 0 0 2rem; padding: 1rem 0 0; }
.dashboard-shell > h2 { text-align: center; margin: 0 0 0.1rem; padding: 0; border: none; font-family: system-ui, -apple-system, sans-serif; font-size: 1.35rem; font-weight: 750; }
.dashboard-subtitle { text-align: center; color: var(--muted); margin: 0 0 1.2rem; font-size: 0.92rem; }
.dashboard-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr) minmax(0, 1.1fr); gap: 1rem; }
.dashboard-card { min-width: 0; border: 1px solid #e6e8f2; border-radius: 8px; padding: 1.1rem; background: linear-gradient(180deg, #fff 0%, #fdfdff 100%); box-shadow: 0 10px 28px rgba(45, 40, 90, 0.06); }
.dashboard-card h3 { margin: 0; font-family: system-ui, -apple-system, sans-serif; font-size: 1.08rem; line-height: 1.25; }
.dashboard-card h4 { margin: 0 0 0.45rem; font-family: system-ui, -apple-system, sans-serif; font-size: 0.9rem; color: #303247; }
.card-title { display: flex; align-items: flex-start; gap: 0.7rem; margin-bottom: 1rem; }
.step { flex: 0 0 auto; display: inline-grid; place-items: center; width: 2rem; height: 2rem; border-radius: 6px; color: #fff; background: linear-gradient(135deg, #6d5dfc, #5338e8); font-weight: 800; box-shadow: 0 4px 10px rgba(83, 56, 232, 0.25); }
.dashboard-badge { display: inline-flex; align-items: center; min-height: 1.7rem; padding: 0.25rem 0.75rem; border-radius: 999px; font-weight: 750; font-size: 0.78rem; white-space: nowrap; }
.dashboard-badge.positive { background: #dff8e8; color: #15803d; }
.dashboard-badge.warning { background: #fef3c7; color: #9a5b00; }
.dashboard-badge.negative { background: #fee2e2; color: #b91c1c; }
.dashboard-badge.neutral { background: #eef0f7; color: #555b70; }
.founder-chips { display: grid; gap: 0.55rem; margin: 0.2rem 0 0.85rem; }
.founder-chip { display: flex; align-items: center; gap: 0.65rem; font-weight: 650; color: #303247; }
.avatar { display: inline-grid; place-items: center; width: 2.45rem; height: 2.45rem; border-radius: 999px; color: #fff; font-weight: 800; letter-spacing: 0; }
.avatar-0 { background: #334155; }
.avatar-1 { background: #4f46e5; }
.avatar-2 { background: #0f766e; }
.check-list { list-style: none; padding: 0; margin: 0.2rem 0 1rem; display: grid; gap: 0.35rem; }
.check-list li { display: flex; align-items: center; gap: 0.55rem; color: #555b70; font-size: 0.92rem; }
.check-list li span { width: 1rem; height: 1rem; border-radius: 999px; display: inline-block; position: relative; border: 2px solid #bcc2d2; }
.check-list li.ok span { border-color: #59c98a; }
.check-list li.ok span::after { content: ""; position: absolute; left: 3px; top: 1px; width: 5px; height: 8px; border: solid #16a34a; border-width: 0 2px 2px 0; transform: rotate(45deg); }
.check-list li.pending span { border-style: dashed; }
.persona-tabs { display: flex; gap: 0.6rem; margin-bottom: 0.9rem; }
.persona-tabs span { padding: 0.42rem 0.85rem; border: 1px solid #e2e5ef; border-radius: 6px; color: #686d80; background: #fff; font-weight: 650; }
.persona-tabs .active { background: linear-gradient(135deg, #7a68ff, #6246ea); color: #fff; border-color: transparent; }
.pmf-grid { display: grid; grid-template-columns: minmax(0, 1fr) 8rem; gap: 1rem; align-items: start; }
.pain-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.45rem; }
.pain-list li { position: relative; padding-left: 1.05rem; color: #555b70; font-size: 0.88rem; line-height: 1.35; }
.pain-list li::before { content: ""; position: absolute; left: 0; top: 0.55em; width: 0.35rem; height: 0.35rem; border-radius: 999px; background: #6656ec; }
.score-box { border: 1px solid #e3e6f0; border-radius: 8px; min-height: 7.2rem; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #fff; }
.score-box span { color: #34384d; font-weight: 650; }
.score-box strong { color: #16a34a; font-size: 2rem; line-height: 1; margin: 0.35rem 0; }
.score-box small { color: var(--muted); }
.audio-wave { display: flex; align-items: center; gap: 0.35rem; margin: 0.4rem 0 1.1rem; color: #8b7dff; }
.audio-wave .play-dot { display: inline-grid; place-items: center; width: 2rem; height: 2rem; border-radius: 999px; background: #7b6bff; color: #fff; font-size: 0.8rem; }
.audio-wave span:not(.play-dot) { width: 0.32rem; height: 2.1rem; border-radius: 999px; background: linear-gradient(#c8bfff, #8068f1); transform-origin: center; }
.audio-wave span:nth-child(3) { height: 1.1rem; }
.audio-wave span:nth-child(4) { height: 1.8rem; }
.audio-wave span:nth-child(5) { height: 0.9rem; }
.audio-wave span:nth-child(6) { height: 2.4rem; }
.call-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin-bottom: 0.85rem; }
.dashboard-metric span { display: block; color: #555b70; font-size: 0.82rem; }
.dashboard-metric strong { display: block; color: #151827; font-size: 1.45rem; line-height: 1.15; margin-top: 0.1rem; }
.calls-card blockquote { margin: 0.6rem 0 1rem; border: none; border-radius: 7px; background: #f2efff; color: #5543d8; padding: 0.75rem 0.85rem; font-weight: 600; }
.stage-card, .market-card { grid-column: span 1; }
.market-card { grid-column: span 2; }
.stage-line { display: grid; grid-template-columns: repeat(4, 1fr); align-items: center; gap: 0; margin: 1rem 1rem 0.3rem; position: relative; }
.stage-line::before { content: ""; position: absolute; left: 0; right: 0; top: 50%; height: 3px; background: #d7d9e5; transform: translateY(-50%); }
.stage-line span { position: relative; z-index: 1; width: 1.1rem; height: 1.1rem; border-radius: 999px; background: #a5a7b8; justify-self: center; }
.stage-line span.active { background: #5b46ea; box-shadow: 0 0 0 4px rgba(91, 70, 234, 0.12); }
.stage-labels { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.35rem; color: #686d80; font-weight: 650; font-size: 0.78rem; text-align: center; margin-bottom: 1rem; }
.stage-labels span:first-child { color: #5b46ea; }
.insight-box { display: flex; align-items: flex-start; gap: 0.65rem; background: #f3f0ff; color: #4f46e5; border: 1px solid #e5ddff; border-radius: 7px; padding: 0.75rem; }
.insight-box p { margin: 0; font-weight: 600; line-height: 1.45; }
.bulb { display: inline-grid; place-items: center; flex: 0 0 auto; width: 1.45rem; height: 1.45rem; border: 2px solid #604eea; border-radius: 999px; font-weight: 800; }
.market-grid { display: grid; grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr); gap: 1.5rem; align-items: start; }
.mini-label { display: block; color: #555b70; font-size: 0.8rem; font-weight: 650; margin-top: 0.65rem; }
.mini-label:first-child { margin-top: 0; }
.market-grid strong { display: block; color: #222538; margin-top: 0.05rem; }
.market-grid .green { color: #16a34a; }
.competitor-bars { list-style: none; padding: 0; margin: 0.45rem 0 0; display: grid; gap: 0.7rem; }
.competitor-bars li { display: grid; grid-template-columns: minmax(11rem, 1fr) minmax(6rem, 1fr); gap: 0.75rem; align-items: center; margin: 0; }
.competitor-bars span { color: #303247; font-weight: 650; }
.competitor-bars em { display: block; height: 0.5rem; border-radius: 999px; background: #eceaf6; position: relative; overflow: hidden; }
.competitor-bars em::before { content: ""; position: absolute; inset: 0 auto 0 0; width: var(--bar); border-radius: inherit; background: linear-gradient(90deg, #8f7cff, #b7a6ff); }
.card-footer { margin-top: 1rem; padding-top: 0.8rem; border-top: 1px solid #edf0f6; display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; color: #686d80; font-weight: 650; font-size: 0.82rem; }

.chart { margin: 1rem 0; padding: 1rem; border: 1px solid var(--line); border-radius: 6px; background: var(--soft); }
.chart-title { font-weight: 600; margin-bottom: 0.5rem; font-size: 0.95rem; }
.chart-legend { font-size: 0.8rem; color: var(--muted); margin-top: 0.35rem; }

.verdict-strip { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.75rem 0 0.4rem; }
.verdict-strip .vc-pill { padding: 0.25rem 0.7rem; border-radius: 999px; font-size: 0.85rem; font-weight: 600; }
.verdict-strip .vc-pill.contradicts { background: #fee2e2; color: #991b1b; }
.verdict-strip .vc-pill.partial { background: #fef3c7; color: #92400e; }
.verdict-strip .vc-pill.no-evidence { background: #fef3c7; color: #92400e; }
.verdict-strip .vc-pill.supports { background: #dcfce7; color: #166534; }
.verdict-strip .vc-pill.pending { background: #f3f4f6; color: #6b7280; font-style: italic; }
.verdict-strip-caption { font-size: 0.85rem; color: var(--muted); margin: 0.1rem 0; }
.verdict-strip-legend { font-size: 0.8rem; color: var(--muted); margin: 0.1rem 0 0.75rem; }

.method-badge { display: inline-block; padding: 0.1rem 0.55rem; border-radius: 4px; font-size: 0.78rem; font-weight: 600; white-space: nowrap; }
.method-badge.persona-reaction { border: 1px solid #9ca3af; color: #4b5563; background: transparent; font-style: italic; }
.method-badge.cross-artifact { background: #2563eb; color: #fff; }
.method-badge.external { background: #16a34a; color: #fff; }
.method-badge.unknown { background: #d1d5db; color: #374151; }

.verdict-badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 4px; font-size: 0.78rem; font-weight: 600; white-space: nowrap; }
.verdict-badge.contradicts { background: #dc2626; color: #fff; }
.verdict-badge.partial { background: #f59e0b; color: #fff; }
.verdict-badge.no-evidence { background: #f59e0b; color: #fff; }
.verdict-badge.supports { background: #16a34a; color: #fff; }
.verdict-badge.pending { background: #f3f4f6; color: #6b7280; font-style: italic; border: 1px dashed #d1d5db; }

.stance-b-caption { display: block; margin-top: 0.3rem; font-size: 0.78rem; color: #6b7280; font-style: italic; }
.pending-group-header { display: inline-block; font-style: italic; color: var(--muted); font-size: 0.9rem; margin: 0.3rem 0; }
.pending-group-row td { background: #fafafa; border-top: 1px dashed var(--line); }
.evidence-pending { color: var(--muted); font-style: italic; }
.evidence-loc { color: var(--muted); font-size: 0.85em; }

.ledger-table .claim-cell { min-width: 22ch; }
.ledger-table .evidence-cell { min-width: 26ch; max-width: 44ch; }

.contradiction-entry { margin: 0.85rem 0; padding: 0.75rem 1rem; border-left: 4px solid #dc2626; background: #fef2f2; border-radius: 4px; }
.contradiction-entry .claim-text { font-weight: 600; color: #1a1a1a; }
.contradiction-entry .file-pointer { display: block; margin-top: 0.4rem; font-size: 0.85rem; color: var(--muted); }
.contradiction-entry blockquote { margin: 0.5rem 0; border-left-color: #dc2626; }

.outreach-table td.warm-quote { font-style: italic; color: #4b5563; }
.outreach-more { display: inline-block; margin-top: 0.5rem; font-size: 0.9rem; color: var(--muted); }
.fallback-note { padding: 0.75rem 1rem; border-left: 4px solid var(--muted); background: var(--soft); border-radius: 4px; color: #4b5563; font-style: italic; }

@media (max-width: 900px) {
  .layout { grid-template-columns: minmax(0, 1fr); }
  nav.toc { position: static; max-height: none; border-right: none; border-bottom: 1px solid var(--line); padding: 1rem 1.5rem; display: none; }
  nav.toc.open { display: block; }
  .toc-toggle { display: block; margin: 0.75rem 1.5rem 0; padding: 0.4rem 0.75rem; background: var(--soft); border: 1px solid var(--line); border-radius: 4px; cursor: pointer; }
  main { padding: 1.5rem; max-width: 100%; }
  header.report { padding: 1.25rem 1.5rem; }
  pre, table { max-width: 100%; }
  .callout { margin-left: 1.5rem; margin-right: 1.5rem; }
  .dashboard-grid { grid-template-columns: 1fr; }
  .market-card { grid-column: span 1; }
  .pmf-grid, .market-grid { grid-template-columns: 1fr; }
  .competitor-bars li { grid-template-columns: 1fr; gap: 0.3rem; }
}

@media print {
  nav.toc, .toc-toggle { display: none; }
  .layout { grid-template-columns: 1fr; }
  main { max-width: none; padding: 0 1rem; }
  header.report { background: none; }
  section.report-section, details.report-section { page-break-before: always; }
  section.report-section:first-of-type, details.report-section:first-of-type { page-break-before: auto; }
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


def _section(html_id: str, title: str, body_html: str, *, star: bool = False) -> str:
    cls = "report-section star-section" if star else "report-section"
    return (
        f'<section id="{html_id}" class="{cls}">'
        f"<h2>{_esc(title)}</h2>{body_html}</section>"
    )


def _details_section(html_id: str, title: str, body_html: str) -> str:
    return (
        f'<details id="{html_id}" class="report-section drilldown" data-toc-target>'
        f"<summary>{_esc(title)}</summary>{body_html}</details>"
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


AUDIO_EXTS: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
}


def _recordings_html(deal_dir: Path) -> str:
    """Discover audio files under calls/ and inputs/ and emit <audio> tags.

    Uses relative paths — report.html ships alongside its deal directory,
    so the browser resolves calls/foo.mp3 against the deal dir.
    """
    blocks: list[str] = []
    for sub, heading in (("calls", "Screener calls"), ("inputs", "Interview recordings")):
        sub_dir = deal_dir / sub
        if not sub_dir.is_dir():
            continue
        files = sorted(
            p for p in sub_dir.iterdir()
            if p.is_file() and p.suffix.lower() in AUDIO_EXTS
        )
        if not files:
            continue
        items: list[str] = []
        for f in files:
            mime = AUDIO_EXTS[f.suffix.lower()]
            label = f.stem.replace("_", " ").replace("-", " ").strip()
            rel = f"{sub}/{f.name}"
            items.append(
                f'<li>'
                f'<div class="recording-label">{_esc(label)}</div>'
                f'<audio controls preload="none" src="{_esc(rel)}" type="{mime}">'
                f'Your browser does not support audio playback. '
                f'<a href="{_esc(rel)}">Download {_esc(f.name)}</a>'
                f'</audio>'
                f'</li>'
            )
        blocks.append(
            f'<div class="recordings-block">'
            f'<h3>{_esc(heading)}</h3>'
            f'<ul class="recordings-list">{"".join(items)}</ul>'
            f'</div>'
        )
    return "".join(blocks)


def _persona_title(name: str) -> str:
    base = name.removesuffix(".md")
    if base == "_context":
        return "Problem-space context"
    base = base.replace("-", " ")
    return base[:1].upper() + base[1:]


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


def _build_header_html(
    deal_dir: Path,
    manifest: dict,
    memo: str | None,
) -> tuple[str, str, dict, str | None, str | None]:
    """Return (header_html, callout_html, manifest_view, slug, company)."""
    company = manifest.get("company") or manifest.get("slug", "Untitled deal")
    slug = manifest.get("slug", deal_dir.name)
    skills = manifest.get("skills_completed", {}) or {}
    pitch_note = manifest.get("pitch_reframe_note")

    generated = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pill_label = "Diligence report" if memo else "Diligence in progress"
    pill_class = "unknown"

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
    )
    return header_html, callout, manifest, slug, company


def _build_html_skeleton(
    title: str,
    header_html: str,
    pre_main_html: str,
    main_body_html: str,
    toc_html: str,
) -> str:
    toggle_html = '<button class="toc-toggle" type="button">Contents</button>'
    return (
        "<!doctype html>\n"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_esc(title)}</title>"
        f"<style>{CSS}</style>"
        "</head><body>"
        + header_html
        + pre_main_html
        + toggle_html
        + '<div class="layout">'
        + toc_html
        + "<main>"
        + main_body_html
        + "</main></div>"
        + f"<script>{JS}</script>"
        "</body></html>\n"
    )


def _build_toc(toc: list[tuple[str, str]], persona_toc: list[tuple[str, str]]) -> str:
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
    return (
        '<nav class="toc" aria-label="Table of contents">'
        '<h2>Contents</h2>'
        f'<ul>{"".join(toc_items)}</ul>'
        "</nav>"
    )


def _personas_block(deal_dir: Path, *, all_closed: bool) -> tuple[str, list[tuple[str, str]]]:
    """Return (group-html, persona_toc). all_closed=True forces every
    individual persona <details> closed (used in the pmf-led layout).
    Empty string if no personas exist.
    """
    personas_dir = deal_dir / "personas"
    if not personas_dir.is_dir():
        return "", []
    files = sorted(personas_dir.glob("*.md"), key=_persona_sort_key)
    blocks: list[str] = []
    persona_toc: list[tuple[str, str]] = []
    for fpath in files:
        body = _read(fpath) or ""
        body = re.sub(r"^#\s+.+\n", "", body, count=1)
        stem = fpath.stem
        title = _persona_title(fpath.name)
        html_id = "persona-" + _slug(stem)
        persona_toc.append((html_id, title))
        if all_closed:
            open_attr = ""
        else:
            open_attr = " open" if stem == "_context" else ""
        blocks.append(
            f'<details id="{html_id}" data-toc-target{open_attr}>'
            f"<summary>{_esc(title)}</summary>"
            f"{render_markdown(body, heading_offset=2)}"
            "</details>"
        )
    if not blocks:
        return "", []
    return "\n".join(blocks), persona_toc


def _source_artifacts_html(
    deal_dir: Path,
    founder_files: list[Path],
    *,
    pmf_inputs: PMFInputs | None = None,
) -> str:
    """Build the source-artifacts list section body."""
    artifacts: list[str] = []
    candidates = [
        "MEMO.md",
        "manifest.json",
        "background.md",
        "market-context.md",
        "market-problem.md",
        "competitive-landscape.md",
        "market-sizing.md",
        "pmf-signal.md",
        "outreach.md",
        "pitch.yaml",
        "customer-discovery-prep.md",
        "customer-discovery.md",
    ]
    for name in candidates:
        if (deal_dir / name).exists():
            artifacts.append(f'<li><a href="{_esc(name)}">{_esc(name)}</a></li>')
    # personas/verdicts.yaml + personas/aggregates.yaml (new in pmf-led layout)
    for sub in ("personas/verdicts.yaml", "personas/aggregates.yaml"):
        p = deal_dir / sub
        if p.exists():
            artifacts.append(f'<li><a href="{_esc(sub)}">{_esc(sub)}</a></li>')
    for fpath in founder_files:
        artifacts.append(f'<li><a href="{_esc(fpath.name)}">{_esc(fpath.name)}</a></li>')
    personas_dir = deal_dir / "personas"
    if personas_dir.is_dir():
        for fpath in sorted(personas_dir.glob("*.md"), key=_persona_sort_key):
            rel = f"personas/{fpath.name}"
            artifacts.append(f'<li><a href="{_esc(rel)}">{_esc(rel)}</a></li>')
    if not artifacts:
        return ""
    return "<ul>" + "".join(artifacts) + "</ul>"


def _founder_background_specs(founder_files: list[Path]) -> list[tuple[str, str, str]]:
    """Return expanded founder dossier sections for the front of the report."""
    specs: list[tuple[str, str, str]] = []
    for fpath in founder_files:
        body = _read(fpath) or ""
        body = re.sub(r"^#\s+.+\n", "", body, count=1)
        html_id = "founder-" + _slug(fpath.stem.removeprefix("founder-"))
        label = "Founder Background: " + fpath.stem.removeprefix("founder-").replace("-", " ").title()
        body_html = render_markdown(body, heading_offset=1)
        if body_html.strip():
            specs.append((html_id, label, body_html))
    return specs


def _plain_text(md: str | None) -> str:
    if not md:
        return ""
    text = re.sub(r"```.*?```", " ", md, flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`>#|]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _sentence_snippet(md: str | None, fallback: str, *, max_len: int = 130) -> str:
    text = _plain_text(md)
    if not text:
        return fallback
    parts = re.split(r"(?<=[.!?])\s+", text)
    snippet = next((p for p in parts if len(p) > 24), parts[0] if parts else fallback)
    if len(snippet) > max_len:
        snippet = snippet[: max_len - 1].rstrip() + "..."
    return snippet


def _extract_first_range(md: str | None, label: str) -> str | None:
    if not md:
        return None
    pat = rf"\*\*{re.escape(label)}:\*\*\s*([^\n]+)"
    m = re.search(pat, md, re.IGNORECASE)
    if m:
        return _plain_text(m.group(1))
    heading = rf"##\s+{re.escape(label)}\s*\n+\s*([^\n]+)"
    m = re.search(heading, md, re.IGNORECASE)
    if m:
        return _plain_text(m.group(1))
    return None


def _top_competitors(md: str | None, limit: int = 3) -> list[str]:
    if not md:
        return []
    out: list[str] = []
    for line in md.splitlines():
        if not line.strip().startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in ("competitor", "source"):
            continue
        name = _plain_text(cells[0])
        if name and name not in out:
            out.append(name)
        if len(out) >= limit:
            break
    return out


def _status_badge(label: str, tone: str = "neutral") -> str:
    return f'<span class="dashboard-badge {tone}">{_esc(label)}</span>'


def _dashboard_metric(label: str, value: str) -> str:
    return (
        '<div class="dashboard-metric">'
        f'<span>{_esc(label)}</span><strong>{_esc(value)}</strong>'
        "</div>"
    )


def _founder_dashboard_card(manifest: dict, founder_files: list[Path]) -> str:
    founders = manifest.get("founders") or []
    file_text = "\n".join(_read(p) or "" for p in founder_files)
    checks = [
        ("Public profile", bool(file_text.strip())),
        ("Experience mapped", "experience" in file_text.lower() or "background" in file_text.lower()),
        ("Track record", "track record" in file_text.lower() or "prior" in file_text.lower()),
        ("Open questions", "open questions" in file_text.lower()),
    ]
    founder_chips = []
    for idx, name in enumerate(founders[:3]):
        initials = "".join(part[:1] for part in str(name).split()[:2]).upper() or "?"
        founder_chips.append(
            '<div class="founder-chip">'
            f'<span class="avatar avatar-{idx % 3}">{_esc(initials)}</span>'
            f'<span>{_esc(str(name))}</span>'
            "</div>"
        )
    check_items = "".join(
        f'<li class="{ "ok" if ok else "pending" }"><span></span>{_esc(label)}</li>'
        for label, ok in checks
    )
    return (
        '<article class="dashboard-card founders-card">'
        '<div class="card-title"><span class="step">1</span><h3>Founders\' Background Check</h3></div>'
        f'<div class="founder-chips">{"".join(founder_chips)}</div>'
        f'<ul class="check-list">{check_items}</ul>'
        '<div class="card-footer">'
        '<span>Evidence status</span>'
        f'{_status_badge("Public dossier built" if founder_files else "Pending", "positive" if founder_files else "neutral")}'
        '</div></article>'
    )


def _pmf_dashboard_card(inputs: PMFInputs, rows: list[dict]) -> str:
    verdicts = inputs.verdicts or {}
    patterns = verdicts.get("cluster_patterns") or []
    persona_rows = [
        v for v in (verdicts.get("claim_verdicts") or verdicts.get("verdicts") or [])
        if _normalize_method(v.get("method") or v.get("verification_method")) == "persona-reaction"
    ]
    score_values: list[float] = []
    for row in persona_rows:
        agree = int(row.get("agree") or 0)
        partial = int(row.get("partial") or 0)
        disagree = int(row.get("disagree") or 0)
        total = agree + partial + disagree
        if total:
            score_values.append((agree + 0.5 * partial) / total * 10)
    score = sum(score_values) / len(score_values) if score_values else None
    score_text = f"{score:.1f}/10" if score is not None else "pending"
    if score is None:
        consensus = ("Awaiting signal", "neutral")
    elif score >= 7.5:
        consensus = ("Strong prior", "positive")
    elif score >= 5.5:
        consensus = ("Mixed prior", "warning")
    else:
        consensus = ("Weak prior", "negative")
    pain_points = patterns[:3] or [
        "Buyer urgency not yet validated by customer interviews.",
        "Claims need triangulation against external evidence.",
        "Data-room checks remain open.",
    ]
    pain_html = "".join(f"<li>{_inline(_esc(_plain_text(p)))}</li>" for p in pain_points)
    sample = str(verdicts.get("sample_size") or len(rows) or "pending")
    return (
        '<article class="dashboard-card pmf-card">'
        '<div class="card-title"><span class="step">2</span><h3>PMF Persona</h3></div>'
        '<div class="persona-tabs"><span class="active">Persona 1</span><span>Persona 2</span><span>Persona 3</span></div>'
        '<div class="pmf-grid">'
        f'<div><h4>Top Pain Points</h4><ul class="pain-list">{pain_html}</ul></div>'
        f'<div class="score-box"><span>Fit Score</span><strong>{_esc(score_text)}</strong><small>synthetic prior</small></div>'
        '</div>'
        '<div class="card-footer">'
        f'<span>Sample size: {_esc(sample)}</span>'
        f'{_status_badge(consensus[0], consensus[1])}'
        '</div></article>'
    )


def _calls_dashboard_card(deal_dir: Path) -> str:
    calls_dir = deal_dir / "calls"
    inputs_dir = deal_dir / "inputs"
    call_json = sorted(calls_dir.glob("*.json")) if calls_dir.is_dir() else []
    transcripts: list[Path] = []
    if inputs_dir.is_dir():
        transcripts = [
            p for p in inputs_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".md", ".txt", ".vtt")
            and not p.name.startswith("deck.")
        ]
    completed = len(call_json) + len(transcripts)
    customer_md = _read(deal_dir / "customer-discovery.md")
    quote = _sentence_snippet(
        customer_md,
        "No real interviews recorded yet; use the outreach list to validate buyer urgency.",
        max_len=115,
    )
    tone = "positive" if completed else "neutral"
    signal = "Available" if completed else "Pending"
    return (
        '<article class="dashboard-card calls-card">'
        '<div class="card-title"><span class="step">3</span><h3>Real Call Insights</h3></div>'
        '<div class="audio-wave" aria-hidden="true"><span class="play-dot">▶</span><span></span><span></span><span></span><span></span><span></span></div>'
        '<div class="call-metrics">'
        f'{_dashboard_metric("Calls / transcripts", str(completed))}'
        f'{_dashboard_metric("Customer signal", signal)}'
        '</div>'
        f'<blockquote>{_inline(_esc(quote))}</blockquote>'
        '<div class="card-footer">'
        '<span>Interview evidence</span>'
        f'{_status_badge("Recorded" if completed else "Pending", tone)}'
        '</div></article>'
    )


def _stage_dashboard_card(manifest: dict, inputs: PMFInputs) -> str:
    pitch = inputs.pitch or {}
    category = (pitch.get("product") or {}).get("category") or manifest.get("pitch") or "Category not specified"
    claim_count = len(pitch.get("claims") or [])
    skills = manifest.get("skills_completed", {}) or {}
    completed = sum(1 for v in skills.values() if v)
    total = max(1, len(skills))
    stage = "Regulatory pre-launch" if "regulated" in str(category).lower() else "Early diligence"
    dots = "".join(
        f'<span class="{ "active" if i == 0 else "" }"></span>'
        for i in range(4)
    )
    return (
        '<article class="dashboard-card stage-card">'
        '<div class="card-title"><span class="step">4</span><h3>Stage of Startup</h3></div>'
        f'<div class="stage-line">{dots}</div>'
        '<div class="stage-labels"><span>Pre-Revenue</span><span>Pre-Seed</span><span>Seed</span><span>Series A+</span></div>'
        '<div class="insight-box">'
        '<span class="bulb">i</span>'
        f'<p>{_esc(stage)} company. Diligence artifacts complete: {completed}/{total}. Claim ledger contains {claim_count} claims.</p>'
        '</div></article>'
    )


def _market_dashboard_card(deal_dir: Path, inputs: PMFInputs) -> str:
    ms = _read(deal_dir / "market-sizing.md")
    cl = _read(deal_dir / "competitive-landscape.md")
    pitch = inputs.pitch or {}
    industry = (pitch.get("product") or {}).get("category") or "Not specified"
    wedge = _extract_first_range(ms, "Wedge TAM") or "Not quantified"
    expansion = _extract_first_range(ms, "Total addressable (wedge + expansion)") or _extract_first_range(ms, "Wedge TAM") or "Not quantified"
    competitors = _top_competitors(cl)
    bars = [88, 62, 48]
    comp_rows = "".join(
        f'<li><span>{idx + 1}. {_esc(name)}</span><em style="--bar:{bars[idx]}%"></em></li>'
        for idx, name in enumerate(competitors[:3])
    )
    if not comp_rows:
        comp_rows = '<li><span>No direct competitors parsed</span><em style="--bar:20%"></em></li>'
    return (
        '<article class="dashboard-card market-card">'
        '<div class="card-title"><span class="step">5</span><h3>Market Check & Industry</h3></div>'
        '<div class="market-grid">'
        '<div>'
        f'<span class="mini-label">Industry</span><strong>{_esc(str(industry))}</strong>'
        f'<span class="mini-label">Wedge TAM</span><strong class="green">{_esc(wedge)}</strong>'
        f'<span class="mini-label">Expansion pool</span><strong class="green">{_esc(expansion)}</strong>'
        '</div>'
        f'<div><span class="mini-label">Top Competitors</span><ol class="competitor-bars">{comp_rows}</ol></div>'
        '</div>'
        '<div class="card-footer">'
        '<span>Market evidence</span>'
        f'{_status_badge("Large, validation-dependent", "warning")}'
        '</div></article>'
    )


def _dashboard_html(
    deal_dir: Path,
    manifest: dict,
    inputs: PMFInputs,
    rows: list[dict],
    founder_files: list[Path],
) -> str:
    company = manifest.get("company") or manifest.get("slug", deal_dir.name)
    return (
        '<section id="dashboard" class="dashboard-shell report-section">'
        f'<h2>Final Output: AI Due Diligence Report</h2>'
        f'<p class="dashboard-subtitle">{_esc(company)} evidence dashboard</p>'
        '<div class="dashboard-grid">'
        f'{_founder_dashboard_card(manifest, founder_files)}'
        f'{_pmf_dashboard_card(inputs, rows)}'
        f'{_calls_dashboard_card(deal_dir)}'
        f'{_stage_dashboard_card(manifest, inputs)}'
        f'{_market_dashboard_card(deal_dir, inputs)}'
        '</div></section>'
    )


# ---------- legacy branch -------------------------------------------------


def render_legacy(deal_dir: Path) -> str:
    """Render the per-deal HTML in the prior artifact-by-artifact layout.

    Used when none of pitch.yaml / verdicts.yaml / pmf-signal.md exist.
    Preserves today's behavior byte-for-byte (modulo the small bookkeeping
    changes shared across both branches: source-artifacts list).
    """
    manifest_path = deal_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"{manifest_path} not found")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{manifest_path} invalid JSON: {e}") from e

    memo = _read(deal_dir / "MEMO.md")
    memo_sections = _split_memo_sections(memo) if memo else {}

    header_html, callout, _, _, company = _build_header_html(deal_dir, manifest, memo)

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

    founder_files = sorted(deal_dir.glob("founder-*.md"))
    if founder_files:
        for html_id, label, body_html in _founder_background_specs(founder_files):
            add_section(html_id, label, body_html)
    elif "founders" in memo_sections:
        add_section("founders", "Founder Background", render_markdown(memo_sections["founders"], heading_offset=OFFSET))

    mp = _read(deal_dir / "market-context.md") or _read(deal_dir / "market-problem.md")
    if mp:
        body = re.sub(r"^#\s+.+\n", "", mp, count=1)
        sections_html.append(
            _details_section("problem", "Problem & Product", render_markdown(body, heading_offset=OFFSET))
        )
        toc.append(("problem", "Problem & Product"))
    elif "problem and product" in memo_sections:
        sections_html.append(
            _details_section("problem", "Problem & Product", render_markdown(memo_sections["problem and product"], heading_offset=OFFSET))
        )
        toc.append(("problem", "Problem & Product"))

    cd = _read(deal_dir / "customer-discovery.md")
    recordings = _recordings_html(deal_dir)
    if cd:
        body = re.sub(r"^#\s+.+\n", "", cd, count=1)
        sections_html.append(
            _details_section("customer-signal", "Customer Signal", recordings + render_markdown(body, heading_offset=OFFSET))
        )
        toc.append(("customer-signal", "Customer Signal"))
    elif "customer signal" in memo_sections:
        sections_html.append(
            _details_section("customer-signal", "Customer Signal", recordings + render_markdown(memo_sections["customer signal"], heading_offset=OFFSET))
        )
        toc.append(("customer-signal", "Customer Signal"))
    elif recordings:
        sections_html.append(_details_section("customer-signal", "Customer Signal", recordings))
        toc.append(("customer-signal", "Customer Signal"))

    if not cd:
        cdp = _read(deal_dir / "customer-discovery-prep.md")
        if cdp:
            body = re.sub(r"^#\s+.+\n", "", cdp, count=1)
            sections_html.append(
                _details_section("customer-discovery-prep", "Discovery Prep", render_markdown(body, heading_offset=OFFSET))
            )
            toc.append(("customer-discovery-prep", "Discovery Prep"))

    cl = _read(deal_dir / "competitive-landscape.md")
    if cl:
        body = re.sub(r"^#\s+.+\n", "", cl, count=1)
        sections_html.append(
            _details_section("competitive-landscape", "Competitive Landscape", render_markdown(body, heading_offset=OFFSET))
        )
        toc.append(("competitive-landscape", "Competitive Landscape"))
    elif "competitive landscape" in memo_sections:
        sections_html.append(
            _details_section("competitive-landscape", "Competitive Landscape", render_markdown(memo_sections["competitive landscape"], heading_offset=OFFSET))
        )
        toc.append(("competitive-landscape", "Competitive Landscape"))

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
        sections_html.append(
            _details_section("market-sizing", "Market Sizing", chart + render_markdown(body, heading_offset=OFFSET))
        )
        toc.append(("market-sizing", "Market Sizing"))
    elif "market sizing" in memo_sections:
        sections_html.append(
            _details_section("market-sizing", "Market Sizing", render_markdown(memo_sections["market sizing"], heading_offset=OFFSET))
        )
        toc.append(("market-sizing", "Market Sizing"))

    if "cross-artifact synthesis" in memo_sections:
        sections_html.append(
            _details_section("synthesis", "Cross-artifact Synthesis", render_markdown(memo_sections["cross-artifact synthesis"], heading_offset=OFFSET))
        )
        toc.append(("synthesis", "Cross-artifact Synthesis"))

    persona_html, persona_toc = _personas_block(deal_dir, all_closed=False)
    if persona_html:
        sections_html.append(_details_section("personas", "Personas", persona_html))
        toc.append(("personas", "Personas"))

    artifacts_body = _source_artifacts_html(deal_dir, founder_files)
    if artifacts_body:
        sections_html.append(_details_section("artifacts", "Source artifacts", artifacts_body))
        toc.append(("artifacts", "Source artifacts"))

    toc_html = _build_toc(toc, persona_toc)
    title = f"{company} — diligence report"
    return _build_html_skeleton(
        title=title,
        header_html=header_html,
        pre_main_html=callout,
        main_body_html="\n".join(sections_html),
        toc_html=toc_html,
    )


# ---------- pmf-led branch ------------------------------------------------


def _drilldown_section_specs(
    deal_dir: Path,
    memo_sections: dict[str, str],
    founder_files: list[Path],
) -> list[tuple[str, str, str]]:
    """Return (id, label, body_html) tuples for the pmf-led drill-down sections.

    Excludes MEMO sections that duplicate visible or per-artifact files
    (Founder Background, Problem and Product, Customer Signal, Competitive
    Landscape, Market Sizing). Includes per-artifact files plus the
    cross-artifact synthesis from MEMO at the end.
    """
    OFFSET = 2  # rendered inside <details><summary><h2-equivalent>
    out: list[tuple[str, str, str]] = []

    mp = _read(deal_dir / "market-context.md") or _read(deal_dir / "market-problem.md")
    if mp:
        body = re.sub(r"^#\s+.+\n", "", mp, count=1)
        out.append(("problem", "Problem & Product", render_markdown(body, heading_offset=OFFSET)))

    cd = _read(deal_dir / "customer-discovery.md")
    recordings = _recordings_html(deal_dir)
    if cd:
        body = re.sub(r"^#\s+.+\n", "", cd, count=1)
        out.append(("customer-signal", "Customer Signal", recordings + render_markdown(body, heading_offset=OFFSET)))
    elif recordings:
        out.append(("customer-signal", "Customer Signal", recordings))
    else:
        cdp = _read(deal_dir / "customer-discovery-prep.md")
        if cdp:
            body = re.sub(r"^#\s+.+\n", "", cdp, count=1)
            out.append(("customer-discovery-prep", "Discovery Prep", render_markdown(body, heading_offset=OFFSET)))

    cl = _read(deal_dir / "competitive-landscape.md")
    if cl:
        body = re.sub(r"^#\s+.+\n", "", cl, count=1)
        out.append(("competitive-landscape", "Competitive Landscape", render_markdown(body, heading_offset=OFFSET)))

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
        out.append(("market-sizing", "Market Sizing", chart + render_markdown(body, heading_offset=OFFSET)))

    if "cross-artifact synthesis" in memo_sections:
        out.append(
            (
                "synthesis",
                "Cross-artifact Synthesis",
                render_markdown(memo_sections["cross-artifact synthesis"], heading_offset=OFFSET),
            )
        )

    return out


def _wrap_details(html_id: str, label: str, body_html: str) -> str:
    return (
        f'<details id="{html_id}" class="drilldown" data-toc-target>'
        f"<summary>{_esc(label)}</summary>"
        f"{body_html}"
        "</details>"
    )


def _star_section(html_id: str, label: str, body_html: str) -> str:
    return _section(html_id, label, body_html, star=True)


def render_pmf_led(deal_dir: Path, inputs: PMFInputs, *, branch: str = "full") -> str:
    """Render the new star-led layout for the full or pitch-only branches.

    branch="full"        — verdicts.yaml present, render contradictions normally
    branch="pitch-only"  — verdicts.yaml missing, all rows pending; replace
                           contradictions section with a "PMF run incomplete" note
    """
    manifest_path = deal_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"{manifest_path} not found")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{manifest_path} invalid JSON: {e}") from e

    memo = _read(deal_dir / "MEMO.md")
    memo_sections = _split_memo_sections(memo) if memo else {}
    header_html, callout, _, _, company = _build_header_html(deal_dir, manifest, memo)

    rows = sort_ledger_rows(
        inputs.pitch,
        inputs.verdicts,
        force_pending=(branch == "pitch-only"),
    )

    sections_html: list[str] = []
    toc: list[tuple[str, str]] = []

    # First visible section: founder background dossiers, including the
    # Prior managers / partners table from founder-check when available.
    founder_files = sorted(deal_dir.glob("founder-*.md"))
    sections_html.append(_dashboard_html(deal_dir, manifest, inputs, rows, founder_files))
    toc.append(("dashboard", "Dashboard"))

    for html_id, label, body_html in _founder_background_specs(founder_files):
        sections_html.append(_section(html_id, label, body_html))
        toc.append((html_id, label))

    # Second visible part: PMF signal.
    ledger_html = render_ledger_section(rows)
    if ledger_html:
        sections_html.append(_star_section("ledger", "PMF Signal", ledger_html))
        toc.append(("ledger", "PMF signal"))

    if branch == "pitch-only":
        sections_html.append(
            _star_section(
                "contradictions",
                "Cross-artifact contradictions",
                '<p class="fallback-note">'
                "PMF run incomplete — verdicts not yet generated."
                "</p>",
            )
        )
        toc.append(("contradictions", "Contradictions"))
    else:
        contradictions_html = render_contradictions_section(rows)
        if contradictions_html:
            sections_html.append(
                _star_section("contradictions", "Cross-artifact contradictions", contradictions_html)
            )
            toc.append(("contradictions", "Contradictions"))

    outreach_entries = parse_outreach(inputs.outreach_md)
    outreach_html = render_outreach_section(outreach_entries)
    if outreach_html:
        sections_html.append(_star_section("outreach", "Warm-path outreach top-N", outreach_html))
        toc.append(("outreach", "Outreach"))

    # Drill-down sections (collapsed)
    drilldowns = _drilldown_section_specs(deal_dir, memo_sections, founder_files)
    if drilldowns:
        drill_blocks: list[str] = []
        for html_id, label, body_html in drilldowns:
            drill_blocks.append(_wrap_details(html_id, label, body_html))
            toc.append((html_id, label))
        sections_html.append(
            f'<section id="drilldown" class="report-section">'
            f"<h2>Drill-down</h2>{''.join(drill_blocks)}</section>"
        )

    # Personas drill-down (collapsed)
    persona_html, persona_toc = _personas_block(deal_dir, all_closed=True)
    if persona_html:
        # Wrap the entire personas group as a single drill-down details
        sections_html.append(
            f'<section id="personas" class="report-section">'
            f'<h2>Personas</h2>{persona_html}</section>'
        )
        toc.append(("personas", "Personas"))

    # Source artifacts
    artifacts_body = _source_artifacts_html(deal_dir, founder_files, pmf_inputs=inputs)
    if artifacts_body:
        sections_html.append(_details_section("artifacts", "Source artifacts", artifacts_body))
        toc.append(("artifacts", "Source artifacts"))

    toc_html = _build_toc(toc, persona_toc)
    pre_main = callout
    title = f"{company} — diligence report"
    return _build_html_skeleton(
        title=title,
        header_html=header_html,
        pre_main_html=pre_main,
        main_body_html="\n".join(sections_html),
        toc_html=toc_html,
    )


def render_pitch_only(deal_dir: Path, inputs: PMFInputs) -> str:
    return render_pmf_led(deal_dir, inputs, branch="pitch-only")


def render_markdown_fallback(deal_dir: Path, inputs: PMFInputs) -> str:
    """Render pmf-signal.md as a single section in place of the three star sections."""
    manifest_path = deal_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"{manifest_path} not found")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{manifest_path} invalid JSON: {e}") from e

    memo = _read(deal_dir / "MEMO.md")
    memo_sections = _split_memo_sections(memo) if memo else {}
    header_html, callout, _, _, company = _build_header_html(deal_dir, manifest, memo)

    sections_html: list[str] = []
    toc: list[tuple[str, str]] = []

    founder_files = sorted(deal_dir.glob("founder-*.md"))
    for html_id, label, body_html in _founder_background_specs(founder_files):
        sections_html.append(_section(html_id, label, body_html))
        toc.append((html_id, label))

    pmf_md = inputs.pmf_signal_md or ""
    body = re.sub(r"^#\s+.+\n", "", pmf_md, count=1)
    pmf_signal_body = render_markdown(body, heading_offset=1)
    if pmf_signal_body.strip():
        sections_html.append(_star_section("pmf-signal", "PMF signal", pmf_signal_body))
        toc.append(("pmf-signal", "PMF signal"))

    drilldowns = _drilldown_section_specs(deal_dir, memo_sections, founder_files)
    if drilldowns:
        drill_blocks: list[str] = []
        for html_id, label, body_html in drilldowns:
            drill_blocks.append(_wrap_details(html_id, label, body_html))
            toc.append((html_id, label))
        sections_html.append(
            f'<section id="drilldown" class="report-section">'
            f"<h2>Drill-down</h2>{''.join(drill_blocks)}</section>"
        )

    persona_html, persona_toc = _personas_block(deal_dir, all_closed=True)
    if persona_html:
        sections_html.append(
            f'<section id="personas" class="report-section"><h2>Personas</h2>{persona_html}</section>'
        )
        toc.append(("personas", "Personas"))

    artifacts_body = _source_artifacts_html(deal_dir, founder_files, pmf_inputs=inputs)
    if artifacts_body:
        sections_html.append(_details_section("artifacts", "Source artifacts", artifacts_body))
        toc.append(("artifacts", "Source artifacts"))

    toc_html = _build_toc(toc, persona_toc)
    pre_main = callout
    title = f"{company} — diligence report"
    return _build_html_skeleton(
        title=title,
        header_html=header_html,
        pre_main_html=pre_main,
        main_body_html="\n".join(sections_html),
        toc_html=toc_html,
    )


# ---------- top-level dispatcher ------------------------------------------


def render_report(deal_dir: Path) -> str:
    """Top-level entry point: detect input shape and dispatch."""
    inputs = load_pmf_inputs(deal_dir)
    branch = detect_branch(inputs, deal_dir)
    if branch == "full":
        return render_pmf_led(deal_dir, inputs, branch="full")
    if branch == "pitch-only":
        return render_pitch_only(deal_dir, inputs)
    if branch == "markdown-fallback":
        return render_markdown_fallback(deal_dir, inputs)
    return render_legacy(deal_dir)


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
