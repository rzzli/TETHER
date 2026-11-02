# TETHER — Packaged study runtime

TETHER (Target Evidence Tracking Harness for Evaluation and Reproducibility) is the current project name. The `tether-target-agents` 0.4.1 package in `packages/tether` supplies the `tether` CLI and import namespace over the frozen AsOf 0.3.11 engine. See [installation and compatibility](../README.md#installation-and-compatibility). Historical version/arm names, module commands, source paths and wire IDs below remain unchanged; the rename does not reactivate retired study or expert-review branches. Direct API aliases preserve legacy outputs; only the separate `tether._presentation` CLI layer wraps `demo`/`run` in the [TETHER run layout](../README.md#tether-cli-run-layout). Delegated source inspection, snapshot construction and evaluation keep their engine layouts.

AsOf 0.3.0 introduced small reusable helpers and a **recorded synthetic smoke
study**, which makes no native request. Version 0.3.1 adds the separately frozen
R07 native diagnostic. Its once-only execution is terminal: six complete responses,
zero accepted output contracts, no retries, stopped owned server. The current
native experiment is stopped; see the [negative disposition](../planning/review-assets/recovery-step7-20261026/DISPOSITION.md).
Neither consumer establishes scientific validity. Existing clinical and
interpretation launchers remain unchanged.

## Scope

`asof.study.proofs` hashes the complete installed AsOf Python inventory and the
consumer's explicit required resources. It authenticates original file bytes,
rejects unsafe logical identities and links/reparse points, and rechecks earlier
members after later files are hashed. Verification uses the currently trusted
package; it never imports executable symbols from archived JSON.

`asof.study.process` manages one non-daemonizing process it starts itself. The
caller supplies pinned executable/input bindings and trusted listener-ownership
and health callbacks. Ownership must be positive before health and generation.
Cleanup uses the retained process handle, preserves a primary failure and records
bounded terminate/kill results. Fake-process tests do not establish operating-system
ownership or actual GPU fit. Arbitrary process trees and daemonization are unsupported.

`asof.study.session` reserves one planned cell, checks capabilities and the frozen
package before dispatch, journals a conservative reservation, then accounts usage
once. Known measured usage survives invalid content. Accounting-write failure
leaves an unresolved conservative reservation. There is no retry/resume operation.
Finalization reconciles accepted state with archived files and the durable journal,
then closes the journal before publishing the receipt. Inspection is read-only.

`asof.study.diagnostic` supplies source-preserving current/simplified codecs and
strict post-validation. Complete payloads reproduce the R05 v2 preparation bytes.
The simplified response has its own contract; it never fabricates contextual
propositions to resemble the current interface. Exact quotes, source fidelity,
scientific entailment and clinical usefulness are distinct guarantees.

Backend IDs are metadata. Explicit capability and trusted verifier interfaces
select behavior. The included recorded adapter binds its evaluator fixture to
both request and complete payload fingerprints. Its reported usage is fixture
data, not observed model consumption. Source-only templates/cases are separate
from evaluator fixtures, prior outputs and completed expert answers.

## Offline installed smoke

```powershell
python -I -m asof.study smoke --output <new-output-directory>
```

The command retains a valid recorded cell and an intentionally malformed recorded
cell, verifies the former and inspects the latter. The failed cell has no success
receipt. The command offers no live-model mode. Default runtime dependencies are
empty; the ingestion extra remains optional and pinned separately.

Programmatic consumers explicitly supply resources/required names, configuration,
budget, prepared request/payload, backend and trusted verifier. A cell can dispatch
only once. A parent comparison must freeze and enforce its aggregate case budget;
creating multiple cells cannot silently reset that budget. Future native consumers
must bind all model/runtime command arguments to proofs and establish listener
ownership on the actual operating system before use.

## Verification and limits

`verify_study` requires an external receipt SHA-256 and an explicitly supplied
trusted verifier. It checks bytes, complete package/resource proofs, request and
payload reconstruction, capability/budget limits, event order, run identity,
measured/conservative accounting and consumer response rules. It does not execute
an archived adapter or automatically trust an archived callback name.

This new study format currently requires matching trusted package/environment
proofs. Independent relocation for this new receipt family is not claimed by the
older archive support matrix. The seven representative legacy families retain
their separate `asof.archive` compatibility path; v1 semantics remain unavailable.

## R07 native consumer and retained result

`asof.study.native` binds one-use loopback transport to the owned process, exact
endpoint, prepared payload and model/runtime proofs. Positive operating-system
listener ownership precedes health and generation. Original native bytes are
retained, including partial capture on failures; prompt/model/settings, positive
completion cause and usage are checked separately from answer contracts. A
bounded watchdog and socket deadline constrain calls. Recovery inspects records;
it never automatically repeats a potentially completed call.

`asof.study.native_diagnostic` freezes six cells and complete source/compiler,
package, model/runtime and payload proofs. It enforces aggregate budgets,
preserves each rejection and terminally seals the original response/accounting
records. Generic failures stop execution; only declared captured response failures
permit proceeding to a different planned cell. The implementation does not support
resuming a terminal experiment or treating each cell as a new aggregate budget.

The real run is `runs/r07-native-diagnostic-20261026T165505Z`. Its external seal
SHA256 is `863bf2a9cfb8d4fd01a5223b993d87fbe2ac06992e7206d3d32ef4c712cf2d41`.
Read-only verification is available through
`python -m asof.study.native_diagnostic verify --path <run> --sha256 <external-seal-hash> --approved-root <project-root> --approved-root <original-data-root>`.
Keep the externally retained anchor; a hash read only from the run itself is not
an independent anchor. Never add post-run reports inside the sealed directory;
the member inventory is part of verification. Post-run reports live under
`planning/review-assets/recovery-step7-20261026/`.

The run used the acquired 14B model and one 16,384-token slot. It reported 14,420
input / 2,108 output tokens and took 59.391 seconds at $0 provider spending. Six
responses had complete verified transport and valid JSON; none met the frozen
consumer contract. AI development triage identifies interface confounds and real
source omissions/attribution concerns. It is not independent human assessment or
a causal test of model capacity. A stronger control was unavailable.

The installed 0.3.1 validation passes 1,485 full tests with no skips, required
probes/package checks and seven legacy replays. Fifty native/diagnostic regressions
are included. Legacy compatibility preserves unavailable v1 semantics; it does
not claim independent relocation for every new native study format.

Human genetics/MR expertise and source-only references remain pending. The
mechanism orientation exercise cannot substitute. R08 source/exposure preparation
can proceed without model generation; fresh evaluation requires references before
generation. No further native experiment or twenty-case expansion is activated.

## Deterministic engineering in 0.3.2

The [synthetic baseline interface](DETERMINISTIC_BASELINES.md) adds pure extraction
and lexical selection, immutable exact quotes, explicit nonselection and
source-inclusive recomputation. It uses no fake model session or token accounting.
The installed four-result bundle and its restored copy verify; all seven legacy
families pass. Accepted 0.3.2 validation includes 1,519 tests/no skips and package
checks. The explicitly reviewed frozen0.3.1 installation still verifies the R07
experiment despite the newer live package. These matching-version checks do not
claim general new-native-format relocation.

## Recorded comparison engineering in 0.3.3

The [fixed-evidence comparison](FIXED_EVIDENCE_COMPARISON.md) passes its separate
acceptance gate: 1,536 full tests, no failures/errors/skips, required probes and
package checks, seven installed legacy replays, and a restored recorded bundle.
The four arms use two invented fixtures, twelve recorded cells and four pure
baseline results. This verifies execution mechanics, not model or scientific
performance. It preserves
full fixed source parity across four arms and the unchanged aggregate case budget.
Only bounded source-ID proposals from proven earlier stages may appear as
untrusted feedback; prior prose, gold and human answers remain outside prompts.
The matching frozen 0.3.1 installation still verifies R07, and frozen 0.3.2 still
verifies its baseline bundle. Accepted reports and prior code remain preserved.

R09 remains open. Offline measurements of the pinned tokenizer exactly matched
all six archived R07 input counts. The full exposed real six-stage preparation
measures 28,241 tokens including margins, below 32,000; the earlier byte proxy
reserved 85,173 units. These measurements do not change the current runtime byte
policy or real-source allowlist. A separately reviewed token-aware preparation
contract now establishes asset stability, raw-row source binding and replay for
that already exposed real development input. No native or real-case
generation follows from these engineering results; human scientific review is
still pending.

## Source and token preparation in 0.3.4

The [preparation interface](SOURCE_AND_TOKEN_PREPARATION.md) passed 1,582 full
tests with no failures/errors/skips, required probes/package checks, installed
replay and seven guarded legacy families. It reconstructed one whole original
Open Targets record and three identifier mapping rows and verified six exact
hypothetical token quotes. All 297 source/resource pins remained unchanged.
The earlier full-run test import error is retained; its correction changed two
test imports and no runtime behavior. Prior matching 0.3.1/0.3.2/0.3.3 verifiers
still pass after the change. R09's retrieval-to-interpretation bridge and general
execution integration remain unfinished.

## Bounded retrieval integration in 0.3.5

The [retrieval bridge](BOUNDED_RETRIEVAL.md) passes 1,616 full tests and 34 focused
retrieval tests, including seven independent peer tests. It binds whole qualified
candidates to two deterministic policies and original-record interpretation input.
Two scripted cells share one budget; four-arm access manifests remain preparation
only. The installed bundle and restored copy verify, seven legacy families pass,
and frozen 0.3.1–0.3.4 verifiers still pass. All 305 source/resource pins stay
unchanged during validation. The actual-format single-record check preserves
parent availability/missingness and makes no new biological claim. A separately
reviewed single-policy four-arm execution contract is the next engineering gate.

## Authority-bound recorded composition in 0.3.6

The [four-arm composition](AUTHORITY_FOUR_ARM_COMPARISON.md) is accepted with
1,646 full tests, 312 unchanged pins, installed/restored replay, seven legacy
families and matching frozen 0.3.1–0.3.5 verifiers. One invented case/policy uses
six recorded cells and two pure arms under the unchanged 300-second budget.
Exact CLI reservations total 14,315 input/6,144 output; actual model usage is zero.

Default session/recorded byte behavior is unchanged. Optional token mode requires
an explicit concrete trusted capacity object, exact current quote and matching
v2 configuration/receipt. Replay additionally requires a finite explicit deadline;
no serialized name selects a policy or archived class. History is verified accepted
source IDs only. A schema downgrade cannot bypass token authority.

The initial E: qualification timed out after two cells and remains failed. An
identical local asset mirror enabled one separately declared qualification in
192.7 seconds, including sealing. Neither the failed attempt nor its two tokenizer
calls is erased. Scientific/native qualification and overall R09 remain open.

## Collected-source recorded integration in 0.3.7

The [current four-arm interface](AUTHORITY_FOUR_ARM_COMPARISON.md) accepts an
explicit immutable `CollectedSourceInput`. Source roots are caller capabilities,
not archived instructions. Fresh source parents, eligible ancestors, whole-record
retrieval, six current token quotes and the two pure results share one unchanged
budget. Source leases remain active through source-inclusive verification and
are released before receipt publication. Replay checks complete original source
inputs; run relocation requires those input roots to be supplied explicitly.

The real-input recorded qualification passes in 157.8 seconds with 22,067 input/
6,144 output reservations, installed replay and guarded run relocation. All 314
pins are unchanged across 1,660 full tests with no failures/errors/skips. Seven
legacy families and matching 0.3.1–0.3.6 verifiers pass. Default installation remains
dependency-free. This supersedes the prior recorded-integration next actions;
model-backed interface qualification and independent scientific review remain
unfinished. No generation, new source acquisition or provider spending occurred.

## Original-path interpretation interface in 0.3.8

The [pure interface](INTERPRETATION_INTERFACE.md) binds quote IDs to original
source paths without relocating passages. It reuses stage/history checks and
strict response semantics, aligning schema states and literal quote/text pairs.
Exact quotations remain separate from authored assertions. Original R07 behavior
and failure records are unchanged; no native adapter or server is activated.

Acceptance passes 1,681 full tests, 316 unchanged pins, 105 external schema cases,
twelve installed stage preparations, seven legacy families and seven matching
preserved versions. The initial Unicode whitespace mismatch and sandbox temp-path
failure remain recorded. Source admission, accepted-history proof, exact token
capacity and native grammar compatibility are separate from pure preparation.
The [next integration contract](../planning/review-assets/recovery-step9-native-integration-20261027/CONTRACT.md)
requires the model-backed adapter to reuse the existing controller and transport.

## Native adapter/controller integration in 0.3.9

The [native mode](NATIVE_INTERPRETATION.md) now reuses the existing controller and
one-use transport, explicit source/model capabilities, original-path interface,
token quotes and accepted history. Owned startup, calls, baselines, shutdown and
sealing share the unchanged case budget. Failed accounting preserves the primary
error; complete retained bodies can recover usage after transport-close failure
without rewriting conservative reservations. Simulation has distinct counters.

Engineering acceptance passes 1,724 full tests, 324 unchanged pins, seven installed
legacy families and all eight prior matching study versions. The existing exposed
real case passes simulated transport in 200.0 seconds; installed source/model
replay and guarded run relocation pass. Six offline tokenizer children run, with
zero actual model/server calls or provider cost. Native grammar conformance,
actual resource feasibility and independent human science remain open.

## Relative-duration correction in 0.3.10

The native verifier now requires complete typed budgets and finite relative
transport duration strictly below the allocated cap. The controller reconciles
that duration with its validated child report using an absolute 1 µs tolerance;
there is no tolerance extending budget expiry. This corrects an independently
reproduced metadata gap without claiming original execution overrun.

Acceptance passes 1,737 full tests/324 unchanged pins, nine older matching
verifiers, seven installed legacy families and eight installed duration cases.
The fresh same-input simulation and source/model-inclusive installed/relocated
replay pass, with all six duration comparisons valid. Its 295.922-second execution
leaves only 4.078 seconds without actual inference. Keep that operational
constraint explicit; source correctness and a successful simulation do not prove
real full-case timing. See the [closeout and resource note](../planning/review-assets/recovery-step9-native-duration-20261028/CLOSEOUT.md).
