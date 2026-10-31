"""Independent review-integrity and evaluator-role checks; never grades answers."""
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import replace
import hashlib
import io
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
INTAKE = ROOT / "data/benchmark/gold_evidence/expert-intake-20261031T160538Z"
EXPECTED = {
    "IL6R_Completed_Responses1.docx": "78af3e50cde860bb551337a69a59bfb9439c327bb8e06693bc799377fbd0ed19",
    "response2.txt": "cf8ddfb04e1827220983d807b79fa7ad1fcb1d16d24449a942c24a6e57e90c84",
    "response3.txt": "8597d4e6d4f68b4f568b8ad09a76722ee100e7e2a64e94e0c0d4258b820ab32b",
}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    checks = []

    def check(name, condition):
        checks.append(dict(id=name, passed=bool(condition)))
        if not condition:
            raise AssertionError(name)

    manifest_path = INTAKE / "intake-manifest.json"
    manifest_pin = pin(manifest_path)
    check("selected_intake_manifest", manifest_pin["sha256"].startswith("64fb6fd7"))
    manifest = json.loads(manifest_path.read_bytes())
    check("manifest_evaluator_only", manifest["role"] == "evaluation_only")
    check("intake_not_human_or_gold_or_agent", manifest["agent_visible"] is False and manifest["human_provenance_accepted"] is False and manifest["adjudicated_gold"] is False)
    check("exact_three_inputs", len(manifest["records"]) == 3 and {Path(r["source"]["path"]).name for r in manifest["records"]} == set(EXPECTED))
    submitted_metadata = []
    ignored_paths = []
    before = []
    for row in manifest["records"]:
        number = row["submission_id"]
        original = Path(row["source"]["path"])
        copied = Path(row["preserved_original"]["path"])
        projection_path = Path(row["projection"]["path"])
        check(number + "_source_inside_supplied_directory", original.resolve().parent == (ROOT / "docs/expert-response10312026").resolve())
        check(number + "_preserved_inside_intake", copied.resolve().parent == (INTAKE / "originals").resolve())
        check(number + "_projection_inside_intake", projection_path.resolve().parent == (INTAKE / "extracts").resolve())
        for kind, path in (("source", original), ("preserved_original", copied), ("projection", projection_path)):
            check(number + "_" + kind + "_ordinary_file", path.is_file() and not path.is_symlink() and not path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
            actual = pin(path)
            check(number + "_" + kind + "_exact_pin", actual == row[kind])
            before.append(actual)
            ignored_paths.append(path)
        check(number + "_original_hash_known", pin(original)["sha256"] == EXPECTED[original.name])
        check(number + "_copy_equal_original", original.read_bytes() == copied.read_bytes())
        check(number + "_catalog_intent_not_gold_acceptance", row["catalog_intent"] == ["gold_evidence", "panel_ratings"] and row["reviewer_id"] is None and row["independence"] is None)
        projection = json.loads(projection_path.read_bytes())
        check(number + "_projection_evaluator_only", projection["role"] == "evaluation_only" and projection["input_parent"] == row["preserved_original"])
        metadata = dict(submission_id=number, exact_copy=True, human_provenance_accepted=False,
                        reviewer_id_in_manifest=None, independence_in_manifest=None)
        if original.suffix == ".docx":
            with zipfile.ZipFile(copied) as archive:
                members = archive.infolist()
                names = [entry.filename for entry in members]
                expanded = sum(entry.file_size for entry in members)
                check(number + "_bounded_archive", len(members) <= 128 and expanded <= 4 * 1024 * 1024)
                check(number + "_unique_members", len(names) == len(set(names)))
                check(number + "_no_links_or_encryption", all(not stat.S_ISLNK(entry.external_attr >> 16) and not entry.flag_bits & 1 for entry in members))
                check(number + "_crc_complete", archive.testzip() is None)
                check(number + "_no_macro_member", not any(name.lower().endswith("vbaproject.bin") for name in names))
                xml = archive.read("word/document.xml")
                check(number + "_no_xml_entities", b"<!DOCTYPE" not in xml.upper() and b"<!ENTITY" not in xml.upper())
                document = ET.fromstring(xml)
                paragraphs = [dict(locator=f"word/document.xml#paragraph[{index}]",
                                   text="".join(part.text or "" for part in paragraph.iter(W + "t")))
                              for index, paragraph in enumerate(document.iter(W + "p"))]
                check(number + "_all_paragraphs_and_locators_exact", paragraphs == projection["paragraphs"])
                comments = []
                if "word/comments.xml" in names:
                    comment_xml = archive.read("word/comments.xml")
                    check(number + "_comment_xml_no_entities", b"<!DOCTYPE" not in comment_xml.upper() and b"<!ENTITY" not in comment_xml.upper())
                    for comment in ET.fromstring(comment_xml):
                        comments.append(dict(id=comment.get(W + "id"), text="".join(part.text or "" for part in comment.iter(W + "t"))))
                check(number + "_comments_exact", comments == projection["comments"])
                counts = dict(insertions=sum(1 for _ in document.iter(W + "ins")), deletions=sum(1 for _ in document.iter(W + "del")))
                check(number + "_revision_counts_exact", all(projection[key] == value for key, value in counts.items()))
                check(number + "_archive_counts_exact", projection["archive_members"] == len(members) and projection["expanded_bytes"] == expanded)
                metadata.update(format="docx_text_projection", paragraphs=len(paragraphs), archive_members=len(members), expanded_bytes=expanded, comments=len(comments), **counts,
                                tab_elements=sum(1 for _ in document.iter(W + "tab")), break_elements=sum(1 for _ in document.iter(W + "br")))
        else:
            text = copied.read_bytes().decode("utf-8-sig")
            lines = [dict(locator=f"line[{index}]", text=line) for index, line in enumerate(text.splitlines(), 1)]
            check(number + "_all_utf8_lines_and_locators_exact", lines == projection["lines"])
            check(number + "_replacement_count_exact", projection["replacement_codepoints"] == text.count("\ufffd") == 0)
            metadata.update(format="utf8_text_lines", lines=len(lines), replacement_codepoints=0)
        submitted_metadata.append(metadata)
    ignored_paths.append(manifest_path)
    for path in ignored_paths:
        result = subprocess.run(["git", "check-ignore", "--quiet", "--", str(path)], cwd=ROOT, capture_output=True)
        check("git_ignored_" + path.relative_to(ROOT).as_posix(), result.returncode == 0)

    # Run only trusted synthetic role checks; no actual returned-review text/path
    # enters any source graph, request, packet or agent-visible manifest.
    sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "tests")]
    from asof.contracts import Snapshot
    from asof.provenance import InputGraph, catalog_index, check_role
    from asof.serde import ContractError, decode
    catalog_path = ROOT / "data/catalog/sources.json"
    catalog = catalog_index(json.loads(catalog_path.read_bytes()))
    for dataset in ("gold_evidence", "panel_ratings"):
        check(dataset + "_catalog_evaluator_only", catalog[dataset]["roles"] == ("evaluation_only",))
        for role in ("evaluation_only", "agent_evidence", "reference"):
            try:
                check_role(dataset, role, catalog)
            except ContractError:
                denied = True
            else:
                denied = False
            check(dataset + "_direct_" + role + "_denied", denied)
    check_role("ot_evidence", "agent_evidence", catalog)
    check("ordinary_agent_role_positive_control", True)
    snapshot = decode(Snapshot, json.loads((ROOT / "src/asof/demo/v2/snapshot.json").read_bytes()))
    template = snapshot.sources[0]
    for dataset in ("gold_evidence", "panel_ratings"):
        for role in ("evaluation_only", "agent_evidence", "reference"):
            parent = replace(template, source_id="synthetic-evaluator-parent", dataset_id=dataset,
                             path="nonexistent-synthetic-parent.json", role=role)
            child = replace(template, source_id="synthetic-derived-child", dataset_id="asof_normalized_packets",
                            path="nonexistent-synthetic-derived.json", role="agent_evidence",
                            computed_at=datetime(2026, 10, 31, tzinfo=timezone.utc),
                            parents=(parent.source_id,), method_id="synthetic-role-denial", method_version="1")
            with patch("asof.provenance.sha256_file", side_effect=AssertionError("No payload hash read is allowed")) as reads:
                try:
                    InputGraph(replace(snapshot, sources=(child, parent)), ROOT, catalog)
                except ContractError as error:
                    denied = str(error).startswith(("Evaluator/unsupported input role denied:", "Catalog denies agent access:"))
                else:
                    denied = False
                check(dataset + "_derived_" + role + "_denied_before_payload", denied and reads.call_count == 0)

    tests = [
        "test_framework.FrameworkTests.test_catalog_label_role_cannot_be_relabeled_agent_evidence",
        "test_framework.FrameworkTests.test_manifest_label_role_is_denied",
        "test_v02_hardening.HardeningTests.test_missing_lineage_cycle_and_evaluator_parent_are_denied",
        "test_science_bounded_interpretation.InterpretationTests.test_evaluator_parent_rejected_before_calls",
        "test_science_interpretation_questions.QuestionInterpretationTests.test_evaluator_only_source_fails_existing_admission",
        "test_science_question_interpretation_runtime.QuestionRuntimeTests.test_evaluator_parent_and_future_program_fail_before_quote",
    ]
    test_temp = ROOT / "data/cache/expert-intake-synthetic-role-tests-20261031"
    test_temp.mkdir(exist_ok=True)
    tempfile.tempdir = str(test_temp)
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(tests))
    test_report_path = BASE / "SYNTHETIC-ROLE-REGRESSIONS-v1.json"
    with test_report_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(dict(status="PASS" if result.wasSuccessful() else "FAIL", methods=tests,
                       tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                       skips=len(result.skipped), fixture_temp_root=str(test_temp),
                       log=log.getvalue(), original_review_content_used=False), stream, indent=2)
        stream.write("\n")
    check("six_preexisting_synthetic_role_regressions", result.wasSuccessful() and result.testsRun == len(tests) and not result.skipped)
    for selected in before + [manifest_pin]:
        check("unchanged_after_checks_" + Path(selected["path"]).relative_to(ROOT).as_posix(), pin(Path(selected["path"])) == selected)
    check("source_bytes_total", sum(row["source"]["bytes"] for row in manifest["records"]) == 22693)
    report = dict(
        schema_version=1, status="PASS_EXACT_INTAKE_INTEGRITY_AND_EVALUATOR_ROLE_ONLY",
        reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
        manifest=manifest_pin, checks=checks,
        counts=dict(checks=len(checks), passed=sum(row["passed"] for row in checks), originals=3, original_bytes=22693,
                    projections=3, role_denial_cases=12, role_positive_controls=1, existing_test_methods=result.testsRun,
                    test_failures=len(result.failures), test_errors=len(result.errors), test_skips=len(result.skipped)),
        projection_metadata=submitted_metadata, regression_methods=tests, regression_log=log.getvalue(),
        inputs=dict(auditor=pin(Path(__file__)), preservation_helper=pin(BASE / "preserve_review_inputs.py"), catalog=pin(catalog_path),
                    provenance=pin(ROOT / "src/asof/provenance.py"),
                    test_files={str(Path(name.split(".")[0] + ".py")): pin(ROOT / "tests" / (name.split(".")[0] + ".py")) for name in tests}),
        checker_first_failure=pin(BASE / "INTEGRITY-PROBE-FIRST-FAILURE-v1.json"),
        checker_temp_failure=pin(BASE / "INTEGRITY-PROBE-TEMP-FAILURE-v1.json"),
        role_test_report=pin(test_report_path),
        eligibility=dict(role="evaluation_only", intended_catalog_products=["gold_evidence", "panel_ratings"],
                         human_provenance_accepted=False, adjudicated_gold=False, independent_source_reference_accepted=False,
                         case_freshness_qualified=False, agent_visible=False, R07_complete=False, HR2_complete=False, HR3_complete=False),
        missing_qualification_metadata=["Reviewer identities and human-versus-AI provenance confirmed separately from filenames",
            "Relevant expertise/experience, conflicts, prior exposure and outside-material disclosure",
            "Independent source-only submission before candidate exposure, with exact packet binding",
            "Actual/self-reported workload and separate original submissions before agreement/adjudication",
            "No reviewed genetics-source/follow-up or fresh-case HR3 acceptance inferred from mechanism returns"],
        metadata_limit="The intake manifest leaves reviewer_id/independence null; this is not a claim that no free-text metadata exists. Root's separate content/provenance review must retain unknowns and disclosures.",
        projection_limit="Exact XML w:t paragraph and UTF8 line projection only; original files retain formatting, line endings, other package parts and any nonprojected content. No render/checkbox/OCR equivalence claim.",
        scope="Preserved bytes, declared text projection and existing synthetic evaluator rejection only. No answer grading, interpretation, adjudication, clinical outcome read, model/native/compiler or full-suite execution. No returned answer enters a source graph or model request.",
    )
    output = BASE / "INTAKE-INTEGRITY-AND-ROLE-REVIEW-v1.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    print(json.dumps(dict(report=pin(output), counts=report["counts"], eligibility=report["eligibility"])))


if __name__ == "__main__":
    main()
