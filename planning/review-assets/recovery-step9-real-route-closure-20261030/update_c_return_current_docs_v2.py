"""Named documentation-only update after the independently reviewed code control."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
NATIVE = ROOT / "planning/review-assets/recovery-step9-native25-component-20261030"


def pin(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def replace_once(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new, 1)


def main():
    prior_path = BASE / "C-RETURN-CURRENT-DOCS-AUTHORING-v1.json"
    prior = json.loads(prior_path.read_bytes())
    before = [pin(ROOT / row["path"]) for row in prior["after_document_pins"]]
    assert before == prior["after_document_pins"], "coherent v1 documentation must remain preserved before the named v2 change"
    proof_path = NATIVE / "NATIVE25-COMPONENT-PROOF-v4.json"
    peer_path = NATIVE / "NATIVE25-COMPONENT-INDEPENDENT-STATIC-REVIEW-v4.json"
    scope_path = NATIVE / "KERNEL-KIND-GUARD-SUCCESSOR-AUTHORING-SCOPE-v5.json"
    assert pin(proof_path)["sha256"] == "dfe90829f1f8ac9e05aaaa7ce31304422150bb286c3cecb300ac7651f61ff63d"
    assert pin(peer_path)["sha256"] == "cb1def1aea2e638ec499c9cebd5b70df50101894fccf426e291a179819c5c3a3"
    proof = json.loads(proof_path.read_bytes())
    assert proof["counts"] == {"COMPONENT_PASS": 41, "FAIL": 2, "DEFERRED_NOT_EXECUTED": 4, "STATIC_DECLARATION_ONLY": 1}
    assert proof["setup_error"] is proof["evidence_error"] is None
    assert proof["audit_denials"] == proof["changed_pins"] == [] and proof["cooperative_deadline_late"] is False
    failed = [row["id"] for row in proof["rows"] if row["outcome"] == "FAIL"]
    assert failed == ["N25.5.scalar_kind_mismatch", "N25.5.count_kind_mismatch"]

    for row in before[:6]:
        path = ROOT / row["path"]
        text = path.read_bytes().decode("utf-8")
        old_end = "Source4 E08's accepted 122 assertions remain unchanged; native25, complete entry, R09 and science remain open."
        new_end = "Source4 E08's accepted 122 assertions remain unchanged. Native25's named expected-code control retains 41 PASS / two FAIL / four DEFERRED / one STATIC; only the two actual API/axis-kind guards remain. Source5 guard authoring is authorized only; the new source/harness is unexecuted. Complete entry, native25, R09 and science remain open."
        text = replace_once(text, old_end, new_end)
        pattern = r"^Next: independently resolve native25.*?$"
        replacement = "Next: correct only the two remaining native25 API/axis-kind guard defects in the separately named Source5 successor, then obtain exact peer review and a separate execution binding. Independent normative errata resolved the three specific-code expectations; the named unchanged-Source4 control is 41 PASS / two FAIL / four DEFERRED / one STATIC. Preserve the 31/12 and callback-only 38/5 diagnostics and every trailing assertion. Close the actual new84 source/import/consumer roster and core4 roles, same-Core C/Python bridge, joint physical14 reservations and genuine held-lease child/image route before activation. Planned/unbuilt descriptors permit authoring, not execution; 19,079 joint calls are not profile fit. AsOf 0.3.11/default v2 retains 1,774 tests/327 pins without rerun. Resource/human/scientific gates, original FAILED/INCOMPLETE_TIMEOUT and historical E16 exclusions remain; $0 and downloader/stopped monitor unchanged."
        text, count = re.subn(pattern, lambda match: replacement, text, flags=re.MULTILINE)
        assert count == 1
        if row["path"] == "TODO.md":
            text = replace_once(text, "native25 remains incomplete after its retained diagnostics and callback-only 38-pass/five-fail control.", "native25 remains incomplete after its retained 31/12 and 38/5 diagnostics and named 41-pass/two-fail expected-code control; Source5 guard work is authoring-only and unexecuted.")
        if row["path"] == "planning/Project Progress Reassessments.md":
            text = replace_once(text, "Native25 control remains 38 PASS/five FAIL/four DEFERRED/one STATIC.", "Named native25 expected-code control is 41 PASS/two FAIL/four DEFERRED/one STATIC; only actual API/axis-kind guards remain, with Source5 authoring-only/unexecuted.")
        path.write_bytes(text.encode("utf-8"))

    assessment = ROOT / "planning/Project Progress Reassessment 2026-10-30 - C Return Capture.md"
    text = assessment.read_bytes().decode("utf-8")
    old = "Three remaining test-code expectations require an independent errata disposition against the frozen contract and specific source refusal: N04 raw-return unknown, N06 explicit `READ_PROGRESS_INCOMPLETE`, and N07 undefined-count semantics. The two N25 valid alternate-kind failures remain actual source guard defects. Preserve both first results; decide exact expected codes independently before any named fixture correction, and correct the source guard separately without weakening the API/axis-kind requirement. No native25 pass or qualified real lease follows."
    new = "At that checkpoint, three generic-code expectations masked trailing assertions and required independent errata disposition. The two N25 valid alternate-kind failures were actual source guard defects. This 38/5 diagnostic remains preserved; no native25 pass or qualified real lease follows.\n\nThe subsequent [independent normative-code peer](review-assets/recovery-step9-native25-component-20261030/NATIVE25-COMPONENT-INDEPENDENT-STATIC-REVIEW-v4.json), `cb1def1a`, verifies the [three exact errata](review-assets/recovery-step9-native25-component-20261030/NATIVE25-EXPECTED-CODE-ERRATA-v4.json): N04.2 `RAW_RETURN_UNKNOWN`, N06.1 `READ_PROGRESS_INCOMPLETE`, and N07.1 `READ_COUNT_UNKNOWN`. These are specific preexisting contract/source refusals, not accepted-code sets, dropped predicates or weakened observations. The once-only [named expected-code control](review-assets/recovery-step9-native25-component-20261030/NATIVE25-COMPONENT-PROOF-v4.json), `dfe90829`, retains **41 PASS / two FAIL / four DEFERRED / one STATIC** in 0.234 seconds, with no setup/evidence/audit/pin/deadline error and unchanged Source4. Only the scalar-kind and count-kind mismatches remain actual failures. [Source5 guard authoring](review-assets/recovery-step9-native25-component-20261030/KERNEL-KIND-GUARD-SUCCESSOR-AUTHORING-SCOPE-v5.json), `0201a0fa`, is narrowly authorized; the new source and its selected harness are unexecuted. Independent source/harness review and a separate runtime binding still precede any Source5 run."
    text = replace_once(text, old, new)
    old = "1. **Close the finite native25 diagnostic correctly.** First independently resolve the three refusal-code expectation discrepancies against the pre-run contract; retain both actual diagnostics and exact reasons. Then author the minimal separately named API/axis-kind guard successor, preserving Source4 and its accepted 122 proof. Run only the bounded corrected component/regression scope after its own pre-code/static/binding gates."
    new = "1. **Correct the two remaining native25 API/axis-kind guards.** Independent normative errata and the named 41-pass/two-fail control resolve the three specific-code expectations; preserve the original 31/12 and callback-only 38/5 diagnostics and all trailing raw assertions. Author only the narrowly scoped Source5 guard, preserving Source4 and its accepted 122 proof. That new source/harness is unexecuted; run only the bounded corrected component/regression scope after its own exact source/harness peer and separate binding."
    text = replace_once(text, old, new)
    assessment.write_bytes(text.encode("utf-8"))

    goals_path = ROOT / "memory/project-goals.md"
    text = goals_path.read_bytes().decode("utf-8")
    old = "Native25 first 31 PASS/12 FAIL/four DEFERRED/one STATIC is preserved; callback-only\ncontrol bca943d0 retains 38 PASS/five FAIL/four DEFERRED/one STATIC in 0.219s.\nNext independently resolve three refusal-code expectation discrepancies, then fix\nthe two actual API/axis-kind guard failures in a named successor without weakening\nassertions."
    new = "Native25 first 31 PASS/12 FAIL/four DEFERRED/one STATIC and callback-only\n38 PASS/five FAIL/four DEFERRED/one STATIC remain preserved. Independent normative\npeer cb1def1a resolves three exact-code errata; named control dfe90829 retains\n41 PASS/two FAIL/four DEFERRED/one STATIC in 0.234s with unchanged Source4 and no\nsetup/evidence/audit/pin/deadline error. Next fix only the two actual API/axis-kind\nguard failures in Source5 under authoring-only scope 0201a0fa; the new source and\nselected harness are unexecuted, awaiting exact review and a separate binding."
    text = replace_once(text, old, new)
    goals_path.write_bytes(text.encode("utf-8"))

    memory_path = ROOT / "memory/MEMORY.md"
    text = memory_path.read_bytes().decode("utf-8")
    text = replace_once(text, "Native25 retains 38 PASS / five FAIL / four DEFERRED / one STATIC; expectation errata and two kind guards next.", "Named native25 control retains 41 PASS / two FAIL / four DEFERRED / one STATIC after independently resolved exact-code errata; 31/12 and 38/5 history preserved. Only Source5 kind-guard authoring is authorized; the new source/harness is unexecuted.")
    text = replace_once(text, "Native25 five failures, real bridge/Core native bank/lease", "Native25 two kind failures (Source5 authoring-only/unexecuted), real bridge/Core native bank/lease")
    memory_path.write_bytes(text.encode("utf-8"))

    log_path = ROOT / "memory/research-log-2026-10-30-c-return-capture.md"
    text = log_path.read_bytes().decode("utf-8")
    old = "Three generic refusal-code expectations\n(N04 raw-return unknown, N06 explicit READ_PROGRESS_INCOMPLETE, N07 undefined\ncount) require independent contract errata review. Two same-width API/axis-kind\nacceptances remain actual source guard defects. Preserve first failures and all\ntrailing assertions; no expectation weakening or native25 completion claim."
    new = "Three generic refusal-code expectations\nmasked trailing assertions at that historical checkpoint; two same-width API/axis-kind\nacceptances were actual source guard defects. Both first diagnostics remain preserved.\n\nIndependent normative peer cb1def1a then resolves exactly N04.2 RAW_RETURN_UNKNOWN,\nN06.1 READ_PROGRESS_INCOMPLETE and N07.1 READ_COUNT_UNKNOWN, retaining all raw\npredicates. The named unchanged-Source4 control dfe90829 records 41 PASS / two FAIL /\nfour DEFERRED / one STATIC in 0.234s, with no setup/evidence/audit/pin/deadline errors.\nOnly the scalar/count API-kind guard failures remain. Source5 scope 0201a0fa permits\nonly narrow guard authoring; its new source/harness is unexecuted and requires exact\npeer review plus a separate runtime binding. No expectation weakening or native25\ncompletion claim."
    text = replace_once(text, old, new)
    text = replace_once(text, "finite native25 disposition\nand named kind guard;", "the remaining native25\nkind guard and separately bound qualification;")
    log_path.write_bytes(text.encode("utf-8"))

    record = {"schema_version": 1, "status": "DOCUMENTATION_AUTHORING_V2_INDEPENDENT_QA_PENDING",
              "preserved_v1_authoring": pin(prior_path), "preserved_v1_author_check": pin(BASE / "C-RETURN-CURRENT-DOCS-AUTHOR-CHECK-v1.json"),
              "reason": "Root requested current-only update after the independently reviewed exact-code control. Preserve 31/12 and 38/5 diagnostic history; new current result41/2, Source5 authoring-only/unexecuted. No earlier dated assessment/log rewritten.",
              "new_evidence": {"normative_peer": pin(peer_path), "expected_code_errata": pin(NATIVE / "NATIVE25-EXPECTED-CODE-ERRATA-v4.json"),
                               "control4_actual": pin(proof_path), "source5_authoring_only": pin(scope_path)},
              "root_acceptance": prior["root_acceptance"], "validated_root_reference_pins": prior["validated_root_reference_pins"],
              "before_document_pins": before, "after_document_pins": [pin(ROOT / row["path"]) for row in before],
              "activity": prior["activity"], "QA_checkbox": "UNTICKED_PENDING_INDEPENDENT_PEER"}
    path = BASE / "C-RETURN-CURRENT-DOCS-AUTHORING-v2.json"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"record": pin(path), "assessment": pin(assessment), "documents": len(before)}, indent=2))


if __name__ == "__main__":
    main()
