"""Caller-pin and review binding regressions using invented preparation files."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.science import freeze_p09_runtime_bundle as freezer


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.draft = self.root / "draft"
        self.draft.mkdir()
        files = {}
        for i in range(311):
            name = f"member-{i:03d}.json"
            raw = b'{}\n'
            (self.draft / name).write_bytes(raw)
            files[name] = dict(path=name, sha256=freezer.sha(raw), bytes=len(raw), role="invented_fixture")
        self.document = dict(schema_version=1, method="p09.public_reconstruction_protocol.v1",
            status="DRAFT_ROOT_AUTHORIZATION_PENDING", actual_reconstruction_authorized=False,
            dataset_payloads=dict(hgnc_included=True), files=files, core_files={}, replay_files={}, environment={}, limits={})
        raw = freezer.canonical(self.document) + b"\n"
        (self.draft / "protocol.json").write_bytes(raw)
        self.pin = hashlib.sha256(raw).hexdigest()
        self.review = self.root / "review.json"
        self.review_doc = dict(status="PASS_DRAFT_METADATA_REVIEW", protocol_sha256=self.pin,
                               unresolved_findings=[], privacy_findings=[])
        self.output = self.root / "data/cache/runtime"
        self.record = self.root / "READY.json"

    def call(self, pin=None):
        self.review.write_text(json.dumps(self.review_doc), encoding="utf-8")
        review_pin = hashlib.sha256(self.review.read_bytes()).hexdigest()
        with patch.object(freezer, "ROOT", self.root), patch.object(freezer.subprocess, "check_output", return_value="0" * 40 + "\n"):
            freezer.freeze(self.draft, self.output, self.review, review_pin, self.record, self.pin if pin is None else pin)

    def test_new_explicit_pin_freezes_exact_inventory_and_external_record(self):
        self.call()
        result = json.loads((self.output / "protocol.json").read_text())
        self.assertEqual(result["status"], "READY")
        self.assertIs(result["actual_reconstruction_authorized"], True)
        self.assertEqual(len(list(self.output.iterdir())), 312)
        record = json.loads(self.record.read_text())
        self.assertEqual(record["draft_protocol_sha256"], self.pin)
        self.assertEqual(record["protocol_sha256"], freezer.sha((self.output / "protocol.json").read_bytes()))

    def test_wrong_caller_pin_is_rejected_before_reservation(self):
        with self.assertRaisesRegex(ValueError, "draft authority"):
            self.call("0" * 64)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.record.exists())

    def test_rehashed_review_for_different_draft_or_failure_cannot_authorize(self):
        for changes in ({"protocol_sha256": "0" * 64}, {"status": "FAIL_DRAFT_METADATA_REVIEW"},
                        {"unresolved_findings": ["invented unresolved finding"]}, {"privacy_findings": ["invented private field"]}):
            with self.subTest(changes=changes):
                original = dict(self.review_doc)
                self.review_doc.update(changes)
                with self.assertRaisesRegex(ValueError, "passing independent"):
                    self.call()
                self.assertFalse(self.output.exists())
                self.review_doc = original


if __name__ == "__main__":
    unittest.main()
