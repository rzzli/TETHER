# TETHER SciFact execution protocol — BG03

**Status: implementation and evaluation plan; no trained SciFact model or scored SciFact result.** BG02 closed at project checkpoint `4dbe7be`. This protocol implements stage 3 of the [benchmark execution plan](<TETHER Benchmark Execution Plan 2026-11-02.md>). It does not reopen the original comparison, historical clinical studies, expert-return route or closed model attempts. Preserve all prior files and results. The default is a small CPU-trained scientific-claim baseline, with native task metrics and a paired assessment of TETHER's checks. A weak or negative result is reportable.

## 1. Question, estimands and limits

The primary question is whether an actual scientific-claim solver's outputs can be checked against their authorized source artifacts while preserving useful native predictions, and what that checking costs. SciFact evaluates abstract-level support/contradiction and rationale selection. Provenance checks alone do not establish entailment, scientific truth or therapeutic efficacy.

Use two distinct panels:

1. **Natural public-development tasks:** one frozen producer creates each candidate once. Compare the identical candidate/source bytes with and without the scoped TETHER checks. Report native scores before checking, checked output scores, retained useful predictions, false rejection, task/operational abstention and full costs. No expectation that a provenance gate improves semantic accuracy.
2. **Explicit constructed policy controls:** mutate or withhold an artifact/permission against a valid neighbor to test the declared native adapter contract. Keep these exposed constructions outside native SciFact denominators. Include semantically wrong but source-valid candidates: their acceptance is expected under the provenance-only contract and must not be relabeled a source-integrity failure.

Independent semantic judging, revision loops, dense retrieval, MultiVerS and calibrated guarantees are later additions, not required to make the first baseline honest. The existing independent equal-policy validator and subsequent Inspect stage may be adapted later under an explicit new native-task contract; do not pretend their therapeutic `Case` interfaces already support SciFact.

## 2. Pinned acquisition checkpoint and unresolved inputs

Root acquired the following public assets separately; this protocol performs no download or dataset extraction. [Acquisition checkpoint](../data/raw/scifact_public/20261105-attempt01/COMPLETE.json) says `downloaded_not_parsed`, with references restricted pending projection. The subsequent [acquisition audit](review-assets/tether-scifact-20261105/ACQUISITION-20261105.json) verifies original bytes/receipts and records archive-member metadata; task-content parsing remains pending.

| Asset | Retained identity | Current evidence / remaining gate |
|---|---|---|
| Official public data archive | `data/raw/scifact_public/20261105-attempt01/scifact-data.tar.gz`; 3,115,079 bytes; SHA-256 `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be` | Original bytes/receipt and metadata-only member inventory checked. The official `release/latest/data.tar.gz` URL is mutable; use the actual digest as local release identity. Content parse, task counts and reference isolation remain pending. |
| SciFact source | Commit `68b98a56d93e0f9da0d2aab4e6c3294699a0f72e`, retained source ZIP and receipt | Pinned `LICENSE.md` reviewed directly from ZIP: claims/annotations CC BY 4.0; corpus abstracts ODC-By 1.0; repository code Apache 2.0. Full member/notice inventory remains to record. |
| Official evaluator | Commit `66feffc5b2cc9e28e3ce3b8c9e824c3c642981eb`, retained source ZIP and receipt | Pinned evaluator license is Apache 2.0. `evaluator/eval.py` SHA-256 `2554fed44c3f5592bdeed59ab0d3918a412b452ba1c77da73ba0f62e74c9987f`. Scorer qualification remains pending. |
| Baseline runtime | Python, NumPy, SciPy, scikit-learn versions and wheel hashes: **pending** | Resolve a compatible isolated CPU environment, record licenses/dependencies and reproduce a fictional smoke test before real fitting. No requirement for a large pretrained model. |
| Parsed task counts, grouping, model, scores and resource measurements | **null / not measured** | Fill only from retained artifacts. No power, accuracy, timing or memory estimate is an observed result. |

