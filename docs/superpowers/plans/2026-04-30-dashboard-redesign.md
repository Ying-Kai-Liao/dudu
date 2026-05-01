# Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 5-card executive dashboard above the existing detailed `report.html`, mirroring the partner-meeting "AI Due Diligence Report" mockup style. Cards map to the dudu pipeline (founders → personas → calls → market → competitors). Existing detailed sections remain unchanged below.

**Architecture:** Single new function `render_dashboard()` in `scripts/render-report.py`, composed of five card helpers (each independent, each returning `str | None`). Inserted into `pre_main_html` after the recommendation ribbon at all four render-branch call sites. Real Vapi audio is downloaded once at render time and rendered with `wavesurfer.js` (vendored, ~30 KB). No new Python dependencies, no skill or orchestrator changes.

**Tech Stack:** Python 3 stdlib + PyYAML (existing), `wavesurfer.js` v7.8.0 (new, vendored), bash + `assert_contains` for tests (existing pattern).

**Spec:** `docs/superpowers/specs/2026-04-30-dashboard-redesign-design.md`

---

## File Structure

**New files:**
- `scripts/vendor/wavesurfer-7.8.0.min.js` — vendored wavesurfer.js, loaded into the report only when Card 3 renders.
- `tests/fixtures/dashboard/` — small fixtures that exercise each card in isolation.
  - `tests/fixtures/dashboard/founders-only/manifest.json` + `founder-jane-doe.md`
  - `tests/fixtures/dashboard/calls-only/manifest.json` + `calls/demo-billing.json` + `calls/demo-validation.md`
  - `tests/fixtures/dashboard/empty/manifest.json` (only manifest — proves dashboard returns empty)
  - `tests/fixtures/dashboard/run.sh` — bash test runner using existing `assert_contains` pattern.

**Modified files:**
- `scripts/render-report.py` — add helpers, CSS constant, JS constant, dashboard composer, three call-site insertions.
- `tests/fixtures/pmf-led-report/run.sh` — add 4 assertions confirming dashboard appears in `full` branch.

---

## Task 1: Vendor wavesurfer.js and add loader constant

**Files:**
- Create: `scripts/vendor/wavesurfer-7.8.0.min.js`
- Modify: `scripts/render-report.py` (add constant)

- [ ] **Step 1: Create the vendor directory and download wavesurfer.js**

```bash
mkdir -p scripts/vendor
curl -fsSL -o scripts/vendor/wavesurfer-7.8.0.min.js \
  https://unpkg.com/wavesurfer.js@7.8.0/dist/wavesurfer.min.js
```

Expected: file size ~30–40 KB. Verify:
```bash
ls -lh scripts/vendor/wavesurfer-7.8.0.min.js
```

- [ ] **Step 2: Add WAVESURFER_JS constant to render-report.py**

In `scripts/render-report.py`, locate the existing `JS = """..."""` constant (around line 1102). Immediately **above** it, add:

```python
_VENDOR_DIR = Path(__file__).parent / "vendor"


def _load_wavesurfer_js() -> str:
    """Read vendored wavesurfer.js. Returns empty string if missing."""
    p = _VENDOR_DIR / "wavesurfer-7.8.0.min.js"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


WAVESURFER_JS = _load_wavesurfer_js()
```

- [ ] **Step 3: Verify the constant loads**

```bash
python3 -c "
import sys
sys.path.insert(0, 'scripts')
from importlib import import_module
m = import_module('render-report')
print('len:', len(m.WAVESURFER_JS))
assert len(m.WAVESURFER_JS) > 10000, 'wavesurfer.js looks too small'
print('OK')
"
```

Expected: `len: 30000+ ... OK`. (The `import_module` form is needed because `render-report.py` has a hyphen in the name.)

- [ ] **Step 4: Commit**

```bash
git add scripts/vendor/wavesurfer-7.8.0.min.js scripts/render-report.py
git commit -m "Vendor wavesurfer.js for dashboard waveform"
```

---

## Task 2: Audio download helper `_ensure_local_recording`

**Files:**
- Modify: `scripts/render-report.py` (add helper near `_recordings_html`, ~line 1241)
- Create: `tests/fixtures/dashboard/calls-only/calls/demo-billing.json`
- Create: `tests/fixtures/dashboard/calls-only/manifest.json`
- Create: `tests/fixtures/dashboard/run.sh` (test runner; will grow across tasks)

- [ ] **Step 1: Create the calls-only fixture**

`tests/fixtures/dashboard/calls-only/manifest.json`:
```json
{
  "slug": "calls-only",
  "company": "Calls Only",
  "stage": "Watch",
  "generated": "2026-04-30T00:00:00Z",
  "skills": {}
}
```

`tests/fixtures/dashboard/calls-only/calls/demo-billing.json`:
```json
{
  "id": "demo-billing-test",
  "status": "ended",
  "endedReason": "customer-ended-call",
  "recording_url": "https://storage.vapi.ai/example-stereo.wav",
  "structured_data": {
    "pain_described": "Manual billing reconciliation costs us 3 days per close.",
    "current_solution_friction": "Excel + Stripe + slack pings",
    "wtp_signal": "yes-with-caveats"
  }
}
```

