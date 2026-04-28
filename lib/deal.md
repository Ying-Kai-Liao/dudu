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
