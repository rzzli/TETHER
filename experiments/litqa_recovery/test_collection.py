"""Fictional recovered collections: transport is always replaced before execute."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from experiments.litqa_recovery import collection as c
from experiments.litqa_recovery import plan as p
from experiments.litqa_recovery import test_plan as fixtures


class RecoveredCollectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RecoveryPlanTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.top = self.fixture.top
        self.authority = self.fixture.reserve()
        qualification = dict(schema_version=2, kind="sc04_recovery_collection_qualification_v2", status="PASS",
                             tests=17, failures=0, errors=0, skipped=0, code_pins=c.source_pins(),
                             scope="Invented qualification record for unit controls; not production authority.")
        self.qualification = c.publish(self.top / "QUALIFICATION.json", qualification)
        self.output = self.top / "collection"
        self.frame, self.frame_proof = self.freeze(self.output, "EXECUTION.json")

    def freeze(self, output, filename):
        frame = c.make_frame(self.authority["frame"], self.authority["authority"], self.qualification, output, 600)
        return frame, c.publish(self.top / filename, frame)

    def fetch(self, url, **limits):
        self.assertIn("10.1234%2Fthree", url)
        return dict(body=b'{"hitCount":0,"resultList":{"result":[]}}', status=200, final_url=url, headers={})

    def execute(self, *, fetch=None, clock=time.monotonic, frame_proof=None, output=None):
        proof = self.frame_proof if frame_proof is None else frame_proof
        with patch.object(c.resolver.legacy, "fetch_http", side_effect=self.fetch if fetch is None else fetch) as transport:
            result = c.execute(proof["path"], proof["sha256"], output=self.output if output is None else output, clock=clock)
        return result, transport

    def reseal(self, output=None):
        output = self.output if output is None else output
        path = output / "RECEIPT.json"
        receipt = json.loads(path.read_bytes())
        receipt["files"] = c.inventory(output, omit=("RECEIPT.json",))[0]
        path.write_bytes(c.canonical(receipt) + b"\n")
        return c.capture(path)[0]["sha256"]

    def test_only_untouched_fetches_full_cohort_replays_without_network(self):
        original = p._inventory(self.fixture.root)
        result, transport = self.execute()
        self.assertEqual(transport.call_count, 1)
        with patch.object(c.resolver.legacy, "fetch_http", side_effect=AssertionError("Replay must not fetch")):
            replay = c.replay(self.output, result["receipt"]["sha256"])
        manifest = replay["manifest"]
        self.assertEqual([r["disposition"] for r in manifest["records"]],
                         ["adopt_completed", "inherited_uncertain_metadata", "newly_completed"])
        self.assertEqual(manifest["doi_schedule"], self.fixture.dois)
        self.assertEqual(manifest["answer_queries"], self.fixture.queries)
        self.assertEqual(manifest["hints"], self.fixture.hints)
        uncertain = replay["by_doi"][self.fixture.dois[1]]
        self.assertIsNone(uncertain["resolution"])
        self.assertIsNone(uncertain["coverage"]["article_retained"])
        self.assertIsNone(uncertain["accounting"]["measured_response_bytes"])
        self.assertEqual(uncertain["parent_proofs"]["reservation"]["byte_reservation"], 1048576)
        self.assertEqual(manifest["accounting"]["historical"]["http_attempts"], 2)
        self.assertEqual(manifest["accounting"]["incremental"]["http_attempts"], 1)
        self.assertEqual(manifest["accounting"]["total"]["http_attempts"], 3)
        self.assertEqual(p._inventory(self.fixture.root), original)
        self.assertFalse((self.output / "products/0000").exists())
        self.assertFalse((self.output / "products/0001").exists())

    def test_explicit_http_failure_is_completed_unavailable_resolution(self):
        def failed(url, **limits): raise TimeoutError("Invented transfer failure")
        result, transport = self.execute(fetch=failed)
        self.assertEqual(transport.call_count, 1)
        manifest = c.replay(self.output, result["receipt"]["sha256"])["manifest"]
        row = manifest["records"][2]
        self.assertEqual(row["disposition"], "newly_completed")
        self.assertFalse(row["coverage"]["article_retained"])
        self.assertEqual(row["accounting"]["measured_response_bytes"], 0)
        self.assertEqual(row["accounting"]["unknown_transfer_upper_bytes"], 1048576)
        self.assertEqual(manifest["accounting"]["total"]["unknown_transfer_upper_bytes"], 2*1048576)

    def test_malformed_fetch_retains_an_unresolved_attempt_without_retry(self):
        def malformed(url, **limits):
            return dict(body=42, status=200, final_url=url, headers={})
        with self.assertRaises(ValueError): self.execute(fetch=malformed)
        failure = json.loads((self.output / "FAILURE.json").read_bytes())
        usage = failure["rows"][2]["attempt_usage"]
        self.assertEqual(usage["status"], "retained_attempt_prefix")
        self.assertEqual(usage["observed_http_attempts"], 1)
        self.assertEqual(usage["observed_terminal_records"], 0)
        self.assertIsNone(usage["measured_response_bytes"])
        self.assertGreater(usage["safety_accounted_bytes"], 0)
        self.assertFalse((self.output / "RECEIPT.json").exists())

    def test_interruption_retains_all_slots_usage_and_exclusive_claim(self):
        with patch.object(c.resolver, "acquire", side_effect=KeyboardInterrupt("Invented stop")) as acquire:
            with self.assertRaises(KeyboardInterrupt): self.execute()
        self.assertEqual(acquire.call_count, 1)
        failure = json.loads((self.output / "FAILURE.json").read_bytes())
        self.assertEqual(len(failure["rows"]), 3)
        self.assertEqual(failure["rows"][2]["disposition"], "new_attempt_incomplete")
        self.assertIsNone(failure["rows"][2]["attempt_usage"]["measured_response_bytes"])
        self.assertEqual(failure["rows"][2]["attempt_usage"]["safety_accounted_bytes"], 3*1048576)
        self.assertFalse((self.output / "RECEIPT.json").exists())
        second = self.top / "second"
        _, frame = self.freeze(second, "SECOND.json")
        with patch.object(c.resolver.legacy, "fetch_http", side_effect=AssertionError("No second dispatch")):
            with self.assertRaises(FileExistsError):
                c.execute(frame["path"], frame["sha256"], output=second)

    def test_two_outputs_cannot_both_enter_http(self):
        second = self.top / "second"
        _, second_frame = self.freeze(second, "SECOND.json")
        def run(item):
            proof, output = item
            try: return c.execute(proof["path"], proof["sha256"], output=output)
            except FileExistsError: return None
        with patch.object(c.resolver.legacy, "fetch_http", side_effect=self.fetch) as transport:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(run, ((self.frame_proof, self.output), (second_frame, second))))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(transport.call_count, 1)

    def test_phase_expiry_before_dispatch_keeps_untouched_slot_unexecuted(self):
        now = time.monotonic()
        count = 0
        def clock():
            nonlocal count
            count += 1
            return now + (700 if count >= 5 else 0)
        with patch.object(c.resolver.legacy, "fetch_http", side_effect=AssertionError("Expired before dispatch")) as transport:
            with self.assertRaisesRegex(ValueError, "deadline"):
                c.execute(self.frame_proof["path"], self.frame_proof["sha256"], output=self.output, clock=clock)
        self.assertEqual(transport.call_count, 0)
        failure = json.loads((self.output / "FAILURE.json").read_bytes())
        self.assertEqual(len(failure["rows"]), 3)
        self.assertEqual(failure["rows"][2]["disposition"], "unexecuted")

    def test_expiry_after_capture_keeps_measured_completed_source_without_accepting_run(self):
        now = time.monotonic()
        count = 0
        def clock():
            nonlocal count
            count += 1
            return now + (700 if count >= 7 else 0)
        with self.assertRaisesRegex(ValueError, "deadline"): self.execute(clock=clock)
        failure = json.loads((self.output / "FAILURE.json").read_bytes())
        usage = failure["rows"][2]["attempt_usage"]
        self.assertEqual(usage["status"], "completed_source_not_accepted_by_controller")
        self.assertGreater(usage["accounting"]["measured_response_bytes"], 0)
        self.assertEqual(usage["accounting"]["http_attempts"], 1)
        self.assertFalse((self.output / "RECEIPT.json").exists())

    def test_record_write_failure_keeps_accounting_and_never_repeats_call(self):
        original = c.publish
        def fail(path, value):
            if Path(path).name == "0002.json": raise OSError("Invented record-write failure")
            return original(path, value)
        with patch.object(c, "publish", side_effect=fail), self.assertRaises(OSError): self.execute()
        failure = json.loads((self.output / "FAILURE.json").read_bytes())
        self.assertEqual(len(failure["rows"]), 3)
        self.assertEqual(failure["rows"][2]["disposition"], "newly_completed")
        self.assertGreater(failure["rows"][2]["accounting"]["measured_response_bytes"], 0)

    def test_changed_parent_input_fails_before_fetch(self):
        source = Path(self.fixture.frame["products"]["answer_queries"]["path"])
        source.write_bytes(source.read_bytes() + b" ")
        with patch.object(c.resolver.legacy, "fetch_http", side_effect=AssertionError("No fetch")) as transport:
            with self.assertRaises(ValueError): c.execute(self.frame_proof["path"], self.frame_proof["sha256"], output=self.output)
        self.assertEqual(transport.call_count, 0)
        # An unauthenticated parent cannot establish protected output roots.
        # Reject before writing; the supervising caller retains this exception.
        self.assertFalse(self.output.exists())

    def test_invalid_output_does_not_write_even_failure_records_into_original(self):
        before = p._inventory(self.fixture.root)
        output = self.fixture.root / "wrong-output"
        frame = deepcopy(self.frame)
        frame["output"] = str(output)
        proof = c.publish(self.top / "WRONG-OUTPUT.json", frame)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            c.execute(proof["path"], proof["sha256"], output=output)
        self.assertFalse(output.exists())
        self.assertEqual(before, p._inventory(self.fixture.root))

    def test_forged_planning_root_cannot_write_failures_into_actual_original(self):
        before = p._inventory(self.fixture.root)
        planning_frame = deepcopy(c.decode(c.bound(self.authority["frame"])))
        planning_frame["plan"]["original_root"] = str(self.top / "false-original-root")
        altered_planning = c.publish(self.top / "ALTERED-PLANNING.json", planning_frame)
        output = self.fixture.root / "forbidden-output"
        frame = deepcopy(self.frame)
        frame["planning_frame"] = altered_planning
        frame["output"] = str(output)
        proof = c.publish(self.top / "ALTERED-EXECUTION.json", frame)
        with patch.object(c.resolver.legacy, "fetch_http", side_effect=AssertionError("No fetch")) as transport:
            with self.assertRaises(ValueError):
                c.execute(proof["path"], proof["sha256"], output=output)
        self.assertEqual(transport.call_count, 0)
        self.assertFalse(output.exists())
        self.assertEqual(before, p._inventory(self.fixture.root))

    def test_changed_code_qualification_and_external_anchor_fail_before_fetch(self):
        with patch.object(c, "source_pins", return_value={"changed.py": "0"*64}), \
                patch.object(c.resolver.legacy, "fetch_http", side_effect=AssertionError("No fetch")):
            with self.assertRaisesRegex(ValueError, "source/environment"):
                c.execute(self.frame_proof["path"], self.frame_proof["sha256"], output=self.output)
        other = self.top / "wrong-anchor"
        with self.assertRaisesRegex(ValueError, "anchor|frame mismatch"):
            c.execute(self.frame_proof["path"], "0"*64, output=other)

    def test_failed_qualification_cannot_authorize_fetch(self):
        value = json.loads(c.bound(self.qualification))
        value["failures"] = 1
        qualifier = c.publish(self.top / "FAILED-QUALIFICATION.json", value)
        frame = deepcopy(self.frame)
        frame["qualification"] = qualifier
        proof = c.publish(self.top / "UNQUALIFIED.json", frame)
        with patch.object(c.resolver.legacy, "fetch_http", side_effect=AssertionError("No fetch")):
            with self.assertRaisesRegex(ValueError, "qualification"):
                c.execute(proof["path"], proof["sha256"], output=self.output)

    def test_loaded_engine_substitution_fails_before_fetch(self):
        alternate = self.top / "alternate-engine"
        alternate.mkdir()
        initializer = alternate / "__init__.py"
        initializer.write_bytes(b"# Different engine source, never executed.\n")
        with patch.object(c.tether_engine, "__file__", str(initializer)), \
                patch.object(c.resolver.legacy, "fetch_http", side_effect=AssertionError("No fetch")):
            with self.assertRaisesRegex(ValueError, "Loaded engine differs"):
                c.execute(self.frame_proof["path"], self.frame_proof["sha256"], output=self.output)

    def test_resealed_manifest_accounting_and_unknown_resolution_are_rejected(self):
        result, _ = self.execute()
        path = self.output / "MANIFEST.json"
        value = json.loads(path.read_bytes())
        value["accounting"]["total"]["http_attempts"] += 1
        path.write_bytes(c.canonical(value))
        with self.assertRaisesRegex(ValueError, "cohort/accounting"):
            c.replay(self.output, self.reseal())

    def test_resealed_uncertain_row_cannot_manufacture_completed_resolution(self):
        self.execute()
        path = self.output / "records/0001.json"
        value = json.loads(path.read_bytes())
        value["resolution"] = dict(root="invented", receipt_sha256="0"*64, plan={})
        path.write_bytes(c.canonical(value))
        with self.assertRaisesRegex(ValueError, "row differs"):
            c.replay(self.output, self.reseal())

    def test_resealed_extra_file_and_journal_reservation_are_rejected(self):
        self.execute()
        extra = self.output / "unexplained.json"
        extra.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            c.replay(self.output, self.reseal())
        extra.unlink()
        path = self.output / "journal.jsonl"
        events = c._chain(path.read_bytes())
        pairs = [(e["event"], e["details"]) for e in events]
        next(d for name, d in pairs if name == "slot_reserved")["ordinal"] = 0
        fixtures.journal(path, pairs)
        with self.assertRaisesRegex(ValueError, "one-shot reservation"):
            c.replay(self.output, self.reseal())

    def test_bound_json_never_decodes_a_second_unverified_read(self):
        value = dict(registry="approved")
        proof = c.publish(self.top / "SINGLE-READ.json", value)
        original = c.read
        calls = []
        def switch(path, limit=32*1024**2):
            if Path(path) == Path(proof["path"]):
                calls.append(path)
                return c.canonical(dict(registry="other")) if len(calls) > 1 else original(path, limit)
            return original(path, limit)
        with patch.object(c, "read", side_effect=switch):
            self.assertEqual(c.decode(c.bound(proof)), value)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
