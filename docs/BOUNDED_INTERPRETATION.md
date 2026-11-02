# TETHER — Experimental bounded interpretation

TETHER (Target Evidence Tracking Harness for Evaluation and Reproducibility) is the current project name. The `tether-target-agents` 0.4.1 package in `packages/tether` supplies the `tether` CLI and import namespace over the frozen AsOf 0.3.11 engine. See [installation and compatibility](../README.md#installation-and-compatibility). Historical version/arm names, module commands, source paths and wire IDs below remain unchanged; the rename does not reactivate retired study or expert-review branches. Direct API aliases preserve legacy outputs; only the separate `tether._presentation` CLI layer wraps `demo`/`run` in the [TETHER run layout](../README.md#tether-cli-run-layout). Delegated source inspection, snapshot construction and evaluation keep their engine layouts.

`tools/science/bounded_interpretation.py` adds a repository-only experimental
sidecar interface. It leaves `Backend.quote()`/`Backend.select()`, workflow
execution, evidence ledgers, features, scoring and archived run semantics intact.
It provides an offline recorded-response interpreter and an explicit optional
loopback interpreter for the separately pinned local model runtime. It adds no
remote provider, default `asof` CLI mode, Python runtime dependency or clinical
probability.

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

An explicit `observation_ids` list can select only admitted, case-eligible,
non-clinical-category records. Foreign and duplicate IDs fail. The request retains
available versus selected counts and the selection scope; an empty subset is
not biological absence. No records are dropped implicitly to satisfy a prompt cap.

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

## Explicit local generation

`tools/science/local_interpretation.py` uses only loopback HTTP, disables proxies,
rejects redirects and has no tools or generation retries. It shares identical
scientific fields losslessly, checking complete round-trip fingerprints. JSON
null/absence and boolean/integer/float distinctions are retained. The model cites
an offered source alias and original string pointer; the adapter copies its whole
original value and exact byte span. The model still authors propositions and
inferences, which can be wrong despite exact quotes.

The local contract restricts output to at most four claims, two quotes per claim,
1,800 characters per text and four limitations. Schema bounds are rechecked after
generation. Prompt bytes plus output tokens and special-token margin must fit the
16,384-token runtime context. Native completeness flags and measured usage are
checked; malformed responses retain native bytes and measured accounting where
valid. Exact native payloads, original response bytes, configuration, translation
and usage are archived and reconstructed during verification.

`tools/science/run_interpretation_development.py` separately freezes source-only
requests, verifies pinned assets, owns the loopback listener and stops only its own
process before sealing candidates. Its initial two-task development protocol is
in `planning/Bounded Interpretation Development 2026-10-25.md`. Both tasks share
the unchanged case-wide budget. Asset verification/startup are separate from the
generation clock. This is an exposed development exercise, not a fresh study.

## Qualification still required

The existing [primary reference](T6_PRIMARY_REFERENCE.md) is an exposed-case AI
development reference. Synthetic lifecycle/contract tests qualify these boundary
mechanisms only. Next retain source-only candidate interpretations, assess their
premises/inferences against the pinned reference with independent AI review, and
document unassessable content without a zero-error victory. Then freeze fresh
questions, reference/prediction seals and paired analysis before new evaluation
outputs. Full T6/H5 and original scientific Tasks 6–8 remain unfinished.

## October25 native development outcome and repair

The first native plan failed at transport validation; separate source-bound AI
reviews also rejected its scientific interpretation. One request ran and the
second was not dispatched. Exact quotations did not rescue unsupported biological
strength inferred from a provider score or denial of reported mechanism context.
The failed journal and original code remain retained.

The separately frozen repair accepts the pinned runtime's modern EOS completion
form, rejects conflicting/limited/truncated stops, and checks exact prompt and
generation-setting echoes. It keeps lossless source fields, identifies descriptive
provider metadata explicitly and asks for distinct source-specific scientific
reading. Version-two development plans bind the claim cap in prepared requests.
The current pilot uses two claims and a14200-byte prompt cap, within the unchanged
16384-token context and shared case budget. No case-specific scientific answer
is supplied. See the repair protocol in
`planning/Bounded Interpretation Repair 2026-10-25.md` and current TODO.md for
validation, execution and scientific qualification status. Older test counts above
are dated checkpoints; they do not establish repaired scientific validity.

The repaired run subsequently finalized both tasks and passed source-inclusive
verification (8552 input/720 output tokens). Two AI reviews and adjudication reject
scientific qualification: inadequate mechanism utility and an unsupported structured
intervention proposition remain. The genetics-transfer caution is credited and the
broader prose-denial charge is narrowed to ambiguity. This version is stopped.
See `planning/Interpretation Qualification Closeout and Next Design 2026-10-25.md`
for the retained closeout and ordered source-question/representation redesign.
No new generation or fresh paired evaluation follows this failed gate.
