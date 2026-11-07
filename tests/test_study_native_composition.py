"""Whole native-mode integration with explicit simulated transport and fake assets."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest
import os
import sys
import hashlib
from datetime import timedelta
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from contextlib import ExitStack
from tether_engine.contracts import Category, Profile, Snapshot, SourceNode, TemporalClass
from unittest.mock import Mock, patch

from tether_engine.serde import ContractError, canonical, encode, parse_json
from tether_engine.study import (
    authority_four_arm as composition,
    native,
    native_interpretation,
    source_preparation,
    tokenization,
)
from tether_engine.study.interpretation_interface import request_from_payload
from tether_engine.study.native_mode import NativeExecutionConfig, ALIAS
from tests import test_study_collected_composition as collected
from tests import test_study_native_mode as mode_helpers
from tests import test_study_native as http_helpers
from tests import test_study_process as process_helpers


class NativeCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mode_helpers.NativeModeTests.setUpClass()
        cls.temp = tempfile.TemporaryDirectory(dir=collected.tokens.TEMP_ROOT)
        cls.root = Path(cls.temp.name)
        cls.source, cls.built = collected.fixture_source(cls.root)
        cls.real_build = staticmethod(source_preparation._build)
        cls.raw_patch = patch.object(
            source_preparation, "_build", return_value=cls.built
        )
        cls.raw_patch.start()
        cls.posts = []
        cls.processes = []

        def spawn(argv, **kwargs):
            kwargs["stderr"].write(b"n_slots = 1, n_ctx_slot = 16384\n")
            kwargs["stderr"].flush()
            process = process_helpers.Process()
            cls.processes.append(process)
            return process

        cls.config = NativeExecutionConfig(
            mode_helpers.NativeModeTests.model,
            55581,
            execution_scope="simulated_native_transport",
            process_factory=spawn,
            availability_probe=lambda *_: None,
            listener_owner=lambda *_: True,
            health_probe=lambda *_: True,
        )

        def connection(*args, **kwargs):
            conn = Mock()
            conn.sock = Mock()

            def request(method, path, body, headers):
                payload = parse_json(body)
                original = request_from_payload(payload)
                text = original["source_request"]["evidence"][0]["statement"]
                document = dict(
                    answer_status="answered",
                    claims=[
                        dict(
                            kind="source_report",
                            text=text,
                            quote_refs=["Q0"],
                            limitations=[],
                        )
                    ],
                    unresolved=[],
                    abstention_reason=None,
                )
                cls.posts.append(payload)
                response = dict(
                    prompt=payload["prompt"],
                    model=ALIAS,
                    generation_settings={
                        k: encode(payload[k])
                        for k in ("seed", "temperature", "n_predict", "stop", "stream")
                    },
                    truncated=False,
                    stop=True,
                    stop_type="eos",
                    stopped_limit=False,
                    stopping_word="",
                    tokens_evaluated=20,
                    tokens_predicted=5,
                    content=json.dumps(document),
                )
                conn.getresponse.return_value = http_helpers.Response(
                    canonical(response)
                )

            conn.request.side_effect = request
            return conn

        cls.spawn = staticmethod(spawn)
        cls.connection_factory = staticmethod(connection)

        real_run = tokenization._run_child
        with (
            patch.object(
                tokenization,
                "_run_child",
                side_effect=lambda *a: real_run(
                    *a, process_factory=collected.HundredTokenChild
                ),
            ),
            patch.object(native.http.client, "HTTPConnection", side_effect=connection),
            patch.object(native, "Timer"),
            patch.object(
                composition.AuthorityRecordedVerifier,
                "document",
                side_effect=AssertionError("No recorded stimulus"),
            ),
        ):
            cls.result = composition.smoke(
                cls.root / "run",
                collected.tokens.TokenizationArtifactTests.authority,
                collected.tokens.TokenizationArtifactTests.roots,
                collected_source=cls.source,
                native_execution=cls.config,
            )
        cls.initial_posts = tuple(cls.posts)
        cls.initial_processes = tuple(cls.processes)

    @classmethod
    def tearDownClass(cls):
        cls.raw_patch.stop()
        cls.temp.cleanup()
        mode_helpers.NativeModeTests.tearDownClass()

    def test_all_arms_source_and_usage_replay_without_recorded_consumption(self):
        self.assertEqual(len(self.initial_posts), 6)
        self.assertEqual(len(self.initial_processes), 1)
        self.assertEqual(self.result["actual_model_calls"], 0)
        self.assertEqual(self.result["simulated_native_calls"], 6)
        self.assertEqual(self.result["simulated_transport_usage"]["input_tokens"], 120)
        self.assertEqual(self.result["recorded_calls"], 0)
        self.assertEqual(self.result["pure_invocations"], 2)
        self.assertEqual(self.result["native_processes"], 0)
        with patch.object(
            native.http.client,
            "HTTPConnection",
            side_effect=AssertionError("No replay connection"),
        ):
            checked = composition.verify(
                self.root / "run",
                self.result["receipt_sha256"],
                source_roots=self.source.roots,
                native_roots={"model": self.config.model_root},
            )
        self.assertEqual(checked, self.result)
        self.assertEqual((self.source._active, self.config._active), (0, 0))

    def test_native_roots_required_and_original_locations_are_metadata(self):
        with self.assertRaises(ContractError):
            composition.verify(
                self.root / "run",
                self.result["receipt_sha256"],
                source_roots=self.source.roots,
            )
        with self.assertRaises(ContractError):
            composition.verify(
                self.root / "run",
                self.result["receipt_sha256"],
                source_roots=self.source.roots,
                native_roots={"wrong": self.config.model_root},
            )

    def test_history_is_same_arm_accepted_quote_sources(self):
        first = parse_json((self.root / "run/cells/00/request.json").read_bytes())
        last = parse_json((self.root / "run/cells/05/request.json").read_bytes())
        self.assertEqual(first["feedback"], [])
        self.assertEqual(len(last["feedback"]), 4)
        self.assertTrue(all(r["source_ids"] == ["E0"] for r in last["feedback"]))
        response = parse_json((self.root / "run/cells/05/response.json").read_bytes())
        self.assertEqual(response["features"], {})
        self.assertIsNone(response["clinical_probability"])

    def test_shutdown_and_existing_output_prevent_duplicate_dispatch(self):
        terminal = parse_json(
            (self.root / "run/native/server-terminal.json").read_bytes()
        )
        self.assertTrue(terminal["server_stopped"])
        before = len(self.posts)
        with self.assertRaises(FileExistsError):
            composition.smoke(
                self.root / "run",
                {},
                {},
                collected_source=self.source,
                native_execution=self.config,
            )
        self.assertEqual(len(self.posts), before)

    def test_run_relocation_uses_logical_case_parent(self):
        path = self.root / "restored"
        shutil.copytree(self.root / "run", path)
        enabled = [True]
        attempts = []
        original = os.path.normcase(str((self.root / "run").absolute()))

        def guard(event, args):
            if (
                enabled[0]
                and event in ("open", "os.listdir", "os.scandir")
                and args
                and isinstance(args[0], (str, bytes, os.PathLike))
            ):
                value = os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
                try:
                    blocked = os.path.commonpath([value, original]) == original
                except ValueError:
                    blocked = False
                if blocked:
                    attempts.append(value)
                    raise PermissionError("Original run unavailable")

        sys.addaudithook(guard)
        try:
            with patch.object(
                native.http.client,
                "HTTPConnection",
                side_effect=AssertionError("No connection"),
            ):
                checked = composition.verify(
                    path,
                    self.result["receipt_sha256"],
                    source_roots=self.source.roots,
                    native_roots={"model": self.config.model_root},
                )
        finally:
            enabled[0] = False
        self.assertEqual(checked, self.result)
        self.assertEqual(attempts, [])

    def run_failure(
        self,
        name,
        *,
        response_error=None,
        interrupt=False,
        timeout=False,
        close_error=False,
        accounting_error=False,
        native_duration=None,
        write_error=False,
        server_cleanup_error=False,
    ):
        base = len(self.posts)

        def spawn(*a, **kw):
            process = self.spawn(*a, **kw)
            if server_cleanup_error:
                process.terminate.side_effect = OSError("fixture owned cleanup")
            return process

        config = NativeExecutionConfig(
            self.config.model_root,
            55581,
            execution_scope="simulated_native_transport",
            process_factory=spawn,
            availability_probe=lambda *_: None,
            listener_owner=lambda *_: True,
            health_probe=lambda *_: True,
        )

        def connection(*args, **kwargs):
            conn = self.connection_factory(*args, **kwargs)
            original = conn.request.side_effect

            def request(*a, **kw):
                original(*a, **kw)
                if len(self.posts) - base == 2:
                    if interrupt:
                        conn.getresponse.side_effect = KeyboardInterrupt()
                    elif timeout:
                        conn.getresponse.side_effect = TimeoutError("fixture timeout")
                    elif response_error:
                        value = parse_json(conn.getresponse.return_value.body)
                        value["content"] = response_error
                        conn.getresponse.return_value = http_helpers.Response(
                            canonical(value)
                        )
                    if close_error:
                        conn.close.side_effect = OSError("fixture transport close")

            conn.request.side_effect = request
            return conn

        real_run = tokenization._run_child
        with ExitStack() as stack:
            if native_duration is not None:
                original_generate = (
                    native_interpretation.TokenQuotedNativeBackend.generate
                )
                generated = []

                def changed_duration(backend, *args, **kwargs):
                    if generated:
                        raise RuntimeError(
                            "Expected first duration rejection before a second call"
                        )
                    result = original_generate(backend, *args, **kwargs)
                    generated.append(True)
                    wrapper = parse_json(result.content)
                    wrapper["elapsed_seconds"] = native_duration
                    return replace(result, content=canonical(wrapper))

                stack.enter_context(
                    patch.object(
                        native_interpretation.TokenQuotedNativeBackend,
                        "generate",
                        new=changed_duration,
                    )
                )
            stack.enter_context(
                patch.object(
                    tokenization,
                    "_run_child",
                    side_effect=lambda *a: real_run(
                        *a, process_factory=collected.HundredTokenChild
                    ),
                )
            )
            stack.enter_context(
                patch.object(
                    native.http.client, "HTTPConnection", side_effect=connection
                )
            )
            stack.enter_context(patch.object(native, "Timer"))
            if accounting_error:

                def counts(*a, **kw):
                    raise OSError("fixture unreadable accounting")

                stack.enter_context(
                    patch.object(composition, "native_accounting", side_effect=counts)
                )
            if write_error:
                original_write = composition._write

                def write(root, name, value):
                    if name == "summary.json":
                        raise OSError("fixture summary write")
                    return original_write(root, name, value)

                stack.enter_context(
                    patch.object(composition, "_write", side_effect=write)
                )
            try:
                composition.smoke(
                    self.root / name,
                    collected.tokens.TokenizationArtifactTests.authority,
                    collected.tokens.TokenizationArtifactTests.roots,
                    collected_source=self.source,
                    native_execution=config,
                )
            except BaseException as error:
                return error, config, len(self.posts) - base
        self.fail("Failure scenario unexpectedly succeeded")

    def test_failed_second_answer_retains_usage_and_stops_without_retry(self):
        error, config, calls = self.run_failure(
            "malformed",
            response_error='{"answer_status":"answered","claims":[],"unresolved":[],"abstention_reason":null}',
        )
        self.assertIsInstance(error, ContractError)
        self.assertEqual(calls, 2)
        marker = parse_json((self.root / "malformed/failure.json").read_bytes())
        self.assertEqual(marker["accepted_cells"], [0])
        self.assertEqual(marker["simulated_transport_usage"]["input_tokens"], 40)
        self.assertFalse((self.root / "malformed/receipt.json").exists())
        self.assertTrue(
            parse_json(
                (self.root / "malformed/native/server-terminal.json").read_bytes()
            )["server_stopped"]
        )
        self.assertEqual((config._active, self.source._active), (0, 0))

    def test_native_duration_above_report_rejected_before_acceptance(self):
        error, config, calls = self.run_failure(
            "native-report-duration", native_duration=20.0
        )
        self.assertIsInstance(error, ContractError)
        self.assertRegex(str(error), "Native duration exceeds child report")
        marker = parse_json(
            (self.root / "native-report-duration/failure.json").read_bytes()
        )
        self.assertEqual(marker["accepted_cells"], [])
        self.assertEqual(calls, 1)
        self.assertEqual(marker["simulated_transport_usage"]["input_tokens"], 20)
        self.assertFalse((self.root / "native-report-duration/receipt.json").exists())
        self.assertEqual((config._active, self.source._active), (0, 0))

    def test_interruption_retains_partial_wrapper_and_primary(self):
        error, _, calls = self.run_failure("interrupt", interrupt=True)
        self.assertIsInstance(error, KeyboardInterrupt)
        self.assertEqual(calls, 2)
        wrapper = parse_json(
            (self.root / "interrupt/cells/01/native-failure-wrapper.json").read_bytes()
        )
        self.assertEqual(wrapper["error_class"], "KeyboardInterrupt")
        self.assertFalse((self.root / "interrupt/receipt.json").exists())

    def test_failure_marker_survives_unreadable_accounting(self):
        error, _, calls = self.run_failure(
            "bad-accounting", response_error="{", accounting_error=True
        )
        self.assertIsInstance(error, ContractError)
        marker = parse_json((self.root / "bad-accounting/failure.json").read_bytes())
        self.assertEqual(marker["accounting_status"], "unavailable")
        self.assertEqual(marker["accounting_error_class"], "OSError")
        self.assertEqual(calls, 2)

    def test_wrong_source_category_fails_before_server_or_quote(self):
        config = NativeExecutionConfig(
            self.config.model_root,
            55581,
            execution_scope="simulated_native_transport",
            process_factory=Mock(),
        )
        with patch.object(
            composition, "tokenize_prompt", side_effect=AssertionError("No quote")
        ):
            with self.assertRaisesRegex(ContractError, "category"):
                composition.smoke(
                    self.root / "wrong-source",
                    {},
                    {},
                    collected_source=replace(self.source, category=Category.GENETICS),
                    native_execution=config,
                )
        config.process_factory.assert_not_called()

    def test_timeout_keeps_unknown_attempt_and_conservative_reservation(self):
        error, _, calls = self.run_failure("timeout", timeout=True)
        self.assertIsInstance(error, TimeoutError)
        marker = parse_json((self.root / "timeout/failure.json").read_bytes())
        self.assertEqual(calls, 2)
        self.assertEqual(marker["unknown_simulated_model_calls"], 1)
        self.assertGreater(marker["conservative_unresolved_usage"]["input_tokens"], 0)
        self.assertEqual(marker["accepted_cells"], [0])

    def test_close_failure_recovers_known_usage_without_accepting_answer(self):
        error, _, calls = self.run_failure("close-failure", close_error=True)
        self.assertIsInstance(error, OSError)
        marker = parse_json((self.root / "close-failure/failure.json").read_bytes())
        self.assertEqual(calls, 2)
        self.assertEqual(marker["accepted_cells"], [0])
        self.assertEqual(marker["recovered_transport_usage"]["input_tokens"], 20)
        self.assertEqual(marker["simulated_transport_usage"]["input_tokens"], 40)

    def test_root_write_failure_keeps_all_usage_and_no_success_receipt(self):
        error, config, calls = self.run_failure("write-failure", write_error=True)
        self.assertIsInstance(error, OSError)
        marker = parse_json((self.root / "write-failure/failure.json").read_bytes())
        self.assertEqual(calls, 6)
        self.assertEqual(marker["accepted_cells"], list(range(6)))
        self.assertFalse((self.root / "write-failure/receipt.json").exists())
        self.assertEqual((config._active, self.source._active), (0, 0))

    def test_owned_cleanup_failure_is_terminal_not_a_success(self):
        error, _, calls = self.run_failure("server-cleanup", server_cleanup_error=True)
        self.assertIsInstance(error, OSError)
        terminal = parse_json(
            (self.root / "server-cleanup/native/server-terminal.json").read_bytes()
        )
        self.assertTrue(terminal["server_stopped"])
        self.assertTrue(terminal["secondary_failures"])
        self.assertEqual(calls, 6)
        self.assertFalse((self.root / "server-cleanup/receipt.json").exists())

    def test_concurrent_reservation_blocks_duplicate_native_dispatch(self):
        held = Event()
        release = Event()
        config = NativeExecutionConfig(
            self.config.model_root,
            55581,
            execution_scope="simulated_native_transport",
            process_factory=Mock(),
        )

        def block(*a, **kw):
            held.set()
            if not release.wait(10):
                raise RuntimeError("fixture scheduling timeout")
            raise TimeoutError("fixture pre-dispatch stop")

        def run():
            try:
                return composition.smoke(
                    self.root / "concurrent",
                    {},
                    {},
                    collected_source=self.source,
                    native_execution=config,
                )
            except BaseException as error:
                return error

        with (
            patch.object(composition, "prepare_retrieval", side_effect=block),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            first = pool.submit(run)
            self.assertTrue(held.wait(10))
            second = pool.submit(run)
            try:
                self.assertIsInstance(second.result(timeout=10), FileExistsError)
            finally:
                release.set()
            self.assertIsInstance(first.result(timeout=10), TimeoutError)
        config.process_factory.assert_not_called()

    def test_real_lineage_gates_future_and_evaluation_only_before_native_io(self):
        for name in ("future", "evaluation"):
            directory = self.root / ("lineage-" + name)
            directory.mkdir()
            source, _ = collected.fixture_source(directory)
            authority = parse_json(source.authority_path.read_bytes())
            catalog_path = Path(source.roots["project"]) / "catalog.json"
            catalog_path.write_bytes(
                canonical(
                    dict(
                        schema_version=1,
                        datasets=[dict(dataset_id="fixture", roles=["agent_evidence"])],
                    )
                )
            )
            authority["files"]["catalog"].update(
                sha256=hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
                bytes=catalog_path.stat().st_size,
            )
            source.authority_path.write_bytes(canonical(authority))
            source = replace(
                source,
                authority_sha256=hashlib.sha256(
                    source.authority_path.read_bytes()
                ).hexdigest(),
            )
            template = collected.sources.CompilerTests()
            template.setUp()
            case = template.case
            available = case.hypothesis.availability
            if name == "future":
                future = case.cutoff + timedelta(days=1)
                available = replace(
                    available,
                    known_public_by=future,
                    retrieved_at=future.date(),
                    evidence_ref="a" * 64,
                )
            node = SourceNode(
                "raw",
                "fixture",
                "v1",
                "unread-raw.json",
                "a" * 64,
                "evaluation_only" if name == "evaluation" else "agent_evidence",
                available,
                TemporalClass.CONTEMPORARY,
                "https://example.test/input",
            )
            snapshot = Snapshot(
                2,
                "fixture",
                Profile.CONTEMPORARY,
                case.origin,
                False,
                (),
                sources=(node,),
                raw_root=source.roots["project"],
            )
            config = NativeExecutionConfig(
                self.config.model_root,
                55581,
                execution_scope="simulated_native_transport",
                process_factory=Mock(),
            )
            with (
                patch.object(source_preparation, "_build", side_effect=self.real_build),
                patch.object(
                    source_preparation, "decode", side_effect=[case, snapshot]
                ),
                patch.object(
                    composition,
                    "tokenize_prompt",
                    side_effect=AssertionError("No quote before lineage"),
                ),
            ):
                with self.assertRaisesRegex(
                    ContractError, "Ineligible source|Evaluator"
                ):
                    composition.smoke(
                        self.root / ("rejected-" + name),
                        {},
                        {},
                        collected_source=source,
                        native_execution=config,
                    )
            config.process_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
