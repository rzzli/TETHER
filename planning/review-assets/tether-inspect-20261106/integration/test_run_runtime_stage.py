"""One-shot orchestration qualification with mocked commands, no native calls."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("runtime_stage_under_test", HERE / "run_runtime_stage.py")
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
from experiments.inspect_policy.records import proof, publish, parse, read_bytes
from tether._process import EngineResult
import tether._process as process_module


class RuntimeStageTests(unittest.TestCase):
    def setUp(self):
        root = ROOT / "data/cache/inspect-stage-mock-tests"
        root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "inputs").mkdir()
        (self.root / "process-inputs").mkdir()
        ordinary = [{"id": "fiction-ordinary"}]
        process_rows = {"IX06": [{"id": "fiction-interrupted"}, {"id": "fiction-unexecuted"}],
                        "IX08": {"id": "fiction-owner"}}
        def ref(path, value):
            return {"path": str(path), **publish(path, value)}
        rows = ref(self.root / "inputs/rows.json", ordinary)
        oracle = ref(self.root / "inputs/oracle.json", {"cases": []})
        processes = ref(self.root / "process-inputs/rows.json", process_rows)
        recipe = ref(self.root / "ordinary-recipe.json", {"rows": ordinary,
            "output_root": str(self.root / "ordinary-cases"), "oracle_path": oracle["path"],
            "oracle_proof": {key: oracle[key] for key in ("sha256", "bytes")}})
        inventory = {str(p.relative_to(self.root)).replace("\\", "/"): proof(p)
                     for p in self.root.rglob("*") if p.is_file()}
        preparation = ref(self.root / "PREPARATION.json", {
            "ordinary": {"rows": rows, "oracle": oracle}, "process_rows": processes,
            "ordinary_recipe": recipe, "input_inventory": inventory})
        source_paths = [HERE / "run_runtime_stage.py", HERE / "run_process_witness.py",
            stage.NATIVE_WORKER, ROOT / "experiments/inspect_policy/records.py", Path(process_module.__file__)]
        config = {"schema_version": 1, "preparation": preparation,
            "python": {"path": sys.executable, **proof(sys.executable)},
            "code_pins": {str(path.absolute()): proof(path) for path in source_paths},
            "limits": stage.DEFAULT_LIMITS}
        self.freeze = self.root / "FROZEN.json"
        self.pin = publish(self.freeze, config)
        self.calls = []

    def success(self, command, *, limits):
        self.calls.append(command)
        if "--work" in command:
            output = Path(command[command.index("--work") + 1])
            output.mkdir()
            publish(output / "RESULT.json", {"status": "success"})
        else:
            which = command[command.index("--which") + 1]
            output = self.root / ("IX06-interruption" if which == "IX06" else "IX08-concurrency")
            output.mkdir()
            publish(output / "RESULT.json", {"status": "PASS"})
        report = {"schema_version": 1, "method": "tether.process_envelope.v1", "limits": limits.payload(),
            "termination_reason": "exited", "execution_elapsed_seconds": 0.01, "total_elapsed_seconds": 0.02,
            "retained_stdout_bytes": 0, "retained_stderr_bytes": 0, "observed_stdout_bytes": 0,
            "observed_stderr_bytes": 0, "observed_counts_are_lower_bounds": False,
            "pipe_eof": {"stdout": True, "stderr": True}, "process_started": True,
            "process_reaped": True, "cleanup_errors": []}
        return EngineResult(0, b"", b"", report)

    def run_stage(self, execute=None, output=None, pin=None):
        return stage.run_stage(self.freeze, pin or self.pin["sha256"], output or self.root / "stage",
                               execute=execute or self.success)

    def test_success_three_once_and_output_collision_preserves_seal(self):
        result = self.run_stage()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(self.calls), 3)
        seal = proof(self.root / "stage/SEALED.json")
        with self.assertRaises(FileExistsError):
            self.run_stage()
        self.assertEqual(proof(self.root / "stage/SEALED.json"), seal)
        self.assertEqual(len(self.calls), 3)

    def test_wrong_external_pin_never_reserves_or_dispatches(self):
        with self.assertRaisesRegex(ValueError, "anchor"):
            self.run_stage(pin="0" * 64)
        self.assertFalse((self.root / "stage").exists())
        self.assertEqual(self.calls, [])

    def test_changed_prepared_input_fails_with_zero_calls_and_retained_statuses(self):
        (self.root / "inputs/oracle.json").write_text("{}")
        result = self.run_stage()
        self.assertEqual(result["status"], "failed")
        self.assertEqual([x["status"] for x in result["schedule"]], ["unexecuted"] * 3)
        self.assertEqual(len(result["case_dispositions"]), 4)
        self.assertEqual(self.calls, [])
        self.assertTrue((self.root / "stage/SEALED.json").exists())

    def test_nonzero_attempt_is_sealed_no_later_dispatch_or_retry(self):
        def failed(command, *, limits):
            outcome = self.success(command, limits=limits)
            return EngineResult(7, outcome.stdout, outcome.stderr, outcome.supervision)
        result = self.run_stage(failed)
        self.assertEqual(result["status"], "failed")
        self.assertEqual([x["status"] for x in result["schedule"]], ["failed", "unexecuted", "unexecuted"])
        self.assertEqual(len(self.calls), 1)
        self.assertTrue((self.root / "stage/ordinary16/receipt.json").exists())
        self.assertFalse((self.root / "IX06-interruption").exists())
        # A new outer folder does not authorize repeating an existing native attempt.
        again = self.run_stage(output=self.root / "different-stage")
        self.assertEqual(again["status"], "failed")
        self.assertEqual(len(self.calls), 1)

    def test_postflight_input_mutation_fails_even_after_successful_commands(self):
        def mutates(command, *, limits):
            outcome = self.success(command, limits=limits)
            if len(self.calls) == 3:
                (self.root / "inputs/oracle.json").write_text("{}")
            return outcome
        result = self.run_stage(mutates)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["postflight"]["status"], "failed")
        self.assertEqual(len(self.calls), 3)

    def test_capture_write_failure_does_not_label_started_call_unexecuted(self):
        original = stage._write_raw
        def failed_capture(path, raw):
            if Path(path).name == "stdout.bin":
                raise OSError("Fictional capture write failure")
            return original(path, raw)
        with patch.object(stage, "_write_raw", failed_capture):
            result = self.run_stage()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["schedule"][0]["status"], "failed_unresolved")
        self.assertTrue(result["schedule"][0]["dispatch_attempted"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual([row["status"] for row in result["schedule"][1:]], ["unexecuted"] * 2)

    def test_minimal_child_environment_removes_fake_credentials_and_restores_parent(self):
        def observe(command, *, limits):
            self.assertNotIn("FICTIONAL_PROVIDER_API_KEY", os.environ)
            self.assertEqual(os.environ["PYTHON_DOTENV_DISABLED"], "1")
            self.assertEqual(os.environ["TEMP"], os.environ["TMP"])
            self.assertTrue(Path(os.environ["TEMP"]).is_relative_to(self.root / "stage"))
            return self.success(command, limits=limits)
        with patch.dict(os.environ, {"FICTIONAL_PROVIDER_API_KEY": "invented-test-marker"}):
            result = self.run_stage(observe)
            self.assertEqual(os.environ["FICTIONAL_PROVIDER_API_KEY"], "invented-test-marker")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(self.calls), 3)


if __name__ == "__main__":
    unittest.main()
