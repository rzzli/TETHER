"""Documentation-only closeout, anchored to the finite Root acceptance."""
from pathlib import Path
import hashlib
import json
import re


ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
ASSESSMENT = "Project Progress Reassessment 2026-10-30 - C Return Capture.md"
LOG = "research-log-2026-10-30-c-return-capture"
PATHS = ["README.md", "TODO.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
         "planning/Recovery Status and Next Gates 2026-10-26.md", "planning/Project Progress Reassessments.md",
         "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md"]


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def once(text, pattern, replacement):
    text, count = re.subn(pattern, lambda match: replacement, text, flags=re.MULTILINE)
    assert count == 1, (pattern, count)
    return text


def main():
    acceptance_path = BASE / "NATIVE-CARRIER-ROOT-ACCEPTANCE-v1.json"
    acceptance_pin = pin(acceptance_path)
    assert acceptance_pin["sha256"] == "ad4c9f0ece7296ac658ecec175caee028883562fd1905da4b58a4fc9952972e1"
    acceptance = json.loads(acceptance_path.read_bytes())
    assert acceptance["status"] == "ACCEPTED_COMPILED_FAKE_TARGET_COMPONENT_ONLY"
    for label, expected in acceptance["references"].items():
        actual = pin(ROOT / expected["path"])
        assert (actual["bytes"], actual["sha256"]) == (expected["bytes"], expected["sha256"]), label
    assert all(value is False for key, value in acceptance["qualification"].items() if key != "compiled_layout_and_fake_target_behavior")

    before = []
    old_checkpoint_paragraphs = {}
    for relative in PATHS:
        path = ROOT / relative
        before.append(pin(path))
        text = path.read_bytes().decode("utf-8")
        old_checkpoint_paragraphs[relative] = re.findall(r"^(?:Current checkpoint, 30 October UTC:|Next: close the operational new84).*?$", text, flags=re.MULTILINE)
        assert len(old_checkpoint_paragraphs[relative]) == 2
        prefix = "planning/" if "/" not in relative else ""
        current = (f"Current checkpoint, 30 October UTC: [C return capture](<{prefix}{ASSESSMENT}>) is accepted only for the compiled x64 raw-carrier layout and one own-source fake-target component run (root ad4c9f0e; compiled peer 5796bcc6; actual peer 1b10326d). All 79 controls / 29,310 measured C checks pass; 79 primary and 17 boundary cells match, with 47 fake calls and 17 error entries / 16 returns. The run reports 0.172s and four retained files / 121,790 B. This does not qualify real Win32, the Python conversion bridge, same-Core native bank/leases, physical14 or resources. Source4 E08's accepted 122 assertions remain unchanged; native25, complete entry, R09 and science remain open.")
        next_paragraph = ("Next: independently resolve native25's three refusal-code expectation discrepancies, then correct the two actual API/axis-kind guard failures in a separately named successor. The callback-only control remains 38 PASS / five FAIL / four DEFERRED / one STATIC; preserve its first 31-pass/12-fail diagnostic and all predicates. Close the actual new84 source/import/consumer roster and core4 roles, same-Core C/Python bridge, joint physical14 reservations and genuine held-lease child/image route before activation. Planned/unbuilt descriptors permit authoring, not execution; the illustrative 19,079 joint calls are not a fitted profile. AsOf 0.3.11/default v2 retains 1,774 tests/327 pins without rerun. No real-target/model or original-payload operation belongs to this closeout. Resource/human/scientific gates, original FAILED/INCOMPLETE_TIMEOUT and historical E16 exclusions remain; $0 and downloader/stopped monitor unchanged.")
        text = once(text, r"^Current checkpoint, 30 October UTC: .*?$", current)
        text = once(text, r"^Next: close the operational new84.*?$", next_paragraph)
        if relative == "README.md":
            old = "[current full-project reassessment](<planning/Project Progress Reassessment 2026-10-29 - Injected Producer.md>)"
            assert text.count(old) == 1
            text = text.replace(old, f"[current full-project reassessment](<planning/{ASSESSMENT}>)")
        if relative == "TODO.md":
            assert text.count("Both historical E16 invocations stay excluded and native25 unexecuted.") == 1
            text = text.replace("Both historical E16 invocations stay excluded and native25 unexecuted.", "Both historical E16 invocations stay excluded; native25 remains incomplete after its retained diagnostics and callback-only 38-pass/five-fail control.")
            text = text.rstrip() + "\n- [x] Qualify only the compiled Windows x64 raw-carrier layout and the once-only 79-control own-source fake-target component: root ad4c9f0e, compiled peer 5796bcc6 (129 checks / 14 store paths / 19 bodies), actual peer 1b10326d (399 checks), 29,310 measured C checks / 47 fake targets / 17 error entries / 16 returns; four run files / 121,790 B. No real Win32/Python bridge/same-Core native bank/lease/physical14/native25/resource/scientific qualification.\n- [ ] Reassess all R01–R16/HR1–HR4 after C return capture and pass independent current-document/memory QA. Assessment: planning/Project Progress Reassessment 2026-10-30 - C Return Capture.md; documentation QA pending, do not tick before the independent peer.\n"
        if relative == "planning/Project Progress Reassessments.md":
            text = text.rstrip() + f"\n\n| R09 compiled raw-carrier layout and C79 fake component accepted | [30 October UTC C-return-capture snapshot](<{ASSESSMENT}>) | Root ad4c9f0e / compiled peer 5796bcc6 / actual peer 1b10326d: 14 store paths and 19 bodies, 129 artifact checks; one fake image, 79 controls / 29,310 C checks / 399 independent actual checks pass. Run 0.172s, four files / 121,790 B. Native25 control remains 38 PASS/five FAIL/four DEFERRED/one STATIC. Real bridge/Win32/Core lease/physical/new84/resource/science gates stay open; independent documentation QA pending. |\n"
        path.write_bytes(text.encode("utf-8"))

    goals_path = ROOT / "memory/project-goals.md"
    before.append(pin(goals_path))
    goals = goals_path.read_bytes().decode("utf-8")
    heading = "## Current recovery execution"
    assert goals.count(heading) == 1
    block = f"""## Current recovery execution

Current checkpoint: [[Project Progress Reassessment 2026-10-30 - C Return Capture]].
Root ad4c9f0e accepts compiled layout and the one C79 fake-target component only:
three build commands exit 0 in 1.047s; compiled peer 5796bcc6 verifies 129 checks,
14 scalar-first stores and 19 bodies. Actual peer 1b10326d passes 399 retained-data
checks for all 79 primary / 17 boundary 256-byte copies and exact counters:
29,310 measured C checks, 116 wrapper attempts, 47 fake targets, 17 error entries /
16 returns. The one fake-image run reports 0.172s and four files / 121,790 B,
excluding final result construction/write from timing; these are disk bytes, not RSS.
Source4 E08/122 remains accepted, not joined to this native C bank. Python 3.11
headers/python311.lib existence is a prerequisite only, not ABI/bridge qualification.
Native25 first 31 PASS/12 FAIL/four DEFERRED/one STATIC is preserved; callback-only
control bca943d0 retains 38 PASS/five FAIL/four DEFERRED/one STATIC in 0.219s.
Next independently resolve three refusal-code expectation discrepancies, then fix
the two actual API/axis-kind guard failures in a named successor without weakening
assertions. Close the real new84 source/import/consumer roster/core4 roles,
same-Core C/Python bridge, joint physical14 reservations and held-lease child/image
route before activation. Planned/unbuilt pins permit authoring, not execution;
19,079 joint calls are a warning, not profile fit. Real Win32/Python conversion/
Core native bank/lease/physical/new84/resources, complete entry/R09 and science/humans
remain unqualified. App 0.3.11/default v2 retains 1,774 tests/327 pins/ten versions,
without rerun/default changes; $0 and downloader/stopped monitor unchanged.
Science gaps remain 65 missing inputs / 36 unqualified labels / 17 of 32 observable
states / 0 of 12 joint-ready cases; features empty, probabilities null.
See [[{LOG}]]. Independent documentation QA remains pending and unticked.

### Prior E08 checkpoint (retained history)
"""
    goals = goals.replace(heading, block, 1)
    goals = goals.replace("Current checkpoint: [[Project Progress Reassessment 2026-10-30 - E08 Policy]].", "Prior checkpoint: [[Project Progress Reassessment 2026-10-30 - E08 Policy]].", 1)
    goals_path.write_bytes(goals.encode("utf-8"))

    memory_path = ROOT / "memory/MEMORY.md"
    before.append(pin(memory_path))
    memory = memory_path.read_bytes().decode("utf-8")
    assert memory.startswith("# Research memory index")
    end = memory.index("\n")
    row = f"- [[{LOG}]] - Root ad4c9f0e accepts compiled x64 layout + one C79 fake image only: 14 stores / 19 bodies, 129 artifact and 399 actual checks; 79 controls / 29,310 C checks / 47 fake targets / 17 error entries / 16 returns, run 0.172s / four files / 121,790 B. Native25 retains 38 PASS / five FAIL / four DEFERRED / one STATIC; expectation errata and two kind guards next. No real bridge/Core lease/Win32/physical/RSS/science qualification; independent current-doc QA pending."
    memory = memory[:end + 1] + "\n" + row + "\n" + memory[end + 1:]
    memory = once(memory, r"^- \[\[project-goals\]\].*?$", "- [[project-goals]] - Current app 0.3.11/default v2, retained 1,774 tests/327 pins/ten versions. Finite compiled layout/C79 fake component accepted under ad4c9f0e; Source4 E08/122 preserved. Native25 five failures, real bridge/Core native bank/lease, full entry/physical/new84/resources and science/humans remain open. R01–R06 accepted; R07 technical negative; R08 no qualified fresh case; H5/clinical/genetics/calibration/comparisons/T2–T5/H6 conditional.")
    memory_path.write_bytes(memory.encode("utf-8"))

    targets = PATHS + ["planning/" + ASSESSMENT, "memory/project-goals.md", "memory/MEMORY.md", "memory/" + LOG + ".md"]
    record = {"schema_version": 1, "status": "DOCUMENTATION_AUTHORED_INDEPENDENT_QA_PENDING", "root_acceptance": acceptance_pin,
              "validated_root_reference_pins": len(acceptance["references"]), "before_existing_document_pins": before,
              "preserved_old_current_paragraphs": old_checkpoint_paragraphs,
              "after_document_pins": [pin(ROOT / relative) for relative in targets],
              "scope": "Ten current documentation/memory files only; finite component TODO checked after verified Root acceptance; reassessment QA remains unticked. Historical assessment/log files remain unchanged.",
              "activity": {"subject_runs": 0, "subject_imports": 0, "application_tests": 0, "builds": 0, "native_dispatches": 0, "original_or_model_payload_reads": 0}}
    path = BASE / "C-RETURN-CURRENT-DOCS-AUTHORING-v1.json"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"authoring": pin(path), "documents": len(targets), "acceptance_pins": len(acceptance["references"])}, indent=2))


if __name__ == "__main__":
    main()
