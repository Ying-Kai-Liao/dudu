#!/usr/bin/env bash
# Smoke tests for the four input-shape branches of scripts/render-report.py.
# Each fixture asserts on a small set of HTML/stderr signals — not byte-for-byte
# equality — so the tests survive small CSS/markup tweaks.
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

run_branch() {
    local fixture="$1"
    local stderr_file
    stderr_file="$(mktemp)"
    python3 "$renderer" "$script_dir/$fixture" >/dev/null 2>"$stderr_file"
    local rc=$?
    local html
    html="$(cat "$script_dir/$fixture/report.html" 2>/dev/null || echo "")"
    local stderr
    stderr="$(cat "$stderr_file")"
    rm -f "$stderr_file"
    echo "exit=$rc"
    echo "$html"
    echo "STDERR:$stderr"
}

echo "[full] full pmf-signal output"
out="$(run_branch full)"
assert_contains "exit 0" "exit=0" "$out"
assert_contains "ledger section" "<section id=\"ledger\"" "$out"
assert_contains "contradictions section" "<section id=\"contradictions\"" "$out"
assert_contains "outreach section" "<section id=\"outreach\"" "$out"
assert_contains "recommendation ribbon" "recommendation-ribbon" "$out"
assert_contains "dashboard grid in full branch" "dashboard-grid" "$out"
assert_contains "founders card in full branch" "dash-card-founders" "$out"
assert_contains "personas card in full branch" "dash-card-personas" "$out"
assert_contains "market card in full branch" "dash-card-market" "$out"
assert_contains "stance B caption" "Calibrated prior, not signal" "$out"
assert_contains "persona-reaction badge" "method-badge persona-reaction" "$out"
assert_contains "cross-artifact badge" "method-badge cross-artifact" "$out"
assert_contains "verdict-strip" "verdict-strip" "$out"
assert_contains "founder background first section" "<section id=\"founder-sample-founder\" class=\"report-section\"><h2>Founder Background: Sample Founder</h2>" "$out"
assert_not_contains "no TL;DR section" "TL;DR" "$out"
assert_not_contains "no persona _context open" "details id=\"persona--context\" data-toc-target open" "$out"
assert_not_contains "no stderr warning" "warning:" "$out"

echo "[pitch-only] pmf-signal incomplete"
out="$(run_branch pitch-only)"
assert_contains "exit 0" "exit=0" "$out"
assert_contains "stderr names verdicts.yaml" "verdicts.yaml is missing" "$out"
assert_contains "stderr names branch" "pitch-only" "$out"
assert_contains "ledger section" "<section id=\"ledger\"" "$out"
assert_contains "all rows pending" "verdict-badge pending" "$out"
assert_contains "PMF run incomplete note" "PMF run incomplete" "$out"
assert_not_contains "no real contradictions entry" "<div class=\"contradiction-entry\"" "$out"

echo "[md-fallback] only pmf-signal.md present"
out="$(run_branch md-fallback)"
assert_contains "exit 0" "exit=0" "$out"
assert_contains "stderr names branch" "markdown-fallback" "$out"
assert_contains "pmf-signal section" "<section id=\"pmf-signal\"" "$out"
assert_not_contains "no ledger section" "<section id=\"ledger\"" "$out"
assert_not_contains "no contradictions section" "<section id=\"contradictions\"" "$out"

echo "[malformed-yaml] invalid pitch.yaml"
out="$(run_branch malformed-yaml)"
assert_contains "exit 0" "exit=0" "$out"
assert_contains "stderr names parse error" "could not parse" "$out"
assert_contains "fallback to legacy or markdown branch" "<header class=\"report\">" "$out"
assert_not_contains "no ledger section (no valid pitch)" "<section id=\"ledger\"" "$out"

echo
if [[ $fail -eq 0 ]]; then
    echo "OK — all pmf-led-report fixtures pass"
    exit 0
else
    echo "FAIL — see above"
    exit 1
fi
