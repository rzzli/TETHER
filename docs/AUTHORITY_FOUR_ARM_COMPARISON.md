# TETHER — Authority-bound four-arm recorded comparison

TETHER (Target Evidence Tracking Harness for Evaluation and Reproducibility) is the current project name. The `tether-target-agents` 0.4.2 package in `packages/tether` supplies the `tether` CLI and import namespace over the frozen AsOf 0.3.11 engine. See [installation and compatibility](../README.md#installation-and-compatibility). Historical version/arm names, module commands, source paths and wire IDs below remain unchanged; the rename does not reactivate retired study or expert-review branches. Direct API aliases preserve legacy outputs; only the separate `tether._presentation` CLI layer wraps `demo`/`run` in the [TETHER run layout](../README.md#tether-cli-run-layout). Delegated source inspection, snapshot construction and evaluation keep their engine layouts.

The recorded composition was qualified under 0.3.7. Current package 0.3.10 connects
the [original-path interface](INTERPRETATION_INTERFACE.md) to an explicit
[native adapter mode](NATIVE_INTERPRETATION.md) of this same controller. Simulated
transport qualification passes; actual model/grammar/scientific qualification
remains open. The preserved real-input recorded run remains verified by its
matching 0.3.7 package rather than being relabeled as new execution.
The collected-source extension below connects
receipt-verified original inputs to the same recorded mechanism. Earlier 0.3.6
engineering acceptance remains preserved. Neither version establishes model
quality, scientific sufficiency or biological validity.

## Collected-source extension in 0.3.7

```python
from asof.contracts import Category
from asof.study.collected_source import CollectedSourceInput
from asof.study.authority_four_arm import smoke, verify

source = CollectedSourceInput(authority_path, authority_sha256,
                              approved_input_roots, Category.LITERATURE)
result = smoke(new_output, tokenizer_authority, tokenizer_roots,
               collected_source=source)
verified = verify(new_output, result["receipt_sha256"],
                  source_roots=approved_input_roots, deadline=absolute_deadline)
```

The explicit immutable capability object supplies source roots and an external
authority hash. Fresh source preparation and retrieval run within the same
300-second budget. Original inputs stay under ordinary Windows sharing locks
through dispatch and source verification. Logical `case_run/source` references
allow run-bundle relocation. Replay must receive caller-approved original input
roots; archived physical locations never grant access. This is run relocation,
not independent restoration of the original source collection.

The accepted exposed IL6R/RA/inhibit/antibody case uses five literature candidates,
one whole selected record, nine available observations and 65 missing inputs.
Each scripted claim copies a complete source `/statement`; oversized statements
produce explicit fixture abstention, never clipping. Extractive limits respect
`min(3, inherited max_claims)`. Real reviewer views retain case, question, action,
modality and unspecified tissue. These are evaluator-only transport fixtures,
not generated interpretations, independent references or an answer key.

Execution finalized in 157.8 seconds with 22,067 input/6,144 output reservations.
Six exact offline tokenizer children ran; actual model calls/provider spending
were zero. Source-inclusive replay took 23.58 seconds. Isolated installed replay
and relocation took 29.30/29.27 seconds with all guard lists empty. The run bundle
is 792,175 bytes; measured parent peak working set was 484,769,792 bytes. Child peak
memory was not independently measured. Default installation remains dependency-free;
optional replay uses existing byte-verified Arrow 21, with no new downloads.

Acceptance passes 1,660 full tests without failures/errors/skips, 26 focused
regressions, 314 unchanged pins, seven installed legacy families and all six
matching 0.3.1–0.3.6 verifiers. The 14 new tests are code-author tests; retained
independent tests are not a new independent review of this extension. See
[acceptance and limitations](../planning/review-assets/recovery-step9-collected-composition-20261027/CLOSEOUT.md)
and [next engineering/scientific gates](../planning/review-assets/recovery-step9-collected-composition-20261027/NEXT-GATE-AUDIT.md).

## Preserved 0.3.6 invented qualification

Accepted 0.3.6 engineering implementation on 27 October 2026. This slice connects one
authenticated invented retrieval subset to six scripted cells and two pure
baselines. It makes no model-quality or biological-validity claim.

## Fixed scope

The universe is `invented-six-v1`; retrieval uses only
`literal_case_overlap_then_id_v1`, selecting original records id03/id04. Every
candidate, including excluded records, is qualified. All arms receive the same
complete selected scientific records, original references, identifiers and
coverage. Statements, structured context and missingness are preserved.

The comparison contains one AsOf interpretation stage, five explicitly adapted
Virtual Biotech role stages, an exact-statement extractive baseline and an
exact-statement lexical baseline. The adapted arm does not reproduce Virtual
Biotech's original tools, data access or full protocol. Recorded responses are
static evaluator-only test stimuli and never source evidence.

Both pure methods use `/statement` only. Lexical matching uses the complete
verified question text, Unicode NFKC/casefold word sets, intersection count and
stable identifier ordering. It ranks text overlap, not evidence strength.
Whole excerpts retain original pointers, text hashes and separate grounded and
scientific-record fingerprints. Nonselection is reported without an absence
claim. Query, selection, quotations and reviewer views are recomputed on replay.

## Exact token capacity

Default `StudySession` and ordinary `RecordedBackend` keep their byte-plus-32
reservation rules. The optional path requires an explicitly supplied concrete
`TrustedTokenCapacity` object and four independent anchors: quote receipt,
prompt, payload and tokenizer specification. Its descriptor includes trusted
implementation identity and omits the physical locator for relocation.

The token bundle authenticates current package code, exact UTF-8 prompt and
payload, pinned tokenizer/model/asset identities, preprocessing, raw trace and
count. Reservation equals the authenticated count plus 32 exactly. Prompt and
payload byte limits, output allocation, context and budget checks still apply.
Capacity establishes sizing; source authority is checked separately.

Token cells emit configuration2/receipt2/report1. Configuration2 seals the trusted
descriptor and verified binding; receipt2 seals their combined fingerprint.
Execution and replay both require a trusted caller object; serialized names and
backend IDs cannot choose behavior. Token replay also requires an explicit finite
absolute deadline. Legacy configuration1 retains its original semantics.

## Budget, history and failure behavior

One unchanged default budget covers the entire case: 16 calls, 32,000 input,
8,000 output, $0 and 300 seconds. Its clock starts before fresh source/proof and
tokenizer preparation and includes all six quotes, cells, pure work and sealing.
At most six pinned offline tokenizer processes run, each bounded by 30 seconds
and the remaining parent time. They count tokens and do not generate answers.
Actual model calls and observed model usage remain zero; scripted declared usage
and token reservations are separate accounting fields.

Only accepted same-run, same-arm predecessor receipts may supply source-ID
feedback. Prior prose and reference answers stay outside evidence and prompts.
Every actual resulting payload gets a fresh current-version quote. Hypothetical
full-ID sizing is not a maximum over arbitrary histories and old-package quotes
cannot authorize current execution.

Failed quotation retains request/payload before dispatch and does not fabricate
a completed configuration. Timeout, interruption, malformed content, write error
or late sealing retains failure/partial records. Recorded consumption checks the
earlier parent/caller deadline immediately before its one-use boundary. Recovery
does not retry. Deadline checks are cooperative, not hard filesystem/CPU preemption.

## Interfaces and verification

```python
from asof.study.authority_four_arm import smoke, verify

# Explicit approved existing tokenizer authority/roots; output must be new.
result = smoke(output, tokenizer_authority, tokenizer_roots)

# Read-only replay: no tokenizer, model assets, generation or network.
verified = verify(output, result["receipt_sha256"], deadline=absolute_deadline)
```

The corresponding module CLI exposes `smoke --output --tokenizer-authority
--tokenizer-roots` and `verify --path --sha256`. Execution requires the existing
approved local tokenizer assets. Replay uses the separately installed matching
package, retained bundle and externally retained receipt hash. No archived class
or repository-only runtime tool is imported.

The prior byte sizing failed at 47,753 input units. The separate accepted-version
feasibility experiment measured 14,315 input/6,144 output reservations for those
six exact prompts. Current 0.3.6 qualification retained fresh parents and all six
exact quotes, matching the original payloads. Its resource report and installed
and relocated replay pass. See the [acceptance](../planning/review-assets/recovery-step9-four-arm-20261026/acceptance.json).

The first E: attempt timed out after two tokenizer calls and two accepted cells;
their separate read-only verification passes. That whole case remains failed.
All 34 approved assets plus acquisition metadata were then copied byte-identically
to an ignored D: mirror, with no original writes or new downloads. One separately
declared second attempt finalized in **192.7 seconds**, with **29.36 seconds** for
subsequent read-only replay. Six new tokenizer calls plus two from the failed
attempt are retained separately. Actual model calls and provider spending are zero.

Full validation passes **1,646 tests, zero failures/errors/skips**, probes and
package/demo checks. All 312 source/resource pins and two hash-only protected
outcome checks remain unchanged. Seven installed legacy families and matching
frozen 0.3.1–0.3.5 verifiers pass. The bundle is 619,912 bytes; parent peak working
set is 36,966,400 bytes. Child peak memory was not independently instrumented.
The one-time 8.46 GiB mirror transfer took 20.53 seconds and is reported separately
from case execution. Source/spec preparation and all asset checks remain inside
the unchanged execution budget; later cases are not guaranteed to fit.

Independent human reviews remain pending. A subsequent
[five-record real retrieval qualification](../planning/review-assets/recovery-step9-real-retrieval-20261027/CLOSEOUT.md)
passes admission/selection mechanics but shows no policy contrast and retains
byte-bound coverage limits. The original check did not execute these arms; the
separate 0.3.7 recorded integration above now does so mechanically.
Fresh cases, real source/interpretation quality, native activation, H5 scientific
evaluation and overall R09 completion remain separate gates. Features stay empty
and clinical probabilities null.
