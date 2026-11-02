"""Freeze an explicit public TETHER packet allowlist after terminal local checks."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.presentation import package_tether_review as packet

HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def log_check(name, count, skips=0):
    raw = (HERE / name).read_bytes()
    text = raw.decode("utf-8-sig")
    assert re.search(rf"Ran {count} tests in [0-9.]+s\s+OK", text), name
    assert "FAILED (" not in text
    assert (f"skipped={skips}" in text) if skips else "OK (skipped=" not in text
    return {"sha256": sha(raw), "tests_collected": count, "tests_executed": count - skips,
            "approved_optional_skips": skips, "failures": 0, "errors": 0}


def reviewed(name):
    raw = (HERE / name).read_bytes()
    value = json.loads(raw)
    assert str(value.get("status", "")).startswith("PASS"), name
    assert not value.get("unresolved_findings", [])
    return {"sha256": sha(raw), "status": value["status"]}


def main():
    gates = {
        "tether_full": log_check("TETHER-TESTS-FULL.txt", 49),
        "tether_core": log_check("TETHER-TESTS-CORE.txt", 49),
        "legacy_targeted_full": log_check("LEGACY-TARGETED-FULL.txt", 115),
        "legacy_targeted_core": log_check("LEGACY-TARGETED-CORE.txt", 115, 19),
        "packet_helper": log_check("PACKET-HELPER-TESTS-v1.txt", 12),
    }
    evidence = {key: reviewed(name) for key, name in {
        "frontdoor_independent": "FRONTDOOR-NAMESPACE-INDEPENDENT-REVIEW-v2.json",
        "wheel_independent": "WHEEL-PEER-REVIEW-v1.json",
        "paper_independent": "PAPER-RENAME-PEER-REVIEW.json",
        "installed_source_isolation": "ISOLATED-INSTALLED-QUALIFICATION.json",
        "preservation_and_visual": "PRESERVATION-AND-PAPER-QA.json",
    }.items()}
    build = json.loads((ROOT / "paper/TETHER-PDF-BUILD.json").read_bytes())
    location = json.loads((HERE / "WHEEL-BUILD-LOCATION.json").read_text(encoding="utf-8-sig"))
    wheel = Path(location["wheel"])
    assert sha(wheel.read_bytes()) == "26bb8059ac0eb1e1b9d6c965dedae2409f7d418fbdb48d13f0c524f8354c4ddf"
    legacy = ROOT / "data/derived/preprint-p09-release-20261101T232900Z/asof-research-artifact-0.1.0.zip"
    results = ROOT / "data/cache/p09-portable-presentation-20261101T202322Z"
    inventory = packet.source_inventory(ROOT, results, wheel, legacy)
    assert len(inventory) == 70
    payloads = {}
    for name, (path, role) in sorted(inventory.items()):
        raw = packet.safe._read(path)
        payloads[name] = {"sha256": sha(raw), "bytes": len(raw), "role": role}
    qualification = {**packet.QUALIFICATION, "qualified_at_utc": datetime.now(timezone.utc).isoformat(),
        "payloads": payloads, "checks": gates, "evidence": evidence,
        "environment": {"qualified_platform": "Windows x64", "python": "3.11.15",
            "tether_version": "0.4.0", "compatibility_engine_version": "0.3.11",
            "isolated_installed_distributions": 2, "isolated_optional_arrow": "absent",
            "full_test_arrow": "21.0.0", "core_test_arrow": "absent",
            "pdf_renderer_versions": {k: v for k, v in build["tool_versions"].items() if k != "interpreter"}},
        "scope_notes": [
            "TETHER means Target Evidence Tracking Harness for Evaluation and Reproducibility; AsOf is the retained former name and compatibility engine.",
            "The project name and canonical interface changed after the experiments. No scientific result, study cost, case selection, code commitment or original receipt was rewritten.",
            "All 100 legacy core/replay payloads and original authorities remain unchanged. New TETHER launcher code has its own versioned proof and receipt.",
            "The same 49 interface tests pass in full and core profiles with no skips. Independent code probes pass all 12 cases after bounded-read/stability and process-cleanup corrections; failing-before evidence is retained.",
            "Targeted compatibility regressions pass 115 tests in full and 96 executed plus 19 approved optional skips in core. Earlier 1973-test broad acceptance is historical baseline, not a newly repeated rename result.",
            "The wheel passes 117 independent closure checks. Isolated installed demo and source-inclusive verification use two local wheels, no optional libraries and no D/E checkout imports. Canonical offline project sync also passes.",
            "The current TETHER PDF has 18 pages and 274 independently checked visible units, three vector figures, no raster/clipping/body overlap and 29 links; all pages were visually reviewed and fresh-process in-memory repetition is byte-identical.",
            "Project-name substitutions plus one explicit naming paragraph invert exactly to the pre-rename scientific paper. Eight formatter/publication controls pass; these are engineering checks, not biomedical validation.",
            "The new source/launcher and packet are distinct from the immutable historical P09 archive. The 37 numerical result payloads are exact historical bytes; portable README and manifest metadata remain separately versioned.",
            "P06 production/audit remain 203.828/7.125 seconds. Post-result P09 reconstruction/audit remain 289.938/15.187 seconds and 6862 source checks. Overlapping software comparisons are not independent studies.",
            "All 137 complete originals are mandatory for native reconstruction. The 136 external Open Targets originals have untested fresh exact-byte reacquisition. Exact CC0 HGNC and project receipt inclusions remain explicit inside the legacy archive.",
            "Only two catalog display fields changed; roles, IDs, date facts and technical keys are preserved. Historical catalog fingerprints remain committed; new catalog bytes have a genuine new fingerprint.",
            "Native Linux replay and current hosted CI are not qualified. Publisher authenticity, old private archives, causal genetics, clinical predictions, source-study independence and agent scientific superiority are not established.",
            "Paper renderer/fonts and raw environment-bearing PDF build metadata are not bundled. Physical I/O and total platform cost remain unknown. Owner author facts/acceptance are deferred and no public deposit or publication is authorized.",
        ], "new_model_calls": 0, "new_provider_downloads": 0, "provider_spending_usd": 0}
    raw = packet.safe._wire(qualification)
    packet._qualification(raw)
    target = ROOT / "paper/release/tether/QUALIFICATION.json"
    with target.open("xb") as stream:
        stream.write(raw)
    record = {"status": qualification["status"], "qualification_sha256": sha(raw),
        "qualification_bytes": len(raw), "qualified_payloads": len(payloads), "expected_zip_members": len(payloads) + 2,
        "wheel": wheel.relative_to(ROOT).as_posix(), "legacy_zip": legacy.relative_to(ROOT).as_posix(),
        "results_root": results.relative_to(ROOT).as_posix()}
    (HERE / "PACKET-QUALIFICATION-FREEZE.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
