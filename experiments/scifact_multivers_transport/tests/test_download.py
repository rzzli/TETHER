"""Invented transport controls; no real endpoints, payloads or model loading."""
from __future__ import annotations

import copy
import hashlib
import io
import json
from email.message import Message
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.scifact_multivers_transport.download import (
    AcquisitionError, ALLOWED_HOSTS, CHUNK_BYTES, acquire, validate_manifest, verify_journal, supervise_process,
)


REVISION = "a" * 40
VERSION = "InventedVersion01"
PAYLOAD = b"invented payload bytes"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def asset(kind="wheel", payload=PAYLOAD):
    common = {"kind": kind, "expected_bytes": len(payload), "expected_sha256": digest(payload)}
    if kind == "wheel":
        return {**common, "logical_id": "invented-1.0-py3-none-any.whl",
                "url": "https://files.pythonhosted.org/packages/ab/cd/invented-1.0-py3-none-any.whl"}
    if kind == "checkpoint":
        return {**common, "logical_id": "fever_sci.ckpt", "expected_sha256": None,
                "url": "https://scifact.s3.us-west-2.amazonaws.com/longchecker/latest/checkpoints/fever_sci.ckpt?versionId=" + VERSION,
                "expected_version_id": VERSION, "expected_etag": "0123456789abcdef0123456789abcdef-2",
                "local_sha256_required_before_deserialization": True}
    return {**common, "logical_id": "vocab.json", "expected_sha256": None,
            "url": "https://huggingface.co/allenai/longformer-large-4096/resolve/" + REVISION + "/vocab.json",
            "expected_revision": REVISION, "expected_git_blob_sha1": blob(payload),
            "local_sha256_required_before_use": True}


def manifest(assets=None):
    assets = assets or [asset()]
    return {"schema": "bounded-sc02-acquisition-v1", "status": "planned_only_no_payloads_downloaded",
            "assets": assets, "total_payload_bytes": sum(a["expected_bytes"] for a in assets),
            "maximum_total_payload_bytes": 9000000000, "preserve_existing_downloader": True,
            "unique_attempt_directory_required": True,
            "receipt_fields": ["logical_id", "source_url", "final_url", "started_utc", "completed_utc", "bytes", "sha256", "http_etag", "http_version_id", "http_repo_commit", "status"],
            "stop_conditions": ["unexpected_length", "hash_mismatch", "version_or_revision_mismatch", "aggregate_cap_exceeded", "redirect_outside_source_host_allowlist"],
            "allowed_source_hosts": list(ALLOWED_HOSTS)}


class FakeResponse:
    def __init__(self, row, payload=PAYLOAD, headers=None, status=200, final_url=None, failure=None):
        self.stream = io.BytesIO(payload)
        self.status = status
        self.headers = {"Content-Length": str(len(payload)), "Content-Encoding": "identity"}
        if row["kind"] == "checkpoint":
            self.headers.update({"x-amz-version-id": VERSION, "ETag": '"' + row["expected_etag"] + '"'})
        if row["kind"] == "tokenizer_config":
            self.headers.update({"X-Repo-Commit": REVISION, "ETag": '"' + blob(payload) + '"'})
        self.headers.update(headers or {})
        self.url = final_url or row["url"]
        self.failure = failure
        self.reads = []
        self.closed = False

    def read1(self, size):
        self.reads.append(size)
        if self.failure and len(self.reads) > 1:
            raise self.failure
        return self.stream.read(min(size, 5) if self.failure else size)

    def geturl(self):
        return self.url

    def close(self):
        self.closed = True


class ManifestTests(unittest.TestCase):
    def test_all_asset_kinds_and_exact_aggregate_are_valid(self):
        value = manifest([asset(), asset("checkpoint"), asset("tokenizer_config")])
        self.assertEqual(validate_manifest(value)["total_payload_bytes"], 3 * len(PAYLOAD))

    def test_wrong_total_cap_and_unknown_fields_rejected(self):
        for changes in ({"total_payload_bytes": 1}, {"maximum_total_payload_bytes": 9000000001},
                        {"maximum_total_payload_bytes": True}, {"retry": 1}, {"unique_attempt_directory_required": False}):
            with self.subTest(changes=changes), self.assertRaises(AcquisitionError):
                validate_manifest({**manifest(), **changes})

    def test_unsafe_urls_paths_and_logical_ids_rejected(self):
        for change in ({"logical_id": "../escape.whl"}, {"logical_id": "CON.whl"},
                       {"logical_id": "x.whl:stream"}, {"url": "http://files.pythonhosted.org/a.whl"},
                       {"url": "https://files.pythonhosted.org.evil.invalid/a.whl"},
                       {"url": "https://user:secret@files.pythonhosted.org/a.whl"},
                       {"url": "https://files.pythonhosted.org:8443/a.whl"},
                       {"url": "https://files.pythonhosted.org/packages/%2e%2e/x.whl"}):
            with self.subTest(change=change), self.assertRaises(AcquisitionError):
                validate_manifest(manifest([{**asset(), **change}]))

    def test_duplicate_case_insensitive_outputs_and_missing_upstream_hash_rejected(self):
        for assets in ([asset(), asset()], [{**asset(), "expected_sha256": None}]):
            with self.assertRaises(AcquisitionError):
                validate_manifest(manifest(assets))

    def test_mutable_hf_revision_or_wrong_checkpoint_version_is_rejected(self):
        for kind, change in (("tokenizer_config", {"url": asset("tokenizer_config")["url"].replace(REVISION, "main")}),
                             ("checkpoint", {"expected_version_id": "different"}),
                             ("checkpoint", {"local_sha256_required_before_deserialization": False})):
            with self.assertRaises(AcquisitionError):
                validate_manifest(manifest([{**asset(kind), **change}]))


