# Question-bound runtime and pilot gate

Status: proposed next implementation specification. Core validation is a separate
checkpoint; this document alone approves no native call. The preceding scientific
failure remains failed and is not regraded under the new response contract.

## Scope and invariants

Build a separate durable execution path for the reviewed question-bound contracts.
Retain the legacy runtime modules byte-for-byte so archived code-bound verification
keeps working. Use the new core after complete source admission, keep generated
outputs separate from admitted evidence and scoring, and preserve features{} and
clinical_probability:null. Provider spending stays$0 and existing case-wide
budgets stay unchanged. No source acquisition, additional model weights, evaluator
answers, clinical labels, historical cohort, MR calculation or scorer training.

Candidate modules are question_interpretation_runtime.py for execution/verification,
question_interpretation_local.py for optional loopback transport and
run_question_development.py for separately frozen local execution. Reuse stable
journal, budget, immutable-envelope, hashing, file and local ownership primitives.
Do not refactor old module bytes in order to obtain code reuse. Any unavoidable
versioned orchestration duplication must be documented and covered by lifecycle
probes for both paths; it cannot justify weakening the existing guarantees.

## Durable execution

Reserve the output directory exclusively before dispatch. Archive the exact new
request, original admission inputs/proofs, selected question/version, effective
catalog, configuration, replay bytes and complete code/dependency identities. A
hash-chained journal records reservation, preflight, quote, dispatch, accounting,
accepted response and terminal success/failure. Output races fail before calls.

Use the existing interpreter quote/generate interface and immutable Generated
usage envelope. Validate response version2 identities and answer state before
claim delegation; never reclassify old responses. Persist exact raw native or
recorded bytes even when JSON or contract validation fails. Measured usage remains
separate from conservative reservations; unavailable measurements stay estimated.
Do not allow an archive/write failure to hide the original timeout or interruption.
Partial/interrupted attempts retain a readable journal, accounting and failure.
Recovery/inspect never dispatches or automatically repeats a potentially billed call.

Successful outputs require sealed hashes for request, response, inputs/configuration,
report, journal, replay and any backend execution record. Semantically reconcile
request identity, call counts, usage, code pins, final journal state and response.
A self-resealed arbitrary object is not proof of scientific validity or actual
provider execution. Native assets/ownership are declared locally, not remote
cryptographic attestation.

## Source-inclusive verification

Verification never generates. Reconstruct prepare_question from the exact original
case/snapshot/catalog, question family, source IDs and limits; compare the complete
new request fingerprint, immutable source/archive proofs and effective policy.
This reuses temporal, lineage and evaluator-parent gates rather than trusting a
saved agent_evidence label. Rebuild the scientific view and any native payload;
compare exact original request bytes, response identities, quotes and answer state.
Reconcile receipt outputs, journal dispatch/accounting, quote/reservation and native
usage. Verify code/dependency fingerprints for all executed helpers, including the
new core and unchanged legacy functions actually reused.

Report byte integrity, mechanical/source consistency and scientific validation
separately. Scientific_validation remains not_performed. A later independently
reviewed scientific seal must not be replaced by successful runtime verification.
Failed runs need not masquerade as finalized outputs; inspect their retained events.

## Native serialization and sizing

The current core views measure13767 and12403 canonical bytes for the two selected
sources, and76646 bytes for all9 admitted sources. They are not approved prompts.
Canonical hashing sorts object keys and cannot itself render scientific-first
salience. Define a deterministic explicit renderer with question and reported
passages before provider annotation/provenance. Archive rendered bytes and bind
all source data to the core view/reconstructed request. Preserve every field,
null/absence/type distinction, passage order and original quote pointer.

Guide text may avoid duplicating scientific instructions already present in the
reviewed question and retained source request. It may not remove a material
scientific boundary, add case-specific expected results, select passages using
review judgments, summarize away disagreement or suppress fields to manufacture
context fit. Source text remains untrusted; escape runtime control delimiters
without changing the reconstructed source. Rendering order is a design hypothesis,
not a demonstrated model improvement.

