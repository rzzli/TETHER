"""Independent replay of two corrected ordinary-interface probes; injected objects only."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
import types

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "verifier_bootstrap_interfaces_v2.py"
SOURCE_SHA = "d937599212133ee7c036ee863b8c751885ffe60f7d657ec1ed5e506bf90c74eb"
REPORT = HERE / "VERIFIER-BOOTSTRAP-PEER-FAULTS-AFTER-v2.json"
BODY = b"VALUE=7\n"
PATH = "C:/synthetic/a.py"  # Opaque fake label; never inspected as a filesystem path.
DENIED = []


def guard(event, args):
    if event.startswith(("socket.", "subprocess.", "ctypes.dlopen", "os.system")):
        DENIED.append(event)
        raise RuntimeError("Pure peer probe forbids live/native/network/process calls")
    if event == "open" and isinstance(args[0], (str, bytes)):
        value = str(args[0]).lower().replace("/", "\\")
        if value.endswith((".gguf", ".dll", ".pyd", ".pack")) or "\\data\\benchmark\\" in value or value.startswith("c:\\synthetic\\"):
            DENIED.append("protected_or_fake_path_open")
            raise RuntimeError("No target/oldpayload/fake-file inspection")


class Clock:
    def __call__(self): return 1000.0


class Sink:
    def __init__(self): self.rows = []
    def reserve(self, nonce): return nonce
    def append(self, row): self.rows.append(copy.deepcopy(row))


class OriginalPort:
    def __init__(self, module):
        self.module, self.opens, self.reads, self.closes = module, 0, 0, 0
    def acquire(self, slot, claim):
        self.opens += 1
        slot.observe_owned_open(object())
    def inspect(self, slot, claim):
        return self.module.IdentityReturn(claim.path, claim.size, True, False)
    def read(self, slot, count):
        self.reads += 1
        slot.observe_read(True, len(BODY))
        return BODY
    def close(self, slot):
        self.closes += 1
        slot.observe_close(True)


class ForeignReader:
    def __init__(self): self.reads = 0
    def read(self, slot, count):
        self.reads += 1
        slot.observe_read(True, len(BODY))
        return BODY


def foreign_port_probe(v):
    original, foreign, retained = OriginalPort(v), ForeignReader(), {}
    claim = v.SourceClaim(PATH, len(BODY), hashlib.sha256(BODY).hexdigest())
    def setup(owner):
        retained["owner"] = owner
        owner.admit_sources((claim,)); owner.reserve_output(Sink())
        slot = owner.acquire(claim, original)
        event_count = len(owner.events)
        try:
            owner.capture(slot, foreign)
        except RuntimeError as error:
            assert str(error) == "Only original source-bound read port"
        else:
            raise AssertionError("Foreign read port unexpectedly accepted")
        assert foreign.reads == original.reads == 0
        assert not slot.hash_attempted and slot.read_attempts == slot.known_bytes == slot.hashed_bytes == 0
        assert len(owner.events) == event_count and owner._port is original and slot.owned
        retained["rejected_before_mutation"] = True
        captured, digest = owner.capture(slot, original)
        assert captured == BODY and digest == claim.sha256 and slot.hash_complete
        return owner.snapshot()
    snapshot = v.start_injected(Clock(), setup)
    owner = retained["owner"]; owner.close_all(original)
    assert foreign.reads == 0 and original.reads == 1 and original.opens == original.closes == 1
    assert snapshot["verification_complete"] is False and snapshot["real_profile_qualified"] is False
    return dict(corrected=True, foreign_read_calls=foreign.reads, original_read_calls=original.reads,
        rejected_before_hash_state_events_or_reads=retained["rejected_before_mutation"],
        original_open_close_calls=[original.opens, original.closes],
        runtime_qualification_flags=[snapshot["verification_complete"], snapshot["real_profile_qualified"]])


def snapshot_alias_probe(v):
    original, retained = OriginalPort(v), {}
    claim = v.SourceClaim(PATH, len(BODY), hashlib.sha256(BODY).hexdigest())
    def setup(owner):
        retained["owner"] = owner
        owner.admit_sources((claim,)); owner.reserve_output(Sink()); owner.capture_all(original)
        engine = owner.handoff().claim()
        loader = v.CapturedLoader(engine, (v.ModuleRule("sample", PATH, ()),), (),
            lambda name, raw, importer: {"module": name, "byte_count": len(raw)})
        loader.load("sample")  # Fake callback; no source compilation/exec.
        owner.error(RuntimeError("original diagnostic"), "fixture")
        owner.errors[0]["nested"] = {"rows": [{"value": 1}], "tuple": ({"value": 2},)}
        owner.compile_records[0]["nested"] = {"rows": [{"value": 3}]}
        return engine
    engine = v.start_injected(Clock(), setup)
    owner = retained["owner"]
    before = copy.deepcopy(owner.snapshot())
    exposed = engine.snapshot()
    exposed["primary_error"]["error"] = "changed through returned snapshot"
    exposed["errors"][0]["phase"] = "changed_phase"
    exposed["compile_records"][0]["state"] = "changed_compile_state"
    exposed["primary_error"]["nested"]["rows"][0]["value"] = 100
    exposed["errors"][0]["nested"]["tuple"][0]["value"] = 200
    exposed["compile_records"][0]["nested"]["rows"][0]["value"] = 300
    # Controls show the failure is nested aliasing, not replacement of copied lists/files.
    exposed["errors"].append({"unrelated": True})
    exposed["files"][0]["known_bytes"] = 999
    after = owner.snapshot()
    assert after["primary_error"] == before["primary_error"]
    assert after["errors"] == before["errors"]
    assert after["compile_records"] == before["compile_records"]
    assert len(owner.errors) == 1 and owner.slots[0].known_bytes == len(BODY)
    engine.close()
    assert original.closes == 1
    return dict(corrected=True, original_primary=before["primary_error"], retained_primary=after["primary_error"],
        original_compile=before["compile_records"], retained_compile=after["compile_records"],
        all_nested_owner_diagnostics_unchanged=True, copied_outer_list_control=True, copied_file_row_control=True,
        fake_compiler_callbacks=1, captured_source_exec_or_compiles=0, original_close_calls=original.closes,
        runtime_qualification_flags=[after["verification_complete"], after["real_profile_qualified"]])


def main():
    started = time.monotonic()
    assert sys.flags.isolated and sys.dont_write_bytecode and not REPORT.exists()
    sys.addaudithook(guard)
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA
    original = (HERE / "verifier_bootstrap_interfaces_v1.py").read_bytes()
    assert hashlib.sha256(original).hexdigest() == "4c5c0ee62c5663e7666094fdccfcd110ab1ed77b420dfc6c6499a12d7a899966"
    old, normalized = ast.parse(original), copy.deepcopy(ast.parse(raw))
    old_owner = next(n for n in old.body if isinstance(n, ast.ClassDef) and n.name == "BootstrapOwner")
    old_methods = {n.name: n for n in old_owner.body if isinstance(n, ast.FunctionDef)}
    normalized.body = [n for n in normalized.body if not (isinstance(n, ast.FunctionDef) and n.name == "_copy_diagnostics")]
    owner_class = next(n for n in normalized.body if isinstance(n, ast.ClassDef) and n.name == "BootstrapOwner")
    for index, method in enumerate(owner_class.body):
        if isinstance(method, ast.FunctionDef) and method.name == "capture":
            guard_call = ast.unparse(method.body[1])
            assert guard_call == "need(port is self._port, 'Only original source-bound read port')"
            method.body.pop(1)
            assert ast.dump(method, include_attributes=False) == ast.dump(old_methods["capture"], include_attributes=False)
        if isinstance(method, ast.FunctionDef) and method.name == "snapshot":
            owner_class.body[index] = copy.deepcopy(old_methods["snapshot"])
    assert ast.dump(normalized, include_attributes=False) == ast.dump(old, include_attributes=False)
    module = types.ModuleType("peer_frozen_bootstrap_v2"); module.__file__ = str(SOURCE)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(SOURCE), "exec"), module.__dict__)
    foreign = foreign_port_probe(module)
    alias = snapshot_alias_probe(module)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA and time.monotonic()-started < 20
    proof = dict(schema_version=1, status="passed_two_scoped_corrections_not_live_qualification", source_sha256=SOURCE_SHA,
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), foreign_read_port=foreign, snapshot_nested_alias=alias,
        elapsed_seconds=time.monotonic()-started, budget_seconds=20, audit_denials=DENIED,
        scope="Injected pure source interface/clock/slots/sink/fake callbacks only; no live adapter, evidence qualification or runtime-success exploit",
        synthetic_original_path_opens=0, live_filesystem_port_calls=0, target_SDK_calls=0, native_compiler_calls=0, CPU_GGUF_oldpack_operations=0,
        normalized_AST_delta_only_expected_methods_and_helper=True,
        preserved_before_proof_sha256="030ade7137ac35f68ed5966d2ec1de04507ac290c4b16c0db8ecb69f48e6c05c")
    with REPORT.open("x", encoding="utf-8", newline="\n") as stream: json.dump(proof, stream, indent=2); stream.write("\n")
    print(json.dumps(dict(status=proof["status"], foreign_port_corrected=foreign["corrected"], alias_corrected=alias["corrected"])))


if __name__ == "__main__": main()
