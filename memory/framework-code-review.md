---
name: framework-code-review
description: Original runtime review and current v0.2 correction status
metadata:
  type: project
updated: 2026-10-11
---

# Framework code review and next stage

## Current correction status — October 11

The five v0.1 correctness findings are addressed with v2 contracts, immutable evidence, preflight, hypothesis-scoped features and durable journals. The later full-project audit reproduced three further verification defects: contradictory run accounting, journal/ledger claim mismatch and omitted raw-parent proofs. Regressions were written before correction; current verification reconciles execution and complete source ancestry and reuses admission rules. Optional receipt auxiliary outputs seal new CLI request files while preserving archived v1/v2 verification.

The updated review utility uses explicit fictional v2 fixtures and checks the effective archived catalog policy with labeled receipt fixtures. Its current passing report is [[planning/review-assets/framework-review-v02-2026-10-11-passed.json]]. Initial utility runs exposed an obsolete fixture assumption (historical inputs without raw receipts); that probe was corrected. The original v1 report remains unchanged.

[[Project Audit and v0.2 Completion]] is the current retained correction/status report. The pinned adapter preserves reported contexts, filters Arrow batches before Python conversion, archives exact receipt bytes and journals build failures. The real ten-case pilot remains scientifically unreviewed; the source audit checks normalization fidelity. The standalone evaluator still supplies descriptive metrics, not locked cohort/prospective provenance.

## Original October 10 review history

The user requested reviewing the current code and making the next-stage plan. The report
is [[Framework Code Review and Next Stage Plan]], supported by
[[planning/review-assets/framework-review-2026-10-10.json]]. Runtime files were read and
fingerprinted but not changed. The existing 51 tests still pass; ten separate fictional
probes reproduced five correctness issues and four integration gaps.

Correctness issues: T6 skips dates on supplied program context; frozen records contain
mutable dictionaries and verification misses semantic output/source bindings;
case-dependent features are not bound to action/modality/context; TimeoutError/ValueError
can lose attempts/usage/artifacts; scorer cutoff checks occur after backend calls.

Integration gaps: descriptive evaluation has no locked prediction provenance; receipts
omit the admission catalog and backend/environment inputs; scorer-facing missingness
collapses distinct coverage reasons; newly computed results need creation dates separate
from eligibility of their historical inputs. The last distinction is necessary to permit
new fixed methods on old information without allowing later evidence or annotations.

Recommended v0.2: harden temporal/immutable/provenance/failure contracts, then ten reviewed
real-data development dossiers via bounded ingestion, with optional provider/replay
selection. Keep probabilities withheld until scorer training/validation. Estimate 10–16
engineering days with one engineer and part-time biological review. Historical cohort and
locked evaluation add 5–8 days after usable snapshots and access; access waiting is not
included. No current-model historical run is claimed clean of pretraining contamination.

No live provider calls, scientific analyses, new biomedical downloads, account actions or
download checks occurred. Official Arrow documentation supports bounded batch reads.
Two AACT browser requests failed; no archive was restored and this is not proof of
unavailability. Preserve stopped monitoring and check downloads only when requested.

Related: [[project-goals]], [[research-log-2026-10-10]], [[docs/FRAMEWORK]],
[[asof-feasibility-findings]], [[data-acquisition-plan]].

