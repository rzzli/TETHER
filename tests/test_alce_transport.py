"""Invented bounded acquisition controls; no real network, data or model assets."""
import copy
from concurrent.futures import ThreadPoolExecutor
from email.message import Message
import hashlib
import io
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
import sys
from unittest import mock

from experiments.alce_transport import download as d


class Response:
    def __init__(self, row, payload, *, status=200, headers=None, step=None, fail=None):
        self.status, self.url = status, row["url"]
        self.headers = {"Content-Length": str(row["expected_bytes"]), "Content-Encoding": "identity"}
        if headers: self.headers.update(headers)
        self.stream, self.step, self.fail, self.reads, self.closed = io.BytesIO(payload), step, fail, 0, False

    def geturl(self): return self.url

    def read1(self, maximum):
        self.reads += 1
        if self.fail and self.reads > 1: raise self.fail
        return self.stream.read(min(maximum, self.step or maximum))

    def close(self): self.closed = True


class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.code = d.source_fingerprint()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.approved = self.root / "assets"; self.approved.mkdir()
        self.metadata = self.root / "source.json"; self.metadata.write_bytes(b'{"invented_metadata":true}')
        self.payload = b"Invented fixed public bytes, no scientific contents.\n"
        self.row = dict(id="one", product_id="invented", revision={"kind": "git_commit", "value": "a" * 40},
            url="https://example.org/repo/resolve/" + "a" * 40 + "/one.bin", destination="models/one.bin",
            expected_bytes=len(self.payload), digest={"algorithm": "sha256", "kind": "content", "value": hashlib.sha256(self.payload).hexdigest()},
            metadata_proof=d.capture(self.metadata)[1], rights_reference="https://example.org/terms")
        self.value = dict(schema_version=1, kind=d.KIND, approved_root=str(self.approved),
            limits=dict(max_total_bytes=1024**3, total_seconds=30, network_seconds=2, stall_seconds=5, max_redirects=2),
            allowed_hosts=["example.org", "cdn.example.org"], assets=[self.row])
        self.manifest = self.root / "manifest.json"; self.output = self.approved / "attempt01"
        self.save()

    def save(self):
        self.manifest.write_bytes(d.canonical(self.value) + b"\n")
        self.msha = d.capture(self.manifest)[1]["sha256"]

    def args(self): return self.manifest, self.msha, self.code, self.output

    def fetch(self, response=None, callback=None):
        self.calls = []
        response = response or Response(self.row, self.payload)
        def opener(*args):
            self.calls.append(args)
            if callback: callback(args)
            return response
        return opener

    def test_success_content_digest_and_chunked_length(self):
        response = Response(self.row, self.payload, step=7)
        response.headers.pop("Content-Length")
        value = d.acquire(*self.args(), opener=self.fetch(response))
        self.assertEqual(value["payload_bytes"], len(self.payload))
        self.assertEqual((self.output / "payloads/models/one.bin").read_bytes(), self.payload)
        self.assertFalse((self.output / "RECEIPT.json").exists())
        self.assertFalse(value["hard_parent_supervision"]); self.assertTrue(response.closed)
        self.assertEqual(len(self.calls), 1); self.assertFalse(any((self.output / "partials").iterdir()))
        d.verify_completed(self.output, self.value, d.capture(self.manifest)[1], self.code, time.monotonic()+10)

    def test_git_blob_hash_and_local_sha256_are_distinct(self):
        self.row["digest"] = dict(kind="git_blob", algorithm="sha1",
            value=hashlib.sha1(b"blob " + str(len(self.payload)).encode() + b"\0" + self.payload).hexdigest())
        self.save(); value = d.acquire(*self.args(), opener=self.fetch())
        self.assertEqual(value["files"][0]["git_blob_sha1"], self.row["digest"]["value"])
        self.assertEqual(value["files"][0]["sha256"], hashlib.sha256(self.payload).hexdigest())

    def test_manifest_rejects_unpinned_and_wrong_types(self):
        for change in (lambda x: x["assets"][0].update(expected_bytes=None),
                       lambda x: x["assets"][0].update(digest=None),
                       lambda x: x["limits"].update(total_seconds=True),
                       lambda x: x["limits"].update(max_total_bytes=1),
                       lambda x: x["assets"][0]["revision"].update(value="main"),
                       lambda x: x["assets"].append(copy.deepcopy(x["assets"][0])),
                       lambda x: x["assets"][0].update(destination="../outside"),
                       lambda x: x["assets"][0].update(destination="nul.txt"),
                       lambda x: x["assets"][0].update(destination="folder./file"),
                       lambda x: x["assets"][0].update(url="http://example.org/file")):
            v = copy.deepcopy(self.value); change(v)
            with self.subTest(value=v), self.assertRaises((ValueError, TypeError)): d.validate_manifest(v)
        self.assertFalse(self.output.exists())

    def test_wrong_manifest_code_or_metadata_hash_never_reserves(self):
        opener = mock.Mock()
        for args in ((self.manifest, "b"*64, self.code, self.output), (self.manifest, self.msha, "b"*64, self.output)):
            with self.assertRaises(ValueError): d.acquire(*args, opener=opener)
        self.metadata.write_bytes(b'{"modified":true}')
        with self.assertRaises(ValueError): d.acquire(*self.args(), opener=opener)
        opener.assert_not_called(); self.assertFalse(self.output.exists())

    def test_approved_root_and_control_overlap_fail_before_write(self):
        opener = mock.Mock()
        for out in (self.root / "attempt", self.approved / ".." / "assets" / "attempt", self.approved):
            with self.assertRaises(ValueError): d.acquire(self.manifest, self.msha, self.code, out, opener=opener)
        opener.assert_not_called()

    def test_digest_mismatch_keeps_partial_and_never_retries(self):
        response = Response(self.row, b"x"*len(self.payload))
        with self.assertRaisesRegex(ValueError, "digest"): d.acquire(*self.args(), opener=self.fetch(response))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual((self.output / "partials/one.part").read_bytes(), b"x"*len(self.payload))
        self.assertFalse((self.output / "payloads/models/one.bin").exists())
        self.assertTrue((self.output / "FAILED.json").is_file())
        self.assertFalse((self.output / "WORKER-RECEIPT.json").exists())

    def test_truncated_and_overflow_bodies_retain_bounded_bytes(self):
        for name, payload in (("short", self.payload[:-1]), ("long", self.payload+b"x")):
            self.output = self.approved / name
            with self.assertRaises(ValueError): d.acquire(*self.args(), opener=self.fetch(Response(self.row, payload)))
            failure = d.strict_json((self.output / "FAILED.json").read_bytes())
            self.assertEqual(failure["received_body_bytes"], len(payload))
            self.assertLessEqual((self.output / "partials/one.part").stat().st_size, len(self.payload))

    def test_interrupt_retains_partial_counter_and_unexecuted_assets(self):
        second = copy.deepcopy(self.row); second.update(id="two", destination="two.bin")
        self.value["assets"].append(second); self.save()
        response = Response(self.row, self.payload, step=7, fail=KeyboardInterrupt("invented"))
        with self.assertRaises(KeyboardInterrupt): d.acquire(*self.args(), opener=self.fetch(response))
        failure = d.strict_json((self.output / "FAILED.json").read_bytes())
        self.assertEqual(failure["received_body_bytes"], 7)
        self.assertEqual(failure["uncompleted_assets"], ["one", "two"])
        self.assertEqual((self.output / "partials/one.part").read_bytes(), self.payload[:7])
        self.assertEqual(len(self.calls), 1)

    def test_write_failure_preserves_attempt_without_success(self):
        original = d.write_new
        def write(path, value):
            if Path(path).name == "REQUEST.json": raise OSError("invented disk write failure")
            return original(path, value)
        with mock.patch.object(d, "write_new", side_effect=write), self.assertRaises(OSError):
            d.acquire(*self.args(), opener=self.fetch())
        self.assertTrue((self.output / "FAILED.json").is_file()); self.assertEqual(self.calls, [])

    def test_no_clobber_publish_collision_preserves_both_bytes(self):
        def collide(args):
            (self.output / "payloads/models/one.bin").write_bytes(b"existing")
        with self.assertRaises(FileExistsError): d.acquire(*self.args(), opener=self.fetch(callback=collide))
        self.assertEqual((self.output / "payloads/models/one.bin").read_bytes(), b"existing")
        self.assertEqual((self.output / "partials/one.part").read_bytes(), self.payload)
        self.assertFalse((self.output / "WORKER-RECEIPT.json").exists())

    def test_same_output_race_allows_exactly_one_attempt(self):
        barrier = threading.Barrier(2); original = d.controls; count = []
        def controls(*args, **kwargs):
            value = original(*args, **kwargs); barrier.wait(5); return value
        def run():
            try:
                d.acquire(*self.args(), opener=lambda *args: (count.append(1) or Response(self.row, self.payload)))
                return "complete"
            except FileExistsError: return "collision"
        with mock.patch.object(d, "controls", side_effect=controls), ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertCountEqual(results, ["complete", "collision"]); self.assertEqual(len(count), 1)
        self.assertFalse((self.output / "FAILED.json").exists())

    def test_deadline_after_blocking_read_rejects_before_publication(self):
        now = [0.0]
        response = Response(self.row, self.payload)
        original = response.read1
        def read(n): now[0] = 31; return original(n)
        response.read1 = read
        with self.assertRaisesRegex(ValueError, "Deadline"): d.acquire(*self.args(), opener=self.fetch(response), clock=lambda: now[0])
        self.assertFalse((self.output / "payloads/models/one.bin").exists())
        self.assertTrue((self.output / "FAILED.json").exists())

    def test_http_range_encoding_length_and_revision_fail_closed(self):
        cases = [(206, {}), (200, {"Content-Range": "bytes 0-1/2"}), (200, {"Content-Encoding": "gzip"}),
                 (200, {"Content-Length": "999"}), (200, {"X-Repo-Commit": "b"*40})]
        for index, (status, headers) in enumerate(cases):
            self.output = self.approved / ("headers" + str(index))
            response = Response(self.row, self.payload, status=status, headers=headers)
            with self.assertRaises(ValueError): d.acquire(*self.args(), opener=self.fetch(response))
            self.assertEqual(response.reads, 0); self.assertTrue(response.closed)

    def test_duplicate_headers_rejected(self):
        response = Response(self.row, self.payload); response.headers = Message()
        response.headers.add_header("Content-Length", str(len(self.payload)))
        response.headers.add_header("Content-Length", str(len(self.payload)))
        with self.assertRaises(ValueError): d.acquire(*self.args(), opener=self.fetch(response))
        self.assertEqual(response.reads, 0)

    def test_redirect_authority_bound_and_signed_query_redaction(self):
        target = "https://cdn.example.org/opaque/blob?Signature=PRIVATE-FICTIONAL"
        response = Response(self.row, self.payload); response.url = target
        def redirect(args): args[3](self.row["url"], target, 302)
        d.acquire(*self.args(), opener=self.fetch(response, redirect))
        receipt = (self.output / "receipts/one.json").read_bytes()
        self.assertNotIn(b"PRIVATE-FICTIONAL", receipt); self.assertIn(b"query_sha256", receipt)
        self.output = self.approved / "badredirect"
        with self.assertRaises(ValueError):
            d.acquire(*self.args(), opener=self.fetch(callback=lambda args: args[3](self.row["url"], "https://evil.example.org/blob", 302)))

    def test_url_and_redirect_limit_actual_handler_without_network(self):
        handlers = []
        fake = mock.Mock(); fake.open.return_value = object()
        def build(*args): handlers.extend(args); return fake
        with mock.patch.object(d.urllib.request, "build_opener", side_effect=build):
            d.open_response(self.row["url"], 1, self.value["allowed_hosts"], lambda *a: None, 1)
        handler = handlers[1]; request = d.urllib.request.Request(self.row["url"])
        handler.redirect_request(request, None, 302, "", {}, "https://cdn.example.org/a")
        with self.assertRaisesRegex(ValueError, "Redirect"): handler.redirect_request(request, None, 302, "", {}, "https://cdn.example.org/b")
        for url in ("http://example.org/a", "https://user@example.org/a", "https://example.org:443/a",
                    "https://example.org/../a", "https://example.org/%252e%252e/a"):
            with self.subTest(url=url), self.assertRaises(ValueError): d.safe_url(url, self.value["allowed_hosts"])

    def test_changed_manifest_after_fetch_retains_completed_asset_but_no_worker_success(self):
        def change(args): self.manifest.write_bytes(b"changed")
        with self.assertRaises(ValueError): d.acquire(*self.args(), opener=self.fetch(callback=change))
        self.assertTrue((self.output / "payloads/models/one.bin").exists())
        self.assertFalse((self.output / "WORKER-RECEIPT.json").exists())

    def test_published_corruption_and_orphan_rejected_by_independent_rehash(self):
        d.acquire(*self.args(), opener=self.fetch())
        path = self.output / "payloads/models/one.bin"
        path.write_bytes(b"x" * len(self.payload))
        with self.assertRaises(ValueError): d.verify_completed(self.output, self.value, d.capture(self.manifest)[1], self.code, time.monotonic()+10)
        path.write_bytes(self.payload); (self.output / "payloads/orphan").write_bytes(b"unexpected")
        with self.assertRaises(ValueError): d.verify_completed(self.output, self.value, d.capture(self.manifest)[1], self.code, time.monotonic()+10)

    def test_retry_existing_attempt_never_dispatches(self):
        d.acquire(*self.args(), opener=self.fetch())
        before = (self.output / "WORKER-RECEIPT.json").read_bytes()
        opener = mock.Mock()
        with self.assertRaises(ValueError): d.acquire(*self.args(), opener=opener)
        opener.assert_not_called(); self.assertEqual((self.output / "WORKER-RECEIPT.json").read_bytes(), before)

    def test_worker_invalid_code_never_starts_a_writer_watchdog(self):
        self.output.mkdir()
        argv = ["download.py", "--worker", "--manifest", str(self.manifest), "--manifest-sha256", self.msha,
                "--code-sha256", "b"*64, "--output", str(self.output), "--reservation-sha256", "c"*64]
        with mock.patch.object(d.sys, "argv", argv), mock.patch.object(d, "DeadlineWatchdog") as watchdog:
            with self.assertRaises((ValueError, FileNotFoundError)): d.main()
        watchdog.assert_not_called()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_unknown_empty_payload_directory_rejected(self):
        d.acquire(*self.args(), opener=self.fetch())
        (self.output / "payloads/unlisted-empty").mkdir()
        with self.assertRaises(ValueError):
            d.verify_completed(self.output, self.value, d.capture(self.manifest)[1], self.code, time.monotonic()+10)

    def test_resealed_journal_false_asset_claim_is_rejected(self):
        d.acquire(*self.args(), opener=self.fetch())
        events = d.primitives.verify_journal(self.output / "journal.jsonl")
        (self.output / "journal.jsonl").unlink(); journal = d.Journal(self.output / "journal.jsonl")
        for event in events:
            details = event["details"]
            if event["event"] == "asset_completed": details = dict(details, id="different-asset")
            journal.append(event["event"], **details)
        worker_path = self.output / "WORKER-RECEIPT.json"
        worker = d.strict_json(worker_path.read_bytes()); worker["journal_tail_sha256"] = journal.previous
        worker_path.unlink(); d.write_new(worker_path, worker)
        with self.assertRaises(ValueError):
            d.verify_completed(self.output, self.value, d.capture(self.manifest)[1], self.code, time.monotonic()+10)

    def test_retained_controls_cannot_contradict_external_manifest(self):
        for i, name in enumerate(("INPUT-MANIFEST.json", "REQUEST.json", "receipts/one.started.json")):
            self.output = self.approved / ("tampered" + str(i)); d.acquire(*self.args(), opener=self.fetch())
            p = self.output / name
            value = d.strict_json(p.read_bytes())
            if name == "INPUT-MANIFEST.json": value["assets"][0]["revision"]["value"] = "b"*40
            elif name == "REQUEST.json": value["code_sha256"] = "b"*64
            else: value["revision"]["value"] = "b"*40
            p.write_bytes(d.canonical(value) + b"\n")
            with self.subTest(name=name), self.assertRaises(ValueError):
                d.verify_completed(self.output, self.value, d.capture(self.manifest)[1], self.code, time.monotonic()+10)


