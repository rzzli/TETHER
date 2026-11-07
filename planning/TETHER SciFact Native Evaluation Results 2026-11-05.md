# TETHER SciFact native evaluation — results and completion record

**Actual execution, independent reconstruction and root acceptance passed; the scientific result is weak.** One fit, nine tuning configurations and one full 300-query development pass completed in `data/benchmark/scifact/native-20261105T234805Z-attempt01`. All **300/300 candidates were admitted**, but only **27/300 (9.00%)** met the predeclared strict native criterion. Raw and checked native metrics are identical: abstract-rationalized F1 is **8.70%**. TETHER preserved the producer's correct predictions and also admitted its source-valid errors; this run shows **no semantic accuracy gain** from provenance checking.

The immutable actual-stage receipt is `3a997165aac2f0a85a93890f5e10a66d8117563e380e98f892dd3cb8a93f8968`. The independent reconstruction (local artifact: `data/benchmark/scifact/reconstruction-20261105-attempt01/RECONSTRUCTION.json`), completed on 6 November 2026 UTC, has SHA-256 `35c589e3ea7706844196830305c61944dd6c66336e76f13d5a3da0bc470d3d07` and reports `PASS` with all primary aggregates matching. The initial report structure was prepared without live results; this revision uses those sealed artifacts and retains the original methods, selection rule and limitations.

The [root acceptance record](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/actual-attempt01/ROOT-ACCEPTANCE.json), SHA-256 `3426f85542f3a2b3355542e9292168db2f5f2ce39c713836a3c0e7cc1202d462`, verifies all 1,601 stage outputs and 72 reconstruction outputs, current source/environment boundaries and unchanged maintained-core/import-cache identities. Acceptance concerns the declared evidence and execution contract; it does not upgrade the weak task performance into scientific validity.

The governing [execution protocol](<TETHER SciFact Execution Protocol 2026-11-05.md>) was frozen before actual fitting. Its plan-time acquisition statements are historical checkpoints; the completed preparation and qualification evidence below supplies the implementation status. The [preflight record](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/actual-attempt01/READY.json) binds commit `4689a5c02b9d41b04542b8499f54d128e109d477`, source hashes, interpreter/environment, protocol, preparation, command and resource limits. `READY_NOT_EXECUTED` is that record's pre-dispatch state, not an execution result.

## 1. Question and scope of inference

This experiment asks whether a trained scientific-claim solver's native predictions can be checked against authorized data, model and execution artifacts while retaining useful predictions, and what those checks cost. It separates **task accuracy** from **provenance and execution-policy compliance**.

The solver is a modest sparse retrieval and supervised linear baseline. TETHER is the checking and evidence-management layer around its outputs. The two natural-task arms use the same frozen candidates: an ungated native reporting arm and a scoped TETHER-checked arm. Checking does not invoke another model, revise an answer, replace rejected output with a new prediction or use the evaluator's answer to decide acceptance. Equal scores with additional checking overhead are an acceptable finding. Good provenance does not imply scientific entailment; a wrong but source-valid label may legitimately pass.

This is a public-development SciFact study, not a private leaderboard result, a test of a state-of-the-art scientific language model, or a clinical target-prioritization validation. The scoped native adapter reuses TETHER primitives but does not establish equivalence with the therapeutic schema-2 or BG02 contract. It does not supply a head-to-head Virtual Biotech comparison.

## 2. Sources, preparation and information boundaries

The receipt-bound data archive is identified by SHA-256 `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be` rather than by the mutable upstream `release/latest` URL. Pinned SciFact code is commit `68b98a56d93e0f9da0d2aab4e6c3294699a0f72e`; the official evaluator is commit `66feffc5b2cc9e28e3ce3b8c9e824c3c642981eb`, with script SHA-256 `2554fed44c3f5592bdeed59ab0d3918a412b452ba1c77da73ba0f62e74c9987f`. Original notices retain the distinct claims/annotations, corpus and code licenses. See the [acquisition record](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/ACQUISITION-20261105.json) and [preparation qualification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/data/QUALIFICATION-20261105.json).

