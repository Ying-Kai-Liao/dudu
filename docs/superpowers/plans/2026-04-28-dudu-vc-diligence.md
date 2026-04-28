# dudu VC Diligence Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin called `dudu` that provides six VC due-diligence skills (founder check, market/problem persona self-play, customer discovery, competitive landscape, market sizing, plus an orchestrator), each producing citation-backed markdown artifacts under a per-deal directory.

**Architecture:** Pure-content plugin (no runtime code beyond a small lint script). Each skill is `skills/<name>/SKILL.md` with YAML frontmatter and a prose body that instructs Claude what to do at invocation time. Three shared lib docs (`lib/deal.md`, `lib/playwright-auth.md`, `lib/research-protocol.md`) are referenced from skill bodies for cross-cutting concerns. A bash linter validates frontmatter and lib references before commit.

**Tech Stack:** Markdown skills, JSON manifests, bash + awk for the linter, Playwright MCP (via `mcp__playwright__*` tools at runtime), WebSearch/WebFetch (at runtime). No build system, no package manager.

---

## File structure (lock decomposition)

```
dudu/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/
│   ├── diligence/SKILL.md
│   ├── founder-check/SKILL.md
│   ├── market-problem/SKILL.md
│   ├── customer-discovery/SKILL.md
│   ├── competitive-landscape/SKILL.md
│   └── market-sizing/SKILL.md
├── lib/
│   ├── deal.md
│   ├── playwright-auth.md
│   └── research-protocol.md
├── scripts/
│   └── lint-skills.sh
├── tests/
│   └── lint/
│       ├── run.sh
│       ├── fixtures/
│       │   ├── good/skills/ok/SKILL.md
│       │   ├── missing-name/skills/bad/SKILL.md
│       │   ├── duplicate-names/skills/a/SKILL.md
│       │   ├── duplicate-names/skills/b/SKILL.md
│       │   └── broken-libref/skills/c/SKILL.md
│       └── expected/
│           ├── good.txt
│           ├── missing-name.txt
│           ├── duplicate-names.txt
│           └── broken-libref.txt
├── README.md
├── .gitignore
└── docs/superpowers/
    ├── specs/2026-04-28-dudu-vc-diligence-design.md
    └── plans/2026-04-28-dudu-vc-diligence.md
```

Each file has one responsibility:
- `plugin.json` / `marketplace.json` → plugin identity for the Claude Code installer.
- `skills/<name>/SKILL.md` → one skill's behavior contract.
- `lib/*.md` → shared procedural knowledge referenced from skill bodies.
- `scripts/lint-skills.sh` → frontmatter + lib-reference validation.
- `tests/lint/` → linter test fixtures and runner.
- `README.md` → install + first-use walkthrough.

---

## Task 1: Plugin scaffolding

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Create `.claude-plugin/plugin.json`**

```json
{
  "name": "dudu",
  "description": "VC due diligence skills for Claude Code: founder checks, market/problem persona self-play, customer discovery, competitive landscape, and market sizing.",
  "version": "0.1.0",
  "author": {
    "name": "Ying-Kai Liao",
    "email": "lykevin890919@gmail.com"
  },
  "license": "MIT",
  "keywords": [
    "vc",
    "venture-capital",
    "due-diligence",
    "skills"
  ]
}
```

- [ ] **Step 2: Create `.claude-plugin/marketplace.json`**

```json
{
  "name": "dudu",
  "description": "VC due diligence plugin marketplace",
  "owner": {
    "name": "Ying-Kai Liao",
    "email": "lykevin890919@gmail.com"
  },
  "plugins": [
    {
      "name": "dudu",
      "description": "VC due diligence skills for Claude Code",
      "version": "0.1.0",
      "source": "./",
      "author": {
        "name": "Ying-Kai Liao",
        "email": "lykevin890919@gmail.com"
      }
    }
  ]
}
```

- [ ] **Step 3: Create `.gitignore`**

```gitignore
# Per-deal artifacts contain VC research and should never be committed
deals/

# OS / editor cruft
.DS_Store
*.swp
.idea/
.vscode/
```

- [ ] **Step 4: Create `README.md` skeleton**

```markdown
# dudu

VC due diligence skills for Claude Code.

Status: under construction. See `docs/superpowers/specs/2026-04-28-dudu-vc-diligence-design.md` for the design and `docs/superpowers/plans/2026-04-28-dudu-vc-diligence.md` for the implementation plan.

## Install (local)

```bash
/plugin marketplace add /Users/ykliao/Workspace/dudu
/plugin install dudu@dudu
```

## Skills

- `dudu:diligence` — orchestrator
- `dudu:founder-check`
- `dudu:market-problem`
- `dudu:customer-discovery`
- `dudu:competitive-landscape`
- `dudu:market-sizing`

A full usage walkthrough is added in Task 12.
```

- [ ] **Step 5: Verify plugin manifest is valid JSON**

Run: `python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); json.load(open('.claude-plugin/marketplace.json')); print('OK')"`
Expected output: `OK`

- [ ] **Step 6: Commit**

```bash
git add .claude-plugin/ .gitignore README.md
git commit -m "Add plugin scaffolding (plugin.json, marketplace.json, README)"
```

---

## Task 2: Lib doc — `lib/deal.md`

**Files:**
- Create: `lib/deal.md`

- [ ] **Step 1: Create `lib/deal.md`**

````markdown
# Deal directory

A "deal" is one company being evaluated. Every dudu skill writes its output under `deals/<slug>/` in the user's current working directory, never anywhere else.

## Slug

Kebab-case, lowercase, derived from the company name.
- "Acme Corp" → `acme`
- "Twenty-Three Capital" → `twenty-three`

The slug is supplied once by the orchestrator (`dudu:diligence`) and reused by every sub-skill in that deal.

## Directory layout

```
deals/<slug>/
├── manifest.json
├── inputs/                       # artifacts the VC supplied (deck, notes, transcripts)
├── founder-<name>.md             # one per founder; <name> is kebab-case of the founder name
├── market-problem.md
├── personas/
│   ├── _context.md
│   ├── persona-1.md
│   ├── persona-2.md
│   ├── persona-3.md
│   └── round-N.md                # one per simulated interview round
├── competitive-landscape.md
├── market-sizing.md
├── customer-discovery-prep.md
├── customer-discovery.md
└── MEMO.md                       # written by the orchestrator at the end
```

## `manifest.json` schema

```json
{
  "slug": "acme",
  "company": "Acme",
  "founders": ["Alice Founder", "Bob Cofounder"],
  "pitch": "One-line pitch.",
  "created_at": "2026-04-28T10:30:00Z",
  "skills_completed": {
    "founder-check": "2026-04-28T11:05:00Z",
    "market-problem": null,
    "customer-discovery-prep": null,
    "customer-discovery-debrief": null,
    "competitive-landscape": null,
    "market-sizing": null
  }
}
```

