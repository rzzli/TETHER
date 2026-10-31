"""Focused pure compile-preparation/finalizer faults; no compiler/child/target API."""
import ast
from contextlib import contextmanager
from importlib import util
import json
from pathlib import Path
import struct
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "build_typed_abi_bridge_v4.py"
spec = util.spec_from_file_location("own_typed_abi_build_v4_pure", SOURCE)
h = util.module_from_spec(spec); spec.loader.exec_module(h)
frozen = h.basis()  # Accepted Python declarations only; no stable_files/tool call.
OLD = json.loads(h.OLD_PROTOCOL.read_bytes())
ROOT = h.ROOT / "data/cache" / ("r09-typed-ABI-build-v4-pure-" + str(time.time_ns()))
ROOT.mkdir()
DENIED = []
def guard(event, args):
    if event in ("subprocess.Popen", "os.system", "ctypes.dlopen", "socket.__new__", "socket.connect", "socket.getaddrinfo"):
        DENIED.append(event); raise RuntimeError("Pure build tests cannot dispatch/load/connect")
sys.addaudithook(guard)


class Leases:
    def __init__(self, fail=False): self.closed = False; self.calls = 0; self.fail = fail
    def close(self):
        self.closed = True; self.calls += 1
        if self.fail: raise OSError("Synthetic lease context close failure")


def fixture(name, *, primary=False, close_fail=False):
    output = ROOT / name
    journal = frozen.RunJournal(output, kind="build")
    (output / "synthetic-artifact.bin").write_bytes(b"own authored fake artifact; not a PE")
    result = dict(status="failed" if primary else h.STATUS, commands=[], pure_fixture=True,
                  executable_executions=0, target_DLL_loads=0)
    if primary:
        result["failure"] = dict(error_class="SyntheticPrimary", message="preserve primary")
        frozen.write_new(output / "failure.json", dict(authoritative=True, **result["failure"]))
    state = dict(dispatches=0, denied=[])
    return output, journal, result, state, Leases(close_fail)


def finish(parts):
    output, journal, result, state, leases = parts
    return h.finalize(frozen, output, result, state, journal, leases,
                      time.monotonic()+20, time.monotonic(), "a"*64)


def minimal_config(name):
    prepared = ROOT / (name + "-prepared"); prepared.mkdir()
    output = ROOT / name
    selected, _ = h.filtered_basis_inputs(OLD, frozen)
    paths = h.extra_input_paths()+[prepared/name for name in ("typed_public_c_recognizer.cpp","recognizer_runtime_pins.hpp")]
    paths += [prepared/"headers"/Path(row["copied"]["path"]).name for row in OLD["headers"]]
    records = {str(Path(row["path"])):row for row in selected}
    for path in paths:
        records.setdefault(str(path),dict(path=str(path),bytes=0,sha256="0"*64))
    value = dict(kind="typed_ABI_bridge_v4_build_recognition_disabled", helper=frozen.pin(SOURCE),
        source=frozen.pin(h.SOURCE), design=frozen.pin(h.DESIGN), limits=h.LIMITS,
        recognition_enabled=False, expected_version="", execute_result=False,
        header=dict(sha256=h.HEADER_SHA), prepared=str(prepared), output=str(output),
        commands=h.commands(frozen, prepared, output, OLD), environment=frozen.build_environment(OLD["environment"], output),
        inputs=list(records.values()), process_scope="Launched compiler/linker handles only; descendants not independently attested")
    return value


