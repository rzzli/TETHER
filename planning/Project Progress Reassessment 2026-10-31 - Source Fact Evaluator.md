# Project progress after the source-fact evaluator

31 October 2026, America/Los_Angeles. Reviewed baseline `6489ea0` plus the new
study modules. **P03 engineering acceptance is complete. The preprint, qualified
scientific measurement endpoint and new model comparison are not complete.**
The next dependent stage is P04, a bounded development comparison with separate
generation inputs and an executable, prospectively frozen protocol.

## What is now implemented

The [reporting contract](../docs/SOURCE_FACT_EVALUATION.md) defines a separate
source-reporting eligibility/composition/missingness/resource study. It preserves
nullable intervention context and explicitly declares exact projection as the
ceiling. Its primary is **group-weighted verified reporting completion**, not the
old unweighted H5-A slot statistic, original expert preference or biomedical
truth. Raw component counts and measurement-family outcomes remain separate.
This development amendment was made before any new candidate generation; the
initial contract and later clarifications are retained.

| Component | Accepted scope and evidence |
|---|---|
| Source compiler/replay | Complete v2 graph, catalog role, source/receipt and temporal checks; explicit additional raw-root approval; source identities/locators; original typed fields and native units; publication eligibility; direct/transitive deny policy; stable reads and replay |
| Composition and missingness | Fixed field taxonomy; exact same-release selected-record joins; zero/one/multiple/conflicting outcomes; no first-row resolution; schema absence/null/empty/QC/join unknowns distinct; no full-release or biological absence inference |
| Common output adapters | Strict retained-byte typed output; no source/value lookup, quote expansion, omission insertion, deduplication or repairs; legacy prose explicitly unscorable for typed facts |
| Shared scorer | Equal-weight answerable groups, common source-bound denominators, strict type/signed-zero/unit/source/unknown checks; explicit abstention and insufficient-input handling; zero measurement denominator null |
| All-cell accounting | Returned/malformed/failed/timeout/interrupted/unexecuted records; raw hashes; no rescue by parseable partial bytes; missing/duplicate/unscheduled/substituted terminal cells rejected |
| Portability boundary | JSON-only dependency-free installed API smoke outside the checkout; logical source paths and same-byte root relocation; Windows original-sharing locks retained, non-Windows lock capability fails closed |

The new APIs are `source_fact_sources`, `source_fact_adapters` and
`source_fact_evaluation` under `asof.study`. Existing defaults, native interfaces,
archived outputs/verifiers, prediction features and probabilities are unchanged.
This is a development addition to the 0.3.11 base, not a final new software release.
The test wheel retains version metadata 0.3.11; its exact wheel hash identifies
this development build and it must not be substituted for earlier same-version
archives. Release versioning and exact-SHA full qualification remain P09 work.

## Verification and corrections

The retained [targeted run](review-assets/preprint-p03-20261031/TARGETED-TESTS-v1.json)
passes **173 tests with zero failures/errors/skips**: 99 new controls and 74
relevant legacy regressions. Sixty new controls were independently authored.
This does not mean the complete application suite was rerun. The earlier accepted
1,774-test/327-pin baseline remains historical evidence: 326 old pins still match;
`tools/validate.py` has one reviewed correction. New study files are additional.
Six separate validation-gate tests also pass (four new/two legacy).

Tests first exposed unreachable valid-output cases: overlong task/source IDs,
native units or context values could compile but could not pass the adapter.
The compiler now checks complete literal-projection representability under the
same output limits. Other finite corrections enforce native numeric measurement
QC and integer p-value exponents, same-release selected joins, unit-dependent
join conflicts, catalog/deny/snapshot binding and approved raw-root separation.
A broader structural check also found an intentionally invalid archived
`before_syntax.py` original being treated as active code. Its exact bytes are
preserved; an exact-path/exact-hash exception classifies only that failed original
as audit data. Four new tamper/alternate-path/active-syntax tests and two legacy
validation-policy tests pass; an independent peer found no suffix bypass. All
other Python artifacts still must parse.

Initial missing-module, sandbox TEMP/cache and fixture-contract failures remain
retained; they are distinguished from production assertion defects.

The [installed smoke](review-assets/preprint-p03-20261031/INSTALLED-SMOKE-v1.json)
built a wheel entirely offline using existing setuptools 84.0.0, installed it in
a fresh environment under the permitted C: visualization root, and passed
source compilation/replay, signed-zero rejection and three-cell accounting with
no Arrow installation. It is a fictional mechanical smoke, not new model data or
the final research release. The failed initial uv cache attempt is preserved.

## Actual-format source result

