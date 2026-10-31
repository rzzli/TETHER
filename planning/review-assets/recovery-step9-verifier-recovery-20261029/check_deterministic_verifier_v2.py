"""Synthetic orchestration checks. Never opens input/old payload/SDK paths."""
import dataclasses
import hashlib
import importlib.util
import json
import pathlib
import pickle
import sys
import unittest

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("recovery_engine_v2", HERE / "deterministic_verifier_v2.py")
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)
PATH = "C:/synthetic/evidence.json"


class Clock:
    def __init__(self):
        self.t = 0.0
        self.trace = []
        self.broken = False
        self.late_countdown = None

    def __call__(self):
        self.trace.append("clock")
        if self.late_countdown is not None:
            if self.late_countdown == 0:
                self.t = 301
            else:
                self.late_countdown -= 1
        return float("nan") if self.broken else self.t


class Sink:
    def __init__(self, clock):
        self.clock = clock
        self.used = False
        self.calls = []
        self.events = []
        self.reserve_mode = self.seal_mode = None
        self.fail_event = None
        self.failure_throws = False

    def reserve(self, key, nonce, deadline):
        self.calls.append("reserve")
        if self.reserve_mode == "throw":
            raise RuntimeError("reserve outcome unknown")
        if self.used or self.reserve_mode == "false":
            return False
        if self.reserve_mode == "foreign":
            return object()
        self.used = True
        if self.reserve_mode == "late":
            self.clock.t = 296
        return nonce

    def append(self, row):
        self.calls.append("append")
        self.events.append(row)
        if row["event"] == self.fail_event:
            raise RuntimeError("journal publication failed")

    def seal(self, candidate, nonce, deadline):
        self.calls.append("seal")
        self.candidate = candidate
        if self.seal_mode == "throw":
            raise RuntimeError("seal return unknown")
        if self.seal_mode == "late":
            self.clock.t = 301
        if self.seal_mode == "last_clock":
            self.clock.late_countdown = 3
        return object() if self.seal_mode == "foreign" else nonce

    def failure(self, result):
        self.calls.append("failure")
        if self.failure_throws:
            raise RuntimeError("veto publication failed")
        self.failed = result


class Files:
    def __init__(self, clock, bodies):
        self.clock, self.bodies = clock, bodies
        self.offsets, self.opened, self.closed = {}, [], []
        self.open_hook = self.read_hook = self.close_hook = None

    def open(self, claim, deadline):
        handle = object()
        self.offsets[handle] = (claim.path, 0)
        self.opened.append(handle)
        if self.open_hook:
            self.open_hook(handle)
        return v.OpenReturn(handle, claim.size, claim.path, owned=True)

    def read(self, handle, count, deadline):
        if self.read_hook:
            override = self.read_hook(handle, count)
            if override is not None:
                return override
        path, offset = self.offsets[handle]
        data = self.bodies[path][offset:offset + count]
        self.offsets[handle] = (path, offset + len(data))
        return v.ReadReturn(True, len(data), data)

    def close(self, handle, deadline):
        self.closed.append(handle)
        if self.close_hook:
            return self.close_hook(handle)
        return True


