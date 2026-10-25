---
name: research-log-2026-10-25-question-recorded-runtime
description: Durable recorded question execution, source-inclusive verification and failed-call inspection
metadata:
  type: project
---

# Recorded question runtime

The new question_interpretation_runtime.py reserves output exclusively, admits
sources, dispatches at most once, retains raw text/cap status, separates measured
usage and conservative estimates, re-admits sources before finalization and seals
report/journal/receipt acyclically. The versioned inspector accounts for unresolved
interpretation calls; it never retries. The verifier reconstructs question/source
inputs, checks exact raw responses, journal/configuration/accounting and code
identities including package initializers, with no artifact-driven code imports.

Independent methods audit found four concrete blockers beyond initially passing
tests: secondary journal failure masking a timeout; resealed replay fields accepted
by verifier but rejected by constructor; missing executable package initializer;
and reserved recorded provenance allowing dispatch without full built-in identity.
All were reproduced and fixed with regressions. Cascading accounting/archive-notice/
terminal/close errors preserve the primary exception and use a run-bound best-effort
failure fallback. Known failure state blocks success verification. Constructor and
verifier share strict replay shape/cap/version checks; reserved replay byte/class/
request identity is checked before dispatch. Local code closure includes package
initializers. Legacy modules and question core remain unchanged.

38 focused tests and10 final independent probe groups pass. Actual-source scripted
recorded abstention fixtures finalize/source-verify for both selected questions,
with available9/selected1/missing65 preserved. These are not generated scientific
answers or qualified dossiers. Both old successful native sidecars still verify.
Full1198 tests/probes/package,235 isolated tests and143 no-site tests pass on unchanged code. No new native model call, download,
provider spending, clinical-label read or scientific qualification occurred.

Details: docs/QUESTION_RUNTIME.md and
planning/Question-Bound Runtime and Pilot Gate 2026-10-25.md.
Receipts: planning/review-assets/question-recorded-runtime-20261025/.
Next native renderer/transport and complete escaped/framed prompt sizing require
separate implementation/review before any new frozen pilot. Prior scientific
failure and original Tasks6–8/fullT6-H5/clinical prerequisites remain unfinished.

## Native renderer proposal and final checkpoint

Data-only full prompt proposal sizes14149/12785 bytes fit the prior14200 cap;
complete source requests reconstruct exactly. Both independent reviews approve
implementation feasibility only. A known redundant global newline replacement
can corrupt adversarial source strings; it must be omitted and covered by production
newline/control-token tests. No native adapter or execution is approved here.
Native render review: planning/review-assets/question-recorded-runtime-20261025/native-render-review.json.

Recorded runtime full validation completed with unchanged code and zero tests
failed/skipped. Legacy native sidecars and both recorded fixtures source-verify.
Next implement the deterministic renderer/source alias layer, then native transport
and exact production sizing before a new frozen scientific pilot. Project goal
and scientific qualification remain unfinished.
