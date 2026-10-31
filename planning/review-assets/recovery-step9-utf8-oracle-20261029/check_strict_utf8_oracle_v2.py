"""Frozen-corpus, API and corruption controls for the independent pure oracle."""
import ast
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import hashlib
from importlib import util
import io
import json
from pathlib import Path
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "strict_utf8_oracle_v1.py"
SOURCE_SHA = "4e5d36afa001339735a349a8ebab88a312cde1cb57fa43336e38ee4195134c21"
CORPUS = HERE / "UTF8-ORACLE-CORPUS-v2.json"
CORPUS_SHA = "65428d32cc06c58836d1d541bde0e893db13cef9e5ae756e26d6e353908b302d"
SPEC = HERE / "UTF8-ORACLE-SPEC-v2.md"
SPEC_SHA = "f4f3835481f1961c01830bf6ba37107cf270ebaad7a9321d6f1b4ee0fcdec44a"
REFERENCE = HERE / "UTF8-ORACLE-SPLIT-REFERENCE-PROOF-v2.json"
REFERENCE_SHA = "1a1c1e683d5e59a0901313fdb8946a0a3da10dc4d4c626bfd7f45895d87555e9"
DECISION = HERE / "UTF8-ORACLE-IMPLEMENTATION-ROOT-DECISION-v1.json"
DECISION_SHA = "3ab0cd82c197a10d80e7c41bc6a5c1c10a71b10e35cdd1d7f1b22b53b5f0a5bd"
REPORT = HERE / "UTF8-ORACLE-IMPLEMENTATION-PURE-PROOF-v2.json"
TRACES = []
CONTROL_RESULTS = []
DENIALS = []


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def exact(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return set(a) == set(b) and all(exact(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(exact(x, y) for x, y in zip(a, b))
    return a == b


def audit(event, args):
    if event in {"ctypes.dlopen", "subprocess.Popen", "os.system", "os.spawn", "socket.connect", "socket.getaddrinfo"}:
        DENIALS.append(event)
        raise RuntimeError("Pure oracle check forbids external capabilities")
    if event == "open" and args and isinstance(args[0], (str, bytes)):
        value = str(args[0]).lower().replace("/", "\\")
        if value.endswith((".gguf", ".dll", ".pyd", "recognition.pack")) or "\\data\\benchmark\\" in value:
            DENIALS.append("protected_payload_open")
            raise RuntimeError("No native/model/old-pack/benchmark payload access")


class OracleChecks(unittest.TestCase):
    def test_frozen_fixture_semantics(self):
        for case in CASES:
            with self.subTest(case=case["id"]):
                decoder = oracle.StrictUtf8Oracle()
                states = []
                for index, step in enumerate(case["steps"]):
                    tick()
                    frame = decoder.feed(bytes.fromhex(step["chunk_hex"]), final=step["final"])
                    actual = frame.to_dict()
                    self.assertTrue(exact(actual, step["expected"]), (case["id"], index, actual, step["expected"]))
                    self.assertIs(decoder.snapshot, frame)
                    states.append(actual)
                TRACES.append(dict(id=case["id"], steps=len(states), matched=True,
                    observed_states_sha256=hashlib.sha256(json.dumps(states, sort_keys=True, separators=(",", ":")).encode()).hexdigest()))

    def test_import_and_implementation_scope(self):
        tree = ast.parse(SOURCE.read_bytes())
        imports = [node.module for node in tree.body if isinstance(node, ast.ImportFrom)]
        self.assertEqual(imports, ["dataclasses"])
        self.assertFalse(any(isinstance(node, ast.Import) for node in ast.walk(tree)))
        forbidden = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                             and node.func.id in forbidden for node in ast.walk(tree)))
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                             and node.func.attr in {"decode", "encode"} for node in ast.walk(tree)))
        self.assertEqual(oracle.SPECIFICATION_SHA256, SPEC_SHA)
        self.assertEqual(oracle.CORPUS_SHA256, CORPUS_SHA)

    def test_invalid_request_types_leave_state_unchanged(self):
        class BytesSubclass(bytes):
            pass
        chunks = [None, "x", bytearray(b"x"), memoryview(b"x"), BytesSubclass(b"x"), 1]
        for setup in (b"", b"\xc2", b"\x80", b"A"):
            decoder = oracle.StrictUtf8Oracle()
            decoder.feed(setup, final=setup == b"A")
            for chunk in chunks:
                before = decoder.snapshot
                with self.assertRaisesRegex(TypeError, "^chunk_must_be_bytes$"):
                    decoder.feed(chunk, final=1)  # Chunk-type failure has precedence.
                self.assertIs(decoder.snapshot, before)
            for final in (0, 1, None, "true", 1.0):
                before = decoder.snapshot
                with self.assertRaisesRegex(TypeError, "^final_must_be_bool$"):
                    decoder.feed(b"", final=final)
                self.assertIs(decoder.snapshot, before)

    def test_successful_finalization_is_terminal(self):
        decoder = oracle.StrictUtf8Oracle()
        terminal = decoder.feed(b"A", final=True)
        for chunk in (b"", b"B", b"\xff"):
            with self.assertRaisesRegex(RuntimeError, "^decoder_already_finalized$"):
                decoder.feed(chunk)
            self.assertIs(decoder.snapshot, terminal)

    def test_snapshots_and_serializations_do_not_mutate_state(self):
        decoder = oracle.StrictUtf8Oracle()
        frame = decoder.feed(b"A\xc2")
        with self.assertRaises(FrozenInstanceError):
            frame.pending_hex = ""
        with self.assertRaises(AttributeError):
            decoder.snapshot = oracle.Snapshot()
        serialized = frame.to_dict()
        serialized["decoded_scalars"].append(999)
        serialized["emitted_scalars"].clear()
        serialized["pending_hex"] = "ff"
        next_frame = decoder.feed(b"\xa2", final=True)
        self.assertEqual(next_frame.decoded_scalars, (65, 162))
        self.assertEqual(frame.decoded_scalars, (65,))
        decoder = oracle.StrictUtf8Oracle()
        error = decoder.feed(b"A\xe0\x80")
        with self.assertRaises(FrozenInstanceError):
            error.error.byte_offset = 99
        copied = error.to_dict()
        copied["error"]["code"] = "changed"
        copied["decoded_scalars"].clear()
        after = decoder.feed(b"repair", final=True)
        self.assertEqual(after.error.code, "overlong_sequence")
        self.assertEqual(after.decoded_scalars, (65,))
        self.assertEqual(after.consumed_total, 2)
        self.assertEqual(after.examined_total, 3)

    def test_caller_serialization_cannot_forge_boolean_integer_equality(self):
        actual = oracle.StrictUtf8Oracle().feed(b"A", final=True).to_dict()
        for field in ("consumed_total", "examined_total", "consumed_in_chunk", "examined_in_chunk"):
            wrong = dict(actual, **{field: True})
            self.assertFalse(exact(actual, wrong), field)
            CONTROL_RESULTS.append(dict(control="integer_not_boolean", field=field, rejected=True))

    def test_frozen_golden_states_detect_meaningful_corruption(self):
        # These are checker corruption controls, not a claim of runtime mutation testing.
        for name, choose, field, mutate in [
            ("BOM_removed", lambda c: c["stratum"] == "BOM preservation", "decoded_scalars", lambda v: [x for x in v if x != 0xFEFF]),
            ("NUL_treated_as_sentinel", lambda c: c["id"] == "ascii/raw_nul", "decoded_scalars", lambda v: []),
            ("scalar_bits_wrong", lambda c: c["stratum"] == "Literal scalar boundaries", "decoded_scalars", lambda v: [v[0] ^ 1]),
            ("premature_EOF_accepted", lambda c: c["stratum"] == "Premature EOF", "status", lambda v: "finished"),
            ("offending_byte_consumed", lambda c: c["stratum"] == "Malformed byte sequences", "consumed_total", lambda v: v + 1),
            ("valid_prefix_discarded", lambda c: c["stratum"] == "Valid output before byte error", "decoded_scalars", lambda v: []),
            ("pending_bytes_lost", lambda c: c["stratum"] == "Every declared representative interior cut", "pending_hex", lambda v: ""),
        ]:
            case = next(c for c in CASES if choose(c))
            step = next(s for s in case["steps"]
                        if (field != "pending_hex" or s["expected"][field])
                        and (name != "BOM_removed" or 0xFEFF in s["expected"][field])
                        and (name != "valid_prefix_discarded" or s["expected"]["status"] == "error"))
            expected = step["expected"]
            changed = dict(expected, **{field: mutate(expected[field])})
            self.assertFalse(exact(expected, changed), name)
            CONTROL_RESULTS.append(dict(control=name, case=case["id"], field=field, rejected=True))


