# PMF signal: render-report-good

**Deal:** render-report-good
**Generated:** 2026-04-29T10:57:34Z
**Population:** N=10 across 1 frames; 9/1 grounded-vs-fabricated split
**Claims tested:** 6 (persona-reaction: 2, cross-artifact: 3, external-evidence: 1)

> ⚠️ This report is a CALIBRATED PRIOR, not signal. Persona-reaction aggregates are LLM aggregates over a structured synthetic population — hypotheses to falsify in real customer interviews. Cross-artifact verdicts triangulate against prior dudu research. External-evidence verdicts are best-effort web checks bounded at 5 fetches per claim — anything forensic is flagged `requires-data-room`. Read the verdict's verification method before drawing conclusions.

## Headline read

[FILL ME — top 3 sentences capturing the strongest pattern, strongest contradiction, largest cluster verdict.]

## Consolidated claim ledger

The full ledger of every claim made by founder/company, sorted by severity (worst news first).

| Claim | Source | Category | Verdict | Verification method | Strongest evidence |
|---|---|---|---|---|---|
| no direct competitors in SA | deck p.6 | competitive | **contradicts** | cross-artifact | Pastel-to-Xero migration firms compete directly |
| 200 paying customers | deck p.4 | customer-count | **insufficient-evidence-for-200** | external-evidence | public surface area inconsistent with 200 |
| co-founder previously exited to Stripe | deck p.2 | founder-background | **partial** | cross-artifact | exit happened but no shareholder return |
| addressable market is $50B globally | deck p.5 | market-size | **partial** | cross-artifact | global TAM band per market-sizing is $12B-$28B |
| SA freelancers lose 2 days/quarter to SARS | deck p.3 | pain | **agree** | persona-reaction | "Two days minimum" (7/10 personas) |
| buyers find us via accountant referrals | deck p.9 | gtm-distribution | **disagree** | persona-reaction | "My CA would never recommend a tool that replaces his work" (9/10 personas) |

## Pitch-reaction aggregates

| Metric | Value | n | σ | Grounded n | Notes |
|---|---|---|---|---|---|
| would_use = yes | 40% | 10 | — | 9 | (n=4 of 10) |
| willing_to_pay = yes | 30% | 10 | — | 9 | (n=3 of 10) |
| WTP ceiling (median, ZAR/mo) | 10000 | 3 | — | 3 | (3 personas anchored a number) |

## Cluster patterns (by trigger_type)

### Cluster: regulatory-growth-collision (n=6)

[FILL ME — mean pain, dominant phrase, would-pay rate, top objection, top resonance quote with persona_id citation.]

## Strongest contradictions

[FILL ME from the contradicts/disagree rows.]

## Weakest assumptions in the founder's pitch

[FILL ME — pull contradicts/partial verdicts from ledger above.]

## Verifications that need a data room

[None flagged.]

## Population audit

- Total personas: 10
- By frame: x.pmf-validation=10
- By trigger type: regulatory-growth-collision=6, switching-cost=4
- Refusals (couldn't ground): see `personas/refusals.md`
- Fabrication flags: 1
- Mode-collapse check: pass

## Source artifacts

- pitch.yaml (claim ledger)
- personas/_context.md
- personas/frames.yaml
- personas/rows/*.yaml
- personas/reactions/*.yaml
- personas/verdicts.yaml
- personas/refusals.md
- (cross-referenced) founder-*.md, market-sizing.md, competitive-landscape.md, market-problem.md
