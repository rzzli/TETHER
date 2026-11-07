# Installed source reconstruction checkpoint

1 November 2026. **P09c and P09d pass in their explicit local scopes.** Author declarations
remain deferred by the owner, and the paper remains a working draft. No external
expert input is required. Nothing is published or pushed.

**Revision 2 update:** the final protocol is
`e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529`.
Its separate reconstruction/audit took 289.938s/15.187s and passed 6,862 source
checks; the metadata review passed 3,481 checks. All 38 raw outputs and 12 reference
files are byte-identical to the first revision. The corrected `-B` test command
passes 82 tests/182.260s and leaves its 312-file bundle unchanged. Only the frozen
README and new authority changed; all 310 other bundle members remain identical.
The revised draft passes 3,149 checks for 311 members/20,486,682 bytes.

The first two broad full/core attempts exposed test-harness issues and Windows
file-access failures; those failed reports remain retained. Third full/core runs
at `3629337` now pass: full 1,973 tests/zero skips; core 1,973 collected/94 approved
optional skips. Both pass probes and offline package/demo. Independent gate review
passes 349 checks. Two fresh 315-member ZIP builds match (`f4d7ab4b`);
independent archive review passes 1,595 checks with no unresolved findings.
The archive is 20,712,230 bytes; its external hash and qualification records are
under `paper/release/`. No public deposit or current hosted result exists.
The initial revision's metrics below are retained historical evidence.

## Initial revision retained for history

The separately versioned `tether-p05-replay` 0.1.0 was built with cached setuptools 84.0.0
and installed with unchanged TETHER 0.3.11 and Arrow 21.0.0 into a fresh C: environment,
outside the checkout and original D:/E: roots. Python 3.11.15 `-I` imports resolve
to that environment and its C: base runtime. Installation was offline, using copied
package files rather than cache hardlinks.

All 137 complete originals (2,866,248,239 bytes) and 137 exact receipts were copied
into the qualification location, with source/destination hashes checked. The first
reconstruction under a new externally pinned READY reproduces all 38 raw-output
hashes and 90 decisions. Independent source-inclusive audit passes 6,862 checks;
additional sealed-output peer review passes 2,400 checks. Neither has unresolved
findings. P06 was not rerun: these are new computations under a separate reproduction
authority after exposure to the original result.

| Evidence | Result |
|---|---|
| Protocol |`650859b151bee4a98d6da8c779a7b498720929bfe1e7218d5e6f426f78cea123` |
| Reconstruction report |`8d29f8dcf27985acfe021548657d0c69c5e6d007913008f4cb061c352ae15db3` |
| Reconstruction receipt |`700895c7890d985448941fc37e089e51b80f379d7e617d6d87b707b563420361` |
| Independent audit report |`9623f1824f5c5f4582355082c66082566ee44787090cccb1db514ede8f9caed5` |
| Independent audit receipt |`7cc8886e27fed8dd47ffd0a71ca7347f38c5ce1f06e47051d3098e5a49f6cc3e` |
| Installed shipped tests |82 passed/177.468s, zero failures/errors/skips |
| Original P05 regression suites |199 passed/110.489s, zero failures/errors/skips |
| Reconstruction process |229.422s wall/222.671875s CPU/477,118,464B checkpoint lifetime peak |
| Independent audit process |14.953s wall/14.796875s CPU/298,065,920B checkpoint lifetime peak |

See [acceptance](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/preprint-p09-20261101/ACTUAL-RECONSTRUCTION-ACCEPTANCE-v1.json)
and [peer review](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/preprint-p09-20261101/ACTUAL-QUALIFICATION-PEER-REVIEW-v1.json).
Exact receipt-verified archive copies remain in the ignored
`data/derived/preprint-p09-installed-20261101T205500Z/`: 156 reconstruction files and
3 audit files. The C: temporary originals/environment remain available.

## What passed and what remains limited

All 12 literal reports are exact and complete at the frozen 60/80/100% thresholds,
with no critical errors. Abstention emits no facts and completes 0/12. Availability
remains 108/132 identity slots and 40/48 measurement slots, with 32 native nulls across
180 facts. The 14 constructed controls retain 0/10, 2/10 and 7/10 invalid admissions under
FULL, WITHOUT_WRAPPER and WIRE_ONLY; valid rejection is 0/4 each. The 90 decisions
contain 57 admissions/33 rejections. Two malformed controls remain malformed;
35 outputs receive core scores.

