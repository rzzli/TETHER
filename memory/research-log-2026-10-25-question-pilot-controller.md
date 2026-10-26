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
planning/review-assets/question-pilot-controller-20261025/. Execution is unrun;
backup/checkpoint precedes it. Next is this bounded real-source pilot,
then two independent AI scientific reviews and third adjudication. Prior failed
scientific gates,65 missing inputs, full T6/H5 and original Tasks6–8 remain open.

Related: [[research-log-2026-10-25-question-native-transport]], [[project-goals]].
