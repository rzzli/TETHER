# SC05 LitQA refinement: prospective interface and isolation review

Prepared November 6, 2026 from the existing SC05 notes and implementation source while SC04 is active. **Design only: no implementation, new retrieval, inference, answer inspection, scoring or activation.** This note specifies the LitQA component; the separate [SciFact calibration design](SC05-CALIBRATION-DESIGN-NOTE.md) remains separate and cannot calibrate LitQA or clinical probabilities.

The recommendation remains the previously selected **SC04 L/O baseline**, regardless of its eventual score. Reuse requires completed, externally anchored SC04 acceptance. “Accepted run” means execution/provenance acceptance, not that every candidate passed admission or was scientifically correct. Preserve all 199 scheduled IDs, original option order, failed candidates and native unsure answers.

## 1. Principal corrections to avoid during implementation

1. **Do not feed the accepted analysis package to the agent.** `litqa_analysis/run.py` writes original reference keys, annotated source identities, per-case correctness and metrics. Even apparently harmless reconstruction files live within that evaluator-only package. Baseline projections must come from the original SC04 execution records and raw collection captures; the coordinator uses acceptance only as an activation gate.
2. **Do not call generated text scientific evidence.** The prior answer, criticism and proposed queries are fallible generated context. They must never become `agent_evidence`/`reference` nodes, acquire scientific weight from a receipt, or satisfy a raw-evidence citation requirement. `InputGraph` currently accepts only those two evidence roles and rejects evaluator/unsupported roles. Preserve that protection; keep generated context in a separate typed channel.
3. **Do not grant a broad parent directory.** The existing controller recursively grants parent-phase files and loads parents before its Python audit is active. That pattern is unsuitable for a mixed evaluation/reuse package. SC05 needs exact role-specific input lists and auditing before opening task data, plus separate coordinator and worker manifests.
4. **Do not silently reuse fixed-task APIs as generic ones.** SC04 transport validates only expansion/ranking/common-answer kinds; its stage schedule names are fixed; its article pool accepts at most three sources. Critic/repair requests, their schedule, and a merge of up to six articles need new adapters and qualification. Calling critique `expand`, or a refinement phase `supplied`, would misstate the retained contract.
5. **Do not encode withholding as a bad citation or native unsure.** Preserve the original decoded candidate and provenance decision. Semantic withholding is an additional policy decision with its own metric layer.

## 2. Control plane and worker inputs

Use a new versioned refinement package, for example `experiments/litqa_refinement/`. The following interfaces are proposals, not existing functions or approved grants.

| Interface | Inputs | Output and invariant |
|---|---|---|
| `prepare_baseline(execution_descriptor, coordinator_acceptance, output)` | Externally anchored original SC04 execution; coordinator-only acceptance attestation | All 199 L/O rows projected by an explicit field allowlist. Verify query, native candidate and original source/context joins without consulting correctness. Produce per-role worker products and a separate private provenance map. |
| `verify_baseline_projection(descriptor, expected_schedule)` | The new projection and its external receipt | Reconstruct every permitted field against execution originals. Reject missing IDs, another arm, reordered choices, unsupported parent roles or imported evaluator-derived products. |
| `critic_request(visible_query, candidate_context, original_selected_raw)` | Original query/options; nullable prior candidate; exact original L/O selected passages | A new critic request/prompt/grammar fingerprint. No alternate SC04 candidate, supplied-source hint, key passage, reference key or scorer result. |
| `refinement_plan(question, critic_query_terms)` | Question identity/text and strictly parsed generated terms only | Existing safe two-query acquisition plan, with the critic native-call hash retained as **control provenance**, not a scientific source ancestor. |
| `merge_sources(original_descriptor, refinement_descriptor, policy)` | Two independently verified original-source forests | New merge manifest, original-root descriptors, duplicate/conflict decisions, raw pool, selected context and coverage. Preserve both original collections intact. |
| `repair_request(visible_query, candidate_context, critique_context, merged_selected_raw)` | Same task/options; prior candidate; critic output; selected raw passages | A new answer request with the unchanged answer-index/citation output schema and explicit raw-source-only citation allowlist. |
| `select_original(candidate, original_admission, critic)` | Original candidate plus separate checks | A deterministic `keep`/`withhold`/`not_applicable` record. Never a newly generated answer. |
| `verify_refinement_run(...)` | Completed external execution roots and code/model pins | Reconstruct all new requests, native calls, query/merge choices, selection gates and resource joins before evaluation. |

