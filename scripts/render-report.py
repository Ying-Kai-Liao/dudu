#!/usr/bin/env python3
"""Render a self-contained report.html for a dudu deal directory.

This renderer has four input-shape branches, selected automatically based
on which pmf-signal artifacts exist in the deal directory. They are tried
in priority order; the first matching branch wins:

  1. full              — pitch.yaml AND personas/verdicts.yaml both present.
                         Renders the star-led layout: header → recommendation
                         ribbon → claim ledger × verdict matrix →
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
    verdicts_list = (verdicts or {}).get("verdicts") or []
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


# ---------- recommendation ribbon ----------------------------------------


def render_recommendation_ribbon(memo_text: str | None) -> str:
    """Extract `## Recommendation` (case-insensitive) from MEMO.md and
    render as a callout ribbon. Returns "" if MEMO is missing or has no
    such section.
    """
    if not memo_text:
        return ""
    sections = _split_memo_sections(memo_text)
    body = sections.get("recommendation")
    if not body:
        return ""
    inner = render_markdown(body, heading_offset=1)
    if not inner.strip():
        return ""
    return (
        '<aside class="recommendation-ribbon">'
        "<h3>Recommendation</h3>"
        f"{inner}"
        "</aside>"
    )


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

.recommendation-ribbon { margin: 1rem 2rem 0; padding: 0.85rem 1.1rem; border-left: 4px solid var(--accent); background: #eff6ff; color: #1e3a8a; border-radius: 4px; font-size: 0.95rem; }
.recommendation-ribbon h3 { font-family: system-ui, -apple-system, sans-serif; font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; color: #1e3a8a; margin: 0 0 0.4rem; padding: 0; border: none; }
.recommendation-ribbon p { margin: 0.3rem 0; }

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
section.report-section, details.report-section { scroll-margin-top: 1rem; }
section.star-section > h2::before { content: "★ "; color: #f59e0b; font-weight: normal; }
details { margin: 0.5rem 0; border: 1px solid var(--line); border-radius: 6px; padding: 0.5rem 0.9rem; background: #fcfcfc; }
details > summary { cursor: pointer; font-weight: 600; color: var(--ink); padding: 0.15rem 0; }
details[open] { background: #fff; }
details[open] > summary { margin-bottom: 0.4rem; }

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
  .recommendation-ribbon, .callout { margin-left: 1.5rem; margin-right: 1.5rem; }
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


_VENDOR_DIR = Path(__file__).parent / "vendor"


def _load_wavesurfer_js() -> str:
    """Read vendored wavesurfer.js. Returns empty string if missing."""
    p = _VENDOR_DIR / "wavesurfer-7.8.0.min.js"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


WAVESURFER_JS = _load_wavesurfer_js()


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


DASHBOARD_JS = """
(function () {
  if (typeof WaveSurfer === 'undefined') return;
  document.querySelectorAll('.dash-waveform[data-audio]').forEach(function (el) {
    var audio = el.getAttribute('data-audio');
    if (!audio) return;
    var ws = WaveSurfer.create({
      container: el,
      url: audio,
      waveColor: '#cbd5f5',
      progressColor: '#7c5cff',
      cursorColor: '#1e3a8a',
      height: 56,
      barWidth: 2,
      barGap: 1,
      barRadius: 1,
      normalize: true,
      backend: 'WebAudio',
      mediaControls: false
    });
    var sibling = el.parentElement.querySelector('audio.dash-audio');
    if (sibling) {
      sibling.addEventListener('play', function () { ws.play(); });
      sibling.addEventListener('pause', function () { ws.pause(); });
      ws.on('interaction', function () { sibling.currentTime = ws.getCurrentTime(); });
    }
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


def _ensure_local_recording(deal_dir: Path, call_json_path: Path) -> Path | None:
    """Download recording_url from a call JSON to calls/recordings/<id>.wav.

    Returns the local path on success, None on any failure.
    Idempotent: if the local file already exists with non-zero size, returns it.
    """
    try:
        data = json.loads(call_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    url = data.get("recording_url")
    if not url:
        return None

    call_id = call_json_path.stem  # e.g. "demo-billing-reconciliation"
    target_dir = deal_dir / "calls" / "recordings"
    target = target_dir / f"{call_id}.wav"
    if target.exists() and target.stat().st_size > 0:
        return target

    target_dir.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".wav.tmp")
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=30) as resp:
            data_bytes = resp.read()
        if not data_bytes:
            return None
        tmp.write_bytes(data_bytes)
        tmp.replace(target)
        return target
    except Exception as exc:  # noqa: BLE001 — network/disk failure shouldn't crash render
        print(f"warning: could not download recording for {call_id}: {exc}", file=sys.stderr)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return None


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
    rec = parse_recommendation(memo) if memo else None

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
        + ("<script>" + WAVESURFER_JS + "</script>"
           if 'class="dash-card dash-card-calls"' in main_body_html or
              'class="dash-card dash-card-calls"' in pre_main_html
           else "")
        + f"<script>{JS}</script>"
        + ("<script>" + DASHBOARD_JS + "</script>"
           if 'class="dash-card dash-card-calls"' in main_body_html or
              'class="dash-card dash-card-calls"' in pre_main_html
           else "")
        + "</body></html>\n"
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


# ---------- dashboard cards ----------------------------------------------


_FOUNDER_AVATAR_PALETTE = ["#7c5cff", "#16a34a", "#f59e0b", "#06b6d4", "#dc2626", "#64748b"]


def _founder_initials(name: str) -> str:
    parts = [p for p in re.split(r"[\s\-]+", name.strip()) if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _founder_avatar_color(name: str) -> str:
    h = sum(ord(c) for c in name) if name else 0
    return _FOUNDER_AVATAR_PALETTE[h % len(_FOUNDER_AVATAR_PALETTE)]


def _founder_risk_count(body: str) -> int:
    """Count bullet items under Risks/Open questions/Controversies headings."""
    count = 0
    in_risk_section = False
    for line in body.split("\n"):
        h = re.match(r"^##\s+(.*)$", line)
        if h:
            title = h.group(1).strip().lower()
            in_risk_section = title in ("risks", "open questions", "controversies", "concerns")
            continue
        if in_risk_section and re.match(r"^\s*[-*]\s+\S", line):
            count += 1
    return count


def _card_founders(deal_dir: Path) -> str | None:
    files = sorted(deal_dir.glob("founder-*.md"))
    if not files:
        return None

    rows: list[str] = []
    total_risks = 0
    for fpath in files:
        body = _read(fpath) or ""
        name = fpath.stem.removeprefix("founder-").replace("-", " ").title()
        slug = _slug(fpath.stem.removeprefix("founder-"))
        anchor = f"founder-{slug}"

        has_linkedin = "linkedin.com/in/" in body.lower()
        has_experience = bool(re.search(r"^##\s+(experience|background|career)\b", body, re.M | re.I))
        has_track = bool(re.search(r"^##\s+(prior ventures|prior partner contacts|track record)\b", body, re.M | re.I))
        has_connections = bool(re.search(r"^##\s+(network|references|prior partner contacts)\b", body, re.M | re.I))
        total_risks += _founder_risk_count(body)

        badges = []
        for ok, key, label in (
            (has_linkedin, "linkedin", "LinkedIn"),
            (has_experience, "experience", "Experience"),
            (has_track, "track-record", "Track Record"),
            (has_connections, "connections", "Connections"),
        ):
            cls = "dash-badge ok" if ok else "dash-badge muted"
            mark = "✓" if ok else "—"
            badges.append(f'<li class="{cls}" data-badge="{key}"><span class="dash-mark">{mark}</span> {label}</li>')

        initials = _founder_initials(name)
        color = _founder_avatar_color(name)
        rows.append(
            f'<a class="dash-founder-row" href="#{_esc(anchor)}">'
            f'<span class="dash-avatar" style="background:{color}">{_esc(initials)}</span>'
            f'<span class="dash-founder-name">{_esc(name)}</span>'
            f'</a>'
            f'<ul class="dash-badges">{"".join(badges)}</ul>'
        )

    if total_risks <= 0:
        risk_level = "LOW"
    elif total_risks <= 3:
        risk_level = "MED"
    else:
        risk_level = "HIGH"
    risk_cls = {"LOW": "ok", "MED": "watch", "HIGH": "risk"}[risk_level]
    first_anchor = f"founder-{_slug(files[0].stem.removeprefix('founder-'))}"

    return (
        f'<article class="dash-card dash-card-founders">'
        f'<header class="dash-card-head"><span class="dash-num">1</span>'
        f'<h3>Founders\' Background</h3></header>'
        f'<div class="dash-card-body">{"".join(rows)}</div>'
        f'<footer class="dash-card-foot">'
        f'<span class="dash-label">Risk Level</span>'
        f'<span class="dash-pill {risk_cls}" data-risk="{risk_level}">{risk_level}</span>'
        f'<a class="dash-more" href="#{_esc(first_anchor)}">Read more →</a>'
        f'</footer>'
        f'</article>'
    )


def _personas_consensus(supports: int, contradicts: int, fit_score: float | None) -> str:
    if fit_score is None:
        return "LOW"
    if supports >= 2 * contradicts and fit_score >= 7:
        return "HIGH"
    if supports >= contradicts:
        return "MED"
    return "LOW"


def _card_personas(deal_dir: Path, inputs: "PMFInputs | None") -> str | None:
    aggregates = None
    verdicts = None
    if inputs is not None:
        aggregates = inputs.aggregates
        verdicts = inputs.verdicts
    if aggregates is None:
        agg_path = deal_dir / "personas" / "aggregates.yaml"
        if agg_path.exists():
            try:
                aggregates = yaml.safe_load(agg_path.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                aggregates = None
    if verdicts is None:
        ver_path = deal_dir / "personas" / "verdicts.yaml"
        if ver_path.exists():
            try:
                verdicts = yaml.safe_load(ver_path.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                verdicts = None
    if not aggregates and not verdicts:
        return None

    triggers: list[tuple[str, int]] = []
    fit_score: float | None = None
    if isinstance(aggregates, dict):
        bt = aggregates.get("by_trigger_type") or {}
        if isinstance(bt, dict):
            triggers = sorted(((k, int(v)) for k, v in bt.items() if isinstance(v, (int, float))),
                              key=lambda kv: -kv[1])[:3]
        wu = aggregates.get("would_use") or {}
        n = aggregates.get("n")
        if isinstance(wu, dict) and isinstance(n, (int, float)) and n:
            yes = float(wu.get("yes", 0) or 0)
            mostly = float(wu.get("yes-with-caveats", 0) or 0)
            fit_score = round((yes + 0.5 * mostly) / float(n) * 10, 1)

    supports = contradicts = 0
    if isinstance(verdicts, dict):
        rows = verdicts.get("verdicts") or []
        for r in rows:
            if not isinstance(r, dict):
                continue
            v = (r.get("verdict") or "").lower()
            if v == "supports":
                supports += 1
            elif v == "contradicts":
                contradicts += 1

    consensus = _personas_consensus(supports, contradicts, fit_score) if verdicts is not None else None
    consensus_cls = {"HIGH": "ok", "MED": "watch", "LOW": "risk"}.get(consensus or "", "muted")

    pills = "".join(
        f'<span class="dash-pill muted">{_esc(name)}</span>'
        for name, _ in triggers
    ) or '<span class="dash-pill muted">—</span>'

    if triggers:
        max_count = max(c for _, c in triggers) or 1
        bars = "".join(
            f'<li class="dash-bar-row">'
            f'<span class="dash-bar-label">{_esc(name)}</span>'
            f'<span class="dash-bar"><span class="dash-bar-fill" style="width:{int(c / max_count * 100)}%"></span></span>'
            f'</li>'
            for name, c in triggers
        )
    else:
        bars = '<li class="dash-bar-row dash-empty">No trigger data</li>'

    score_html = (
        f'<div class="dash-score"><span class="dash-score-num" data-fit-score="{fit_score}">{fit_score}</span>'
        f'<span class="dash-score-denom">/10</span><span class="dash-score-label">Fit Score</span></div>'
        if fit_score is not None
        else '<div class="dash-score dash-empty">Fit Score —</div>'
    )

    consensus_html = (
        f'<span class="dash-pill {consensus_cls}" data-consensus="{consensus}">{consensus}</span>'
        if consensus is not None
        else '<span class="dash-pill muted">N/A</span>'
    )

    return (
        f'<article class="dash-card dash-card-personas">'
        f'<header class="dash-card-head"><span class="dash-num">2</span>'
        f'<h3>PMF Personas</h3></header>'
        f'<div class="dash-card-body">'
        f'<div class="dash-pill-row">{pills}</div>'
        f'<div class="dash-personas-split">'
        f'<ul class="dash-bars">{bars}</ul>'
        f'{score_html}'
        f'</div></div>'
        f'<footer class="dash-card-foot">'
        f'<span class="dash-label">PMF Consensus</span>'
        f'{consensus_html}'
        f'<a class="dash-more" href="#ledger">Read more →</a>'
        f'</footer>'
        f'</article>'
    )


_POSITIVE_SIGNAL_KEYS = ("pain_described", "current_solution_friction", "wtp_signal")


def _is_positive_call(structured_data: dict | None) -> bool:
    if not isinstance(structured_data, dict):
        return False
    for key in _POSITIVE_SIGNAL_KEYS:
        v = structured_data.get(key)
        if isinstance(v, str) and v.strip() and v.strip().lower() not in ("no", "none", "n/a"):
            return True
        if isinstance(v, (list, dict)) and v:
            return True
    return False


def _read_pull_quote(deal_dir: Path) -> str:
    """Longest non-empty cell from the 'Read' column of demo-validation.md table."""
    md = _read(deal_dir / "calls" / "demo-validation.md") or ""
    candidates: list[str] = []
    in_table = False
    header_cells: list[str] = []
    for line in md.split("\n"):
        if line.strip().startswith("|"):
            cells = _split_pipe_row(line)
            if not header_cells:
                header_cells = [c.strip().lower() for c in cells]
                continue
            if all(re.fullmatch(r"[\s:\-]+", c or "") for c in cells):
                in_table = True
                continue
            if in_table and "read" in header_cells:
                idx = header_cells.index("read")
                if idx < len(cells):
                    val = cells[idx].strip()
                    if val:
                        candidates.append(val)
        else:
            in_table = False
            header_cells = []
    if not candidates:
        return ""
    longest = max(candidates, key=len)
    if len(longest) > 180:
        longest = longest[:177].rstrip() + "…"
    return longest


def _card_calls(deal_dir: Path) -> str | None:
    calls_dir = deal_dir / "calls"
    if not calls_dir.is_dir():
        return None
    call_jsons = sorted(
        p for p in calls_dir.glob("demo-*.json")
        if "-rerun-" not in p.stem
    )
    if not call_jsons:
        return None

    total = len(call_jsons)
    positive = 0
    hero_path: Path | None = None
    hero_audio_src: str | None = None
    for p in call_jsons:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if _is_positive_call(data.get("structured_data")):
            positive += 1
        if hero_path is None:
            local = _ensure_local_recording(deal_dir, p)
            if local is not None:
                hero_path = p
                hero_audio_src = f"calls/recordings/{local.name}"
            elif data.get("recording_url"):
                hero_path = p
                hero_audio_src = data["recording_url"]

    pct = round(positive / total * 100) if total else 0
    pull_quote = _read_pull_quote(deal_dir)

    if hero_audio_src:
        wave_id = f"dash-wave-{_slug(hero_path.stem) if hero_path else 'hero'}"
        waveform_html = (
            f'<div class="dash-waveform" id="{wave_id}" data-audio="{_esc(hero_audio_src)}"></div>'
            f'<audio class="dash-audio" controls preload="none" src="{_esc(hero_audio_src)}"></audio>'
        )
    else:
        waveform_html = '<div class="dash-waveform dash-empty">No audio available</div>'

    quote_html = (
        f'<blockquote class="dash-quote">"{_esc(pull_quote)}"</blockquote>'
        if pull_quote else ''
    )

    return (
        f'<article class="dash-card dash-card-calls" data-has-audio="{"1" if hero_audio_src else "0"}">'
        f'<header class="dash-card-head"><span class="dash-num">3</span>'
        f'<h3>Real Call Insights</h3></header>'
        f'<div class="dash-card-body">'
        f'{waveform_html}'
        f'<div class="dash-metrics-row">'
        f'<div class="dash-metric"><span class="dash-metric-label">Calls Completed</span>'
        f'<span class="dash-metric-num" data-calls-completed="{total}">{total}</span></div>'
        f'<div class="dash-metric"><span class="dash-metric-label">Positive Signal</span>'
        f'<span class="dash-metric-num" data-positive-pct="{pct}">{pct}%</span></div>'
        f'</div>'
        f'{quote_html}'
        f'</div>'
        f'<footer class="dash-card-foot">'
        f'<a class="dash-more" href="#demo-call-validation">Read more →</a>'
        f'</footer>'
        f'</article>'
    )


def _format_money_m(value_m: float) -> str:
    """Format a value in millions as $X.YB or $XM."""
    if value_m >= 1000:
        return f"${value_m / 1000:.1f}B"
    return f"${int(round(value_m))}M"


def _parse_industry_tag(market_md: str, memo_text: str | None) -> str:
    for src in (market_md, memo_text or ""):
        m = re.search(r"\*\*\s*(?:Industry|Sector)\s*:\s*\*\*\s*(.+)", src, re.I)
        if m:
            return m.group(1).strip().splitlines()[0].rstrip(".")
    return ""


def _parse_cagr(market_md: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*CAGR", market_md, re.I)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _card_market(deal_dir: Path, memo_text: str | None) -> str | None:
    market_md = _read(deal_dir / "market-sizing.md")
    if not market_md:
        return None
    try:
        sizing = parse_market_sizing(market_md)
    except Exception:
        sizing = None
    if not sizing:
        return None

    expansion = sizing.get("expansion") or sizing.get("wedge")
    if not expansion:
        return None
    tam_upper_m = float(expansion[1])

    industry = _parse_industry_tag(market_md, memo_text)
    cagr = _parse_cagr(market_md)
    sparkline = _market_chart_svg(sizing) if sizing else ""

    industry_html = (
        f'<div class="dash-row"><span class="dash-label">Industry</span>'
        f'<span class="dash-value">{_esc(industry)}</span></div>'
        if industry else ''
    )
    tam_html = (
        f'<div class="dash-row"><span class="dash-label">Market Size</span>'
        f'<span class="dash-value" data-tam="{tam_upper_m:g}">{_format_money_m(tam_upper_m)} (TAM)</span></div>'
    )
    cagr_html = (
        f'<div class="dash-row"><span class="dash-label">Growth Rate</span>'
        f'<span class="dash-value" data-cagr="{cagr:g}">{cagr:g}% CAGR</span></div>'
        if cagr is not None else ''
    )

    return (
        f'<article class="dash-card dash-card-market">'
        f'<header class="dash-card-head"><span class="dash-num">4</span>'
        f'<h3>Market Sizing</h3></header>'
        f'<div class="dash-card-body">'
        f'{industry_html}{tam_html}{cagr_html}'
        f'</div>'
        f'<footer class="dash-card-foot">'
        f'<a class="dash-more" href="#market-sizing">Read more →</a>'
        f'</footer>'
        f'</article>'
    )


def _parse_competitors(comp_md: str) -> list[str]:
    """Extract top 3 competitor names from a markdown table or H2 headings."""
    names: list[str] = []
    in_table = False
    header_cells: list[str] = []
    for line in comp_md.split("\n"):
        if line.strip().startswith("|"):
            cells = _split_pipe_row(line)
            if not header_cells:
                header_cells = [c.strip().lower() for c in cells]
                continue
            if all(re.fullmatch(r"[\s:\-]+", c or "") for c in cells):
                in_table = True
                continue
            if in_table and "competitor" in header_cells:
                idx = header_cells.index("competitor")
                if idx < len(cells):
                    val = cells[idx].strip()
                    if val:
                        names.append(val)
                        if len(names) >= 3:
                            return names
        else:
            in_table = False
            header_cells = []
    if names:
        return names[:3]

    for line in comp_md.split("\n"):
        h = re.match(r"^##\s+(.+)$", line)
        if h:
            title = h.group(1).strip()
            if 2 <= len(title.split()) <= 4 and title[0].isupper():
                names.append(title)
                if len(names) >= 3:
                    break
    return names[:3]


def _parse_market_opportunity(memo_text: str | None) -> str:
    if not memo_text:
        return "MED"
    m = re.search(r"market opportunity\s*:\s*\**\s*(HIGH|MED|MEDIUM|LOW)", memo_text, re.I)
    if m:
        v = m.group(1).upper()
        return "MED" if v == "MEDIUM" else v
    return "MED"


def _card_competitors(deal_dir: Path, memo_text: str | None) -> str | None:
    comp_md = _read(deal_dir / "competitive-landscape.md")
    if not comp_md:
        return None
    names = _parse_competitors(comp_md)
    if not names:
        return None

    bar_widths = [100, 75, 50]
    rows = "".join(
        f'<li class="dash-bar-row">'
        f'<span class="dash-bar-label">{idx + 1}. {_esc(name)}</span>'
        f'<span class="dash-bar"><span class="dash-bar-fill" style="width:{bar_widths[idx]}%"></span></span>'
        f'</li>'
        for idx, name in enumerate(names)
    )

    opportunity = _parse_market_opportunity(memo_text)
    opp_cls = {"HIGH": "ok", "MED": "watch", "LOW": "risk"}.get(opportunity, "muted")

    return (
        f'<article class="dash-card dash-card-competitors">'
        f'<header class="dash-card-head"><span class="dash-num">5</span>'
        f'<h3>Top Competitors</h3></header>'
        f'<div class="dash-card-body">'
        f'<ul class="dash-bars">{rows}</ul>'
        f'</div>'
        f'<footer class="dash-card-foot">'
        f'<span class="dash-label">Market Opportunity</span>'
        f'<span class="dash-pill {opp_cls}" data-opportunity="{opportunity}">{opportunity}</span>'
        f'<a class="dash-more" href="#competitive-landscape">Read more →</a>'
        f'</footer>'
        f'</article>'
    )


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

    if "recommendation" in memo_sections:
        sections_html.append(
            _details_section("recommendation", "Recommendation", render_markdown(memo_sections["recommendation"], heading_offset=OFFSET))
        )
        toc.append(("recommendation", "Recommendation"))

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
        pre_main_html=callout + (_card_founders(deal_dir) or "") + (_card_personas(deal_dir, None) or "") + (_card_calls(deal_dir) or "") + (_card_market(deal_dir, memo) or "") + (_card_competitors(deal_dir, memo) or ""),
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
    ribbon = render_recommendation_ribbon(memo)

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
    pre_main = callout + ribbon + (_card_founders(deal_dir) or "") + (_card_personas(deal_dir, inputs) or "") + (_card_calls(deal_dir) or "") + (_card_market(deal_dir, memo) or "") + (_card_competitors(deal_dir, memo) or "")
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
    ribbon = render_recommendation_ribbon(memo)

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
    pre_main = callout + ribbon + (_card_founders(deal_dir) or "") + (_card_personas(deal_dir, inputs) or "") + (_card_calls(deal_dir) or "") + (_card_market(deal_dir, memo) or "") + (_card_competitors(deal_dir, memo) or "")
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
