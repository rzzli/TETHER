# Bounded local specialist pilot

**Status: Task 4 technical development and validation completed.**
Ten original dossiers and three focused lossless-wire dossiers passed source-inclusive
verification. Scientific review and clinical evaluation remain unqualified.
This document describes exposed T6 development work, not independent scientific
validation or a locked clinical comparison. The model selects source observation
IDs; accepted factual statements are copied from admitted records. Probabilities
remain null and real numerical prediction features remain empty.

## Model, data and controls

Official Qwen2.5-14B-Instruct Q4_K_M uses the three pinned GGUF shards at revision
`b466e1f8c07172155743e8e1307507d8a4f91fbd`, totaling 8,988,110,496 bytes.
The separate download tool verified every publisher LFS SHA-256. Portable llama.cpp
`b11717` uses the publisher-hashed Windows Vulkan archive (32,307,240 bytes).
Extracted runtime binaries are rehashed before launch. Assets and the original
license are on E:, outside Git. The biomedical downloader/monitor are unchanged.

The launcher owns one IPv4-loopback server with `--offline`, a 16,384-token context,
one slot and eight CPU threads. It starts without a visible window and is stopped
in `finally`. Local model setup is explicit; the dependency-free default stays
offline extraction. The model has no search, filesystem, evaluator-label or tool
interface. Python orchestration is trusted code, not an OS sandbox.

Inputs are the canonical complete-selected-literature contemporary build,
`data/derived/literature-coverage-20261017T082208Z`, selected through the run registry.
Old source packets, baseline outputs and receipts are unchanged. Historical source
eligibility and the candidate clinical window are separate gates.

Each category receives whole admitted records ranked by literal case-token overlap,
then stable ID. Maximums are 12 records and 12,000 canonical UTF-8 bytes; a separate
rendered-prompt byte cap includes escaped role delimiters. Oversized records are
reported and skipped, not truncated. Provider scores do not become ranking weights
or effect sizes. These conservative packets can hold very few complete records;
that limits the selection exercise and is not evidence of biological absence.

The model returns at most three allowlisted IDs, with temperature zero, seed
20261017 and 256 generation tokens. A deadline and bounded response reader protect
each attempt. No automatic HTTP retry occurs. The workflow retains its existing
16-call/32,000-input-token/8,000-output-token/$0/300-second defaults. Source admission
and source-inclusive verification are outside the workflow meter; end-to-end times
include them and must not be described as inference latency.

## Verification and retained evidence

The model archive seals exact requests, native payloads, responses, hashes and usage.
Finalization and verification recompute retrieval from admitted records, match model
selections to the dispatch/journal and ledger, and independently check current raw
parents and archived receipts. A separate process verifies every completed dossier.
Failures retain the reserved directory, console output, attempts and accounting.

The code passes 218 full-suite tests, required probes, PowerShell syntax and installed
wheel/demo checks. Ten local-adapter tests cover caps, whole-record exclusion,
ordering, role-token injection, remote endpoints/redirects, malformed or out-of-packet
IDs, timeout accounting, provenance tampering and attempted rewriting of admitted
content. Four hosted Windows/Linux core/full jobs passed for the initial 216-test
code checkpoint; the two additional adversarial checks passed locally.

The completed OSMR case has also replayed with identical ledger, features and null
prediction and zero model-server calls. Replay accounting uses recorded original
tokens; it does not mean tokens were consumed during replay. The first replay
diagnostic is retained separately from the corrected tool's fresh-output validation.

Active pilot: `runs/local-model-pilot-20261018T033050Z`. The execution journal,
per-case verification, resource observations and final seal are retained there.
`planning/review-assets/ordered-execution-20261017/` holds sanitized test/replay/CI
evidence. Model receipts are under the E: model root. This is technical execution
and source consistency; biological relevance and independent reference quality
remain unestablished. No clinical AUROC, calibration or therapeutic claim is produced.

## Interim correction and transport amendment

The original ten-case run finished and its owned server stopped. All ten dossiers
passed separate-process source-inclusive verification: 22 local calls, 61,022 input
tokens and 1,247 output tokens, with $0 provider charges. Native prompt/generation
time summed to 64.797 seconds; end-to-end time was 3,075.469 seconds. Original inputs
span 8,256,817,498 unique bytes. These timings measure this machine and workflow,
not model quality or an amortized production service.

The original cap admitted only one candidate per model call. Preserve that result
as a diagnostic, not a ranking-quality benchmark. Frozen evaluation-v0.2 adds a
readable lossless common-field transport and three fixed development validation
cases. Every scientific field, null, context, parameter and identity reconstructs
exactly. The adapter still accepts only unchanged admitted views and source IDs.
The canonical representation and its old trace fingerprints remain compatible.

A new regression reproduced acceptance of a native truncated/unqualified prompt
with otherwise valid JSON. The adapter now rejects it. All 22 original responses
report `truncated: false`; sealed outputs pass the stronger response and unchanged
canonical retrieval checks. That compatibility pass did not repeat raw hashing;
the original per-case source-inclusive checks are retained separately. The full
suite now passes 228 tests. The focused new-format native run is still in progress;
Task 4 remains incomplete until it passes. Do not pool the two formats as a
comparative or independent scientific evaluation.

The final all-ten transport probe fits 66 candidates versus 22 under the original
format at the same 12,000-byte cap. Twenty of 24 populated categories fit multiple
candidates. Every probed selected packet reconstructs exactly; this is a width and
fidelity measurement, not model-quality validation. The full suite now passes 229
tests including portable seal-path handling. The focused native run remains active.

## Final focused validation

All three cases frozen in evaluation-v0.2 passed source-inclusive verification and
the multi-candidate acceptance checks. The owned server is stopped. The focused
run used seven calls, 26,030 input tokens and 764 output tokens, with $0 provider
charges. Native prompt/generation time summed to 22.090 seconds; total time including
asset checks, admission and verification was 749.109 seconds. It is a separate
engineering validation, not an independent three-case scientific benchmark.

The source-inclusive native run is `runs/local-wire-pilot-20261018T042530Z`. Its public
anchor is `data/manifests/public/2026-10-17-local-model-wire-pilot.json`; original
ten-case output is retained separately under its canonical-pilot public anchor.
The 229-test full suite and four hosted Windows/Linux jobs passed at 48359ca.
The later genetics feasibility decision defers features and training; the ordered
execution is stopped at Task 6 for missing qualified scientific comparison inputs.
See `Ordered Execution Progress 2026-10-17.md` and `TODO.md`.

A session-local sample observed native-process peak working set of 13,890,174,976
bytes so far and total device use of 13,250 MiB. The GPU sample includes other
applications and is not a continuously measured isolated peak. These measured
workloads fit this 32 GiB/16 GB machine; they do not size the full data inventory.
