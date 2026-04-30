"""Recipe: count distinct named customer logos and detailed case studies in HTML."""

from __future__ import annotations

import re

LOGO_ALT = re.compile(r'<img\b[^>]*\balt="([^"]+?)\s+logo"', re.IGNORECASE)
CASE_HEADING = re.compile(r"<h[1-6][^>]*>\s*([^<]+?)\s+case\s+study\s*</h[1-6]>", re.IGNORECASE)


def run(htmls: list[str]) -> str:
    logos: set[str] = set()
    cases = 0
    for html in htmls:
        for m in LOGO_ALT.finditer(html):
            logos.add(m.group(1).strip())
        cases += len(CASE_HEADING.findall(html))
    return f"homepage shows {len(logos)} named logo(s); {cases} detailed case stud(ies)"
