#!/usr/bin/env bash
set -u
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
linter="$script_dir/../../scripts/lint-skills.sh"
fail=0

run_case() {
    local name="$1"
    local fixture="$script_dir/fixtures/$name"
    local expected="$script_dir/expected/$name.txt"
    local actual
    actual="$(cd "$fixture" && "$linter" 2>&1)"
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

run_case good
run_case missing-name
run_case duplicate-names
run_case broken-libref

exit "$fail"
