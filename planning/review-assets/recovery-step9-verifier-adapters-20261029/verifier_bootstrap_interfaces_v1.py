"""Pure injected origin/ownership/source-loader prototype, with no live adapter.

A real entry must take its first clock BEFORE importing this component. This
module supplies the continuation interfaces and synthetic entry harness only.
There is no filesystem/ctypes/SDK/CLI, real evidence checker or success gate.
Trusted ports/compilers are a source-review boundary, not hostile-Python security.
"""
from dataclasses import dataclass
import hashlib
import math
from types import MappingProxyType

_MINT = object()
MAX_SOURCES = 16
MAX_CAPTURE = 64 * 1024**2
MAX_EVENTS = 128  # Narrow prototype bound, not a new live journal allowance.
CHUNK = 65536
STDLIB_NAMES = frozenset({"hashlib", "json", "struct", "math", "types", "dataclasses", "sys", "time"})


def need(value, message):
    if not value:
        raise RuntimeError(message)


class WorkExpired(TimeoutError):
    pass


def source_key(path):
    need(type(path) is str and 4 <= len(path) <= 4096, "Source path bound")
    need(path[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" and path[1] == ":" and path[2] in "/\\", "Absolute DOS source path")
    need(path[0].lower() != "e", "Protected drive")
    path.encode("utf-16-le", "strict")
    normalized = path.replace("\\", "/")
    for part in normalized[3:].split("/"):
        need(part not in ("", ".", "..") and not part.endswith((".", " ")) and not any(ord(c) < 32 or ord(c) == 127 or c in '<>:"|?*~' for c in part), "Noncanonical source component")
        need(part.split(".", 1)[0].lower() not in {"con", "prn", "aux", "nul", *["com" + str(i) for i in range(1, 10)], *["lpt" + str(i) for i in range(1, 10)]}, "Device source spelling")
    return normalized.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))


class Origin:
    __slots__ = ("_clock", "_start", "_last", "_nonce")

    def __init__(self, mint, clock, start):
        need(mint is _MINT, "Trusted entry must mint the origin")
        need(type(start) in (int, float) and math.isfinite(start), "Finite origin")
        object.__setattr__(self, "_clock", clock)
        object.__setattr__(self, "_start", start)
        object.__setattr__(self, "_last", start)
        object.__setattr__(self, "_nonce", object())

    def __setattr__(self, name, value):
        raise TypeError("Origin is not assignable")

    @property
    def start(self): return self._start

    @property
    def work_end(self): return self._start + 295

    @property
    def hard_end(self): return self._start + 300

    def check(self, *, cleanup=False):
        current = self._clock()
        need(type(current) in (int, float) and not isinstance(current, bool)
             and math.isfinite(current) and current >= self._last, "Invalid original clock")
        object.__setattr__(self, "_last", current)
        if current >= (self.hard_end if cleanup else self.work_end):
            raise WorkExpired("Original owner cutoff reached")
        return current

    def __reduce_ex__(self, protocol):
        raise TypeError("Origin is not serialized authority")


@dataclass(frozen=True)
class SourceClaim:
    path: str
    size: int
    sha256: str


def source_claim(pin):
    """Actual three-field file-pin schema; claims remain unverified metadata."""
    need(type(pin) is dict and set(pin) == {"path", "bytes", "sha256"}, "Exact source pin schema")
    return SourceClaim(pin["path"], pin["bytes"], pin["sha256"])


@dataclass(frozen=True)
class IdentityReturn:
    path: str
    size: int
    regular: bool
    reparse: bool


