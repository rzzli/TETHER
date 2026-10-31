"""Retain new source/pure evidence only, never old archive/input/payload bytes."""
import ast
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import unittest

HERE = Path(__file__).parent


def pin(name):
    path = HERE / name
    raw = path.read_bytes()
    return dict(path=str(path.absolute()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    spec = importlib.util.spec_from_file_location("bootstrap_interface_checks", HERE / "check_verifier_bootstrap_interfaces_v1.py")
    checker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    source = (HERE / "verifier_bootstrap_interfaces_v1.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [n.module if isinstance(n, ast.ImportFrom) else n.names[0].name for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert imports == ["dataclasses", "hashlib", "math", "types"]
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("open", "exec", "eval", "compile", "__import__") for n in ast.walk(tree))
    text = io.StringIO()
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=text, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(checker.Checks))
    elapsed = time.monotonic() - started
    assert result.wasSuccessful() and result.testsRun == 20
    bindings = [pin(n) for n in (
        "VERIFIER-INTERFACE-SOURCE-IMPLEMENTATION-DECISION-v1.json",
        "VERIFIER-ADAPTER-DESIGN-CONTRACT-v1.json",
        "VERIFIER-ADAPTER-PLATFORM-CLARIFICATION-v1.json",
        "VERIFIER-ADAPTER-INDEPENDENT-DESIGN-REVIEW-v1.json",
        "ROOT-DESIGN-REVIEW-v1.md")]
    record = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status="PURE_ORIGIN_HANDOFF_INTERFACES_PASS_INDEPENDENT_SOURCE_REVIEW_PENDING",
        source=pin("verifier_bootstrap_interfaces_v1.py"), checker=pin("check_verifier_bootstrap_interfaces_v1.py"),
        recorder=pin(Path(__file__).name), design_and_approval_bindings=bindings,
        methods=result.testsRun, failures=len(result.failures), errors=len(result.errors), elapsed_seconds=elapsed,
        output=text.getvalue(), source_imports=imports,
        scope="Injected clock/ports/sink/compiler and synthetic Python bytes only. Test-module imports precede the injected origin: these tests do NOT establish a real first-clock bootstrap.",
        critical_observations=[
            "Original t0/work/hard deadlines and exact owner/slot/context objects survive one-time handoff without new original opens/hashes",
            "Setup/source-load lateness cannot reset t0; numeric/foreign/serialized or repeated origins/handoffs cannot supply completed evidence",
            "Known owned raw returns survive deliberate allocation/identity failures; null/failure/unreturned opens never guess cleanup ownership",
            "Defined read counts survive copy/digest/post-return timeout; known and hashed bytes plus pending unknown tails stay distinct",
            "Central bootstrap failure cleanup uses original source-bound closer and closes uncertain handles once only",
            "Current source context/roster/live leases are required; foreign contexts and expired/closed slots reject before compiler",
            "Finite dependency/stdlib map and captured bytes only; no own sys.modules/default import/path fallback",
            "Compiler returns can be retained late but cannot become loaded-module authority after expiry; failed/unknown compilation cannot retry",
            "All snapshots deny evidence completion and real profile qualification even when a stub returns passed/ready"],
        prototype_bounds=dict(declared_sources=16, joint_admitted_sources_at_most=12, events=128,
                              event_rule="10*N+8<=128", capture_bytes=67108864, chunk_bytes=65536,
                              full_live_roster_and_joint_budget="pending separately, unchanged256/2048 live design limits"),
        not_performed=dict(old_original_or_source_rehashes=0, CPU_GGUF_pack_operations=0,
                           live_filesystem_or_ctypes_or_SDK_calls=0, target_or_compiler_dispatches=0,
                           reviewed_old_helpers_executed=0, runtime_protocols_created=0),
        pending=["real first-clock entry before importing this component", "production verifier engine-v2 continuation integration",
                 "real source-bound loader/compiler and exact authority/roster/call/event budgets",
                 "real stream/metadata/output platform adapters", "real archive/journal/resource/core checker bindings",
                 "live qualification and any new runtime permission"],
        previous_negative_and_timeout_unchanged=True, author_self_clearance=False)
    raw = (json.dumps(record, indent=2, allow_nan=False) + "\n").encode("utf-8")
    out = HERE / "VERIFIER-BOOTSTRAP-INTERFACES-PURE-PROOF-v1.json"
    with out.open("xb") as stream:
        stream.write(raw)
    print(json.dumps(pin(out.name)))


if __name__ == "__main__":
    main()