The actual prepared release contains **5,183 documents, 809 official training claims, 300 public-development claims and 300 unlabelled test claims**. All 300 development claims remain scheduled. Test records were schema-checked and were not included in an answering/evaluation product. The current preparation is `preparation-20261105-attempt03`, manifest SHA-256 `cb32f1384c49b66b912a62120abd7137a8a19b303f3ad052f035f21779c131f8`.

Preparation validates bounded allowlisted archive members, duplicate/path/link/size restrictions, native IDs, sentence references and schemas. It binds approved fields to original member, row and field hashes. The raw mixed archive remains a preparation container. A physical container relationship does not grant a predictor access to every member or field.

| Product | Authorized use and content |
|---|---|
| Public corpus | Native document ID, title and ordered original abstract sentences; retrieval/indexing and appropriate task processes. |
| Query views | Claim ID and text only. No citation hints, evidence labels or gold rationales. |
| Fit pairs | Fitting only: permitted claim/document labels and rationale annotations. |
| Tune references | Internal configuration selection, scored after each corresponding candidate output is sealed. |
| Calibration references | Reserved; unused for fitting or this evaluation. |
| Development references | Reference-only scoring after the frozen development candidate output. |
| Full preparation manifest, source locators and grouping records | Trusted preparation/audit control information; not predictor inputs. |

Trusted preparation and source checking may inspect/reconstruct labelled archive members, including labels used to define overlap exclusions. Consequently, this study does not claim that all project participants or preparatory code were unexposed to public development information. The enforced distinction is that fitting/prediction workers receive only their approved byte-bound inputs. Their actual recipes and managed Python opens are retained. This is not an operating-system boundary against hostile same-user code or arbitrary native-library access.

## 3. Grouped supervision and the shared unlabelled corpus

Components connect claims through cited/evidence document IDs and exact normalized claim text (Unicode normalization, case folding and whitespace normalization). Training components connected to any development claim are quarantined: **278 of 809 training claims are removed**, leaving 531 for internal partitioning. Remaining components are assigned by fixed seeded group-hash order, seed `20261105`, with group boundaries at 70% and 85%. Components are not divided to obtain preferred claim counts.

| Partition | Claims | SUPPORT pairs | CONTRADICT pairs | NEI pairs | Role |
|---|---:|---:|---:|---:|---|
| Fit | 380 | 169 | 82 | 176 | Two learned classifiers; 427 labelled document pairs. |
| Tune | 82 | 44 | 14 | 41 | Fixed nine-setting selection; no refitting. |
| Reserved calibration | 69 | 28 | 15 | 31 | Unused in this run; no calibrated guarantee. |
| Public development | 300 | N/A | N/A | N/A | No supervision-pair counts in this row; native claim strata are given separately below. |

These are retained preparation counts, not task-performance or statistical-power results. Claim counts and pair counts have different denominators. NEI supervision is limited to a claim's cited documents without annotated supporting/contradicting evidence; arbitrary unannotated corpus documents are not converted into negatives. Such negatives remain benchmark-relative, not assertions of universal biological nonassociation.

**The supervision is source-disjoint under the declared component rule; the retrieval corpus is shared.** The retrieval IDF/index uses all 5,183 unlabelled public documents, including documents relevant to development claims. This transductive corpus use is explicit. The supervised pair vocabulary/IDF is fit on fit-partition claim and eligible pair-document text only. Development questions, evidence labels and citation hints do not fit the retrieval index or supervised classifiers. Exact normalized duplicates and source links are handled; semantic paraphrases, unrecorded source relationships and near duplicates are not guaranteed to be separated.

This stricter training derivative differs from standard SciFact training. Published scores under other training splits or stronger architectures cannot be treated as matched comparisons. Public availability and prior developer exposure also prevent a claim of an untouched private holdout.