class AcquisitionTests(unittest.TestCase):
    def run_fake(self, root, rows=None, responder=None, **kwargs):
        rows = rows or [asset()]
        value = manifest(rows)
        path = root / "manifest.json"
        path.write_bytes((json.dumps(value) + "\n").encode("utf-8"))
        from experiments.scifact_multivers_transport import download
        source_sha = digest(Path(download.__file__).read_bytes())
        responses, calls = [], []
        def opener(url, timeout, allowed_hosts, on_redirect):
            calls.append(url)
            row = next(a for a in rows if a["url"] == url)
            result = responder(row) if responder else FakeResponse(row)
            responses.append(result)
            return result
        receipt = acquire(path, digest(path.read_bytes()), source_sha, root / "output", open_response=opener, **kwargs)
        return receipt, responses, calls

    def test_success_streams_and_receipts_bind_bytes_and_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt, responses, calls = self.run_fake(root, [asset(), asset("checkpoint"), asset("tokenizer_config")])
            self.assertEqual(receipt["status"], "PASS")
            self.assertEqual(len(calls), 3)
            self.assertEqual({f["relative_path"].split("/")[0] for f in receipt["files"]}, {"wheel", "checkpoint", "tokenizer"})
            for row in receipt["files"]:
                self.assertEqual((root / "output" / row["relative_path"]).read_bytes(), PAYLOAD)
                self.assertEqual(row["sha256"], digest(PAYLOAD))
                self.assertTrue((root / "output" / (row["relative_path"] + ".receipt.json")).is_file())
            self.assertTrue(all(r.closed and max(r.reads) <= CHUNK_BYTES for r in responses))
            records = verify_journal(root / "output" / "journal.jsonl")
            self.assertEqual(records[0]["event"], "acquisition_started")
            self.assertEqual(records[-1]["event"], "acquisition_completed")

    def test_size_hash_header_status_and_redirect_failures_are_terminal(self):
        scenarios = (
            (asset(), lambda a: FakeResponse(a, b"bad")),
            (asset(), lambda a: FakeResponse(a, b"x" * len(PAYLOAD))),
            (asset(), lambda a: FakeResponse(a, headers={"Content-Encoding": "gzip"})),
            (asset(), lambda a: FakeResponse(a, status=206)),
            (asset(), lambda a: FakeResponse(a, final_url="https://evil.invalid/payload")),
            (asset("checkpoint"), lambda a: FakeResponse(a, headers={"x-amz-version-id": "wrong"})),
            (asset("checkpoint"), lambda a: FakeResponse(a, headers={"ETag": '"wrong"'})),
            (asset("tokenizer_config"), lambda a: FakeResponse(a, headers={"X-Repo-Commit": "b" * 40})),
            (asset("tokenizer_config"), lambda a: FakeResponse(a, b"x" * len(PAYLOAD), {"ETag": '"' + a["expected_git_blob_sha1"] + '"'})),
        )
        for row, responder in scenarios:
            with self.subTest(kind=row["kind"]), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaises(AcquisitionError):
                    self.run_fake(root, [row], responder)
                self.assertTrue((root / "output" / "FAILED.json").is_file())
                self.assertFalse((root / "output" / "RECEIPT.json").exists())
                records = verify_journal(root / "output" / "journal.jsonl")
                self.assertEqual(records[-1]["event"], "acquisition_failed")

    def test_short_or_overlong_stream_is_rejected_even_when_header_matches(self):
        for payload in (PAYLOAD[:-1], PAYLOAD + b"extra"):
            with self.subTest(size=len(payload)), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaises(AcquisitionError):
                    self.run_fake(root, responder=lambda a: FakeResponse(a, payload, {"Content-Length": str(len(PAYLOAD))}))
                self.assertFalse((root / "output/wheel" / asset()["logical_id"]).exists())

    def test_duplicate_length_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            def responder(row):
                response = FakeResponse(row)
                response.headers = Message()
                response.headers.add_header("Content-Length", str(len(PAYLOAD)))
                response.headers.add_header("Content-Length", str(len(PAYLOAD)))
                return response
            with self.assertRaisesRegex(AcquisitionError, "duplicate"):
                self.run_fake(Path(directory), responder=responder)

    def test_midstream_interrupt_retains_partial_and_no_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            responses = []
            def responder(row):
                response = FakeResponse(row, failure=KeyboardInterrupt())
                responses.append(response)
                return response
            with self.assertRaises(KeyboardInterrupt):
                self.run_fake(root, responder=responder)
            self.assertEqual(len(responses), 1)
            partial = root / "output/wheel" / (asset()["logical_id"] + ".partial")
            self.assertEqual(partial.read_bytes(), PAYLOAD[:5])
            self.assertTrue(responses[0].closed)
            self.assertEqual(verify_journal(root / "output/journal.jsonl")[-1]["event"], "acquisition_failed")

    def test_no_clobber_even_if_output_exists_or_destination_appears_during_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "output").mkdir()
            (root / "output/sentinel").write_bytes(b"retain")
            with self.assertRaises((FileExistsError, AcquisitionError)):
                self.run_fake(root)
            self.assertEqual((root / "output/sentinel").read_bytes(), b"retain")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def responder(row):
                (root / "output/wheel" / row["logical_id"]).write_bytes(b"retain")
                return FakeResponse(row)
            with self.assertRaises((FileExistsError, AcquisitionError)):
                self.run_fake(root, responder=responder)
            self.assertEqual((root / "output/wheel" / asset()["logical_id"]).read_bytes(), b"retain")

    def test_soft_total_deadline_and_manifest_source_pins_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            counter = iter([0.0, 7201.0, 7202.0, 7203.0, 7204.0])
            with self.assertRaisesRegex(AcquisitionError, "deadline"):
                self.run_fake(root, clock=lambda: next(counter))
            self.assertTrue((root / "output/FAILED.json").is_file())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "manifest.json"
            path.write_bytes(b"{}\n")
            for manifest_hash, source_hash in (("0" * 64, "0" * 64), (digest(path.read_bytes()), "0" * 64)):
                with self.assertRaisesRegex(AcquisitionError, "hash"):
                    acquire(path, manifest_hash, source_hash, root / "output")
                self.assertFalse((root / "output").exists())

    def test_journal_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_fake(root)
            path = root / "output/journal.jsonl"
            path.write_bytes(path.read_bytes().replace(b"acquisition_completed", b"acquisition_invented"))
            with self.assertRaises(AcquisitionError):
                verify_journal(path)