class LeaseSlot:
    """Preallocated application-level observations; future FFI conversion is not atomic."""
    def __init__(self, owner, claim):
        self.owner, self.claim = owner, claim
        self.handle = None
        self.open_state = "reserved"
        self.open_return_observed = False
        self.owned = False
        self.identity_return = None
        self.identity_ok = False
        self.read_attempts = self.read_returns = self.known_bytes = self.hashed_bytes = 0
        self.pending_read = False
        self.last_count = None
        self.last_count_defined = False
        self.requested = 0
        self.close_attempted = self.close_return_observed = self.closed = False
        self.close_state = "not_attempted"
        self.hash_complete = False
        self.hash_attempted = False
        self.hash_update_pending = False

    def observe_owned_open(self, handle):
        if self.open_state != "entered_unknown":
            raise RuntimeError("Open observation order")
        self.handle = handle  # First deliberate assignment after Python-visible return.
        self.open_return_observed = True
        self.owned = handle is not None
        self.open_state = "owned" if self.owned else "malformed_unknown"

    def observe_open_failure(self):
        if self.open_state != "entered_unknown":
            raise RuntimeError("Open observation order")
        self.open_return_observed = True
        self.open_state = "known_failure_no_handle"

    def observe_read(self, ok, count):
        if not self.pending_read:
            raise RuntimeError("No reserved read")
        self.last_count = count
        self.read_returns += 1
        self.pending_read = False
        self.last_count_defined = ok is True and type(count) is int and 0 <= count <= self.requested
        if self.last_count_defined:
            self.known_bytes += count

    def observe_close(self, ok):
        if not self.close_attempted or self.close_return_observed:
            raise RuntimeError("Close observation order")
        self.close_return_observed = True
        self.closed = ok is True
        self.close_state = "returned_success" if self.closed else "returned_failure"


@dataclass(frozen=True)
class CapturedSources:
    _nonce: object
    claims: tuple
    blobs: object
    digests: object

    def __post_init__(self):
        object.__setattr__(self, "blobs", MappingProxyType(dict(self.blobs)))
        object.__setattr__(self, "digests", MappingProxyType(dict(self.digests)))

    def __reduce_ex__(self, protocol):
        raise TypeError("Captured source context is not reusable authority")


