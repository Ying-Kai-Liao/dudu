#!/usr/bin/env bash
# Integration tests for scripts/fleet-run.py + scripts/render-dashboard.py.
#
# These tests cover the orchestration glue (manifest + queue + slug
# validation + budget + dashboard) against synthetic fixtures. They do
# NOT invoke the heavy LLM-driven sub-skills (dudu:background-check /
# dudu:pmf-signal) — those are exercised by manual end-to-end QA against
# real deals; here we drive the manifest with explicit `mark` calls to
# simulate sub-skill outcomes.
set -u

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fleet_py="$repo_root/scripts/fleet-run.py"
dashboard_py="$repo_root/scripts/render-dashboard.py"
fail=0

assert_eq() {
    local name="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        echo "  expected: $expected"
        echo "  actual:   $actual"
        fail=1
    fi
}

assert_contains() {
    local name="$1" needle="$2" haystack="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        echo "  expected substring: $needle"
        echo "  in: $haystack"
        fail=1
    fi
}

assert_file_exists() {
    local name="$1" path="$2"
    if [[ -f "$path" ]]; then
        echo "PASS: $name"
    else
        echo "FAIL: $name (missing file: $path)"
        fail=1
    fi
}

mk_workspace() {
    local ws
    ws="$(mktemp -d 2>/dev/null || mktemp -d -t fleet-run)"
    mkdir -p "$ws/deals/alpha" "$ws/deals/beta" "$ws/deals/_archive"
    cat >"$ws/deals/alpha/manifest.json" <<EOF
{ "slug": "alpha", "company": "Alpha Co" }
EOF
    cat >"$ws/deals/beta/manifest.json" <<EOF
{ "slug": "beta", "company": "Beta Co" }
EOF
    echo "$ws"
}

# --- Test 1: no input source = exit 2 with the three options listed ----
ws="$(mk_workspace)"
out="$(cd "$ws" && python3 "$fleet_py" init 2>&1; echo "EXIT=$?")"
assert_contains "no-input-source error message" "no fleet input source provided" "$out"
assert_contains "no-input-source exit 2" "EXIT=2" "$out"
assert_contains "no-input-source mentions --slugs" "--slugs" "$out"
assert_contains "no-input-source mentions --auto" "--auto" "$out"
assert_contains "no-input-source mentions queue.txt" "queue.txt" "$out"
rm -rf "$ws"

# --- Test 2: underscore-prefixed slug rejects whole run ----
ws="$(mk_workspace)"
out="$(cd "$ws" && python3 "$fleet_py" init --slugs _archive,beta 2>&1; echo "EXIT=$?")"
assert_contains "underscore-slug exit 2" "EXIT=2" "$out"
assert_contains "underscore-slug error mentions reserved" "reserved" "$out"
if [[ -f "$ws/deals/_fleet/manifest.json" ]]; then
    echo "FAIL: underscore-slug must not write manifest"
    fail=1
else
    echo "PASS: underscore-slug must not write manifest"
fi
rm -rf "$ws"

# --- Test 3: invalid kebab-case rejects whole run ----
ws="$(mk_workspace)"
out="$(cd "$ws" && python3 "$fleet_py" init --slugs Alpha,beta 2>&1; echo "EXIT=$?")"
assert_contains "invalid-kebab exit 2" "EXIT=2" "$out"
assert_contains "invalid-kebab message" "kebab-case" "$out"
rm -rf "$ws"

# --- Test 4: --auto enrolls non-underscore directories only ----
ws="$(mk_workspace)"
out="$(cd "$ws" && python3 "$fleet_py" init --auto 2>&1; echo "EXIT=$?")"
assert_contains "auto exit 0" "EXIT=0" "$out"
queue="$(python3 -c "import json; print(','.join(json.load(open('$ws/deals/_fleet/manifest.json'))['queue']))")"
assert_eq "auto enrolls alpha,beta" "alpha,beta" "$queue"
rm -rf "$ws"

# --- Test 5: missing deal directory marks slug failed but continues ----
ws="$(mk_workspace)"
(cd "$ws" && python3 "$fleet_py" init --slugs alpha,nope >/dev/null 2>&1)
alpha_status="$(python3 -c "import json; print(json.load(open('$ws/deals/_fleet/manifest.json'))['per_deal']['alpha']['status'])")"
nope_status="$(python3 -c "import json; print(json.load(open('$ws/deals/_fleet/manifest.json'))['per_deal']['nope']['status'])")"
assert_eq "missing-dir alpha pending" "pending" "$alpha_status"
assert_eq "missing-dir nope failed" "failed" "$nope_status"
rm -rf "$ws"

# --- Test 6: queue.txt parsing ignores blanks and comments ----
ws="$(mk_workspace)"
mkdir -p "$ws/deals/_fleet"
cat >"$ws/deals/_fleet/queue.txt" <<EOF
# this is a comment
alpha