class SupervisorTests(unittest.TestCase):
    def test_cli_interrupt_records_terminal_failure_in_owned_reserved_root(self):
        from experiments.scifact_multivers_transport import download
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "manifest.json"
            path.write_bytes((json.dumps(manifest()) + "\n").encode("utf-8"))
            argv = ["download", "--manifest", str(path), "--manifest-sha256", digest(path.read_bytes()),
                    "--source-sha256", digest(Path(download.__file__).read_bytes()), "--output", str(root / "output")]
            with patch.object(sys, "argv", argv), patch.object(download, "supervise_process", side_effect=KeyboardInterrupt()), patch.object(download, "_emit"):
                self.assertEqual(download.main(), 1)
            self.assertTrue((root / "output/SUPERVISOR-STARTED.json").is_file())
            self.assertTrue((root / "output/SUPERVISOR-FAILED.json").is_file())
            self.assertEqual(verify_journal(root / "output/journal.jsonl")[-1]["event"], "supervisor_failed")

    def test_real_tiny_child_without_heartbeat_is_stopped(self):
        command = [sys.executable, "-I", "-B", "-c", "import time; time.sleep(5)"]
        with self.assertRaisesRegex(AcquisitionError, "progress"):
            supervise_process(command, total_seconds=2, stall_seconds=0.2)

    def test_real_tiny_child_heartbeat_and_success(self):
        command = [sys.executable, "-I", "-B", "-c", 'import json; print(json.dumps({"type":"heartbeat"}),flush=True)']
        result = supervise_process(command, total_seconds=2, stall_seconds=1)
        self.assertEqual(result["exit_code"], 0)

    def test_total_deadline_is_not_extended_by_heartbeats(self):
        command = [sys.executable, "-I", "-B", "-c", 'import time,json\nfor i in range(200):\n print(json.dumps({"type":"heartbeat"}),flush=True)\n time.sleep(.01)']
        with self.assertRaisesRegex(AcquisitionError, "deadline"):
            supervise_process(command, total_seconds=0.2, stall_seconds=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