The minimal public catalog changes genuine reference fingerprints. The approved
equivalence removes only `method.catalog_sha256`; every other reference/task/source
field remains covered. All 12 references pass. New G0 authenticates the new authority
and generated artifacts; unavailable old private archives are not byte-verified.
The auditor independently projects sources/scores without producer policy/baseline/
control imports, but shares core contracts, provenance, serialization, stable-read
helpers and field taxonomy. This is technical independence, not scientific adjudication.

The 311-member draft allowlist passes 3,144 checks and includes source, two project
wheels, rights cards, neutral configuration, evaluator-only comparison, 37 exact
numerical/table/figure payloads, and new portable README/manifest. The exact 17 MB HGNC
CC0 original is an explicit exception. All 136 OT originals remain external; fresh
exact-byte reacquisition is untested. No model/font binaries, human-response
descendants, protected outcomes or private journals are bundled.

Policy counters record 2,866,364,290 logical hashed bytes and 2,866,248,239 original
compressed bytes scanned. These exclude repeated core reference replay and are
**not total process I/O**. Audit counters record 2,896,929,829 logical hashed bytes and
one original row pass. Physical I/O/platform cost remain unknown. Peaks are Windows
lifetime checkpoints; elapsed installed-test time overlaps both framework gates.
These are not hardware performance comparisons. The original unmeasured reference-
producer memory remains unmeasured.

The working manuscript PDF is supplied as retained output; its original renderer/
fonts are not in the portable package. The standalone presentation exporter recreates
37 historical payloads. Its new README/manifest deliberately replace old machine-
path versions. Current-code hosted checks are unexecuted. Scientific validation,
study independence, genetic causality and clinical utility remain unestablished.

## Full-project status and next actions

| Programme | Status |
|---|---|
| v2 framework, ten T6 dossiers and source audit |Implemented within technical limits; features empty/probabilities null |
| P04 model pilot and conformance control |Closed negative; no more calls/scaling |
| P05-P07 deterministic study and original results |Complete/audited; 78 code pins, results, catalog and working PDF unchanged |
| P08 manuscript/supplement/PDF |Technical checks passed; author declarations deferred |
| P09 installed source reconstruction |Passed, including final full/core gates and deterministic allowlist ZIP; local Windows scope only |
| P10 local submission preparation |Pending release checks and owner facts; no publication authorized |
| Clinical H1-H4, MR/scorer/full Virtual Biotech, T2-T5/H6 |Conditional later programmes, not completed by this preprint |
| Original expert-preference H5/HR1-HR4 |Retired dependency and untested; no new response collection |

Recovery-plan accounting (original definitions retained in the dated recovery plan):

| Item | Current disposition |
|---|---|
| R01 Scope |Bounded technical preprint accepted; broader hypotheses remain separate |
| R02 Checkpoint |78 P05/100 package pins intact; installed evidence and final local release gates pass |
| R03 Archive/relocation |New Windows public reconstruction qualifies; old private archive G0 explicitly separate |
| R04 Correctness |Base fixes retained; new auditor journal/bridge and wheel-closure defects reproduced and fixed |
| R05 Diagnostic design |Frozen rules retained; no further model branch |
| R06 Study infrastructure |Actual installed137-original reconstruction and separate source audit now pass |
| R07 Capability |Six complete responses/zero frozen-contract passes; negative unchanged |
| R08 Fresh feasibility |No certified fresh scientific cohort;12 technical units have unqualified study independence |
| R09 Interpretation arms |Original FAILED/INCOMPLETE_TIMEOUT retained; P04/P04b model branch closed negative |
| R10 Timed development |Bounded negative development retained; original expert-aligned scientific pilot untested |
| R11 Protocol/sample size |Technical 38/90 schedule/descriptive endpoint frozen; no independent-study power claim |
| R12 Execution/report |P06/P07 accepted; new source reproduction passes; original expert-preference H5 untested |
| R13 Clinical feasibility |Earlier 17/32 observable registry states are not qualified clinical labels |
| R14 Genetics/scorer |MR, causal features, training/calibration deferred; real predictions null |
| R15 Clinical comparison |Locked clinical/full Virtual Biotech evaluation uncompleted |
| R16 Extensions/release |T2-T5/H6 conditional; P08 factual declarations deferred, P09 complete locally, P10 pending |
| HR1-HR4 |Retired as dependencies; response descendants archive-only and excluded from new inputs |

Next: perform paper-to-artifact checks, separately version the updated working
paper/PDF and prepare the local working package. P08c/P10 facts remain pending. Keep 65
missing interpretation inputs, 36 unqualified clinical endpoints, 17/32 observable
registry states and 0/12 jointly source-ready packages distinct. No new acquisitions,
models, paid queries, original-worker changes or monitor restart occurred. Provider spending remains $0.
