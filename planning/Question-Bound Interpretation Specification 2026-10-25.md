# Question-bound interpretation specification

Status: proposed for independent scientific and methods review before implementation.
This is the next stage after the failed development qualification. It does not
change old artifacts or their scientific verdicts, authorize another native run,
qualify full T6/H5 or reopen clinical evaluation. Original project scope remains.

## Design objective

The request must state the scientific question actually assessed. Scientific
passages should be readily visible without deleting scientific fields, provider
annotations or provenance. A response must distinguish a question from a proposition
it endorses. These changes address plausible framing/representation defects; their
scientific benefit is unproven and still requires an independently reviewed pilot.

## Frozen generic question families

No target names, disease-specific answers, study results, reference judgments or
expected directional conclusions are permitted in the template registry.

**mechanism-report.v1** — What experimental or observational mechanism context is
reported in the offered sources? Identify reported manipulation or exposure, model
and population, comparator, measured endpoint and timing when supplied. Distinguish
reported findings from the source authors' proposals and from your inference. State
how context limits applicability to the case hypothesis. Missing fields remain
unprovided; do not assume absent biology or clinical benefit.

**genetic-study-report.v1** — What genetic exposure/outcome evidence is reported in
the offered sources? Identify exposure and outcome orientation, study design,
instruments/proxies, discovery and replication where reported, estimates/units and
uncertainty when supplied. Separate cited prior findings from the present study.
Explain supported conclusions and limits of transfer to the intended intervention,
modality and tissue. Do not equate nonsignificance with absence, infer an unknown
scale or convert a genetic exposure association into a drug effect.

Questions may be unanswerable from an admitted subset. The registry is closed and
versioned; callers choose a family rather than supplying unrestricted text that
could contain evaluator answers. Future families need separate reviewed versions.
No source is selected or ranked using evaluator labels.

## Request contract version2

A new module constructs requests after existing complete T6 admission via the old
prepare_input function. It retains the exact immutable version1 source request as
source_request, including case/hypothesis versions, evidence, limits and declared
coverage. It adds schema_version2, role agent_evidence, question (closed template),
question_key (canonical template fingerprint), hypothesis_key and source_scope.

source_scope names the snapshot, ordered admitted observation IDs and the selected
scientific-record fingerprints. The complete new request fingerprint binds the
question, hypothesis, source records, missingness and all other input fields. Same
source/different question must yield distinct fingerprints. A source scope is not
proof that collection is complete. Snapshot coverage must retain missing/available/
selected counts and absence_claim:false; unknown coverage is not a zero count.

The returned request and archive are deeply immutable copies. The archive retains
original source/receipt proofs and the exact question and version. Structure checks
alone cannot establish source admission. Execution/verification must reconstruct
admission and this request before claiming source-inclusive integrity.

## Reversible scientific-first view

The view places the question first, followed by records with reported_passages,
scientific_context, provider_metadata and annotation. reported_passages holds the
entire original textMiningSentences field, including every item and unknown nested
field, without selecting sentences, changing their order or extracting results.
scientific_context holds the other scientific-record fields. provider_metadata
holds remaining source_metrics. annotation holds every other evidence-row field,
including summary, source reference and fingerprints. Complete source-request and
new-request context is retained separately.

Explicit presence/object flags preserve absent versus null versus empty fields;
non-object source_metrics and non-list passage values are retained as opaque data
rather than fabricated into scientific passages. Every field must round-trip to
the canonical request with exact JSON types. No summarization, derived support
weight, semantic normalization, score conversion or source substitution occurs.
Original quote pointers still refer to scientific_record; view locations are not
new source locations. Provider text is untrusted source data, not instructions.
The view is not automatically admitted evidence or a scientific interpretation.
A later native prompt must include it in full or fail its context cap explicitly.

## Response contract version2

Fields: schema_version2, kind question_interpretation, request_sha256,
hypothesis_key, question_key, answer_status, claims, abstention_reason, features
and clinical_probability. The last two remain {} and null. All identity fields
must match the complete new request. A hypothesis key identifies the question
frame; it is never an endorsed positive assertion.

- answered: at least one claim and null abstention_reason.
- partial: at least one claim and a nonempty reason identifying unresolved scope.
- abstained: no claims and a nonempty reason. No affirmative structured proposition
  can hide inside an abstention claim because abstention is not a claim kind.

Claim kinds are source_report, scientific_inference and caution. All retain the
existing proposition, text, premise IDs, original UTF-8 quotes, limitations and
applicability contract. source_report remains verbatim quoted attribution; it does
not by itself satisfy positive scientific utility. Inference and caution require
source-linked propositions and limitations. Any positive proposition remains a
candidate assertion subject to semantic expert review. Marking a claim caution or
applicability uncertain cannot make an unsupported proposition acceptable.

All claims require exact source references and original quotes. Existing bounds
remain enforced. Empty-source requests cannot invent supporting claims. The new
validator may reuse unchanged version1 claim/quote checks internally with a
transient legacy envelope, while the archived response and external interface stay
version2. This reuse does not authorize rewriting an original response or treating
an old run as a new contract.

Mechanical checks enforce enum/shape/state consistency, not truth, biological
entailment, usefulness or complete consistency of generated prose. answered is a
model declaration, not verified scientific success. partial/caution output can
contain useful evidence; its role is not grounds for automatic acceptance or
rejection. All-abstention, repeated source copying and generic disclaimer-only
outputs continue to fail the positive utility gate. Unsupported assertions in
prose or limitations still count scientifically even when the structured claim
set is empty. No new contract can hide these obligations through a zero-error
score or fewer reviewed fields.

## Compatibility and implementation order

Do not edit the old bounded_interpretation.py, local_interpretation.py or native
launcher during this stage. Their exact-code archived verification must keep
working. Add a separate interpretation_questions.py core module and synthetic
regressions first. No downloads, native adapter, execution launch, paid queries,
clinical labels or source changes belong in this core stage.

After review approval, implement question selection/binding, immutable request
construction, reversible view and version2 response checks. Tests must cover both
families on the same source, unknown families, tampered bindings/scope, null versus
absence and exact scalar types, all nested source fields, exact quote positions,
future/evaluator-only source rejection through existing admission, unsupported
answer-state shapes, uncited claims, valid positive/caution fixtures and useful
partial responses. Tests are synthetic contract checks, not scientific validation.

Retain an actual-format view round-trip with selected existing source packets,
missingness preserved and no generation. Record size measurements rather than
claiming the scientific-first view fits the pinned native context without sizing.
Oversized inputs fail later; scientific fields must not be truncated to fit.

A later separately reviewed runtime milestone must define durable version2
execution/verification, local transport, full-code identities, accounting, migration
and recovery before any new frozen native pilot. No current failed plan is rerun.
Core completion is not runtime completion; runtime completion is not scientific
qualification. Update TODO and memory with these separate gates.

## Acceptance and remaining work

Independent scientific and methods review must resolve specification defects
before code. Retain those reviews and immutable reviewed versions. After code,
retain focused/full/isolated validation, unchanged legacy code fingerprints and
actual-format lossless reconstruction/coverage. Reviewer judgments remain
procedurally independent with shared-AI/exposed-case limits.

The original failed scientific gate remains failed. Fresh paired experiments,
general T6/H5, clinical scoring, registry-scale eligibility, power and original
Tasks6–8 remain unfinished. This stage needs no user file or permission; it uses
existing admitted public inputs only. Evaluator-only primary qualifications remain
excluded from agent-visible input.