Every skill that produces an artifact MUST update `skills_completed[<skill-key>]` with the current ISO-8601 UTC timestamp. If the skill aborts, it leaves the value as `null`.

## Idempotency

When invoked, a skill checks whether its artifact already exists.
- If yes and `--force` was NOT passed: print "Artifact already exists at <path>. Pass --force to overwrite." and exit.
- If `--force` was passed: overwrite the artifact and re-update the manifest timestamp.

## Reading prior artifacts

Later skills MAY read earlier artifacts. For example, `customer-discovery prep` reads `personas/persona-*.md` if they exist. Always check existence before reading; never crash if a prior step was skipped.
````

- [ ] **Step 2: Verify markdown is parseable**

Run: `python3 -c "open('lib/deal.md').read(); print('OK')"`
Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add lib/deal.md
git commit -m "Add lib/deal.md (deal directory schema and manifest format)"
```

---

## Task 3: Lib doc — `lib/playwright-auth.md`

**Files:**
- Create: `lib/playwright-auth.md`

- [ ] **Step 1: Create `lib/playwright-auth.md`**

````markdown
# Playwright authentication pattern

Some sources (LinkedIn, Crunchbase, certain forums) require authentication. Dudu skills drive these sites with the VC's own browser session via the Playwright MCP server, never with bots or stored credentials.

## Tools

The Playwright MCP server exposes (among others):
- `mcp__playwright__browser_navigate` — open a URL
- `mcp__playwright__browser_snapshot` — read the current page
- `mcp__playwright__browser_click`, `browser_type`, `browser_fill_form` — interact
- `mcp__playwright__browser_wait_for` — wait for content
- `mcp__playwright__browser_close` — close the browser

If these tools are not available in the current Claude Code session, abort the run and tell the VC to install/enable the Playwright MCP server before retrying.

## Login-once pattern

Before scraping a gated site, the skill MUST:

1. Navigate to a known-public page on the site (e.g. `https://www.linkedin.com/feed/`).
2. Take a snapshot.
3. If the snapshot shows the login wall, instruct the VC:

   > I need you to log into LinkedIn in the Playwright browser window. I'll wait. Tell me "logged in" when you're ready.

4. Wait for the VC's confirmation message before proceeding.
5. Re-snapshot to verify the session is now authenticated.

Once authenticated, the session persists for the rest of the run. If a session expires mid-run, the skill detects the redirect to the login page, pauses, and re-prompts the VC.

## Pacing and rate limits

- Pace navigations at human speed: at minimum a 2-second wait between page loads on the same domain.
- Never open more than one tab on the same site at a time.
- Hard cap per skill per founder/competitor: ~30 page fetches. If you hit the cap, stop and report what you have.

## Terms of service

Skills must not initiate scraping campaigns. Driving the VC's own authenticated browser at human pace for personal due-diligence research is the only permitted pattern. If a skill author is tempted to "fan out" or "speed up", that's a sign the design is wrong.

## Artifact citations

Every fact pulled from a Playwright-driven page MUST be cited with the URL the data came from. If a URL would expose VC-private data (e.g. logged-in profile views), cite the source as `"<domain> (authenticated session)"` and include the public-equivalent URL when one exists.
````

- [ ] **Step 2: Commit**

```bash
git add lib/playwright-auth.md
git commit -m "Add lib/playwright-auth.md (login-once UX, pacing, ToS)"
```

---

## Task 4: Lib doc — `lib/research-protocol.md`

**Files:**
- Create: `lib/research-protocol.md`

- [ ] **Step 1: Create `lib/research-protocol.md`**

````markdown
# Research protocol

Every dudu skill that gathers information follows these rules. They are non-negotiable: VCs make money decisions on what these artifacts say, and a fabricated claim is worse than no claim.

## Citation format

Every factual claim has a source. Two formats:

- **Public web** — inline link: `[Acme raised $4M Seed in 2024](https://techcrunch.com/...)`
- **VC-supplied** — parenthetical: `Founder claims TAM is $20B (VC-supplied: deck slide 14)`
- **Authenticated browser session** — domain plus public equivalent if one exists: `Headcount: 47 employees (linkedin.com, authenticated session; public equivalent: https://www.crunchbase.com/...)`

## Source honesty

- If a fact cannot be sourced, write **"Not found in public sources."** Never invent.
- If two sources contradict, surface both with citations and label the contradiction. Do not silently pick a winner.
- Estimates are explicit: `~50–200 (range; no precise public source)` — never a single fabricated number.
- Never paraphrase a quote into something the source did not say. If quoting, reproduce verbatim.

## Search budgeting

Deep research is token-heavy. Each skill declares a per-run budget in its body. Default budgets:

- founder-check: ~30 fetches per founder
- market-problem phase 1: ~50 fetches total
- competitive-landscape: ~5 fetches per competitor, ~30 competitors max
- market-sizing: ~30 fetches total
- customer-discovery prep: ~20 fetches total

If a skill hits its budget, it stops, writes what it has, and notes the truncation in the artifact.

## Ordering of sources

Prefer in roughly this order:
1. Primary sources (filings, patents, the company's own blog, founder's own writing)
2. Reputable secondary (industry analysts, established trade press)
3. Aggregators (Crunchbase, Product Hunt)
4. User-generated (Reddit, HN, forums) — useful for sentiment, weak for facts
5. AI-summarized content — never as a primary source

## Output structure

Every research artifact ends with two sections:

```markdown
## Sources

- [Title](url) — brief description
- [Title](url) — brief description

## Open questions

- Question the next step in due diligence should answer
- Question the next step in due diligence should answer
```
````

- [ ] **Step 2: Commit**

```bash
git add lib/research-protocol.md
git commit -m "Add lib/research-protocol.md (citation rules, source honesty, budgets)"
```

---

## Task 5: Skill linter (TDD)

The linter validates that every `skills/<name>/SKILL.md`:
1. Has YAML frontmatter (between `---` lines)
2. Frontmatter contains `name:` and `description:` fields
3. The `name` value matches the directory name
4. Names are unique across all skills
5. Every `lib/<file>.md` reference in the body actually exists