def synthetic_PE(*, address=0x1200, names=1, ordinal=0):
    raw = bytearray(2048); raw[:2] = b"MZ"
    def put(offset, form, value): struct.pack_into(form, raw, offset, value)
    put(0x3c, "<I", 0x80); raw[0x80:0x84] = b"PE\0\0"
    put(0x84, "<H", 0x8664); put(0x86, "<H", 1); put(0x94, "<H", 240)
    put(0x98, "<H", 0x20b); put(0x108, "<I", 0x1000); put(0x10c, "<I", 0x180)
    section = 0x188; put(section+8, "<I", 0x400); put(section+12, "<I", 0x1000)
    put(section+16, "<I", 0x400); put(section+20, "<I", 0x400)
    for offset, value in ((20,1),(24,names),(28,0x1040),(32,0x1044),(36,0x1048)):
        put(0x400+offset, "<I", value)
    put(0x440, "<I", address); put(0x444, "<I", 0x1080); put(0x448, "<H", ordinal)
    raw[0x480:0x488] = b"example\0"; raw[0x490:0x49b] = b"other.name\0"
    return bytes(raw)


class Checks(unittest.TestCase):
    def test_frozen_tool_identity_and_finalizer_pattern(self):
        self.assertEqual(h.sha(h.BASIS), h.BASIS_SHA)
        self.assertEqual(h.sha(h.FINALIZER_BASIS), h.FINALIZER_BASIS_SHA)
        def body(path):
            return next(n for n in ast.parse(path.read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == "finalize")
        actual = body(SOURCE)
        for node in ast.walk(actual):
            if isinstance(node, ast.Constant) and node.value == "typed_ABI_bridge_v4_build_terminal":
                node.value = "own_harmless_build_terminal"
        self.assertEqual(ast.dump(actual, include_attributes=False), ast.dump(body(h.FINALIZER_BASIS), include_attributes=False))

    def test_filtered_input_selection_never_selects_CPU_model_or_pack(self):
        selected, excluded = h.filtered_basis_inputs(OLD, frozen)
        self.assertTrue(any(Path(r["path"]).name == "ggml-cpu-x64.dll" for r in excluded))
        self.assertFalse(any(Path(r["path"]).name == "ggml-cpu-x64.dll" or Path(r["path"]).suffix.casefold() == ".gguf" for r in selected))
        self.assertFalse(any("00-roundtrip" in r["path"] for r in selected))
        self.assertEqual({Path(r["path"]).name for r in selected if Path(r["path"]).parent == frozen.RUNTIME}, h.CORE_NAMES)
        self.assertEqual(len({r["path"] for r in selected}), len(selected))

    def test_exact_source_map_and_actual_four_core_exports(self):
        rows = h.source_checks(); self.assertEqual(len(rows), 25)
        tables = h.export_tables(OLD); self.assertEqual(set(tables), h.CORE_NAMES)
        h.verify_export_mapping(rows, tables)
        for row in rows:
            if row["owner"] == "ggml-base.dll":
                wrong = [{**r, "owner":"ggml.dll"} if r is row else r for r in rows]
                with self.assertRaises(RuntimeError): h.verify_export_mapping(wrong, tables)

    def test_missing_duplicate_zero_and_forwarded_export_rejected(self):
        rows = h.source_checks()
        tables = {r["owner"]:{} for r in rows}
        for row in rows: tables[row["owner"]][row["symbol"]] = dict(rva=1,forwarder=None)
        for value in (None, dict(rva=0,forwarder=None), dict(rva=1,forwarder="other.symbol")):
            changed = {owner:dict(names) for owner,names in tables.items()}
            if value is None: del changed[rows[0]["owner"]][rows[0]["symbol"]]
            else: changed[rows[0]["owner"]][rows[0]["symbol"]] = value
            with self.assertRaises(RuntimeError): h.verify_export_mapping(rows, changed)
        with self.assertRaises(RuntimeError): h.verify_export_mapping(rows[:-1]+[rows[0]], tables)

    def test_PE_reader_bounds_ordinal_and_forwarder(self):
        self.assertEqual(h.named_exports(synthetic_PE())["example"], dict(rva=0x1200,forwarder=None))
        self.assertEqual(h.named_exports(synthetic_PE(address=0x1090))["example"]["forwarder"], "other.name")
        for raw in (b"bad", synthetic_PE(names=65537), synthetic_PE(ordinal=2), synthetic_PE()[:0x450]):
            with self.assertRaises((RuntimeError,UnicodeError)): h.named_exports(raw)

    def test_commands_and_limits_unchanged_compile_link_only(self):
        c = minimal_config("commands"); steps = c["commands"]
        self.assertEqual([r["seconds"] for r in steps], [45,10]); self.assertEqual(h.LIMITS, frozen.LIMITS)
        self.assertTrue(all(flag in steps[0]["argv"] for flag in ("/MD","/W4","/WX","/c")))
        self.assertEqual(Path(steps[0]["argv"][0]).name, "cl.exe"); self.assertEqual(Path(steps[1]["argv"][0]).name, "link.exe")
        self.assertIn('/DR09_PIN_HEADER="recognizer_runtime_pins.hpp"', steps[0]["argv"])
        self.assertFalse(c["execute_result"]); self.assertFalse(c["recognition_enabled"])
        h.validate_config(c, frozen, OLD)
        c["commands"][0]["argv"].append("/UNREVIEWED")
        with self.assertRaises(RuntimeError): h.validate_config(c, frozen, OLD)

    def test_existing_output_and_recognition_scope_rejected(self):
        c = minimal_config("consumed"); Path(c["output"]).mkdir()
        with self.assertRaises(RuntimeError): h.validate_config(c, frozen, OLD)

    def test_CPU_or_model_injection_rejected_before_any_input_read(self):
        for name in ("ggml-cpu-x64.dll", "model.gguf", "unlisted-pack.bin"):
            c = minimal_config("inject-"+name.replace(".","-"))
            c["inputs"].append(dict(path=str(frozen.RUNTIME/name),bytes=0,sha256="0"*64))
            with self.assertRaises(RuntimeError): h.validate_config(c, frozen, OLD)
        c = minimal_config("missing-input");c["inputs"].pop()
        with self.assertRaises(RuntimeError): h.validate_config(c, frozen, OLD)
        c = minimal_config("wrong-role"); c["recognition_enabled"] = True
        with self.assertRaises(RuntimeError): h.validate_config(c, frozen, OLD)

    def test_PE_policy_no_target_network_process_or_delays(self):
        h.pe_policy({"KERNEL32.dll":["GetProcAddress","ReadProcessMemory"],"ucrt.dll":["_execute_onexit_table"]}, {})
        for ordinary, delayed in (({"llama.dll":[]},{}),({"KERNEL32.dll":["CreateProcessW"]},{}),
                                  ({"WINHTTP.dll":[]},{}),({"KERNEL32.dll":[]},{"anything":[]})):
            with self.assertRaises(RuntimeError): h.pe_policy(ordinary, delayed)

    def test_success_context_cleanup_and_complete_seal(self):
        parts = fixture("seal-success"); self.assertTrue(finish(parts)); self.assertTrue(parts[-1].closed)
        output = parts[0]; seal = json.loads((output/"terminal-seal.json").read_bytes())
        self.assertEqual(seal["status"], h.STATUS); self.assertTrue(seal["complete_output_universe"])
        self.assertIn("context-manager", seal["cleanup_scope"])

    def test_existing_primary_plus_late_close_failure_preserved(self):
        parts = fixture("primary-close", primary=True, close_fail=True)
        before = (parts[0]/"failure.json").read_bytes(); self.assertFalse(finish(parts))
        self.assertEqual((parts[0]/"failure.json").read_bytes(), before); self.assertEqual(parts[-1].calls,1)
        cleanup = json.loads((parts[0]/"post-lease-cleanup.json").read_bytes())
        self.assertFalse(cleanup["close_returned"]); self.assertIn("Synthetic",cleanup["close_error"]["error"])
        self.assertTrue((parts[0]/"late-failure.json").exists())
        self.assertEqual(json.loads((parts[0]/"terminal-seal.json").read_bytes())["status"], "failed")

    def test_early_publication_failure_still_closes_and_supplements(self):
        parts = fixture("early-publication"); original = frozen.write_new
        def fail(path, value):
            if Path(path).name == "build-report.json": raise OSError("Synthetic early publication failure")
            return original(path,value)
        with patch.object(frozen,"write_new",side_effect=fail): self.assertFalse(finish(parts))
        self.assertTrue(parts[-1].closed); self.assertTrue((parts[0]/"post-lease-cleanup.json").exists())
        self.assertTrue((parts[0]/"late-failure.json").exists())

    def test_postcleanup_inventory_failure_cannot_hide_close(self):
        parts = fixture("inventory-failure"); original = frozen.hash_file
        def fail(path, deadline):
            if parts[-1].closed: raise OSError("Synthetic postcleanup inventory failure")
            return original(path,deadline)
        with patch.object(frozen,"hash_file",side_effect=fail): self.assertFalse(finish(parts))
        self.assertTrue(parts[-1].closed); self.assertTrue((parts[0]/"late-failure.json").exists())
        self.assertFalse(json.loads((parts[0]/"terminal-seal.json").read_bytes())["complete_output_universe"])

    def test_seal_publication_failure_has_authoritative_marker(self):
        parts = fixture("seal-publication"); original = frozen.write_new
        def fail(path,value):
            if Path(path).name == "terminal-seal.json": raise OSError("Synthetic seal write failure")
            return original(path,value)
        with patch.object(frozen,"write_new",side_effect=fail): self.assertFalse(finish(parts))
        self.assertTrue(parts[-1].closed); self.assertFalse((parts[0]/"terminal-seal.json").exists())
        self.assertTrue((parts[0]/"post-seal-failure.json").exists())

    def test_postseal_deadline_vetoes_earlier_success(self):
        parts = fixture("postseal-deadline"); original = frozen.deadline_check
        def expire(deadline):
            if (parts[0]/"terminal-seal.json").exists(): raise TimeoutError("Synthetic postseal deadline")
            return original(deadline)
        with patch.object(frozen,"deadline_check",side_effect=expire): self.assertFalse(finish(parts))
        self.assertEqual(json.loads((parts[0]/"terminal-seal.json").read_bytes())["status"], h.STATUS)
        self.assertTrue((parts[0]/"post-seal-failure.json").exists())

    def test_fake_compile_failure_runs_hardened_finalization(self):
        c = minimal_config("fake-compile-failure")
        protocol = ROOT/"fake-build-protocol.json"; protocol.write_bytes(frozen.canonical(c)+b"\n")
        @contextmanager
        def fake_leases(*args,**kwargs): yield
        def no_compile(*args,**kwargs): raise RuntimeError("Synthetic compiler boundary failure; no child")
        with patch.object(h,"PROTOCOL",protocol),patch.object(h,"accepted",return_value=OLD), \
             patch.object(frozen,"audit"),patch.object(frozen,"stable_files",side_effect=fake_leases), \
             patch.object(frozen,"run_tool",side_effect=no_compile),patch.object(h,"basis",return_value=frozen), \
             patch.object(h,"verify_pins"):
            self.assertEqual(h.build(h.sha(protocol)),1)
        output=Path(c["output"]);self.assertTrue((output/"post-lease-cleanup.json").exists())
        self.assertEqual(json.loads((output/"terminal-seal.json").read_bytes())["status"],"failed")
        self.assertIn("Synthetic compiler boundary",json.loads((output/"failure.json").read_bytes())["message"])


if __name__ == "__main__":
    if h.PURE.exists(): raise RuntimeError("Pure proof exists; retain it and use a separate new version")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    proof = dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed", helper_sha256=h.sha(SOURCE),
        checker_sha256=h.sha(__file__),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        actual_compiler_dispatches=0,actual_children=0,target_DLL_loads=0,CPU_binary_reads=0,GGUF_model_reads=0,
        denied_real_operations=DENIED,output=str(ROOT),
        scope="Own fake compiler/leases/finalizer plus bounded source/PE data; no build or target execution")
    with h.PURE.open("x",encoding="utf-8") as stream: json.dump(proof,stream,indent=2);stream.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
