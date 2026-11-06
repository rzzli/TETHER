"""Actual Inspect runner, with invented files and a local deterministic provider."""
from copy import deepcopy
import ipaddress
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
os.environ["PYTHON_DOTENV_DISABLED"] = "1"

# Windows asyncio needs a stdlib self-pipe. No external connect, DNS or sendto
# is permitted; this is a trusted-code audit hook, not an OS network sandbox.
NETWORK_ATTEMPTS = []
_SOCKET = str(Path(socket.__file__).resolve())
def _audit(event, args):
    if event not in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        return
    frame, self_pipe = sys._getframe(1), False
    while frame is not None:
        if frame.f_code.co_name == "_fallback_socketpair" and str(Path(frame.f_code.co_filename).resolve()) == _SOCKET:
            self_pipe = True
            break
        frame = frame.f_back
    if event == "socket.connect" and self_pipe and ipaddress.ip_address(args[1][0]).is_loopback:
        return
    NETWORK_ATTEMPTS.append(event)
    raise PermissionError("Native fixture tests deny non-self-pipe networking")
sys.addaudithook(_audit)

from inspect_ai import eval
from fixtures import source, runtime_row
from experiments.inspect_policy.records import inspect_record, publish, thaw
from experiments.inspect_policy.task import build_archive_task
from experiments.inspect_policy.runtime import WitnessHooks, build_runtime_task
from experiments.inspect_policy.archive import replay_archive_case


class InspectNativeTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "data/cache/inspect-policy-native-tests"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        os.environ["INSPECT_CACHE_DIR"] = str(self.root / "cache")
        os.environ["TIKTOKEN_CACHE_DIR"] = str(self.root / "token-cache")

    def evaluate(self, task):
        logs = eval(task, display="none", log_dir=str(self.root / "logs"), log_format="json",
                    fail_on_error=False, retry_on_error=0, score_on_error=False,
                    max_retries=0, max_samples=1, max_tasks=1, time_limit=20,
                    log_shared=False, notification=False, log_samples=True, log_model_api=True)
        self.assertEqual(len(logs), 1)
        self.assertFalse(NETWORK_ATTEMPTS)
        return logs[0]

    def runtime(self, row, expected):
        output = self.root / "output"
        output.mkdir()
        oracle = self.root / "oracle.json"
        pin = publish(oracle, {"cases": [{"control_id": row["id"], "fields": expected}]})
        task = build_runtime_task([row], output, oracle, pin)
        self.assertEqual(task.dataset[0].target, "")
        log = self.evaluate(task)
        record = inspect_record(output / row["id"])
        return log, record

    def test_native_archive_solver_scorer_and_source_replay(self):
        row = source(self.root / "source")
        output = self.root / "output"
        output.mkdir()
        oracle = self.root / "oracle.json"
        pin = publish(oracle, {"cases": [{"control_id": row["control_id"], "decision": "accept", "observables": {"eligible_observation_ids": ["obs-1", "obs-2"]}}]})
        task = build_archive_task([row], output, oracle, pin)
        self.assertEqual(task.dataset[0].target, "")
        log = self.evaluate(task)
        self.assertEqual(log.status, "success")
        sample = log.samples[0]
        self.assertIsNone(sample.error)
        self.assertEqual(next(iter(sample.scores.values())).value, "C")
        anchor = sample.metadata["policy_record"]["receipt"]["sha256"]
        self.assertEqual(replay_archive_case(output / row["control_id"], anchor)["status"], "verified")
        (Path(row["bundle_root"]) / "input/source.json").write_bytes(b'{"changed":true}\n')
        with self.assertRaises(ValueError):
            replay_archive_case(output / row["control_id"], anchor)

    def test_native_generate_and_usage_with_frozen_source_despite_state_mutation(self):
        row = runtime_row(source(self.root / "source"), mutate_task_state=True)
        log, record = self.runtime(row, {"status": "completed", "provider_dispatches": 1,
            "accounting.measured_usage.input_tokens": 10, "accounting.estimated_usage.input_tokens": 0})
        self.assertEqual(log.status, "success")
        self.assertEqual(next(iter(log.samples[0].scores.values())).value, "C")
        self.assertEqual(len(record["result"]["commits"][0]["claims"]), 2)
        statement = record["result"]["commits"][0]["claims"][0]["evidence"]["observation"]["statement"]
        self.assertNotIn("attempted nested", statement)
        names = [event["event"] for event in record["events"]]
        self.assertLess(names.index("attempt_reserved"), names.index("provider_dispatched"))
        self.assertIn("inspect_before_model", names)
        self.assertIn("inspect_model_usage", names)
        self.assertEqual(sum(value.input_tokens for value in log.stats.model_usage.values()), 10)
        self.assertEqual(sum(value.output_tokens for value in log.stats.model_usage.values()), 8)
        hooks = [event["details"]["identity"] for event in record["events"] if event["event"] in ("inspect_before_model", "inspect_model_usage")]
        self.assertEqual(hooks[0], hooks[1])
        self.assertEqual(hooks[0]["control_id"], row["id"])
        self.assertEqual(hooks[0]["epoch"], 1)
        self.assertEqual(hooks[0]["attempt"], 0)
        self.assertEqual(hooks[0]["native_sample_uuid"], log.samples[0].uuid)
        self.assertTrue(hooks[0]["run_id"])

    def test_native_zero_call_budget_prevents_provider(self):
        row = runtime_row(source(self.root / "source"))
        row["budget"]["max_calls"] = 0
        log, record = self.runtime(row, {"status": "budget_exhausted", "provider_dispatches": 0, "accounting.calls": 0})
        self.assertEqual(next(iter(log.samples[0].scores.values())).value, "C")
        self.assertNotIn("provider_entered", [event["event"] for event in record["events"]])

    def test_native_error_is_not_retry_and_keeps_unknown_quote(self):
        row = runtime_row(source(self.root / "source"))
        row["steps"][0]["script"]["behavior"] = "error"
        row["steps"].append(deepcopy(row["steps"][0]))
        log, record = self.runtime(row, {})
        self.assertIsNotNone(log.samples[0].error, thaw(record["result"]))
        result = record["result"]
        self.assertEqual(result["provider_dispatches"], 1)
        self.assertEqual(result["accounting"]["estimated_usage"]["input_tokens"], 20)
        self.assertEqual(result["accounting"]["measured_usage"]["input_tokens"], 0)

    def test_native_timeout_retains_reservation_without_second_call(self):
        row = runtime_row(source(self.root / "source"), call_seconds=0.05)
        row["steps"][0]["script"].update(behavior="sleep", delay_seconds=1.0)
        log, record = self.runtime(row, {})
        self.assertIsNotNone(log.samples[0].error, {"retained": thaw(record["result"]), "native": log.samples[0].model_dump(mode="json", exclude={"transcript", "events", "messages", "input", "metadata"})})
        self.assertEqual(record["result"]["status"], "timeout")
        self.assertEqual(record["result"]["provider_dispatches"], 1)
        self.assertEqual(record["result"]["accounting"]["estimated_usage"]["output_tokens"], 40)

    def test_native_valid_overquote_retains_measured_and_prevents_later_call(self):
        row = runtime_row(source(self.root / "source"))
        row["steps"][0]["script"]["usage"]["input_tokens"] = 21
        row["steps"].append(deepcopy(row["steps"][0]))
        log, record = self.runtime(row, {"status": "budget_exhausted", "provider_dispatches": 1,
            "accounting.measured_usage.input_tokens": 21, "accounting.estimated_usage.input_tokens": 0})
        self.assertEqual(next(iter(log.samples[0].scores.values())).value, "C")
        self.assertEqual(record["result"]["commits"], ())

    def test_native_invalid_response_keeps_observed_telemetry_separate_from_conservative_policy_usage(self):
        row = runtime_row(source(self.root / "source"))
        row["steps"][0]["script"]["content"] = "not a JSON selection"
        row["steps"][0]["script"]["usage"]["input_tokens"] = 21
        row["steps"].append(deepcopy(row["steps"][0]))
        log, record = self.runtime(row, {})
        self.assertIsNotNone(log.samples[0].error)
        self.assertEqual(record["result"]["provider_dispatches"], 1)
        self.assertEqual(record["result"]["accounting"]["estimated_usage"]["input_tokens"], 20)
        self.assertEqual(record["result"]["accounting"]["measured_usage"]["input_tokens"], 0)
        self.assertEqual(sum(value.input_tokens for value in log.stats.model_usage.values()), 21)

    def test_native_commit_deadline_retains_prefix_and_abstention(self):
        row = runtime_row(source(self.root / "source"), commit_clock=[0.0, 1.0])
        row["steps"].append(deepcopy(row["steps"][0]))
        log, record = self.runtime(row, {"status": "budget_exhausted", "provider_dispatches": 1,
            "commits.0.prediction.reason": "run_incomplete", "commits.0.prediction.probability": None})
        self.assertEqual(next(iter(log.samples[0].scores.values())).value, "C")
        self.assertEqual(len(record["result"]["commits"][0]["claims"]), 1)

    def test_native_hook_failure_is_telemetry_not_admission_authority(self):
        row = runtime_row(source(self.root / "source"), hook_fault=True)
        log, record = self.runtime(row, {"status": "completed", "provider_dispatches": 1})
        self.assertEqual(next(iter(log.samples[0].scores.values())).value, "C")
        self.assertEqual(len(record["result"]["commits"][0]["claims"]), 2)
        self.assertEqual(record["result"]["telemetry_faults"], ("declared_optional_hook_exception_after_durable_before_event",))

    def test_native_missing_required_hook_cannot_be_success(self):
        async def omitted(self, data):
            pass
        row = runtime_row(source(self.root / "source"))
        with patch.object(WitnessHooks, "on_before_model_generate", omitted):
            log, record = self.runtime(row, {})
        self.assertIsNotNone(log.samples[0].error)
        self.assertEqual(record["result"]["status"], "error")
        self.assertEqual(record["result"]["commits"], ())
        self.assertEqual(record["result"]["accounting"]["estimated_usage"]["input_tokens"], 20)

    def test_native_future_program_gate_has_zero_provider_entries(self):
        def mutate(documents):
            documents["case"]["task"] = "T6"
            documents["case"]["program"]["availability"]["record_public_at"] = "2025-01-01"
        row = runtime_row(source(self.root / "source", mutate=mutate))
        log, record = self.runtime(row, {})
        self.assertIsNotNone(log.samples[0].error)
        self.assertEqual(record["result"]["provider_entries"], 0)
        self.assertEqual(record["result"]["accounting"]["calls"], 0)

    def test_native_hook_request_mutation_is_rejected_by_provider_guard(self):
        row = runtime_row(source(self.root / "source"), hook_mutate_request=True)
        log, record = self.runtime(row, {})
        self.assertIsNotNone(log.samples[0].error)
        self.assertEqual(record["result"]["provider_entries"], 1)
        self.assertEqual(record["result"]["provider_dispatches"], 0)
        self.assertEqual(record["result"]["accounting"]["estimated_usage"]["input_tokens"], 20)


if __name__ == "__main__":
    unittest.main()