**Files:**
- Create: `scripts/lint-skills.sh`
- Create: `tests/lint/run.sh`
- Create: `tests/lint/fixtures/good/skills/ok/SKILL.md`
- Create: `tests/lint/fixtures/missing-name/skills/bad/SKILL.md`
- Create: `tests/lint/fixtures/duplicate-names/skills/a/SKILL.md`
- Create: `tests/lint/fixtures/duplicate-names/skills/b/SKILL.md`
- Create: `tests/lint/fixtures/duplicate-names/lib/.gitkeep`
- Create: `tests/lint/fixtures/broken-libref/skills/c/SKILL.md`
- Create: `tests/lint/fixtures/good/lib/foo.md`
- Create: `tests/lint/fixtures/missing-name/lib/.gitkeep`
- Create: `tests/lint/fixtures/broken-libref/lib/.gitkeep`
- Create: `tests/lint/expected/good.txt`
- Create: `tests/lint/expected/missing-name.txt`
- Create: `tests/lint/expected/duplicate-names.txt`
- Create: `tests/lint/expected/broken-libref.txt`

- [ ] **Step 1: Create test fixtures (good case)**

`tests/lint/fixtures/good/skills/ok/SKILL.md`:

```markdown
---
name: ok
description: A valid skill for testing.
---

# OK skill

See `lib/foo.md` for details.
```

`tests/lint/fixtures/good/lib/foo.md`:

```markdown
# Foo
```

`tests/lint/expected/good.txt`:

```
OK: 1 skill(s) lint-clean
```

- [ ] **Step 2: Create test fixtures (missing-name case)**

`tests/lint/fixtures/missing-name/skills/bad/SKILL.md`:

```markdown
---
description: Missing the name field.
---

# Bad
```

`tests/lint/fixtures/missing-name/lib/.gitkeep` (empty file).

`tests/lint/expected/missing-name.txt`:

```
ERROR: skills/bad/SKILL.md missing required frontmatter field: name
FAIL: 1 error(s)
```

- [ ] **Step 3: Create test fixtures (duplicate-names case)**

`tests/lint/fixtures/duplicate-names/skills/a/SKILL.md`:

```markdown
---
name: same
description: First.
---
```

`tests/lint/fixtures/duplicate-names/skills/b/SKILL.md`:

```markdown
---
name: same
description: Second.
---
```

`tests/lint/fixtures/duplicate-names/lib/.gitkeep` (empty file).

`tests/lint/expected/duplicate-names.txt`:

```
ERROR: skills/a/SKILL.md name 'same' does not match directory 'a'
ERROR: skills/b/SKILL.md name 'same' does not match directory 'b'
FAIL: 2 error(s)
```

(Note: with this stricter rule, "name must match directory" automatically prevents duplicates because directory names are already unique. The fixture exists to confirm the rule fires.)

- [ ] **Step 4: Create test fixtures (broken-libref case)**

`tests/lint/fixtures/broken-libref/skills/c/SKILL.md`:

```markdown
---
name: c
description: References a missing lib doc.
---

See `lib/does-not-exist.md`.
```

`tests/lint/fixtures/broken-libref/lib/.gitkeep` (empty file).

`tests/lint/expected/broken-libref.txt`:

```
ERROR: skills/c/SKILL.md references missing lib/does-not-exist.md
FAIL: 1 error(s)
```

- [ ] **Step 5: Create test runner `tests/lint/run.sh`**

```bash
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
```

- [ ] **Step 6: Make the test runner executable**

Run: `chmod +x tests/lint/run.sh`

- [ ] **Step 7: Run tests to verify they all fail (linter not yet written)**

Run: `bash tests/lint/run.sh`
Expected: every case prints `FAIL` because `scripts/lint-skills.sh` does not exist yet, and the runner exits non-zero.

- [ ] **Step 8: Write `scripts/lint-skills.sh`**

```bash
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

if [[ "$errors" -eq 0 ]]; then
    echo "OK: $skill_count skill(s) lint-clean"
    exit 0
else
    echo "FAIL: $errors error(s)"
    exit 1
fi
```

- [ ] **Step 9: Make the linter executable**

Run: `chmod +x scripts/lint-skills.sh`

- [ ] **Step 10: Run tests, verify all pass**

Run: `bash tests/lint/run.sh`
Expected: four `PASS` lines, exit code 0.

If any case fails, fix the linter (not the expected output, unless the rule itself is wrong) and re-run.

- [ ] **Step 11: Commit**

```bash
git add scripts/ tests/
git commit -m "Add skill linter with TDD fixtures"
```

---

## Task 6: `dudu:founder-check` skill

**Files:**
- Create: `skills/founder-check/SKILL.md`

- [ ] **Step 1: Create `skills/founder-check/SKILL.md`**

````markdown
---
name: founder-check
description: Build a public-web + authenticated-browser dossier on each founder of a deal under evaluation. Surfaces career, prior ventures, controversies, and open questions a partner would ask.
---

# Founder check

Produce a citation-backed dossier on each founder named in the deal. Read `lib/research-protocol.md` and `lib/playwright-auth.md` before starting and follow them strictly.

## Inputs

Required (prompt the VC if missing):
- Deal slug (kebab-case directory name under `deals/`)
- Founder names (one or more)

Optional (use if available):
- Founder LinkedIn URLs (skip the LinkedIn search step if supplied)
- Pitch deck or company website URL (helps disambiguate the right person)

## Pre-flight

1. If `deals/<slug>/manifest.json` does not exist, create it with the schema in `lib/deal.md`. If the founder is not in the manifest yet, add them.
2. For each founder, the artifact path is `deals/<slug>/founder-<kebab-name>.md`. If it exists and `--force` was not passed, print "Artifact already exists. Pass --force to overwrite." and stop.

## Sources to consult (per founder)

In rough priority order, capping at ~30 fetches per founder:

1. **Google web search** for the founder's name + their company name (disambiguates from same-named people).
2. **Personal site / blog** if findable.
3. **GitHub** profile: owned repos, contribution graph, language mix, recent activity.
4. **Twitter/X** profile: bio, pinned tweet, last ~50 posts. Look for stated positions, networks, controversies.
5. **News search** (Google News, TechCrunch, sector trade press) for the founder's name in quotes.
6. **Podcast appearances** — search "<founder name> podcast" — listen to short intro/bio segments only.
7. **Conference talks** — search "<founder name> talk OR keynote OR slides".
8. **LinkedIn** — Playwright with the VC's authenticated session. Career timeline, current role, notable connections (only count, not names, in the artifact). Follow `lib/playwright-auth.md` exactly.
9. **Crunchbase founder page** — Playwright. Prior ventures with funding/exit data.
10. **Court records / litigation** — search "<founder name> lawsuit OR litigation OR settled" with the company name as additional context. Only include results clearly tied to this person.

## Artifact template

Write to `deals/<slug>/founder-<kebab-name>.md`:

