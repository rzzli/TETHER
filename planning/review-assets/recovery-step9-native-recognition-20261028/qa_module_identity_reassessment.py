"""Text and retained-data QA only; no SDK/target/helper invocation."""
import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(r"D:\Projects\drug_target_agents")
PHASE = ROOT / "planning/review-assets/recovery-step9-native-recognition-20261028"
DOC = ROOT / "planning/Project Progress Reassessment 2026-10-29 - Module Identity.md"
RUN = ROOT / "data/cache/r09-detached-ABI-observation-v3-20261029T001629Z"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    text = DOC.read_bytes().decode("utf-8", errors="strict")
    assert not text.startswith("\ufeff") and "\ufffd" not in text
    assert "29 October 2026 UTC / 28 October Los Angeles" in text
    rows = re.findall(r"^\| (R\d\d|HR[1-4]) \|", text, re.M)
    assert rows == [f"R{i:02d}" for i in range(1, 17)] + [f"HR{i}" for i in range(1, 5)]
    assert re.findall(r"^([1-6])\. \*\*", text, re.M) == list("123456")
    links = []
    for label, target in re.findall(r"\[([^\]]+)\]\((<[^>]+>|[^)]+)\)", text):
        target = target.strip("<>")
        assert not target.startswith(("http:", "https:"))
        path = (DOC.parent / target.split("#", 1)[0]).resolve()
        assert path.is_file(), (label, str(path))
        links.append({"label": label, "path": str(path)})
    evidence = {
        PHASE / "DETACHED-ABI-V3-RESULT-VERIFICATION.json": "a92b92376c090401a70fd5ab0e699d0bd02b478b1d3490b9a64817d30cc34221",
        PHASE / "TYPED-ABI-BUILD-V5-RESULT-VERIFICATION.json": "5878717f9048398f4c710fdc4a2b796d81872b9f8d0b3383176108c2ffd4d0c5",
        PHASE / "DETACHED-ABI-NEGATIVE-INTEGRATION-PROOF-v6.json": "9aaa761b38c880cd12955ecd2371bf3d6e9b8032749fbe257e221f663c8c8784",
        PHASE / "DETACHED-ABI-NEGATIVE-INTEGRATION-BINDING-v6.json": "e0d0d46367922bcf23eed2edc091549f2460a0de1e0c9e38d28d787311112a7b",
        ROOT / "planning/review-assets/recovery-step9-generation-contract-20261028/acceptance.json": "491feb0f5fbeefb9df841de46d104b160e3ad4832241b449115037b79961070b",
        ROOT / "planning/Project Progress Reassessment 2026-10-28 - ABI Module Policy.md": "13f1cfefeac05cc660e0c7a5a1bb4deacd01d202c7065a9210d178bf1f97b7fd",
    }
    for p, digest in evidence.items():
        assert sha(p) == digest, str(p)
    actual = json.loads((PHASE / "DETACHED-ABI-V3-RESULT-VERIFICATION.json").read_text())
    diagnostic = actual["reported_current_run_module"]
    assert diagnostic["reported_name"] == "apphelp.dll"
    assert diagnostic["reported_lexical_path"] == r"C:\Windows\SYSTEM32\apphelp.dll"
    assert diagnostic["reported_image_file_opened_by_verifier"] is False
    assert actual["old_v2_offender"] == "unknown; no retrospective identity attribution"
    assert actual["old_v2_original_outputs_verified_unchanged"] == 13
    protocol = json.loads((RUN / "effective-protocol.json").read_text())
    assert len(protocol["inputs"]) == 243
    assert not any(Path(item["path"]).name.casefold() == "apphelp.dll" for item in protocol["inputs"])
    assert len(protocol["system_candidates"]) == 16 and len(protocol["runtime_pins"]) == 4
    limits = protocol["limits"]
    child = RUN / "execution/child"
    assert (child / "attempt.json").stat().st_size <= limits["attempt_bytes"]
    assert (child / "failure.json").stat().st_size <= limits["row_bytes"]
    assert (child / "result.partial.jsonl").stat().st_size <= limits["result_bytes"]
    partial = (child / "result.partial.jsonl").read_bytes().splitlines()
    assert len(partial) == 3 and all(len(row) <= limits["row_bytes"] for row in partial)
    assert (RUN / "stdout.bin").stat().st_size <= limits["stream_bytes"]
    assert (RUN / "stderr.bin").stat().st_size <= limits["stream_bytes"]
    marker = json.loads((child / "failure.json").read_text())
    fields = ",\"module_policy\":" + json.dumps(marker["module_policy"], ensure_ascii=False, separators=(",", ":"))
    assert len(fields.encode()) <= 32768
    assert actual["owned_child"]["full_process_elapsed_seconds"] < limits["child_seconds"]
    assert actual["parent_seconds_before_terminal_seal"] < limits["parent_seconds"]
    md = PHASE / "DETACHED-ABI-V3-RESULT-VERIFICATION.md"
    assert "\ufffd" not in md.read_bytes().decode("utf-8", errors="strict")
    result = {
        "schema_version": 1, "status": "passed",
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "assessment": {"path": str(DOC), "bytes": DOC.stat().st_size, "sha256": sha(DOC)},
        "verification_markdown": {"path": str(md), "sha256": sha(md)},
        "checker": {"path": str(Path(__file__)), "sha256": sha(Path(__file__))},
        "UTF8": "strict, no BOM/replacement characters", "status_rows": rows,
        "ordered_next_gates": 6, "local_links_checked": links,
        "evidence_pins": [{"path": str(p), "sha256": digest} for p, digest in evidence.items()],
        "supplemental_actual_checks": {
            "reported_module_image_not_in_approved_read_set": True,
            "unchanged_16_system_names_and_4_package_DLL_scope": True,
            "attempt_row_partial_stream_and_stdout_stderr_caps": "passed",
            "module_context_existing_32768_byte_cap": "passed",
            "old_v2_outputs_unchanged_and_offender_remains_unknown": True,
        },
        "activity": {"actual_children": 0, "SDK_or_target_API_calls": 0, "native_loads": 0,
                     "GGUF_or_protected_payload_reads": 0, "reported_image_file_opens": 0},
        "limitations": "Text/evidence QA only, not new application tests, native qualification or scientific review."
    }
    out = PHASE / "MODULE-IDENTITY-REASSESSMENT-QA.json"
    with out.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({"status": "passed", "rows": len(rows), "gates": 6, "links": len(links),
                      "document_sha256": sha(DOC), "QA_sha256": sha(out), "verification_MD_sha256": sha(md)}))


if __name__ == "__main__":
    main()