- [ ] **Step 2: Create the test runner with the first assertion (TDD: write failing test first)**

`tests/fixtures/dashboard/run.sh`:
```bash
#!/usr/bin/env bash
# Smoke tests for the dashboard cards in scripts/render-report.py.
set -u
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
renderer="$repo_root/scripts/render-report.py"
fail=0

assert_contains() {
    local label="$1" needle="$2" haystack="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        echo "  PASS: $label"
    else
        echo "  FAIL: $label — did not find '$needle'"
        fail=1
    fi
}

assert_not_contains() {
    local label="$1" needle="$2" haystack="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        echo "  PASS: $label"
    else
        echo "  FAIL: $label — unexpectedly found '$needle'"
        fail=1
    fi
}

run_unit_test() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        echo "  PASS: $label"
    else
        echo "  FAIL: $label — expected '$expected' got '$actual'"
        fail=1
    fi
}

echo "[ensure_local_recording] returns None when recording_url missing"
out="$(python3 -c "
import sys, json, tempfile, pathlib
sys.path.insert(0, '$repo_root/scripts')
from importlib import import_module
m = import_module('render-report')
with tempfile.TemporaryDirectory() as td:
    deal = pathlib.Path(td)
    (deal / 'calls').mkdir()
    p = deal / 'calls' / 'no-url.json'
    p.write_text(json.dumps({'id': 'x'}))
    r = m._ensure_local_recording(deal, p)
    print('None' if r is None else r)
")"
run_unit_test "no recording_url -> None" "None" "$out"

echo "[ensure_local_recording] returns existing local file (cache hit)"
out="$(python3 -c "
import sys, json, tempfile, pathlib
sys.path.insert(0, '$repo_root/scripts')
from importlib import import_module
m = import_module('render-report')
with tempfile.TemporaryDirectory() as td:
    deal = pathlib.Path(td)
    (deal / 'calls' / 'recordings').mkdir(parents=True)
    cached = deal / 'calls' / 'recordings' / 'demo-x.wav'
    cached.write_bytes(b'RIFFXXXX')
    p = deal / 'calls' / 'demo-x.json'
    p.write_text(json.dumps({'id': 'x', 'recording_url': 'http://example/x.wav'}))
    r = m._ensure_local_recording(deal, p)
    print('hit' if r == cached else 'miss')
")"
run_unit_test "cache hit returns local file" "hit" "$out"

echo
if [[ $fail -eq 0 ]]; then
    echo "OK — all dashboard fixtures pass"
    exit 0
else
    echo "FAIL — see above"
    exit 1
fi
```

Make executable:
```bash
chmod +x tests/fixtures/dashboard/run.sh
```

- [ ] **Step 3: Run the test, expect failure (function not yet defined)**

```bash
bash tests/fixtures/dashboard/run.sh
```

Expected: both unit tests FAIL with `AttributeError: module ... has no attribute '_ensure_local_recording'`. Output ends with `FAIL — see above`.

- [ ] **Step 4: Implement `_ensure_local_recording`**

In `scripts/render-report.py`, immediately **after** the existing `_recordings_html` function (around line 1278), insert:

```python
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
```

- [ ] **Step 5: Run the test, expect pass**

```bash
bash tests/fixtures/dashboard/run.sh
```

Expected: both unit tests PASS. Final line: `OK — all dashboard fixtures pass`.

- [ ] **Step 6: Commit**

```bash
git add scripts/render-report.py tests/fixtures/dashboard/
git commit -m "Add _ensure_local_recording for Vapi audio cache"
```

---

## Task 3: Card 1 — Founders' Background

**Files:**
- Modify: `scripts/render-report.py` (add `_card_founders` near other card helpers — append at end of `# ---------- HTML assembly ----------` region, around line 1340)
- Create: `tests/fixtures/dashboard/founders-only/manifest.json`
- Create: `tests/fixtures/dashboard/founders-only/founder-jane-doe.md`
- Modify: `tests/fixtures/dashboard/run.sh` (append assertions)

- [ ] **Step 1: Create the founders-only fixture**

`tests/fixtures/dashboard/founders-only/manifest.json`:
```json
{
  "slug": "founders-only",
  "company": "Founders Only",
  "stage": "Watch",
  "generated": "2026-04-30T00:00:00Z",
  "skills": {}
}
```

`tests/fixtures/dashboard/founders-only/founder-jane-doe.md`:
```markdown
# Founder: Jane Doe

**Generated:** 2026-04-30T00:00:00Z

## Experience

- 10 years at FinTech Inc as VP Product
- LinkedIn: https://linkedin.com/in/janedoe

## Prior ventures

- Founded WidgetCo (acquired 2019)

## Network

- Co-founder of YC W21 batch peer group

## Risks

- Single non-technical founder (no CTO yet)
- One previous startup pivoted twice before exit
```