```markdown
# Founder check: <Full Name>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## Career timeline

| Years | Company | Role | Outcome |
|-------|---------|------|---------|
| ... | ... | ... | ... |

## Domain credibility

[2-4 sentences on what makes them credible — or not — to ship this product. Cite specific evidence.]

## Prior ventures

- **<Company>** (<years>) — <one-paragraph summary, including outcome: acquired / shut down / still operating>. Source: [link]

## Public controversies / litigation

[Either bulleted findings with sources, or "Not found in public sources."]

## Communication style

[2-3 sentences with a representative quote and source.]

## Network density

[Notable co-founders, advisors, or employer alumni. Count of LinkedIn connections if available. Source.]

## Open questions a partner would ask

- [Specific question grounded in something above]
- [Another]

## Sources

- [Title](url) — brief description
- ...
```

## After writing

1. Update `deals/<slug>/manifest.json` `skills_completed["founder-check"]` to the current ISO-8601 UTC timestamp.
2. Print a one-line summary: `Wrote founder-check for N founder(s) to deals/<slug>/`.
````

- [ ] **Step 2: Run linter**

Run: `bash scripts/lint-skills.sh`
Expected: `OK: 1 skill(s) lint-clean`

- [ ] **Step 3: Smoke test (manual, in Claude Code)**

The engineer must manually verify by:
1. Installing the plugin: `/plugin marketplace add /Users/ykliao/Workspace/dudu` then `/plugin install dudu@dudu` in a fresh Claude Code session.
2. Confirming the skill is listed: it should appear under available skills as `dudu:founder-check`.
3. Invoking with a public-figure test case: tell Claude "use dudu:founder-check on slug=test-elon, founder=Elon Musk, company=SpaceX".
4. Verifying Claude (a) asks for missing inputs cleanly, (b) creates `deals/test-elon/manifest.json`, (c) starts pulling sources and citing them, (d) writes the artifact in the documented format.
5. Deleting `deals/test-elon/` after the smoke test.

If any of those fail, edit the SKILL.md to fix and re-run from Step 2.

- [ ] **Step 4: Commit**

```bash
git add skills/founder-check/
git commit -m "Add dudu:founder-check skill"
```

---

## Task 7: `dudu:competitive-landscape` skill

**Files:**
- Create: `skills/competitive-landscape/SKILL.md`

- [ ] **Step 1: Create `skills/competitive-landscape/SKILL.md`**

````markdown
---
name: competitive-landscape
description: Map direct and indirect competitors, assess incumbent threat, and analyze moat durability. Produces a competitor matrix with citations.
---

# Competitive landscape

Map every direct and indirect competitor for the deal. Read `lib/research-protocol.md` and `lib/playwright-auth.md` before starting. Cap at ~5 fetches per competitor and ~30 competitors.

## Inputs

Required (prompt if missing):
- Deal slug
- Company name
- One-line product description
- Target customer (ICP) if known

## Pre-flight

Same idempotency check as other skills (read `lib/deal.md`). Artifact path: `deals/<slug>/competitive-landscape.md`.

## Sources

1. **Product Hunt** — search the product category. Pull launch posts, traction signals, comments.
2. **Crunchbase** — Playwright with VC session. Funding history, headcount, last raise.
3. **GitHub** — search the category for open-source competitors. Star counts, commit cadence (active vs abandoned).
4. **Public job boards** — search incumbents for roles in this product area. Hiring signals indicate seriousness.
5. **Google Patents** — search the core technique or product noun. Filed-and-granted vs filed-and-abandoned matters.
6. **News and tech press** — search the category for the last 18 months.

## Artifact template

```markdown
# Competitive landscape: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## Direct competitors

| Competitor | Positioning | Traction | Last funding | Moat type | Last activity | Source |
|------------|-------------|----------|--------------|-----------|---------------|--------|
| ... | ... | ... | ... | ... | ... | [link] |

## Indirect competitors

| Competitor | Why indirect | Risk it becomes direct | Source |
|------------|--------------|------------------------|--------|
| ... | ... | ... | [link] |

## Incumbent threat assessment

For each incumbent who could plausibly crush a startup in this space:

### <Incumbent name>

- **Currently shipping in this area?** Yes / No / Building. Evidence: [link]
- **Hiring signal?** [count of job postings tagged with the relevant keywords, with link]
- **Public statements?** [quotes from earnings calls, blog posts, conference talks, with sources]
- **Verdict:** Sleeping / Watching / Building / Already shipping.

## Moat analysis

For each candidate moat type, with evidence:

- **Network effects:** [analysis with evidence, or "Not applicable"]
- **Proprietary data:** [analysis with evidence, or "Not applicable"]
- **Switching costs:** [analysis with evidence, or "Not applicable"]
- **Brand:** [analysis with evidence, or "Not applicable"]

## Sources

- ...

## Open questions

- ...
```

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["competitive-landscape"]`.
````

- [ ] **Step 2: Run linter**

Run: `bash scripts/lint-skills.sh`
Expected: `OK: 2 skill(s) lint-clean`

- [ ] **Step 3: Smoke test (manual, in Claude Code)**

Same procedure as Task 6 Step 3, with: "use dudu:competitive-landscape on slug=test-co, company=Linear, product='issue tracker for software teams', icp='engineering leads'". Verify:
- Asks for ICP cleanly if missing.
- Searches Product Hunt and surfaces Jira / Asana / Notion / GitHub Issues / etc.
- Writes the matrix with citations.
- Updates manifest.

- [ ] **Step 4: Commit**

```bash
git add skills/competitive-landscape/
git commit -m "Add dudu:competitive-landscape skill"
```

---

## Task 8: `dudu:market-sizing` skill

**Files:**
- Create: `skills/market-sizing/SKILL.md`

- [ ] **Step 1: Create `skills/market-sizing/SKILL.md`**

````markdown
---
name: market-sizing
description: Build a bottom-up TAM model from scratch, anchored on a clearly defined ICP and a transparent reachable-population calculation. Does not anchor on the founder's number.
---

# Market sizing

Produce a defensible bottom-up TAM. Read `lib/research-protocol.md` first. Cap at ~30 fetches.

## Critical rule

You MUST NOT anchor on any TAM number the founder claimed. Build from zero. Compare to the founder's number only at the end, in a labeled section.

## Inputs

Required:
- Deal slug
- Company name
- Product description
- Target ICP — if missing, read `deals/<slug>/personas/persona-*.md` if available, otherwise prompt the VC.

## Pre-flight

Idempotency check. Artifact: `deals/<slug>/market-sizing.md`.

## Method

1. **Define the wedge.** Write a one-sentence ICP that names a job title, a company size band, and a buying trigger.
2. **Count the reachable population.** Use public data:
   - Industry directories (e.g. SIC/NAICS counts, association memberships)
   - Government statistics (BLS, Eurostat, equivalent)
   - LinkedIn-style search counts via Playwright if needed
   - Cite every number.
3. **Anchor the ACV.** Find 3 reference points:
   - What do incumbents in this space charge?
   - What does a comparable adjacent product cost?
   - What did your customer-discovery work (if available) suggest WTP was?
   Pick a range, not a point estimate.
4. **Compute the wedge TAM.** `reachable population × ACV range`. Show your work.
5. **Identify expansion adjacent.** Name 1-3 named adjacent segments the company could expand into. For each, repeat steps 2-4.
6. **Compare to founder claim.** Only now, side-by-side.

## Artifact template

```markdown
# Market sizing: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## Wedge ICP

