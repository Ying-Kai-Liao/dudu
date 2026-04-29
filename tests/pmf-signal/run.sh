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

exit "$fail"
