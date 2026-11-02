"""Validate checker-only fixes using fictional text and unchanged real evidence."""
from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
INTEGRATION = HERE.parent
EVIDENCE = INTEGRATION.parent
CHECKER = INTEGRATION / "check_stage.py"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main():
    directory = HERE / "green"
    directory.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location("checked_bg01_fixes", CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    before = checker.current_gate_sources()
    source_pin = sha(CHECKER)
    controls = []

    def check(name, expected, function):
        audit = checker.Audit()
        try:
            function(audit)
            observed, error = "accepted", None
        except Exception as exc:
            observed, error = "rejected", dict(type=type(exc).__name__, message=str(exc))
        controls.append(dict(name=name, expected=expected, observed=observed,
            passed=observed == expected, checks=len(audit.checks), inputs=audit.inputs, error=error))

    red = json.loads((HERE / "RESULTS.json").read_bytes())
    for row in red["controls"]:
        if row["name"].startswith("fictional_log_"):
            name = row["name"][len("fictional_log_"):]
            check("original_" + name, row["expected"], lambda a, name=name: a.unittest_log(
                HERE / "fictional-logs" / (name + ".log"), 138))

    report = dict(status="passed", stage="complete", mode="full",
                  tests=dict(run=2020, failures=0, errors=0, skipped=[]))
    summary = "test_example (fictional.Test) ... ok\n\n----------------------------------------------------------------------\nRan 2020 tests in 1.000s\n\nOK\n"
    probes = json.dumps(dict(required_probes="fictional_placeholder")) + "\n"
    footer = json.dumps(report, indent=2) + "\n"
    variants = {
        "driver_valid_lf": (summary + probes + footer, report, "accepted"),
        "driver_valid_crlf": ((summary + probes + footer).replace("\n", "\r\n"), report, "accepted"),
        "ordinary_valid_crlf": (summary.replace("\n", "\r\n"), None, "accepted"),
        "ordinary_forbids_driver_footer": (summary + footer, None, "rejected"),
        "driver_missing_final_json": (summary + probes, report, "rejected"),
        "driver_wrong_final_json": (summary + json.dumps(dict(status="failed")), report, "rejected"),
        "driver_extra_text_after_json": (summary + footer + "unfinished", report, "rejected"),
        "driver_extra_json_after_report": (summary + footer + "{}\n", report, "rejected"),
        "driver_second_complete_suite": (summary + summary + footer, report, "rejected"),
        "driver_second_incomplete_suite": (summary + "Ran 2020 tests in 2.000s\n" + footer, report, "rejected"),
        "driver_second_skipped_suite": (summary + "Ran 2020 tests in 2.000s\n\nOK (skipped=1)\n" + footer, report, "rejected"),
        "driver_trailing_started_test": (summary + "test_pending (fictional.Test) ... \n" + footer, report, "rejected"),
        "driver_trailing_setup": (summary + "setUpClass (fictional.Test) ... \n" + footer, report, "rejected"),
        "driver_trailing_interrupt": (summary + "KeyboardInterrupt\n" + footer, report, "rejected"),
        "driver_trailing_traceback": (summary + "Traceback (most recent call last):\n" + footer, report, "rejected"),
        "driver_earlier_ok_latest_skip_crlf": (("Ran 1 test in 0.001s\n\nOK\n" +
            "Ran 2020 tests in 1.000s\n\nOK (skipped=1)\n" + footer).replace("\n", "\r\n"), report, "rejected"),
    }
    for name, (text, driver, expected) in variants.items():
        path = directory / (name + ".log")
        path.write_bytes(text.encode("utf-8"))
        check("fictional_" + name, expected, lambda a, path=path, driver=driver:
              a.unittest_log(path, 2020, driver_report=driver))

    check("actual_facade138", "accepted", lambda a: a.unittest_log(INTEGRATION / "package-tests-02.log", 138))
    check("actual_platform7", "accepted", lambda a: a.unittest_log(INTEGRATION / "platform-gate-tests.log", 7))
    check("actual_all_correction_and_peer_evidence", "accepted", checker.check_regressions)
    check("actual_both_archive_migrations", "accepted", lambda a: checker.check_archive_profile(
        a, EVIDENCE / "archive-profile-v2/VALIDATION.json"))
    check("actual_bounded_serde_evidence", "accepted", lambda a: checker.check_atomic_validation(
        a, INTEGRATION / "windows-replace/VALIDATION.json"))
    check("actual_current_installed_attempt02", "accepted", lambda a: checker.check_installed(
        a, ROOT / "data/cache/tether-051-installed-qualification-attempt02"))
    check("stale_installed_attempt01", "rejected", lambda a: checker.check_installed(
        a, ROOT / "data/cache/tether-051-installed-qualification-attempt01"))

    preservation = EVIDENCE / "legacy-preservation/PRESERVATION-20261102T192818Z.json"
    readback = EVIDENCE / "legacy-preservation/PRESERVATION-20261102T192818Z-READBACK.json"
    check("actual_preservation_records", "accepted", lambda a: checker.check_preservation_records(a, preservation, readback))
    original = json.loads(preservation.read_bytes())
    for name, rows in (("empty", []), ("unrelated", [dict(name="unrelated", passed=True)]),
                       ("one_removed", original["checks"][:-1])):
        changed = dict(original, checks=rows)
        path = directory / ("fictional-preservation-" + name + ".json")
        write(path, changed)
        check("preservation_" + name, "rejected", lambda a, path=path: checker.check_preservation_records(a, path, readback))
    invalid_readback = directory / "fictional-readback.json"
    write(invalid_readback, dict(json.loads(readback.read_bytes()), installed_payloads_rehashed_after_demo=109))
    check("preservation_weakened_readback", "rejected", lambda a: checker.check_preservation_records(a, preservation, invalid_readback))

    # Isolate the exact new inventory expression too: hash rejection must not
    # be mistaken for having exercised its additional completeness condition.
    tree = ast.parse(CHECKER.read_text())
    inventory = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute) and node.func.attr == "need"
        and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "old preservation complete reviewed check inventory")
    expression = compile(ast.Expression(inventory.args[0]), str(CHECKER), "eval")
    for name, rows, expected in (("original196", original["checks"], "accepted"),
                                ("empty", [], "rejected"),
                                ("missing_retained", [row for row in original["checks"] if row["name"] != "retained_hash"], "rejected")):
        check("inventory_predicate_" + name, expected, lambda a, rows=rows: a.need(eval(expression, dict(
            checks=rows, Counter=Counter, PRESERVATION_CHECK_COUNTS=checker.PRESERVATION_CHECK_COUNTS)), "exact inventory predicate"))

    # Freshly rehash every retained_hash record just as main does. The only
    # exception is the exact two-step, independently checked archive migration.
    old_profile = ROOT / json.loads((EVIDENCE / "archive-profile/PREPARED.json").read_bytes())["old_copy"]
    retained = []
    for row in original["checks"]:
        if row["name"] != "retained_hash":
            continue
        path = ROOT / row["path"].replace("\\", "/")
        old_profile_case = path.resolve() == (ROOT / checker.PROFILE_PATH).resolve()
        current = sha(path)
        okay = (row["expected_sha256"] == row["actual_sha256"] == sha(old_profile) == checker.OLD_PROFILE_SHA256
                and current == checker.NEW_PROFILE_SHA256) if old_profile_case else current == row["expected_sha256"] == row["actual_sha256"]
        retained.append(dict(path=str(path), current_sha256=current, passed=okay, reviewed_profile_exception=old_profile_case))
    check("all12_retained_artifacts_freshly_match", "accepted", lambda a: a.need(
        len(retained) == 12 and all(row["passed"] for row in retained), "fresh old retained hashes"))

    after = checker.current_gate_sources()
    stable = before == after and sha(CHECKER) == source_pin
    result = dict(schema_version=1, status="PASS" if stable and all(row["passed"] for row in controls) else "FAILED",
        scope="Checker-only component validation; no full gate execution or aggregate BG01 completion",
        completed_at_utc=datetime.now(timezone.utc).isoformat(), checker_sha256=source_pin,
        checker_stable=sha(CHECKER) == source_pin, runtime_test_tool_pinset_stable=before == after,
        control_count=len(controls), controls=controls, freshly_rehashed_preserved_artifacts=retained,
        preserved_red_results_sha256=sha(HERE / "RESULTS.json"),
        preserved_red_preservation_sha256=sha(HERE / "preservation-red.json"),
        provider_spending_usd=0, model_calls=0)
    write(HERE / "GREEN-VALIDATION.json", result)
    print(json.dumps(dict(status=result["status"], controls=len(controls),
        failures=[row["name"] for row in controls if not row["passed"]], checker_sha256=source_pin,
        source_pinset_stable=before == after), indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
