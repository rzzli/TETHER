# TETHER — Source and token preparation

TETHER (Target Evidence Tracking Harness for Evaluation and Reproducibility) is the current project name. The `tether-target-agents` 0.4.2 package in `packages/tether` supplies the `tether` CLI and import namespace over the frozen AsOf 0.3.11 engine. See [installation and compatibility](../README.md#installation-and-compatibility). Historical version/arm names, module commands, source paths and wire IDs below remain unchanged; the rename does not reactivate retired study or expert-review branches. Direct API aliases preserve legacy outputs; only the separate `tether._presentation` CLI layer wraps `demo`/`run` in the [TETHER run layout](../README.md#tether-cli-run-layout). Delegated source inspection, snapshot construction and evaluation keep their engine layouts.

Accepted AsOf 0.3.4 adds preparation capabilities separate from execution. The
existing byte-based `StudySession` capacity policy, recorded synthetic allowlist
and R07 native stop remain unchanged. These APIs do not start a model server,
generate an answer or establish scientific validity.

## Source admission and row reconstruction

`asof.study.source_preparation.prepare_source_request(authority_path,
authority_sha256, roots, output, deadline=...)` requires an independently retained
authority hash and a new output directory. Its supported profile is contemporary
T6, Open Targets 25.09 normalization 2.2 and the pinned HGNC 2026-10-10 reference.
The authority binds case, snapshot, effective catalog, identifier-validation data,
explicit selected observation IDs, question family, bounds and every source and
receipt file. Root IDs are mapped to explicit absolute local directories by the
caller. No path or saved request grants itself admission.

The wrapper checks prohibited paths, catalog roles, temporal eligibility and the
complete inventory before raw source reads. It holds Windows read-sharing locks
through admission and interpretation. The unchanged chronology/lineage kernel
admits the complete snapshot; a separate audit replays every selected evidence row
and target/disease/HGNC mapping row. Projected Arrow batches preserve physical
row-group and row coordinates and convert only the selected row to Python.
Optional ingestion requires exactly `pyarrow==21.0.0`; the default runtime still
declares no dependencies.

The audit reconstructs the entire supported Observation, including method metadata,
source kind, source scores, context, dates, missingness and lineage. Canonical
equality is required. Grounded-record fingerprints include their citation;
scientific-record hashes have a different domain. Nonempty numerical features
are rejected rather than cleared. Unknown source recipes, mismatched namespaces,
future/evaluator ancestors and unavailable inputs fail explicitly. Source scores
remain descriptive, and biological absence is never inferred from collection gaps.

`verify_source_preparation(path, receipt_sha256, approved_authority_sha256, roots,
deadline=...)` redoes source admission and original-row reconstruction under the
externally retained anchors. It requires the original approved data and matching
trusted package. It does not execute an archived compiler or tokenizer. A complete
snapshot admission count and selected-row audit count are distinct denominators.

## Offline token quotation

`asof.study.tokenization.prepare_tokenizer_spec(authority, roots, deadline=...)`
authenticates the fixed R05 acquisition/inventory and all 34 approved local assets:
the dedicated tokenizer utility, its runtime DLLs and three GGUF shards. Arbitrary
executables, new model bytes, extra DLLs, relative/device roots and path aliases are
rejected. The specification may relocate the same approved bytes; it cannot select
a different tokenizer.

`tokenize_prompt(prompt, spec, deadline, output, payload_sha256=...)` runs that
utility once with exact UTF-8 stdin, offline/no-escape/no-BOS settings and the pinned
special-token behavior. It starts no server and uses no generation backend.
Owned stdin/stdout/stderr pipes are bounded and drained concurrently; timeout,
interruption and failures retain partial streams and primary errors. There is no
automatic retry. All approved assets stay locked across hashing, the child and
post-hashing. The environment restricts loader paths and omits inherited model
overrides and credentials.

The retained token ID list and reported count must agree. A quote binds the exact
prompt, preprocessing, asset authority, implementation and parser. The finalized
HTTP/schema payload has a separate binding. Model usage remains zero: these are
local tokenizer counts, not observed inference usage. Uncached quotation and
externally anchored replay are supported; no automatic cache lookup or recompute
is introduced.

`verify_tokenization(path, receipt_sha256, expected_prompt_sha256,
expected_spec_sha256, expected_payload_sha256=...)` checks receipt inventory,
same-buffer hashes, current package/resource proofs, raw count agreement, journal
and child accounting, and final file consistency. It neither reads model assets
nor launches a process. A digest obtained solely from the cache itself is not an
external anchor.

## Payload and budget boundaries

`asof.study.preparation_payloads.prepare_payloads(request)` is pure rendering,
not admission. It preserves the whole request and returns six exact hypothetical
payloads: one AsOf interpretation and five role-inspired adapted Virtual Biotech
stages. The original Virtual Biotech tool/retrieval system is not reproduced.
Guide and schema share `min(3, original max_claims)`. Source-ID history is labeled
untrusted and contains no prior prose or answers.

Preparation allows 32,768 prompt bytes and 65,536 complete HTTP payload bytes while
recording model tokens separately. Each exact prompt reserves its verified count
plus 32, with 1,024 output tokens and a 16,384-token context ceiling. Aggregate
case defaults stay at 16 calls, 32,000 input, 8,000 output, $0 and 300 seconds.
The legacy retry field stays unchanged; this capability performs zero retries.

The longest history string is not a proven maximum BPE token count. A preparation
receipt certifies its exact six hypothetical payloads only. Any future actual
history needs a fresh quote before dispatch and a separately reviewed execution
policy. No real/native execution is activated by a passing preparation.

## Retained qualification and limits

The already exposed IL6R request was reconstructed exactly as
`14b735ef940bde56c04ea964cf145f3f7d1e343b2fe1e35de157cc8a5af2d61a`.
The final preparation verifies its selected whole source row and mappings, six
quotes and source-inclusive replay. Input reservation is 28,241; output is 6,144;
preparation took 98.5 seconds. See
[the retained report](../planning/review-assets/recovery-step9-token-aware-20261026/REAL-PREPARATION.json).
The initial harness failure is preserved separately; it rejected the first child
before launch because Windows serializes its subprocess audit arguments. The
revised harness changed no source, model, prompt policy or runtime code.

Deadlines are cooperative around unchanged kernel admission and synchronous
filesystem/native-library operations; hard CPU/blocked-I/O preemption is not
claimed. The tokenizer child has its own bounded process watchdog. Cleanup may
outlast a deadline, and a late operation cannot return a valid preparation.
Windows sharing locks protect ordinary approved-file reads and directory names;
they do not sandbox all directory additions or privileged/same-user attacks. OS
and system DLLs remain trust dependencies. Receipts establish anchored provenance,
not cryptographic CPU attestation or scientific truth.

This was one previously exposed development input. It is not a fresh evaluation,
genetics/MR feature validation, clinical prediction or independent adjudication.
Numerical features remain empty, probabilities remain null, human reviews are
pending, and R09 and the later study gates remain open. Full 0.3.4 acceptance
passes 1,582 tests with no failures/errors/skips and 297 unchanged source/resource
pins. [Acceptance evidence](../planning/review-assets/recovery-step9-token-aware-20261026/acceptance.json)
also records installed source-inclusive replay, seven legacy families and matching
frozen prior verifiers. The original full-run test-discovery failure is retained;
its correction only qualified two test-module imports.

The subsequent [0.3.6 recorded composition](AUTHORITY_FOUR_ARM_COMPARISON.md)
connects trusted token proofs to explicit optional execution/replay capacity.
Its accepted scope is one invented retrieved subset, not expansion of this real
source preparation. Default byte behavior remains unchanged. Old preparation
receipts retain their matching installed verifier; current-version admission
requires fresh proofs. No native or scientific activation follows automatically.

The [0.3.7 extension](AUTHORITY_FOUR_ARM_COMPARISON.md) also connects explicitly
authorized collected inputs to that recorded mechanism. A fresh parent rebuilds
all five existing IL6R literature candidates; the same whole selected record
enters six scripted stages and two pure methods. Source-inclusive replay and
run-bundle relocation pass with explicit original input roots. Archived physical
locations never grant access, and the original raw inputs are not independently
restored by that relocation. No model generation or scientific validity follows.