def main():
    global oracle, CASES, DEADLINE
    started = time.monotonic()
    DEADLINE = started + 20
    if REPORT.exists():
        raise RuntimeError("Pure proof already exists; do not overwrite")
    for path, expected in ((SOURCE, SOURCE_SHA), (CORPUS, CORPUS_SHA), (SPEC, SPEC_SHA),
                           (REFERENCE, REFERENCE_SHA), (DECISION, DECISION_SHA)):
        if pin(path)["sha256"] != expected:
            raise RuntimeError("Exact source/spec/reference/decision pin differs")
    CASES = json.loads(CORPUS.read_bytes())["cases"]
    assert len(CASES) == 107 and sum(len(c["steps"]) for c in CASES) == 167
    assert sum(len(bytes.fromhex(c["raw_hex"])) for c in CASES) == 354
    assert all(len(bytes.fromhex(c["raw_hex"])) <= 128 for c in CASES)
    sys.addaudithook(audit)
    spec = util.spec_from_file_location("independent_strict_utf8_oracle_v1", SOURCE)
    oracle = util.module_from_spec(spec)
    sys.modules[spec.name] = oracle
    spec.loader.exec_module(oracle)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OracleChecks))
    tick()
    record = dict(schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        status="passed" if result.wasSuccessful() and not DENIALS else "failed", helper=pin(SOURCE),
        checker=pin(__file__), specification=pin(SPEC), corpus=pin(CORPUS), reference=pin(REFERENCE),
        root_decision=pin(DECISION), tests=result.testsRun, fixtures=107, steps=167, supplied_bytes=354,
        failures=[dict(test=str(t), traceback=e) for t, e in result.failures],
        errors=[dict(test=str(t), traceback=e) for t, e in result.errors],
        case_results=TRACES, checker_corruption_controls=CONTROL_RESULTS, audit_denials=DENIALS,
        elapsed_seconds=time.monotonic()-started, budget_seconds=20, source_after=pin(SOURCE),
        implementation_basis="Frozen specification/corpus; independent reference checker source was not consumed",
        reference_scope="104 direct CPython paths plus3 RFC/certificate paths; not107directAPIagreement",
        scope="Pure fixed byte/chunk/API behavior only; no vendor/DLL/vocabulary/native/model/scientific qualification",
        old_payload_reads=0, SDK_constructors=0, native_calls=0, compiler_calls=0, default_application_changed=False,
        unittest_output=stream.getvalue())
    assert record["source_after"] == record["helper"]
    with REPORT.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(record, indent=2, sort_keys=True)+"\n")
    print(json.dumps(dict(status=record["status"], tests=result.testsRun, fixtures=107,
                         steps=167, proof=pin(REPORT), failures=len(result.failures), errors=len(result.errors))))
    return 0 if record["status"] == "passed" else 1


def tick():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError("Pure oracle check20s expired")


if __name__ == "__main__":
    raise SystemExit(main())
