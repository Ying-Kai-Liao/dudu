#!/usr/bin/env bash
set -u
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fail=0

run_preflight_case() {
    local name="$1"
    local extra_args="${2:-}"
    local fixture="$script_dir/fixtures/$name"
    local expected="$script_dir/expected/$name.txt"
    local actual
    actual="$(python3 "$script_dir/../../scripts/pmf-signal-preflight.py" "$fixture" $extra_args 2>&1; echo "EXIT=$?")"
    local expected_contents
    expected_contents="$(cat "$expected")"
    if [[ "$actual" == "$expected_contents" ]]; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        echo "--- expected ---"
        echo "$expected_contents"
        echo "--- actual ---"
        echo "$actual"
        echo "--- end ---"
        fail=1
    fi
}

run_preflight_case preflight-good
run_preflight_case preflight-missing
run_preflight_case preflight-already-done

run_yaml_case() {
    local name="$1"
    local script="$2"
    local fixture="$script_dir/fixtures-yaml/$name.yaml"
    local expected="$script_dir/expected/$script-${name#pitch-}.txt"
    local actual
    actual="$(python3 "$script_dir/../../scripts/pmf-signal-$script.py" "$fixture" 2>&1; echo "EXIT=$?")"
    local expected_contents
    expected_contents="$(cat "$expected")"
    if [[ "$actual" == "$expected_contents" ]]; then
        echo "PASS: $script-$name"
    else
        echo "FAIL: $script-$name"
        echo "--- expected ---"
        echo "$expected_contents"
        echo "--- actual ---"
        echo "$actual"
        echo "--- end ---"
        fail=1
    fi
}

run_yaml_case pitch-good validate-pitch
run_yaml_case pitch-missing-fields validate-pitch
run_yaml_case pitch-bad-method validate-pitch

run_yaml_case seeds-good mode-collapse
run_yaml_case seeds-collapsed mode-collapse

exit "$fail"
