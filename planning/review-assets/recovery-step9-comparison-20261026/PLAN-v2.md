# Prospective fixed-evidence four-arm comparison: synthetic engineering only

The frozen prospective machine plan is `PLAN-v2.json`, SHA256 `33d2b7dff7a3f834132b005be650129f0378cf74a1f3083dc60f8db2688e3a52`. Its preparation script writes new files exclusively and produced twelve **non-dispatchable** payload specifications plus `PREPARATION-CHECK-v2.json`. No responses, answers, model calls, real cases, source replacements or runtime changes were generated. Existing source code remains frozen while full validation runs.

V2 explicitly supersedes the preserved v1 guide/payload proposal. It spells `abstention_reason` in every answer-state rule and distinguishes retained input bounds/instructions from active response permissions. All original v1 artifacts and pins remain unchanged. Active text/limitations/unresolved item limits match the actual strict validator (1,800 characters); abstention_reason is bounded to 512. Synthetic-context aggregate input headroom is only **285** reservation units, so future changes must be remeasured; exceeding the unchanged ceiling fails preparation rather than enlarging the budget or dropping source material.

## Arms and identical evidence

Only the authenticated packaged `synthetic-context` and `synthetic-orientation` source fixtures are eligible. Each original request, source_scope and literal scientific-record bytes is preserved identically across all arms and every stage. Source table entries explicitly map `E0`, `E1`, etc. to original observation IDs and original JSON pointer paths; positional shorthand is not accepted in place of a pointer. Full original sources remain visible, including after a prior stage proposes only a subset. No role gets extra scientific evidence or evaluator context.

| Arm | Stage behavior | Execution in the next engineering increment |
|---|---|---|
| AsOf interpretation | One source-bounded interpretation stage | Explicit recorded fixture response through existing StudySession/RecordedBackend with a narrow new stage verifier |
| Adapted VB interpretation | chief_of_staff → coordinator_delegate → mapped_specialist → scientific_reviewer → coordinator_synthesize | Five recorded stage fixtures, bound to the same original sources; no original SDK or tools |
| Extractive | Existing pure exact-source baseline | Zero dispatch/model usage; no generated interpretation |
| Lexical | Existing pure lexical baseline, query exactly the original question text | Zero dispatch/model usage; no generated interpretation |

The adaptation is explicitly role-inspired: prompt guidance is rewritten and bounded, all roles use the same source packet, feedback contains source-ID proposals only, and external tools/adaptive redelegation/provider-specific specialist models are absent. This differs from the original CSO no-direct-analysis design and Haiku chief/reviewer routing. The provenance source revision remains `71f9da68c95c5ee0ef4c1d9b8f45f10693de022d`; exact prompt/registry hashes and locally established tool-name limits are in `../recovery-step9-20261026/COMPARATOR-SOURCE-PINS.json`. No unavailable original MCP argument schema is invented.

Unlike the legacy observation-ID selector, this prospective interface separates literal source reports from authored interpretation. Review/synthesis may reconsider any **original** source; the prior source-ID proposal is not a hard scientific support whitelist. This is a declared deviation from the old response-informed subset decoder. It does not permit a new source, an added tool result or a quote from prior generated history.

## One unchanged aggregate budget per fixture

The **same single `Budget()` is shared across all four arms for a fixture**, not reset at an arm or stage: 16 calls, 32,000 input tokens, 8,000 output tokens, $0 provider cost, 300 seconds, max_retries=1. The legacy field max_retries remains unchanged, but this comparison performs no automatic retry. The two fixtures are separate cases with the same budget, not a silent global budget increase for one case.

Generative-fixture stages reserve their complete prompt UTF-8 bytes plus 32 as conservative input units, with 1,024 output-token reservation per stage. Per-stage prompt cap is 6,368 bytes, full serialized payload cap 65,536 bytes and context ceiling 16,384; the per-stage cap alone does **not** prove aggregate feasibility. Complete worst-case source-ID history shapes and framing were measured:

| Fixture | Recorded generative stage count | Sum input reservations | Sum output reservations | Largest full payload |
|---|---:|---:|---:|---:|
| synthetic-context | 6 | 31,715 | 6,144 | 7,395 bytes |
| synthetic-orientation | 6 | 28,503 | 6,144 | 6,775 bytes |

All measured bounds fit without trimming sources. These are **preparation reservations**, not observed model tokens. Recorded fixtures may declare usage for accounting tests; it must be identified as fixture-declared usage, bounded by reservations and retained separately from zero actual model calls/provider spending. CPU/time is not claimed free. A future comparison driver maintains one monotonic fixture deadline and aggregate reservation ledger; each existing session receives remaining limits rather than fresh defaults. Preflight reserves the whole fixed schedule conservatively, and skips later stages with explicit dispositions on exhaustion/failure. Pure baselines consume no fake dispatch or model-token budget; their execution time still falls within the fixture wall-time ceiling.

## Exact serialized stage inputs and chain binding

Proposed `fixed_evidence_stage_request.v1` contains only:

- `schema_version`, `kind`, `comparison_run_id`, `arm`, `fixture_id`, `stage_index`, `stage_name`;
- `original_request` (unchanged authenticated request), its SHA256, source_scope SHA256, question_key and hypothesis_key;
- complete versioned adaptation-policy SHA256, shared-budget-policy SHA256 and renderer/schema identity;
- `prior_stage_proofs`: ordered predecessor cell IDs and their request, raw-response, validated-response and externally anchored cell-receipt hashes;
- `history_projection`: ordered `{stage, source_ids}` objects derived from those predecessors; `history_projection_sha256` and an explicit `untrusted_generated_selection_not_evidence` authority tag;
- the exact original alias/observation/pointer table and its fingerprint.

