#!/usr/bin/env python3
"""Fleet-run state manager.

Subcommands:

  init           Resolve the input source (--slugs / --auto / queue.txt),
                 validate every slug, check that each deal directory exists,
                 and create deals/_fleet/manifest.json with every queued slug
                 pre-populated as `pending`. Truncates per-slug log files.

  mark           Update a single slug's status. Writes started_at /
                 finished_at timestamps as appropriate. With --phase, updates
                 a per-phase status (background-check or pmf-signal) and
                 reflects the per_deal[slug].status as the terminal state.

  add-tokens     Add an integer count to manifest.cumulative_tokens. Best-
                 effort: skip the call if the sub-skill did not report tokens.

  budget-check   Exit 0 if cumulative_tokens <= max_tokens (or no cap is set).
                 Exit 1 if the cap is set and crossed.

  summary        Print the end-of-run summary line and set finished_at if all
                 slugs are in a terminal state.

Stdlib only. Designed to be invoked from the SKILL.md procedural prose by an
LLM agent that does the actual sub-skill dispatch and concurrency control.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any

FLEET_DIR = Path("deals/_fleet")
MANIFEST = FLEET_DIR / "manifest.json"
LOGS_DIR = FLEET_DIR / "logs"
QUEUE_FILE = FLEET_DIR / "queue.txt"
DEALS_DIR = Path("deals")

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TERMINAL_STATUSES = {"complete", "failed", "aborted-budget"}
PHASE_NAMES = ("background-check", "pmf-signal")


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def die(msg: str, code: int = 2) -> int:
    print(msg, file=sys.stderr)
    return code


# ---------- queue resolution -------------------------------------------------


def parse_queue_file(path: Path) -> list[str]:
    if not path.is_file():
        return []
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def auto_enroll() -> list[str]:
    if not DEALS_DIR.is_dir():
        return []
    return sorted(
        p.name
        for p in DEALS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )


def resolve_queue(slugs: str | None, auto: bool) -> tuple[list[str], str]:
    """Return (queue, source). Source is one of: slugs, auto, queue-file."""
    if slugs:
        return ([s.strip() for s in slugs.split(",") if s.strip()], "slugs")
    if auto:
        return (auto_enroll(), "auto")
    qf = parse_queue_file(QUEUE_FILE)
    if qf:
        return (qf, "queue-file")
    return ([], "")


def validate_slugs(queue: list[str]) -> list[str]:
    """Return list of validation errors (empty list = clean)."""
    errors: list[str] = []
    seen: set[str] = set()
    for s in queue:
        if s in seen:
            errors.append(f"duplicate slug: {s}")
            continue
        seen.add(s)
        if s.startswith("_"):
            errors.append(f"slug '{s}' starts with underscore (reserved for fleet/system use)")
            continue
        if not SLUG_RE.match(s):
            errors.append(f"slug '{s}' is not kebab-case (lowercase letters, digits, hyphens)")
    return errors


# ---------- manifest helpers -------------------------------------------------


def load_manifest() -> dict[str, Any]:
    if not MANIFEST.is_file():
        raise SystemExit(f"manifest not found: {MANIFEST} — run `init` first")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save_manifest(m: dict[str, Any]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(m, indent=2, sort_keys=False, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def empty_phase() -> dict[str, Any]:
    return {"status": "pending", "started_at": None, "finished_at": None}


def empty_per_deal(slug: str) -> dict[str, Any]:
    return {
        "status": "pending",
        "started_at": None,
        "finished_at": None,
        "error_summary": None,
        "log_path": f"deals/_fleet/logs/{slug}.log",
        "phases": {},
    }


# ---------- subcommand: init -------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    if args.slugs and args.auto:
        return die("error: --slugs and --auto are mutually exclusive")

    queue, source = resolve_queue(args.slugs, args.auto)
    if not source:
        print(
            "error: no fleet input source provided. Pass one of:\n"
            "  --slugs a,b,c           explicit comma-separated slug list\n"
            "  --auto                  enroll every non-underscore directory under deals/\n"
            "  (or write deals/_fleet/queue.txt with one slug per line)",
            file=sys.stderr,
        )
        return 2

    if not queue:
        print(
            f"error: input source '{source}' resolved to an empty queue. "
            "Check --slugs / --auto / deals/_fleet/queue.txt and try again.",
            file=sys.stderr,
        )
        return 2

    errors = validate_slugs(queue)
    if errors:
        print("error: invalid slug(s) — entire run rejected:", file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        return 2

    if args.mode not in ("gate", "all", "pmf-only"):
        return die(f"error: --mode must be one of gate|all|pmf-only (got '{args.mode}')")

    # Build manifest.
    FLEET_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    started = now()
    per_deal: dict[str, Any] = {}
    for slug in queue:
        entry = empty_per_deal(slug)
        deal_dir = DEALS_DIR / slug
        if not deal_dir.is_dir():
            entry["status"] = "failed"
            entry["error_summary"] = (
                f"deals/{slug}/ does not exist. Scaffold it (e.g. by running "
                "dudu:background-check on the slug) before re-invoking the fleet."
            )
            entry["finished_at"] = started
        else:
            # Pre-populate phases the run will actually execute.
            if args.mode in ("gate", "all"):
                entry["phases"]["background-check"] = empty_phase()
            if args.mode == "all":
                entry["phases"]["pmf-signal"] = empty_phase()
            if args.mode == "pmf-only":
                # Refuse if L1 not complete; mark slug failed up front so the
                # worker pool never tries to run pmf-signal on an incomplete L1.
                sentinel = deal_dir / "background.md"
                if not sentinel.is_file():
                    entry["status"] = "failed"
                    entry["error_summary"] = (
                        f"L1 sentinel deals/{slug}/background.md not found — "
                        "run dudu:background-check first."
                    )
                    entry["finished_at"] = started
                else:
                    entry["phases"]["pmf-signal"] = empty_phase()

        per_deal[slug] = entry

        # Truncate per-slug log file so each fleet run starts fresh.
        log_path = LOGS_DIR / f"{slug}.log"
        log_path.write_text("", encoding="utf-8")

    manifest = {
        "fleet_run_id": started,
        "started_at": started,
        "finished_at": None,
        "mode": args.mode,
        "concurrency": args.concurrency,
        "max_tokens": args.max_tokens,
        "cumulative_tokens": 0,
        "input_source": source,
        "queue": queue,
        "per_deal": per_deal,
    }
    save_manifest(manifest)

    # Friendly stdout for the agent / user.
    print(f"Fleet initialized: {len(queue)} slug(s), mode={args.mode}, concurrency={args.concurrency}")
    print(f"Input source: {source}")
    if args.max_tokens is not None:
        print(f"Token cap: {args.max_tokens}")
    else:
        print("Token cap: none (concurrency cap only)")
    print("Queue:")
    for slug in queue:
        status = per_deal[slug]["status"]
        marker = "✓" if status == "pending" else "✗"
        suffix = "" if status == "pending" else f" [{status}: {per_deal[slug]['error_summary']}]"
        print(f"  {marker} {slug}{suffix}")
    print(f"Manifest written to: {MANIFEST}")
    return 0


# ---------- subcommand: mark -------------------------------------------------


def _terminal_for_per_deal(entry: dict[str, Any]) -> str:
    """Compute terminal status from phase statuses."""
    phases = entry.get("phases", {})
    if not phases:
        return entry.get("status", "pending")
    statuses = [p.get("status", "pending") for p in phases.values()]
    if any(s == "failed" for s in statuses):
        return "failed"
    if any(s == "aborted-budget" for s in statuses):
        return "aborted-budget"
    if all(s == "complete" for s in statuses):
        return "complete"
    if any(s == "running" for s in statuses):
        return "running"
    return "pending"


def cmd_mark(args: argparse.Namespace) -> int:
    valid = {"running", "complete", "failed", "aborted-budget", "pending", "skipped"}
    if args.status not in valid:
        return die(f"error: status must be one of {sorted(valid)} (got '{args.status}')")

    m = load_manifest()
    if args.slug not in m["per_deal"]:
        return die(f"error: slug '{args.slug}' not in fleet manifest")

    entry = m["per_deal"][args.slug]
    ts = now()

    if args.phase:
        if args.phase not in PHASE_NAMES:
            return die(f"error: --phase must be one of {PHASE_NAMES}")
        # Lazily create the phase entry if needed (covers --all chaining where
        # pmf-signal isn't pre-populated until L1 completes).
        if args.phase not in entry["phases"]:
            entry["phases"][args.phase] = empty_phase()
        ph = entry["phases"][args.phase]
        ph["status"] = args.status
        if args.status == "running" and not ph["started_at"]:
            ph["started_at"] = ts
        if args.status in TERMINAL_STATUSES or args.status == "skipped":
            ph["finished_at"] = ts
        # Recompute the per-deal terminal status from phases.
        entry["status"] = _terminal_for_per_deal(entry)
        if entry["status"] == "running" and not entry["started_at"]:
            entry["started_at"] = ts
        if entry["status"] in TERMINAL_STATUSES:
            entry["finished_at"] = ts
    else:
        # No phase given — direct per-deal status update.
        entry["status"] = args.status
        if args.status == "running" and not entry["started_at"]:
            entry["started_at"] = ts
        if args.status in TERMINAL_STATUSES:
            entry["finished_at"] = ts

    if args.error:
        entry["error_summary"] = args.error
    if args.log_path:
        entry["log_path"] = args.log_path

    save_manifest(m)
    phase_label = f" (phase {args.phase})" if args.phase else ""
    print(f"marked {args.slug}{phase_label}: {args.status}")
    return 0


# ---------- subcommand: add-tokens / budget-check ----------------------------


def cmd_add_tokens(args: argparse.Namespace) -> int:
    if args.count < 0:
        return die("error: token count cannot be negative")
    m = load_manifest()
    m["cumulative_tokens"] = int(m.get("cumulative_tokens", 0)) + args.count
    save_manifest(m)
    print(f"cumulative_tokens={m['cumulative_tokens']}")
    return 0


def cmd_budget_check(_: argparse.Namespace) -> int:
    m = load_manifest()
    cap = m.get("max_tokens")
    if cap is None:
        return 0
    used = int(m.get("cumulative_tokens", 0))
    if used > cap:
        print(f"budget exceeded: {used} > {cap}", file=sys.stderr)
        return 1
    print(f"budget ok: {used}/{cap}")
    return 0


# ---------- subcommand: summary ---------------------------------------------


def cmd_summary(_: argparse.Namespace) -> int:
    m = load_manifest()
    counts: dict[str, int] = {"complete": 0, "failed": 0, "aborted-budget": 0, "running": 0, "pending": 0}
    for entry in m["per_deal"].values():
        s = entry.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1

    # If everything is terminal, set finished_at.
    all_terminal = all(
        entry.get("status") in TERMINAL_STATUSES for entry in m["per_deal"].values()
    )
    if all_terminal and not m.get("finished_at"):
        m["finished_at"] = now()
        save_manifest(m)

    line = (
        f"{counts['complete']} complete, {counts['failed']} failed, "
        f"{counts['aborted-budget']} aborted-budget"
    )
    if counts["running"] or counts["pending"]:
        line += f", {counts['running']} running, {counts['pending']} pending"
    line += " — see deals/_fleet/manifest.json"
    print(line)
    return 0


# ---------- argument parsing ------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fleet-run.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="resolve queue, validate, create manifest")
    p_init.add_argument("--slugs", help="comma-separated slug list (overrides queue file)")
    p_init.add_argument("--auto", action="store_true", help="enroll every non-underscore deals/ subdir")
    p_init.add_argument("--concurrency", type=int, default=3, help="max parallel sub-skill invocations (default 3)")
    p_init.add_argument("--max-tokens", type=int, default=None, help="opt-in cumulative token cap (default: none)")
    p_init.add_argument(
        "--mode",
        choices=("gate", "all", "pmf-only"),
        default="gate",
        help="gate=L1 only, all=L1+L2, pmf-only=L2 only on slugs with L1 already done",
    )
    p_init.set_defaults(func=cmd_init)

    p_mark = sub.add_parser("mark", help="update a slug's status")
    p_mark.add_argument("slug")
    p_mark.add_argument("status", help="running|complete|failed|aborted-budget|pending|skipped")
    p_mark.add_argument("--phase", choices=PHASE_NAMES, default=None, help="phase to update (default: per-deal)")
    p_mark.add_argument("--error", default=None, help="error summary string (for failed)")
    p_mark.add_argument("--log-path", default=None, help="path to per-slug log")
    p_mark.set_defaults(func=cmd_mark)

    p_tok = sub.add_parser("add-tokens", help="increment cumulative_tokens")
    p_tok.add_argument("count", type=int)
    p_tok.set_defaults(func=cmd_add_tokens)

    p_bud = sub.add_parser("budget-check", help="exit 1 iff token cap is set and exceeded")
    p_bud.set_defaults(func=cmd_budget_check)

    p_sum = sub.add_parser("summary", help="print end-of-run summary line")
    p_sum.set_defaults(func=cmd_summary)

    return p


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
