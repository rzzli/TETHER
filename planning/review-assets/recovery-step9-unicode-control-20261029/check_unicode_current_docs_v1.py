"""Check this checkpoint's repository documentation; no application/payload run."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ASSESSMENT = "planning/Project Progress Reassessment 2026-10-29 - Unicode Controls.md"
DOCUMENTS = (
    "README.md", "TODO.md", ASSESSMENT,
    "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
    "planning/Recovery Status and Next Gates 2026-10-26.md",
    "planning/Project Progress Reassessments.md",
    "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md",
    "memory/MEMORY.md", "memory/project-goals.md",
    "memory/research-log-2026-10-29-r09-unicode-controls.md",
)


def main():
    texts, pins = {}, {}
    for relative in DOCUMENTS:
        data = (ROOT / relative).read_bytes()
        texts[relative] = data.decode("utf-8", "strict")
        pins[relative] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    assessment = texts[ASSESSMENT]
    rows = re.findall(r"^\| (R\d\d|HR\d) \|", assessment, re.M)
    assert rows == [f"R{i:02d}" for i in range(1, 17)] + [f"HR{i}" for i in range(1, 5)]
    assert re.findall(r"^([1-5])\. ", assessment, re.M) == list("12345")
    links = []
    for wrapped, bare in re.findall(r"\]\((?:<([^>]+)>|([^\s)]+))\)", assessment):
        target = wrapped or bare
        if target.startswith(("https://", "http://", "#")):
            continue
        target = unquote(target.split("#", 1)[0])
        path = ((ROOT / ASSESSMENT).parent / target).resolve()
        assert path.is_relative_to(ROOT) and path.is_file(), target
        links.append(str(path.relative_to(ROOT)))
    assert "INCOMPLETE_TIMEOUT" in assessment and "No old payload pass" in assessment
    assert "1,774 retained" in assessment and "327 source/resource pins" in assessment
    assert "b219f1f2" in assessment and "739d83df" in assessment
    assert "[ ] R09 Implement" in texts["TODO.md"]
    assert all(f"[ ] HR{i}" in texts["TODO.md"] for i in range(1, 5))
    for relative in DOCUMENTS[:7]:
        if relative != ASSESSMENT:
            assert "Unicode Controls.md" in texts[relative], relative
    acceptance = json.loads((HERE / "UNICODE-CONTROL-SCOPED-ACCEPTANCE-v1.json").read_bytes())
    assert acceptance["execution_authorized"] is False
    assert acceptance["status"] == "ACCEPTED_SOURCE_ONLY_FROZEN_FULL_RESPONSE_FIXTURES"
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed", "scope": "Ten current UTF8 documents, the new assessment's local links/status/order and source-only acceptance consistency.",
        "documents": pins, "status_rows": rows, "ordered_next_gates": 5,
        "assessment_local_links": links, "application_tests_rerun": False,
        "retained_application_tests": 1774, "retained_application_source_pins": 327,
        "new_payload_or_native_activity": False,
    }
    output = HERE / "UNICODE-CONTROL-CURRENT-DOCS-QA-v1.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"status": result["status"], "documents": len(pins), "links": len(links), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
