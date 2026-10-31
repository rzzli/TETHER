"""Exact incremental v2 review: only the preserved synthetic peer probes."""
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


def write_new(name, value):
    with (HERE / name).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
    return pin(name)


def main():
    expected = {
        "captured_journal_v2.py": "d6c2f8ef61ffda069f7cbb41c5c06417d2e0fd530ce490e9488442131e385d91",
        "check_captured_journal_v2.py": "3bd8261596694995c40fc67d07f7cdeefd805b33ed5ea6522b7b723700f60609",
        "CAPTURED-JOURNAL-SOURCE-PURE-PROOF-v2.json": "3be62ccf191f57714c61760d44bb43928b23a692f528f8550bd348755c16a7a6",
        "CAPTURED-JOURNAL-CORRECTION-BINDING-v2.json": "a812e070abefdb71265f714e9445164b69792d4107ea2875b740b1e6f3689e64",
        "CAPTURED-JOURNAL-CONTRACT-v1.json": "2993cf83b8768f2324feb495bae65217d627135f0ce4d20fb341d537893d71ff",
        "CAPTURED-JOURNAL-FIXTURE-FREEZE-v1.json": "cd4f6b3f381a837d790dfcad84e92231111456e3eb6648a0ebd7617c84980140",
        "CAPTURED-JOURNAL-FIXTURES-v1.json": "1448873002dc5350be8ca835254ff283b734d04bda88382273b1c4b4319fe28c",
        "captured_journal_v1.py": "5b86f70a57dd1b51d7fe74829b032ddd954f656075ec585c062d5c6dc5e3cf37",
        "CAPTURED-JOURNAL-INDEPENDENT-PEER-v1.json": "d7b6c1d13e96ed6236b0a5acb9e3a37ef35ee9d36e4d87974f0ca26a53d5ae97",
        "check_captured_journal_peer_v1.py": "5fc7e50d0fcf9bc660d7110e9af7dbdda437715daa9160ce375804cd2f08a30c",
    }
    artifacts = {name: pin(name) for name in expected}
    assert all(artifacts[name]["sha256"] == sha for name, sha in expected.items())
    old = ast.parse((HERE / "captured_journal_v1.py").read_text(encoding="utf-8"))
    new = ast.parse((HERE / "captured_journal_v2.py").read_text(encoding="utf-8"))
    old_functions = {n.name: n for n in old.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    changed = [n.name for n in new.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
               and ast.dump(n, include_attributes=False) != ast.dump(old_functions[n.name], include_attributes=False)]
    assert changed == ["check_native_v7"]
    new.body[0] = old.body[0]
    new.body = [old_functions[n.name] if isinstance(n, ast.FunctionDef) and n.name == "check_native_v7" else n for n in new.body]
    assert ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False)
    spec = importlib.util.spec_from_file_location("incremental_journal_peer", HERE / "check_captured_journal_peer_v2.py")
    checker = importlib.util.module_from_spec(spec); sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    output = io.StringIO(); started = time.monotonic()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(checker.PeerChecks))
    elapsed = time.monotonic() - started
    assert result.testsRun == 7 and result.wasSuccessful()
    assert len(checker.REJECTED_PROBES) == 5 and not checker.FALSE_POSITIVES
    after = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status="ALL_PRESERVED_BOUNDED_PEER_PROBES_PASS_V2",
        source=artifacts["captured_journal_v2.py"], checker=pin("check_captured_journal_peer_v2.py"),
        methods=result.testsRun, failures=len(result.failures), errors=len(result.errors), elapsed_seconds=elapsed,
        output=output.getvalue(), formerly_accepted_contradictions_now_rejected=checker.REJECTED_PROBES,
        unchanged_frozen_baseline_expectations=30,
        no_additional_probe_families=True, old_replay_or_source_closure_or_native_calls=False)
    after_pin = write_new("CAPTURED-JOURNAL-INDEPENDENT-AFTER-PROOF-v2.json", after)
    peer = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status="CLEAR_SOURCE_PURE_JOURNAL_COMPONENT_ONLY_NO_LIVE_AUTHORITY",
        artifacts=artifacts, independent_after_proof=after_pin, recorder=pin(Path(__file__).name),
        source_delta=dict(changed_function="check_native_v7", other_module_AST_unchanged_except_docstring=True),
        resolved_before_findings=["terminal errors must be present and empty", "drain status/call count coherence",
                                  "strict integer polls_reserved", "required drain status/count fields",
                                  "observed_pipe_EOF nonempty calls require a final knownNone availability"],
        declared_field_checks_confirmed=["already_observed_EOF requireszero calls; observed_pipe_EOF requiresnonemptycalls",
            "strict perstream count and increasing poll ordinals plus contiguousglobalpolls",
            "availability/read invocation statusreturned and known attempt/call/return flags",
            "missing availability cannot substitute for knownNone; no earlierNone beforefinalcall",
            "read consume_error rejected; knownreadbytes cannot exceedretainedcapture",
            "optional aggregate polls isstrict; terminal Job invocation statusreturned"],
        scope="Same bounded chain/order/reference/counter/framing/deadline/immutability probes only; the author10method/13newcase proof is pinned but not re-executed here.",
        flags=dict(profile_qualified=False, resource_semantics_validated=False, owner_context_provenance_authenticated=False,
                   live_adapter_qualified=False, scientific_validation="not_established"),
        limitations=["Pure supplied bytes/bindings require future fresh source-bound owner context",
                     "Raw resource/PID/limits truth and profile correctness remain other gates",
                     "Explicit known-launched native-v7 policy only; future Unicode parent needs its own source/event-policy binding",
                     "No old run replay, original source closure, payload or SDK/native operations",
                     "V1source/proof/HOLD remain historical and are not rewritten or retroactively cleared"],
        material_blockers=[], previous_negative_and_timeout_unchanged=True)
    peer_pin = write_new("CAPTURED-JOURNAL-INDEPENDENT-PEER-v2.json", peer)
    print(json.dumps(dict(after_proof=after_pin, peer=peer_pin)))


if __name__ == "__main__":
    main()
