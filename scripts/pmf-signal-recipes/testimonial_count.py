"""Recipe: count testimonial blocks with vs without named attribution."""

from __future__ import annotations

import re

TESTIMONIAL = re.compile(
    r'<blockquote\b[^>]*\bclass="[^"]*testimonial[^"]*"[^>]*>(.*?)</blockquote>',
    re.IGNORECASE | re.DOTALL,
)
CITE = re.compile(r"<cite\b[^>]*>(.*?)</cite>", re.IGNORECASE | re.DOTALL)


def run(htmls: list[str]) -> str:
    named = 0
    unattributed = 0
    for html in htmls:
        for m in TESTIMONIAL.finditer(html):
            block = m.group(1)
            cite = CITE.search(block)
            if cite and cite.group(1).strip():
                named += 1
            else:
                unattributed += 1
    return f"{named} testimonial(s) with named attribution; {unattributed} unattributed quote(s)"
