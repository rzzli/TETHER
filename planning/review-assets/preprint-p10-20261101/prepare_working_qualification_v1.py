"""Write a public allowlisted projection of completed P10 presentation evidence."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    audit_raw = (HERE / "P10-INDEPENDENT-AUDIT-v1.json").read_bytes()
    assert sha(audit_raw) == "393d845f8134911778a092679c92dbd9e1c496a4618a186fd09f19817b3c5133"
    audit = json.loads(audit_raw)
    assert audit["status"] == "PASS_SOURCE_PDF_README_REVIEW" and audit["unresolved_findings"] == []
    assert audit["evaluated_checklist_items"] == 30 and audit["passed_items"] == 28
    spec = importlib.util.spec_from_file_location("working_packet", HERE / "package_working_packet_v1.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    for name, expected in helper.PAPER_SHA256.items():
        assert sha((ROOT / name).read_bytes()) == expected
    record = {**helper.QUALIFICATION,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "paper_sha256": helper.PAPER_SHA256, "pdf_sha256": helper.PAPER_SHA256[helper.PDF_NAME],
        "pdf_pages": 18, "source_pdf_audit_sha256": sha(audit_raw), "source_pdf_audit_status": "passed",
        "source_pdf_audit_method": audit["method"], "source_pdf_audit_checks": 30,
        "pdf_text_units": 273, "pdf_vector_figures": 3, "pdf_visual_status": "passed",
        "pdf_source_preservation_status": "passed", "p09_archive_sha256": helper.P09_SOURCES[helper.P09_ZIP_NAME][1],
        "p09_protocol_sha256": helper.P09_PROTOCOL,
        "portable_results_manifest_sha256": helper.RESULTS_MANIFEST_SHA256,
        "new_model_calls": 0, "new_provider_downloads": 0, "provider_spending_usd": 0,
        "packet_purpose": "local_working_draft_review_only",
        "scope_notes": [
            "New sanitized presentation qualification; not the raw local PDF build manifest.",
            "The independent review evaluated30 checklist items:28passed and2conditional quantities absent from target Markdown; no unresolved finding.",
            "Four release/status paragraphs changed; exact inverse restores original manuscript/supplement. Earlier118 content checks carry forward only for unchanged text.",
            "273 units were freshly inventoried;18final pages visually covered;3vector figures,0raster,29links,no out-of-page glyphs. Fresh-process in-memory render was byte-identical.",
            "Six retention and two publication-failure controls pass. Byte/layout checks do not establish biomedical validity.",
            "Local paper PDF environment:CPython3.12.14,ReportLab4.4.9,pypdf6.10.0,pdfplumber0.11.9. Original local renderer/fonts/raw manifests are not bundled or claimed portable.",
            "Nested P09 replay separately qualifies Windowsx64/CPython3.11.15/PyArrow21.0.0;136OpenTargets originals external,exact reacquisition untested. ExactCC0HGNC exception and project receipts stay explicit.",
            "Outer paper is the current18-pageP10 revision; nested P09 retains immutable older P08 paper history.",
            "37historical result payloads are byte-exact; portable README/ARTIFACTS are new metadata. Historical S1anchors refer to original checkout artifacts.",
            "P06 primary production/audit203.828/7.125s stay separate from post-result P09 reconstruction/audit289.938/15.187s. Total physicalIO/platformcost unknown; provider spending0.",
            "No independent-study,clinical,causal,model-superiority,expert-equivalence,publisher-authentication,old-private-archive,nativeLinux or currenthosted claim.",
            "Owner facts and final author acceptance remain deferred; no publicdeposit,DOI,publication,push or new externalexpert input.",
        ],
    }
    raw = helper.safe._wire(record)
    helper._qualify(raw)
    path = ROOT / "paper/release/WORKING-PACKET-QUALIFICATION.json"
    with path.open("xb") as stream:
        stream.write(raw)
    print(json.dumps({"status": record["status"], "sha256": sha(raw), "bytes": len(raw)}))


if __name__ == "__main__":
    main()