class BootstrapOwner:
    def __init__(self, mint, origin):
        need(mint is _MINT and type(origin) is Origin, "Trusted owner construction")
        self.origin = origin
        self.claims = ()
        self.slots = []
        self.events = []
        self.errors = []
        self.primary = None
        self.sink = None
        self.output_owned = False
        self.context = None
        self._fresh_context = None
        self.compile_records = []
        self._handed_off = False
        self._adopted = False
        self._port = None

    def error(self, exc, phase):
        row = dict(phase=phase, error_class=type(exc).__name__, error=str(exc)[:512])
        if self.primary is None: self.primary = row
        self.errors.append(row)

    def event(self, name, *, cleanup=False, **fields):
        need(self.output_owned, "No writes into an unowned output")
        self.origin.check(cleanup=cleanup)
        need(len(self.events) < MAX_EVENTS, "Prototype event cap")
        row = dict(sequence=len(self.events), event=name, details=fields)
        self.events.append(row)
        try:
            self.sink.append(row)
        except BaseException as exc:
            self.error(exc, "journal_append")
            raise

    def reserve_output(self, sink):
        self.origin.check()
        need(self.sink is None, "No repeat reservation")
        self.sink = sink
        ack = object()
        returned = sink.reserve(ack)
        self.output_owned = returned is ack  # Before post-return clock/logging.
        self.origin.check()
        need(self.output_owned, "Output ownership not returned")
        self.event("bootstrap_reserved", origin=self.origin.start)

    def admit_sources(self, claims):
        self.origin.check()
        need(not self.claims and type(claims) is tuple and 0 < len(claims) <= MAX_SOURCES, "Finite exact source roster")
        need(10 * len(claims) + 8 <= MAX_EVENTS, "Joint source/event budget")
        paths = set()
        for claim in claims:
            need(type(claim) is SourceClaim and type(claim.path) is str and claim.path.endswith(".py"), "Source-only claim")
            key = source_key(claim.path)
            need(key not in paths, "Duplicate source role")
            paths.add(key)
            need(type(claim.size) is int and 0 <= claim.size <= MAX_CAPTURE, "Source byte cap")
            need(type(claim.sha256) is str and len(claim.sha256) == 64 and all(c in "0123456789abcdef" for c in claim.sha256), "Source SHA")
        need(sum(c.size for c in claims) <= MAX_CAPTURE, "Source capture aggregate")
        self.claims = claims

    def acquire(self, claim, port):
        self.origin.check()
        need(self.output_owned and claim in self.claims, "Admitted owned source required")
        need(self._port is None or self._port is port, "One source-bound file port per owner")
        self._port = port
        need(not any(s.claim.path == claim.path for s in self.slots), "No repeat original acquisition")
        slot = LeaseSlot(self, claim)
        self.slots.append(slot)  # Before port dispatch.
        self.event("source_open_reserved", path=claim.path)
        self.origin.check()
        slot.open_state = "entered_unknown"
        port.acquire(slot, claim)
        self.origin.check()
        need(slot.open_return_observed and slot.owned and slot.handle is not None, "No explicit owned original")
        self.event("source_open_returned", path=claim.path)
        self.event("source_identity_reserved", path=claim.path)
        self.origin.check()
        observed = port.inspect(slot, claim)
        slot.identity_return = observed  # Retain returned query data before time/type checks.
        self.origin.check()
        need(type(observed) is IdentityReturn and observed.path == claim.path and type(observed.size) is int
             and observed.size == claim.size and observed.regular is True and observed.reparse is False, "Original identity differs")
        slot.identity_ok = True
        self.event("source_identity_returned", path=claim.path)
        return slot

    def capture(self, slot, port, hash_factory=hashlib.sha256):
        self.origin.check()
        need(slot in self.slots and slot.identity_ok and not slot.hash_attempted, "Current inspected source slot required, no retry")
        slot.hash_attempted = True
        self.event("source_hash_reserved", path=slot.claim.path)
        self.origin.check()
        digest, captured = hash_factory(), bytearray()
        while slot.known_bytes < slot.claim.size:
            self.origin.check()
            need(slot.read_attempts < (slot.claim.size + CHUNK - 1) // CHUNK + 16, "Source read cap exhausted")
            slot.requested = min(CHUNK, slot.claim.size - slot.known_bytes)
            slot.pending_read = True
            slot.read_attempts += 1
            raw = port.read(slot, slot.requested)
            self.origin.check()
            need(not slot.pending_read and slot.last_count_defined and slot.last_count > 0, "Unknown/undefined/incomplete read")
            need(type(raw) is bytes and len(raw) == slot.last_count, "Read data/count mismatch")
            slot.hash_update_pending = True
            digest.update(raw)
            slot.hash_update_pending = False
            slot.hashed_bytes += len(raw)
            captured.extend(raw)
            self.origin.check()
        checksum = digest.hexdigest()
        self.origin.check()
        need(checksum == slot.claim.sha256, "Fresh source hash differs")
        slot.hash_complete = True
        self.event("source_hash_returned", path=slot.claim.path)
        self.origin.check()
        return bytes(captured), checksum

    def capture_all(self, port):
        blobs, digests = {}, {}
        for claim in self.claims:
            self.origin.check()
            slot = self.acquire(claim, port)
            blobs[claim.path], digests[claim.path] = self.capture(slot, port)
        self.context = CapturedSources(self.origin._nonce, self.claims, blobs, digests)
        self._fresh_context = self.context
        return self.context

    def require_live_sources(self):
        need(type(self.context) is CapturedSources and self.context is self._fresh_context
             and self.context._nonce is self.origin._nonce and self.context.claims is self.claims,
             "Current owner-issued source context required")
        need(len(self.slots) == len(self.claims) and tuple(s.claim for s in self.slots) == self.claims
             and all(s.owned and s.identity_ok and s.hash_complete and not s.close_attempted for s in self.slots),
             "Fresh live original sources required")

    def handoff(self):
        self.origin.check()
        need(self.primary is None and self.context is not None and not self._handed_off, "Complete current source handoff required")
        self.require_live_sources()
        self._handed_off = True
        self.event("bootstrap_handoff_reserved")
        self.origin.check()
        return Handoff(_MINT, self)

    def close_all(self, port):
        need(not self.slots or port is self._port, "Only original source-bound closer")
        for slot in reversed(self.slots):
            if not slot.owned or slot.close_attempted: continue
            try:
                self.origin.check(cleanup=True)
                slot.close_attempted = True
                slot.close_state = "reserved_once"
                try: self.event("source_close_reserved", cleanup=True, path=slot.claim.path)
                except BaseException as exc: self.error(exc, "close_reservation_journal")
                self.origin.check(cleanup=True)
                slot.close_state = "entered_unknown"
                port.close(slot)
                self.origin.check(cleanup=True)
                need(slot.close_return_observed and slot.closed, "Original close failed or unknown")
            except BaseException as exc:
                self.error(exc, "original_close")
            try: self.event("source_close_returned_or_unknown", cleanup=True, path=slot.claim.path, state=slot.close_state)
            except BaseException as exc: self.error(exc, "close_return_journal")

    def snapshot(self):
        return dict(status="PURE_INTERFACE_OBSERVATIONS_ONLY_NOT_EVIDENCE_VERIFIED", verification_complete=False,
                    real_profile_qualified=False, original_start=self.origin.start,
                    work_end=self.origin.work_end, hard_end=self.origin.hard_end,
                    primary_error=self.primary, errors=list(self.errors), output_owned=self.output_owned,
                    adopted=self._adopted, compile_records=list(self.compile_records), files=[dict(path=s.claim.path, open_state=s.open_state,
                        known_bytes=s.known_bytes, hashed_bytes=s.hashed_bytes, pending_read=s.pending_read,
                        hash_update_pending=s.hash_update_pending,
                        hash_complete=s.hash_complete, owned=s.owned, close_attempted=s.close_attempted,
                        close_return_observed=s.close_return_observed, closed=s.closed) for s in self.slots])


class Handoff:
    __slots__ = ("_owner", "_claimed")

    def __init__(self, mint, owner):
        need(mint is _MINT, "Owner-issued handoff only")
        object.__setattr__(self, "_owner", owner)
        object.__setattr__(self, "_claimed", False)

    def __setattr__(self, name, value):
        raise TypeError("Handoff identity is not assignable")

    def claim(self):
        need(not self._claimed and not self._owner._adopted, "No repeated/cross-owner handoff")
        object.__setattr__(self, "_claimed", True)
        self._owner.origin.check()  # No new start/owner/output/source read.
        need(self._owner.primary is None, "Owner failure before adoption")
        self._owner.require_live_sources()
        self._owner._adopted = True
        return EngineContinuation(_MINT, self._owner)

    def __reduce_ex__(self, protocol):
        raise TypeError("Handoff is not serializable authority")


class EngineContinuation:
    """Same-owner interface, not the production verification/checker binding."""
    def __init__(self, mint, owner):
        need(mint is _MINT and owner._adopted, "Claimed trusted handoff required")
        self.owner = owner

    def check(self): return self.owner.origin.check()

    def snapshot(self): return self.owner.snapshot()

    def close(self):
        if self.owner._port is not None:
            self.owner.close_all(self.owner._port)


@dataclass(frozen=True)
class ModuleRule:
    fullname: str
    path: str
    dependencies: tuple
    package: bool = False


class CapturedLoader:
    """Injected compiler only: no importlib, sys.modules, path or default import."""
    def __init__(self, continuation, rules, stdlib, compiler):
        need(type(continuation) is EngineContinuation, "Current owner continuation required")
        self.owner = continuation.owner
        self.owner.origin.check()
        self.owner.require_live_sources()
        need(type(rules) is tuple and 0 < len(rules) <= MAX_SOURCES, "Finite module map")
        self.rules = {r.fullname: r for r in rules if type(r) is ModuleRule}
        need(len(self.rules) == len(rules), "Duplicate/invalid module rules")
        need(type(stdlib) is tuple, "Exact stdlib binding tuple")
        self.stdlib = dict(stdlib)
        need(len(self.stdlib) == len(stdlib) and set(self.stdlib) <= STDLIB_NAMES and not set(self.rules) & set(self.stdlib), "Module binding/stdlib whitelist collision")
        self.compiler, self.loaded, self.active, self.attempted = compiler, {}, set(), set()
        need(len({r.path for r in rules}) == len(rules), "One exact source per own module")
        for rule in rules:
            need(type(rule.dependencies) is tuple and len(set(rule.dependencies)) == len(rule.dependencies), "Exact dependencies")
            need(rule.path in self.owner.context.blobs and all(d in self.rules or d in self.stdlib for d in rule.dependencies), "Uncaptured/unknown module dependency")
        def visit(name, chain):
            need(name not in chain, "Own module dependency cycle")
            for dep in self.rules[name].dependencies:
                if dep in self.rules: visit(dep, chain + (name,))
        for name in self.rules: visit(name, ())

    def resolve(self, caller, name, level=0):
        self.owner.origin.check()
        need(caller in self.active and type(name) is str and type(level) is int and level >= 0, "Source-bound active importer required")
        target = name
        if level:
            rule = self.rules[caller]
            package = caller.split(".") if rule.package else caller.split(".")[:-1]
            need(level <= len(package), "Unresolved relative import")
            base = package[:len(package) - level + 1]
            target = ".".join(base + ([name] if name else []))
        need(target in self.rules[caller].dependencies, "Undeclared import/no fallback")
        return self.load(target) if target in self.rules else self.stdlib[target]

    def load(self, fullname):
        self.owner.origin.check()
        need(self.owner.primary is None, "Owner failure latched; no continued source execution")
        self.owner.require_live_sources()
        need(fullname in self.rules, "Unknown own module/no cached fallback")
        need(fullname not in self.active, "Recursive source compilation")
        rule = self.rules[fullname]
        # Original leases must still be owned/live when captured source executes.
        slot = next(s for s in self.owner.slots if s.claim.path == rule.path)
        need(slot.owned and not slot.close_attempted and slot.hash_complete, "Source lease no longer live")
        if fullname in self.loaded: return self.loaded[fullname]
        need(fullname not in self.attempted, "No retry of failed/unknown compile")
        self.attempted.add(fullname)
        rec = dict(module=fullname, state="reserved", return_observed=False)
        self.owner.compile_records.append(rec)
        self.owner.event("source_compile_reserved", module=fullname)
        self.owner.origin.check()
        self.active.add(fullname)
        try:
            rec["state"] = "entered_unknown"
            result = self.compiler(fullname, self.owner.context.blobs[rule.path],
                                   lambda name, level=0: self.resolve(fullname, name, level))
            rec.update(state="return_observed", return_observed=True)
            self.owner.origin.check()
            self.loaded[fullname] = result
            self.owner.event("source_compile_returned", module=fullname)
            return result
        except BaseException as exc:
            self.owner.error(exc, "source_compile")
            raise
        finally:
            self.active.remove(fullname)


def start_injected(clock, setup):
    """Synthetic entry only; a future real bootstrap takes its origin before import."""
    started = clock()  # Before setup/factory/source/import simulation.
    origin = Origin(_MINT, clock, started)
    owner = BootstrapOwner(_MINT, origin)
    try:
        owner.origin.check()
        return setup(owner)
    except BaseException as exc:
        owner.error(exc, "bootstrap_or_continuation")
        # Central registry only: no adapter/destructor retries or new owner.
        if owner._port is not None:
            owner.close_all(owner._port)
        raise