## 4. Qualified solver and fixed selection rule

The CPU environment is Python **3.11.15**, NumPy **2.3.5**, SciPy **1.16.3**, scikit-learn **1.7.2**, joblib **1.5.2**, threadpoolctl **3.6.0**, TETHER core **0.3.13** and TETHER **0.5.2**. The [environment qualification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/ENVIRONMENT-QUALIFICATION-02.json) retains wheel identities, licenses, executable hashes and 3,900 verified distribution payloads. Actual execution pins the current qualified source set; earlier peer-review hashes remain historical evidence of those reviews.

The retriever uses NFKC-normalized, lowercase word unigram/bigram TF-IDF, sublinear term frequency, L2 normalization and a 100,000-feature cap. Cosine ranking has deterministic document-ID ties. The separate supervised vectorizer has a 50,000-feature cap. Claim/document and claim/sentence features concatenate the two vectors, their elementwise product and absolute difference.

Two `SGDClassifier` learners use fixed log-loss/L2 settings: `alpha=1e-4`, `max_iter=2000`, `tol=1e-4`, balanced class weights and seed `20261105`. One predicts SUPPORT/CONTRADICT/NEI for documents; the other learns binary sentence selection from fit-only positive documents. Convergence warnings abort fitting. Explicit JSON/numeric array artifacts replace pickle/joblib model loading, with bounded verified bytes and checked sparse-array structure.

Document labels use three-way argmax. Predicted NEI documents are omitted from native evidence; a claim with no predicted evidentiary documents receives a substantive empty-evidence prediction. Supporting/contradicting documents retain selected sentences above threshold, ordered by score then sentence ID, capped at five. Empty selections are preserved; inference does not borrow gold rationale length or invent a rationale.

Both learners are fit once. The fixed tuning grid is `k ∈ {5,10,20}` crossed with rationale threshold `{0.25,0.5,0.75}`. Selection maximizes official abstract-rationalized F1, then sentence-label F1, then prefers smaller k and higher threshold. No development result can select another setting, retraining set or exclusion. Model, configuration, policy, evaluator and the full 300-query schedule are sealed before development inference.

The selected setting was **k = 5, rationale threshold = 0.25**. Fitting used 380 claims, 261 distinct eligible pair documents, 427 document pairs and 2,503 sentence rows. The document and rationale learners completed 16 and 10 iterations, respectively, without a retained convergence failure. The retrieval index has 100,000 features and 1,177,207 nonzero entries across 5,183 documents; the supervised vocabulary has 48,985 features and the concatenated pair representation has 195,940 dimensions. The two model files total **22,456,342 bytes**. Model-manifest SHA-256 is `31bdea32db03488f2ac590a4cf28049886af900ca0f7442df5f29ae45e673e9a`; retained model/fit proof (local artifact: `data/benchmark/scifact/native-20261105T234805Z-attempt01/jobs/fit/model/model-manifest.json`) links the exact inputs and fit session. These observed fit details establish an executed learned model, not calibrated scientific or clinical probabilities.

## 5. Matched-candidate checking and native evaluation

Each scheduled development claim is predicted once. The checked arm validates the original producer session and query/configuration, approved corpus identity, source sentence locators and bytes, permitted model parents, fitted output identity, native output shape, journal/receipt accounting and complete schedule. Original producer resource records are preserved in the candidate envelope; checker cost is recorded separately.

The official scorer runs in a separate reference-only process with the exact pinned upstream evaluator. Report all four official families with precision, recall and F1. These are not replaced by a field-level sentence-accuracy proxy.