> [One-sentence ICP definition]

## Reachable population

| Segment | Count | Source |
|---------|-------|--------|
| ... | ... | [link] |

**Total reachable:** [number with range]

## ACV anchors

| Reference | Annual price | Source |
|-----------|--------------|--------|
| ... | ... | [link] |

**Defensible ACV range:** $X–$Y

## Wedge TAM math

```
reachable population × annual ACV range
= <low_count> × $<low_acv> = $<low_tam>
to
  <high_count> × $<high_acv> = $<high_tam>
```

**Wedge TAM:** $<low_tam>–$<high_tam>

## Expansion segments

### <Segment 1>

- Reachable: ... (source)
- ACV: $... (source)
- TAM: $...

### <Segment 2>

[same shape]

## Total addressable (wedge + expansion)

$<low_total>–$<high_total>

## Founder claim comparison

| Source | Number | Method |
|--------|--------|--------|
| Founder | $<founder_tam> | <if disclosed> |
| Bottom-up (this artifact) | $<our_tam> | Bottom-up |
| Delta | <ratio or absolute> | |

## Verdict on wedge

- **Clearly defined?** Yes / No / Partial — explain.
- **Reachable?** Yes / No / Partial — explain. (Specifically: can a small startup actually find and contact this population?)
- **Credible expansion path?** Yes / No / Partial — explain.

## Sources

## Open questions
```

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["market-sizing"]`.
````

- [ ] **Step 2: Run linter**

Run: `bash scripts/lint-skills.sh`
Expected: `OK: 3 skill(s) lint-clean`

- [ ] **Step 3: Smoke test**

Manual: invoke with a real test case (e.g. an existing public startup) and verify:
- It refuses to anchor on a fake "founder claimed $50B" if you provide one.
- It cites every population count.
- It produces a defensible ACV range, not a single point estimate.

- [ ] **Step 4: Commit**

```bash
git add skills/market-sizing/
git commit -m "Add dudu:market-sizing skill"
```

---

## Task 9: `dudu:market-problem` skill

This is the most complex skill: deep context, persona generation, self-play, cross-round analysis.

**Files:**
- Create: `skills/market-problem/SKILL.md`

- [ ] **Step 1: Create `skills/market-problem/SKILL.md`**

````markdown
---
name: market-problem
description: Three-phase market/product/problem analysis. Phase 1 builds a deep context bundle from web research. Phase 2 auto-generates personas and runs self-play interviews. Phase 3 synthesizes patterns and contradictions to surface questions for real customer discovery.
---

# Market / product / problem

Run a three-phase exploration of the problem space. Read `lib/research-protocol.md` and `lib/playwright-auth.md` first. Heavier budget than other skills: ~50 fetches in phase 1.

## What this skill IS and IS NOT

- IS: a rehearsal tool. Possibility-space exploration before real customer interviews.
- IS NOT: validation. Self-play does not produce signal — only patterns to test against reality. Real signal comes from `dudu:customer-discovery`.

State this distinction in your output every time. VCs misuse persona output if you don't.

## Inputs

Required:
- Deal slug
- Company name
- Product description
- Target ICP if known (else generate during persona phase)

Optional:
- Loop count (default 6)
- Persona count (default 3)
- Pitch deck text (helps phase 1)

## Pre-flight

Idempotency check. Artifact: `deals/<slug>/market-problem.md`. Personas live under `deals/<slug>/personas/`.

## Phase 1: Deep context engineering

Goal: produce `deals/<slug>/personas/_context.md` — a structured snapshot of what's known about the problem space before constructing any persona.

Sources (cap at ~50 total):
1. The product's own home page and any public docs.
2. Adjacent products' marketing pages — what jobs do they claim to do?
3. Customer reviews on G2, Capterra, Trustpilot for adjacent products.
4. Reddit threads on the problem (search the relevant subreddits).
5. Hacker News threads — search for the product category and the pain point words.
6. Niche forum threads (industry-specific Slacks/Discords/forums when public).
7. Industry analyst reports if findable (often paywalled — note when blocked).
8. Podcast transcripts where relevant.

Write `personas/_context.md` with these sections:

```markdown
# Problem-space context bundle

**Generated:** <ISO timestamp>

## What is the problem?

[3-4 sentences synthesized across sources, with citations]

## Who has it?

[The market segments where this pain shows up, with evidence]

## How are they solving it today?

[The current workarounds and competing products. Cite reviews.]

## What's contested?

[Disagreements across sources — e.g. one camp says this matters, another says it doesn't]

## What we couldn't find

[Be honest. "No public data on willingness-to-pay for this category."]

## Sources

- ...
```

## Phase 2: Persona generation + self-play

1. Using `_context.md` only (not your prior knowledge), generate N personas (default 3). Save each to `personas/persona-K.md`:

```markdown
# Persona <K>: <short label>

**Role:** <job title>
**Demographics:** <relevant context>
**Current workflow:** <how they handle this today>
**Pain intensity (1-10):** <number with justification>
**Willingness-to-pay anchor:** $<range> annually, justified by <reference>
**Voice / phrasing:** <how this person actually talks — sample phrases>
```

2. Distribute the loop count across personas. Default: 6 rounds = 3 personas × 2 rounds each. Loop variable assignment goes in the artifact: persona-1 gets rounds 1 and 2, persona-2 gets rounds 3 and 4, persona-3 gets rounds 5 and 6.

3. For each round R, write `personas/round-R.md`:

```markdown
# Round <R> — Persona <K>

**Generated:** <ISO timestamp>

## Conversation

**Interviewer:** Tell me about this problem in your day-to-day.
**Persona <K>:** [in-character response, drawing only on persona profile + context bundle]

**Interviewer:** [Mom-Test follow-up rooted in the persona's last response]
**Persona <K>:** [in-character response]

[continue for ~6-10 exchanges; cover: current workflow, pain triggers, prior solution attempts, willingness to pay, what would make them switch]

## Round notes

- What surprised the interviewer
- What contradicted the persona profile (the persona "discovered" something)
- What questions came up that aren't answerable from context
```

