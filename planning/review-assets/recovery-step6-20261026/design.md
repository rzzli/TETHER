# R06 minimal study infrastructure — design only

Prepared 2026-10-26 during the R04 frozen validation pass. **Proposed, not accepted or implemented.** No source/profile changes, inference, network requests, subprocess launches, or protected outcome reads were made for this design. The controlling scope is Step 6 of `planning/Project Recovery and Evaluation Plan 2026-10-26.md`; the sole first consumer is the new bounded capacity/interface diagnostic being prepared under R05.

## Scope and existing behavior to preserve

Reuse `asof.journal.RunJournal`, `asof.atomic.publish_bytes`, `asof.agents.Usage`, `asof.workflow.Budget/BudgetMeter`, and canonical encoding/hashing. Keep old `tools/science` launchers, receipts and failed runs unchanged. Do not copy their complete pipelines into the package or create a compatibility shim that imports them from the wheel.

The old question launcher contains useful protections to preserve: the process handle is stored immediately after `Popen`, before log context-manager exits; primary failures survive cleanup errors; execution is accounted from retained task journals; failed outputs are not repaired. Its repository-root AST walker, study-specific two-task constants, clinical/genetic preparation and source rendering are not generic lifecycle responsibilities.

Three new implementation modules plus the package initializer are sufficient initially:

- `asof.study.proofs`: installed package code inventory and explicit resource/input proofs.
- `asof.study.process`: one owned, non-daemonizing local server process with bounded startup/cleanup.
- `asof.study.session`: exclusive run reservation, once-only attempts, accounting, terminal records and sealed recorded-study inspection.

The R05 helper owns semantic requests, concrete interface rendering and response validation. It supplies exact prepared bytes and trusted functions to these helpers. None of the three helpers needs to understand IL6R, MR, clinical labels, scientific claims or native JSON grammar.

## Proposed proof API

```python
@dataclass(frozen=True)
class FileProof:
    logical_id: str
    sha256: str
    bytes: int

def capture_package_proof(*, resources: Mapping[str, str]) -> Mapping: ...
def verify_package_proof(proof: Mapping) -> None: ...
def capture_file(path: Path, *, logical_id: str) -> FileProof: ...
def verify_file(path: Path, proof: FileProof) -> None: ...
```

`resources` maps semantic names such as `diagnostic_template_v1` to explicit paths relative to the **installed trusted asof package**. Capture a sorted inventory of every `.py` file under that package, including initializers, plus the explicitly required resource bytes. Record package version, Python implementation/version, declared dependency versions, inventory policy version and entry-point identifiers. Logical identities use package-relative names; machine-specific physical locations belong in caller bindings, not in the stable identity.

This is deliberately a conservative static package inventory, not a claim to discover every possible runtime import. It avoids generalizing `question_interpretation_runtime.code_paths`, whose ROOT/`src`/`tools` resolution assumes a repository. Do not use manifest-provided import names to load code, execute archived Python, or dynamically import an archived verifier. The dependency-free package can use already-imported trusted package location and `importlib.metadata` for environment identity. Fail explicitly for unsupported zipped/non-filesystem installation rather than silently omitting code. External runtime binaries, weights and user configuration remain explicit caller proofs, not Python code to execute during verification.

The consuming study declares its complete required resource-name set in its versioned contract. Preparation fails on absent/duplicate names or unsafe resource paths; hashing an arbitrary caller subset is not proof of completeness. Resource bytes actually used for rendering must be the same authenticated bytes represented by the proof. Reject traversal, escaped symlinks/reparse points, duplicate logical identities and inconsistent size/hash. File checks should guard replacement during hashing, using the existing authenticated-file pattern rather than separate unchecked read/hash passes. Stage package resources/configuration as data in the run archive if relocation verification will need their original bytes; do not save only hashes and call that a restorable archive.

Hashing all package Python files is slightly broader than the runtime closure, but is small and avoids a new AST dependency resolver. It does not authorize loading other case packs or evaluator answers into the prompt. Request source manifests and evaluator separation remain explicit consumer controls.

## Proposed owned-process API

```python
@dataclass(frozen=True)
class ServerSpec:
    argv: tuple[str, ...]
    executable: FileProof
    required_inputs: tuple[FileProof, ...]
    host: str                    # exactly 127.0.0.1 for first adapter
    port: int
    startup_seconds: float
    terminate_seconds: float
    kill_seconds: float

class OwnedServer:
    def __init__(self, spec: ServerSpec, *, bindings: Mapping[str, Path],
                 output: Path, journal: RunJournal,
                 listener_owner, health_probe): ...
    def __enter__(self) -> "OwnedServer": ...
    def assert_ready(self) -> None: ...
    def __exit__(self, error_type, error, traceback) -> bool: ...
    @property
    def terminal_record(self) -> Mapping: ...
```