Official routes: [SciFact release](https://github.com/allenai/scifact/tree/68b98a56d93e0f9da0d2aab4e6c3294699a0f72e), [pinned evaluator](https://github.com/allenai/scifact-evaluator/blob/66feffc5b2cc9e28e3ce3b8c9e824c3c642981eb/evaluator/eval.py). Do not claim historical information availability or model-training nonexposure from these download dates. The public dev set is development evaluation, not a private leaderboard holdout. Private test evaluation is outside this first run and its service availability is unverified.

## 3. Typed data products, permissions and isolation

Implement a trusted preparation process with its own manifest and byte/field projection proofs. It may inspect labels for grouping, training partition construction and evaluation. The predictor may not. Retain the original mixed archive in the restricted preparation area and publish separate, explicitly permitted products:

| Product | Consumer and allowed contents |
|---|---|
| Public corpus view | Retrieval/prediction: native document ID, title, original ordered abstract sentences and explicitly approved corpus fields. Preserve original bytes/locators and record any normalization. |
| Query-only view | Prediction: native claim ID and claim text. No `evidence`, rationale labels, `cited_doc_ids`, gold answer, reference-derived relevance flag or source-citation hint. |
| Fit-only supervision | Fitting process: permitted training-partition claims, document labels, rationale sentence sets and explicitly eligible negative-pair labels. Never a candidate-visible source. |
| Tune/calibration references | Their designated development processes only. Neither used in model fitting; no dev gold included. |
| Official dev reference | Evaluator only, opened after the candidate schedule/output freeze. Keep all official dev claims in the scheduled denominator. |
| Model provenance | Verifier/training auditor: fit claim/group IDs, supervision/product hashes, code/environment, hyperparameters and seed. Evaluator answers are prohibited model ancestors. |

The tarball is a **mixed-role preparation container**, not universally evaluator-only or inference-readable. Physical containment edges stay in the projection receipt; purpose-specific logical products distinguish corpus, permitted fit supervision, queries and held-out answers. Extraction does not create a new public-download receipt, and a restricted logical parent is not made agent-visible by labeling a generated child `reference`. A new, reviewed projection authority must bind the archive/member hash, permitted fields, producer code and consumer purpose. Prove that changing reference-label or `cited_doc_ids` bytes leaves predictor-view bytes unchanged, while corpus/claim changes alter the relevant approved view. The trusted projector deliberately processes mixed data; its authority and information-flow checks must be explicit. Add sentinel taint/access checks before fitting. Held-out answer products can never be fitting or prediction ancestors.

Use separate filesystem roots/process argument allowlists for training, prediction and evaluation. Start prediction without a reference-root argument; retain its actual argv, environment allowlist and opened-input inventory. A folder convention is not an operating-system security boundary. If process isolation cannot prevent arbitrary same-user filesystem reads, state that limitation and rely on the qualified bounded baseline code plus audited opens; do not claim a malicious-code sandbox.

## 4. Grouping and split freeze before model tuning

1. Inspect schemas, duplicate IDs, sentence ranges, conflicting labels and archive paths without printing individual reference answers in progress reports. Retain counts and anomalies. Do not silently discard conflicting or unparsable scheduled records.
2. In the trusted split process, construct claim/source components using native cited/evidence document IDs and exact normalized duplicate claim text. Retain grouping method, edges and hashes. Near-duplicate grouping requires a separately fixed rule; it cannot be adjusted after seeing predictions.
3. Official dev stays the full public-development evaluation set. Quarantine official-training components that overlap dev by the declared source/claim links from fitting, tuning and calibration. This is a stricter source-disjoint training derivative; report all removals and compare no scores from a differently trained standard baseline as if training were identical.
4. Deterministically assign remaining official-training components to fit/tune/calibration at intended 70/15/15 proportions using a fixed published seed `20261105` and group-level hash order. Record actual counts rather than promising exact proportions. A component cannot be split to rescue a preferred sample size.
5. Check that every required label occurs in fitting and that tune/calibration contain evaluable positive and negative cases. If grouping leaves inadequate examples, retain the feasibility failure before evaluation; amend the design transparently before training rather than silently relaxing overlap rules. Any calibrated guarantee additionally requires an explicit sample-size/assumption analysis. No general-power claim follows from this engineering split.
6. Seal split, source permissions, implementation, model configuration, tuning criterion and evaluation schedule before fitting/tuning. References used to define grouping remain trusted preparation inputs, not extra predictor features.

Document this as public-development evaluation with fixed internal calibration. Public availability and historical pretraining exposure prevent describing it as unknown to all models/developers.

## 5. Default small native solver

The first route is a deliberately modest supervised baseline. Its weak linguistic representation is a limitation, not a reason to replay gold answers or switch models after viewing dev performance.

**Retrieval.** Build a sparse word unigram/bigram TF-IDF index over the approved title+abstract corpus, using lowercase Unicode-normalized text, L2 normalization, sublinear term frequency and a predeclared 100,000-feature cap. The index may fit IDF on the whole *unlabeled public corpus*; disclose this corpus-level transductive step. It must not use dev questions, evidence annotations or citation hints to rank candidates. Rank by cosine similarity with deterministic document-ID ties. Tune `k ∈ {5,10,20}` only on internal tune groups. Record top-k IDs and scores and retrieval evidence coverage separately from classification.

**Document labels.** Fit a separate vocabulary/IDF on fit-partition text only, capped at 50,000 word unigram/bigram features. For each claim/document pair, use sparse claim and document vectors plus their elementwise product and absolute difference. Fit a regularized three-class linear classifier for SUPPORT, CONTRADICT and benchmark-relative NEI, with fixed seed and a small explicitly pinned implementation. Default candidate is scikit-learn `SGDClassifier(loss="log_loss", penalty="l2", alpha=1e-4, max_iter=2000, tol=1e-4, class_weight="balanced", random_state=20261105)`. Pin the exact package/API and convergence behavior before use; an incompatible API or nonconverged fit is a retained failure, not permission to silently change parameters.

Positive fit pairs come from fit-only annotated evidence. Default NEI pairs come only from the documented, annotated source-citation candidate pool without a supporting/contradicting annotation, after verifying that this is a valid benchmark-relative negative construction. Unannotated arbitrary corpus documents are **unlabeled**, not automatically scientific negatives. If the default pool is insufficient or its annotation semantics cannot be established, stop that fit and retain the blocker; an explicitly revised negative-sampling protocol may be considered before dev inference.

**Rationales.** Fit a binary linear sentence selector using fit-only annotated positive documents: a sentence is positive when it belongs to an annotated rationale set. Use the same sparse feature construction for claim/sentence pairs. This learns annotation-relative selection, not exhaustive scientific support. For a predicted SUPPORT/CONTRADICT document, emit sentences above threshold in descending score with sentence-ID ties, capped at five. Tune rationale threshold in `{0.25,0.5,0.75}` jointly with retrieval k; nine fixed configurations, selected by internal-tune official abstract-rationalized F1, then sentence-label F1, then smaller k and higher threshold. Do not use gold rationale length at inference. Preserve empty selected-sentence lists rather than fabricating a rationale.

Use the model's three-way argmax for the native document label. A predicted NEI document is omitted from the native evidence dictionary; a claim with no predicted evidentiary documents receives an explicit empty dictionary. **NEI is a substantive task prediction, not a policy refusal or an execution failure.** Keep raw per-pair scores and native predictions, including poor ones.

Train the two learners once on fit data; tune the fixed nine settings without refitting on tune/calibration. No post-tuning fit+dev retraining. Prefer explicit numeric/vocabulary model artifacts with hashes; never load untrusted pickle/joblib files from benchmark inputs. Retain model-fit and prediction code/environment pins. Calibrated semantic probabilities and selective guarantees are not claimed. The calibration partition stays available for a separately declared optional selective-risk analysis after the native baseline is qualified; it must not become extra fitting data.

## 6. Native integration seam and scoped TETHER adapter

Current [StudySession](../src/asof/study/session.py) is an LLM cell interface: its capacity checks require `prompt`, `n_predict` and conservative token reservations. **Do not implement a sklearn backend by inventing prompts, token counts, tokenizer identities or model usage.** `Case(T1/T6)` also must not receive fake target/indication IDs.

Implement a separate native-task adapter, initially under `experiments/scifact/`, with a versioned contract and explicit product imports. Proposed components are `data_views.py`, `split.py`, `baseline.py`, `native_contract.py`, `tether_adapter.py`, `run.py` and `evaluate.py`; these are intended files, not existing commands or completed code.

The native request identifies benchmark release, claim ID/text hash, approved corpus/index, model and configuration. The native candidate is the official `{id, evidence: {doc_id: {label, sentences}}}` prediction plus a separate immutable envelope linking retrieved IDs, exact source sentence bytes/locators, raw scores, producer identity and resource record. A successful check means the candidate follows this scoped contract, not that its label is scientifically true.

Reuse actual TETHER primitives for stable source reads, canonical serialization, target-free `Snapshot`/`SourceNode`/`Availability`, `InputGraph`, `catalog_index`/`check_role`, hash-chained `RunJournal`, trusted code/package proofs and exclusive atomic publication. `source_fact_sources.py` already demonstrates calling `InputGraph.exclusion` with an object containing `cutoff`; reuse the graph, **not that compiler's therapeutic-task schema**. Existing `InputGraph` accepts only `agent_evidence`/`reference`, so do not invent `training_reference` or `model` roles and expect them to pass.

Use `Snapshot`/`InputGraph` to admit original receipt-bound container bytes in the trusted **preparation** phase under an explicit phase/use grant. Low-level `reference` is not permission for arbitrary consumers: the new native authority restricts purpose and fields. Runtime prediction receives only sealed products and fitted parameters, with actual information-dependency parents retained. The reviewed projection verifier reconciles those products with archive/member proofs without fabricating child download receipts. This is a new scoped policy, not an exception silently supplied by the existing graph. The [architecture peer note](<../research_notes/TETHER benchmark priorities and methods/scifact-native-seam.md>) details this unimplemented seam.

Keep three separately typed proof domains and join them in the run receipt:

1. **Admitted source graph:** approved corpus products and their declared source lineage, role, exact bytes and current availability bound; query-only text is a task input, not supporting evidence.
2. **Purpose-scoped training/model proof:** authorized fit supervision and model lineage, with tune/calibration/dev gold prohibited as fitting ancestors. Training supervision is permitted to fitting by this new contract; it is not relabeled general agent evidence.
3. **Preparation/evaluator proof:** mixed archive projection authority, split construction and sealed reference identity, unavailable to prediction.

The new adapter must verify the projection/training boundaries itself. It must not claim canonical all-ancestor `authorize_snapshot` schema-2 parity or the entire BG02 contract, because those interfaces bind therapeutic cases/use frames. Name the native obligations explicitly: request/model/config binding; approved corpus identity and source locators; consumer-purpose separation; model training provenance; native output shape; immutable captured bytes; sealed result/trace consistency; exclusive outputs; budget/failure accounting; complete schedule. Independently qualify this scope before labeling its arm “TETHER checked.” If its source proof is merely a new standalone hash check with no real TETHER admission semantics, the claimed integration gate is not met.

## 7. Execution, arms and accounting

Reserve a fresh UTC-named stage directory before work. Retain append-only stage events for projection, grouping, index construction, fit, tuning, prediction, checking, scoring and failure. Recovery inspects and reports; it does not automatically rerun a partial fit or prediction cell. A retry is a new attempt with its predecessor and reason retained.

Predict every frozen official dev query exactly once using the frozen index/model/settings. Preserve a shared immutable candidate store. The two principal reporting arms consume the identical bytes:

- **Ungated native reporting:** parse with the same bounded native codec and report the producer's output. It has transport/format accounting but no claim of the TETHER policy.
- **Scoped TETHER checking:** verify the native policy and either retain the candidate or record policy rejection. No additional model inference, answer editing or oracle-assisted replacement.

On clean, correctly projected data, equal native scores and added overhead are plausible and acceptable. Separate constructed controls test invalid-source rejection. They do not turn natural wrong answers into policy violations. Reject-all and hash/schema-only diagnostics may be included in the control panel but cannot be advertised as equal-policy competitors.

Initial resource bounds, to be sealed before execution: CPU-only; one worker/thread group by default; at most nine tuning configurations; two fitted learners; no model/provider calls; provider spend $0; 10 GiB new stage storage; a **monitored 8 GiB process working-memory ceiling**; 30 minutes for each fit, 30 minutes for index construction, 60 seconds per query/check cell, and four hours total native-stage execution. These are ceilings, not measured requirements. Sample OS working memory at a declared 0.5-second interval where the existing launcher supports it; on an observed breach, stop the cell through its existing process-termination mechanism, retain its resource-exhausted disposition, maximum observed usage, sampling gaps and termination delay, and do not retry automatically. Report possible between-sample overshoot; a monitored limit is not a hard memory guarantee. Use a hard cap only if an already qualified launcher supplies one. Do not create a new kernel/native-toolchain project as a prerequisite for this modest CPU study. If a metric is unavailable, retain that fact and the available monitoring evidence. Full-corpus byte scans count against stage time; an expensive hash operation must not reset a per-cell clock.

Record measured wall/CPU time, OS process peak memory when available, read/written/retained bytes, corpus and feature counts, model size, fit iterations, rows scored and disposition. Distinguish actual measured, monitored estimate and unavailable. `model_input_tokens`, `model_output_tokens`, tokenizer identity and provider usage are **null with `not_applicable_non_llm`**, not fabricated zero-token measurements. Provider charges are zero because no provider is invoked. Include training/index setup and amortized inference cost separately, plus cold/import/check overhead and unsuccessful attempts.

## 8. Native scoring and all-case denominators

Pin and run the official evaluator as a separate reference-only process. Preserve the original output and all native metrics: `abstract_label_only`, `abstract_rationalized`, `sentence_selection`, `sentence_label`, with precision/recall/F1. At the pinned commit, the abstract-rationale cap is `max(3, shortest_gold_rationale_length)` (lines 157–161). Sentence scoring requires the complete relevant rationale set. A field-wise sentence accuracy proxy cannot replace these scores.

Publish both:

1. Official scores for raw native predictions and for retained checked predictions under a disclosed projection rule.
2. An independent all-scheduled-case ledger: candidate produced, parse failure, policy accepted/rejected, native empty-evidence prediction, policy abstention, timeout/error, scorer failure and unexecuted. It must reject missing or duplicate scheduled IDs.

Do not silently map a failed call to a successful NEI prediction. If a complete official-score file uses an empty-evidence placeholder for a failed/rejected candidate, label the score **failure-as-empty projection**, retain raw missingness, and never count that placeholder as successful useful completion on an empty-gold claim. Report coverage and native score jointly. Define supplemental strict useful completion before scoring: an actually produced and accepted prediction has the correct complete evidence-document set and labels and includes an allowed complete rationale for each evidentiary document; a valid native empty-evidence prediction can be correct, while a failure placeholder cannot. This supplemental case metric is distinct from the official micro-aggregated F1 measures.

Retain per-case paired raw/checked outcomes and source-group metadata. Bootstrap or other uncertainty must use justified claim/source components rather than treating related claims, tuning settings or repeated checks as independent samples. Report all class/source strata and selection loss, including wrong-but-source-valid and correct-but-policy-rejected outputs. No dev metric may choose a new threshold, model or exclusion for the same evaluation.

## 9. Ordered implementation and validation gates

Complete each gate before its dependent work; root owns project TODO/status updates.

| Gate | Work and required retained evidence |
|---|---|
| **G1 — inspect** | Reuse the retained receipt/hash and metadata inventory checks, then qualify bounded allowlisted extraction and parse schemas in restricted preparation. Reject absolute/traversal/duplicate/symlink or oversized members. Explicitly inventory and exclude non-task Apple `._` entries; do not extract unknown members. Retain license/notice text, task counts, conflicts and projection specification. No candidate receives raw archive or reference fields. |
| **G2 — split and views** | Implement purpose-scoped views and group split. Test reference-field perturbation leaves predictor view identical; corpus/claim changes alter expected hashes. Prove fit/tune/calibration/dev and source-component boundaries. Retain native-ID manifest and all exclusions. |
| **G3 — codec/scorer** | Fictional hand-computable controls for support, contradiction, empty evidence, wrong/missing documents, duplicate/out-of-range sentence IDs, complete multi-sentence rationales, several allowed rationale sets and rationales longer than three. Compare a small independent hand calculation to official scores. Test order/missing-ID failures and failure-as-empty accounting. No production answers used to invent scorer expectations. |
| **G4 — native policy** | Implement the scoped TETHER adapter and compute accounting. Negative/positive neighbors: changed source, bad locator, evaluator-field/ancestor access, prohibited model-training ancestor, altered model/config/request, future-bound source, valid later computation from permitted inputs, tampered journal/receipt, missing/duplicate cell, output alias/collision, timeout/interruption/write failure. Rejected semantic falsehood alone is not a provenance-policy requirement. |
| **G5 — solver feasibility** | Install pinned CPU dependencies; fictional train/predict smoke verifies classes/rationale shape and deterministic seeds. Inspect real fit-only label availability and group counts. Resolve negative-pair semantics before fitting. Retain convergence/resource failures; do not claim qualification from all-empty output alone. |
| **G6 — train/tune/freeze** | Fit only authorized fit products; run the fixed nine inner-tune configurations; select by the predeclared criterion. Freeze model/index/config, public-dev query schedule, native policy, evaluator and output transforms. Record actual input opens and evidence that prediction has no gold access. |
| **G7 — execute and score** | Produce all frozen public-dev candidates, then run paired fixed-candidate arms; preserve every failure. Reference scoring occurs only after the candidate freeze. Independent reconstruction checks native score concordance, all-case accounting, paired bytes and resource boundaries. |
| **G8 — report** | Retain native result files, exact manifests, unknowns, contamination limits, controls, failure records, cost tables and a source-to-claim completion matrix. Update manuscript/status honestly; mark BG03 complete only when a task-capable solver has actually run and all preceding gates have evidence. |

Run meaningful unit/adapter regressions and impacted installed-package/full project checks if packaged TETHER code changes. A pure experiment plugin still needs its own pinned environment and source-inclusive qualification. No claim of valid reproduction may rely solely on a parser, supplied gold predictions, a copied abstract or all-abstention run.

## 10. Artifact layout and reporting checkpoint

Preserve `data/raw/scifact_public/20261105-attempt01/`. Proposed fresh ignored stage roots: `data/benchmark/scifact/<snapshot-id>/restricted/` for source/reference products; `views/`, `splits/`, `models/`, `candidates/`, `runs/` and `evaluation/` with purpose-specific manifests. Keep only sanitized provenance, protocol, code and aggregate reports tracked under `planning/review-assets/tether-scifact-20261105/` and the study's report tree. Do not expose reference records through a broadly reusable candidate manifest or commit bulk benchmark/model files.

Current checkpoint: public acquisition completed separately; pinned code/license members and scorer cap inspected; **archive parsing, purpose-scoped projection, split counts, solver implementation, training, candidate generation, scoring and BG03 completion remain pending**. This document is the plan to perform that work. No data, file or permission request is currently required from the owner; if the public route or local dependency/resource qualification fails, retain the exact blocker rather than substitute results or reopen expert review.