| Official family | Raw precision | Raw recall | Raw F1 | Checked precision | Checked recall | Checked F1 |
|---|---|---|---|---|---|---|
| Abstract label only | 8.37% | 34.93% | 13.51% | 8.37% | 34.93% | 13.51% |
| Abstract rationalized | 5.39% | 22.49% | 8.70% | 5.39% | 22.49% | 8.70% |
| Sentence selection | 4.38% | 37.98% | 7.86% | 4.38% | 37.98% | 7.86% |
| Sentence label | 2.68% | 23.22% | 4.81% | 2.68% | 23.22% | 4.81% |

Values are percentages rounded to two decimals; the reconstruction retains all 12 metrics at full precision for both arms. Their exact equality follows from admitting every unchanged candidate, not from an independently improved second solver.

If failure/rejection requires an empty-evidence placeholder for a complete official-score file, label the output **failure-as-empty projection**. A placeholder is never counted as a successful NEI prediction or useful completion. The supplemental strict case measure requires an actually produced candidate with the correct complete evidence-document set and labels and an allowed complete rationale under the official cap; checked useful completion additionally requires admission. It is distinct from the official micro-aggregated metrics.

| All-scheduled accounting item | Final value / denominator |
|---|---|
| Scheduled claims | 300, fixed before fitting |
| Produced; parse failure; timeout/error; unexecuted | 300; 0; 0; 0 |
| Policy accepted; rejected; check error; not checked | 300; 0; 0; 0 |
| Native empty-evidence predictions | 53, of which 26 are strict-correct NEI predictions |
| Raw failure placeholders; checked failure/rejection placeholders | 0; 0 |
| Strict correct raw; correct and admitted | 27/300 (9.00%); 27/300 (9.00%) |
| Correct but policy rejected; correct but otherwise not admitted | 0; 0; no false policy rejection observed |
| Admitted but failing the strict native criterion | 273/300 (91.00%); not 273 established biological falsehoods |
| Retained useful predictions and selection loss | 27/27 strict-correct producer predictions retained; 0 lost |
| Annotated document-pair retrieval coverage | 159/209 (76.08%); excludes NEI from recall denominator |
| Nonempty-gold claims with their complete document set retrieved | 147/188 (78.19%); not a full-answer accuracy score |

| Native reference stratum | Claims | Produced/admitted | Strict correct raw and checked | Strict correct / scheduled |
|---|---:|---:|---:|---:|
| SUPPORT | 124 | 124 | 1 | 0.81% |
| CONTRADICT | 64 | 64 | 0 | 0.00% |
| NEI | 112 | 112 | 26 | 23.21% |
| All | 300 | 300 | 27 | 9.00% |

There are 247 development source/claim components. The stratum-specific component counts are 120 for SUPPORT, 62 for CONTRADICT and 90 for NEI; these overlap across strata and must not be summed as independent groups. Only **1/188 nonempty-gold claims** meets the strict complete-answer criterion despite 159 retrieved annotated document pairs. Thus retrieval coverage alone is insufficient to explain or remedy the poor final task result. This diagnostic does not isolate a causal contribution of retrieval, labels, extra predicted documents or rationale selection; no post-result ablation or retuning is performed.

### Explicit post hoc analytical context: constant NEI

After inspecting the final aggregate strata, an always-empty-evidence rule would analytically satisfy the strict criterion on the **112/300 NEI claims (37.33%)**, compared with this learned baseline's **27/300 (9.00%)**. It would predict no evidentiary documents or rationale sentences, yielding **zero evidence precision/recall/F1** under the pinned official metric convention. This exposes the importance of reporting both complete-case utility and evidence retrieval/label/rationale measures: high strict correctness from class prevalence alone would not establish evidence finding.

This is a **post hoc arithmetic reference, not an executed competing run**. It has no retained predictor session, frozen competitor configuration or measured compute cost, and it does not replace the predeclared primary outcome. The comparison nevertheless makes the learned baseline's weak strict-case result explicit rather than presenting 9% as intrinsically useful.

