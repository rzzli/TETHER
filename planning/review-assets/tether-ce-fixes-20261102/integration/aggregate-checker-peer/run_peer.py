"""Read-only BG01 acceptance review, plus explicitly fictional log controls.

Does not run the full gate, mutate existing evidence, or assert aggregate PASS.
All generated files remain beneath this independent peer directory.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
INTEGRATION = HERE.parent
EVIDENCE = INTEGRATION.parent
CHECKER = INTEGRATION / "check_stage.py"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(obj, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main():
    output = HERE / "RESULTS.json"
    if output.exists():
        raise SystemExit("Use a distinct peer version; existing results are retained")
    spec = importlib.util.spec_from_file_location("bg01_checker_peer_target", CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    before = checker.current_gate_sources()
    checker_pin = digest(CHECKER)
    rows = []

    def examine(name, expected, action):
        audit = checker.Audit()
        try:
            value = action(audit)
            observed = "accepted"
            error = None
        except Exception as exc:
            value = None
            observed = "rejected"
            error = dict(type=type(exc).__name__, message=str(exc))
        row = dict(name=name, expected=expected, observed=observed,
                   expectation_met=observed == expected, error=error,
                   checks=len(audit.checks), inputs=audit.inputs)
        if value is not None:
            row["value"] = str(value)
        rows.append(row)
        return row

    examine("current_installed_attempt02", "accepted", lambda a: checker.check_installed(
        a, ROOT / "data/cache/tether-051-installed-qualification-attempt02/QUALIFICATION.json"))
    examine("stale_installed_attempt01", "rejected", lambda a: checker.check_installed(
        a, ROOT / "data/cache/tether-051-installed-qualification-attempt01/QUALIFICATION.json"))
    examine("missing_installed", "rejected", lambda a: checker.check_installed(a, HERE / "nonexistent-qualification.json"))
    examine("both_reviewed_profile_migrations", "accepted", lambda a: checker.check_archive_profile(
        a, EVIDENCE / "archive-profile-v2/VALIDATION.json"))
    examine("stale_profile_validation_as_current", "rejected", lambda a: checker.check_archive_profile(
        a, EVIDENCE / "archive-profile/VALIDATION.json"))
    examine("current_bounded_serde_controls", "accepted", lambda a: checker.check_atomic_validation(
        a, INTEGRATION / "windows-replace/VALIDATION.json"))
    examine("stale_serde_pin", "rejected", lambda a: a.pins({"src/asof/serde.py": "0" * 64}))
    examine("current_facade_log", "accepted", lambda a: a.unittest_log(INTEGRATION / "package-tests-02.log", 138))

    # Fictional unittest text only: no result is an actual test execution.
    logs = {
        "single_complete": ("Ran 138 tests in 1.000s\n\nOK\n", "accepted"),
        "interrupted_without_terminal": ("Ran 138 tests in 1.000s\n", "rejected"),
        "wrong_count": ("Ran 137 tests in 1.000s\n\nOK\n", "rejected"),
        "explicit_skip": ("Ran 138 tests in 1.000s\n\nOK (skipped=1)\n", "rejected"),
        "earlier_ok_latest_interrupted": ("Ran 1 test in 0.001s\n\nOK\nRan 138 tests in 1.000s\n", "rejected"),
        "earlier_ok_latest_skipped": ("Ran 1 test in 0.001s\n\nOK\nRan 138 tests in 1.000s\n\nOK (skipped=1)\n", "rejected"),
        "second_suite_started_after_ok": ("Ran 138 tests in 1.000s\n\nOK\ntest_next (fictional.Example) ... ", "rejected"),
    }
    fixture_dir = HERE / "fictional-logs"
    fixture_dir.mkdir(exist_ok=False)
    for name, (text, expected) in logs.items():
        path = fixture_dir / (name + ".log")
        path.write_text(text, encoding="utf-8", newline="\n")
        examine("fictional_log_" + name, expected, lambda a, path=path: a.unittest_log(path, 138))

    # Exercise the exact expression in main without manufacturing a full-gate
    # PASS record or mocking any surrounding acceptance checks.
    tree = ast.parse(CHECKER.read_text(encoding="utf-8"))
    gate_call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute) and node.func.attr == "need"
        and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "complete 2020-test gate no failures/skips")
    expression = compile(ast.Expression(gate_call.args[0]), str(CHECKER), "eval")
    for name, data, expected in [
        ("exact_count_zero_skips", dict(run=2020, failures=0, errors=0, skipped=[]), "accepted"),
        ("one_fewer_test", dict(run=2019, failures=0, errors=0, skipped=[]), "rejected"),
        ("one_more_test", dict(run=2021, failures=0, errors=0, skipped=[]), "rejected"),
        ("one_skip", dict(run=2020, failures=0, errors=0, skipped=["fictional"]), "rejected"),
        ("one_error", dict(run=2020, failures=0, errors=1, skipped=[]), "rejected"),
        ("missing_skip_field", dict(run=2020, failures=0, errors=0), "rejected"),
    ]:
        examine("full_count_predicate_" + name, expected, lambda a, data=data: a.need(
            eval(expression, {"tests": data}), "original exact full-count predicate"))

    # Bracket inventory comparison is deliberately actual-current, not a fake
    # source map. This only checks the live gate's captured starting inventory.
    before_gate = json.loads((INTEGRATION / "full-gate-04.source-before.json").read_bytes())
    examine("live_gate_start_inventory_still_current", "accepted", lambda a: a.need(
        before_gate["sources"] == before, "same current source inventory"))
    examine("missing_source_bracket_rejected", "rejected", lambda a: checker.check_source_bracket(
        a, HERE / "nonexistent.source-bracket.json", HERE / "nonexistent-report.json", HERE / "nonexistent.log"))

    # The real aggregate checker should not produce PASS without a terminal
    # bracket. Point to an explicitly absent bracket, preserving the live gate.
    missing_aggregate = HERE / "aggregate-missing-bracket.json"
    args = [sys.executable, "-B", str(CHECKER),
        "--full-gate", str(INTEGRATION / "full-gate-04.json"),
        "--full-log", str(INTEGRATION / "full-gate-04.log"),
        "--source-bracket", str(HERE / "nonexistent.source-bracket.json"),
        "--archive-profile-validation", str(EVIDENCE / "archive-profile-v2/VALIDATION.json"),
        "--atomic-validation", str(INTEGRATION / "windows-replace/VALIDATION.json"),
        "--facade-log", str(INTEGRATION / "package-tests-02.log"),
        "--installed", str(ROOT / "data/cache/tether-051-installed-qualification-attempt02"),
        "--preservation", str(EVIDENCE / "legacy-preservation/PRESERVATION-20261102T192818Z.json"),
        "--preservation-readback", str(EVIDENCE / "legacy-preservation/PRESERVATION-20261102T192818Z-READBACK.json"),
        "--output", str(missing_aggregate)]
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=60)
    save(HERE / "aggregate-missing-bracket-command.json", dict(argv=args,
        exit_code=completed.returncode, stdout=completed.stdout, stderr=completed.stderr))
    aggregate = json.loads(missing_aggregate.read_bytes())
    rows.append(dict(name="real_aggregate_missing_terminal_bracket", expected="rejected",
        observed="rejected" if completed.returncode == 1 and aggregate["status"] == "FAILED" else "accepted",
        expectation_met=completed.returncode == 1 and aggregate["status"] == "FAILED",
        failure=aggregate.get("failure"), checks=len(aggregate["checks"])))

    after = checker.current_gate_sources()
    document = dict(schema_version=1, completed_at_utc=datetime.now(timezone.utc).isoformat(),
        status="FINDINGS" if any(not row["expectation_met"] for row in rows) else "SCOPED_PASS",
        scope="Independent component checks; NOT full-gate execution or aggregate stage completion",
        checker_sha256=checker_pin, checker_stable=digest(CHECKER) == checker_pin,
        runtime_test_tool_pinset_stable=before == after, controls=rows,
        observed_unexpected_acceptances=[row["name"] for row in rows if not row["expectation_met"]],
        provider_spending_usd=0, model_calls=0)
    save(output, document)
    print(json.dumps({key: document[key] for key in ("status", "checker_stable", "runtime_test_tool_pinset_stable", "observed_unexpected_acceptances")}, indent=2))
    return 0 if document["checker_stable"] and document["runtime_test_tool_pinset_stable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
