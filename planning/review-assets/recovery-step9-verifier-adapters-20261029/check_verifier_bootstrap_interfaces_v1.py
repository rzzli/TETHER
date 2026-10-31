"""Synthetic bytes/clock/slots only. Source import is NOT a real clock bootstrap."""
import dataclasses
import hashlib
import importlib.util
import pathlib
import pickle
import sys
import unittest

HERE = pathlib.Path(__file__).parent
s = importlib.util.spec_from_file_location("bootstrap_proto", HERE / "verifier_bootstrap_interfaces_v1.py")
v = importlib.util.module_from_spec(s)
sys.modules[s.name] = v
s.loader.exec_module(v)
A = "C:/synthetic/a.py"
B = "C:/synthetic/b.py"


class Clock:
    def __init__(self): self.t, self.calls = 1000.0, []
    def __call__(self): self.calls.append("clock"); return self.t


class Sink:
    def __init__(self): self.rows, self.calls, self.mode = [], [], None
    def reserve(self, nonce):
        self.calls.append("reserve")
        if self.mode == "throw": raise RuntimeError("reserve unknown")
        return nonce if self.mode is None else object()
    def append(self, row): self.calls.append("append"); self.rows.append(row)


class Files:
    def __init__(self, bodies):
        self.bodies, self.offsets, self.opens, self.closes = bodies, {}, [], []
        self.open_hook = self.inspect_hook = self.read_hook = self.close_hook = None
    def acquire(self, slot, claim):
        raw = object()
        slot.observe_owned_open(raw)
        self.opens.append(raw)
        self.offsets[raw] = 0
        if self.open_hook: self.open_hook(slot)
    def inspect(self, slot, claim):
        if self.inspect_hook: self.inspect_hook(slot)
        return v.IdentityReturn(claim.path, claim.size, True, False)
    def read(self, slot, count):
        if self.read_hook: return self.read_hook(slot, count)
        offset = self.offsets[slot.handle]
        n = min(count, len(self.bodies[slot.claim.path]) - offset)
        slot.observe_read(True, n)
        raw = self.bodies[slot.claim.path][offset:offset + n]
        self.offsets[slot.handle] += len(raw)
        return raw
    def close(self, slot):
        self.closes.append(slot.handle)
        if self.close_hook: return self.close_hook(slot)
        slot.observe_close(True)


class Harness:
    def __init__(self, bodies=None):
        self.bodies = bodies or {A: b"VALUE=7\n", B: b"VALUE=11\n"}
        self.clock, self.sink, self.port = Clock(), Sink(), Files(self.bodies)
        self.claims = tuple(v.source_claim(dict(path=p, bytes=len(b), sha256=hashlib.sha256(b).hexdigest())) for p, b in self.bodies.items())
        self.owner = self.handoff = self.engine = None
    def setup(self, owner):
        self.clock.calls.append("setup")
        self.owner = owner
        owner.admit_sources(self.claims)
        owner.reserve_output(self.sink)
        owner.capture_all(self.port)
        self.handoff = owner.handoff()
        self.engine = self.handoff.claim()
        return self.engine
    def run(self): return v.start_injected(self.clock, self.setup)
    def close(self): self.owner.close_all(self.port)