Native task rows and constructed policy controls remain separate panels. Fictional mutations test permissions, tampering, locators, accounting and valid neighbours; their rejection rates are not natural-task accuracy or unexposed robustness. Test methods are not independent scientific samples. No confidence interval or population-power claim is supplied. Any later uncertainty calculation must respect claim/source components and must not count tuning settings or repeated checks as independent observations. All-candidate acceptance here demonstrates preservation under a clean owned producer; it does not estimate the prevalence or rejection rate of invalid provenance in deployment.

## 6. Costs, limits and failure reporting

The frozen ceiling is CPU-only execution, one configured thread group, zero model-provider calls, 10 GiB new stage storage, four hours total native-stage time, 30 minutes for fitting/index setup, and 60 seconds per query/check. Working memory is monitored at 0.5-second intervals against an 8 GiB process threshold. Parent process supervision also bounds phase time and captured output; source hashing consumes stage time.

| Actual-run measurement | Value | Interpretation |
|---|---|---|
| Reported whole-stage wall time | **587.287 s** | Native stage through report construction, including source/environment scans and controller work; excludes prior qualification and later reconstruction. |
| Combined fit/index/serialization wall and CPU | **3.413 s / 3.313 s** | One actual fit; its internal sub-operations are not separately timed. Parent fit-process time is 4.625 s. |
| Nine tuning configurations | Setup 1.867 s; 738 query cells 14.092 s; scoring 0.509 s | Corresponding cell CPU: 1.844 / 13.469 / 0.516 s. Parent process totals: predictions 34.595 s and scorers 2.969 s. |
| Development setup and inference | Setup **0.210 s**; 300 query cells **4.344 s**, mean **14.480 ms/query** | Cell CPU: setup 0.203 s, inference 4.109 s. Parent development process: 8.406 s. |
| Native checker setup, checks and source replay | **2.590 / 0.271 / 2.606 s** | Corresponding CPU: 2.453 / 0.109 / 2.578 s. Direct checks average **0.902 ms/case**, excluding setup/replay/process costs. |
| Checking process and attributable controller brackets | **8.094 s** parent process; **20.701 s** for three checking-phase runtime brackets | Measured subtotal **28.795 s**; not a fully instrumented counterfactual marginal total. Controller's additional final replay/other work is not separately timed. |
| Final reference scoring | **0.089 s** cell wall / **0.094 s** CPU; parent process 0.359 s | Exact pinned scorer computes both arms; this is separate from prediction/checking. |
| Independent reconstruction | Passed; separate monotonic duration not available in retained summary | Outside the reported native-stage wall time; its 72 sealed outputs occupy 1,261,321 bytes. |
| Repeated code/environment verification | **486.680 s wall / 472.344 s CPU**, 47 brackets | Shared fitting/tuning/prediction/scoring and checking phases; not all marginal answer-checking cost. |
| All separately timed controller operations | **500.203 s wall / 485.563 s CPU**, 49 operations | Includes the 47 brackets, initial qualification and model/source context construction; do not add this to its component rows. |
| All parent-observed subprocesses | **59.048 s**, 22 processes; zero reported cleanup errors | Includes cell work and cold/process/journal overhead; do not add to child cell times. |
| Process lifetime peak; sampled working set | Maximum lifetime peak **304,451,584 bytes**; maximum sampled set **282,071,040 bytes** | Both occurred in fitting. Peaks are maxima, not sums. All 10 fast scorer processes had zero polling observations; their cell lifetime peaks remain available. |
| Declared input/output bytes; retained stage bytes | Known logical inputs **317,269,655**; primary outputs **30,096,069**; retained stage **36,570,027 bytes** | Input/output byte counts for final checker verification are unknown; known sums are not complete physical I/O. Stage inventory: 1,601 outputs. |
| Actual-stage failures and repeats | **0 failed/partial subprocesses; 0 retries** | One fit, nine tune predictions, one development prediction, ten scorers and one checker. Earlier qualification/rehearsal failures remain preserved separately. |
| Provider charges | **$0**, reconciled | No provider is invoked. |
| Model tokens, tokenizer identity and provider usage | Not applicable | Null with `not_applicable_non_llm`, not invented zero-token measurements. |