- [ ] **Step 2: Append failing assertions to `tests/fixtures/dashboard/run.sh`**

Insert this block before the final `echo` / exit summary:

```bash
echo "[card-founders] renders for founders-only fixture"
python3 "$renderer" "$script_dir/founders-only" >/dev/null 2>&1
out="$(cat "$script_dir/founders-only/report.html")"
assert_contains "founders card present" 'class="dash-card dash-card-founders"' "$out"
assert_contains "founder name shown" "Jane Doe" "$out"
assert_contains "linkedin badge" 'data-badge="linkedin"' "$out"
assert_contains "experience badge" 'data-badge="experience"' "$out"
assert_contains "track record badge" 'data-badge="track-record"' "$out"
assert_contains "risk pill MED" 'data-risk="MED"' "$out"
assert_contains "read more anchor" 'href="#founder-jane-doe"' "$out"

echo "[card-founders] absent when no founder files"
python3 "$renderer" "$script_dir/calls-only" >/dev/null 2>&1
out="$(cat "$script_dir/calls-only/report.html")"
assert_not_contains "no founders card" 'dash-card-founders' "$out"
```

- [ ] **Step 3: Run test, expect failure**

```bash
bash tests/fixtures/dashboard/run.sh
```

Expected: founders card assertions FAIL (function does not yet emit dashboard).

- [ ] **Step 4: Implement `_card_founders`**

Insert after the existing `_personas_block` function (around line 1426). The function and its helpers:

```python
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
```

Note: this card is NOT yet wired into the rendered output. Step 5 wires it via a temporary call site so the test passes; final wiring happens in Task 8.

- [ ] **Step 5: Wire the card temporarily into `render_legacy` (will move to dashboard composer in Task 8)**

In `scripts/render-report.py`, locate `render_legacy` (line 1473). Find the line that builds `pre_main` (`callout` is the variable, returned from `_build_header_html`). Find the call to `_build_html_skeleton` at the end. Replace the `pre_main_html=callout` argument with:

```python
        pre_main_html=callout + (_card_founders(deal_dir) or ""),
```

Do the same in `render_pmf_led` — find the line `pre_main = callout + ribbon` and change to:

```python
    pre_main = callout + ribbon + (_card_founders(deal_dir) or "")
```

Do the same in `render_markdown_fallback` — locate its `_build_html_skeleton` call (line ~1813) and adjust similarly.

- [ ] **Step 6: Run the test, expect pass**

```bash
bash tests/fixtures/dashboard/run.sh
```

Expected: all assertions PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/render-report.py tests/fixtures/dashboard/
git commit -m "Add Card 1: Founders' Background dashboard card"
```

---

## Task 4: Card 2 — PMF Personas

**Files:**
- Modify: `scripts/render-report.py` (add `_card_personas`)
- Create: `tests/fixtures/dashboard/personas-only/manifest.json`
- Create: `tests/fixtures/dashboard/personas-only/personas/aggregates.yaml`
- Create: `tests/fixtures/dashboard/personas-only/personas/verdicts.yaml`
- Create: `tests/fixtures/dashboard/personas-only/pitch.yaml`
- Modify: `tests/fixtures/dashboard/run.sh` (append assertions)

- [ ] **Step 1: Create the personas-only fixture**

`tests/fixtures/dashboard/personas-only/manifest.json`:
```json
{
  "slug": "personas-only",
  "company": "Personas Only",
  "stage": "Watch",
  "generated": "2026-04-30T00:00:00Z",
  "skills": {}
}
```

`tests/fixtures/dashboard/personas-only/pitch.yaml`:
```yaml
schema_version: 1
deal: personas-only
claims: []
```

`tests/fixtures/dashboard/personas-only/personas/aggregates.yaml`:
```yaml
schema_version: 1
n: 12
grounded: 12
fabricated: 0
would_use:
  yes: 6
  yes-with-caveats: 4
  no: 2
willing_to_pay:
  yes: 5
  maybe: 5
  no: 2
by_trigger_type:
  contract-exception: 5
  billing-reconciliation: 4
  audit-readiness: 2
  finance-stack: 1
```

`tests/fixtures/dashboard/personas-only/personas/verdicts.yaml`:
```yaml
schema_version: 1
verdicts:
  - claim_id: c1
    verdict: supports
  - claim_id: c2
    verdict: supports
  - claim_id: c3
    verdict: supports
  - claim_id: c4
    verdict: partial
  - claim_id: c5
    verdict: contradicts
