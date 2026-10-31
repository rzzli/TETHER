"""Root finite indexed-source authorization after pre-code tests and design review."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE_DIR = HERE.parent / "recovery-step9-indexed-accounting-20261029"
PINS = {
    "INDEXED-ACCOUNTING-SUCCESSOR-PROPOSAL-v1.json": "7e2b1b5b71095863ab687a92f8152239c2922f0bd8ada9c875562ec15d6d9a5b",
    "INDEXED-ACCOUNTING-APPEND-ENVELOPE-CLARIFICATION-v1.json": "147dc12855fe6f9bbd5b1994bc1e389b938cb03bdc25ddb1cf4137c5fc48cfd6",
    "INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v2.json": "cccf8a1f4f6219ff51ade0279e82f587cfbe76c969e1be69125c0cc72ff2a3bd",
    "indexed_accounting_controls_v2.py": "d76e1a2d7c70a9a42fa70c5f4989f08f2e291e79f12fa53b454250998c74bf5b",
    "INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v2.json": "52da9451c215d50f4b3e559a47eb4c286dd7e33fc884b8bf67430d9e6ac9703d",
    "INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v2.json": "24da94c6576a7d94ef1c88467e28a179ae4f57b7da6e0a6a885f1e836101ef7d",
    "INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-PEER-v2.json": "4f5d8553a9dcf4e48af2eb864bbbdac1d1c00ad2487eb573ff3fffee977f656f",
    "INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-HOLD-v1.json": "50eff232619227c3beeae736e9fac35910a29baf81d205f4e059e6b3bd50ea3a",
}


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    inputs = {}
    for name, digest in PINS.items():
        inputs[name] = pin(HERE / name)
        assert inputs[name]["sha256"] == digest, name
    peer = json.loads((HERE / "INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-PEER-v2.json").read_text(encoding="utf-8"))
    assert peer["status"] == "CLEAR_DESIGN_AND_PRECODE_CONTROLS_ONLY" and peer["material_blockers"] == []
    accepted = ROOT / "planning/review-assets/recovery-step9-shared-owner-20261029/SHARED-OWNER-SCOPED-ACCEPTANCE-v2.json"
    inputs[str(accepted.relative_to(ROOT))] = pin(accepted)
    assert inputs[str(accepted.relative_to(ROOT))]["sha256"] == "7e0d94849d5ba9da358167a9d103b44fa6ae25acc8e5bed646d2839162220344"
    sources = ("shared_owner_v3.py", "shared_file_ports_v3.py", "continue_verification_v3.py")
    assert not any((SOURCE_DIR / name).exists() for name in sources), "Tests must precede implementation."
    inputs[Path(__file__).name] = pin(Path(__file__))
    report = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FINITE_INDEXED_ACCOUNTING_SOURCE_PURE_IMPLEMENTATION_AUTHORIZED",
        "inputs": inputs, "source_directory": str(SOURCE_DIR.relative_to(ROOT)), "source_files": list(sources),
        "effective_design": "7e2b proposal plus147d append envelope; all current caps, public DATA, SourceV2 observations and48-history oracle unchanged.",
        "authorized": [
            "Create a separately versioned coherent three-module V3 source set; preserve accepted V2 and all first pre-code artifacts.",
            "Implement only canonical ordinal/file lookup, pre-invoke source-call indices and per-file reservation/known-read contributions; keep the authoritative raw record list and original owner/Origin/rights.",
            "Catch append plus index registration before invocation, including committed-append errors. Preserve unentered raw records and the same original fault; quarantine work with no rollback/retry or guessed entry.",
            "Store the first valid raw scalar/count before cache/auxiliary work. Guard all fold interruptions, preserve known lower bounds and idempotence, and prevent work after a dirty partial cache.",
            "Use one canonical O(N+r) read-only reporting/consistency projection; do not heal caches or hide a scan in read work. Cleanup derives known ownership directly and respects the original hard deadline.",
            "Run the frozen six-control indexed mode with real ledger instrumentation, the same48 histories/eight regressions/12+4 controls and strict snapshot validation. No source base-list bypass or fake metric window may hide scans.",
            "Freeze source/module/dependency maps before first V3 execution; preserve first source/harness failures and correct only through retained regression evidence and separately named coherent versions.",
            "Obtain a finite independent exact source/delta/test review before root acceptance, then update the full-project assessment/docs/memory/TODO."
        ],
        "limits": [
            "No public API/schema/oracle/cap/generation/role/packet/stream/query-storage/entry-kernel change or new public fault hook. CurrentN4/file4096/capture16384/R68/C92/E224/generation68 remain.",
            "Counter access metrics prove only bounded hot-path algorithm behavior. No physical timing, full-roster memory/performance or scientific fit follows.",
            "No actual Win32/FFI/SDK/C++/native/model/tokenizer/original-source/payload operation, old actual-run replay, download, paid query or production activation.",
            "Keep application0.3.11/defaultv2, current budgets, empty real prediction features/null probabilities, download worker and stopped monitor unchanged."
        ],
        "precode_chronology": "Frozen six-control v2 and actual accepted-V2 before evidence predate V3 source: four real hot-scan failures and two functional passes, zero errors. Earlier control-gap HOLD/proofs remain preserved.",
        "source_implementation_authorized": True, "component_accepted": False,
        "runtime_authorized": False, "FFI_registration_proven": False,
        "production_owner_bound": False, "originals_authenticated": False,
        "profile_qualified": False, "verification_complete": False,
        "scientific_validation": "not_established", "provider_spending": 0,
    }
    output = HERE / "INDEXED-ACCOUNTING-ROOT-SOURCE-SCOPE-v3.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "sha256": pin(output)["sha256"], "inputs": len(inputs)}))


if __name__ == "__main__":
    main()
