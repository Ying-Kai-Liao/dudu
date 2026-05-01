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

echo "[card-personas] renders for personas-only fixture"
python3 "$renderer" "$script_dir/personas-only" >/dev/null 2>&1
out="$(cat "$script_dir/personas-only/report.html")"
assert_contains "personas card present" 'class="dash-card dash-card-personas"' "$out"
assert_contains "trigger pill 1" 'contract-exception' "$out"
assert_contains "trigger pill 2" 'billing-reconciliation' "$out"
assert_contains "fit score 6.7" 'data-fit-score="6.7"' "$out"
assert_contains "consensus pill MED" 'data-consensus="MED"' "$out"

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

echo
if [[ $fail -eq 0 ]]; then
    echo "OK — all dashboard fixtures pass"
    exit 0
else
    echo "FAIL — see above"
    exit 1
fi