```

- [ ] **Step 2: Append failing assertions to `tests/fixtures/dashboard/run.sh`**

```bash
echo "[card-personas] renders for personas-only fixture"
python3 "$renderer" "$script_dir/personas-only" >/dev/null 2>&1
out="$(cat "$script_dir/personas-only/report.html")"
assert_contains "personas card present" 'class="dash-card dash-card-personas"' "$out"
assert_contains "trigger pill 1" 'contract-exception' "$out"
assert_contains "trigger pill 2" 'billing-reconciliation' "$out"
assert_contains "fit score 6.7" 'data-fit-score="6.7"' "$out"
assert_contains "consensus pill MED" 'data-consensus="MED"' "$out"
```

Math check (for the implementer): `(6 + 0.5*4) / 12 × 10 = 6.666... → 6.7`. Verdicts: 3 supports, 1 partial, 1 contradicts. `supports (3) >= 2 × contradicts (1×2=2)` AND `fit_score 6.7 < 7` → fails HIGH; `supports (3) >= contradicts (1)` → MED.

- [ ] **Step 3: Run test, expect failure**

```bash
bash tests/fixtures/dashboard/run.sh
```

Expected: personas card assertions FAIL.

- [ ] **Step 4: Implement `_card_personas`**

Insert after `_card_founders`:

```python
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
```

- [ ] **Step 5: Wire the card temporarily**

The personas card needs `inputs: PMFInputs | None`. In each render branch:
- `render_pmf_led`: change to `pre_main = callout + ribbon + (_card_founders(deal_dir) or "") + (_card_personas(deal_dir, inputs) or "")`
- `render_legacy`: pass `None` for inputs: `pre_main_html=callout + (_card_founders(deal_dir) or "") + (_card_personas(deal_dir, None) or "")`
- `render_markdown_fallback`: same as legacy: `... + (_card_personas(deal_dir, None) or "")`

- [ ] **Step 6: Add personas-only fixture handling — the renderer needs PyYAML installed**

Verify:
```bash
python3 -c "import yaml; print(yaml.__version__)"
```

Expected: any version ≥ 5.0. If missing: `pip install pyyaml`.

- [ ] **Step 7: Run test, expect pass**

```bash
bash tests/fixtures/dashboard/run.sh
```

Expected: personas card assertions PASS.

- [ ] **Step 8: Commit**

```bash
git add scripts/render-report.py tests/fixtures/dashboard/
git commit -m "Add Card 2: PMF Personas dashboard card"
```

---

## Task 5: Card 3 — Real Call Insights

**Files:**
- Modify: `scripts/render-report.py` (add `_card_calls`)
- Create: `tests/fixtures/dashboard/calls-only/calls/demo-validation.md`
- Create: `tests/fixtures/dashboard/calls-only/calls/demo-audit.json` (second call for count assertion)
- Modify: `tests/fixtures/dashboard/run.sh` (append assertions)

- [ ] **Step 1: Extend the calls-only fixture**

`tests/fixtures/dashboard/calls-only/calls/demo-validation.md`:
```markdown
# Demo callagent validation

| Demo flow | Result file | Status | Read |
|---|---|---:|---|
| Billing reconciliation | demo-billing.json | ended | Tester described 3-day close cost and conditional WTP. |
| Audit readiness | demo-audit.json | ended | Tester identified time cost around offshored audit/revenue-impacting work. |
```

`tests/fixtures/dashboard/calls-only/calls/demo-audit.json`:
```json
{
  "id": "demo-audit-test",
  "status": "ended",
  "endedReason": "customer-ended-call",
  "recording_url": "https://storage.vapi.ai/example2-stereo.wav",
  "structured_data": {}
}
```

(Note: the second call has empty `structured_data` — it should NOT count as a positive signal. Total calls = 2, positive = 1, % = 50.)

- [ ] **Step 2: Append failing assertions**

```bash
echo "[card-calls] renders for calls-only fixture"
python3 "$renderer" "$script_dir/calls-only" >/dev/null 2>&1
out="$(cat "$script_dir/calls-only/report.html")"
assert_contains "calls card present" 'class="dash-card dash-card-calls"' "$out"
assert_contains "calls completed = 2" 'data-calls-completed="2"' "$out"
assert_contains "positive signal = 50" 'data-positive-pct="50"' "$out"
assert_contains "waveform div" 'class="dash-waveform"' "$out"
assert_contains "wavesurfer init" "WaveSurfer.create" "$out"
assert_contains "pull-quote present" "3-day close cost" "$out"
assert_contains "read more anchor" 'href="#demo-call-validation"' "$out"
```

- [ ] **Step 3: Run test, expect failure**

```bash
bash tests/fixtures/dashboard/run.sh
```

Expected: calls card assertions FAIL.

- [ ] **Step 4: Implement `_card_calls`**

Insert after `_card_personas`:

```python
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
```

- [ ] **Step 5: Wire the card and embed wavesurfer init**

In `_build_html_skeleton`, change the script block to detect whether the calls card is present and emit wavesurfer init only then. Replace the existing `f"<script>{JS}</script>"` with:

```python
        + ("<script>" + WAVESURFER_JS + "</script>"
           if 'class="dash-card dash-card-calls"' in main_body_html or
              'class="dash-card dash-card-calls"' in pre_main_html
           else "")
        + f"<script>{JS}</script>"
        + ("<script>" + DASHBOARD_JS + "</script>"
           if 'class="dash-card dash-card-calls"' in main_body_html or
              'class="dash-card dash-card-calls"' in pre_main_html
           else "")