# another comment
beta
EOF
(cd "$ws" && python3 "$fleet_py" init >/dev/null 2>&1)
queue="$(python3 -c "import json; print(','.join(json.load(open('$ws/deals/_fleet/manifest.json'))['queue']))")"
assert_eq "queue-file parses alpha,beta" "alpha,beta" "$queue"
rm -rf "$ws"

# --- Test 7: --slugs overrides queue file ----
ws="$(mk_workspace)"
mkdir -p "$ws/deals/_fleet"
cat >"$ws/deals/_fleet/queue.txt" <<EOF
alpha
beta
EOF
mkdir -p "$ws/deals/x" "$ws/deals/y"
(cd "$ws" && python3 "$fleet_py" init --slugs x,y >/dev/null 2>&1)
queue="$(python3 -c "import json; print(','.join(json.load(open('$ws/deals/_fleet/manifest.json'))['queue']))")"
assert_eq "--slugs overrides queue.txt" "x,y" "$queue"
rm -rf "$ws"

# --- Test 8: pmf-only mode without L1 sentinel marks slug failed up front --
ws="$(mk_workspace)"
(cd "$ws" && python3 "$fleet_py" init --slugs alpha --mode pmf-only >/dev/null 2>&1)
alpha_status="$(python3 -c "import json; print(json.load(open('$ws/deals/_fleet/manifest.json'))['per_deal']['alpha']['status'])")"
err="$(python3 -c "import json; print(json.load(open('$ws/deals/_fleet/manifest.json'))['per_deal']['alpha']['error_summary'])")"
assert_eq "pmf-only without L1 fails" "failed" "$alpha_status"
assert_contains "pmf-only error mentions background.md" "background.md" "$err"
rm -rf "$ws"

# --- Test 9: pmf-only mode WITH L1 sentinel succeeds at init ----
ws="$(mk_workspace)"
touch "$ws/deals/alpha/background.md"
(cd "$ws" && python3 "$fleet_py" init --slugs alpha --mode pmf-only >/dev/null 2>&1)
alpha_status="$(python3 -c "import json; print(json.load(open('$ws/deals/_fleet/manifest.json'))['per_deal']['alpha']['status'])")"
phase_keys="$(python3 -c "import json; print(','.join(sorted(json.load(open('$ws/deals/_fleet/manifest.json'))['per_deal']['alpha']['phases'].keys())))")"
assert_eq "pmf-only with L1 pending" "pending" "$alpha_status"
assert_eq "pmf-only schedules pmf-signal phase only" "pmf-signal" "$phase_keys"
rm -rf "$ws"

# --- Test 10: budget cap exceed → budget-check exits 1 ----
ws="$(mk_workspace)"
(cd "$ws" && python3 "$fleet_py" init --slugs alpha --max-tokens 100 >/dev/null 2>&1)
(cd "$ws" && python3 "$fleet_py" add-tokens 200 >/dev/null 2>&1)
(cd "$ws" && python3 "$fleet_py" budget-check >/dev/null 2>&1)
ec=$?
assert_eq "budget-check exit 1 when exceeded" "1" "$ec"
# And it exits 0 when within budget.
ws2="$(mk_workspace)"
(cd "$ws2" && python3 "$fleet_py" init --slugs alpha --max-tokens 1000 >/dev/null 2>&1)
(cd "$ws2" && python3 "$fleet_py" add-tokens 50 >/dev/null 2>&1)
(cd "$ws2" && python3 "$fleet_py" budget-check >/dev/null 2>&1)
ec=$?
assert_eq "budget-check exit 0 within cap" "0" "$ec"
rm -rf "$ws" "$ws2"

# --- Test 11: phase-aware mark + terminal status rollup (--all mode) ----
ws="$(mk_workspace)"
(cd "$ws" && python3 "$fleet_py" init --slugs alpha --mode all >/dev/null 2>&1)
(cd "$ws" && python3 "$fleet_py" mark alpha running --phase background-check >/dev/null 2>&1)
(cd "$ws" && python3 "$fleet_py" mark alpha complete --phase background-check >/dev/null 2>&1)
top="$(python3 -c "import json; print(json.load(open('$ws/deals/_fleet/manifest.json'))['per_deal']['alpha']['status'])")"
assert_eq "all-mode top status pending after L1 only" "pending" "$top"
(cd "$ws" && python3 "$fleet_py" mark alpha complete --phase pmf-signal >/dev/null 2>&1)
top="$(python3 -c "import json; print(json.load(open('$ws/deals/_fleet/manifest.json'))['per_deal']['alpha']['status'])")"
assert_eq "all-mode top status complete after both phases" "complete" "$top"
rm -rf "$ws"

