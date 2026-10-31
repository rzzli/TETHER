"""Independent adversarial helper checks; fake process ownership is not attestation."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from asof.serde import ContractError, encode
from asof.study import proofs
from asof.study.process import OwnedServer, ServerSpec


class StudyHelpersPeerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.executable = self.root / "fake.exe"
        self.executable.write_bytes(b"never execute")
        self.output = self.root / "output"
        self.output.mkdir()
        self.proof = proofs.capture_file(self.executable, "runtime/fake.exe")

    def server(self, **changes):
        process = Mock(pid=12345)
        process.poll.return_value = None
        process.wait.side_effect = lambda **kwargs: setattr(
            process.poll, "return_value", 0
        )
        values = dict(
            bindings={"runtime/fake.exe": self.executable},
            output=self.output,
            journal=Mock(),
            listener_owner=Mock(return_value=True),
            health_probe=Mock(return_value=True),
            process_factory=Mock(return_value=process),
            availability_probe=Mock(),
            monotonic=lambda: 0,
            sleep=Mock(),
        )
        values.update(changes)
        return OwnedServer(
            ServerSpec((str(self.executable),), self.proof, (), "127.0.0.1", 55001),
            **values,
        ), process

    def test_spawn_is_recorded_before_fallible_clock(self):
        clock = Mock(side_effect=[0, OSError("clock failure after spawn"), 1])
        server, process = self.server(monotonic=clock)
        with self.assertRaises(OSError):
            server.__enter__()
        process.terminate.assert_called_once()
        self.assertTrue(server.terminal_record["started"])
        self.assertEqual(server.terminal_record["pid"], 12345)

    def test_cleanup_clock_failure_cannot_replace_primary_interrupt(self):
        failing = False

        def clock():
            if failing:
                raise OSError("clock read failed during terminal accounting")
            return 0

        server, process = self.server(monotonic=clock)
        primary = KeyboardInterrupt("original interruption")
        with self.assertRaises(KeyboardInterrupt) as caught:
            with server:
                failing = True
                raise primary
        self.assertIs(caught.exception, primary)
        process.terminate.assert_called_once()
        self.assertTrue(server.terminal_record["server_stopped"])
        self.assertTrue(server.terminal_record["secondary_failures"])

    def test_package_capture_rejects_previously_hashed_code_changed_mid_capture(self):
        package = self.root / "package"
        package.mkdir()
        early = package / "__init__.py"
        early.write_text("original=1\n")
        (package / "later.py").write_text("later=1\n")
        original = proofs.capture_file

        def capture(path, logical):
            result = original(path, logical)
            if logical == "asof/later.py":
                early.write_text("changed_after_hash=2\n")
            return result

        with (
            patch.object(proofs, "_package_root", return_value=package),
            patch.object(proofs, "capture_file", side_effect=capture),
        ):
            with self.assertRaises(ContractError):
                proofs.capture_package_proof({}, ())

    def test_ownership_is_rechecked_at_dispatch_boundary(self):
        owner = Mock(return_value=True)
        server, process = self.server(listener_owner=owner)
        with server:
            owner.return_value = False
            with self.assertRaises(ContractError):
                server.assert_ready()
        process.terminate.assert_called_once()
        self.assertIsNone(server.terminal_record["peak_native_memory_bytes"])
        self.assertEqual(
            server.terminal_record["peak_native_memory_reason"], "Not instrumented"
        )

    def test_cleanup_failure_is_retained_without_foreign_process_action(self):
        server, process = self.server()
        process.terminate.side_effect = OSError("cannot terminate")
        process.kill.side_effect = OSError("cannot kill")
        with self.assertRaises(OSError):
            with server:
                pass
        self.assertFalse(server.terminal_record["server_stopped"])
        self.assertEqual(
            [x["stage"] for x in server.terminal_record["secondary_failures"]],
            ["server_terminate", "server_cleanup"],
        )

    def test_omitted_package_code_proof_rejected(self):
        package = self.root / "package"
        package.mkdir()
        (package / "__init__.py").write_text("original=1\n")
        with patch.object(proofs, "_package_root", return_value=package):
            proof = encode(proofs.capture_package_proof({}, ()))
            proof["code"] = []
            with self.assertRaises(ContractError):
                proofs.verify_package_proof(proof, required_resources=())


if __name__ == "__main__":
    unittest.main()
