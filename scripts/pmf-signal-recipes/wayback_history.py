"""Recipe: extract numeric claims from a sequence of Wayback snapshots and report the trajectory."""

from __future__ import annotations

import re

NUMBER_NEAR_TRUSTED = re.compile(r"Trusted\s+by\s+([0-9][0-9,]*)\b", re.IGNORECASE)


def run(htmls: list[str]) -> str:
    numbers: list[int] = []
    for html in htmls:
        m = NUMBER_NEAR_TRUSTED.search(html)
        if m:
            numbers.append(int(m.group(1).replace(",", "")))
    if not numbers:
        return f"{len(htmls)} snapshot(s); no claim numbers extractable"
    trajectory = " → ".join(str(n) for n in numbers)
    return (
        f"{len(htmls)} snapshot(s); claim numbers found: {numbers}; "
        f"trajectory: {trajectory}"
    )