```

And add the `DASHBOARD_JS` constant immediately after the `JS = """..."""` constant:

```python
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
```

Wire `_card_calls` into the three render branches the same way the prior cards were wired. Each `pre_main` line gains:

```python
+ (_card_calls(deal_dir) or "")
```

- [ ] **Step 6: Run test, expect pass**

```bash
bash tests/fixtures/dashboard/run.sh
```

Expected: all calls card assertions PASS. Note: the test does not actually download audio (URL is fake), so `_ensure_local_recording` will fail with a stderr warning and the card falls back to streaming the URL — that's the path the assertion checks.

- [ ] **Step 7: Commit**

```bash
git add scripts/render-report.py tests/fixtures/dashboard/
git commit -m "Add Card 3: Real Call Insights with wavesurfer waveform"
```

---

## Task 6: Card 4 — Market Sizing

**Files:**
- Modify: `scripts/render-report.py` (add `_card_market`)
- Create: `tests/fixtures/dashboard/market-only/manifest.json`
- Create: `tests/fixtures/dashboard/market-only/market-sizing.md`
- Modify: `tests/fixtures/dashboard/run.sh` (append assertions)

- [ ] **Step 1: Create the market-only fixture**

`tests/fixtures/dashboard/market-only/manifest.json`:
```json
{
  "slug": "market-only",
  "company": "Market Only",
  "stage": "Watch",
  "generated": "2026-04-30T00:00:00Z",
  "skills": {}
}
```

`tests/fixtures/dashboard/market-only/market-sizing.md`:
```markdown
# Market sizing — Market Only

**Industry:** Fintech / B2B SaaS

## Bottom-up TAM

**Wedge TAM (year 1 reachable):** 200m – 320m
**Expansion TAM (3-year):** 1500m – 2400m
**Founder claim:** 12000m – 12500m

Growth rate: 18.4% CAGR (Source: Gartner Q1 2026).
```

- [ ] **Step 2: Append failing assertions**

```bash
echo "[card-market] renders for market-only fixture"
python3 "$renderer" "$script_dir/market-only" >/dev/null 2>&1
out="$(cat "$script_dir/market-only/report.html")"
assert_contains "market card present" 'class="dash-card dash-card-market"' "$out"
assert_contains "industry tag" "Fintech / B2B SaaS" "$out"
assert_contains "TAM upper" 'data-tam="2400"' "$out"
assert_contains "growth rate" 'data-cagr="18.4"' "$out"
assert_contains "read more anchor" 'href="#market-sizing"' "$out"
```

- [ ] **Step 3: Run test, expect failure**

```bash
bash tests/fixtures/dashboard/run.sh
```

- [ ] **Step 4: Implement `_card_market`**

Insert after `_card_calls`:

```python
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
```

- [ ] **Step 5: Wire the card**

Append `+ (_card_market(deal_dir, memo) or "")` to the three `pre_main` expressions. The variable `memo` already exists in each render function (`render_pmf_led`, `render_legacy`, `render_markdown_fallback`).

- [ ] **Step 6: Run test, expect pass**

```bash
bash tests/fixtures/dashboard/run.sh
```

- [ ] **Step 7: Commit**

```bash
git add scripts/render-report.py tests/fixtures/dashboard/
git commit -m "Add Card 4: Market Sizing dashboard card"
```

---

## Task 7: Card 5 — Competitive Landscape

**Files:**
- Modify: `scripts/render-report.py` (add `_card_competitors`)
- Create: `tests/fixtures/dashboard/competitors-only/manifest.json`
- Create: `tests/fixtures/dashboard/competitors-only/competitive-landscape.md`
- Create: `tests/fixtures/dashboard/competitors-only/MEMO.md`
- Modify: `tests/fixtures/dashboard/run.sh` (append assertions)

- [ ] **Step 1: Create the competitors-only fixture**

`tests/fixtures/dashboard/competitors-only/manifest.json`:
```json
{
  "slug": "competitors-only",
  "company": "Competitors Only",
  "stage": "Watch",
  "generated": "2026-04-30T00:00:00Z",
  "skills": {}
}
```

`tests/fixtures/dashboard/competitors-only/MEMO.md`:
```markdown
# MEMO — Competitors Only

## Recommendation

- **Verdict:** Watch
- **Market opportunity:** HIGH — large fragmented incumbent set
```

`tests/fixtures/dashboard/competitors-only/competitive-landscape.md`:
```markdown
# Competitive landscape

