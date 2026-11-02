"""Real finite synthetic children test wall-time and aggregate pipe limits."""
from contextlib import redirect_stdout, redirect_stderr
import copy
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages/tether/src"))
from asof.serde import ContractError, canonical
from tether import _process as supervisor, _presentation as layer, _cli as cli


class ProcessTests(unittest.TestCase):
    def command(self, script):
        return [sys.executable, "-I", "-u", "-c", script]

    def run_child(self, script, seconds=3, cap=4096):
        return supervisor.supervise_command(self.command(script),
            limits=supervisor.ProcessLimits(seconds, cap))

    def assert_capture(self, error, cap, reason):
        result = error.tether_engine_result
        report = result.supervision
        self.assertLessEqual(len(result.stdout) + len(result.stderr), cap)
        self.assertLessEqual(report["observed_stdout_bytes"] + report["observed_stderr_bytes"], cap + 1)
        self.assertEqual(report["termination_reason"], reason)
        self.assertTrue(report["process_reaped"])
        return result

    def test_exact_aggregate_cap_and_utf8_bytes_are_accepted(self):
        result = self.run_child("import os; os.write(1, b'\\xc3\\xa9'*512); os.write(2, b'e'*1024)", cap=2048)
        self.assertEqual((len(result.stdout), len(result.stderr)), (1024, 1024))
        supervisor.validate_success_report(result.supervision, supervisor.ProcessLimits(3, 2048), 1024, 1024)
        self.assertFalse(result.supervision["observed_counts_are_lower_bounds"])

    def test_one_byte_over_combined_cap_rejects(self):
        with self.assertRaises(supervisor.EngineOutputLimitExceeded) as caught:
            self.run_child("import os; os.write(1,b'a'*2048); os.write(2,b'b'*2049)")
        result = self.assert_capture(caught.exception, 4096, "output_limit_exceeded")
        self.assertEqual(len(result.stdout) + len(result.stderr), 4096)
        self.assertEqual(result.supervision["observed_stdout_bytes"] + result.supervision["observed_stderr_bytes"], 4097)

    def test_stdout_stderr_and_dual_floods_stay_bounded(self):
        for script in ("import os; os.write(1,b'a'*1000000)", "import os; os.write(2,b'e'*1000000)",
                       "import os\nfor i in range(200):\n os.write(1,b'a'*8192); os.write(2,b'e'*8192)"):
            with self.subTest(script=script), self.assertRaises(supervisor.EngineOutputLimitExceeded) as caught:
                self.run_child(script)
            self.assert_capture(caught.exception, 4096, "output_limit_exceeded")

    def test_block_and_trickle_have_the_same_absolute_deadline(self):
        for script in ("import time; time.sleep(10)",
                       "import os,time\nfor i in range(100):\n os.write(1,b'x'); time.sleep(.02)"):
            start = time.monotonic()
            with self.subTest(script=script), self.assertRaises(supervisor.EngineDeadlineExceeded) as caught:
                self.run_child(script, seconds=.35)
            self.assertLess(time.monotonic()-start, 3)
            result = self.assert_capture(caught.exception, 4096, "deadline_exceeded")
            self.assertGreaterEqual(result.supervision["execution_elapsed_seconds"], .35)

    def test_closed_pipes_do_not_hide_a_live_child(self):
        with self.assertRaises(supervisor.EngineDeadlineExceeded) as caught:
            self.run_child("import os,time; os.close(1); os.close(2); time.sleep(10)", seconds=.3)
        self.assert_capture(caught.exception, 4096, "deadline_exceeded")

    def test_inherited_pipe_handle_cannot_hold_supervisor_forever(self):
        script = ("import subprocess,sys; "
                  "subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(1)'])")
        start = time.monotonic()
        with self.assertRaises(supervisor.EngineDeadlineExceeded) as caught:
            self.run_child(script, seconds=.3)
        self.assertLess(time.monotonic()-start, 2)
        result = self.assert_capture(caught.exception, 4096, "deadline_exceeded")
        self.assertTrue(result.supervision["observed_counts_are_lower_bounds"])

    def test_nonzero_exit_retains_both_streams_and_reaps(self):
        result = self.run_child("import os; os.write(1,b'out'); os.write(2,b'err'); raise SystemExit(7)")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (7, b"out", b"err"))
        self.assertTrue(result.supervision["process_reaped"])

    def test_invalid_limits_fail_before_spawn(self):
        for seconds in (True, False, 0, -1, math.inf, math.nan):
            with self.subTest(seconds=seconds), patch.object(supervisor.subprocess, "Popen") as spawn:
                with self.assertRaises(ContractError):
                    self.run_child("pass", seconds=seconds)
                spawn.assert_not_called()
        for cap in (True, False, 0, -1, 1.5, supervisor.MAX_OUTPUT_BYTES + 1):
            with self.subTest(cap=cap), patch.object(supervisor.subprocess, "Popen") as spawn:
                with self.assertRaises(ContractError):
                    self.run_child("pass", cap=cap)
                spawn.assert_not_called()

    def test_success_report_rejects_resealed_lies_and_bool_aliases(self):
        result = self.run_child("import os; os.write(1,b'x')", seconds=1, cap=1)
        for mutate in (lambda r: r["pipe_eof"].update(stdout=1), lambda r: r["limits"].update(max_output_bytes=True),
                       lambda r: r.update(retained_stdout_bytes=True), lambda r: r.update(execution_elapsed_seconds=1),
                       lambda r: r.update(observed_stderr_bytes=1), lambda r: r.update(process_reaped=False)):
            report = copy.deepcopy(result.supervision)
            mutate(report)
            with self.subTest(report=report), self.assertRaises(ContractError):
                supervisor.validate_success_report(report, supervisor.ProcessLimits(1, 1), 1, 0)

    def test_deadline_is_checked_after_final_poll(self):
        clock = [0.0]
        from unittest.mock import Mock
        child = Mock(returncode=0)
        def exited():
            clock[0] = 2.0
            return 0
        child.poll.side_effect = exited
        with patch.object(supervisor.subprocess, "Popen", return_value=child), \
             patch.object(supervisor, "_read_ready", return_value=b""), \
             patch.object(supervisor.time, "monotonic", side_effect=lambda: clock[0]), \
             self.assertRaises(supervisor.EngineDeadlineExceeded):
            self.run_child("pass", seconds=1)

    def test_cli_limits_are_bound_without_modifying_workflow_args(self):
        with tempfile.TemporaryDirectory(prefix="tether-process-") as folder:
            output = Path(folder) / "outer"
            stdout = io.StringIO()
            argv = ["demo", "--output", str(output), "--process-timeout-seconds=10", "--process-output-bytes", "8192"]
            with redirect_stdout(stdout):
                self.assertEqual(cli.main(argv), 0)
            created = json.loads(stdout.getvalue())
            manifest = json.loads((output / layer.MANIFEST).read_text())
            self.assertEqual(manifest["process_limits"], dict(timeout_seconds=10.0, max_output_bytes=8192))
            self.assertEqual(manifest["invocation_sha256"], layer.digest(canonical(argv)))
            self.assertEqual(json.loads((output / "engine/run.json").read_text())["budget"]["max_seconds"], 300)
            self.assertTrue(layer.verify_outer(output, created["receipt_sha256"])["external_anchor_checked"])
            with redirect_stderr(io.StringIO()), patch.object(layer, "invoke_engine") as invoke:
                self.assertEqual(cli.main(["inspect-run", "--run-dir", str(output), "--process-timeout-seconds", "1"]), 2)
            invoke.assert_not_called()

    def test_bad_cli_limits_and_abbreviations_do_not_reserve_or_dispatch(self):
        with tempfile.TemporaryDirectory(prefix="tether-process-") as folder:
            output = Path(folder) / "outer"
            with redirect_stderr(io.StringIO()), patch.object(layer, "invoke_engine") as invoke:
                self.assertEqual(cli.main(["demo", "--output", str(output), "--process-timeout-seconds=nan"]), 2)
                with self.assertRaises(SystemExit):
                    cli.main(["demo", "--output", str(output), "--process-timeout-sec=1"])
            invoke.assert_not_called()
            self.assertFalse(output.exists())

    def test_failed_delegate_reports_bounded_diagnostics_without_an_outer_directory(self):
        with self.assertRaises(supervisor.EngineOutputLimitExceeded) as caught:
            self.run_child("import os; os.write(1,b'x'*100)", cap=10)
        stderr = io.StringIO()
        with patch.object(layer, "invoke_engine", side_effect=caught.exception), redirect_stderr(stderr):
            self.assertEqual(cli.main(["inspect-run", "--run-dir", "fictional-does-not-exist"]), 2)
        self.assertIn('"termination_reason": "output_limit_exceeded"', stderr.getvalue())
        self.assertIn('"process_reaped": true', stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