Canonical serialization uses existing canonical JSON/fingerprint functions. The raw fixture response binds to `fingerprint(stage_request)` and `fingerprint(payload)`; the output audit binds its validated response, original quote materializations, predecessor chain and policy. Prior proofs reside in execution provenance, never in original_request, source_scope or a scientific-record ancestry list. Case/arm/stage identity and accepted-prefix length must match exactly. A predecessor may contribute only after its raw response, strict postvalidation, request/source equivalence and cell receipt have all verified in the same comparison run and arm. An unrun, failed, malformed or cross-case predecessor cannot supply feedback.

**Caller-supplied hashes or IDs are not trusted history.** The implementation must rebuild each projection from the actual verified predecessor response's paired citations, sort/deduplicate its original aliases, and compare it to the serialized projection. No arbitrary role file, human selection, gold/reference packet or external fixture can be supplied as an accepted history shortcut. Recorded fixtures are explicit evaluator-only **transport test inputs**, not predictor evidence or human references; their contents are not accepted into the source graph. There is no general evaluator-only ancestry exception.

Only source aliases are projected into later prompt history. No prior candidate prose, rationale, quotations, human ratings, answers, correctness labels, suggested conclusion or asserted biological fact is inserted. Even these IDs are untrusted generated selection and cannot alter source membership, quote eligibility, missingness or scientific truth. The underlying full predecessor artifacts remain available only to execution verification. Maximum history is four stages, at most three source aliases per stage and 1,024 canonical bytes; no history truncation. Both present fixtures have only two aliases, so the preparation uses every possible alias at every prior stage as a conservative shape.

The twelve retained stage specs deliberately contain **no real accepted predecessor proofs**. Their history is labeled `history_is_worst_case_source_id_shape_not_an_accepted_response=true` and `dispatchable=false`. They are payload sizing/schema proposals, not executable stage requests, approved fixture responses or prevalidated run artifacts.

## Guide, schema and strict postvalidation

The common guide and role guidance are literal fields in PLAN-v2. Each payload includes the full original source request and an explicit table of original aliases and JSON pointers, eliminating the undeclared positional-pointer convention encountered in R07. Original strings preserve Unicode/HTML and runtime delimiters are escaped only in serialization, with source-byte equality restored by decoding. Complete payload hashes are retained.

The proposed native JSON schema derives from the retained active flat schema, narrows aliases and pointers to the current source table, uses the actual max_claims and retains state-dependent constraints. The native grammar's support for that schema remains **unverified** and does not authorize a native run. The authoritative postvalidator remains `diagnostic.validate_output(original_request, 'simplified', raw_document)`:

- answered: one or more claims and null abstention_reason;
- partial: one or more claims and a nonblank reason;
- abstained: no claims and a nonblank reason;
- each claim has exactly kind/text/source_ids/quote_pointers/limitations, at most two matched alias-pointer pairs, no foreign references or duplicate quote pairs;
- source_report has one citation and text exactly equal to its original source string;
- scientific_inference/caution is authored text with explicit limitations, not relabeled as a verbatim source report;
- nonblank/length/duplicate checks remain strict; unresolved entries are bounded; features stay empty and probability null.

Quotes materialized from pointer references are separate source-copy fields, not generated inference. The verifier must not repair malformed JSON, infer omitted fields, change partial to answered, substitute a correct pointer, or replace a model-authored sentence with an exact quote while presenting it as original output. Generative outputs and deterministic literal baseline results keep distinct scientific-answer semantics; empty generated_interpretations in a baseline is not an abstained LLM response.

## Minimal integration without a controller replacement

Reuse StudySession and RecordedBackend only for recorded generative fixture cells. A narrow `RoleRecordedVerifier` can override payload/response checks for the stage envelope while preserving recorded raw-byte identity and existing execution/package-proof checks. Current RecordedVerifier's unchanged renderer cannot validate a new stage payload; pretending it can would be incorrect. No existing native adapter automatically accepts this new interface.

The comparison layer needs only deterministic stage-request construction, same-run predecessor verification/projection, common-budget/deadline aggregation and final source-equality/masked-output checks. Keep existing deterministic baselines pure. A recorded chain's valid bytes establish mechanics, not scientific correctness or actual model quality. Retain comparator deviations and fixture-declared usage in evaluator-only artifacts; reviewer projections contain neutral labels and genuine source/inference distinctions, never an AI correctness key or method-identifying scores. A deterministic label map is not randomized blinding.

## Freeze and remaining checks

Before implementation, coordinator and peer review must confirm source equality, the history boundary, shared budget, schema/guide state alignment and adaptation naming. Then implement regression-first tests for cross-arm/case history substitution, fabricated caller feedback, quote/source changes, evaluator-reference injection, invalid partial states/pointers, feedback/payload/aggregate budget exhaustion, role omissions/reordering, fixture response/request mismatches and package/resource tampering. Verify the installed package without importing planning/tools and without native/network/child execution.

The model identity for any future separately approved native diagnostic is only the existing receipt-pinned Qwen2.5-14B-Instruct Q4_K_M asset family (acquisition receipt `cc95c56ce1f497b36d6b9ed62b22721d8af7eaccc0a8c50da91439c5b076acbf`). No model is activated or newly selected by this plan; a future runtime/model alias/options and transport proof must be separately pinned. R07 current native-version stop remains.

This is the **fixed-evidence** track. End-to-end retrieval needs a separate common corpus/index, source-bound query/response contracts, retrieval/tool budgets and failure/missingness accounting; it remains unimplemented. Original VB tools/model routing/full reproduction, real-case scientific references, human judgments and study completion remain separate. These limitations do not block the safe synthetic recorded engineering work once this prospective plan is accepted.