Working-memory polling can miss brief peaks and overshoot between observations; it is not a kernel-enforced cap. Fast children can complete before a polling tick. OS process-lifetime peaks, where available, and unknown sampling gaps must be retained. Managed Python opens do not measure all native-library/OS reads. Declared bytes omit logs, journals and other overhead unless separately counted. Bracketed source/environment verification is not continuous host attestation.

The completed **fictional** process rehearsal took 693.953 seconds, of which 651.016 seconds were repeated code/environment verification; 22 supervised subprocesses used 21.452 seconds of parent-observed execution. These numbers establish a qualified execution path and expose potentially substantial fixed verification overhead. They must not be copied into actual SciFact cost/performance tables. The [rehearsal report](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/runner/RUNNER-COMPLETION.md) preserves scope and missing-memory-observation details.

**Full-workflow cost and marginal checking cost have different scopes.** Repeated source/environment brackets surround shared fitting, tuning, prediction and scoring as well as checking. Report all of that overhead in total workflow time, then identify the measured checking subprocess, its setup/per-case/replay resources and any controller brackets attributable to the checking phase. Do not charge every package scan to each admitted answer, and do not omit the scans because they dominate a small task. Shared source preparation, model training, configuration selection and candidate production must remain visible as shared or fixed costs. These two arms reuse one producer trace; they are not independently timed alternative end-to-end pipelines. Where a controller operation was not separately timed, retain it as unavailable/unattributed rather than inventing an exact marginal total or assigning the whole workflow residual to checking. Report directly measured per-case checks separately from initialization, source replay and process overhead.

Numerically, 486.680 of 587.287 reported seconds were repeated runtime verification. The overall residual after the disjoint separately timed controller operations and parent subprocess times is **28.035 seconds**; this is an arithmetic unallocated remainder, not a measured checker operation. The measured checking-branch subtotal combines the 8.094-second child and 20.701 seconds of phase-specific brackets, without adding the child setup/cell/replay times a second time. Independent reconstruction verifies the consistency and sums of retained timing records; it cannot independently remeasure past execution. No separately executed ungated timing arm supports an exact end-to-end speed ratio.

## 7. G1–G8 completion and source-to-claim matrix

| Gate | Final evidence status | Evidence supporting that status | Scope retained |
|---|---|---|---|
| G1 — source inspection | Completed in declared scope | [Data qualification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/data/QUALIFICATION-20261105.json), receipt/member/row/field bindings, safe-member/schema controls; actual anchors pass final replay. | Public source identity, not independently adjudicated scientific truth. |
| G2 — split/views | Completed | [G1/G2 report](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/data/G1-G2-COMPLETION.md), sealed preparation attempt03, all 12 products reconstructed and exact grants retained. | Source-disjoint supervision under the stated rule with shared unlabelled retrieval corpus. |
| G3 — codec/scorer | Completed | [Scorer qualification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/scoring/QUALIFICATION.md), fictional hand expectations, actual official CLI score agreement and all-case reconstruction. | Native annotation metrics and strict-case supplement remain distinct. |
| G4 — native TETHER policy | Completed in declared scope | [Control map](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/policy/G1-G5-COVERAGE.md), core admission, actual producer/checker byte joins and source-inclusive replay. | No semantic truth filter, hostile-code sandbox or inherited full therapeutic contract. |
| G5 — solver feasibility | Completed | [Environment](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/ENVIRONMENT-QUALIFICATION-02.json), fictional numerical/repeat-fit/convergence controls and successful actual two-learner fit. | Task-capable implementation achieved; empirical accuracy remains weak. |
| G6 — train/tune/freeze | Completed and independently reconciled | [Preflight READY](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/actual-attempt01/READY.json), one fit, all nine settings, model proof and pre-inference freeze (local artifact: `data/benchmark/scifact/native-20261105T234805Z-attempt01/DEV-FROZEN.json`). | k=5, threshold0.25 selected without development retuning. |
| G7 — execute/score | Completed; independent reconstruction PASS | All 300 same-candidate pairs, no missing/failed cases, official native scores and resource/source/accounting reconstruction. | Public-development result; no accuracy improvement from the check. |
| G8 — report | Results and evidence completed; root acceptance PASS | This report, exact stage/reconstruction receipts and [root acceptance](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/actual-attempt01/ROOT-ACCEPTANCE.json). | Weak results, post hoc context and measurement unknowns are explicit. Project-wide status/manuscript integration is maintained by root. |