Before any generation, measure the COMPLETE actual prompt including guide, framing
and source data. The pinned runtime context remains16384 tokens and native output
cap2048. Existing conservative reservation uses prompt UTF-8 bytes plus32 tokens;
therefore prompt cap may not exceed14304 bytes with this output bound. This is an
upper allowable cap, not a finding that a particular renderer fits. Any configured
cap and shared32k-input/8k-output case reservations must pass exactly. The13767-byte
view leaves only537 bytes at that upper bound, including all guide/framing overhead.
At the previous14200 cap it leaves433 bytes. If full requests do not fit, stop and
retain a sizing failure. No automatic budget growth, tokenizer-based relaxation,
context increase, truncation or source substitution is part of this stage.

The full9-source view is outside that byte reservation; this milestone cannot claim
full-case coverage from it. A separately frozen selected-subset development pilot
retains all9 available/selected counts,65 missing collection inputs and absence:false.
Fresh evaluation later needs a predeclared retrieval/source-selection frame, not
cherry-picking based on scientific labels.

Native JSON schema represents answer_status and source_report/scientific_inference/
caution claims, with no abstention claim kind. Post-generation state checks remain
mandatory because valid JSON is insufficient. The adapter copies exact original
quote strings/UTF-8 spans from source alias+pointer references; it never repairs
inferences, edits contradictions or manufactures scientific context. End-of-sequence,
legacy/modern stop-cause consistency, limit/truncation, prompt/settings echoes and
exact JSON-type checks must retain the repaired native-format regressions. The
request temperature is explicitly0.0 as echoed by the pinned runtime. Disable
redirects/proxies and tools; use only the launcher-owned loopback endpoint, explicit
timeouts and no generation retry. Stop only the owned server on all terminal paths.

## Ordered acceptance before a new pilot

1. Independent scientific/methods review of this runtime/sizing specification;
   preserve reviewed versions and resolve concrete blockers before implementation.
2. Implement durable recorded execution/verification and regressions before native
   adaptation. Exercise timeout, malformed response, partial/abstained valid states,
   wrong question/scope, quote tampering, usage/journal disagreement, write failure,
   interruption, races and evaluator/future ancestors. Prove old artifacts still verify.
3. Implement and independently probe native renderer/transport using synthetic and
   retained runtime-format fixtures only. Measure exact actual source prompts and
   reservations. A no-generation complete sizing report is a separate gate.
4. Run appropriate full/isolated/dependency-free validation on unchanged final code;
   seal source, question, configuration and reference identities before execution.
5. Only if all preceding gates pass, freeze a NEW exposed development plan using
   the same2source-scoped questions/case/model and default case budget, one call per
   question, no retry. Record every previous-version call separately, and do not
   present exploratory versions as matched performance comparisons. If sizing or
   any other gate fails, no native call occurs until a separately reviewed proposal.
6. Seal exact candidates and stop server before2independently authored AI reviews
   and third evidence-based adjudication inspect every clause, proposition, quote,
   limitation and abstention reason. Bind all judgments to exact source locations.

The scientific gate is unchanged: both tasks finalize and each has a useful,
correctly bounded source-specific inference or contextual caution, without unresolved
critical source/numerical/context/intervention-transfer errors. Source copying,
generic disclaimers, all-abstention or hiding assertions in prose cannot pass through
zero errors. Answered/partial/abstained are model declarations, not verdicts. Useful
partial/caution components receive credit even if another assertion fails. Do not
turn missingness/nonsignificance into absence or charge ambiguous qualified prose
as unequivocal denial. Keep uncertainty and shared-AI/previous-exposure limits.

A failure stops that version; retain it without automatic experiments or parameter
search. A pass permits only fresh-question paired feasibility preparation. Neither
outcome establishes general T6/H5, clinical benefit, calibrated probabilities or
completion of original Tasks6–8. No user file/permission is presently required for
specification, core or recorded/synthetic runtime work; broader science/data gates
remain in their original plans.
