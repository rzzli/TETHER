# TETHER — Question-bound interpretation core

TETHER (Target Evidence Tracking Harness for Evaluation and Reproducibility) is the current project name. The `tether-target-agents` 0.4.0 package in `packages/tether` supplies the `tether` CLI and import namespace over the frozen AsOf 0.3.11 engine. See [installation and compatibility](../README.md#installation-and-compatibility). Historical version/arm names, module commands, source paths and wire IDs below remain unchanged; the rename does not reactivate retired study or expert-review branches. Direct API aliases preserve legacy outputs; only the separate `tether._presentation` CLI layer wraps `demo`/`run` in the [TETHER run layout](../README.md#tether-cli-run-layout). Delegated source inspection, snapshot construction and evaluation keep their engine layouts.

The experimental tools/science/interpretation_questions.py module adds explicit
scientific question identity, a reversible source view and coherent response states.
It has no backend, network, downloader, execution launcher or durable run verifier.
It does not implement clinical scoring or claim scientific truth.

## Interface

prepare_question(case_path, snapshot_path, family, catalog_path=None, ...)
performs existing complete T6 admission and returns copied/frozen Prepared request
and archive. Supported reviewed families are mechanism-report.v1 and
genetic-study-report.v1. Custom question text is excluded. The immutable version2
request retains the full version1 source request, then binds question/hypothesis,
selected source identities/record hashes, missingness and source context.

bind_question and validate_request perform structure/binding checks only. They do
not independently admit data or verify chronology. A caller cannot replace future
source-inclusive runtime verification with either helper. The admitted preparation
path remains prepare_question. Evaluator-only ancestors are still forbidden there.

scientific_view preserves every original source field, including opaque/null/absent
metrics and all textMiningSentences items. It separates reported passages, scientific
context, provider metadata and annotation. expand_view reconstructs the exact typed
request fingerprint. Neither function extracts biological conclusions or upgrades
provider text into validated premises. Original scientific-record pointers remain
the quote addresses; view positions are not new evidence locations.

validate_response checks version2 identities, declared answer_status and claims.
answered requires claims and no abstention reason; partial requires claims and an
explicit unresolved-scope reason; abstained requires an explicit reason and no
claims. Abstention is not a claim kind, so it cannot carry an affirmative proposition
inside a supposedly abstaining claim. source_report/scientific_inference/caution
retain exact source quotes, propositions, limits and applicability checks. The
old claim validator is called only in an unarchived transient envelope after v2
prechecks; malformed legacy enum types become ContractError. Accepted state is a
deeply immutable copy. Features remain{} and clinical_probability remains null.

This does not establish entailment or reconcile arbitrary prose. Unsupported prose
and limitations remain reviewable even when claims is empty. A response declaring
answered has not passed scientific review. Verbatim source copying, generic
cautions and all-abstention cannot pass the existing positive utility gate.

## Archived compatibility

The three legacy interpretation modules are unchanged. Existing successful v1
sidecars retain exact-code/source verification; failed runs remain failed. New
requests/responses are not accepted as v1 or silently converted into old archives.
No original fixture or receipt is rewritten. Retained input archives include the
original source proofs and question version, but are not finalized v2 run receipts.

A later runtime must reconstruct admission and the new request, archive effective
code/configuration, bind responses to the complete fingerprint and persist failures,
accounting and cleanup. It must define recorded/native adapter migration before
execution. The old verifier is not a new-runtime verifier.

## Sizing and serialization

The actual-format source-scoped views measured13767 and12403 canonical bytes;
all9 admitted sources measured76646 bytes. The first leaves only433 bytes under
the prior14200-byte prompt cap before any guide or framing. These measurements do
not establish native context fit. No source field may be dropped to manufacture fit.
Native schema, guide, reservations and full prompt require separate sizing/review.

Fingerprint serialization sorts JSON keys. It is not a prompt renderer and would
not guarantee scientific-first salience. View artifacts written with normal
write_json preserve insertion order; a future native renderer must explicitly
preserve question/passage ordering, archive its exact bytes and still round-trip
all data. No effect on model behavior is established by field order alone.

All65 declared missing inputs remain explicit; selected subsets are not complete
collection and cannot imply biological absence. No generation, new data acquisition
or scientific qualification is part of this core checkpoint.

Specification: planning/Question-Bound Interpretation Specification 2026-10-25.md.
Current predecessor/remaining work:
planning/Interpretation Qualification Closeout and Next Design 2026-10-25.md.
Validation receipts: planning/review-assets/question-interpretation-20261025/.

## Core checkpoint

1160 full tests/probes/package,197 isolated tests and105 no-site tests pass with
unchanged final source code. Independent methods probes pass; both legacy native
outputs still source-verify. The reviewed next runtime plan is
`planning/Question-Bound Runtime and Pilot Gate 2026-10-25.md`. It approves recorded
runtime implementation only; no adapter, new native run or scientific qualification
is part of this core completion.