`listener_owner(pid, host, port)` and `health_probe(host, port, timeout)` are explicitly supplied **trusted implementations**, never names resolved from archived JSON. Their code proofs are part of the study configuration. The first real implementation may remain Windows-only; fake implementations make the helper testable on other platforms. A future POSIX implementation must positively establish ownership or refuse execution, not assume that a healthy port belongs to this process.

Required invariants:

1. Verify pinned executable/required inputs and frozen command before launch. Validate host, port and finite positive time limits. Reject existing listeners; record command bytes and create stdout/stderr with exclusive creation. Use argv without a shell, disabled proxy/redirect behavior in the health adapter, and hidden windows on Windows. Offline flags are configuration, not a network sandbox claim.
2. Retain the returned `Popen` object immediately, before journaling `server_started` or closing parent log handles. Any later failure cleans this same process. If startup fails inside `__enter__`, Python will not call `__exit__`: `__enter__` must explicitly run cleanup before propagating the primary exception.
3. A temporary bind check is only an initial availability check; it cannot reserve the port until another executable binds. Before health requests and before each generation, require the retained process to be alive and OS listener ownership to match its PID. After health success, recheck ownership/liveness before declaring ready. Do not contact a competing listener and later call that an owned health result.
4. Startup polling is bounded and must not relaunch the process. Health probes have bounded individual timeouts, do not generate responses and are recorded separately from model-call accounting. On timeout, unexpected exit or ownership mismatch, preserve logs and cleanup; no port takeover or automatic retry.
5. Cleanup operates only through the retained process object/handle: bounded terminate/wait, then bounded kill/wait if necessary. Never kill by process name, a newly queried port owner, or a historical bare PID. The first adapter supports a non-daemonizing single server; it does not claim arbitrary descendant-tree cleanup. Reject unsupported daemon/child-owner behavior rather than killing unrelated processes.
6. Preserve the original exception and traceback, including KeyboardInterrupt; attach cleanup/log/journal errors as secondary diagnostics. If no primary existed, a cleanup failure becomes the terminal failure. Failure to stop is explicit and cannot produce a successful sealed study. `server_stopped` describes the owned process; a later unrelated port listener is separate information, not justification to kill it or mark the owned process alive.
7. Use an absolute monotonic deadline for startup and cleanup. Record elapsed time and observed exit code; record unmeasured native peak memory as null with a reason. The study configuration must explicitly state whether source admission, startup and teardown are outside its inference budget, and also report end-to-end time. Do not silently reset a shared case deadline for every question.

Use small constructor-injected fake process/clock/probe implementations for tests, or a private factory seam. They are test/trusted-code injection points, never input-manifest execution hooks. No mandatory process-monitor dependency is needed.

## Proposed session and backend boundary

```python
@dataclass(frozen=True)
class GeneratedBytes:
    content: bytes
    usage: Usage | None

@dataclass(frozen=True)
class BackendCapabilities:
    interface_version: str
    max_prompt_bytes: int
    max_response_bytes: int
    context_tokens: int | None
    max_output_tokens: int
    tokenizer_identity: str | None

class StudySession:
    def __init__(self, output: Path, *, budget: Budget,
                 configuration: Mapping, input_proofs: Mapping): ...
    def __enter__(self) -> "StudySession": ...
    def call_once(self, *, attempt_id: str, request_sha256: str,
                  payload_sha256: str, quote: Usage,
                  generate) -> GeneratedBytes: ...
    def finish(self, report: Mapping, *, outputs: Mapping[str, bytes]) -> FileProof: ...
    def __exit__(self, error_type, error, traceback) -> bool: ...

def inspect_study(output: Path) -> Mapping: ...
def verify_study(output: Path, *, expected_receipt_sha256: str,
                 verifier) -> Mapping: ...
```

These signatures are a proposed small boundary, not approval to implement a general orchestration framework. `generate(timeout_seconds=...)` and `verifier(...)` are supplied trusted code; their identity/proofs are archived. The concrete R05 adapter exposes capabilities, preparation/quote/generation and a pure replay verifier. Its backend ID is metadata, not an `if backend_id` selection mechanism. Preserve versioned explicit adapters for legacy traces; do not route old receipts through new request semantics.

Session rules:

