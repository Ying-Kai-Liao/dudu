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
run_preflight_case preflight-legacy
run_preflight_case preflight-no-deck

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

run_recipe_case() {
    local recipe="$1"
    local fixture_name="$2"
    local fixture_dir="$script_dir/fixtures-recipes/$fixture_name"
    local label="recipe-$recipe-${fixture_name#${recipe}-html-}"
    local expected="$script_dir/expected/recipe-$recipe-${fixture_name#${recipe}-html-}.txt"
    local module_name="${recipe//-/_}"
    local actual
    actual="$(python3 -c "
import importlib.util, sys
from pathlib import Path
recipes_dir = Path('$script_dir/../../scripts/pmf-signal-recipes')
sys.path.insert(0, str(recipes_dir))
spec = importlib.util.spec_from_file_location('_pmf_recipe_${module_name}', recipes_dir / '${module_name}.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
htmls = []
for p in sorted(Path('$fixture_dir').glob('*.html')):
    htmls.append(p.read_text(encoding='utf-8'))
print(mod.run(htmls))
" 2>&1; echo "EXIT=$?")"
    local expected_contents
    expected_contents="$(cat "$expected")"
    if [[ "$actual" == "$expected_contents" ]]; then
        echo "PASS: $label"
    else
        echo "FAIL: $label"
        echo "--- expected ---"
        echo "$expected_contents"
        echo "--- actual ---"
        echo "$actual"
        echo "--- end ---"
        fail=1
    fi
}

run_recipe_case customer-list customer-list-html-good
run_recipe_case testimonial-count testimonial-count-html-good
run_recipe_case wayback-history wayback-history-html-good

run_dir_case() {
    local name="$1"
    local script="$2"
    local fixture="$script_dir/fixtures-yaml/$name"
    local expected="$script_dir/expected/$name.txt"
    local actual
    actual="$(python3 "$script_dir/../../scripts/pmf-signal-$script.py" "$fixture" 2>&1; echo "EXIT=$?")"
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
    if [[ "$name" == "consolidate-good" ]]; then
        local parse_actual
        parse_actual="$(python3 - "$script_dir/../../scripts/pmf-signal-validate-pitch.py" "$fixture/personas/verdicts.yaml" <<'PY'
import importlib.util
import sys
from pathlib import Path

validator = Path(sys.argv[1])
verdicts = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("_pmf_validate", validator)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)
doc = mod.parse_yaml_subset(verdicts.read_text(encoding="utf-8"))
print(f"parsed {len(doc.get('verdicts') or [])} verdict(s)")
PY
)"
        if [[ "$parse_actual" == "parsed 4 verdict(s)" ]]; then
            echo "PASS: $name parseable-verdicts"
        else
            echo "FAIL: $name parseable-verdicts"
            echo "--- actual ---"
            echo "$parse_actual"
            echo "--- end ---"
            fail=1
        fi
    fi
    rm -f "$fixture/personas/aggregates.yaml" "$fixture/personas/verdicts.yaml"
}

run_dir_case consolidate-good consolidate-verdicts
run_dir_case aggregate-good aggregate

run_render_report_case() {
    local name="$1"
    local fixture="$script_dir/fixtures-yaml/$name"
    local expected="$script_dir/expected/$name.md"
    python3 "$script_dir/../../scripts/pmf-signal-render-report.py" "$fixture" >/dev/null
    local actual_path="$fixture/pmf-signal.md"
    if [[ ! -f "$actual_path" ]]; then
        echo "FAIL: $name (no output written)"
        fail=1
        return
    fi
    local norm_expected norm_actual
    norm_expected="$(sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z?/<ISO_TIMESTAMP>/g' "$expected")"
    norm_actual="$(sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z?/<ISO_TIMESTAMP>/g' "$actual_path")"
    if [[ "$norm_expected" == "$norm_actual" ]]; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        diff <(echo "$norm_expected") <(echo "$norm_actual") | head -40
        fail=1
    fi
    rm -f "$actual_path"
}

run_render_report_case render-report-good

run_outreach_case() {
    local name="$1"
    local fixture="$script_dir/fixtures-yaml/$name"
    local expected_outreach="$script_dir/expected/$name.outreach.md"
    local expected_cdp="$script_dir/expected/$name.cdp.md"
    python3 "$script_dir/../../scripts/pmf-signal-render-outreach.py" "$fixture" >/dev/null
    local fail_local=0
    for pair in "outreach.md:$expected_outreach" "customer-discovery-prep.md:$expected_cdp"; do
        local actual_name="${pair%%:*}"
        local expected_path="${pair#*:}"
        local actual_path="$fixture/$actual_name"
        if [[ ! -f "$actual_path" ]]; then
            echo "FAIL: $name ($actual_name not written)"
            fail_local=1
            continue
        fi
        local norm_expected norm_actual
        norm_expected="$(sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z?/<ISO_TIMESTAMP>/g' "$expected_path")"
        norm_actual="$(sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z?/<ISO_TIMESTAMP>/g' "$actual_path")"
        if [[ "$norm_expected" != "$norm_actual" ]]; then
            echo "FAIL: $name ($actual_name diff)"
            diff <(echo "$norm_expected") <(echo "$norm_actual") | head -40
            fail_local=1
        fi
        rm -f "$actual_path"
    done
    if [[ $fail_local -eq 0 ]]; then
        echo "PASS: $name"
    else
        fail=1
    fi
}

run_outreach_case render-outreach-good

exit "$fail"
