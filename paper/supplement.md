# Supplementary methods and artifact guide

Companion to the working AsOf source-reporting draft, 1 November 2026. Public deposit and owner declarations remain pending. The separately qualified local artifact is described in S8. Paths below describe this local research checkout, not a public data deposit. No external expert response is required or used.

## S1. Frozen chronology and immutable anchors

All dates below are UTC. The information cutoff is 2026-11-01T07:16:26.101448+00:00. The run used source-only inputs sealed before references; references were finalized before generation. The final experiment READY was committed as 31c52d3 before the single native study. Later audits and analysis do not overwrite its ledger or pre-run exposure register.

| Stage | UTC output directory suffix | Status |
| --- | --- | --- |
| Prospective registry | 20261101T071713Z | Twelve identity-ranked units; complete physical-row enumeration |
| Original-only packets | 20261101T074942Z | Twelve source-only packets; zero blocked |
| Neutral tasks | 20261101T075541Z | Twelve tasks; no evaluator fact values |
| References | 20261101T081933Z | Twelve evaluator-only references; independently source checked |
| Exposure/denominator register | 20261101T083548Z | Pre-run UNKNOWN broader exposure; frozen answerability |
| Fictional source controls | 20261101T090035Z | Fourteen source-only fixture scenarios |
| Fictional qualification | 20261101T090042Z | Fourteen scenarios/42 decisions; no native outputs |
| Actual study | 20261101T091345Z | Thirty-eight outputs/90 decisions, terminal |
| Frozen descriptive analysis | 20261101T092110Z | Pinned ledger and later source-audit gate |

Exact file SHA-256 anchors are listed below. These are byte hashes, not canonical-object fingerprints. The distinction matters because whitespace changes affect byte hashes. The manifest and audit objects record additional canonical fingerprints where used.

| Artifact | Exact SHA-256 |
| --- | --- |
| EXPERIMENT-READY-v1.json | 49c2ce672356bfcfd572a7b6c963c56bd5c96e3d042a9972f2c36434ebb8de3f |
| Study ledger.json | b2a9727ca9ce89865b80ffe80b21a325ea6d91d8844247740ac2c2ecc9a4faa0 |
| Study seal.json | 84b1e87b187dd5704c143f0da0fcac41103a88affe8c8b022c2890c8dc89c70f |
| EXPERIMENT-AUDIT-v1.json | f10f15959f8497821115f65268808c98ae345079c7361722390a479b15506922 |
| Analysis analysis.json | ee9f02ea3c3692bbd8b7d63d2d2cd545cfd769ccee9ee7454b4ed00c7ac87312 |
| Results ARTIFACTS.json | 84d4a31e842d3085133d384429729ef2501425d33bf2b92f65d9c64699a87428 |
| ANALYSIS-PRESENTATION-AUDIT-v1.json | 80815c8fafd7e2225930f3ea54fbccdca926269c872f893a9f841386c14ce031 |

READY, source-audit and presentation-audit files live under planning/review-assets/preprint-p05-20261031/. The study and analysis directories live under data/derived/ with their UTC suffixes. The original ledger's COMPLETED_PENDING_INDEPENDENT_AUDIT status remains unchanged; the separately pinned later PASS audit supplies the subsequent verification result. A successful audit is not a reason to rewrite old output bytes.

## S2. Source and interpretation card

| Product | Local selected frame | Purpose | Interpretation limit |
| --- | --- | --- | --- |
| Open Targets 25.09 GWAS evidence | 100 files; 1,753,850 rows | Target/disease/locus identity and native fields | Provider aggregation and publication dates do not establish causal relevance |
| Open Targets 25.09 credible sets | 25 files; 2,862,043 rows | Exact locus join and four native measurement components | No inferred effect units, allele orientation, ancestry or causal direction |
| Open Targets 25.09 targets | Ten files; 78,726 rows | Canonical target normalization | Current normalization cannot silently fill historical gaps |
| Open Targets 25.09 diseases | One file; 39,530 rows | Required disease identities | Ontology identity does not establish disease-model equivalence |
| HGNC local 10 October 2026 snapshot | One TSV; 45,233 rows | Approved symbol/Ensembl normalization | Acquisition date differs from annotation release and historical availability |

All 137 originals total 2,866,248,239 bytes. Receipt copies are content-addressed and archived separately from transport receipts. Parent paths, source hashes, row-group/row locators and role restrictions are retained. Full original-file hashes cannot be reproduced by an extract containing only the 24 used rows. Source inventories are selected subsets of the providers' overall releases.