# --- Test 12: failed L1 prevents L2 (top status stays failed) ----
ws="$(mk_workspace)"
(cd "$ws" && python3 "$fleet_py" init --slugs alpha --mode all >/dev/null 2>&1)
(cd "$ws" && python3 "$fleet_py" mark alpha failed --phase background-check --error "boom" >/dev/null 2>&1)
top="$(python3 -c "import json; print(json.load(open('$ws/deals/_fleet/manifest.json'))['per_deal']['alpha']['status'])")"
assert_eq "failed L1 → top status failed" "failed" "$top"
rm -rf "$ws"

# --- Test 13: per-slug log file is truncated at init ----
ws="$(mk_workspace)"
mkdir -p "$ws/deals/_fleet/logs"
echo "leftover from previous run" >"$ws/deals/_fleet/logs/alpha.log"
(cd "$ws" && python3 "$fleet_py" init --slugs alpha >/dev/null 2>&1)
log_size="$(wc -c <"$ws/deals/_fleet/logs/alpha.log" | tr -d ' ')"
assert_eq "log truncated to 0 at init" "0" "$log_size"
rm -rf "$ws"

# --- Test 14: dashboard renderer is idempotent ----
ws="$(mk_workspace)"
(cd "$ws" && python3 "$fleet_py" init --slugs alpha,beta >/dev/null 2>&1)
(cd "$ws" && python3 "$dashboard_py" >/dev/null 2>&1)
cp "$ws/deals/_fleet/dashboard.html" "$ws/dash1.html"
(cd "$ws" && python3 "$dashboard_py" >/dev/null 2>&1)
if diff -q "$ws/dash1.html" "$ws/deals/_fleet/dashboard.html" >/dev/null; then
    echo "PASS: dashboard idempotent"
else
    echo "FAIL: dashboard not idempotent"
    fail=1
fi
rm -rf "$ws"

# --- Test 15: dashboard shows fleet-in-progress footer when slugs running --
ws="$(mk_workspace)"
(cd "$ws" && python3 "$fleet_py" init --slugs alpha,beta >/dev/null 2>&1)
(cd "$ws" && python3 "$fleet_py" mark alpha running --phase background-check >/dev/null 2>&1)
(cd "$ws" && python3 "$dashboard_py" >/dev/null 2>&1)
if grep -q "Fleet in progress" "$ws/deals/_fleet/dashboard.html"; then
    echo "PASS: dashboard footer notes fleet in progress"
else
    echo "FAIL: dashboard missing fleet-in-progress footer"
    fail=1
fi
rm -rf "$ws"

# --- Test 16: dashboard slug column links to per-deal report.html ----
ws="$(mk_workspace)"
(cd "$ws" && python3 "$fleet_py" init --slugs alpha >/dev/null 2>&1)
(cd "$ws" && python3 "$fleet_py" mark alpha complete --phase background-check >/dev/null 2>&1)
(cd "$ws" && python3 "$dashboard_py" >/dev/null 2>&1)
if grep -q '<a href="../alpha/report.html">alpha</a>' "$ws/deals/_fleet/dashboard.html"; then
    echo "PASS: dashboard slug links to per-deal report"
else
    echo "FAIL: dashboard slug link missing"
    fail=1
fi
rm -rf "$ws"

# --- Test 17: dashboard renders against real fixture deals ----
# Uses the committed deals/ledgerloop, deals/callagent, deals/tiny so we
# exercise the cell extractors against real artifacts.
if [[ -d "$repo_root/deals/ledgerloop" && -d "$repo_root/deals/callagent" && -d "$repo_root/deals/tiny" ]]; then
    ws="$(mktemp -d 2>/dev/null || mktemp -d -t fleet-run)"
    cp -R "$repo_root/deals" "$ws/deals"
    rm -rf "$ws/deals/_fleet"
    (cd "$ws" && python3 "$fleet_py" init --slugs ledgerloop,callagent,tiny >/dev/null 2>&1)
    for slug in ledgerloop callagent tiny; do
        (cd "$ws" && python3 "$fleet_py" mark "$slug" complete --phase background-check >/dev/null 2>&1)
    done
    (cd "$ws" && python3 "$dashboard_py" >/dev/null 2>&1)
    assert_file_exists "fixture dashboard exists" "$ws/deals/_fleet/dashboard.html"
    if grep -q "LedgerLoop" "$ws/deals/_fleet/dashboard.html"; then
        echo "PASS: fixture dashboard contains LedgerLoop company"
    else
        echo "FAIL: fixture dashboard missing LedgerLoop"
        fail=1
    fi
    rm -rf "$ws"
else
    echo "SKIP: fixture deals not present (deals/ledgerloop, deals/callagent, deals/tiny)"
fi

if [[ "$fail" -ne 0 ]]; then
    echo "FAIL: fleet-run tests had failures"
    exit 1
fi
echo "OK: all fleet-run tests passed"
exit 0
