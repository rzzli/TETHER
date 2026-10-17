---
name: research-log-2026-10-17-claude-review
description: Independent Claude review of the project after the Oct 17 sessions; verification results and the proposed next six weeks
metadata:
  type: project
---

# Research log — Claude review, October 17, 2026

Objective: write a review and plan document and verify the claims of earlier sessions by re-running them, not re-reading
them. Output: [[Claude Review and Plan_claude10172026]]; scripts and raw results in
`planning/review-assets/claude-review-20261017/`.

Sources: the repository, sealed bundles and E: data; publisher checksum files and manifests (Open Targets 25.09 and
22.11); live ClinicalTrials.gov, Europe PMC, PMC, sponsor releases; GitHub (pinned Virtual Biotech commit); Anthropic
model and deprecation pages. No database restart, no download beyond public checksum files and a portable
PowerShell 7.6.7 (scratchpad only), no provider call.

Compared with earlier work: 42 ledger entries tested, none contradicted. Seals (728 files), raw inputs (2,206),
AACT archives (6), Open Targets files (2,205 against publisher SHA-1), 29.8 M scanned rows, 213 traced observations,
the full LD matrix, ten dossier receipts and 173 tests all reproduce. Three summary lines are stale or overstated
(test count, catalog text, "rules applied to all 24"). Sixteen Oct 11 findings: ten closed, three partly open (1, 4, 5), two open by design (2, 3), one reframed (15).

What changed the picture: Oct 17 work is uncommitted with no remote; the v0.3 endpoint makes T1 look infeasible by
definition and 24 cases cannot measure event rates (expected 0.7–4.8 events at 3–20%); a crude pair-level count finds
485–659 transitions in 24 months; Sonnet 4.5 retires 2026-11-30 and current Claude models have June 2026 cutoffs, so
an October 2025 origin with Open Targets 25.09 and a 12-month horizon is the cheap leakage-controlled window.

Uncertainty: crude sizing uses a lagging, comparator-contaminated linkage; AACT snapshot availability near
2025-10-01 is unconfirmed; AI-assisted scientific judgments were not re-adjudicated.

Next: PI decisions D1–D7 in the review; first action is committing, adding a private remote and backing up
`data/benchmark/` and `data/derived/`. Then the registry-scale label-sizing sprint (WP1) before any further per-case
qualification.