The interviewer asks Mom-Test-style questions (about current behavior, never about hypothetical future behavior or vague preferences). The persona stays grounded in the persona profile and `_context.md`; if either is silent on a topic, the persona says so rather than fabricating.

## Phase 3: Cross-round analysis

After all rounds complete, write `deals/<slug>/market-problem.md`:

```markdown
# Market / product / problem: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

> ⚠️ This analysis is based on simulated personas. It is for rehearsal and possibility-space exploration only. Real signal requires running `dudu:customer-discovery` with real people.

## Patterns across rounds

[3-6 things multiple personas agreed on, with round citations: round-1.md, round-3.md, etc.]

## Contradictions across rounds

[2-4 places personas disagreed — these are the most valuable surfaces]

## Strongest pain signals

[Rank-ordered list of pains by intensity × frequency across rounds]

## Weakest assumptions

[2-4 places where the persona felt thin / had to fabricate / where context was missing]

## Questions to bring to real customer interviews

[5-10 specific questions, each rooted in a contradiction or weak assumption. Format: "Q: ... — root: ..."]

## Source artifacts

- personas/_context.md
- personas/persona-1.md
- ...
- personas/round-1.md
- ...
```

## After writing

Update `deals/<slug>/manifest.json` `skills_completed["market-problem"]`.
````

- [ ] **Step 2: Run linter**

Run: `bash scripts/lint-skills.sh`
Expected: `OK: 4 skill(s) lint-clean`

- [ ] **Step 3: Smoke test**

