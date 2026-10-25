# Experimental bounded interpretation

`tools/science/bounded_interpretation.py` adds a repository-only experimental
sidecar interface. It leaves `Backend.quote()`/`Backend.select()`, workflow
execution, evidence ledgers, features, scoring and archived run semantics intact.
It provides an offline recorded-response interpreter; it adds no live adapter,
CLI command, network client, default runtime dependency or clinical probability.

## Source admission and request

`prepare_input(case_path, snapshot_path, catalog_path=None, ...)` validates a v2
T6 case and uses the existing complete snapshot admission route: catalog roles,
input ancestry, temporal/publication eligibility and source hashes. Clinical
category rows are excluded from this source-only experiment. Embedded literature
may still contain clinical claims; this is not a semantic clinical-content filter.

The immutable request contains the hypothesis, case, admitted source observations,
record fingerprints and source citations. Prediction features are hidden. No
evaluator reference, review, primary-adjudication label or filesystem capability
is added. Provenance paths and effective catalog policy are archived separately
for the trusted runner, not passed as the archive object to the interpreter.
Source records may themselves carry provenance strings; these are not tools.

Default limits are 256 observations, 12 claims, 8 quotes per claim, 8 KiB per claim
text, a 64 MiB request and a 256 KiB response. Exceeding a bound fails explicitly;
records are not silently dropped. Only a declared snapshot missing-input count is
shown; otherwise it remains unknown. Incomplete collection cannot become a
machine-generated biological absence declaration.

## Output boundary

Each response binds the exact request and hypothesis fingerprints. Claims contain
separate contextual propositions, source quotes, declared premises, applicability
and limitations. A proposition preserves subject/relation/object, modal force,
negation, population, tissue, intervention, comparator, endpoint, timing and
exposure/outcome orientation. Missing context stays null.

Quotes point to original admitted string values with RFC6901 pointers and
half-open decoded UTF-8 byte coordinates. All cited premises require an exact
quote. `source_report` text must equal its sole quote; newly generated prose is
explicitly `scientific_inference`, `caution` or `abstention`. Inference, caution
and abstention require limitations. Empty output needs an abstention reason.
Structured features must remain empty and clinical probability must remain null.

These are structural and provenance checks. They do not establish that a
proposition follows from its quotes, that a quotation includes sufficient
context, that reported numbers are scientifically interpretable, or that prose
avoids clinical overreach. Candidate applicability is a model declaration, not
validated pharmacological applicability. Incorrect inferences can be structurally
valid and must be detected by the separate scientific audit.

## Execution and recovery

`run_interpretation(...)` reserves a new output directory before admission,
archives the request, effective input proofs, configuration and code fingerprints,
and journals the quote, dispatch, usage and terminal result in a hash chain.
It dispatches once with the remaining timeout, preserving current budget defaults
and zero provider-spending cap. It never retries or resumes a potentially billed
call. Adapters are trusted code: quote must be local, and generation must enforce
its transport timeout. This runner cannot interrupt arbitrary blocking Python
code or provide an OS sandbox.

Valid adapter usage is retained even when response parsing or contract validation
fails. Unexpected exceptions and interruption retain conservative quoted usage
when measured usage is unavailable. Raw bounded response text is retained; an
oversized response records its byte count/hash and fails. Disk errors leave the
durable journal prefix. Existing output cannot be reused, including concurrently.

`RecordedInterpreter(path)` reads one bounded, immutable response document bound
to the request fingerprint. Its exact original UTF-8 bytes and parsed document
are archived, together with usage. A recorded call is not model execution.

`verify_interpretation(output)` never dispatches. It reconstructs current source
admission, compares the archived request and source inputs, verifies output hashes,
code identities, quote/configuration decisions, call accounting, raw responses and
the absence of structured predictive outputs. It requires the original input
files and matching recorded code; a hash chain is not external authentication or
proof that a provider actually executed. Receipt integrity and mechanical
consistency do not establish scientific quality.

## Qualification still required

The existing [primary reference](T6_PRIMARY_REFERENCE.md) is an exposed-case AI
development reference. Synthetic lifecycle/contract tests qualify these boundary
mechanisms only. Next retain source-only candidate interpretations, assess their
premises/inferences against the pinned reference with independent AI review, and
document unassessable content without a zero-error victory. Then freeze fresh
questions, reference/prediction seals and paired analysis before new evaluation
outputs. Full T6/H5 and original scientific Tasks 6–8 remain unfinished.
