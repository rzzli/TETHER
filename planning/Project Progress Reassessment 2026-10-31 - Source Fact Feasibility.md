# Project progress reassessment after the source to fact prototype

31 October 2026, America/Los_Angeles. P02 now has measured, retained source-feasibility results for three exposed development units. **The bounded prototype is complete; the intended target-linked statistical measurements are not yet available in the inspected local subset.** This is a data/collection limitation, not a request for expert judgment. P03 implementation and the later paper experiments remain incomplete.

The [paper roadmap](Preprint%20Readiness%20Review%20and%20Completion%20Plan%202026-10-31.md) and no-external-expert policy remain controlling. No new model run, clinical feature, calibrated probability or scientific interpretation result was created.

## Actual work and results

| Check | Inputs and measured result | Interpretation |
|---|---|---|
| Fixed literature prototype | Six pre-response-selected Open Targets 25.09 Europe PMC rows: three BTK/psoriasis and three CTLA4/Crohn rows. Exact projection matches all 57 populated identity/date fields; 204 scientific-family values are null | Identity/context copying reaches its ceiling. Scientific coverage/pass are null, not a successful zero-denominator result |
| Missing-input unit | FCGRT/Crohn is the first zero-match pair under the retained metadata selector; it has no rows in that selected literature scan | Collection-bounded missingness only. No biological absence or full-release zero is established |
| Additive GWAS check | Prospective frozen plan, same three pairs, 100 already-collected `gwas_credible_sets` files: 1,753,850 rows and 180,049,263 bytes freshly verified. BTK 0 exact matches, CTLA4 1, FCGRT 0 | No cases or null records were replaced. The CTLA4 row has a `studyLocusId`, but no populated measurement components |
| Field-family correction | The legacy prototype's broad scientific-family bucket includes `studyLocusId`; the GWAS report separates that identifier from ten measurement components, all null | A study/locus/variant identifier cannot earn scientific-measurement coverage. P03 must enforce that distinction |
| Local credible-set join | Exact CTLA4 locus key checked across the two local receipt-verified `credible_set` files, covering 230,761 rows / 157,880,681 bytes: zero joins | Catalog/inventory lists 25 files. Local 2-of-25 coverage is incomplete; a missing join cannot establish absence or lack of genetic evidence |
| Positive parser control | Lexical-first local credible-set file, row zero, fixed before inspecting its values: native beta, p-value components and standard error are populated | The parser can read numerical data. This unlinked control is not an additional target case or a CTLA4 effect |

The fixed context identifiers are BTK/ENSG00000010671/EFO_0000676, CTLA4/ENSG00000163599/EFO_0000384 and FCGRT/ENSG00000104870/EFO_0000384. Action, modality and tissue remain unspecified for these reporting contexts. All artifacts and descendants are evaluator-only, exposed development material. No agent-visible evidence manifest was produced.

## Verification and retained evidence

- [Literature prototype](review-assets/preprint-p02-20261031/PROTOTYPE-REPORT-v1.json) and [independent reconstruction](review-assets/preprint-p02-20261031/INDEPENDENT-CHECK-v1.json): all 264 slot structures, 57 baseline answers, 204 schema-present nulls, six source/receipt hashes and deterministic counters match. Ten fictional-control tests pass. The first 9-pass/1-fail log is preserved; explicit unknown handling was corrected without granting coverage credit.
- [GWAS plan](review-assets/preprint-p02-20261031/GWAS-SCAN-PLAN-v1.json), [report](review-assets/preprint-p02-20261031/GWAS-SCAN-REPORT-v1.json) and [independent check](review-assets/preprint-p02-20261031/GWAS-INDEPENDENT-CHECK-v1.json): all 100 hashes/receipts/footer/schema metadata and the selected raw row were checked. Independent verification did not rerun every row-key match; that scope limit is explicit.
- [Credible-set plan](review-assets/preprint-p02-20261031/CREDIBLE-JOIN-PLAN-v1.json) and [report](review-assets/preprint-p02-20261031/CREDIBLE-JOIN-REPORT-v1.json): exact-key scan and fixed parser control replayed; current transport receipts were copied into a hash-bound retained private archive and checked against the originals. OS-enforced immutability was not tested. The original worker/state/receipts were not changed.

Study code and test logs are retained in [the P02 directory](review-assets/preprint-p02-20261031/README.md); original projected values remain in ignored evaluator-only artifacts bound by hashes. The tests are controls, not new biomedical cases. No literal narrative-count extraction, old AI answer, human response or candidate output supplied expected values.

The first run rehashed 486,979,325 original bytes; projected columns covered 1,373,560 row-group rows before selecting six rows/2,364 Arrow bytes for Python conversion. Its 81,671,893 compressed-column bytes are a metadata estimate, not physical I/O. Elapsed time was 0.814 seconds. Python-traced and Arrow allocator peaks are separately reported; neither is process RSS. The GWAS run took about 13.2 seconds, retaining one selected row. No cold-cache or total-cost claim follows from these measurements.

## Concrete missing-input action

The pinned 25.09 inventory lists 25 credible-set Parquet files; 23 are missing locally. HEAD resolution verified all 23 public URLs and exact payload sizes totaling **2,430,231,014 bytes** (about 2.26 GiB). The prepared batch is capped at **3 GiB** and uses separate timestamped raw paths, receipt IDs and a separate state file under the authorized E: root. The originals require compressed storage plus small receipts; no bulk expansion or index is planned. A separate backup would consume additional storage. Both drives had more than 1.5 TiB free at this check; this is not a capacity claim for the entire catalogue.

