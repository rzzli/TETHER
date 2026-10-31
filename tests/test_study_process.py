"""Owned process tests use fake processes/probes; no server, model or network."""

from dataclasses import replace
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from asof.serde import ContractError
from asof.study.process import OwnedServer, ServerSpec
from asof.study.proofs import capture_file


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, duration):
        self.now += duration


class Process:
    pid = 4242

    def __init__(self):
        self.code = None
        self.terminate = Mock()
        self.kill = Mock()
        self.wait = Mock(side_effect=self._wait)

    def poll(self):
        return self.code

    def _wait(self, timeout):
        self.code = 0
        return 0


class StudyProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exe = self.root / "server.exe"
        self.exe.write_bytes(b"not executable; never launched")
        self.weights = self.root / "weights.bin"
        self.weights.write_bytes(b"fixture")
        self.output = self.root / "output"
        self.output.mkdir()
        self.spec = ServerSpec(
            (str(self.exe), "--fixture"),
            capture_file(self.exe, "runtime/server.exe"),
            (capture_file(self.weights, "model/weights.bin"),),
            "127.0.0.1",
            55581,
            startup_seconds=0.3,
            terminate_seconds=0.2,
            kill_seconds=0.1,
        )
        self.clock, self.process = Clock(), Process()
        self.journal, self.owner, self.health = (
            Mock(),
            Mock(return_value=True),
            Mock(return_value=True),
        )
        self.factory, self.available = Mock(return_value=self.process), Mock()

    def server(self, **changes):
        values = dict(
            bindings={
                "runtime/server.exe": self.exe,
                "model/weights.bin": self.weights,
            },
            output=self.output,
            journal=self.journal,
            listener_owner=self.owner,
            health_probe=self.health,
            process_factory=self.factory,
            availability_probe=self.available,
            monotonic=self.clock.monotonic,
            sleep=self.clock.sleep,
        )
        values.update(changes)
        return OwnedServer(self.spec, **values)

    def test_success_owns_checks_and_stops_exact_process(self):
        server = self.server()
        with server:
            server.assert_ready()
            self.assertEqual(self.health.call_count, 1)
        self.factory.assert_called_once()
        self.assertFalse(self.factory.call_args.kwargs["shell"])
        self.process.terminate.assert_called_once()
        self.process.kill.assert_not_called()
        self.assertTrue(server.terminal_record["server_stopped"])
        self.assertIsNone(server.terminal_record["peak_native_memory_bytes"])
        with self.assertRaises(TypeError):
            server.terminal_record["started"] = False
        with self.assertRaises(ContractError):
            server.__enter__()

    def test_existing_listener_prevents_launch_and_foreign_cleanup(self):
        self.available.side_effect = OSError("address already in use")
        with self.assertRaises(OSError):
            with self.server():
                pass
        self.factory.assert_not_called()
        self.health.assert_not_called()
        self.process.terminate.assert_not_called()

    def test_wrong_or_modified_executable_and_input_fail_before_launch(self):
        self.weights.write_bytes(b"modified")
        with self.assertRaises(ContractError):
            with self.server():
                pass
        self.factory.assert_not_called()

    def test_foreign_listener_never_receives_health_and_only_owned_child_stops(self):
        self.owner.return_value = False
        with self.assertRaises(TimeoutError):
            with self.server():
                pass
        self.factory.assert_called_once()
        self.health.assert_not_called()
        self.process.terminate.assert_called_once()

    def test_ownership_rechecked_after_health(self):
        self.owner.side_effect = [True, False]
        with self.assertRaises(ContractError):
            with self.server():
                pass
        self.health.assert_called_once()
        self.process.terminate.assert_called_once()

    def test_ownership_lost_before_generation_rejects(self):
        with self.server() as server:
            self.owner.return_value = False
            with self.assertRaises(ContractError):
                server.assert_ready()

    def test_start_event_write_failure_still_cleans_saved_handle(self):
        original = OSError("journal write failed")

        def append(event, **details):
            if event == "server_started":
                raise original

        self.journal.append.side_effect = append
        with self.assertRaises(OSError) as caught:
            with self.server():
                pass
        self.assertIs(caught.exception, original)
        self.process.terminate.assert_called_once()

    def test_log_close_failure_after_spawn_still_cleans_handle(self):
        original_open = Path.open

        class Log:
            def __init__(self, wrapped):
                self.wrapped = wrapped

            def close(self):
                self.wrapped.close()
                raise OSError("log close failed")

        def opened(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            return Log(stream) if path.suffix == ".log" else stream

        with patch.object(Path, "open", opened), self.assertRaises(OSError):
            with self.server():
                pass
        self.factory.assert_called_once()
        self.process.terminate.assert_called_once()

    def test_startup_exit_keeps_logs_without_relaunch(self):
        self.process.code = 12
        server = self.server()
        with self.assertRaises(ContractError):
            with server:
                pass
        self.factory.assert_called_once()
        self.process.terminate.assert_not_called()
        self.assertEqual(server.terminal_record["exit_code"], 12)
        self.assertTrue((self.output / "server.stderr.log").is_file())

    def test_startup_health_timeout_is_bounded_and_no_relaunch(self):
        self.health.side_effect = TimeoutError("health timeout")
        with self.assertRaises(TimeoutError):
            with self.server():
                pass
        self.assertGreater(self.health.call_count, 0)
        self.assertLessEqual(self.health.call_count, 4)
        self.factory.assert_called_once()
        self.process.terminate.assert_called_once()

    def test_terminate_timeout_escalates_only_owned_handle(self):
        self.process.wait.side_effect = [subprocess.TimeoutExpired("fixture", 0.2), 0]
        self.process.kill.side_effect = lambda: setattr(self.process, "code", -9)
        server = self.server()
        with server:
            pass
        self.process.kill.assert_called_once()
        self.assertEqual(
            [c.kwargs["timeout"] for c in self.process.wait.call_args_list], [0.2, 0.1]
        )
        self.assertTrue(server.terminal_record["server_stopped"])

    def test_kill_failure_preserves_primary_interruption(self):
        primary = KeyboardInterrupt("original")
        self.process.wait.side_effect = subprocess.TimeoutExpired("fixture", 0.2)
        self.process.kill.side_effect = PermissionError("cannot kill")
        server = self.server()
        with self.assertRaises(KeyboardInterrupt) as caught:
            with server:
                raise primary
        self.assertIs(caught.exception, primary)
        self.assertFalse(server.terminal_record["server_stopped"])
        self.assertIn("server_cleanup: PermissionError", primary.__notes__)

    def test_cleanup_failure_without_primary_is_not_success(self):
        self.process.terminate.side_effect = PermissionError("cannot terminate")
        server = self.server()
        with self.assertRaises(PermissionError):
            with server:
                pass
        self.process.kill.assert_called_once()
        self.assertTrue(server.terminal_record["server_stopped"])

    def test_health_return_after_deadline_is_not_ready(self):
        def delayed(*args):
            self.clock.now += 1
            return True

        self.health.side_effect = delayed
        with self.assertRaises(TimeoutError):
            with self.server():
                pass
        self.process.terminate.assert_called_once()
        self.assertNotIn(
            "server_ready", [c.args[0] for c in self.journal.append.call_args_list]
        )

    def test_spawn_failure_never_cleans_an_unowned_process(self):
        self.factory.side_effect = OSError("spawn failed")
        with self.assertRaises(OSError):
            with self.server():
                pass
        self.factory.assert_called_once()
        self.process.terminate.assert_not_called()
        self.health.assert_not_called()

    def test_startup_interruption_cleanup_is_explicit(self):
        original = KeyboardInterrupt("startup")
        self.owner.side_effect = original
        with self.assertRaises(KeyboardInterrupt) as caught:
            with self.server():
                pass
        self.assertIs(caught.exception, original)
        self.process.terminate.assert_called_once()

    def test_secondary_terminal_journal_error_preserves_primary(self):
        original = RuntimeError("caller failed")

        def append(event, **details):
            if event == "server_terminal":
                raise OSError("journal failed")

        self.journal.append.side_effect = append
        with self.assertRaises(RuntimeError) as caught:
            with self.server():
                raise original
        self.assertIs(caught.exception, original)
        self.assertIn("server_terminal_journal: OSError", original.__notes__)

    def test_invalid_bounds_and_nonloopback_reject(self):
        for changes in (
            {"port": True},
            {"host": "0.0.0.0"},
            {"startup_seconds": float("inf")},
            {"terminate_seconds": 0},
            {"argv": ()},
        ):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                OwnedServer(
                    replace(self.spec, **changes),
                    bindings={},
                    output=self.output,
                    journal=self.journal,
                    listener_owner=self.owner,
                    health_probe=self.health,
                )


if __name__ == "__main__":
    unittest.main()
