from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy import controller
from experiments.inspect_policy.records import CaseRecord, publish, proof, parse, read_bytes


class ControllerTests(unittest.TestCase):
    def test_three_rotations_have_identical_full_denominator(self):
        schedule = controller.batch_schedule(3)
        self.assertEqual(len(schedule), 9)
        self.assertEqual([r["arm"] for r in schedule[:3]], list(controller.ARMS))
        self.assertEqual([r["arm"] for r in schedule[3:6]], list(controller.ARMS[1:]+controller.ARMS[:1]))
        self.assertEqual({a: sum(r["arm"] == a for r in schedule) for a in controller.ARMS}, {a: 3 for a in controller.ARMS})

    def test_task_recipe_excludes_oracle_from_bare_workers(self):
        config = {"rows": [{"control_id": "fictional"}], "oracle": {"path": "hidden"},
                  "limits": controller.DEFAULT_LIMITS, "code_pins": {}, "mode": "fictional"}
        for arm in controller.ARMS:
            recipe = controller.worker_recipe(config, arm, "output")
            self.assertEqual("oracle" in recipe, arm == "inspect")
            self.assertNotIn("expected", recipe["rows"][0])

    def test_errors_on_rejects_and_unstarted_do_not_score_correct(self):
        oracle = {"cases": [{"control_id": "a", "decision": "reject", "observables": {}},
                            {"control_id": "b", "decision": "accept", "observables": {}}]}
        records = [{"control_id": "a", "status": "error", "decision": {"decision": "error", "observables": {}}},
                   {"control_id": "b", "status": "unstarted", "decision": None}]
        result = controller.score_rows(records, oracle)
        self.assertEqual(result["scheduled"], 2)
        self.assertEqual(result["full_conformance"], 0)
        self.assertEqual(result["correct_rejection"], 0)
        self.assertEqual(result["completed"], 0)

    def test_source_bracket_detects_changed_and_omitted_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data/cache") as folder:
            path = Path(folder)/"source.py"
            path.write_bytes(b"fictional source")
            pins = {str(path): proof(path)}
            controller.verify_pins(pins)
            path.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                controller.verify_pins(pins)

    def test_invalid_limits_and_protected_outputs_fail_before_mutation(self):
        for key, value in (("case_seconds", float("nan")), ("batch_seconds", float("inf")),
                           ("process_output_bytes", 1.5), ("stage_seconds", True)):
            limits = dict(controller.DEFAULT_LIMITS)
            limits[key] = value
            with self.assertRaises(ValueError):
                controller.validate_limits(limits)
        with tempfile.TemporaryDirectory(dir=ROOT/"data/cache") as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "protected"):
                controller.output_boundary(root/"nested", [root])
            self.assertFalse((root/"nested").exists())

    def test_postflight_failure_preserves_dispatched_valid_prefix(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data/cache") as folder:
            root = Path(folder)
            input_root = root/"input"
            input_root.mkdir()
            pinned = input_root/"source"
            pinned.write_bytes(b"original")
            freeze_root = root/"freeze"
            freeze_root.mkdir()
            rows = [{"control_id": "fictional-one"}]
            config = {"mode": "fictional", "rows": rows, "schedule": controller.batch_schedule(),
                "limits": controller.DEFAULT_LIMITS, "code_pins": {}, "input_pins": {str(pinned): proof(pinned)},
                "corpus_root": str(input_root), "python": {"path": sys.executable},
                "oracle": {"path": str(input_root/"oracle.json")}, "expected_cells": 9}
            pin = publish(freeze_root/"FROZEN.json", config)
            def dispatch(command, **kwargs):
                recipe = parse(read_bytes(command[command.index("--recipe")+1]))
                worker = CaseRecord(recipe["output"], recipe)
                (worker.path/"cases").mkdir()
                case = CaseRecord(worker.path/"cases/fictional-one", rows[0])
                case.finish({"status": "completed", "decision": {"decision": "accept", "observables": {}}, "error": None})
                worker.finish({"status": "completed"})
                pinned.write_bytes(b"changed after actual dispatch")
                return SimpleNamespace(returncode=0, stdout=b"", stderr=b"", supervision={})
            with patch("tether._process.supervise_command", side_effect=dispatch), patch("tether._process.validate_success_report"):
                result = controller.run_stage(freeze_root/"FROZEN.json", pin["sha256"], root/"run")
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["retained_cells"], 9)
            self.assertEqual(result["batches"][0]["status"], "failed")
            self.assertEqual(result["batches"][0]["rows"][0]["status"], "completed")
            self.assertTrue(all(b["status"] == "unstarted" for b in result["batches"][1:]))

    def test_current_supervisor_exact_cap_cap_plus_one_and_timeouts(self):
        from tether._process import ProcessLimits, supervise_command, validate_success_report
        exact = ProcessLimits(timeout_seconds=5, max_output_bytes=16)
        command = [sys.executable, "-I", "-B", "-S", "-c", "import os;os.write(1,b'x'*16)"]
        result = supervise_command(command, limits=exact)
        self.assertEqual(result.stdout, b"x"*16)
        validate_success_report(result.supervision, exact, len(result.stdout), len(result.stderr))
        with self.assertRaises(Exception) as failure:
            supervise_command(command[:-1]+["import os;os.write(1,b'x'*17)"], limits=exact)
        retained = failure.exception.tether_engine_result
        self.assertEqual(retained.supervision["termination_reason"], "output_limit_exceeded")
        self.assertTrue(retained.supervision["process_reaped"])
        for program in ("import time;time.sleep(2)", "import os,time;os.close(1);os.close(2);time.sleep(2)"):
            with self.assertRaises(Exception) as timeout:
                supervise_command(command[:-1]+[program], limits=ProcessLimits(timeout_seconds=0.1, max_output_bytes=16))
            retained = timeout.exception.tether_engine_result
            self.assertEqual(retained.supervision["termination_reason"], "deadline_exceeded")
            self.assertTrue(retained.supervision["process_reaped"])

    def test_fatal_per_case_deadline_leaves_marker(self):
        import subprocess
        with tempfile.TemporaryDirectory(dir=ROOT/"data/cache") as folder:
            program = ("import sys,time;sys.path.insert(0,"+repr(str(ROOT))+");"
                "from experiments.inspect_policy.controller import case_deadline;"
                "guard=case_deadline("+repr(folder)+",'fictional-timeout',0.05);guard.__enter__();time.sleep(2)")
            result = subprocess.run([sys.executable, "-I", "-B", "-c", program],
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 124)
            marker = parse(read_bytes(Path(folder)/"WATCHDOG.json"))
            self.assertEqual(marker["control_id"], "fictional-timeout")
            self.assertEqual(marker["reason"], "per_case_deadline")

    def test_recipe_and_output_collisions_never_dispatch(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data/cache") as folder:
            output = Path(folder)/"existing"
            output.mkdir()
            with self.assertRaises(FileExistsError):
                controller.run_stage(Path(folder)/"missing-freeze.json", "0"*64, output)
            self.assertEqual(list(output.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