Worker-visible products should be small, typed, and have exact schemas:

```text
VisibleQuery = {id, question, choices}
GeneratedCandidate = {
  kind: "model_generated_candidate_context_v1",
  id, query_sha256, prediction: {answer_index, evidence_ids} | null,
  producer_status, original_admission_status,
  native_call_sha256, generated_at_utc,
  is_scientific_evidence: false
}
RawPassage = {source_id, text, sha256}
CritiqueContext = {kind, query_sha256, candidate_sha256,
                   source_context_sha256, decoded | null,
                   native_status, native_call_sha256,
                   is_scientific_evidence: false}
```

The proof fields bind execution; they do not imply correctness. Keep original candidate bytes in a raw native archive. A missing/invalid original decode has `prediction: null`, never a fabricated unsure answer. A provenance-rejected but syntactically valid candidate remains rejected; critique-only cannot upgrade it. Repair can produce a separately verified new answer from valid raw sources.

The coordinator may read the final SC04 acceptance and evaluator package to establish that the prerequisite has passed, but **must not derive the candidate product from that package**. Use original predictor-side query/native/context records and collection receipts as data parents. Keep the acceptance record in control-plane authorization metadata only, outside the worker manifest, model prompt and evidence graph. Hashing, copying, renaming or sealing evaluator-only content does not authorize its use. If a proposed parent graph contains evaluator-only data, reject it; do not strip the disallowed edge and relabel the child.

| Role | Data it may receive | Data withheld |
|---|---|---|
| Coordinator/projection verifier | Original execution, acceptance, provenance descriptors | Must not turn correctness into case selection, prompt tuning or worker content. |
| Critic | Visible query/options, original L/O candidate, original selected raw passages | Other-arm answers, reference keys, benchmark paper hints, correctness/metrics, full evaluator receipts. |
| Acquisition | Question-only task, bounded generated terms, public retrieval policy | Choices, candidate/critique prose, raw model trace, reference papers/keys. |
| Merge/admission | Raw collection manifests/receipts, question, fixed merge policy | Correctness and all generated prose as evidence. |
| Repair | Visible query/options, typed candidate and criticism, selected raw passages | Scorer outputs, alternate arm answers, annotated DOI selection, final repair answer before its own dispatch. |
| Evaluator | Sealed outputs plus explicitly evaluator-only keys, groups and annotations | No feedback channel into completed prediction stages. |

Refinement terms are **option/candidate-informed** because the critic saw those inputs. Their acquisition worker receives a minimal projection, but this does not make the entire refinement procedure question-only. Record this method difference from SC04. Public article IDs encountered in ordinary sources are distinct from benchmark-annotated paper hints; neither authorizes adding the privileged supplied-source arm to ordinary refinement.

Python `InputAudit` and retained opens support role enforcement but are not an OS sandbox. Keep exact files, separate roots, fresh import caches, explicit interpreter roots, output-only writes and independent I/O-log review. No pre-opened evaluator handles or recursive evaluator grants. A worker must not inherit the coordinator's loaded references.

## 3. Critic and critique-only policy

Propose one critic generation for every scheduled case, including an explicit null original candidate. Its finite output contract is:

```text
{
  support: "supported" | "contradicted" | "insufficient" | "not_assessable",
  evidence_ids: [zero to two unique offered original passage IDs],
  criticism: string of at most 160 UTF-8 bytes,
  queries: [[one or two safe terms], [one or two safe terms]]
}
```

Terms are at most 48 ASCII bytes, use the existing literal-term character restrictions, and exclude search operators, URLs, DOI/PMID/PMCID identifiers and duplicate terms. The first list compiles with AND, the second with OR under the existing rights/publication filters. Reuse the existing expansion parser where compatible, then apply these tighter limits; do not reinterpret unrestricted criticism as a search query. No proposed replacement answer or confidence probability is requested. `supported`/`contradicted` require at least one offered passage citation; a null candidate requires `not_assessable`. These are structural conditions, not proof that the criticism is correct.

