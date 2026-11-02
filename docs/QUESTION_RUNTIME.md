# TETHER — Recorded question runtime

TETHER (Target Evidence Tracking Harness for Evaluation and Reproducibility) is the current project name. The `tether-target-agents` 0.4.0 package in `packages/tether` supplies the `tether` CLI and import namespace over the frozen AsOf 0.3.11 engine. See [installation and compatibility](../README.md#installation-and-compatibility). Historical version/arm names, module commands, source paths and wire IDs below remain unchanged; the rename does not reactivate retired study or expert-review branches. Direct API aliases preserve legacy outputs; only the separate `tether._presentation` CLI layer wraps `demo`/`run` in the [TETHER run layout](../README.md#tether-cli-run-layout). Delegated source inspection, snapshot construction and evaluation keep their engine layouts.

The separate tools/science/question_interpretation_runtime.py executes and verifies
question-contract version2 without changing any legacy interpreter module. It has
no built-in native model adapter, downloader or paid provider. The separate optional
[local adapter](QUESTION_LOCAL.md) uses its explicit verifier callback. Scientific qualification
remains failed from the previous development attempt.

## Execution and verification

run_question_interpretation(case,snapshot,family,output,backend,catalog=None,...)
reserves a fresh directory before admission and dispatches at most once. It archives
the immutable request, original lineage/admission archive, scientific view, effective
policy, budget, adapter declaration, Python version and complete local static import
closure. Package initializers are included in that code identity. Source admission
is repeated before successful finalization, including original parent proofs.

RecordedQuestionInterpreter reads a capped version2 replay, keeps its exact original
UTF-8 bytes and parsed document, binds request fingerprints and permits one use.
The constructor and verifier share the same strict field/version/size contract.
The reserved recorded provenance kind additionally requires the built-in module
identity, request and original-byte/document consistency before dispatch. Missing,
null or unknown provenance requires an explicit trusted verifier; archived paths
are never imported as executable code. Optional adapter callbacks are explicitly
supplied trusted code, pinned and checked before sealing and during verification;
they are not execution attestations or scientific adjudicators.

verify_question_interpretation re-admits sources and reconstructs the complete
question request and scientific view. It checks output hashes, journal/report/run
identity, quote and dispatch decisions, measured accounting, exact raw response,
accepted claims, replay provenance and code identities. Byte integrity, mechanical
consistency, source readmission, adapter declarations and scientific validation are
reported separately. Scientific validation remains not_performed; features remain{}
and clinical_probability:null. A source-linked or answered result is not necessarily
scientifically useful or true.

## Durable attempts and failures

The journal records reservation/preparation, quote, dispatch, raw capture, accounting,
accepted response and terminal outcome. Responses are captured before JSON/contract
validation. The response contract cap is256KiB. Raw capture keeps up to64MiB; an
over-cap prefix is explicitly marked incomplete with original/retained byte counts
and hashes. Such captures cannot pass successful verification. The optional native
transport independently preserves its bounded original bytes, separately from
this runtime's translated response text.

Reported usage and conservative unknown usage are distinct. Usage.cost_usd is
normalized through its declared floating type; original replay bytes and scientific
JSON scalar types are preserved. Timeouts/interruption never trigger an automatic
repeat. The generic build inspector is not used for call accounting.

inspect_question_interpretation reads interpretation dispatch/account events,
includes outstanding reservations in estimated_upper_usage, accepts a physically
incomplete final journal line and never dispatches. Duplicate/foreign accounts are
rejected. It reports unverified receipt presence separately from successful
verification. Inspection is not a cost invoice or provider attestation.

Secondary account/archive-notice/terminal/close errors preserve the original
exception. A run-bound failure.json fallback records failure when possible, including
secondary diagnostics; it is not a success receipt or authenticated scientific
artifact. A known failure fallback blocks finalized verification even if a prior
receipt exists. When all storage writes fail, the original exception/notes and last
durable journal are retained as far as the filesystem permits; a terminal write
cannot be guaranteed on unwritable storage. No failed directory is overwritten.

Sealing is acyclic: the terminal journal binds report.json, then receipt.json hashes
all outputs including the completed journal. The journal does not hash that receipt.
Concurrent reservations fail before calls. Recovery and verification never retry.

## Scope and remaining gates

Focused synthetic regressions and independent methods probes cover lifecycle and
resealed semantic failures. Two real-source recorded abstention fixtures demonstrate
source-inclusive execution/verification and correct available=9, selected=1 and
missing=65 per request. These are scripted fixtures, not generated scientific
answers or qualified dossiers. Original successful native sidecars still verify.

Full project, isolated-copy and dependency-free validation passed for this stage.
Native scientific-first rendering, exact escaped/framed prompt
sizing and optional native transport now pass their separate mechanics checkpoint;
the next frozen pilot remains a later gate. The13767-byte
source view has little guide/framing headroom; no field truncation or context-cap
increase is authorized. Prior scientific failures and original Tasks6–8 remain open.

The later renderer/transport checkpoint passes1,239 full tests/probes/package,
276 isolated and184 no-site tests. Exact complete prompts measure14,149/12,785 bytes.
No new native generation follows from those mechanics checks. See QUESTION_LOCAL.md.

Reviewed specification: planning/Question-Bound Runtime and Pilot Gate 2026-10-25.md.
Evidence: planning/review-assets/question-recorded-runtime-20261025/.

## Recorded checkpoint

1198 full tests/probes/package,235 isolated-copy tests and143 no-site tests pass
on unchanged code.38 focused runtime tests and10 independent probe groups pass.
Both real-source recorded fixtures and both prior successful native sidecars
source-verify. Retained failed audit versions and final correction proofs are
under the evidence directory. Native renderer proposal is independently reviewed
for implementation only at that checkpoint. The later tested production renderer
removes its known newline bug and preserves exact source reconstruction. No scientific qualification
or new native generation follows this recorded checkpoint.
