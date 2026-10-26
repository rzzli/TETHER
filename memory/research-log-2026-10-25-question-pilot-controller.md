---
name: research-log-2026-10-25-question-pilot-controller
description: Frozen pilot controller under validation; source/config/payload/budget and cleanup corrections
metadata:
  type: project
---

# Question pilot controller — work in progress

Separate run_question_development.py prepares the two fixed generic question
families and exposed source subsets, pins protocol/reference/model/code/requests,
and controls owned-server startup, default shared budgets and prediction sealing.
No real model/process/network execution occurred in this implementation phase.

Independent methods probes reproduced five defects beyond initially passing tests:
lost process ownership on log-close failure; dispatch of a request differing from
the frozen task; unrecorded final seal-write failure; config/payload drift after a
pin check; and acceptance of a resealed task budget contradicting the shared plan.
Root regressions reproduced each before correction. A later startup/health cleanup
probe also exposed primary-interruption masking, fixed by reusing the qualified
primary-preserving transport context helper. Ownership transfer, composite
pre-dispatch request/config-byte/payload gates, protected finalization/failure
fallback and exact task budget reconciliation now pass23 focused tests. Original
failed reviews remain under data/cache/question-pilot-controller-review-20261025/.

The composite callback delegates to the unchanged qualified native transport.
verify_predictions source-replays individual runs and checks the frozen plan,
task identities, code/config/payload, lifecycle proofs and aggregate journal usage.
Budget time uses declared monotonic elapsed time, without physical-clock or remote
execution attestation. Known failure state blocks a retained prediction seal.

Initial full/isolated checks were cancelled after the cleanup finding;205 no-site
tests passed on that earlier snapshot and do not qualify the corrected release.
The stopped attempt and its reviewed code copy are explicitly retained. Final
independent cleanup recheck passes23 focused tests/11 independent groups, with all
six findings resolved. Fresh299 isolated/207 no-site tests and1,262 full tests,
required probes/package pass on unchanged code. A helper date typo affected only
output paths; original reports/helpers and corrected aliases are retained.
Real-source plan question-development-20261026T023832Z is frozen with requests
identical to prior sizing/recorded scope. Acceptance and plan metadata are under
planning/review-assets/question-pilot-controller-20261025/. At the checkpoint,
execution was unrun; backup preceded it.91 entries, ZIP CRC/every-entry SHA256 and Git bundle
through03f9a9e verified; manifest SHA256:
f470346c9ada45bf6e04528cb9944776709d95cb25b4d7d713635c921cbf8423.
The receipt/status commit follows that bundle. Next is this bounded real-source pilot,
then two independent AI scientific reviews and third adjudication. Prior failed
scientific gates,65 missing inputs, full T6/H5 and original Tasks6–8 remain open.

## Actual once-only attempt

The pilot subsequently executed one native call (4650 input/601 output tokens,
provider$0) and failed contract validation: partial/null reason plus two paraphrased
source_report texts. Source readmission, frozen payload/native bytes, completion
and prompt/settings binding replayed correctly. Measured accounting is retained,
second MR task unrun, no success receipt/predictions seal, owned server stopped and
PID32688 independently absent. Original draft was sealed without repair at
data/benchmark/labels/question-development-review-20261026/attempt-v1/failed-candidate-seal.json,
SHA256:fc24543281d18bb8314adfe4a683d9067265b5975e221352ba5aea232b82c0b0.

Two independent AI scientific reviews each cover all40 leaves with matching
values/fingerprints and sealed outputs. Both credit the qualified proposals but
flag the first citation and omitted provided mechanisms; they disagree on whether
qualified no-specific-context prose is contradictory or ambiguous. Third
adjudication is now sealed, SHA256:
80342d060e010ac5b2127dbdfdbcb91dc683c941295300e76545002fd3212019.
It accepts qualified ambiguity/major omission rather than critical unequivocal
denial, retains citation/applicability defects, and fails usefulness. Root replay
checks40 leaves/13 clauses/12 source-passage occurrences,16 evidence references,
29 sealed output proofs and all decoded UTF-8 spans. MR remains unknown/unrun.
The guide states partial needs a reason but does not define
source_report as verbatim; native schema leaves both cross-field rules unenforced.
This does not authorize validator relaxation, response repair or a retry of the
failed version. Interface diagnosis is separate from scientific usefulness.

Next generic wire repair was independently reviewed by scientific/methods agents:
choose pointer-only verbatim_quote, transparently copy selected source text into
qv2 source_report and preserve every generated proposition/limitation/applicability.
wire_version2/disjoint state branches and all gates are recorded under
planning/review-assets/question-wire-repair-20261026/. Projected337-byte guide has
only16 bytes margin; actual fit unproved. Existing receipt-verified b11717 CLI
help-only converter probe (no model path/load/generation) accepts state branches
but warns that the proposed nonblank regex is ignored. Pinned-converter feasibility
review is active; generation remains blocked. No validator relaxation or extra
native model call occurred. Broader scientific qualification and Tasks6–8 stay open.

Related: [[research-log-2026-10-25-question-native-transport]], [[project-goals]].