The final integration gate passed **148 tests, zero failures/errors/skips**, with unchanged sources; see [VALIDATION.json](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-scifact-20261105/integration-attempt01/VALIDATION.json). The completed full fictional rehearsal verified 337 output hashes and its complete inventory. Its receipt is `57d3724e7b37bce1b99ef9c080ac891654879c5ee74df66681525b1e77e1968f`. These qualify software and execution controls, not real benchmark results. Earlier logs/counts overlap and are not added as independent experiments.

Preserved corrections include a legitimate repeated cited-document ID, report-field reconciliation, numeric-model loading from captured bytes, empty-schedule rejection, worker request/config/input reconciliation, deadlines consumed by source hashing or between polling ticks, watchdog-marker persistence failure and the explicitly resolved qualified Python runtime alias. None authorizes dropping an inconvenient actual development result. The first fictional rehearsal failed before fitting and remains retained; the successful second rehearsal is a separate attempt.

## 8. Independent finalization and defensible conclusion

Independent reconstruction read the sealed outputs, verified original source/receipt identities, rebuilt relevant joins from raw members, confirmed all 300 scheduled native IDs and same-candidate identities, reran the exact official scorer, recomputed strict useful-completion/accounting totals, reconciled selected settings/model/input proofs, and checked resource/status consistency. Across the tuning and development predictions it checked **10,110 retrieved-document bindings and 12,777 returned-sentence bindings** against original sources. It found all primary aggregates concordant and no unexplained policy disagreement. The helper uses an independent reconstruction path and the pinned upstream scorer, rather than treating the original controller's summary as its own result. It supplies no independent biological adjudication or historical performance measurement.

The sealed final record retains the actual stage receipt, `FROZEN.json`, `DEV-FROZEN.json`, model/fit proofs, original producer and checker sessions, scored candidate inputs, official metric outputs, all-case dispositions, resource evidence and independent reconstruction receipt. Root acceptance verifies **1,601 stage outputs (36,570,027 bytes retained)** and **72 reconstruction outputs (1,261,321 bytes retained)**. Aggregate reporting is tracked; bulk/model/reference records remain in ignored data paths with their purpose restrictions. The original stage remains immutable.

The defensible conclusion is limited: a trained native scientific-claim pipeline executed under the scoped TETHER contract, all 300 outputs remained traceable and admissible, and all 27 strict-correct predictions were preserved. The baseline was weak, especially on nonempty evidence cases. The gate also admitted 273 outputs that fail the strict native criterion, as expected for provenance checking that does not judge entailment. There was no semantic gain and no observed false policy rejection. Fixed workflow verification dominated elapsed time, while directly measured candidate checks were short; those are different cost statements, not a claim that all verification is cheap.

Nothing here shows that hashing proves learning, admitted claims are true, public-development performance generalizes clinically, probabilities are calibrated, this modest baseline matches stronger systems under comparable training, or the native adapter provides an OS sandbox/full therapeutic contract. The post hoc constant-NEI arithmetic underscores the weak strict-case result without replacing the primary outcome. Further semantic improvement would require a separately declared method/evaluation study, not relabeling this completed run as a successful semantic validator.
