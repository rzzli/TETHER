"""Design metadata/delta recorder only; no file-port or Win32 implementation."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
OLD = HERE / "FILE-PORTS-DESIGN-CONTRACT-v1.json"
NEW = HERE / "FILE-PORTS-DESIGN-CONTRACT-v2.json"
FREEZE = HERE / "FILE-PORTS-DESIGN-FREEZE-v2.json"
PEER = HERE / "FILE-PORTS-INDEPENDENT-DESIGN-REVIEW-v2.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    if PEER.exists(): raise FileExistsError(PEER)
    old, new = json.loads(OLD.read_bytes()), json.loads(NEW.read_bytes())
    frozen = json.loads(FREEZE.read_bytes())
    assert pin(OLD)["sha256"] == "bc73427712614a6652e37924a6ff91646c1b8a881e5928cd98b200516bce7a05"
    assert pin(NEW)["sha256"] == "d2c775cb9e24dce90f2dc0cc97d7976567d94a1e147e1f57be72f7a5d21efd4d"
    assert pin(FREEZE)["sha256"] == "37db5004b81cf4069a9ecb5d0b23a1b6584dda039b2b82a0e85c36c512135b35"
    a, b = old["semantic_contract"], new["semantic_contract"]
    assert hashlib.sha256(canonical(b)).hexdigest() == new["semantic_sha256"] == frozen["semantic_sha256"]
    allowed = {"admission_formulas", "admitted_paths", "metadata_scans", "output", "port_design_id", "required_fake_vectors"}
    changed = {key for key in set(a) | set(b) if a.get(key) != b.get(key)}
    assert changed == allowed
    for key in set(a) - allowed: assert a[key] == b[key]
    for key in set(a["admission_formulas"]) - {"symbols"}:
        assert a["admission_formulas"][key] == b["admission_formulas"][key]
    for key in set(a["admission_formulas"]["symbols"]) - {"U"}:
        assert a["admission_formulas"]["symbols"][key] == b["admission_formulas"]["symbols"][key]
    assert set(b["admitted_paths"]) - set(a["admitted_paths"]) == {"metadata_directory_nodes", "long_path_limit"}
    for key in set(a["admitted_paths"]) - {"ancestor_index"}:
        assert a["admitted_paths"][key] == b["admitted_paths"][key]
    assert set(a["metadata_scans"]) == set(b["metadata_scans"])
    for key in set(a["metadata_scans"]) - {"ancestor_calls", "iterator"}:
        assert a["metadata_scans"][key] == b["metadata_scans"][key]
    assert set(b["output"]) - set(a["output"]) == {"late_known_write", "registry_only_observations"}
    for key in a["output"]: assert a["output"][key] == b["output"][key]
    assert b["required_fake_vectors"][:len(a["required_fake_vectors"])] == a["required_fake_vectors"]
    assert len(b["required_fake_vectors"]) - len(a["required_fake_vectors"]) == 5
    assert b["port_design_id"] == "finite-original-file-and-exclusive-sink-v2"
    root = b["admitted_paths"]["metadata_directory_nodes"]["drive_root"]
    pattern = re.compile(root["path_regex"])
    syntax = []
    for path, accepted in (("C:\\", True), ("D:\\", True), ("c:\\", False), ("d:\\", False),
                           ("C:", False), ("C:/", False), ("C:\\\\", False), ("C:\\leaf", False),
                           ("\\\\server\\share\\", False), ("\\\\?\\C:\\", False), ("C:\\ ", False)):
        observed = pattern.fullmatch(path) is not None
        assert observed == accepted
        syntax.append(dict(path=path, pattern_match=observed))
    # Syntax alone intentionally does not grant a new drive. The normative
    # derivation separately restricts the approved C/D roster; no port exists.
    assert pattern.fullmatch("E:\\") is not None
    assert root["utf16_units"] == 3
    assert set(root["exact_record_shape"]) == {"kind", "path"}
    assert root["exact_record_shape"]["kind"] == "canonical_drive_root"
    for key in ("original FileSpec", "output file leaf", "output namespace leaf", "scan root", "FindFirst/FindNext traversal"):
        assert key in root["prohibited_uses"]
    for key in ("author", "contract", "peer_basis", "prior_contract"):
        assert pin(Path(frozen[key]["path"])) == frozen[key]
    result = dict(schema_version=1, status="CLEAR_CORRECTED_DESIGN_ONLY_NO_PORT_IMPLEMENTATION",
        contract=pin(NEW), freeze=pin(FREEZE), predecessor=pin(OLD), prior_peer=frozen["peer_basis"],
        recorder=pin(Path(__file__).resolve()), semantic_sha256=new["semantic_sha256"], findings=[],
        prior_drive_root_gap_resolved=True, no_other_confirmed_material_design_discrepancy=True,
        verified_changed_semantic_top_fields=sorted(changed), unchanged_semantic_top_fields=sorted(set(a)-allowed),
        literal_regex_probes=syntax,
        syntax_is_not_roster_admission="E-root matches the general syntax but remains forbidden by the approved C/D ancestor derivation; no new drive discovery or file/scan role follows.",
        review_conclusions=[
            "Distinct CanonicalDriveRoot derives only from the approved finite C/D ancestor roster, is counted once in U, and authorizes only the existing ancestor attributes observation.",
            "The root descriptor is explicitly forbidden as original/output/namespace leaf, scan root, traversal or scan-discovered authority. Failed/undefined/late/unknown attributes block ancestry completion.",
            "Leaf grammar, roles, API/layout/flags, original inspection/read rules, clock/slot ownership, source/seal DAG, calls/events/output quotas and K/F_fixed lists are unchanged.",
            "Registry-only output observations, late-known-write/hash-pending and path-capacity-not-API-success statements match the prior reviewed clarifications and add no API/event allowance.",
            "Future implementation must use the root-specific validator/ASCII collision normalization rather than call the old file-leaf source_key on a root. This is an implementation watch point, not a remaining design contradiction."
        ],
        pending=["Root authorization and separately frozen closed literal/fault fixtures before source implementation",
                 "Exact future roster/event/API/report/capture fit; source/owner/loader/continuation integration",
                 "Typed ABI and harmless live file-port qualification; original source/path/lease authentication",
                 "All native/profile/resource/scientific authority"],
        activity=dict(design_metadata_reads_only=True, ctypes_or_SDK_constructions=0, Win32_API_calls=0,
                      source_qualification=False, CPU_GGUF_oldpack_operations=0, file_port_implementation=False),
        implementation_authorized=False, execution_authorized=False, profile_qualified=False)
    with PEER.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(result, out, indent=2); out.write("\n")
    print(json.dumps(dict(status=result["status"], peer_sha256=pin(PEER)["sha256"], regex_probes=len(syntax))))


if __name__ == "__main__":
    main()