Source-valued InputGraph parents are limited to pinned eligible originals, with their retained receipt proofs. Validated neutral Task/Snapshot, selected-case routing and plan configuration remain outside the source-valued InputGraph; their hashes are checked as configuration, and they cannot be relabeled as original evidence. Registry captures, mapping/coverage audits, SQL values, earlier generation packets, expected references, model outputs, old selected-join descendants and historical answer-aware derivatives are quarantined from the new source-only reference branch. Generation uses its separately admitted original-only packets and value-free fact bindings; evaluator references and descendants cannot become generation evidence. Recorded parent roles, exact byte anchors and fresh original projections enforce the declared branch policy; they do not prove a hostile operating-system sandbox.

The complete Open Targets study table is not available in the eligible local input set. Twelve exact locus matches therefore do not qualify upstream study agreement. GWAS-versus-credible-set variant-identifier agreement is unresolved; the join is not a qualified composite study-and-variant match. Genome build, ancestry, units, effect alleles and cohort overlap remain unresolved. Sample size is unavailable in ten selected credible-set records and is not a graded measurement fact. Numerical clinical features are empty and probabilities null. No MR estimate, colocalization probability, intervention direction or effect-size support weight is calculated.

Source availability is separate from scientific validity. Identity 108/132 and measurement 40/48 are populated-field counts. Nulls 24+8 are preserved. A populated source value can be scientifically problematic; a null cannot be replaced with zero. No claim that missing local evidence establishes biological absence is allowed.

## S3. Selection, exposure and dependence

The registry scans all 1,753,850 local GWAS physical rows. Fixed rules retain 1,681,738 eligible rows and exclude 72,112. Eligibility reasons can overlap, so a summed reason histogram is not the number of excluded rows. Target/disease/locus identity rank is fixed without measurement-value or candidate-performance ranking. The nine excluded previously used symbols are CD276, OSMR, ERBB2, PCSK9, IL6R, CFTR, GLP1R, SCN9A and CTLA4.

For each eligible unique release/target/disease/locus unit, the rank key is SHA-256 of the UTF-8 concatenation preprint-p05-deterministic-v1|25.09|targetId|diseaseId|studyLocusId. Ascending hash order is followed by lexical targetId, diseaseId, studyLocusId and release_id tie order; the first twelve units are selected. Missing, conflicting, blocked or insufficient selected units keep their position, failure or missingness. There is no replacement, answerability reranking or numeric-performance selection after the freeze.

The units are p05-01 through p05-12, with one original GWAS and one exact-locus credible-set row per unit. The evaluator register contains 180 requested slots: 132 identity and 48 measurement. Native nulls are 24 identity and eight measurement. Per-unit answerable measurement group sizes are 3,3,4,4,4,3,3,2,4,3,3,4. Identity and measurement components are not independent observations. Twelve locus strings and one repeated disease string group do not establish twelve independent studies or cohorts.

Broader exposure is UNKNOWN in the frozen pre-run register. After the study all twelve outputs and underlying identities are exposed. New holdout claims cannot be created by moving them to a different folder. Old bespoke review responses, normalized responses, candidate assessments, answer-aware mappings and descendants are archive-only and excluded from generation, reference construction, judging, tuning and source/case/arm selection. This exclusion is a declared input policy with retained ancestry checks, not evidence that an AI model never encountered a public source during training.

## S4. Fields, wire contract and endpoint

Each output declares schema_version, task_id, task_sha256, status, facts, collection_status and reason. A fact declares fact_id, value, unit, source and unknown_reason. The source object binds source_id, file sha256, release_id, physical locator and field. No prompt-only prose is scored as an emitted typed fact. Arrays preserve order, integers/floats/Booleans remain distinct, duplicate JSON keys are rejected and oversized outputs fail without truncation or repair.

Missingness reasons distinguish field_not_in_schema, null_source_value and empty_source_value. Native empty values can be reportable or unknown only according to the declared field policy. Unit is null for these native reporting tasks. An abstained or insufficient_input response has no facts and a reason. Wrong collection status or a wrong value, unit, binding or missingness reason is a critical mechanical error. Unknown fact IDs and duplicate fact emissions are errors.

C02's absent-standard-error example tests the generic JSON/core path only. The unchanged P05 native Parquet scanner requires its declared measurement columns, so that control does not qualify native absent-column acceptance or weaken the native schema policy. All eight unavailable native measurement slots in this study are present-column nulls.