| Competitor | Wedge | Pricing | Moat |
|---|---|---|---|
| Stripe Billing | Full billing platform | $0 + 0.5% volume | Network |
| Maxio (formerly Chargify) | SaaS billing | seat | ICP fit |
| Tabs | Contract-to-cash | seat | API-first |
```

- [ ] **Step 2: Append failing assertions**

```bash
echo "[card-competitors] renders for competitors-only fixture"
python3 "$renderer" "$script_dir/competitors-only" >/dev/null 2>&1
out="$(cat "$script_dir/competitors-only/report.html")"
assert_contains "competitors card present" 'class="dash-card dash-card-competitors"' "$out"
assert_contains "competitor 1" "Stripe Billing" "$out"
assert_contains "competitor 2" "Maxio" "$out"
assert_contains "competitor 3" "Tabs" "$out"
assert_contains "opportunity HIGH" 'data-opportunity="HIGH"' "$out"
```

- [ ] **Step 3: Run test, expect failure**

```bash
bash tests/fixtures/dashboard/run.sh
```

- [ ] **Step 4: Implement `_card_competitors`**

Insert after `_card_market`:

```python
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
```

- [ ] **Step 5: Wire the card**

Append `+ (_card_competitors(deal_dir, memo) or "")` to each of the three `pre_main` expressions.

- [ ] **Step 6: Run test, expect pass**

```bash
bash tests/fixtures/dashboard/run.sh
```

- [ ] **Step 7: Commit**

```bash
git add scripts/render-report.py tests/fixtures/dashboard/
git commit -m "Add Card 5: Competitive Landscape dashboard card"
```

---

## Task 8: Dashboard composer + CSS + clean wire-in

**Files:**
- Modify: `scripts/render-report.py` (add `render_dashboard`, add `DASHBOARD_CSS`, replace ad-hoc card concatenation in three render branches with single composer call)
- Create: `tests/fixtures/dashboard/empty/manifest.json`
- Modify: `tests/fixtures/dashboard/run.sh` (append empty-deal assertion)
- Modify: `tests/fixtures/pmf-led-report/run.sh` (append dashboard assertions for `full` branch)

- [ ] **Step 1: Create the empty-deal fixture**

`tests/fixtures/dashboard/empty/manifest.json`:
```json
{
  "slug": "empty",
  "company": "Empty",
  "stage": "Watch",
  "generated": "2026-04-30T00:00:00Z",
  "skills": {}
}
```

- [ ] **Step 2: Append failing assertions for the composer**

To `tests/fixtures/dashboard/run.sh`:

```bash
echo "[dashboard] grid wrapper present when at least one card renders"
python3 "$renderer" "$script_dir/founders-only" >/dev/null 2>&1
out="$(cat "$script_dir/founders-only/report.html")"
assert_contains "dashboard wrapper" 'class="dashboard-grid"' "$out"

echo "[dashboard] no wrapper when zero cards render"
python3 "$renderer" "$script_dir/empty" >/dev/null 2>&1
out="$(cat "$script_dir/empty/report.html")"
assert_not_contains "no dashboard wrapper" 'dashboard-grid' "$out"
```

To `tests/fixtures/pmf-led-report/run.sh`, inside the `[full]` block (right after the existing recommendation-ribbon assertion):

```bash
assert_contains "dashboard grid in full branch" "dashboard-grid" "$out"
assert_contains "founders card in full branch" "dash-card-founders" "$out"
assert_contains "personas card in full branch" "dash-card-personas" "$out"
assert_contains "market card in full branch" "dash-card-market" "$out"
```

- [ ] **Step 3: Run tests, expect failures**

```bash
bash tests/fixtures/dashboard/run.sh
bash tests/fixtures/pmf-led-report/run.sh
```

Both should fail on the `dashboard-grid` assertions.

- [ ] **Step 4: Implement `render_dashboard`**

Insert immediately after `_card_competitors`:

```python
def render_dashboard(
    deal_dir: Path,
    memo_text: str | None,
    inputs: "PMFInputs | None",
) -> str:
    """Compose the 5-card dashboard. Returns "" if zero cards have data."""
    cards = [
        _card_founders(deal_dir),
        _card_personas(deal_dir, inputs),
        _card_calls(deal_dir),
        _card_market(deal_dir, memo_text),
        _card_competitors(deal_dir, memo_text),
    ]
    cards = [c for c in cards if c]
    if not cards:
        return ""
    return (
        '<section class="dashboard-wrap" aria-label="Executive summary">'
        '<div class="dashboard-grid">'
        + "".join(cards)
        + "</div></section>"
    )