The [actual-source report](review-assets/preprint-p03-20261031/ACTUAL-SOURCE-REPLAY-v1.json)
retains one already fixed, exposed CTLA4/Crohn source row. The compiler read the
receipt-verified original Parquet row and both source-inclusive replays passed.
A separate fresh checker verified all 15 projected facts, types, groups, bindings
and unknown reasons directly against the selected original row. Identity has
7/9 answerable fields, context 2/2 and measurement **0/4**: three native nulls and
one schema-absent field. Measurement coverage/pass remain null.

The reference SHA-256 is
`a0e18937d15603cd3008b613ec1bd3ef23df2383a7b43ff037d6e164b563c41e`.
The original is 1,816,029 bytes. Its transport receipt, new approved E: archive
copy and private D: copy are byte-equal at 841 bytes. This filesystem-only archive
did not start the downloader, alter its receipts/state or authorize the pending
23-file batch. All new answer-bearing artifacts remain ignored, evaluator-only
and unavailable to generation. Prior row-projection exposure is disclosed.

Reported compile/replay times concern this selected row, not corpus ingestion.
Peak RSS, physical I/O and total platform costs are unmeasured. Independent
checking does not authenticate publisher checksums, unknown upstream namespace
versions, first-public history, undisclosed ancestry, timing chronology or
scientific validity. Trusted catalogs, deny lists and Python code remain trust
boundaries, not semantic laundering detectors or an OS sandbox. Deadlines are
cooperative; existing graph hashing finishes before its next check.

## Whole-project disposition

| Workstream | Current disposition |
|---|---|
| R01–R06 | Prior engineering/preparation accepted in their recorded scope; current source-reporting addition separately tested |
| R07 | Six complete responses/zero frozen-contract passes unchanged; optional retrospective appendix, no repair/retry |
| R08 | Exposed source frame and measured P02 limits retained; zero qualified fresh evaluation cases |
| R09 | P03 shared evaluator now implemented; previous recorded/v3 preparation is not successful generated interpretation; native FAILED/INCOMPLETE_TIMEOUT unchanged |
| R10/P04 | New bounded pilot is next; no new model output or measured model-comparison result yet |
| R11/P05 | Cohort/exposure/cluster qualification, conservative sizing/precision and analysis freeze incomplete |
| R12/P06–P07 | Locked comparisons, ablations, secondary AI audits and reproducible main-paper analysis incomplete |
| R13–R15 | Clinical/genetics/scorer/comparator routes remain conditional; 65 missing interpretation inputs, 36 unqualified clinical labels, 17/32 primary observable states and 0/12 joint-ready packages are distinct unresolved scopes |
| R16/P08–P10 | Manuscript, figures/bibliography/supplements, portable lawful release and final preprint audit incomplete; T2–T5/H6/full Virtual Biotech reproduction deferred separately |
| HR1–HR4 | Retired, not waiting or completed; all bespoke responses and response-aware descendants excluded |

No new model/provider spending, clinical prediction feature or probability was
introduced. Existing downloader/stopped monitor remain untouched. P02a's isolated
2.43 GB source completion is still optional and awaiting one-time approval after
the retained automatic-review rejection; the 841-byte archive is a separate
already-authorized preservation action, not a download workaround.

## Next major step: P04

1. Revalidate the existing permitted generator/runtime path and current files or
   live handle without starting old jobs. A new named typed-report protocol must
   not inherit failed v3/native conformance or claim a stronger-model control.
2. Build generation packets directly from eligible originals and a neutral
   predeclared task, independently of evaluator references or their descendants.
   Record source/case selection and every exclusion; use 2–4 exposed development
   units, including bounded missing-input handling. No freshness claim.
3. Implement the exact literal assembler/always-abstain controls using only
   generation inputs. Compare any feasible same-model plain and AsOf workflows
   under matched evidence and existing budget defaults. An adapted Virtual
   Biotech prompt must be labeled as an adaptation, not a full reproduction.
4. Freeze all cells, prompts, outputs/adapters, primary contrast, masks, caps,
   failure rules, source/analysis versions and resource measurements before new
   calls. The maximum permitted cost remains $0; no paid adapter/model acquisition.
5. Run each declared cell once and preserve every terminal result. Retain raw
   bytes, measured/estimated usage separately and source-inclusive replay. Compare
   completion, false rejection, reporting/missingness and overhead against the
   extractive ceiling; do not claim improved interpretation from copying.
6. If no generator path qualifies within the existing resources, retain that
   concrete negative feasibility result and complete the deterministic study
   component. Choose an explicitly limited feasibility report before P05; do not
   restart old failures or open a native-proof expansion merely to rescue results.

P04 acceptance needs an executable protocol, every scheduled cell accounted,
independent source/evaluator isolation, actual feasible arms and retained resource
evidence. More unit tests or a reference schema alone cannot close it. P05 then
requires a prospective candidate/exclusion register, exposure crosswalk,
study/article/locus/family clusters, actual sufficient/insufficient counts and a
precision objective with an explicit exploratory fallback.