The batch queue/resolution are in ignored `data/manifests/private/preprint-p02-credible-completion-20261101T031842Z/`. It uses the same Open Targets release and existing public-download tooling, without modifying old files or restarting the periodic monitor. Newly downloaded bytes would retain their actual present-day observation bounds; they would not fill old runs or be backdated to an earlier case origin.

**Automatic approval review rejected starting `Start-DownloadBatch.ps1` for this batch**, citing the retained instruction to leave the existing downloader untouched: isolated paths did not remove that conflict. The command was rejected before process creation. No worker was launched and no dataset payload was downloaded. A one-time approval request for this separate batch is pending; no indirect downloader or alternative transfer is used to bypass the rejection.

After approval, complete and verify only that named batch, then repeat the exact locus join under a new versioned plan/output directory. If the complete same-release table still lacks the key, retain that provider-linkage gap; do not substitute a newer release, a neighboring variant or an unrelated study. A matching locus's statistics would still be reported as linked-locus source values, not a gene-perturbation or drug effect.

This is a **conditional data branch**, not a universal preprint prerequisite. It resolves this exact complete-table join question; it does not guarantee useful measurement coverage, a multicase cohort or a nontrivial endpoint. Task-contract, evaluator-control and introduction/methods preparation can proceed while approval is pending. Before committing to broader experiments, choose either a measurable source-reporting/eligibility/composition/resource question or an explicitly narrower technical-feasibility paper. Do not choose the endpoint after viewing new arm results.

## P03 scoring specification prepared from the feasibility findings

Before model evaluation, implement the small common evaluator with these requirements:

1. Separate **identity/linkage**, **reported context**, **reported measurement** and **provider metric** families. Study, locus, variant and article IDs cannot count as measurements. Count beta/uncertainty and p-value components as declared related fact groups, not independent studies.
2. Bind each expected fact to a verified original file/receipt, source record/row/field locator, scope, source version, literal transform/version and unknown reason. A source-derived value is not biomedical truth. No assertion of source binding is made merely from hashing an evaluator's expected-answer file.
3. Keep the scoring representation independent of each generator's wire format. Adapters may expose emitted facts but cannot insert omitted facts, read extra sources, repair errors or hide failures.
4. Preserve explicit unknowns without credit or false-positive error. Distinguish null, absent schema, incomplete collection, completed selected zero-match collection, failed QC and biological absence. Boolean/numeric type confusion, wrong source, invented units, duplicates and unknown slot IDs remain meaningful negative controls.
5. Use the same predeclared answerable measurement denominator for all arms. Zero answerable measurements means coverage/pass null; context or identifier accuracy is reported separately. Failed/timed-out cells remain failures in the intended experiment, and insufficient-input conditions form a separate stratum.
6. Preserve complete source lineage and exclude bespoke responses and response-derived ancestors. References are evaluator-only and never agent evidence. Fresh source contexts use no conversation fork. Semantic support/transfer judgments remain separate AI secondary results.
7. Freeze the actual source task and primary contrast before the new pilot. If exact field projection is a ceiling, study a declared source-eligibility/composition/missingness or resource tradeoff; do not represent straightforward copying as evidence of improved LLM interpretation.
8. Declare source grain and exact join keys before collecting values; handle zero, one and multiple matches and conflicting duplicates explicitly. Record native/unknown units and literal transforms. Keep linked-locus statistics distinct from gene- or intervention-level effects.
9. Freeze fact grouping/weights before scoring so related measurement components do not inflate independent evidence. A valid readable answer may earn partial coverage for correct facts, while omissions lose coverage. Malformed, failed, timed-out or unreadable cells fail completion and remain in the planned-cell denominator; their main coverage is null when unscorable. Any partial-response diagnostic is secondary and never silently repairs the response or turns failure into completion.
10. Qualify the later cohort through an executable prospective candidate/exclusion register and exposure crosswalk, source-study/article/locus/target-family clusters, actual answerable/insufficient-input counts and a declared precision objective. Reacquisition does not make an exposed context fresh. Keep the P04 development pilot separate; freeze an exploratory fallback if fresh coverage or precision is inadequate.

This is a prepared implementation specification, not completed P03 code or a newly qualified scientific benchmark. No new public framework interface/version has been declared.

## Whole-project disposition

R01–R06 engineering/preparation and the accepted 0.3.11/default-v2 core remain unchanged. The retained 1,774-test result is not a new full-suite run; all 327 previously accepted application/resource pins still match. R07 remains six complete responses/zero contract passes. Recorded comparisons and pure v3 preparation are not actual successful interpretation. Existing real source-selection studies remain exposed exploratory evidence, not the new H5-A primary result.

P01 review and P02 bounded feasibility are complete. P03 evaluator, P04 pilot, P05 cohort/analysis freeze, P06 experiments, P07 analysis, P08 manuscript, P09 research release and P10 final preprint package remain unfinished. There is still no qualified fresh evaluation cohort or complete manuscript/release package. The old genetics questionnaire and old-pair audit remain optional, not prerequisites. HR1–HR4 are retired; no external expert input is needed.

The 65 missing interpretation inputs, 36 unqualified clinical endpoint labels, 17/32 observable primary registry states and 0/12 jointly ready packages remain different unresolved denominators. Clinical/scorer/MR/T2–T5/H6/full original Virtual Biotech reproduction remain conditional future programmes. No real numerical feature or clinical probability was introduced. Native FAILED/INCOMPLETE_TIMEOUT, no-retry rules, $0 model-provider spending with unknown platform costs, unchanged source downloader and stopped monitor boundaries remain preserved.

**Next paper stage:** freeze the P03 task, join and scoring contract; implement only the evaluator required for the selected reporting question, then run P04. The prepared one-time data batch remains a conditional source-gap branch awaiting approval. No external scientist, review form or private native proof expansion is required.