```

- [ ] **Step 5: Replace ad-hoc concatenation with composer call**

In `render_pmf_led`:

Replace any earlier line of the form
```python
pre_main = callout + ribbon + (_card_founders(deal_dir) or "") + (_card_personas(deal_dir, inputs) or "") + (_card_calls(deal_dir) or "") + (_card_market(deal_dir, memo) or "") + (_card_competitors(deal_dir, memo) or "")
```
with:
```python
pre_main = callout + ribbon + render_dashboard(deal_dir, memo, inputs)
```

In `render_legacy`, change the `_build_html_skeleton` call's `pre_main_html` argument back to:
```python
pre_main_html=callout + render_dashboard(deal_dir, memo, None),
```

In `render_markdown_fallback`, do the same.

- [ ] **Step 6: Add `DASHBOARD_CSS`**

Insert this constant immediately after the existing `CSS = """..."""` (around line 1099) and before the `JS = """..."""` constant:

```python
DASHBOARD_CSS = """
.dashboard-wrap { margin: 1.25rem 2rem 1rem; padding: 1.5rem; border: 1px solid var(--line); border-radius: 20px; background: linear-gradient(180deg, #ffffff, #fbfbff); }
.dashboard-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); grid-auto-flow: dense; gap: 16px; }
.dash-card { background: #ffffff; border-radius: 16px; padding: 1.1rem 1.2rem; box-shadow: 0 1px 2px rgba(15,23,42,0.06), 0 8px 24px rgba(80,72,229,0.06); display: flex; flex-direction: column; min-width: 0; }
.dash-card-market { grid-column: span 2; }
.dash-card-head { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.65rem; }
.dash-card-head h3 { font-family: system-ui, -apple-system, sans-serif; font-size: 0.95rem; margin: 0; padding: 0; border: none; color: #0f172a; }
.dash-num { display: inline-flex; align-items: center; justify-content: center; width: 1.6rem; height: 1.6rem; background: #7c5cff; color: #fff; font-weight: 700; font-size: 0.85rem; border-radius: 8px; }
.dash-card-body { flex: 1; font-size: 0.88rem; color: #1f2937; }
.dash-card-foot { margin-top: 0.85rem; padding-top: 0.65rem; border-top: 1px dashed var(--line); display: flex; align-items: center; gap: 0.55rem; flex-wrap: wrap; font-size: 0.82rem; }
.dash-card-foot .dash-label { font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
.dash-more { margin-left: auto; color: #7c5cff; font-weight: 600; }
.dash-pill { display: inline-block; padding: 0.18rem 0.6rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; }
.dash-pill.ok { background: #dcfce7; color: #166534; }
.dash-pill.watch { background: #fef3c7; color: #92400e; }
.dash-pill.risk { background: #fee2e2; color: #991b1b; }
.dash-pill.muted { background: #f3f4f6; color: #4b5563; }
.dash-pill-row { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.6rem; }
.dash-personas-split { display: grid; grid-template-columns: 1.4fr 1fr; gap: 0.85rem; align-items: center; }
.dash-bars { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.35rem; }
.dash-bar-row { display: grid; grid-template-columns: 1fr; gap: 0.2rem; font-size: 0.78rem; }
.dash-bar-label { color: #374151; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dash-bar { display: block; height: 6px; background: #e5e7eb; border-radius: 3px; overflow: hidden; }
.dash-bar-fill { display: block; height: 100%; background: #7c5cff; border-radius: 3px; }
.dash-score { text-align: center; font-family: Georgia, serif; }
.dash-score-num { font-size: 2.1rem; font-weight: 600; color: #16a34a; }
.dash-score-denom { font-size: 1rem; color: var(--muted); margin-left: 0.15rem; }
.dash-score-label { display: block; font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-top: 0.1rem; }
.dash-score.dash-empty { font-family: system-ui, sans-serif; color: var(--muted); font-style: italic; }
.dash-founder-row { display: flex; align-items: center; gap: 0.55rem; text-decoration: none; color: inherit; margin-bottom: 0.35rem; }
.dash-founder-row:hover { text-decoration: none; }
.dash-founder-name { font-weight: 600; color: #0f172a; }
.dash-avatar { display: inline-flex; align-items: center; justify-content: center; width: 2rem; height: 2rem; border-radius: 50%; color: #fff; font-weight: 700; font-size: 0.75rem; }
.dash-badges { list-style: none; margin: 0 0 0.45rem 0; padding: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 0.15rem 0.6rem; font-size: 0.78rem; }
.dash-badge { display: flex; align-items: center; gap: 0.25rem; }
.dash-badge.ok { color: #166534; }
.dash-badge.muted { color: #9ca3af; }
.dash-badge .dash-mark { font-weight: 700; }
.dash-row { display: flex; align-items: baseline; justify-content: space-between; gap: 0.6rem; padding: 0.25rem 0; border-bottom: 1px dashed var(--line); }
.dash-row:last-child { border-bottom: none; }
.dash-row .dash-label { font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
.dash-row .dash-value { font-weight: 600; color: #0f172a; }
.dash-waveform { width: 100%; min-height: 56px; background: #f8fafc; border-radius: 8px; margin-bottom: 0.5rem; }
.dash-waveform.dash-empty { display: flex; align-items: center; justify-content: center; color: var(--muted); font-style: italic; font-size: 0.85rem; }
.dash-audio { width: 100%; margin-bottom: 0.6rem; }
.dash-metrics-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; margin: 0.5rem 0 0.6rem; }
.dash-metric { display: flex; flex-direction: column; }
.dash-metric-label { font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
.dash-metric-num { font-family: Georgia, serif; font-size: 1.5rem; color: #16a34a; font-weight: 600; }
.dash-quote { margin: 0; padding: 0.5rem 0.7rem; border-left: 3px solid #7c5cff; background: #f5f3ff; border-radius: 4px; font-size: 0.82rem; color: #4c1d95; font-style: italic; }
.dash-empty { color: var(--muted); font-style: italic; }

@media (max-width: 900px) {
  .dashboard-wrap { margin: 1rem 1rem; padding: 1rem; }
  .dashboard-grid { grid-template-columns: 1fr; }
  .dash-card-market { grid-column: auto; }
  .dash-personas-split { grid-template-columns: 1fr; }
}
""".strip()
```

- [ ] **Step 7: Inline `DASHBOARD_CSS` into the page CSS**

In `_build_html_skeleton`, find `f"<style>{CSS}</style>"` and replace with:

```python
        f"<style>{CSS}\n{DASHBOARD_CSS}</style>"