The 256-output-token allowance may still truncate a syntactically long valid response. Qualify the exact grammar, escaping and tokenizer on invented long/Unicode/context cases before freezing it. Do not promise that the byte bounds guarantee a complete native decode. Do not shrink the schema after seeing production accuracy.

Critique-only keeps a candidate only when: the original decode exists and is **substantive** (not the visible unsure option), original provenance admission passed, the critic decoded successfully, and `support == supported`. Otherwise it withholds or records `not_applicable` for an original native unsure/absent candidate. Preserve separate reasons such as `critic_contradicted`, `critic_insufficient`, `critic_unavailable`, `original_not_admitted` and `original_native_unsure`. No extra call is needed for this policy. Unsupported/failed criticism is not a provenance failure. A retained native unsure remains native unsure, not a substantive answer.

## 4. One acquisition/merge/repair cycle

1. Seal the full baseline projection and critic phase. The same critic record feeds both critique-only selection and repair; do not call separate critics and claim shared evidence.
2. If valid critic terms exist, execute **one** public two-query acquisition using the existing article/rights/receipt rules, even when the critic says supported. This avoids making the repair attempt conditional on eventual correctness. If critic decoding/capacity fails, record `refinement_query_unavailable`, perform no substitute model call, and continue to repair with the original raw sources and explicit unavailable critique. This is a prospective fallback, not a fabricated empty collection.
3. Verify both source forests in their original acquisition roots. Keep the original publication cutoff; capture a new UTC information-availability cutoff after new acquisition. Never backdate new receipts to SC04. Separate publication date, acquisition time and merge computation time.
4. Merge at most three original and three newly retained articles. For repeated PMCID with identical original body hash and compatible identity/rights, use one raw document with alias references to **both** receipts; choose original-first deterministically. For the same PMCID with conflicting body bytes or identity/rights, retain both originals in the archive but exclude the conflicting identity from the merged eligible pool and report it. Do not silently replace an older source with a new version. Distinct publications remain distinct even if some sentences match.
5. Use one deterministic raw-text chunk/relevance algorithm over all eligible merged articles, original articles before new articles for ties. Reuse the existing UTF-8 chunk and lexical scoring semantics. The new merge adapter must allow six source documents; `selection.build_pool()` currently refuses more than three and cannot be called unchanged on that union. Final pool remains at most 16 chunks/10,000 raw bytes and selected context at most eight chunks/8,000 raw bytes. Preserve exclusion counts, duplicate aliases, original document/span/character locators and all source versions. Do not pass summaries or criticism into this pool or silently truncate original evidence.
6. Generate **one revised answer per scheduled ID** with the new repair prompt, unless its explicit capacity/infrastructure policy prevents dispatch. Original candidate and criticism occupy clearly marked generated-context fields. Only the selected raw passage IDs may be emitted as evidence. Prior citations omitted from current selection do not gain citation eligibility merely because the candidate or critic repeats them. No additional ranker, critic loop, query expansion call or answer retry fits this three-generation design.
7. Seal the new candidate, native request/output and admission separately from original candidate and critique-only decision. Empty new retrieval does not justify skipping an otherwise eligible repair: repair may still assess original sources plus criticism. Record whether new sources changed the selected context.

Merged source manifests should contain **two kinds of lineage**: scientific evidence parents (original metadata/XML/mapping bytes) and control provenance (critic/query/selection hashes). Neither the critic nor the prior answer enters the scientific-evidence graph. A query plan can explain why a source was fetched without becoming evidence for its conclusions.

Move capacity checking inside a reserved per-cell operation before dispatch and before source admission constructs the final request. SC04's known pre-call capacity-abort limitation must not be copied into the new instrument. Test and retain capacity as an explicit no-generation disposition. Genuine integrity, source-binding or uncertain transport failures remain fatal to the phase and preserve all unexecuted slots. No automatic resume or replay of a potentially executed call.