- Reserve a new directory via RunJournal before work. Archive exact effective configuration/input bindings and accept only zero provider-spend budgets. Keep existing budget defaults; `call_once` never retries regardless of `Budget.max_retries`. Serial execution permits only one unresolved call, avoiding concurrent reservations escaping BudgetMeter's account-at-completion totals.
- Complete payload/source/capability preflight precedes `call_once`. Validate quote and remaining shared budget. Record and fsync dispatch, request/payload fingerprints and conservative reservation **before** invoking the callback. If dispatch journaling fails, do not call. Each attempt ID is unique and cannot be reused, including after failures.
- Capture bounded raw response bytes separately from contract acceptance. Valid adapter usage remains measured even if returned content fails post-validation; missing/untrusted usage uses the full conservative reservation. Report over-quote actual usage and fail, rather than clipping it to the quote. Invalid envelope, timeout, transport error and interruption remain terminal for that planned cell. A consumer may continue separately declared cells under its frozen policy, but cannot retry the failed one.
- Account exactly once. If an accounting write fails, do not attempt another generation or invent a durable measured event. Inspection derives unresolved conservative usage from the existing dispatch reservation. Any in-memory totals are not substitutes for durable evidence. There is no resume/redispatch method.
- Preserve primary failures when response capture, backend-execution archive, accounting, failure snapshots or journal close also fail. Retain best-effort independent failure diagnostics; never emit a success receipt for incomplete bookkeeping. If journal storage itself is broken, explicitly acknowledge what could not be retained.
- Finalization rechecks input/code/resource proofs and invokes the explicit pure consumer verifier. Write immutable outputs/report, then terminal journal event, close the journal, and finally publish the receipt over stable bytes. Avoid receipt/report/journal hash cycles. A close/seal failure has an independent failure marker and cannot be described as successful merely because a report exists. Never amend already sealed outputs.
- Inspection is read-only: validate hash chain, unique attempts/accounts, usage basis, terminal state and outstanding reservations; report `never automatically repeat unresolved calls`. It makes no source-entailment or scientific-quality claim. Verification also checks receipt/output hashes, proof closure, request/payload equality, accounting and the explicit consumer contract.

R05 may use a single session per planned cell and a simple parent manifest of cell results, which avoids copying the old multi-question controller. A single-case shared budget still needs explicit totals across its cells if the frozen protocol defines a shared allowance; per-cell budget resets must not silently raise that cap.

## Meaningful tests and acceptance

| Component | Required evidence |
|---|---|
| Installed proofs | Run from a clean wheel outside the repository; capture/verify complete package inventory and required templates. Changed/missing code, altered resource, omitted required resource, unsafe logical path, replacement during read and wrong external anchor fail. Reading a file containing import-time side effects must never execute it. |
| Ownership | Pre-existing/competing listener: zero generation, no foreign termination. Popen success followed by journal/log-close failure: retained child still cleaned. Startup death/timeout: one launch only. Health succeeds but PID differs: not ready. Before-call owner changes: no dispatch. |
| Cleanup | Normal exit; terminate timeout followed by kill; kill failure; log close failure; KeyboardInterrupt during startup/generation. Preserve primary error and secondary diagnostics, retain logs, and prevent a success seal when cleanup fails. Tests use fakes, not a native model. |
| Accounting | Dispatch-write failure means zero callback invocations. Timeout/malformed/untrusted usage reserves conservative usage once. Valid measured usage plus invalid scientific envelope stays measured. Over-quote fails with full actual usage. Duplicate attempt/account and parallel outstanding calls reject. A failed accounting write leaves a readable unresolved reservation and no repeat. |
| Sealing | Two creators cannot reuse an output; output/report/journal/receipt tampering rejects. Close/seal/write failure leaves failure inspection, no false completed status. Archived configuration/resources are the bytes actually used. Source-answer isolation is asserted by the diagnostic-specific verifier. |
| First consumer | One recorded synthetic success and one recorded failure executed and inspected from the installed wheel, with tools/planning imports blocked. No model or network call, features empty and probability null. Capabilities and explicit verifier dispatch work with two fake backend IDs without adding ID branches. |
| Compatibility | Existing seven representative old runs still replay through supported archive verification. Version/CHANGELOG/package metadata agree; scoped lint/format and coverage report covers new modules. No new default runtime dependency or raw dataset collection. |

Do not promote test doubles to proof of real native listener ownership, hardware fit, inference quality or independent human review. Those remain separately qualified stages.

## Implementation order and remaining decisions

After R04 accepts: agree the R05 prepared-byte/capability interface, implement proofs and session with recorded fixtures, add the minimal owned process helper with fake tests, and migrate only the new diagnostic smoke path. Native transport extraction is needed only when that scheduled consumer uses it; AACT sessions remain deferred. The precise resource names and concrete diagnostic response schema belong to the R05 consumer and should be finalized together, not guessed by the generic helper.

The proposed all-package static inventory is a deliberate simplification to confirm before implementation. If a narrow import closure is required instead, it needs an explicit allowed-package/module map and complete resource declaration; silently retaining the old repository ROOT walker is not an acceptable wheel implementation. No further owner approval is needed for the already authorized engineering; an unavailable stronger model or human scientific submission is an independent named gate.