class Harness:
    def __init__(self, body=b'{"archive":true,"journal":true,"resources":true,"core":true}'):
        self.clock = Clock()
        self.sink = Sink(self.clock)
        self.files = Files(self.clock, {PATH: body})
        self.claims = (v.FileSpec(PATH, "owner_metadata", len(body), hashlib.sha256(body).hexdigest(), True),)
        self.ids = tuple((stage, hashlib.sha256(stage.encode()).hexdigest()) for stage in v.CHECKS)
        self.seen = []
        self.contexts = []
        self.handler_override = {}
        self.factory_hook = None

    def factory(self, name, value):
        self.clock.trace.append(name)
        if self.factory_hook:
            self.factory_hook(name)
        return value

    def handlers(self):
        def make(stage):
            def handler(context):
                self.seen.append(stage)
                self.contexts.append(context)
                if stage in self.handler_override:
                    return self.handler_override[stage](context)
                doc = json.loads(context.bytes_for(PATH))
                verdict = "consistent" if doc[stage] else "inconsistent"
                return v.CheckObservation(context, stage, verdict, (PATH,))
            return handler
        return tuple(make(stage) for stage in v.CHECKS)

    def run(self, request=None, authority=None, handlers=None):
        return v.run_once(request or v.Request("fresh-output", self.claims), clock=self.clock,
                          output_factory=lambda: self.factory("output_factory", self.sink),
                          authority_factory=lambda: self.factory("authority_factory", authority or v.Authority(self.claims, self.ids)),
                          file_factory=lambda: self.factory("file_factory", self.files),
                          checker_factory=lambda: self.factory("checker_factory", v.CheckerPorts(self.ids, handlers or self.handlers())))