```

- [ ] **Step 8: Run all tests, expect pass**

```bash
bash tests/fixtures/dashboard/run.sh
bash tests/fixtures/pmf-led-report/run.sh
```

Expected: all assertions PASS in both.

- [ ] **Step 9: Commit**

```bash
git add scripts/render-report.py tests/fixtures/dashboard/ tests/fixtures/pmf-led-report/run.sh
git commit -m "Compose 5-card dashboard via render_dashboard()"
```

---

## Task 9: End-to-end verification

**Files:**
- (no code changes)
- Verify: `deals/dimely/report.html`, `deals/callagent/report.html`, all fixture outputs.

- [ ] **Step 1: Re-render the dimely deal**

```bash
python3 scripts/render-report.py deals/dimely 2>&1 | tee /tmp/dimely-render.log
```

Expected: exit 0. The log may include `warning: could not download recording for ...` lines if `storage.vapi.ai` URLs have rotated — that is expected and the report still renders. If the URLs are still live, you'll see no warnings and `deals/dimely/calls/recordings/*.wav` files will appear.

Verify the dashboard exists:
```bash
grep -c "dashboard-grid" deals/dimely/report.html
grep -c "dash-card-" deals/dimely/report.html
```

Expected: at least 1 grid wrapper, 5+ card hits (one per card).

- [ ] **Step 2: Re-render the callagent deal**

```bash
python3 scripts/render-report.py deals/callagent
grep -c "dashboard-grid" deals/callagent/report.html || echo "no dashboard"
```

Expected: callagent has only `idea-validation.md`, `market-map.md`, `manifest.json`, candidates — no founder, personas, calls, market, or competitors files. Result: dashboard returns empty, output: `no dashboard`. The existing legacy report renders unchanged.

- [ ] **Step 3: Run the full test suite**

```bash
bash tests/fixtures/dashboard/run.sh
bash tests/fixtures/pmf-led-report/run.sh
bash tests/lint/run.sh 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 4: Open dimely report.html in a browser and visually inspect**

```bash
open deals/dimely/report.html  # macOS
```

Visual checklist:
- [ ] Dashboard grid appears between the recommendation ribbon and the TOC.
- [ ] Numbered chips (1–5) match mockup style.
- [ ] Founders card shows initials avatars and badges.
- [ ] Personas card shows fit score in violet/green and consensus pill.
- [ ] Calls card shows a waveform that animates when you press the audio play button (if recordings downloaded).
- [ ] Market card shows industry tag, TAM, CAGR.
- [ ] Competitors card shows top 3 with bars.
- [ ] Click any "Read more →" link — page scrolls to the corresponding section, TOC entry highlights.
- [ ] On mobile (resize to <900px), cards stack single-column.

- [ ] **Step 5: Update `dimely/report.html` checkin if it's tracked**

```bash
git status deals/dimely/report.html deals/callagent/report.html
```

If they're already tracked in git, the regenerated versions are fine to commit. If they're untracked / gitignored, no action.

- [ ] **Step 6: Final commit (only if there are tracked-file changes)**

```bash
git add deals/dimely/report.html deals/callagent/report.html  # only if tracked
git commit -m "Regenerate sample reports with dashboard" || echo "nothing to commit"
```

---

## Self-review notes

- **Spec coverage:** Each spec section maps to a task: §Architecture → Task 8; §Card 1–5 → Tasks 3–7; §Audio download → Task 2; §Wavesurfer embedding → Tasks 1, 5; §Visual style → Task 8 step 6; §Wikipedia-style references → no code change needed (existing `<details>`/anchors already work, dashboard "Read more" anchors hit existing IDs).
- **Type consistency:** `_card_*` helpers all return `str | None`. `render_dashboard` returns `str` (empty string when no cards). `_ensure_local_recording` returns `Path | None`. `PMFInputs | None` is the type for personas card; `inputs` already exists in `render_pmf_led`; we pass `None` in `render_legacy` and `render_markdown_fallback`.
- **No placeholders:** all helper bodies are full code; all CSS classes used in helpers are defined in `DASHBOARD_CSS`; all anchor IDs (`#ledger`, `#market-sizing`, `#competitive-landscape`, `#demo-call-validation`, `#founder-<slug>`) exist in the existing renderer output.
- **Out of plan scope (deferred per spec):** real audio waveform pre-computation server-side, founder photo fetching, threat-scoring competitors from text, multi-deal index, manifest fields for stage/industry.