class Checks(unittest.TestCase):
    def test_same_owner_origin_and_early_leases_no_second_pass(self):
        h = Harness(); engine = h.run()
        self.assertEqual(h.clock.calls[0], "clock")
        self.assertEqual(h.clock.calls[1], "clock")
        self.assertLess(h.clock.calls.index("clock"), h.clock.calls.index("setup"))
        self.assertIs(engine.owner, h.owner)
        self.assertEqual(engine.snapshot()["original_start"], 1000)
        self.assertEqual(engine.snapshot()["work_end"], 1295)
        self.assertEqual(engine.snapshot()["hard_end"], 1300)
        self.assertEqual(len(h.port.opens), 2)
        self.assertEqual(h.port.closes, [])
        self.assertEqual(h.owner.context.blobs[A], h.bodies[A])
        h.close(); h.close(); self.assertEqual(len(h.port.closes), 2)
        self.assertFalse(engine.snapshot()["verification_complete"])
        self.assertFalse(engine.snapshot()["real_profile_qualified"])

    def test_late_setup_and_handoff_do_not_reset_clock(self):
        clock = Clock(); captured = []
        def delayed(owner):
            captured.append(owner); clock.t = 1296
            owner.admit_sources(())
        with self.assertRaises(v.WorkExpired): v.start_injected(clock, delayed)
        self.assertEqual(captured[0].origin.start, 1000)
        h = Harness(); h.run(); h.clock.t = 1296
        with self.assertRaises(v.WorkExpired): h.engine.check()
        h.close(); self.assertEqual(len(h.port.closes), 2)

    def test_origin_and_handoff_not_serialized_or_resettable(self):
        h = Harness(); h.run()
        with self.assertRaises(TypeError): h.owner.origin._start = 1290
        with self.assertRaises(TypeError): pickle.dumps(h.owner.origin)
        with self.assertRaises(TypeError): pickle.dumps(h.handoff)
        with self.assertRaises(RuntimeError): h.handoff.claim()
        with self.assertRaises(RuntimeError): v.Origin(None, h.clock, 1290)
        with self.assertRaises(TypeError): h.handoff._owner = object()
        h.close()

    def test_failed_output_reservation_prevents_source_opens_and_writes(self):
        for mode in ("foreign", "throw"):
            h = Harness(); h.sink.mode = mode
            with self.assertRaises(RuntimeError): h.run()
            self.assertEqual(h.port.opens, [])
            self.assertEqual(h.sink.calls, ["reserve"])

    def test_raw_owned_handle_survives_allocation_or_identity_failure(self):
        for phase in ("open", "inspect"):
            h = Harness()
            def fail(slot):
                self.assertIs(slot.owner.slots[-1], slot)
                self.assertTrue(slot.owned)
                raise MemoryError("injected after registration")
            if phase == "open": h.port.open_hook = fail
            else: h.port.inspect_hook = fail
            with self.assertRaises(MemoryError): h.run()
            self.assertEqual(h.port.closes, h.port.opens)  # Error path already closed centrally.
            h.close(); h.close()
            self.assertEqual(h.port.closes, h.port.opens)
            self.assertEqual(h.owner.primary["error_class"], "MemoryError")

    def test_open_failure_null_and_unreturned_are_not_guessed_closed(self):
        for mode in ("failure", "null", "unreturned"):
            h = Harness()
            def acquire(slot, claim, mode=mode):
                if mode == "failure": slot.observe_open_failure()
                elif mode == "null": slot.observe_owned_open(None)
                else: raise KeyboardInterrupt("unreturned open")
            h.port.acquire = acquire
            with self.assertRaises(BaseException): h.run()
            h.close(); self.assertEqual(h.port.closes, [])
            slot = h.owner.slots[0]
            self.assertFalse(slot.owned)
            self.assertEqual(slot.open_return_observed, mode != "unreturned")

    def test_late_owned_open_and_identity_return_are_preserved(self):
        for phase in ("open", "inspect"):
            h = Harness()
            if phase == "open": h.port.open_hook = lambda slot: setattr(h.clock, "t", 1296)
            else: h.port.inspect_hook = lambda slot: setattr(h.clock, "t", 1296)
            with self.assertRaises(v.WorkExpired): h.run()
            h.close(); self.assertEqual(len(h.port.closes), 1)
            self.assertTrue(h.owner.slots[0].owned)
            self.assertEqual(h.owner.slots[0].identity_return is not None, phase == "inspect")

    def test_known_read_count_before_copy_hash_and_deadline_failures(self):
        for mode in ("copy", "late", "undefined", "unreturned"):
            h = Harness()
            def read(slot, count, mode=mode):
                if mode == "unreturned": raise KeyboardInterrupt("read unknown")
                slot.observe_read(mode != "undefined", 3)
                if mode == "copy": raise MemoryError("copy failed after known count")
                if mode == "late": h.clock.t = 1296
                return b"abc"
            h.port.read_hook = read
            with self.assertRaises(BaseException): h.run()
            slot = h.owner.slots[0]
            self.assertEqual(slot.known_bytes, 3 if mode in ("copy", "late") else 0)
            self.assertEqual(slot.hashed_bytes, 0)
            self.assertEqual(slot.pending_read, mode == "unreturned")
            h.close(); self.assertEqual(len(h.port.closes), 1)

    def test_digest_failure_preserves_known_bytes_and_unknown_hash_tail(self):
        h = Harness()
        class Digest:
            def update(self, raw): raise RuntimeError("digest update unknown")
        def setup(owner):
            h.owner = owner; owner.admit_sources(h.claims); owner.reserve_output(h.sink)
            slot = owner.acquire(h.claims[0], h.port)
            owner.capture(slot, h.port, Digest)
        with self.assertRaises(RuntimeError): v.start_injected(h.clock, setup)
        slot = h.owner.slots[0]
        self.assertEqual(slot.known_bytes, len(h.bodies[A]))
        self.assertEqual(slot.hashed_bytes, 0)
        self.assertTrue(slot.hash_update_pending)
        with self.assertRaises(RuntimeError): h.owner.capture(slot, h.port)
        h.close()

    def test_close_unknown_false_late_and_primary_are_once_only(self):
        for mode in ("unknown", "false", "late"):
            h = Harness(); h.run()
            h.owner.error(RuntimeError("earlier primary"), "fixture")
            def close(slot, mode=mode):
                if mode == "unknown": raise KeyboardInterrupt("close unknown")
                slot.observe_close(mode != "false")
                if mode == "late": h.clock.t = 1301
            h.port.close_hook = close
            h.close(); before = len(h.port.closes); h.close()
            self.assertEqual(len(h.port.closes), before)
            self.assertEqual(h.owner.primary["error"], "earlier primary")
            self.assertEqual(before, 1 if mode == "late" else 2)

    def test_handoff_rejects_early_close_missing_hash_and_reuse(self):
        h = Harness(); h.run(); h.close()
        with self.assertRaises(RuntimeError): h.owner.handoff()
        h = Harness()
        def setup(owner):
            h.owner = owner; owner.admit_sources(h.claims); owner.reserve_output(h.sink)
            owner.acquire(h.claims[0], h.port)
            return owner.handoff()
        with self.assertRaises(RuntimeError): v.start_injected(h.clock, setup)
        h.close()

    def test_loader_uses_same_captured_bytes_and_only_declared_dependencies(self):
        h = Harness(); h.run(); seen = []
        def compiler(name, raw, resolve):
            seen.append((name, raw))
            compile(raw, name, "exec")  # Synthetic bytes only; no execution or source read.
            return {"name": name, "dep": resolve("pkg.a", 0) if name == "pkg.b" else None}
        rules = (v.ModuleRule("pkg.a", A, ()), v.ModuleRule("pkg.b", B, ("pkg.a",)))
        loader = v.CapturedLoader(h.engine, rules, (), compiler)
        result = loader.load("pkg.b")
        self.assertEqual(result["dep"]["name"], "pkg.a")
        self.assertIs(seen[0][1], h.owner.context.blobs[B])
        self.assertEqual(len(h.port.opens), 2)
        self.assertIs(loader.load("pkg.b"), result)
        self.assertEqual(len(seen), 2)
        h.close()
        with self.assertRaises(RuntimeError): loader.load("pkg.b")

    def test_loader_no_sys_modules_path_stdlib_or_relative_fallback(self):
        h = Harness(); h.run(); sentinel = object()
        old = sys.modules.get("cached_own")
        sys.modules["cached_own"] = sentinel
        try:
            loader = v.CapturedLoader(h.engine, (v.ModuleRule("pkg.a", A, ()),), (), lambda n, b, r: r("cached_own"))
            with self.assertRaises(RuntimeError): loader.load("pkg.a")
            self.assertNotIn("cached_own", loader.loaded)
        finally:
            if old is None: sys.modules.pop("cached_own", None)
            else: sys.modules["cached_own"] = old
        h.close()
        h = Harness(); h.run()
        with self.assertRaises(RuntimeError): v.CapturedLoader(h.engine, (v.ModuleRule("pkg.a", A, ()),), (("os", object()),), lambda *a: None)
        loader = v.CapturedLoader(h.engine, (v.ModuleRule("pkg.a", A, ("math",)),), (("math", sentinel),), lambda n, b, r: r("math"))
        self.assertIs(loader.load("pkg.a"), sentinel)
        h.close()

    def test_loader_relative_cycle_missing_source_and_late_compile(self):
        h = Harness(); h.run()
        rules = (v.ModuleRule("pkg.a", A, ()), v.ModuleRule("pkg.b", B, ("pkg.a",)))
        loader = v.CapturedLoader(h.engine, rules, (), lambda n, b, r: r("a", 1) if n == "pkg.b" else n)
        self.assertEqual(loader.load("pkg.b"), "pkg.a")
        with self.assertRaises(RuntimeError): v.CapturedLoader(h.engine, (v.ModuleRule("a", A, ("b",)), v.ModuleRule("b", B, ("a",))), (), lambda *a: None)
        with self.assertRaises(RuntimeError): v.CapturedLoader(h.engine, (v.ModuleRule("x", "C:/synthetic/missing.py", ()),), (), lambda *a: None)
        h.close()
        h = Harness(); h.run()
        def late(name, raw, resolve): h.clock.t = 1296; return object()
        loader = v.CapturedLoader(h.engine, (v.ModuleRule("a", A, ()),), (), late)
        with self.assertRaises(v.WorkExpired): loader.load("a")
        self.assertTrue(h.owner.compile_records[-1]["return_observed"])
        self.assertNotIn("a", loader.loaded)
        h.close()

    def test_source_pin_alias_joint_caps_and_context_immutability(self):
        with self.assertRaises(RuntimeError): v.source_claim(dict(path=A, bytes=3, sha256="a" * 64, ready=True))
        for claim in (dataclasses.replace(Harness().claims[0], size=True), v.SourceClaim("C:\\synthetic\\..\\x.py", 0, "a" * 64)):
            h = Harness(); h.claims = (claim,)
            with self.assertRaises(RuntimeError): h.run()
            self.assertEqual(h.port.opens, [])
        h = Harness(); h.claims += (dataclasses.replace(h.claims[0], path=A.upper().replace("/", "\\")),)
        with self.assertRaises(RuntimeError): h.run()
        self.assertEqual(h.port.opens, [])
        h = Harness(); h.run()
        with self.assertRaises(TypeError): h.owner.context.blobs[A] = b"changed"
        with self.assertRaises(dataclasses.FrozenInstanceError): h.owner.context.claims = ()
        with self.assertRaises(TypeError): pickle.dumps(h.owner.context)
        h.close()

    def test_no_stub_result_can_claim_real_evidence_success(self):
        h = Harness(); h.run()
        loader = v.CapturedLoader(h.engine, (v.ModuleRule("a", A, ()),), (), lambda *a: {"passed": True, "ready": True})
        self.assertTrue(loader.load("a")["passed"])
        self.assertFalse(h.engine.snapshot()["verification_complete"])
        self.assertFalse(h.engine.snapshot()["real_profile_qualified"])
        self.assertEqual(h.engine.snapshot()["status"], "PURE_INTERFACE_OBSERVATIONS_ONLY_NOT_EVIDENCE_VERIFIED")
        h.close()

    def test_foreign_context_and_changed_roster_rejected_before_compiler(self):
        first, second = Harness(), Harness()
        first.run(); second.run(); calls = []
        first.owner.context = second.owner.context
        with self.assertRaises(RuntimeError):
            v.CapturedLoader(first.engine, (v.ModuleRule("a", A, ()),), (), lambda *a: calls.append(a))
        self.assertEqual(calls, [])
        first.close(); second.close()
        h = Harness(); h.run(); h.owner.claims = ()
        with self.assertRaises(RuntimeError):
            v.CapturedLoader(h.engine, (v.ModuleRule("a", A, ()),), (), lambda *a: None)
        h.close()

    def test_joint_source_event_admission_and_no_hidden_extra_open(self):
        h = Harness({f"C:/synthetic/s{i}.py": b"VALUE=1\n" for i in range(12)})
        h.run(); h.close()
        self.assertLessEqual(len(h.owner.events), v.MAX_EVENTS)
        self.assertEqual(len(h.port.opens), 12)
        h = Harness({f"C:/synthetic/s{i}.py": b"VALUE=1\n" for i in range(13)})
        with self.assertRaises(RuntimeError): h.run()
        self.assertEqual(h.port.opens, [])

    def test_journal_delay_prevents_next_identity_dispatch_and_latches(self):
        h = Harness(); original = h.sink.append; inspections = []
        def delayed(row):
            original(row)
            if row["event"] == "source_identity_reserved": h.clock.t = 1296
        h.sink.append = delayed
        h.port.inspect_hook = lambda slot: inspections.append(slot)
        with self.assertRaises(v.WorkExpired): h.run()
        self.assertEqual(inspections, [])
        h.close(); self.assertEqual(len(h.port.closes), 1)
        h = Harness(); original = h.sink.append
        def failed(row):
            if row["event"] == "source_open_returned": raise RuntimeError("append failed")
            original(row)
        h.sink.append = failed
        with self.assertRaises(RuntimeError): h.run()
        self.assertEqual(h.owner.primary["phase"], "journal_append")
        h.close()

    def test_foreign_closer_rejected_and_continuation_uses_original_port(self):
        h = Harness(); h.run(); foreign = Files(h.bodies)
        with self.assertRaises(RuntimeError): h.owner.close_all(foreign)
        self.assertEqual(foreign.closes, [])
        h.engine.close(); h.engine.close()
        self.assertEqual(len(h.port.closes), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
