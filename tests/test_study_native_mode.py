"""Approved launch capability and leases; fake owned process only."""

from dataclasses import FrozenInstanceError
import hashlib
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, encode, parse_json
from asof.study import native_mode as mode
from asof.study import process as process_module
from tests import test_study_process as processes
from tests import test_study_tokenization as tokens


class NativeModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tokens.TokenizationArtifactTests.setUpClass()
        cls.model = tokens.TokenizationArtifactTests.model
        cls.server = cls.model / "runtime/llama-server.exe"
        cls.server.write_bytes(b"Invented server never executed")
        cls.resource = dict(
            schema_version=1,
            kind="approved_owned_native_server_v2",
            tokenizer_resource_sha256=mode.tokenization.RESOURCE_SHA256,
            server=dict(
                relative_path="runtime/llama-server.exe",
                sha256=hashlib.sha256(cls.server.read_bytes()).hexdigest(),
                bytes=cls.server.stat().st_size,
            ),
        )
        cls.patch = patch.object(mode, "_resource", return_value=cls.resource)
        cls.patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.patch.stop()
        tokens.TokenizationArtifactTests.tearDownClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=tokens.TEMP_ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "run"
        self.journal = RunJournal(self.root, kind="build")
        self.addCleanup(self.journal.close)
        self.process = processes.Process()
        self.factory = Mock(side_effect=self.spawn)
        self.config = mode.NativeExecutionConfig(
            self.model,
            55581,
            process_factory=self.factory,
            availability_probe=lambda *_: None,
            listener_owner=lambda *_: True,
            health_probe=lambda *_: True,
        )
        self.spec = tokens.TokenizationArtifactTests.spec
        (self.root / "tokenizer-spec.json").write_bytes(canonical(self.spec))

    def spawn(self, argv, **kwargs):
        kwargs["stderr"].write(b"n_slots = 1, n_ctx_slot = 16384\n")
        kwargs["stderr"].flush()
        return self.process

    def test_config_is_explicit_immutable_local_and_fixed_command(self):
        with self.assertRaises(FrozenInstanceError):
            self.config.port = 80
        for port in (True, 0, 65536):
            with self.assertRaises(ContractError):
                mode.NativeExecutionConfig(self.model, port)
        desc = self.config.describe(self.spec)
        self.assertEqual(desc["model_alias"], "asof-interpretation-v2")
        argv = self.config.server_spec(self.spec, time.monotonic() + 30).argv
        self.assertIn("--offline", argv)
        self.assertEqual(argv[argv.index("--host") + 1], "127.0.0.1")
        self.assertEqual(argv[argv.index("--parallel") + 1], "1")
        self.assertEqual(argv[argv.index("--ctx-size") + 1], "16384")

    def test_lease_checks_assets_and_blocks_mutation_then_releases(self):
        end = time.monotonic() + 30
        with self.config.locked(self.spec, end):
            self.config.assert_active()
            with self.assertRaises(OSError):
                self.server.write_bytes(b"changed")
        with self.assertRaises(ContractError):
            self.config.assert_active()
        self.factory.assert_not_called()

    def test_owned_start_context_and_terminal_are_retained(self):
        end = time.monotonic() + 30
        with self.config.locked(self.spec, end):
            with self.config.running(self.root, self.journal, self.spec, end) as owner:
                self.assertEqual(owner.terminal_record["pid"], 4242)
                context = self.config.context(self.spec, owner)
                self.assertEqual(context["owner_pid"], 4242)
                self.assertEqual(
                    context["model_provenance"]["runtime_sha256"],
                    self.resource["server"]["sha256"],
                )
        terminal = parse_json((self.root / "native/server-terminal.json").read_bytes())
        self.assertTrue(terminal["server_stopped"])
        self.process.terminate.assert_called_once()
        self.assertEqual(
            [r["event"] for r in read_chain(self.root / "journal.jsonl")],
            [
                "build_reserved",
                "native_preparing",
                "server_started",
                "server_ready",
                "native_context_qualified",
                "server_terminal",
                "native_stopped",
            ],
        )

    def test_missing_or_modified_server_fails_before_spawn(self):
        original = self.server.read_bytes()
        try:
            self.server.write_bytes(b"changed")
            with self.assertRaises(ContractError):
                with self.config.locked(self.spec, time.monotonic() + 30):
                    self.fail("bad asset admitted")
        finally:
            self.server.write_bytes(original)
        self.factory.assert_not_called()

    def test_context_failure_stops_owned_process_and_keeps_primary(self):
        def bad(argv, **kwargs):
            return self.process

        config = mode.NativeExecutionConfig(
            self.model,
            55581,
            process_factory=bad,
            availability_probe=lambda *_: None,
            listener_owner=lambda *_: True,
            health_probe=lambda *_: True,
        )
        end = time.monotonic() + 30
        with config.locked(self.spec, end), self.assertRaises(ContractError):
            with config.running(self.root, self.journal, self.spec, end):
                self.fail("context not proved")
        self.process.terminate.assert_called_once()
        self.assertTrue((self.root / "native/server-terminal.json").is_file())

    def test_archived_locations_cannot_authorize_replay(self):
        end = time.monotonic() + 30
        with self.config.locked(self.spec, end):
            with self.config.running(self.root, self.journal, self.spec, end):
                pass
        with self.assertRaises(ContractError):
            mode.NativeExecutionConfig.from_run(self.root, None)
        restored = mode.NativeExecutionConfig.from_run(self.root, {"model": self.model})
        self.assertEqual(restored.describe(self.spec), self.config.describe(self.spec))
        self.factory.assert_called_once()

    def test_parent_expiry_during_launch_hashing_prevents_spawn(self):
        now = [time.monotonic()]
        end = now[0] + 10
        original = process_module.verify_file

        def delayed(*args):
            result = original(*args)
            now[0] = end + 1
            return result

        with self.config.locked(self.spec, end):
            with (
                patch.object(time, "monotonic", side_effect=lambda: now[0]),
                patch.object(process_module, "verify_file", side_effect=delayed),
            ):
                with self.assertRaises(TimeoutError):
                    with self.config.running(self.root, self.journal, self.spec, end):
                        pass
        self.factory.assert_not_called()

    def test_cleanup_wait_is_limited_by_current_parent_time(self):
        spec = self.config.server_spec(self.spec, time.monotonic() + 30)
        clock = processes.Clock()
        owner = process_module.OwnedServer(
            spec,
            bindings={
                p["logical_id"]: self.model / a["relative_path"]
                for p, a in zip(
                    (*spec.required_inputs, spec.executable), mode._assets(self.spec)
                )
            },
            output=self.root,
            journal=self.journal,
            listener_owner=lambda *_: True,
            health_probe=lambda *_: True,
            process_factory=lambda *a, **kw: self.process,
            availability_probe=lambda *_: None,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
            parent_deadline=0.5,
        )
        with owner:
            clock.now = 0.49
        self.assertLessEqual(self.process.wait.call_args.kwargs["timeout"], 0.011)

    def test_archived_native_clock_cannot_move_backwards(self):
        end = time.monotonic() + 30
        with self.config.locked(self.spec, end):
            with self.config.running(self.root, self.journal, self.spec, end):
                pass
            events = encode(read_chain(self.root / "journal.jsonl"))
            for row in events:
                if row["event"] == "native_context_qualified":
                    row["details"]["elapsed_seconds"] = -1
            with self.assertRaises(ContractError):
                self.config.verify_archive(
                    self.root, self.spec, events, successful=True
                )

    def test_simulation_cannot_start_default_real_process(self):
        config = mode.NativeExecutionConfig(
            self.model, 55581, execution_scope="simulated_native_transport"
        )
        end = time.monotonic() + 30
        with (
            config.locked(self.spec, end),
            patch.object(
                mode, "OwnedServer", side_effect=AssertionError("No real launch")
            ),
        ):
            with self.assertRaises(ContractError):
                with config.running(self.root, self.journal, self.spec, end):
                    pass


if __name__ == "__main__":
    unittest.main()
