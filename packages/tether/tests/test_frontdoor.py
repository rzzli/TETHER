"""Fictional JSON/demo front-door checks; no provider or model calls."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import threading
import tomllib
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from asof import cli as legacy
from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, fingerprint
from tether import _cli as cli
from tether import _presentation as layer


class FrontDoorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tether-frontdoor-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "outer"

    def complete(self, argv=None):
        argv = argv or ["demo", "--output", str(self.output)]
        return layer.create_outer(self.output, argv)

    def changed_stat(self, path, **changes):
        original = Path.stat
        info = original(path)
        values = {name: getattr(info, name) for name in
                  ("st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")}
        values.update(changes)
        replacement = SimpleNamespace(**values)
        def changed(member, *args, **kwargs):
            if member == path and kwargs.get("follow_symlinks", True):
                return replacement
            return original(member, *args, **kwargs)
        return changed

    def reseal(self, change=None, event_change=None):
        """Rehash attacker edits to exercise semantic checks beyond byte integrity."""
        manifest = json.loads((self.output / layer.MANIFEST).read_text())
        manifest["artifacts"] = {n: layer._descriptor(self.output, n) for n in manifest["artifacts"]}
        if change:
            change(manifest)
        (self.output / layer.MANIFEST).write_bytes(canonical(manifest) + b"\n")
        mh = layer.digest((self.output / layer.MANIFEST).read_bytes())
        events = [dict(e) for e in read_chain(self.output / layer.JOURNAL)]
        events[-1]["details"] = dict(events[-1]["details"], manifest_sha256=mh)
        if event_change:
            event_change(events)
        previous, payload = None, b""
        for i, event in enumerate(events):
            event = {k: v for k, v in event.items() if k != "sha256"}
            event.update(sequence=i, previous_sha256=previous)
            event["sha256"] = fingerprint(event)
            previous = event["sha256"]
            payload += canonical(event) + b"\n"
        (self.output / layer.JOURNAL).write_bytes(payload)
        receipt = json.loads((self.output / layer.RECEIPT).read_text())
        receipt.update(manifest_sha256=mh, journal_sha256=layer.digest(payload))
        (self.output / layer.RECEIPT).write_bytes(canonical(receipt) + b"\n")

    def test_distribution_and_license_are_separate_from_legacy_core(self):
        project = tomllib.loads((PROJECT / "pyproject.toml").read_text())
        self.assertEqual(project["project"]["name"], "tether-target-agents")
        self.assertEqual(project["project"]["version"], "0.4.0")
        self.assertEqual(project["project"]["dependencies"], ["asof-target-agents==0.3.11"])
        self.assertEqual(project["project"]["optional-dependencies"]["ingest"], ["pyarrow==21.0.0"])
        self.assertEqual(project["tool"]["setuptools"]["packages"]["find"]["include"], ["tether", "tether.*"])
        self.assertEqual((PROJECT / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())

    def test_help_version_and_legacy_parser_are_independent(self):
        for argv, expected in [(["--help"], "usage: tether"), (["--version"], "TETHER 0.4.0"),
                               (["run", "--help"], "usage: tether run")]:
            stream = io.StringIO()
            with redirect_stdout(stream), self.assertRaises(SystemExit) as stop:
                cli.main(argv)
            self.assertEqual(stop.exception.code, 0)
            self.assertIn(expected, stream.getvalue())
        self.assertEqual(legacy.parser().prog, "asof")

    def test_invalid_arguments_are_branded_and_never_reserve_or_dispatch(self):
        stream = io.StringIO()
        with patch.object(layer, "invoke_engine") as engine, redirect_stderr(stream), self.assertRaises(SystemExit):
            cli.main(["run", "--output", str(self.output)])
        engine.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertIn("tether run: error:", stream.getvalue())

    def test_output_rewrite_removes_both_legacy_argument_forms(self):
        result = layer._engine_args(["demo", "--output=first", "--output", "second"], self.root / "engine")
        self.assertEqual(result, ["demo", "--output", str(self.root / "engine")])

    def test_metadata_oversize_is_rejected_before_open_without_large_allocation(self):
        for name in (layer.RECEIPT, layer.MANIFEST, layer.FAILURE):
            with self.subTest(name=name):
                path = self.root / name
                path.write_bytes(b"{}")
                with patch.object(Path, "stat", new=self.changed_stat(path, st_size=layer.MAX_METADATA_BYTES + 1)), \
                     patch.object(Path, "open", side_effect=AssertionError("must not open oversized metadata")) as opened, \
                     self.assertRaises(ContractError):
                    layer._json(path)
                opened.assert_not_called()

    def test_nonregular_metadata_is_rejected_before_open(self):
        path = self.root / "fictional-fifo.json"
        path.write_bytes(b"{}")
        with patch.object(Path, "stat", new=self.changed_stat(path, st_mode=stat.S_IFIFO | 0o600)), \
             patch.object(Path, "open", side_effect=AssertionError("must not open nonregular input")) as opened, \
             self.assertRaises(ContractError):
            layer._json(path)
        opened.assert_not_called()

    def test_link_and_reparse_metadata_are_rejected_before_open(self):
        path = self.root / "fictional-link.json"
        path.write_bytes(b"{}")
        original = Path.lstat
        for mode, attributes in ((stat.S_IFLNK, 0), (stat.S_IFREG, 0x400)):
            with self.subTest(mode=mode, attributes=attributes):
                def linked(member, *args, **kwargs):
                    if member == path:
                        return SimpleNamespace(st_mode=mode | 0o600, st_file_attributes=attributes)
                    return original(member, *args, **kwargs)
                with patch.object(Path, "lstat", new=linked), \
                     patch.object(Path, "open", side_effect=AssertionError("must not open link")) as opened, \
                     self.assertRaises(ContractError):
                    layer._read(path)
                opened.assert_not_called()

    def test_read_rejects_actual_midread_file_mutation(self):
        path = self.root / "changing.json"
        path.write_bytes(b'{"fictional":1}')
        original = Path.open
        mutated = []
        class ChangingStream:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return self.stream.__exit__(*args)
            def fileno(self):
                return self.stream.fileno()
            def read(self, count):
                self.assertion = count
                block = self.stream.read(count)
                if not mutated:
                    mutated.append(True)
                    with original(path, "wb") as writer:
                        writer.write(b'{"fictional":999}')
                return block
        def changing(member, mode="r", *args, **kwargs):
            stream = original(member, mode, *args, **kwargs)
            return ChangingStream(stream) if member == path and mode == "rb" else stream
        with patch.object(Path, "open", new=changing), self.assertRaisesRegex(ContractError, "changed"):
            layer._read(path)
        self.assertTrue(mutated)

    def test_read_uses_bounded_chunks_and_a_separate_dossier_limit(self):
        path = self.root / "small.bin"
        path.write_bytes(b"123456789")
        original, counts = Path.open, []
        class MeasuredStream:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return self.stream.__exit__(*args)
            def fileno(self):
                return self.stream.fileno()
            def read(self, count):
                counts.append(count)
                return self.stream.read(count)
        def measured(member, mode="r", *args, **kwargs):
            stream = original(member, mode, *args, **kwargs)
            return MeasuredStream(stream) if member == path and mode == "rb" else stream
        with patch.object(Path, "open", new=measured):
            self.assertEqual(layer._read(path), b"123456789")
        self.assertTrue(all(0 < n <= 1024 * 1024 for n in counts))
        self.assertEqual(layer.MAX_METADATA_BYTES, 64 * 1024 * 1024)
        self.assertEqual(layer.MAX_DOSSIER_BYTES, 256 * 1024 * 1024)
        with self.assertRaisesRegex(ContractError, "read bound"):
            layer._read(path, max_bytes=4)
        self.assertEqual(layer._read(path, max_bytes=layer.MAX_DOSSIER_BYTES), b"123456789")

    def test_oversize_outer_and_engine_journals_are_not_opened_by_inspect(self):
        for relative, key in [(layer.JOURNAL, "journal_inspection_error"), ("engine/journal.jsonl", "engine")]:
            with self.subTest(relative=relative):
                output = self.root / relative.split("/")[0]
                output.mkdir(exist_ok=True)
                path = output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"tiny fixture")
                with patch.object(Path, "stat", new=self.changed_stat(path, st_size=layer.MAX_METADATA_BYTES + 1)), \
                     patch.object(Path, "open", side_effect=AssertionError("oversized journal must not open")):
                    answer = layer.inspect_outer(output)
                if key == "engine":
                    self.assertEqual(answer[key]["inspection_error"], "ContractError")
                else:
                    self.assertEqual(answer[key], "ContractError")

    def test_legacy_verify_journal_preflight_blocks_delegate(self):
        self.output.mkdir()
        path = self.output / "journal.jsonl"
        path.write_bytes(b"tiny fixture")
        with patch.object(Path, "stat", new=self.changed_stat(path, st_size=layer.MAX_METADATA_BYTES + 1)), \
             patch.object(layer, "invoke_engine") as engine, redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["verify", "--run-dir", str(self.output)]), 2)
        engine.assert_not_called()

    def test_real_demo_is_sealed_and_source_inclusively_verified(self):
        result = self.complete()
        engine_before = {p.name: p.read_bytes() for p in (self.output / "engine").iterdir()}
        expected = layer.project_dossier(engine_before["dossier.md"])
        self.assertEqual((self.output / "dossier.md").read_bytes(), expected)
        answer = layer.verify_outer(self.output, result["receipt_sha256"])
        self.assertTrue(answer["external_anchor_checked"])
        self.assertEqual(answer["engine"]["source_binding"], "current_originals")
        self.assertEqual(engine_before, {p.name: p.read_bytes() for p in (self.output / "engine").iterdir()})
        self.assertFalse(layer.verify_outer(self.output)["external_anchor_checked"])

    def test_cli_demo_and_inspect_do_not_redispatch(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(cli.main(["demo", "--output", str(self.output)]), 0)
        answer = json.loads(stdout.getvalue())
        self.assertEqual(answer["brand"], "TETHER")
        with patch.object(layer, "invoke_engine") as engine, redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["inspect-run", "--run-dir", str(self.output)]), 0)
            self.assertEqual(cli.main(["verify", "--run-dir", str(self.output), "--receipt-sha256", answer["receipt_sha256"]]), 0)
        engine.assert_not_called()

    def test_outer_header_tamper_rejected_even_after_rehash(self):
        self.complete()
        dossier = self.output / "dossier.md"
        dossier.write_bytes(dossier.read_bytes().replace(b"# TETHER dossier:", b"# FALSE dossier:", 1))
        self.reseal()
        with self.assertRaisesRegex(ContractError, "projection differs"):
            layer.verify_outer(self.output)

    def test_outer_body_tamper_rejected_even_after_rehash(self):
        self.complete()
        dossier = self.output / "dossier.md"
        dossier.write_bytes(dossier.read_bytes() + b"\nFabricated claim.\n")
        self.reseal()
        with self.assertRaisesRegex(ContractError, "projection differs"):
            layer.verify_outer(self.output)

    def test_receipt_and_external_anchor_tamper_reject(self):
        result = self.complete()
        with self.assertRaisesRegex(ContractError, "external receipt"):
            layer.verify_outer(self.output, "0" * 64)
        path = self.output / layer.RECEIPT
        receipt = json.loads(path.read_text())
        receipt["role"] = "agent_evidence"
        path.write_bytes(canonical(receipt) + b"\n")
        with self.assertRaisesRegex(ContractError, "envelope"):
            layer.verify_outer(self.output)
        self.assertNotEqual(result["receipt_sha256"], layer.digest(path.read_bytes()))

    def test_boolean_byte_metadata_does_not_alias_integer_zero(self):
        self.complete()
        def change(manifest):
            self.assertEqual(manifest["artifacts"]["engine-stderr.txt"]["bytes"], 0)
            manifest["artifacts"]["engine-stderr.txt"]["bytes"] = False
        self.reseal(change)
        with self.assertRaisesRegex(ContractError, "hash/bytes/path"):
            layer.verify_outer(self.output)

    def test_rechained_journal_cannot_contradict_launcher_proof(self):
        self.complete()
        def change(events):
            events[1]["details"] = dict(events[1]["details"], launcher_proof_sha256="0" * 64)
        self.reseal(event_change=change)
        with self.assertRaisesRegex(ContractError, "dispatch/proof binding"):
            layer.verify_outer(self.output)

    def test_source_tamper_uses_only_copied_synthetic_json(self):
        sources = self.root / "fictional-sources"
        shutil.copytree(ROOT / "src/asof/demo/v2", sources)
        argv = ["run", "--case", str(sources / "case.json"), "--snapshot", str(sources / "snapshot.json"),
                "--scorer", str(sources / "scorer.json"), "--output", str(self.output)]
        self.complete(argv)
        source = sources / "evidence.json"
        source.write_bytes(source.read_bytes() + b"\n")
        with self.assertRaisesRegex(ContractError, "Source integrity|Source hash"):
            layer.verify_outer(self.output)

    def test_engine_receipt_tamper_rejects(self):
        self.complete()
        path = self.output / "engine/receipt.json"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaises(ContractError):
            layer.verify_outer(self.output)

    def test_wrapper_file_tamper_rejects_without_editing_executing_source(self):
        copied = self.root / "fictional-package"
        shutil.copytree(PROJECT / "src/tether", copied, ignore=shutil.ignore_patterns("__pycache__"))
        with patch.object(layer, "_package_root", return_value=copied):
            self.complete()
            target = copied / "_cli.py"
            target.write_bytes(target.read_bytes() + b"\n# fictional changed launcher\n")
            with self.assertRaisesRegex(ContractError, "launcher code/version"):
                layer.verify_outer(self.output)

    def test_unlisted_artifact_and_directory_reject(self):
        self.complete()
        extra = self.output / "unlisted.txt"
        extra.write_text("fictional")
        with self.assertRaisesRegex(ContractError, "whole artifact inventory"):
            layer.verify_outer(self.output)
        extra.unlink()
        (self.output / "empty-extra").mkdir()
        with self.assertRaisesRegex(ContractError, "directory inventory"):
            layer.verify_outer(self.output)

    def test_existing_output_is_never_changed(self):
        self.output.mkdir()
        original = self.output / "owner.txt"
        original.write_bytes(b"existing owner")
        with self.assertRaises(FileExistsError):
            self.complete()
        self.assertEqual(list(self.output.iterdir()), [original])
        self.assertEqual(original.read_bytes(), b"existing owner")

    def test_concurrent_reservation_dispatches_exactly_once(self):
        count, lock = [], threading.Lock()
        def engine(argv):
            with lock:
                count.append(argv)
            return layer.EngineResult(3)
        def run():
            try:
                layer.create_outer(self.output, ["demo", "--output", str(self.output)], engine=engine)
            except Exception as error:
                return type(error)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(len(count), 1)
        self.assertCountEqual(outcomes, [layer.EngineFailure, FileExistsError])
        self.assertTrue((self.output / layer.FAILURE).is_file())
        self.assertFalse((self.output / layer.RECEIPT).exists())

    def test_nonzero_engine_retains_attempt_and_has_no_success_receipt(self):
        with self.assertRaises(layer.EngineFailure):
            layer.create_outer(self.output, ["demo", "--output", str(self.output)],
                               engine=lambda argv: layer.EngineResult(3, b"out", b"asof: failure\n"))
        self.assertEqual((self.output / "engine-stdout.txt").read_bytes(), b"out")
        self.assertEqual(layer.inspect_outer(self.output)["failure"]["status"], "failed")
        self.assertFalse((self.output / layer.RECEIPT).exists())
        with self.assertRaisesRegex(ContractError, "retained failure"):
            layer.verify_outer(self.output)

    def test_engine_interrupt_exit_is_retained_as_interrupted(self):
        with self.assertRaises(layer.EngineInterrupted):
            layer.create_outer(self.output, ["demo", "--output", str(self.output)],
                               engine=lambda argv: layer.EngineResult(130))
        self.assertEqual(layer.inspect_outer(self.output)["failure"]["status"], "interrupted")
        self.assertEqual(read_chain(self.output / layer.JOURNAL)[-1]["event"], "run_interrupted")

    def test_interruption_retains_inner_journal_and_never_retries(self):
        calls = []
        def interrupted(argv):
            calls.append(argv)
            inner = RunJournal(self.output / "engine")
            inner.append("fictional_started")
            inner.close()
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            layer.create_outer(self.output, ["demo", "--output", str(self.output)], engine=interrupted)
        before = (self.output / "engine/journal.jsonl").read_bytes()
        self.assertEqual(layer.inspect_outer(self.output)["failure"]["status"], "interrupted")
        self.assertEqual(len(calls), 1)
        self.assertEqual((self.output / "engine/journal.jsonl").read_bytes(), before)

    def test_subprocess_interruption_reaps_one_dispatch(self):
        process = Mock()
        process.poll.return_value = None
        process.returncode = -1
        process.communicate.side_effect = [KeyboardInterrupt(), (b"out", b"err")]
        with patch.object(layer.subprocess, "Popen", return_value=process) as spawn, self.assertRaises(layer.EngineInterrupted):
            layer.invoke_engine(["demo", "--output", "fictional"])
        spawn.assert_called_once()
        process.terminate.assert_called_once()
        self.assertEqual(process.communicate.call_count, 2)

    def test_pipe_oserror_and_systemexit_preserve_primary_and_reap_once(self):
        for primary in (OSError("fictional pipe error"), SystemExit(7)):
            with self.subTest(error=type(primary).__name__):
                process = Mock()
                process.poll.return_value = None
                process.returncode = -1
                process.communicate.side_effect = [primary, (b"partial output", b"accounting")]
                with patch.object(layer.subprocess, "Popen", return_value=process) as spawn, self.assertRaises(type(primary)) as caught:
                    layer.invoke_engine(["demo", "--output", "fictional"])
                self.assertIs(caught.exception, primary)
                self.assertEqual(primary.tether_engine_result.stdout, b"partial output")
                self.assertTrue(primary.tether_process_reaped)
                spawn.assert_called_once()
                process.terminate.assert_called_once()
                process.wait.assert_called_once_with(timeout=layer.CLEANUP_SECONDS)

    def test_cleanup_failure_preserves_primary_and_partial_bytes_in_failure(self):
        primary = OSError("fictional primary")
        primary.output = b"before cleanup"
        primary.stderr = b"usage before cleanup"
        process = Mock()
        process.poll.return_value = None
        process.returncode = None
        process.terminate.side_effect = OSError("fictional terminate failure")
        process.kill.side_effect = OSError("fictional kill failure")
        process.wait.side_effect = layer.subprocess.TimeoutExpired("fictional", 5)
        process.communicate.side_effect = [primary, layer.subprocess.TimeoutExpired("fictional", 5), OSError("fictional drain failure")]
        with patch.object(layer.subprocess, "Popen", return_value=process) as spawn, self.assertRaises(OSError) as caught:
            layer.create_outer(self.output, ["demo", "--output", str(self.output)])
        self.assertIs(caught.exception, primary)
        spawn.assert_called_once()
        self.assertEqual(process.communicate.call_count, 3)
        self.assertFalse((self.output / layer.RECEIPT).exists())
        failure = json.loads((self.output / layer.FAILURE).read_text())
        self.assertIs(failure["engine_process_reaped"], False)
        self.assertEqual(failure["error_class"], "OSError")
        self.assertIn("process_kill", [x["operation"] for x in failure["cleanup_errors"]])
        captures = {row["path"]: (self.output / row["path"]).read_bytes() for row in failure["partial_streams"]}
        self.assertIn(b"before cleanup", captures.values())
        self.assertIn(b"usage before cleanup", captures.values())

    def test_failure_metadata_fault_does_not_replace_primary(self):
        primary = OSError("fictional original failure")
        def engine(argv):
            raise primary
        original = layer._save
        def fail_metadata(path, payload):
            if path.name == layer.FAILURE:
                raise OSError("fictional secondary storage failure")
            return original(path, payload)
        with patch.object(layer, "_save", side_effect=fail_metadata), self.assertRaises(OSError) as caught:
            layer.create_outer(self.output, ["demo", "--output", str(self.output)], engine=engine)
        self.assertIs(caught.exception, primary)

    def test_journal_close_failure_prevents_success_receipt(self):
        class BadClose(RunJournal):
            def close(self):
                super().close()
                raise OSError("fictional close failure")
        with patch.object(layer, "RunJournal", BadClose), self.assertRaises(OSError):
            self.complete()
        self.assertTrue((self.output / layer.FAILURE).exists())
        self.assertFalse((self.output / layer.RECEIPT).exists())

    def test_constructor_failure_keeps_readable_outer_failure(self):
        def broken(output):
            output.mkdir()
            (output / "journal.jsonl").write_bytes(b"")
            raise OSError("fictional first journal write")
        with patch.object(layer, "RunJournal", side_effect=broken), self.assertRaises(OSError):
            self.complete()
        inspected = layer.inspect_outer(self.output)
        self.assertEqual(inspected["failure"]["stage"], "reservation")
        self.assertEqual(inspected["journal_inspection_error"], "ContractError")

    def test_failure_append_error_does_not_suppress_failure_seal(self):
        class BadFailure(RunJournal):
            def fail(self, *args):
                raise OSError("fictional failure append")
        with patch.object(layer, "RunJournal", BadFailure), self.assertRaises(layer.EngineFailure):
            layer.create_outer(self.output, ["demo", "--output", str(self.output)], engine=lambda argv: layer.EngineResult(2))
        failure = json.loads((self.output / layer.FAILURE).read_text())
        self.assertEqual(failure["cleanup_errors"][0]["operation"], "journal_failure_append")

    def test_receipt_readback_failure_quarantines_published_receipt(self):
        original = layer._save
        def fail_after(path, payload):
            original(path, payload)
            if path.name == layer.RECEIPT:
                raise OSError("fictional final readback error")
        with patch.object(layer, "_save", side_effect=fail_after), self.assertRaises(OSError):
            self.complete()
        self.assertFalse((self.output / layer.RECEIPT).exists())
        self.assertTrue((self.output / "tether-receipt.failed.json").exists())
        self.assertTrue((self.output / layer.FAILURE).exists())

    def test_outputs_only_cannot_qualify_outer_and_delegate_errors_are_branded(self):
        self.complete()
        stream = io.StringIO()
        with redirect_stderr(stream):
            self.assertEqual(cli.main(["verify", "--run-dir", str(self.output), "--outputs-only"]), 2)
        self.assertIn("tether:", stream.getvalue())
        with patch.object(layer, "invoke_engine", return_value=layer.EngineResult(2, stderr=b"asof: bad fixture\n")), redirect_stderr(stream):
            self.assertEqual(cli.main(["verify", "--run-dir", str(self.root / "absent")]), 2)
        self.assertIn("tether: bad fixture", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