class SupervisionTests(unittest.TestCase):
    setUpClass = classmethod(TransportTests.setUpClass.__func__)
    setUp = TransportTests.setUp
    save = TransportTests.save
    args = TransportTests.args
    def child(self, *, fail=False, stall=False):
        """Actual owned Python child; only HTTP transport is replaced by invented bytes."""
        root = Path(d.__file__).resolve().parents[2]
        script = self.root / "invented_worker.py"
        code = "import sys,time,io\n"
        code += "sys.path[:0]=" + repr([str(root), str(root/"src"), str(root/"packages/tether/src")]) + "\n"
        code += "from experiments.alce_transport import download as d\n"
        if stall:
            code += "time.sleep(60)\n"
        else:
            code += "class Response:\n status=200\n headers={'Content-Length':" + repr(str(len(self.payload))) + "}\n"
            code += " def __init__(self,url):self.url=url;self.s=io.BytesIO(" + repr(self.payload) + ");self.n=0\n"
            code += " def geturl(self):return self.url\n def close(self):pass\n"
            code += " def read1(self,size):\n  self.n+=1\n"
            if fail: code += "  if self.n>1:raise OSError('invented interrupted stream')\n"
            code += "  return self.s.read(min(size,7))\n"
            code += "original=d.acquire\n"
            code += "def acquire(*a,**kw):return original(*a,opener=lambda url,*other:Response(url),**kw)\n"
            code += "d.acquire=acquire\n"
            code += "sys.argv=sys.argv[1:]\nd.main()\n"
        script.write_text(code, encoding="utf-8")
        original = d.processes.supervise_command
        def launch(command, *, limits):
            return original([sys.executable, "-I", "-B", str(script), *command[3:]], limits=limits)
        return launch

    def test_supervised_real_child_success_seals_only_after_exit(self):
        with mock.patch.object(d, "contain_process_tree", return_value=object()), \
             mock.patch.object(d.processes, "supervise_command", side_effect=self.child()) as launch:
            proof = d.supervise(*self.args())
        self.assertEqual(launch.call_count, 1)
        root = d.strict_json(d.bound(proof))
        self.assertEqual(root["status"], "verified"); self.assertTrue(root["payload_hashes_rechecked"])
        proc = d.strict_json(d.bound(root["process"]))
        self.assertEqual(proc["returncode"], 0); self.assertTrue(proc["supervision"]["process_reaped"])
        self.assertEqual((self.output / "payloads/models/one.bin").read_bytes(), self.payload)

    def test_supervised_real_child_failure_retains_streams_and_partial(self):
        with mock.patch.object(d, "contain_process_tree", return_value=object()), \
             mock.patch.object(d.processes, "supervise_command", side_effect=self.child(fail=True)) as launch:
            with self.assertRaises(ValueError): d.supervise(*self.args())
        self.assertEqual(launch.call_count, 1)
        self.assertTrue((self.output / "SUPERVISOR-FAILED.json").is_file())
        self.assertTrue((self.output / "stderr.bin").stat().st_size)
        self.assertEqual((self.output / "partials/one.part").read_bytes(), self.payload[:7])
        self.assertFalse((self.output / "RECEIPT.json").exists())

    def test_supervised_real_child_timeout_retains_observed_process_no_retry(self):
        self.value["limits"].update(total_seconds=5, network_seconds=1, stall_seconds=2); self.save()
        with mock.patch.object(d, "contain_process_tree", return_value=object()), \
             mock.patch.object(d.processes, "supervise_command", side_effect=self.child(stall=True)) as launch:
            with self.assertRaises(Exception): d.supervise(*self.args())
        self.assertEqual(launch.call_count, 1)
        proc = d.strict_json((self.output / "PROCESS.json").read_bytes())
        self.assertTrue(proc["supervision"]["process_reaped"])
        self.assertEqual(proc["supervision"]["termination_reason"], "deadline_exceeded")
        self.assertFalse((self.output / "RECEIPT.json").exists())


if __name__ == "__main__": unittest.main()