## 5. Evidence-removal diagnostic

Use a separately labeled full-199 diagnostic. Construct its input from the **same pre-repair** candidate, critic and question/options, with only the current raw passage list removed. Freeze both request forms before either final generation; never use the new repair answer as diagnostic context. Do not regenerate criticism or retrieval for the diagnostic.

The diagnostic still contains information carried by the prior candidate/criticism and model parameters. It measures **raw-passage dependence conditional on generated context**, not complete evidence independence or contamination freedom. A further condition removing generated context would be a different, currently unbudgeted experiment.

The evidence allowlist becomes empty, so any substantive diagnostic answer necessarily fails raw-source admission. Report paired **raw** answer changes/accuracy/unsure rates and operational failures; a mechanically zero substantive admitted yield is not evidence that raw passages improved reasoning. Keep diagnostic metrics out of the primary three-condition comparison. Its scheduled denominator stays 199, including cases where the factual repair failed.

## 6. Logical and physical accounting

Let `B` be the reused original L/O answer, `C` the new critic, `R` the new repair and `D` its evidence-removal counterpart. Let `H0` be original L-branch collection and `H1` the single refinement collection when attempted.

| Condition | Logical model dependencies | Logical public-source dependencies |
|---|---|---|
| One pass | B | H0 |
| Critique only | B + C | H0 |
| One repair | B + C + R | H0 + H1 |
| Removal diagnostic | B + C + D | H0 informs B/C. H1 is attributed only as matched-pipeline control/scheduling overhead; D receives no raw passages and H1 did not inform B/C. |

Each primary condition has the same **ceiling** of three generations/768 output tokens per question, not equal actual work. Do not spend dummy calls or call this an equal-compute experiment. Calls retain the proposed 256 output-token, 14,000 prompt-byte, 16,384 context-token and 120-second per-call limits, pending invented-input qualification. Critic/repair prompts have extra context and need new capacity checks; SC04 prompt feasibility is not their guarantee.

With all baseline calls reused, at most 199 physical critics + 199 repairs = **398 new primary generations**; the diagnostic adds at most 199, for **597 new generations / 152,832 output tokens**. Count reused B calls as historical attributable work, not new execution. Show three distinct resource totals: full historical SC04 execution, the L/O-attributable dependencies reused here, and incremental SC05 work. Never sum logical arm totals as physical expenditure.

One refinement collection permits two metadata requests plus three article attempts, **995 additional HTTP attempts maximum** across 199 cases. Combined logical H0+H1 permits four metadata plus six article attempts and 16 MiB response allowance per question. “Six article attempts” does not imply six usable articles. Failed transfers charge conservative reservations; measured bytes remain null/known separately. Preserve tokenization requests, generation entries, measured tokens, conservative reservations, status causes, wall time, peak-memory scope, captured response bytes and unknown-transfer bounds. Deduplication reduces selected documents, not already incurred HTTP cost. Critic-unavailable cases have zero H1 requests with an explicit reason.

Give every physical call/capture a unique immutable execution ID. Logical arms refer to those IDs; shared B/C/H0/H1 dependencies are charged per condition but deduplicated once in physical totals. Distinguish information dependencies from control/scheduling attribution: the removal diagnostic's H1 charge does not claim H1 content influenced its candidate or critic. Replay should reject missing/duplicated edges, hidden extra calls, budgets exceeded, counters inconsistent with journals, and measurement-to-estimate substitution. Provider spending remains $0; that is not a claim of zero compute cost.

## 7. Evaluation and reuse boundary

Retain the native prediction and existing provenance disposition unchanged. Add a separate semantic-selection record; do not add a `withheld` producer status to the existing five-field `score_arm` contract and hope it behaves as abstention. Reuse native scoring for generated candidates, and add a small independently reconstructed selection layer for retained yield/coverage/precision. Zero substantive selections have undefined statistical precision, not zero confidence.

Freeze before SC05 execution: three primary contrasts (critique-only versus one pass; repair versus one pass; repair versus critique-only), their endpoints and the separate diagnostic contrast. Reuse the 199-ID schedule, 186 original publication groups and deterministic paired-bootstrap machinery; the SC04 four-arm factorial wrapper and five-arm aggregate are not the SC05 estimator. The evaluator alone reads reference keys and group/DOI annotations after outputs are sealed.

