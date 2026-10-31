"""Root acceptance of literal preparation; authorize only the next pure source batch."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json": "90fc021a044bba34953a8f8f8e42b05f5d61f49da945044e1e108f92bb1fc3cd",
    "SHARED-OWNER-ROOT-PREPARATION-SCOPE-v2.json": "ba6328a7a22d43af33e1e1c15265cb87960fe3b1354bee0434474bedfd91fa16",
    "SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json": "50ee2d7a9285370e6a3f0d18801c43e441b327f7ceac9eb46ebdf0463eff28d6",
    "SHARED-OWNER-PUBLIC-DATA-INDEPENDENT-PEER-v2.json": "3b32ba1bb0f3ebbd33be91aeb190e86b4da575a05196ff5d9950c69c042d0f6a",
    "SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json": "34c3df0519df387e31439096b8c76e39fc3ce74437e1281346da58ab3a33952e",
    "SHARED-OWNER-INTEGRATION-FIXTURES-v3.json": "e12d6485d0bc38b38c5b4bf33edcab22c1471da15858718185f18f1b5179eee2",
    "SHARED-OWNER-INTEGRATION-LITERAL-PROOF-v3.json": "c76a7913a6a42c26b3f14d10f5a926de57f6ab2152225ba3fa0107b42f05513e",
    "SHARED-OWNER-INTEGRATION-FIXTURE-FREEZE-v3.json": "69dd02e73654094ec746ff710f49efd6259f5fa1785616e66f5e5d97d2da428e",
    "SHARED-OWNER-LITERAL-INDEPENDENT-PRECHECK-v2.json": "472105a3c18ad67bce7a2504a1b7cd8b2d142a87a139376245586a56435d43c9",
    "SHARED-OWNER-AUTHOR-CONTROL-TABLE-v1.json": "ac9ca49a703e348947ab000330c11a679c5eef111da2d84a54d1a07a554e9f8d",
}
PEER_NAME = "SHARED-OWNER-LITERAL-INDEPENDENT-PEER-v3.json"
PEER_SHA = "2d4fb217584d588d5343ec38a3b19b587dbf727091fd4c7bf9f8e727ea2d6e02"
SOURCE_FILES = ("shared_owner_v1.py", "shared_file_ports_v1.py", "continue_verification_v1.py")


def pin(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main():
    inputs = {}
    for name, expected in {**PINS, PEER_NAME: PEER_SHA}.items():
        inputs[name] = pin(HERE / name)
        assert inputs[name]["sha256"] == expected, name
    freeze = read("SHARED-OWNER-INTEGRATION-FIXTURE-FREEZE-v3.json")
    for record in freeze["pins"].values():
        path = Path(record["path"])
        assert path.resolve().parent == HERE
        assert pin(path) == {"bytes": record["bytes"], "sha256": record["sha256"]}, path.name
    proof = read("SHARED-OWNER-INTEGRATION-LITERAL-PROOF-v3.json")
    assert proof["status"] == "passed" and proof["methods"] == 8
    assert not proof["failures"] and not proof["errors"]
    assert proof["histories"] == 48 and proof["groups"] == 14
    fixture = read("SHARED-OWNER-INTEGRATION-FIXTURES-v3.json")
    assert len(fixture["cases"]) == 48
    assert len({case["id"] for case in fixture["cases"]}) == 48
    assert len({case["group"] for case in fixture["cases"]}) == 14
    assert all(flag is False for flag in fixture["qualification"].values())
    peer = read(PEER_NAME)
    assert peer["status"].startswith("CLEAR"), peer["status"]
    assert peer["material_blockers"] == []
    encoded_peer = json.dumps(peer, sort_keys=True)
    for name in ("SHARED-OWNER-INTEGRATION-FIXTURES-v3.json", "SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json", "SHARED-OWNER-INTEGRATION-FIXTURE-FREEZE-v3.json"):
        assert PINS[name] in encoded_peer
    assert all(not (HERE / name).exists() for name in SOURCE_FILES), "Sources must follow the frozen expectations."
    inputs[Path(__file__).name] = pin(Path(__file__))
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "LITERAL_PREPARATION_ACCEPTED_SOURCE_PURE_IMPLEMENTATION_AUTHORIZED",
        "inputs": inputs, "verified_freeze_pins": len(freeze["pins"]),
        "literal_histories": 48, "causal_groups": 14, "preparation_methods": 8,
        "code_files": list(SOURCE_FILES),
        "authorized": [
            "Implement exactly the three named inactive source components against the frozen DATA/public interfaces, not the fixtures or expected labels.",
            "Use one canonical owner/Origin/nonce/registry/output/early context/loader/journal from start; ports and continuation controller are non-owning views. Copy tested algorithms with new regressions; no old-owner constructor/reset/lease clone after handoff.",
            "Implement and execute the independent generic seven-API fake binding, fictional SinkSpy, callback/clock fixtures and actual shared-method tests for all48 frozen histories.",
            "Validate every actual issued snapshot against the complete closed DATA keys/types/enums/bounds before expected comparisons. Pythonbool must not pass an integer check. Compare actual object/exception identities externally.",
            "Execute the unchanged141B toy helper bodies with an actual in-memory CPython compiler/exec and the same closed captured-byte resolver. Parse the68B toy JSON. No prebuilt marker stub, filesystem helper import, undeclared dependency or cache fallback qualifies this test.",
            "Implement meaningful author controls from the12-row table and preserve first test failures, including three original raw-core regression families, strict domains, buffer lifetime, immutable diagnostics and original exception identity.",
            "Freeze code/dependencies/replay test inputs and retain the first full driver/author results. If a source or harness defect appears, keep its exact witness and separately named coherent successor with before/after regression evidence; do not rewrite expected outputs to fit code.",
            "Obtain exact independent source review after tests pass. Then retain a fresh full-project20-row reassessment and critical next actual-entry/FFI/source/format/resource/native gate; update TODO/docs/memory."
        ],
        "implementation_owners": {"source": "OS", "independent_driver": "Grammar", "source_peer": "Native"},
        "limits": [
            "Seven injected original-file APIs and ReadFile counts only; sink callbacks are fictional attempt/ack observations, not physical write/flush/close or durability.",
            "No real Win32/ctypes/SDK construction or invocation, C++/native compiler, CPU/GGUF/tokenizer/model/native calls, original-source closure qualification, old actual-run replay, downloads, paid queries or production activation.",
            "Real first-entry, full-roster/budget/time/process-memory fit and actual raw FFI/native-to-Python delivery remain unqualified. The interpreter-side hook cannot close that residual window.",
            "Fictional immutable sequence/ACK-prefix digest does not qualify a persisted hash-chain or actual new-parent journal/archive/resource format. Old known-v7 policies retain their scopes.",
            "Source guard/produced-payload checks do not claim an isolated public8193-byte/repeated-kind refusal probe. Compound foreign/cap cases do not prove every isolated predicate.",
            "Current application0.3.11/defaultv2, budget defaults, empty real prediction features/null probabilities, download worker and stopped monitor remain unchanged. Provider spending stays0."
        ],
        "source_implementation_authorized": True,
        "actual_API_calls_so_far": 0, "original_or_payload_operations": 0,
        "runtime_authorized": False, "FFI_registration_proven": False,
        "production_owner_bound": False, "originals_authenticated": False,
        "profile_qualified": False, "real_checkers_bound": False,
        "verification_complete": False, "scientific_validation": "not_established",
        "preserved": "Every draft, v1/v2 literal candidate/freeze,6method proof,472105 two-closure HOLD, earlier DATA/design HOLD and accepted source component remains unchanged. v3 adds only the62 approved checks and closed harness semantics."
    }
    output = HERE / "SHARED-OWNER-ROOT-SOURCE-SCOPE-v1.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "sha256": pin(output)["sha256"], "inputs": len(inputs), "freeze_pins": result["verified_freeze_pins"]}))


if __name__ == "__main__":
    main()