For an answerable group g, let n_g be its number of populated reference components and m_g the number of exactly matched emitted components. Group coverage is m_g/n_g. Family coverage is the equal-weight mean over groups with n_g greater than zero. Measurement completion requires an eligible answered/partial response, correct collection status, no critical mechanical errors and mean measurement coverage at least 4/5. Sensitivities use 3/5 and 1. A zero-answerable-group family has undefined coverage and cannot pass by 0/0. The literal twelve-unit study has one answerable measurement group per unit. Technically valid C04 has none and remains uncompleted despite exact reporting.

The four native measurement fields are beta, standardError, pValueMantissa and pValueExponent. P-value mantissa/exponent are reported separately; no p-value is recomputed. Exactness uses typed source-value equality, not a scientific tolerance or inferred sign. Field-family coverage and exact all-fact reporting are distinct. The missing-schema/empty behavior occurs in constructed controls and regressions; it is not falsely reported as observed native missingness.

Strict exactness additionally requires a returned, structurally scorable report with status answered, zero critical errors and exactly one emission of each declared slot. Status partial is permitted by the coverage-completion contract but cannot satisfy strict exactness even with full coverage. Reference-value/null correctness, source bindings, units, unknown reasons and collection status must all agree.

## S5. Fixed guards and control inventory

| ID | Constructed condition | First full-policy failure |
| --- | --- | --- |
| C01 | Complete valid report | None |
| C02 | Valid null/absent/empty handling | None |
| C03 | Multiple groups and finite negative standard error, interpretation unqualified | None |
| C04 | All measurements unavailable, exact report, coverage undefined | None |
| F01 | Changed source hash | G0 |
| F02 | Evaluator-only ancestor | G1 |
| F03 | Future release metadata | G2 |
| F04 | Incomplete declared inventory | G2 |
| F05 | Wrong number | G4 |
| F06 | Wrong physical locator | G4 |
| F07 | Wrong unknown reason | G4 |
| F08 | Duplicate JSON key | G4/schema |
| F09 | Boolean in a measurement field | G3 |
| F10 | Oversized output | G4/schema |

FULL requires G0-G4. WITHOUT_WRAPPER requires G0,G1,G3,G4. WIRE_ONLY requires G0 and G4's schema status, not G4's exactness status. An unexecuted guard is not automatically a pass. F02 and F09 may still be admitted by WIRE_ONLY because their required schema/byte checks pass while stronger source checks do not. No policy is credited with factual source fidelity solely because the wire is valid. All intended decisions remain in the ledger, including early guard failures.

There are 24 native outputs: twelve literal plus twelve abstentions. Literal outputs have 36 decisions and abstentions twelve. Fourteen controls have 42 decisions. Total: 38 outputs and 90 decisions. All 90 reach a terminal verdict; 57 admit and 33 reject under their respective policies. Returned36 and deliberately malformed2 is output accounting, not decision accounting. The 35 core-scored-output subset is secondary. These denominators must not be mixed.

## S6. Development model card and stopped routes

The local development model is Qwen/Qwen2.5-14B-Instruct-GGUF, Q4_K_M, revision b466e1f8c07172155743e8e1307507d8a4f91fbd, served by the pinned b11717 runtime. Three weight-shard hashes are retained in the P04 protocol. No weights are redistributed by this manuscript. The configured context is 16,384 tokens, eight threads, seed zero and at most 2,048 output tokens per call. The configured GPU-layer count is 99; actual hardware/offload is not inferred from this setting. Ordinary completion is used without grammar/schema-constrained decoding.

P04's two exposed literature contexts have no populated graded measurement fields. Their model contract failures cannot be described as failed native GWAS extraction. Its twelve scheduled cells yield seven returned, four malformed and one failed cell; five actual model calls consume 13,582 input and 5,726 output tokens. Wall time is 424.516 seconds. Plain and proposal/check arms each complete 0/2 clean contexts; literal completes 2/2. Two preceding zero-call setup failures and later metadata corrections remain retained.

P04b's two fictional calls consume 2,501 input and 1,881 output tokens over 38.563 seconds. The two-fact example passes and the eight-fact example is malformed. This fails the fixed branch-qualification rule and closes model scaling. The observed failures are conditional on the task, prompt, format, implementation and model. They are not a comparison of model families, a clinical benchmark or an explanation of failure causality. No new generation is authorized by preparing the paper.

## S7. Verification, failures and resource interpretation

