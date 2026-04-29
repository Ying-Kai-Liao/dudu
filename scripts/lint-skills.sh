#!/usr/bin/env bash
# Validates every skills/<name>/SKILL.md in CWD.
# - Frontmatter present and parseable
# - name and description fields present
# - name matches parent directory name
# - lib/<file>.md references all exist
set -u

errors=0
skill_count=0

emit_err() {
    echo "ERROR: $1"
    errors=$((errors + 1))
}

# Find all SKILL.md files under skills/
shopt -s nullglob
for skill_path in skills/*/SKILL.md; do
    skill_count=$((skill_count + 1))
    rel="$skill_path"
    dir_name="$(basename "$(dirname "$skill_path")")"

    # Extract frontmatter (between first --- line and second --- line)
    fm="$(awk 'NR==1 && /^---$/ {inside=1; next} inside && /^---$/ {exit} inside' "$skill_path")"
    if [[ -z "$fm" ]]; then
        emit_err "$rel missing YAML frontmatter"
        continue
    fi

    # Extract name and description fields
    fm_name="$(echo "$fm" | awk -F': *' '/^name:/ {sub(/^name: */, ""); print; exit}')"
    fm_desc="$(echo "$fm" | awk -F': *' '/^description:/ {sub(/^description: */, ""); print; exit}')"

    if [[ -z "$fm_name" ]]; then
        emit_err "$rel missing required frontmatter field: name"
    elif [[ "$fm_name" != "$dir_name" ]]; then
        emit_err "$rel name '$fm_name' does not match directory '$dir_name'"
    fi

    if [[ -z "$fm_desc" ]]; then
        emit_err "$rel missing required frontmatter field: description"
    fi

    # Check lib/<file>.md references in body
    body="$(awk 'NR==1 && /^---$/ {inside=1; next} inside && /^---$/ {inside=0; next} !inside' "$skill_path")"
    while IFS= read -r ref; do
        [[ -z "$ref" ]] && continue
        if [[ ! -f "$ref" ]]; then
            emit_err "$rel references missing $ref"
        fi
    done < <(echo "$body" | grep -oE 'lib/[a-zA-Z0-9_-]+\.md' | sort -u)
done

if [[ "$errors" -ne 0 ]]; then
    echo "FAIL: $errors error(s)"
    exit 1
fi
echo "OK: $skill_count skill(s) lint-clean"

# ---- render-report smoke test ------------------------------------------
# Render the committed test fixture and assert the output is non-empty.
# Skip silently if python3 is missing so this lint stays portable.
fixture="test/ledgerloop"
if [[ -d "$fixture" && -f scripts/render-report.py ]]; then
    if command -v python3 >/dev/null 2>&1; then
        if ! python3 scripts/render-report.py "$fixture" >/dev/null; then
            echo "FAIL: render-report.py exited non-zero on $fixture"
            exit 1
        fi
        out="$fixture/report.html"
        if [[ ! -s "$out" ]]; then
            echo "FAIL: $out missing or empty after render"
            exit 1
        fi
        if ! awk 'BEGIN{found=0} /<body[^>]*>/{p=1; next} /<\/body>/{exit} p && /[^[:space:]]/{found=1} END{exit !found}' "$out"; then
            echo "FAIL: $out has empty <body>"
            exit 1
        fi
        echo "OK: render-report smoke test passed on $fixture"
    else
        echo "SKIP: python3 not on PATH; render-report smoke test not run"
    fi
fi
exit 0