class Checks(unittest.TestCase):
    def complete(self, result):
        self.assertTrue(result["verification_complete"])
        self.assertEqual(result["completed_gates"], list(v.GATES))
        self.assertFalse(result["real_profile_qualified"])

    def incomplete(self, result):
        self.assertFalse(result["verification_complete"])
        self.assertFalse(result["real_profile_qualified"])

    def test_complete_order_and_negative(self):
        for negative in (False, True):
            with self.subTest(negative=negative):
                h = Harness()
                if negative:
                    h.handler_override["core"] = lambda c: v.CheckObservation(c, "core", "negative", (PATH,), "fixed profile unavailable")
                r = h.run()
                self.complete(r)
                self.assertEqual(r["status"], "COMPLETE_CONSISTENT_NEGATIVE" if negative else "COMPLETE_POSITIVE_EVIDENCE")
                self.assertEqual(h.seen, list(v.CHECKS))
                self.assertEqual(h.clock.trace[0], "clock")
                self.assertLess(h.clock.trace.index("output_factory"), h.clock.trace.index("authority_factory"))
                self.assertEqual(h.sink.calls[0], "reserve")
                self.assertEqual(len(h.files.closed), 1)
                self.assertEqual(h.sink.candidate["status"], "CANDIDATE_NONFINAL")
                events = [e["event"] for e in h.sink.events]
                self.assertLess(events.index("finalization_reserved"), events.index("file_close_reserved"))
                self.assertEqual(events[-1], "terminal_seal_reserved")

    def test_shape_before_output_and_failed_reservations(self):
        for request in (v.Request("../old", ()), v.Request("", ()), {"ready": True}):
            h = Harness()
            r = h.run(request=request)
            self.incomplete(r)
            self.assertEqual(h.sink.calls, [])
            self.assertNotIn("output_factory", h.clock.trace)
        for mode in ("false", "foreign", "throw"):
            h = Harness(); h.sink.reserve_mode = mode
            r = h.run()
            self.incomplete(r)
            self.assertEqual(r["status"], "INCOMPLETE_OUTPUT_RESERVATION")
            self.assertEqual(h.sink.calls, ["reserve"])
            self.assertEqual(h.files.opened, [])

    def test_same_output_cannot_repeat(self):
        h = Harness(); self.complete(h.run())
        old_opens = len(h.files.opened)
        old_calls = len(h.sink.calls)
        self.incomplete(h.run())
        self.assertEqual(len(h.files.opened), old_opens)
        self.assertEqual(h.sink.calls[old_calls:], ["reserve"])

    def test_factories_under_original_clock_and_reserve(self):
        for factory in ("output_factory", "authority_factory", "file_factory", "checker_factory"):
            h = Harness()
            h.factory_hook = lambda name, target=factory: setattr(h.clock, "t", 296) if name == target else None
            r = h.run()
            self.incomplete(r)
            self.assertEqual(h.files.opened, [])
            self.assertEqual(r["original_deadline"], 300)
            self.assertEqual(r["work_deadline"], 295)
        h = Harness(); h.sink.reserve_mode = "late"
        r = h.run(); self.assertEqual(r["status"], "INCOMPLETE_TIMEOUT")
        self.assertEqual(h.files.opened, [])
        self.assertEqual(r["output_reservation"], "returned_owned")

    def test_roles_collision_caps_and_exact_claims(self):
        base = Harness().claims[0]
        mutations = [dataclasses.replace(base, size=True), dataclasses.replace(base, sha256="f" * 64),
                     dataclasses.replace(base, role="model", capture=False),
                     dataclasses.replace(base, role="software", size=v.SMALL_CAP + 1),
                     dataclasses.replace(base, role="CPU", capture=True),
                     dataclasses.replace(base, path="E:/forbidden/x.dll"),
                     dataclasses.replace(base, path="C:/synthetic/../x.json")]
        for claim in mutations:
            h = Harness(); r = h.run(request=v.Request("fresh", (claim,)))
            self.incomplete(r); self.assertEqual(h.files.opened, [])
        for claims in ((base, dataclasses.replace(base, path=PATH.upper().replace("/", "\\"))), (base,) * 257):
            h = Harness(); h.claims = claims
            r = h.run(); self.incomplete(r); self.assertEqual(h.files.opened, [])
        # Exact trusted model exception is not a general size/capture exemption.
        h = Harness(); model = v.FileSpec("C:/synthetic/m.gguf", "model", v.SMALL_CAP + 1, "1" * 64, False)
        h.claims = (base, model)
        h.files.open_hook = lambda handle: (_ for _ in ()).throw(RuntimeError("stop before synthetic body"))
        r = h.run(); self.assertIn("admission", r["completed_gates"])
        self.assertEqual(len(h.files.opened), 1)

    def test_late_open_owned_and_closed(self):
        h = Harness(); h.files.open_hook = lambda handle: setattr(h.clock, "t", 296)
        r = h.run(); self.assertEqual(r["status"], "INCOMPLETE_TIMEOUT")
        self.assertEqual(len(h.files.closed), 1)
        self.assertEqual(r["files"][0]["open_state"], "return_observed_owned")
        self.assertEqual(r["files"][0]["read_attempts"], 0)

    def test_read_late_failed_and_unreturned(self):
        h = Harness()
        h.files.read_hook = lambda handle, count: (setattr(h.clock, "t", 296), v.ReadReturn(True, 3, b"abc"))[1]
        r = h.run(); self.assertEqual(r["status"], "INCOMPLETE_TIMEOUT")
        self.assertEqual(r["files"][0]["known_returned_bytes"], 3)
        self.assertEqual(r["files"][0]["hash_updated_bytes"], 0)
        for result in (v.ReadReturn(False, 999, b""), v.ReadReturn(True, True, b"x")):
            h = Harness(); h.files.read_hook = lambda handle, count, result=result: result
            r = h.run(); self.assertEqual(r["status"], "INCOMPLETE_UNKNOWN_IO_OR_CLEANUP")
            self.assertEqual(r["files"][0]["known_returned_bytes"], 0)
            self.assertEqual(r["files"][0]["read_returns"], 1)
        h = Harness(); h.files.read_hook = lambda h, n: (_ for _ in ()).throw(KeyboardInterrupt("unknown read"))
        r = h.run(); self.assertEqual(r["status"], "INCOMPLETE_UNKNOWN_IO_OR_CLEANUP")
        self.assertTrue(r["files"][0]["pending_read"])
        self.assertEqual(len(h.files.closed), 1)

    def test_hash_fault_and_late_digest(self):
        class BadHash:
            def update(self, data):
                raise RuntimeError("hash failed after read")
        old = v._new_hasher
        try:
            v._new_hasher = BadHash
            h = Harness(); r = h.run()
            self.incomplete(r)
            self.assertGreater(r["files"][0]["known_returned_bytes"], 0)
            self.assertEqual(r["files"][0]["hash_updated_bytes"], 0)
            self.assertEqual(len(h.files.closed), 1)
        finally:
            v._new_hasher = old
        h = Harness()
        class LateDigest:
            def __init__(self): self.inner = hashlib.sha256()
            def update(self, data): self.inner.update(data)
            def hexdigest(self):
                h.clock.t = 296
                return self.inner.hexdigest()
        try:
            v._new_hasher = LateDigest
            r = h.run(); self.assertEqual(r["status"], "INCOMPLETE_TIMEOUT")
            self.assertFalse(r["files"][0]["hash_complete"])
        finally:
            v._new_hasher = old

    def test_context_immutable_nonserializable_foreign(self):
        h = Harness(); self.complete(h.run()); context = h.contexts[0]
        for name, value in (("specs", ()), ("_blobs", {}), ("digests", {}), ("_check", lambda: None)):
            with self.assertRaises((AttributeError, dataclasses.FrozenInstanceError)):
                setattr(context, name, value)
        with self.assertRaises(TypeError): context._blobs[PATH] = b"changed"
        with self.assertRaises(TypeError): pickle.dumps(context)
        h2 = Harness(); h2.handler_override["archive"] = lambda c: v.CheckObservation(context, "archive", "consistent", (PATH,))
        self.incomplete(h2.run())

    def test_required_checker_results_not_ready_markers(self):
        for returned in (True, {"ready": True}, {"passed": True}, None):
            h = Harness(); h.handler_override["archive"] = lambda c, returned=returned: returned
            r = h.run(); self.incomplete(r)
            self.assertNotIn("archive", r["completed_gates"])
        h = Harness()
        ids = h.ids[::-1]
        r = h.run(authority=v.Authority(h.claims, ids))
        self.incomplete(r); self.assertEqual(h.files.opened, [])

    def test_late_checker_return_and_clock_primary(self):
        h = Harness()
        def late(context):
            h.clock.t = 296
            return v.CheckObservation(context, "archive", "consistent", (PATH,))
        h.handler_override["archive"] = late
        r = h.run(); self.assertEqual(r["status"], "INCOMPLETE_TIMEOUT")
        self.assertTrue(r["checker_operations"][0]["return_observed"])
        self.assertEqual(r["checker_operations"][0]["reported_verdict"], "consistent")
        self.assertNotIn("archive", r["completed_gates"])
        h = Harness()
        def fail(context):
            h.clock.broken = True
            raise RuntimeError("original checker failure")
        h.handler_override["archive"] = fail
        r = h.run(); self.incomplete(r)
        self.assertEqual(r["primary_error"]["error"], "original checker failure")
        self.assertTrue(any(e["phase"] == "timing_observation" for e in r["errors"]))

    def test_every_work_stage_uses_same_deadline(self):
        for stage in v.CHECKS:
            h = Harness()
            def late(context, stage=stage):
                h.clock.t = 295
                return v.CheckObservation(context, stage, "consistent", (PATH,))
            h.handler_override[stage] = late
            r = h.run(); self.assertEqual(r["status"], "INCOMPLETE_TIMEOUT")
            self.assertNotIn(stage, r["completed_gates"])
            self.assertEqual(r["original_deadline"], 300)

    def test_synthetic_archive_journal_resource_contradictions(self):
        for stage in ("archive", "journal", "resources", "core"):
            doc = {k: k != stage for k in v.CHECKS}
            h = Harness(json.dumps(doc).encode())
            r = h.run(); self.assertEqual(r["status"], "FAILED_INCONSISTENT_EVIDENCE")
            self.assertNotIn(stage, r["completed_gates"])
            self.assertEqual(len(h.files.closed), 1)

    def test_close_false_unknown_late_no_retry(self):
        for mode in ("false", "throw", "late"):
            h = Harness()
            def close(handle, mode=mode):
                if mode == "throw": raise RuntimeError("close unknown")
                if mode == "late": h.clock.t = 301
                return mode != "false"
            h.files.close_hook = close
            r = h.run(); self.incomplete(r)
            self.assertEqual(len(h.files.closed), 1)
            self.assertTrue(r["leases"][0]["close_attempted"])
            self.assertEqual(r["status"], {"false": "INCOMPLETE_CLEANUP", "throw": "INCOMPLETE_UNKNOWN_IO_OR_CLEANUP", "late": "INCOMPLETE_TIMEOUT"}[mode])

    def test_cleanup_journal_error_and_primary_later_preserved(self):
        h = Harness(); h.sink.fail_event = "file_close_reserved"
        r = h.run(); self.incomplete(r); self.assertEqual(len(h.files.closed), 1)
        self.assertEqual(r["status"], "INCOMPLETE_PUBLICATION")
        h = Harness(); h.sink.fail_event = "file_open_returned"
        h.files.close_hook = lambda handle: (_ for _ in ()).throw(RuntimeError("late close failure"))
        r = h.run(); self.incomplete(r)
        self.assertEqual(r["primary_error"]["error"], "journal publication failed")
        self.assertTrue(any(e["error"] == "late close failure" for e in r["errors"]))
        self.assertEqual(len(h.files.closed), 1)

    def test_seal_failure_foreign_and_postseal_timeout(self):
        for mode in ("throw", "foreign", "late", "last_clock"):
            h = Harness(); h.sink.seal_mode = mode
            r = h.run(); self.incomplete(r)
            self.assertIn("failure", h.sink.calls)
            self.assertEqual(r["terminal_publication"]["return_observed"], mode != "throw")
            self.assertEqual(r["status"], "INCOMPLETE_TIMEOUT" if mode in ("late", "last_clock") else "INCOMPLETE_PUBLICATION")
        h = Harness(); h.sink.seal_mode = "throw"; h.sink.failure_throws = True
        r = h.run(); self.incomplete(r)
        self.assertEqual(r["primary_error"]["error"], "seal return unknown")
        self.assertEqual(r["errors"][-1]["phase"], "failure_reporting")

    def test_max_files_joint_event_headroom_and_capture_cap(self):
        h = Harness()
        h.claims = tuple(v.FileSpec(f"C:/synthetic/evidence{i}.json", "owner_metadata", 0, hashlib.sha256(b"").hexdigest(), True) for i in range(256))
        h.files.bodies = {s.path: b"" for s in h.claims}
        h.handler_override = {stage: (lambda c, stage=stage: v.CheckObservation(c, stage, "consistent", (c.specs[0].path,))) for stage in v.CHECKS}
        r = h.run(); self.complete(r)
        self.assertLessEqual(r["event_attempts"], v.EVENTS_PER_FILE * 256 + v.FIXED_EVENTS)
        self.assertLessEqual(v.EVENTS_PER_FILE * 256 + v.FIXED_EVENTS + v.FAILURE_EVENTS, v.MAX_EVENTS)
        h = Harness(); h.claims = (v.FileSpec(PATH, "pack", v.PACK_CAP + 1, "1" * 64, True),)
        r = h.run(); self.incomplete(r); self.assertEqual(h.files.opened, [])

    def test_hard_expiry_stops_remaining_close_dispatch(self):
        h = Harness()
        second = dataclasses.replace(h.claims[0], path="C:/synthetic/second.json")
        h.claims += (second,)
        h.files.bodies[second.path] = h.files.bodies[PATH]
        def late_close(handle):
            h.clock.t = 301
            return True
        h.files.close_hook = late_close
        r = h.run(); self.assertEqual(r["status"], "INCOMPLETE_TIMEOUT")
        self.assertEqual(len(h.files.closed), 1)
        self.assertEqual(r["leases"][0]["close_state"], "not_dispatched_deadline")
        self.assertFalse(r["leases"][0]["close_attempted"])

    def test_checker_mutation_and_omitted_gate_cannot_complete(self):
        h = Harness()
        def mutation(context):
            context.specs = ()
            return v.CheckObservation(context, "archive", "consistent", (PATH,))
        h.handler_override["archive"] = mutation
        self.incomplete(h.run())
        old = v._Owner.proof
        try:
            def omit(owner, gate):
                if gate != "consistency":
                    return old(owner, gate)
            v._Owner.proof = omit
            r = Harness().run(); self.incomplete(r)
            self.assertNotIn("final_clock", r["completed_gates"])
        finally:
            v._Owner.proof = old

    def test_open_return_explicit_ownership_only(self):
        cases = (None, object(), v.OpenReturn(None, 0, PATH, owned=True),
                 v.OpenReturn(object(), 0, PATH, owned=False),
                 v.OpenReturn(object(), 0, PATH, owned=1))
        for returned in cases:
            with self.subTest(type=type(returned).__name__):
                h = Harness(); h.files.open = lambda claim, deadline, returned=returned: returned
                r = h.run(); self.incomplete(r)
                self.assertEqual(h.files.closed, [])
                self.assertEqual(r["leases"], [])
                self.assertEqual(r["status"], "INCOMPLETE_UNKNOWN_IO_OR_CLEANUP")
                self.assertTrue(r["files"][0]["open_return_observed"])
                self.assertEqual(r["files"][0]["open_state"], "return_observed_malformed_ownership_unknown")

    def test_open_failure_known_no_transferred_handle(self):
        for reason in ("denied", "", "x" * 513, None):
            h = Harness(); h.files.open = lambda claim, deadline, reason=reason: v.OpenFailure(reason)
            r = h.run(); self.incomplete(r)
            self.assertEqual(h.files.closed, [])
            self.assertEqual(r["leases"], [])
            self.assertEqual(r["status"], "INCOMPLETE_ORIGINAL_IO")
            self.assertEqual(r["files"][0]["open_state"], "return_observed_failure_no_handle")

    def test_owned_metadata_failure_still_closed_once(self):
        h = Harness(); handle = object()
        h.files.open = lambda claim, deadline: v.OpenReturn(handle, claim.size + 1, claim.path, owned=True)
        r = h.run(); self.incomplete(r)
        self.assertEqual(h.files.closed, [handle])
        self.assertEqual(r["files"][0]["open_state"], "return_observed_owned")

    def test_factories_have_reserved_and_return_witnesses(self):
        for factory in ("authority_factory", "file_factory", "checker_factory"):
            for mode in ("throw", "late"):
                h = Harness()
                def hook(name, factory=factory, mode=mode):
                    if name == factory:
                        if mode == "throw": raise RuntimeError("factory return unknown")
                        h.clock.t = 296
                h.factory_hook = hook
                r = h.run(); self.incomplete(r)
                self.assertEqual(h.files.opened, [])
                row = next(s for s in r["stages"] if s["stage"] == factory)
                self.assertEqual(row["state"], "failed_or_unknown" if mode == "throw" else "return_observed")
                reserved = [e for e in h.sink.events if e["event"] == "stage_reserved" and e["details"].get("stage") == factory]
                self.assertEqual(len(reserved), 1)
        h = Harness(); r = h.run(); self.complete(r)
        for factory in ("authority_factory", "file_factory", "checker_factory"):
            self.assertEqual(next(s for s in r["stages"] if s["stage"] == factory)["state"], "return_observed")
        self.assertLessEqual(r["event_attempts"], v.EVENTS_PER_FILE + v.FIXED_EVENTS)
        h = Harness(); h.claims = (v.FileSpec(PATH, "owner_metadata", v.CAPTURE_CAP + 1, "1" * 64, True),)
        r = h.run(); self.incomplete(r); self.assertEqual(h.files.opened, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