Preparation audits retain 789 registry checks, 1,238 input checks, 1,163 reference checks and a separate 478-check root register audit. These are bounded software/source consistency checks with overlapping evidence, not additive independent validation samples. Final runner, auditor and analysis preparation suites contain 36, 25 and 17 methods respectively. A keyed-dictionary/list mismatch in the independent auditor was reproduced in a retained regression and fixed before the actual study. No actual native study was run under that defective auditor.

Production has one original-row enumeration, 203.828 seconds wall and 198.984375 seconds CPU. Sampled RSS is 241,364,992 bytes and checkpoint-observed lifetime process peak is 305,827,840 bytes. Source verification is an overlapping 197.812-second subphase. Separate audit has one enumeration, 7.125 seconds wall, 7.046875 seconds CPU, sampled RSS 327,589,888 bytes and peak 333,893,632 bytes. Combined completed logical hash reads are 143,349,572,350 bytes. No physical I/O or dollar-valued platform cost is inferred from this.

The reference producer took 342.750 seconds and did not measure RSS/peak because its optional instrumentation was absent. This null is retained. Later process measurements cannot substitute for it. Source-preparation costs, study costs, audit costs and post-result rendering costs are separate. Shared native packet reads and policy projections are counted once at their actual operation granularity.

The 351-check presentation audit initially flagged four checker differences concerning unavailable scores, a scope label, resource-label spacing and floating SVG serialization. The checker was corrected; paper result payloads were unchanged. The initial report/code remain retained. A fresh local rebuild matches all 39 result-bundle files under the same runtime/standard-font environment. This does not guarantee cross-platform byte identity or full-study relocation.

## S8. Result files and reproduction scopes

The paper/results bundle includes eleven CSV tables totaling 392 rows, eleven readable Markdown views with 316 displayed rows, three vector PDF/SVG figures, PNG previews, exact figure data and captions, plus ARTIFACTS.json. The CSVs retain full serialized numeric precision; Markdown rounds display values. Unknown cells stay unknown rather than zero. The manifest binds every generated payload to its exact analyzed source. See paper/results/README.md for the local rebuild command and resource semantics.

The frozen descriptive analyzer is tools/science/analyze_source_validation_experiment.py. It consumes the exact audited ledger and produces the sealed analysis; it does not reread protected outcomes or use new judgments. tools/science/build_p05_paper_assets.py formats the already frozen quantities. Rendering was written after results and is not represented as preregistered analysis. Bibliographic source verification is in paper/RELATED-WORK-SOURCE-AUDIT.md, with machine-readable paper/references.bib and paper/references.json.

Verified scopes now also include the separately versioned P09 installed, relocated reconstruction and its source-inclusive independent audit on Windows x64, CPython 3.11.15 and PyArrow 21.0.0. These are post-result technical qualification operations, separate from the frozen P06 study and its 203.828-second production / 7.125-second source audit. Reconstruction reproduced all 38 output hashes and 90 decisions in 289.938 seconds; the separate audit passed 6,862 checks in 15.187 seconds. All 137 exact originals remain mandatory: 136 Open Targets files are external, and the one exact CC0 HGNC file is included with its receipt. Selected-row extracts cannot replace them. The public catalog produces genuine new reference identities; equivalence removes only `method.catalog_sha256`, while new G0 does not establish publisher authenticity or old private-archive integrity. Fresh exact-byte reacquisition of the 136 external originals remains untested. Policy-session logical counters exclude repeated compiler/caller reads; total physical I/O and platform cost remain unknown. The frozen P09 runtime bundle retains its earlier paper snapshot; later P10 working-paper and PDF updates are separate versions.

## S9. Availability, rights and unresolved author metadata

No public deposit, release DOI, hosted exact-release result or publication is claimed in this draft. Apache-2.0 applies to project code; external provider and underlying-source terms require product-specific review. The qualified local allowlist includes the exact CC0 HGNC original and project receipt metadata; 136 Open Targets originals remain external. This narrow inclusion is not general dataset redistribution clearance. Credentials, private machine paths, historical bespoke responses and their descendants, raw clinical outcomes and unreviewed model/data bytes are excluded. A local artifact can contain evidence not licensed for redistribution; its presence is not clearance.

Author names/affiliations, corresponding author, actual contributions, funding, competing interests and acknowledgments need factual owner confirmation before submission. AI assistance is disclosed in the main text; final human authors remain responsible for content. The draft does not infer a no-conflict or no-funding declaration. No new external scientific expert input is required. Scientific validation, study independence and clinical utility remain unestablished even after technical paper packaging is finished.
