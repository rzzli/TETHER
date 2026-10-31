"""Source/pure orchestration only. No filesystem, SDK, CLI or live adapter.

Factories and checker ports are trusted, source-bound code, invoked under the
owner clock. Their correctness is a separate review boundary. Test ports do not
qualify real archive/core logic. Private tokens prevent accidental/serialized
gate reuse; they are not a hostile-Python security boundary.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from types import MappingProxyType

TOTAL = 300
RESERVE = 5
MAX_FILES = 256
MAX_EVENTS = 2048
FIXED_EVENTS = 64
FAILURE_EVENTS = 128
EVENTS_PER_FILE = 6
SMALL_CAP = 128 * 1024**2
PACK_CAP = 20 * 1024**2
CAPTURE_CAP = 64 * 1024**2
REPORT_CAP = 2 * 1024**2
CHUNK = 65536
CHECKS = ("archive", "journal", "resources", "core")
GATES = ("admission", "hashes", *CHECKS, "consistency", "leases_closed", "sealed", "final_clock")
ROLES = {"software", "CPU", "model", "pack", "owner_metadata", "artifact"}
_new_hasher = hashlib.sha256


class VerificationError(RuntimeError):
    pass


class Deadline(VerificationError):
    pass


def require(value, message):
    if not value:
        raise VerificationError(message)


def path_key(value):
    require(type(value) is str and 4 <= len(value) <= 32767, "DOS path required")
    try:
        require(len(value.encode("utf-16-le", "strict")) // 2 <= 32767, "UTF16 path cap")
    except UnicodeError as error:
        raise VerificationError("Scalar path required") from error
    require(value[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" and value[1] == ":" and value[2] in "\\/", "Absolute DOS path required")
    require(value[0].lower() != "e", "Protected drive is not admitted")
    converted = value.replace("/", "\\")
    devices = {"con", "prn", "aux", "nul", *[f"com{i}" for i in range(1, 10)], *[f"lpt{i}" for i in range(1, 10)]}
    for part in converted[3:].split("\\"):
        require(part not in ("", ".", "..") and not part.endswith((".", " ")), "Noncanonical path component")
        require(not any(ord(c) < 32 or ord(c) == 127 or c in '<>:"|?*~' for c in part), "Forbidden path spelling")
        require(part.split(".", 1)[0].lower() not in devices, "Device path forbidden")
    return converted.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))


@dataclass(frozen=True)
class FileSpec:
    path: str
    role: str
    size: int
    sha256: str
    capture: bool = False


@dataclass(frozen=True)
class Request:
    output_key: str
    files: tuple


@dataclass(frozen=True)
class Authority:
    """Expected claims from a trusted factory, not a serialized ready flag.

    The future source-bound factory must preserve the exact approved root graph,
    roster and checker identities. The engine still freshly hashes every file.
    """
    files: tuple
    checker_ids: tuple


@dataclass(frozen=True)
class OpenReturn:
    handle: object
    size: int
    original_path: str
    regular: bool = True
    reparse: bool = False


@dataclass(frozen=True)
class ReadReturn:
    ok: bool
    count: object
    data: bytes


@dataclass(frozen=True)
class CheckObservation:
    context: object
    stage: str
    verdict: str
    evidence_paths: tuple
    detail: str = ""


@dataclass(frozen=True)
class CheckerPorts:
    ids: tuple
    handlers: tuple


@dataclass(frozen=True, slots=True)
class CapturedContext:
    _owner: object
    specs: tuple
    _blobs: object
    digests: object
    _check: object

    def __post_init__(self):
        object.__setattr__(self, "_blobs", MappingProxyType(dict(self._blobs)))
        object.__setattr__(self, "digests", MappingProxyType(dict(self.digests)))

    def bytes_for(self, path):
        self._check()
        return self._blobs[path]

    def check_work(self):
        self._check()

    def __reduce_ex__(self, protocol):
        raise TypeError("Owner context is not serializable authority")


@dataclass(frozen=True)
class _Proof:
    owner: object
    gate: str

    def __reduce_ex__(self, protocol):
        raise TypeError("Owner proof is not serializable authority")


@dataclass
class _Lease:
    spec: FileSpec
    handle: object
    ordinal: int
    close_attempted: bool = False
    close_returned: bool = False
    closed: bool = False
    close_state: str = "not_attempted"


class _Owner:
    def __init__(self, clock, started):
        self.clock, self.started = clock, started
        self.last_time = started
        self.work_end, self.end = started + TOTAL - RESERVE, started + TOTAL
        self.token = object()
        self.sink = self.port = None
        self.leases = []
        self.files = []
        self.operations = []
        self.events = []
        self.proofs = []
        self.stages = []
        self.primary = None
        self.errors = []
        self.timed_out = False
        self.clock_failed = False
        self.unknown = False
        self.publication_failed = False
        self.negative = False
        self.context = None
        self.output_state = "not_attempted"
        self.output_owned = False
        self.cleanup_failed = False
        self.publication = dict(state="not_attempted", return_observed=False, acknowledgment=False)

    def now(self):
        try:
            value = self.clock()
            require(type(value) in (int, float) and not isinstance(value, bool) and math.isfinite(value), "Finite owner clock required")
            require(value >= self.last_time, "Owner clock moved backwards")
        except BaseException:
            self.clock_failed = True
            raise
        self.last_time = value
        return value

    def report_time(self):
        """Failure bookkeeping only: a broken clock cannot replace a primary."""
        try:
            return self.now()
        except BaseException as error:
            self.latch(error, "timing_observation")
            return None

    def check(self, final=False):
        value = self.now()
        if value >= (self.end if final else self.work_end):
            self.timed_out = True
            raise Deadline("Original verifier deadline expired")
        return value

    def latch(self, error, phase):
        record = dict(phase=phase, error_class=type(error).__name__, error=str(error)[:512])
        if self.primary is None:
            self.primary = record
        self.errors.append(record)
        if isinstance(error, Deadline):
            self.timed_out = True

    def emit(self, event, **details):
        require(len(self.events) < MAX_EVENTS, "Verifier event cap")
        row = dict(sequence=len(self.events), event=event, elapsed_seconds=self.now() - self.started, details=details)
        self.events.append(row)  # Reservation survives a failed append acknowledgment.
        try:
            self.sink.append(row)
        except BaseException:
            self.publication_failed = True
            raise

    def cleanup_emit(self, event, **details):
        try:
            self.emit(event, **details)
        except BaseException as error:
            self.latch(error, "cleanup_journal")

    def stage(self, name, action):
        self.check()
        row = dict(stage=name, started=self.now(), state="reserved")
        self.stages.append(row)
        self.emit("stage_reserved", stage=name)
        self.check()
        try:
            value = action()
        except BaseException as error:
            row["state"] = "failed_or_unknown"
            self.latch(error, "stage_" + name)
            row["ended"] = self.report_time()
            raise
        row["state"] = "return_observed"
        row["ended"] = self.now()
        self.check()
        self.emit("stage_returned", stage=name)
        return value

    def proof(self, gate):
        self.check(final=gate in ("leases_closed", "sealed", "final_clock"))
        require(len(self.proofs) < len(GATES) and GATES[len(self.proofs)] == gate, "Required gate order or omission")
        self.proofs.append(_Proof(self.token, gate))

    def admit(self, request, authority, checkers):
        require(type(request) is Request and type(authority) is Authority and type(checkers) is CheckerPorts, "Typed trusted factory claims required")
        require(type(request.output_key) is str and 0 < len(request.output_key) <= 256 and "\0" not in request.output_key, "Output key cap")
        require(type(request.files) is tuple and request.files == authority.files, "Exact original role roster required")
        require(0 < len(request.files) <= MAX_FILES, "Original file cap")
        require(EVENTS_PER_FILE * len(request.files) + FIXED_EVENTS + FAILURE_EVENTS <= MAX_EVENTS, "Joint journal/file budget")
        require(type(checkers.ids) is tuple and checkers.ids == authority.checker_ids and tuple(k for k, _ in checkers.ids) == CHECKS, "Fixed source-bound checker identity order")
        require(type(checkers.handlers) is tuple and len(checkers.handlers) == len(CHECKS) and all(callable(h) for h in checkers.handlers), "All trusted checker ports required")
        keys = set()
        capture = models = 0
        for spec in request.files:
            require(type(spec) is FileSpec and spec.role in ROLES and type(spec.size) is int and 0 <= spec.size < 2**63, "Strict original descriptor")
            require(type(spec.sha256) is str and len(spec.sha256) == 64 and all(c in "0123456789abcdef" for c in spec.sha256), "Descriptor hash")
            require(type(spec.capture) is bool, "Capture bool required")
            key = path_key(spec.path)
            require(key not in keys, "Original role alias/collision")
            keys.add(key)
            if spec.role == "model":
                models += 1
                require(not spec.capture and spec.size > 0 and spec.path.lower().endswith(".gguf"), "Exact model role is stream/hash only")
            else:
                require(spec.size <= (PACK_CAP if spec.role == "pack" else SMALL_CAP), "Role-specific size cap")
                require(not spec.path.lower().endswith(".gguf"), "No model suffix in software role")
            if spec.role == "CPU":
                require(not spec.capture, "CPU body is hash only")
            if spec.capture:
                capture += spec.size
        require(models <= 3 and capture <= CAPTURE_CAP, "Model count/capture aggregate cap")
        self.proof("admission")

    def hash_files(self, request):
        blobs, digests = {}, {}
        for spec in request.files:
            self.check()
            rec = dict(path=spec.path, role=spec.role, open_state="reserved", read_attempts=0, read_returns=0, pending_read=False,
                       known_returned_bytes=0, hash_updated_bytes=0, hash_complete=False)
            self.files.append(rec)
            self.emit("file_open_reserved", path=spec.path)
            self.check()
            rec["open_state"] = "entered_return_unknown"
            opened = self.port.open(spec, self.work_end)
            # Every returned handle is registered BEFORE validation/clock/log.
            handle = opened.handle if type(opened) is OpenReturn else opened
            lease = _Lease(spec, handle, len(self.leases))
            self.leases.append(lease)
            rec["open_state"] = "return_observed_owned"
            self.check()
            self.emit("file_open_returned", path=spec.path, lease=lease.ordinal)
            require(type(opened) is OpenReturn and handle is not None and opened.size == spec.size
                    and type(opened.size) is int and opened.original_path == spec.path and opened.regular is True and opened.reparse is False, "Original lease identity differs")
            self.emit("file_hash_reserved", path=spec.path)
            self.check()
            digest = _new_hasher()
            captured = bytearray() if spec.capture else None
            while rec["known_returned_bytes"] < spec.size:
                self.check()
                count = min(CHUNK, spec.size - rec["known_returned_bytes"])
                rec["read_attempts"] += 1
                rec["pending_read"] = True
                result = self.port.read(handle, count, self.work_end)
                rec["read_returns"] += 1
                rec["pending_read"] = False
                rec["last_raw_count"] = result.count if type(result) is ReadReturn else None
                defined = type(result) is ReadReturn and result.ok is True and type(result.count) is int and 0 <= result.count <= count and type(result.data) is bytes and len(result.data) == result.count
                rec["last_count_defined"] = defined
                if defined:
                    rec["known_returned_bytes"] += result.count
                else:
                    self.unknown = True
                # A late count survives, but hashing/capture after expiry does not.
                self.check()
                require(defined and result.count > 0, "Failed/undefined/incomplete original read")
                digest.update(result.data)
                rec["hash_updated_bytes"] += result.count
                if captured is not None:
                    captured.extend(result.data)
                self.check()
            checksum = digest.hexdigest()
            self.check()
            require(checksum == spec.sha256, "Fresh original digest differs")
            rec.update(hash_complete=True, sha256=checksum)
            digests[spec.path] = checksum
            if captured is not None:
                blobs[spec.path] = bytes(captured)
            self.emit("file_hash_returned", path=spec.path, bytes=rec["known_returned_bytes"])
        self.context = CapturedContext(self.token, request.files, blobs, digests, self.check)
        self.proof("hashes")

    def check_stage(self, stage, handler):
        row = dict(stage=stage, state="entered_return_unknown", return_observed=False)
        self.operations.append(row)
        try:
            observed = handler(self.context)
        except BaseException:
            self.unknown = True
            raise
        # A late return remains an observed return, never an accepted gate.
        row.update(state="return_observed", return_observed=True,
                   typed_observation=type(observed) is CheckObservation)
        if type(observed) is CheckObservation:
            row["reported_verdict"] = observed.verdict[:64] if type(observed.verdict) is str else "invalid_type"
        self.check()
        require(type(observed) is CheckObservation and observed.context is self.context and observed.stage == stage, "Owner-local typed checker observation required")
        require(type(observed.detail) is str and len(observed.detail) <= 4096, "Bounded checker detail required")
        require(type(observed.evidence_paths) is tuple and 0 < len(observed.evidence_paths) <= MAX_FILES and len(set(observed.evidence_paths)) == len(observed.evidence_paths), "Captured evidence references required")
        require(all(p in self.context._blobs for p in observed.evidence_paths), "Checker used uncaptured/foreign bytes")
        require(observed.verdict in ("consistent", "negative"), "Checker evidence inconsistent/unknown")
        require(observed.verdict != "negative" or stage == "core", "Negative classification belongs to source core observer")
        self.check()
        self.negative = self.negative or observed.verdict == "negative"
        self.proof(stage)

    def close_all(self):
        for lease in reversed(self.leases):
            if lease.close_attempted:
                continue
            try:
                self.check(final=True)
            except BaseException as error:
                self.latch(error, "close_not_dispatched_deadline")
                lease.close_state = "not_dispatched_deadline"
                continue
            lease.close_attempted = True
            lease.close_state = "reserved_once"
            self.cleanup_emit("file_close_reserved", lease=lease.ordinal)
            try:
                self.check(final=True)
                lease.close_state = "entered_return_unknown"
                returned = self.port.close(lease.handle, self.end)
                lease.close_returned = True
                lease.closed = returned is True
                lease.close_state = "returned_success" if lease.closed else "returned_failure"
                self.check(final=True)
                require(lease.closed, "Original close failed")
            except BaseException as error:
                self.unknown = self.unknown or not lease.close_returned
                self.cleanup_failed = True
                self.latch(error, "original_close")
            self.cleanup_emit("file_close_returned_or_unknown", lease=lease.ordinal, state=lease.close_state)

    def result(self, status):
        return dict(scope="orchestration_only_no_real_profile_qualification", status=status, real_profile_qualified=False,
                    observed_source_outcome="negative" if self.negative else "positive_or_not_decided",
                    elapsed_seconds=self.last_time - self.started, original_deadline=self.end, work_deadline=self.work_end,
                    primary_error=self.primary, errors=list(self.errors), stages=list(self.stages), files=list(self.files),
                    checker_operations=list(self.operations), output_reservation=self.output_state,
                    terminal_publication=dict(self.publication), cleanup_failed=self.cleanup_failed,
                    leases=[dict(path=l.spec.path, ordinal=l.ordinal, close_attempted=l.close_attempted, close_returned=l.close_returned, closed=l.closed, close_state=l.close_state) for l in self.leases],
                    completed_gates=[p.gate for p in self.proofs], event_attempts=len(self.events),
                    verification_complete=status.startswith("COMPLETE_"))

    def finish(self):
        # Failed/unknown reservation grants no right to write into that output.
        if not self.output_owned:
            return self.result("INCOMPLETE_OUTPUT_RESERVATION")
        finalization = dict(stage="finalize", started=self.report_time(), state="reserved")
        self.stages.append(finalization)
        self.cleanup_emit("finalization_reserved")
        self.close_all()
        normal = self.primary is None and [p.gate for p in self.proofs] == list(GATES[:7])
        try:
            if normal:
                require(all(l.closed and l.close_returned for l in self.leases), "Known lease closure required")
                self.proof("leases_closed")
            self.check(final=True)
            self.publication.update(state="reserved")
            self.emit("terminal_seal_reserved")
            self.check(final=True)
            candidate = self.result("CANDIDATE_NONFINAL")
            require(len(json.dumps(candidate, allow_nan=False).encode("utf-8")) <= REPORT_CAP, "Verifier report cap")
            self.check(final=True)
            ack = object()
            self.publication.update(state="entered_return_unknown")
            returned = self.sink.seal(candidate, ack, self.end)
            # Store the observed return before any clock check.
            seal_returned = returned is ack
            self.publication.update(state="return_observed", return_observed=True, acknowledgment=seal_returned)
            self.check(final=True)
            require(seal_returned, "Seal acknowledgment missing/foreign")
            if normal and self.primary is None:
                self.proof("sealed")
                finalization.update(state="return_observed", ended=self.now())
                complete = self.result("COMPLETE_CONSISTENT_NEGATIVE" if self.negative else "COMPLETE_POSITIVE_EVIDENCE")
                # Construct the bounded report BEFORE the final same-clock gate.
                self.proof("final_clock")
                require([p.gate for p in self.proofs] == list(GATES) and all(p.owner is self.token for p in self.proofs), "Every owner-issued gate required")
                complete.update(elapsed_seconds=self.last_time - self.started, completed_gates=list(GATES))
                return complete
        except BaseException as error:
            self.publication_failed = True
            self.latch(error, "terminal_publication_or_clock")
        finalization.update(state="failed_or_incomplete", ended=self.report_time())
        status = "INCOMPLETE_TIMEOUT" if self.timed_out else "INCOMPLETE_CLOCK" if self.clock_failed else "INCOMPLETE_UNKNOWN_IO_OR_CLEANUP" if self.unknown else "INCOMPLETE_CLEANUP" if self.cleanup_failed else "INCOMPLETE_PUBLICATION" if self.publication_failed else "FAILED_INCONSISTENT_EVIDENCE"
        failed = self.result(status)
        try:
            # Reporting-only veto, including after deadline. Never mints proofs.
            self.sink.failure(failed)
        except BaseException as error:
            self.latch(error, "failure_reporting")
            failed = self.result(status)
        return failed


def run_once(request, *, clock, output_factory, authority_factory, file_factory, checker_factory):
    started = clock()  # First action: before every factory/import validation/inspection.
    require(type(started) in (int, float) and not isinstance(started, bool) and math.isfinite(started), "Finite first clock required")
    owner = _Owner(clock, started)
    try:
        # Shape validation is pure; it precedes even output factory construction.
        require(type(request) is Request and type(request.files) is tuple, "Typed request shape required")
        key = request.output_key
        require(type(key) is str and 0 < len(key) <= 128 and key not in (".", "..")
                and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-" for c in key), "Output key shape")
        owner.sink = output_factory()
        owner.check()
        reservation = object()
        owner.output_state = "entered_return_unknown"
        returned = owner.sink.reserve(key, reservation, owner.end)
        owner.output_owned = returned is reservation
        owner.output_state = "returned_owned" if owner.output_owned else "returned_not_owned"
        require(owner.output_owned, "Exclusive output reservation required")
        owner.check()
        owner.emit("verifier_reserved", maximum_files=MAX_FILES, event_capacity=MAX_EVENTS)
        # All factories run after ownership reservation, under the original clock.
        authority = authority_factory()
        owner.check()
        owner.port = file_factory()
        owner.check()
        checkers = checker_factory()
        owner.check()
        owner.stage("admit", lambda: owner.admit(request, authority, checkers))
        owner.stage("hash_capture", lambda: owner.hash_files(request))
        for stage, handler in zip(CHECKS, checkers.handlers):
            owner.stage(stage, lambda stage=stage, handler=handler: owner.check_stage(stage, handler))
        owner.stage("consistency", lambda: owner.proof("consistency"))
    except BaseException as error:
        owner.unknown = owner.unknown or any(f.get("open_state") == "entered_return_unknown" or f.get("pending_read") for f in owner.files)
        owner.latch(error, "verification")
    if owner.sink is None:
        return owner.result("INCOMPLETE_PUBLICATION")
    return owner.finish()
