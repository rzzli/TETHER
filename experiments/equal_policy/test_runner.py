"""Independent runner QA with fictional terminal records; never score corpus."""
from collections import Counter
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.equal_policy import run_comparison as runner


class RunnerTests(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[2] / "data/cache/equal-policy-runner-peer-tests"
        base.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        self.output = self.project / "fictional-comparison"
        self.output.mkdir()
        self.python = self.project / "fictional-python.exe"
        self.python.write_bytes(b"Not executable; every launcher test injects a fake Popen")
        self.source_files = {}
        for name in ("cases.py", "materialize.py", "reference.py", "policy_cases.py", "run_comparison.py"):
            relative = "experiments/equal_policy/" + name
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Fictional pinned code\n", encoding="utf-8")
            self.source_files[relative] = runner.pin(path)
        self.addCleanup(patch.stopall)
        patch.object(runner, "PROJECT", self.project).start()
        patch.object(runner, "PYTHON", self.python).start()
        self.specs = [dict(schema_version=1, control_id=key, operation="prepare_run", variant="core_v2_catalog1",
            construction_stratum="new_synthetic_construction", title="Fictional runner QA", preparation={},
            oracle=dict(decision=decision, obligation_ids=["EP-WIRE-01"], observables={}, rationale="Invented terminal record"))
            for key, decision in (("UNIT-A", "accept"), ("UNIT-B", "reject"))]
        self.oracle = dict(schema_version=1, corpus_id="fictional-runner-qa", cases=[
            dict(control_id=row["control_id"], operation=row["operation"], variant=row["variant"],
                 construction_stratum=row["construction_stratum"], **copy.deepcopy(row["oracle"])) for row in self.specs])
        runner.publish(self.output / "oracle.json", self.oracle)
        installed = self.project / 'installed'
        runtime_paths = {}
        for product in ('asof', 'tether'):
            package = installed / product
            package.mkdir(parents=True)
            (package / '__init__.py').write_text('# Fictional product payload\n', encoding='utf-8')
            runtime_paths[product + '_file'] = str(package / '__init__.py')
        self.trusted = dict(runtime_paths=runtime_paths,
            core_code_sha256={'__init__.py': runner.pin(installed / 'asof/__init__.py')['sha256']},
            launcher_proof=dict(code={'__init__.py': runner.pin(installed / 'tether/__init__.py')}))
        runner.publish(self.output / "trusted-runtime.json", self.trusted)
        records = []
        prepared = []
        for spec in self.specs:
            bundle = self.output / "bundles" / spec["control_id"]
            bundle.mkdir(parents=True)
            descriptor = dict(schema_version=1, control_id=spec["control_id"], operation=spec["operation"],
                variant=spec["variant"], paths={}, options={}, anchors={})
            runner.publish(bundle / "descriptor.json", descriptor)
            relative = (bundle / "descriptor.json").relative_to(self.output).as_posix()
            records.append(dict(control_id=spec["control_id"], descriptor=relative, operation=spec["operation"], variant=spec["variant"]))
            prepared.append(dict(control_id=spec["control_id"], status="prepared", descriptor=relative,
                                 descriptor_pin=runner.pin(bundle / "descriptor.json")))
        runner.publish(self.output / "case-preparation-schedule.json", dict(schema_version=1, cases=self.specs))
        runner.publish(self.output / "PREPARATION.json", dict(status="prepared", records=prepared,
            started=dict(sources=copy.deepcopy(self.source_files))))
        self.frozen = dict(schema_version=1, status="frozen", cases=records,
            settings=dict(repetitions=1, deadline_seconds=0.01, stdout_cap_bytes=4096, stderr_cap_bytes=1024),
            sources=copy.deepcopy(self.source_files), oracle_pin=runner.pin(self.output / "oracle.json"),
            trusted_runtime_pin=runner.pin(self.output / "trusted-runtime.json"), bundles=runner.tree(self.output / "bundles"),
            bundle_directories=runner.directories(self.output / "bundles"),
            installed_runtime=runner.installed_inventory(self.trusted),
            python=dict(path=str(self.python), **runner.pin(self.python)))
        runner.publish(self.output / "FROZEN.json", self.frozen)

    def overwrite(self, path, value):
        path.write_bytes(runner.materialize.canonical(value) + b"\n")

    def terminal_records(self, decisions=None):
        directory = self.output / "comparison"
        directory.mkdir()
        runner.publish(directory / "STARTED.json", dict(freeze_pin=runner.pin(self.output / "FROZEN.json"),
                                                       checks=runner.check_frozen(self.output, self.frozen)))
        records = []
        for spec in self.specs:
            for implementation in runner.IMPLEMENTATIONS:
                name = spec["control_id"] + "-r1-" + implementation
                cell = directory / name
                cell.mkdir()
                decision = (decisions or {}).get(implementation, spec["oracle"]["decision"])
                value = dict(schema_version=1, control_id=spec["control_id"], repetition=1,
                    implementation=implementation, disposition="returned",
                    result=dict(schema_version=1, control_id=spec["control_id"], decision=decision, observables={}))
                runner.publish(cell / "RESULT.json", value)
                records.append(dict(cell=name, **runner.pin(cell / "RESULT.json")))
        execution = dict(schema_version=1, status="executed", expected_cells=8, terminal_cells=8,
                         records=records, after_checks=runner.check_frozen(self.output, self.frozen))
        runner.publish(directory / "EXECUTION.json", execution)
        return execution

    def test_complete_denominator_is_accepted_for_fictional_records(self):
        self.terminal_records()
        runner.analyze(self.output)
        result = runner.materialize.load(self.output / "ANALYSIS.json")
        self.assertEqual(result["cells"], 8)
        self.assertEqual({row["cell"] for row in result["rows"]},
                         {f"{case}-r1-{impl}" for case in ("UNIT-A", "UNIT-B") for impl in runner.IMPLEMENTATIONS})

    def test_duplicate_terminal_reference_cannot_replace_a_missing_cell(self):
        execution = self.terminal_records()
        execution["records"][1] = copy.deepcopy(execution["records"][0])
        self.overwrite(self.output / "comparison/EXECUTION.json", execution)
        with self.assertRaises((RuntimeError, ValueError)):
            runner.analyze(self.output)

    def test_declared_counts_cannot_hide_a_short_record_inventory(self):
        execution = self.terminal_records()
        execution["records"].pop()
        self.overwrite(self.output / "comparison/EXECUTION.json", execution)
        with self.assertRaises((RuntimeError, ValueError)):
            runner.analyze(self.output)

    def test_changed_oracle_after_execution_is_rejected(self):
        self.terminal_records()
        self.oracle["cases"][0]["decision"] = "reject"
        self.overwrite(self.output / "oracle.json", self.oracle)
        with self.assertRaises((RuntimeError, ValueError)):
            runner.analyze(self.output)

    def test_changed_code_after_execution_is_rejected(self):
        self.terminal_records()
        (self.project / next(iter(self.source_files))).write_text("# Changed after execution\n")
        with self.assertRaises((RuntimeError, ValueError)):
            runner.analyze(self.output)

    def test_changed_installed_product_after_execution_is_rejected(self):
        self.terminal_records()
        Path(self.trusted['runtime_paths']['asof_file']).write_text('# Altered installed payload\n', encoding='utf-8')
        with self.assertRaises((RuntimeError, ValueError)):
            runner.analyze(self.output)

    def test_actual_installation_must_match_declared_code_inventory(self):
        installed = runner.installed_inventory(self.trusted)
        runner.check_trusted_installation(self.trusted, installed)
        self.trusted['core_code_sha256']['__init__.py'] = '0' * 64
        with self.assertRaises(RuntimeError):
            runner.check_trusted_installation(self.trusted, installed)

    def test_changed_bundle_after_execution_is_rejected(self):
        self.terminal_records()
        (self.output / "bundles/UNIT-A/descriptor.json").write_text("{}")
        with self.assertRaises((RuntimeError, ValueError)):
            runner.analyze(self.output)

    def test_changed_empty_directory_after_execution_is_rejected(self):
        self.terminal_records()
        (self.output / 'bundles/UNIT-A/new-empty-directory').mkdir()
        with self.assertRaises((RuntimeError, ValueError)):
            runner.analyze(self.output)

    def test_removed_frozen_empty_directory_is_rejected(self):
        empty = self.output / 'bundles/UNIT-A/declared-empty-directory'
        empty.mkdir()
        self.frozen['bundle_directories'] = runner.directories(self.output / 'bundles')
        self.overwrite(self.output / 'FROZEN.json', self.frozen)
        self.terminal_records()
        empty.rmdir()
        with self.assertRaises((RuntimeError, ValueError)):
            runner.analyze(self.output)

    def test_error_and_unsupported_are_not_counted_as_rejections(self):
        self.terminal_records(dict(tether="error", independent="unsupported", hash_schema="reject", reject_all="reject"))
        runner.analyze(self.output)
        totals = runner.materialize.load(self.output / "ANALYSIS.json")["totals"]
        for implementation, decision in (("tether", "error"), ("independent", "unsupported")):
            self.assertEqual(totals[implementation]["cells"], 2)
            self.assertEqual(totals[implementation]["decision_" + decision], 2)
            self.assertEqual(totals[implementation].get("false_rejection", 0), 0)
            self.assertEqual(totals[implementation].get("fully_conformant", 0), 0)
        self.assertEqual(totals["reject_all"]["false_rejection"], 1)

    def test_missing_observable_is_not_equal_to_explicit_null(self):
        self.assertIsNone(runner.observable_projection({"scorer_preflight": None}, "scorer_preflight"))
        self.assertIsNotNone(runner.observable_projection({}, "scorer_preflight"))
        actual = runner.observable_projection({"features": {"values": {"genetic_support": {}}}}, "feature_values")
        self.assertNotEqual(actual, {"genetic_support": None})

    def test_oracle_projection_uses_declared_fields_without_rounding(self):
        observed = dict(prediction=dict(status="abstained", probability=None, reason="required_features_missing"),
            features=dict(values=dict(genetic_support=dict(value=0.125, status="observed", dependency_groups=1))),
            exclusions=[dict(item_id="x", level="observation", reason="publication_after_origin")],
            recovery=dict(unresolved_attempts=["genetics:1"], recovery_action="inspect only; never automatically repeat unresolved calls"))
        self.assertIs(runner.observable_projection(observed, "probability_is_null"), True)
        self.assertEqual(runner.observable_projection(observed, "feature_values"), {"genetic_support": 0.125})
        self.assertEqual(runner.observable_projection(observed, "exclusion_reasons"), ["publication_after_origin"])
        self.assertIs(runner.observable_projection(observed, "recovery_may_dispatch"), False)
        with self.assertRaises(ValueError):
            runner.observable_projection(observed, "undeclared")

    def freeze_context(self):
        (self.output / "FROZEN.json").unlink()
        return patch.multiple(runner.cases, case_specs=lambda: copy.deepcopy(self.specs), oracle_manifest=lambda: copy.deepcopy(self.oracle))

    def test_freeze_refuses_oracle_changed_from_authored_schedule(self):
        altered = copy.deepcopy(self.oracle)
        altered["cases"][0]["decision"] = "reject"
        self.overwrite(self.output / "oracle.json", altered)
        with self.freeze_context(), patch.object(runner, "source_pins", return_value=self.source_files):
            with self.assertRaises((RuntimeError, ValueError)):
                runner.freeze(self.output)

    def test_freeze_refuses_duplicate_preparation_record_inventory(self):
        prepared = runner.materialize.load(self.output / "PREPARATION.json")
        prepared["records"][1] = copy.deepcopy(prepared["records"][0])
        self.overwrite(self.output / "PREPARATION.json", prepared)
        with self.freeze_context(), patch.object(runner, "source_pins", return_value=self.source_files):
            with self.assertRaises((RuntimeError, ValueError)):
                runner.freeze(self.output)

    def test_existing_comparison_output_preserves_files(self):
        result_root = self.output / "comparison"
        result_root.mkdir()
        sentinel = result_root / "sentinel"
        sentinel.write_bytes(b"preserve")
        before = runner.tree(result_root)
        with self.assertRaises(FileExistsError):
            runner.execute(self.output)
        self.assertEqual(runner.tree(result_root), before)

    def fake_child(self, mode):
        children = []

        class Child:
            def __init__(child, command, *, stdout, stderr, **kwargs):
                implementation = command[command.index("--implementation") + 1]
                control_id = Path(command[command.index("--root") + 1]).name
                payload = dict(schema_version=1, implementation=implementation,
                    result=dict(schema_version=1, control_id=control_id, decision="accept", observables={}), metrics={}, runtime={})
                body = runner.materialize.canonical(payload)
                if mode == "stdout_fast":
                    body += b" " * 5000
                os.write(stdout.fileno(), body)
                if mode == "stderr_fast":
                    os.write(stderr.fileno(), b"x" * 5000)
                child.returncode = None if mode == "timeout" else 0
                child.kills = child.waits = 0
                children.append(child)

            def poll(child):
                return child.returncode

            def kill(child):
                child.kills += 1
                child.returncode = -9

            def wait(child, timeout=None):
                child.waits += 1
                return child.returncode

        return Child, children

    def check_execution_mode(self, mode, expected):
        child, children = self.fake_child(mode)
        with patch.object(runner.subprocess, "Popen", child):
            runner.execute(self.output)
        execution = runner.materialize.load(self.output / "comparison/EXECUTION.json")
        self.assertEqual(execution["expected_cells"], 8)
        self.assertEqual(execution["terminal_cells"], 8)
        self.assertEqual(len({row["cell"] for row in execution["records"]}), 8)
        for row in execution["records"]:
            result = runner.materialize.load(self.output / "comparison" / row["cell"] / "RESULT.json")
            self.assertEqual(result["disposition"], expected)
            self.assertEqual(result["result"]["decision"], "error" if expected != "returned" else "accept")
        self.assertEqual(len(children), 8)
        self.assertTrue(all(child.waits >= 1 for child in children))
        return children

    def test_timeout_retains_all_error_terminals_without_retry(self):
        children = self.check_execution_mode("timeout", "timeout")
        self.assertTrue(all(child.kills == 1 for child in children))

    def test_fast_exited_stdout_limit_still_records_output_failure(self):
        self.check_execution_mode("stdout_fast", "output_limit")

    def test_fast_exited_stderr_limit_still_records_output_failure(self):
        self.check_execution_mode("stderr_fast", "output_limit")


if __name__ == "__main__":
    unittest.main()