Manual, with a small loop count (e.g. count=2) for speed:
- Invoke with slug=test-mp, product description, ICP.
- Verify phase 1 produces `_context.md` with cited sections, not vibes.
- Verify personas are distinct (don't all sound the same) and grounded in context.
- Verify round files are written individually.
- Verify the final artifact's caveat about self-play vs real signal is visible at the top.
- Verify "Questions to bring to real customer interviews" is concrete, not abstract.

- [ ] **Step 4: Commit**

```bash
git add skills/market-problem/
git commit -m "Add dudu:market-problem skill (deep context + persona self-play)"
```

---

## Task 10: `dudu:customer-discovery` skill

**Files:**
- Create: `skills/customer-discovery/SKILL.md`

- [ ] **Step 1: Create `skills/customer-discovery/SKILL.md`**

````markdown
---
name: customer-discovery
description: Helps the VC do their own customer discovery — without the founder. 'prep' builds a target list and outreach drafts. 'debrief' synthesizes interview transcripts into pain/WTP/objections with quote-level evidence.
---

# Customer discovery

Two sub-actions, dispatched by argument: `prep` and `debrief`. Read `lib/research-protocol.md` and `lib/playwright-auth.md` first.

## Dispatch

If the user invokes the skill without specifying:
- If `customer-discovery-prep.md` does not exist → run `prep`.
- If `customer-discovery-prep.md` exists and `customer-discovery.md` does not → run `debrief`.
- Else → ask which they want.

## Inputs (both sub-actions)

Required:
- Deal slug

`prep` additionally:
- Persona profiles from `deals/<slug>/personas/persona-*.md` if available — else prompt for ICP.

`debrief` additionally:
- Interview transcripts or notes (the VC pastes these in or supplies file paths under `deals/<slug>/inputs/`).

## Pre-flight

Idempotency check on the relevant artifact.

---

## Sub-action: prep

Goal: produce a target list, outreach drafts, and an interview script.

### Steps

1. **Target list.** Search ~20 fetches across:
   - LinkedIn — Playwright with VC session. Filter by job title from the persona profile and by company size.
   - Reddit — identify ~3 relevant subreddits, surface ~5 candidates each (people posting about the relevant pain).
   - Niche communities — identify 1-2 relevant Slack/Discord communities (only ones with public membership lists).
   - X — search for the persona phrasing from the persona profile.

   Aim for 30 candidates total. For each, capture: name, channel, link, why-they-fit (one sentence), how-to-reach (DM / email / public post reply).

2. **Outreach templates.** One per channel:
   - LinkedIn DM
   - Reddit DM
   - X DM
   - Cold email

   Each ~80 words. The persona-N.md profile dictates phrasing variants for the top 3 candidates per channel — slot them in inline.

3. **Interview script.** Anchored on these four questions; expand each with 1-2 follow-ups:
   - Tell me about this problem in your day-to-day.
   - How are you solving it today?
   - What would it be worth to you to solve this properly?
   - Have you looked for solutions? Why didn't they work?

### Artifact: `deals/<slug>/customer-discovery-prep.md`

```markdown
# Customer discovery prep: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## Target list

| # | Name | Channel | Link | Why they fit | How to reach |
|---|------|---------|------|--------------|--------------|
| 1 | ... | LinkedIn | [link] | ... | DM |
| ... |

## Outreach templates

### LinkedIn DM (template)

> [80-word draft]

#### Variant for candidate #<N>

> [tweaked draft]

[Repeat for Reddit DM, X DM, Cold email]

## Interview script

1. **Tell me about this problem in your day-to-day.**
   - Follow-ups: ...

2. **How are you solving it today?**
   - Follow-ups: ...

[etc.]

## Sources

- ...
```

After writing, update manifest `skills_completed["customer-discovery-prep"]`.

---

## Sub-action: debrief

Goal: synthesize the VC's actual interview notes into a research artifact.

### Steps

1. Read transcripts/notes from `deals/<slug>/inputs/` or from VC's pasted text. Each interview becomes one input section.
2. For each interview, extract:
   - Pain intensity (1-10) with quote
   - Current solution with quote
   - WTP signal with quote
   - Failed prior solutions with quote
   - Surprises (anything the VC didn't expect)
3. Cross-reference against `personas/persona-*.md` if they exist. Flag where reality contradicted the persona. **Contradictions are the most valuable signal.**

### Artifact: `deals/<slug>/customer-discovery.md`

```markdown
# Customer discovery: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>
**Interviews:** <N>

## Pain intensity

| Interviewee | Score (1-10) | Verbatim |
|-------------|--------------|----------|
| C1 | ... | "..." |
| ... |

**Aggregate read:** [1-2 sentences]

## Current solutions

[Per-interviewee with verbatim quotes]

## Willingness to pay

[Per-interviewee with verbatim quotes. Surface explicit numbers ONLY when the interviewee gave one. Never extrapolate.]

## Failed prior solutions

[Per-interviewee with verbatim quotes. This is the most actionable insight for the founder.]

## Persona contradictions

[Where reality diverged from `persona-N.md`. For each, name the persona, the assumption, and the contradicting quote.]

## Aggregate verdict

- **Pain real?** Yes / No / Mixed — explain in 2 sentences.
- **Buyers willing to pay?** Yes / No / Insufficient signal — explain.
- **Wedge clear after talking to real people?** Yes / No / Partial — explain.

## Sources

- inputs/interview-1.md
- ...
```

After writing, update manifest `skills_completed["customer-discovery-debrief"]`.
````

- [ ] **Step 2: Run linter**

Run: `bash scripts/lint-skills.sh`
Expected: `OK: 5 skill(s) lint-clean`

- [ ] **Step 3: Smoke test**

Two passes:
- prep: invoke after running `dudu:market-problem` for the same deal; verify it reads the persona files and the target list looks plausible.
- debrief: paste a fake interview transcript; verify the synthesis quotes verbatim and flags persona contradictions.

- [ ] **Step 4: Commit**

```bash
git add skills/customer-discovery/
git commit -m "Add dudu:customer-discovery skill (prep + debrief)"
```

---

## Task 11: `dudu:diligence` orchestrator skill

**Files:**
- Create: `skills/diligence/SKILL.md`

- [ ] **Step 1: Create `skills/diligence/SKILL.md`**

````markdown
---
name: diligence
description: Orchestrates the full dudu due-diligence workflow for a deal. Runs founder-check, market-problem, customer-discovery prep, competitive-landscape, market-sizing, pauses for the VC's real customer interviews, then runs customer-discovery debrief and stitches the final memo.
---

# Diligence orchestrator

Run the full dudu workflow end-to-end on one deal. Read `lib/deal.md`, `lib/playwright-auth.md`, and `lib/research-protocol.md` before starting.

## Inputs (prompt if missing)

- Deal slug (kebab-case)
- Company name
- Founder names (one or more)
- One-line pitch
- Pitch deck (file path or pasted text), optional but strongly preferred

## Steps

1. **Initialize deal directory.** If `deals/<slug>/` does not exist, create it. Write `manifest.json` per the schema in `lib/deal.md`. If supplied, save the deck to `deals/<slug>/inputs/deck.<ext>` (or `deck.md` if pasted text).

2. **Run sub-skills in this order**, each as a sub-invocation. After each, confirm the artifact exists before moving on. If the user passed `--force`, propagate it to each sub-skill.

   1. `dudu:founder-check` — for each founder
   2. `dudu:market-problem`
   3. `dudu:customer-discovery prep`
   4. `dudu:competitive-landscape`
   5. `dudu:market-sizing`

3. **Pause for real interviews.** After the five sub-skills, print:

   > Prep complete. The next step is yours: reach out to the candidates in `deals/<slug>/customer-discovery-prep.md` and run 5–10 real interviews. Save transcripts under `deals/<slug>/inputs/`. When done, re-run `dudu:diligence` and I'll continue with the debrief and final memo.

   Stop. Do not proceed.

4. **On re-invocation**, detect that prep is done and inputs exist:
   - If `customer-discovery-prep.md` exists AND `inputs/` has at least one new file AND `customer-discovery.md` does not exist → run `dudu:customer-discovery debrief`, then continue to step 5.
   - If everything is done → skip straight to step 5.

5. **Stitch `MEMO.md`.** Read every artifact under `deals/<slug>/` and produce `deals/<slug>/MEMO.md`:

```markdown
# Investment memo: <Company>

**Deal:** <slug>
**Generated:** <ISO timestamp>

## TL;DR

[3-5 sentences. Founder credibility, problem severity, market size, competitive position, recommendation tilt.]

## Founders

[For each founder, summarize from `founder-<name>.md` in 3-5 bullets. Link to the full dossier.]

## Problem and product

[Summary from `market-problem.md` (4-6 sentences) + the strongest pattern + the most valuable contradiction. Link to the full file.]

## Customer signal

[Summary from `customer-discovery.md`. Quote 2-3 strongest verbatims. Flag any persona contradictions explicitly.]

## Competitive landscape

[Summary from `competitive-landscape.md`. Top 3 direct competitors. Incumbent verdict. Moat verdict.]

## Market sizing

[Wedge TAM range, expansion TAM range, comparison to founder claim.]

## Cross-artifact synthesis

[New section. Surfaces contradictions ACROSS artifacts. e.g.: "Founder claims engineering teams are the buyer (deck p.3), but customer interviews showed product managers driving the purchase (interview-2)." This is where the orchestrator earns its keep.]

## Recommendation

- **Pass / Watch / Pursue:** <verdict>
- **Why:** [3 sentences]
- **What would change my mind:** [2-3 specific things to verify]

## Source artifacts

- founder-<name>.md
- market-problem.md
- customer-discovery.md
- competitive-landscape.md
- market-sizing.md
```

6. **Update manifest** to record completion of orchestration.

7. **Print** the path to `MEMO.md`.

## Re-runnability

Each sub-skill checks its own artifact and skips if present (unless `--force`). The orchestrator therefore can be re-run safely; only missing pieces will be filled.
````

- [ ] **Step 2: Run linter**

Run: `bash scripts/lint-skills.sh`
Expected: `OK: 6 skill(s) lint-clean`

- [ ] **Step 3: Smoke test**

End-to-end with a small test case:
- Pass `--force` so the run is deterministic.
- For loop count, override `dudu:market-problem` to use 2 rounds (faster).
- Verify the orchestrator: creates the manifest, runs each sub-skill, pauses correctly after the five, resumes correctly when transcripts are added, stitches MEMO.md with the cross-artifact synthesis section, and prints the final path.

- [ ] **Step 4: Commit**

```bash
git add skills/diligence/
git commit -m "Add dudu:diligence orchestrator skill"
```

---

## Task 12: README walkthrough

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace `README.md` with a complete walkthrough**

````markdown
# dudu

VC due diligence skills for Claude Code. Six skills + an orchestrator that produce citation-backed markdown artifacts under a per-deal directory.

## Install

In a Claude Code session:

```
/plugin marketplace add /Users/ykliao/Workspace/dudu
/plugin install dudu@dudu
```

(Substitute the actual path on your machine. Once published, this becomes a git URL.)

## Prerequisites

- The Playwright MCP server must be installed and enabled. Skills that touch LinkedIn or Crunchbase use it to drive *your own* authenticated browser session — they do not store credentials and do not bypass site authentication.
- WebSearch and WebFetch tools must be available (default in Claude Code).

## Skills

| Skill | What it does | Output |
|-------|--------------|--------|
| `dudu:diligence` | Orchestrates the full workflow on one deal | `deals/<slug>/MEMO.md` |
| `dudu:founder-check` | Public-web + LinkedIn dossier per founder | `deals/<slug>/founder-<name>.md` |
| `dudu:market-problem` | Deep context + persona self-play (rehearsal) | `deals/<slug>/market-problem.md` |
| `dudu:customer-discovery` | `prep` builds target list + scripts; `debrief` synthesizes real interviews | `deals/<slug>/customer-discovery*.md` |
| `dudu:competitive-landscape` | Competitor matrix, incumbent threat, moat analysis | `deals/<slug>/competitive-landscape.md` |
| `dudu:market-sizing` | Bottom-up TAM ignoring founder claims | `deals/<slug>/market-sizing.md` |

Each skill can be invoked standalone, or run all together via the orchestrator.

## Typical workflow

1. **Start the diligence:** invoke `dudu:diligence` and answer its prompts (slug, company, founders, pitch, optional deck).
2. **Wait for the prep phase to complete.** Five skills run, taking ~15–45 minutes depending on the deal complexity and your network access.
3. **Read the prep output.** Especially `customer-discovery-prep.md` — the candidate list, outreach templates, and interview script.
4. **Run real customer interviews** (5–10 of them). Save transcripts/notes under `deals/<slug>/inputs/`.
5. **Re-invoke `dudu:diligence`.** The orchestrator detects the inputs, runs `customer-discovery debrief`, and stitches `MEMO.md`.

## What's NOT in v1

- Founder reference checks via your personal network (out of scope — that's a calendar task, not a skill task).
- Paid-API integrations (Crunchbase Pro, PitchBook).
- Auto-generated investment-committee slide decks.
- Multi-tenant deal sharing across a partnership.
- Hybrid VC-in-the-loop persona interviewing (deferred).

## Repository layout

```
.claude-plugin/        plugin and marketplace manifests
skills/                six SKILL.md files
lib/                   shared procedural docs (deal schema, Playwright UX, research protocol)
scripts/lint-skills.sh frontmatter + lib-reference linter
tests/lint/            linter test fixtures and runner
docs/superpowers/      design spec and implementation plan
deals/                 per-deal artifacts (gitignored)
```

## Development

Run the linter before every commit:

```bash
bash scripts/lint-skills.sh
```

Run the linter test suite:

```bash
bash tests/lint/run.sh
```

## License

MIT
````

- [ ] **Step 2: Verify markdown is parseable**

Run: `python3 -c "open('README.md').read(); print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Expand README with install, prerequisites, and workflow walkthrough"
```

---

## Task 13: End-to-end install validation

**Files:**
- (No files modified; this is a verification task.)

- [ ] **Step 1: Run the full linter**

Run: `bash scripts/lint-skills.sh`
Expected: `OK: 6 skill(s) lint-clean`

- [ ] **Step 2: Run the linter test suite**

Run: `bash tests/lint/run.sh`
Expected: four `PASS` lines, exit 0.

- [ ] **Step 3: Validate JSON manifests**

Run: `python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); json.load(open('.claude-plugin/marketplace.json')); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Verify directory layout matches the plan**

Run:

```bash
find . -type f \( -name "*.md" -o -name "*.json" -o -name "*.sh" \) ! -path "./.git/*" ! -path "./deals/*" | sort
```

Expected: matches the file structure section at the top of this plan.

- [ ] **Step 5: Manual install in a fresh Claude Code session**

Outside the plan, the engineer runs:

```
/plugin marketplace add /Users/ykliao/Workspace/dudu
/plugin install dudu@dudu
```

Expected: install succeeds, all six skills (`dudu:diligence`, `dudu:founder-check`, `dudu:market-problem`, `dudu:customer-discovery`, `dudu:competitive-landscape`, `dudu:market-sizing`) appear in the available-skills list.

- [ ] **Step 6: Final commit if anything changed during validation**

```bash
git status
# If clean, no commit needed.
# If files changed during smoke testing fixes:
git add -A
git commit -m "Fixes from end-to-end validation"
```

---

## Self-review (completed inline before publishing this plan)

**Spec coverage:**

- ✅ Plugin shape and namespace → Task 1
- ✅ `lib/deal.md`, `lib/playwright-auth.md`, `lib/research-protocol.md` → Tasks 2, 3, 4
- ✅ `dudu:founder-check` → Task 6
- ✅ `dudu:market-problem` (3 phases) → Task 9
- ✅ `dudu:customer-discovery` (prep + debrief) → Task 10
- ✅ `dudu:competitive-landscape` → Task 7
- ✅ `dudu:market-sizing` → Task 8
- ✅ `dudu:diligence` orchestrator (with pause for real interviews + cross-artifact synthesis) → Task 11
- ✅ Per-deal directory + manifest schema → defined in `lib/deal.md` (Task 2), enforced by every skill
- ✅ Citation rules and source honesty → `lib/research-protocol.md` (Task 4), referenced by every skill
- ✅ Playwright auth UX → `lib/playwright-auth.md` (Task 3), referenced by founder-check / competitive-landscape / customer-discovery
- ✅ Idempotency → defined in `lib/deal.md`, enforced by every skill
- ✅ Build sequence (founder-check first to validate Playwright pattern) → Tasks 6 → 7 → 8 → 9 → 10 → 11
- ✅ Linter + tests → Task 5
- ✅ README walkthrough → Task 12
- ✅ End-to-end install validation → Task 13

**Open questions deferred from the spec:**
- Self-play implementation (single long prompt vs multi-turn loop) → resolved in Task 9: multi-turn, one round file per round, driven by skill body.
- Manifest update ownership → resolved across tasks: each skill updates its own `skills_completed` entry; orchestrator does not write on behalf of sub-skills.
- LinkedIn / Crunchbase Playwright selectors → discovered during smoke tests in Tasks 6, 7, 10. Skill bodies tell Claude to take a snapshot and re-orient when selectors change rather than embedding brittle selectors.

**Placeholder scan:** No "TBD", "TODO", or "implement later" tokens remain. Every skill body is reproduced in full inside its task. Linter code is complete.

**Type / name consistency:**
- Manifest key `customer-discovery-prep` (Task 2 schema) → matches the update site in Task 10 prep. ✓
- Manifest key `customer-discovery-debrief` (Task 2 schema) → matches the update site in Task 10 debrief. ✓
- Skill name `competitive-landscape` (directory + frontmatter) consistent across Tasks 7, 11, 13. ✓
- All artifact paths in `lib/deal.md` match the artifact paths each skill writes to. ✓

---

## Execution handoff

Plan complete. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration. Best for a plan this long because the main session stays clean.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch with checkpoints.

Which approach?