Report preserved raw accuracy, semantic retained yield, precision/coverage, false withholding, repaired wrong answers, damaged correct answers, persistent errors and source-context changes. Distinguish repairing a wrong substantive answer from recovering an original operational failure; distinguish a newly wrong answer, native unsure, policy withholding and an unproduced candidate. Critique-only cannot increase the count of correct answers available in its fixed original candidates. This is a mathematical constraint, not an empirical result.

| Reuse after its prerequisite gate | New work requiring its own controls/replay |
|---|---|
| Pinned model acquisition/license, owned server, native HTTP capture/tokenization, process supervision, watchdogs, journals and atomic publishing | Critic/repair request kinds, payload binding, dynamic grammar/strict decoding and new native reader adapters. Existing transport task validation is not extensible by passing an arbitrary task string. |
| Original query validation and safe literal-query acquisition, rights checks, original source receipts and independent collection reconstruction | Exact baseline-role projection; critic-term provenance; six-article merge/dedup/version-conflict adapter and merged eligibility/admission. |
| Pure chunking/scoring/selection semantics and source span identities | New phase schedule/schema and parent graph; do not relabel fixed SC04 stages or copy the whole controller. Compose the common supervision/journal primitives and extract only necessary reusable internals in a separately qualified version. |
| Native prediction schema, provenance checks and original `score_arm` | Semantic selection wrapper, three-condition/diagnostic aggregation and cross-stage independent reconstruction. |
| Bootstrap/group primitives and physical/logical accounting patterns | New all-scheduled dependency graph and supplemental resource reconciliation. Reuse neither SC04's fixed five-arm aggregator nor evaluator-bearing projection as an agent input. |

Keep the archived qualified SC04 producer/analysis bytes verifiable. A future common primitive extraction must preserve that version and rerun relevant controls; it is not permission to edit code while SC04 is active. Avoid a second raw-XML parser, downloader, server manager, native-response archive or bootstrap implementation just for refinement.

## 8. Implementation order and qualification gate

1. **Role projections first:** invented malicious-key/annotated-DOI/evaluator-receipt parents, renamed evaluator content, cross-arm candidates and mismatched options must fail before any model/network call. Test coordinator and actor manifests separately.
2. **Critic codecs and deterministic withholding:** test null candidates, unsupported citations, quoted prompt injections, malformed/oversized outputs, true native unsure and provenance-rejected candidates. Assert original candidate bytes never change.
3. **One-cycle collection and merge:** exercise missing sources, failed HTTP reservations, duplicate same-version aliases, conflicting PMCID versions, different rights, UTF-8 offsets, six-source input, empty pools and cap exclusions. Independently reconstruct every merged selected span from its original root.
4. **New reserved native cells and controller:** qualify exact prompts/grammar/tokenization and explicit task kinds on invented fixtures. Inject capacity, timeout, interruption, malformed output, write failure and uncertain native completion. Retain records; never duplicate dispatch.
5. **Independent replay and accounting:** reconstruct candidate/critic/query/source/repair/removal joins, actor I/O permissions, cutoffs and all logical/physical resources. Both semantic-selection and absent-input diagnostics require explicit new tests.
6. **Invented end-to-end qualification, then protocol freeze:** require all scheduled fixture cases, successful replay and source preservation; retain negative controls. Fix all prompt and policy choices before production outcomes can inform them. SC04 completion/acceptance remains a prerequisite; this note does not activate SC05.
7. **Full execution and evaluator-only analysis:** execute every planned case or preserve an explicitly incomplete attempt; compare only completed independently accepted schedules. Keep negative findings, abstention-heavy behavior and damaged answers. Do not select a better baseline, tune thresholds on LitQA keys, substitute experts/AI criticism as gold, or claim calibrated clinical decisions.

The associated `SC05-LITQA-IMPLEMENTATION-REVIEW.json` records the exact source/doc bytes inspected for this review. No new outcomes were opened or used to choose these interfaces.
