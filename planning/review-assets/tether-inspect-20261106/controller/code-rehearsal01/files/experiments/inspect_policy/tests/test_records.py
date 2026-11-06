import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy.records import (CaseRecord, checked_json, digest,
    freeze, inspect_record, parse, proof, publish, read_bytes, thaw)
from experiments.inspect_policy.accounting import Accounting, BudgetDenied


class ExtensionRecordTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "data/cache/inspect-policy-record-tests"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def record(self):
        return CaseRecord(self.root / "case", {"id": "fictional", "evidence": [{"id": "e1", "features": {"a": [1]}}]})

    def budget(self, **overrides):
        return {"max_calls": 2, "max_input_tokens": 20, "max_output_tokens": 10,
                "max_cost_usd": 0.0, "max_seconds": 10.0, **overrides}

    def test_nested_capture_copies_and_freezes(self):
        raw = {"rows": [{"values": [1]}]}
        frozen = freeze(raw)
        raw["rows"][0]["values"][0] = 9
        self.assertEqual(thaw(frozen), {"rows": [{"values": [1]}]})
        with self.assertRaises(TypeError):
            frozen["rows"][0]["values"][0] = 3
        with self.assertRaises(TypeError):
            frozen["rows"][0]["new"] = 3

    def test_duplicate_nonfinite_and_wrong_keys_reject(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'\xff'):
            with self.assertRaises((ValueError, UnicodeError)):
                parse(raw)
        for value in ({1: "bad"}, float("nan"), object()):
            with self.assertRaises(ValueError):
                freeze(value)

    def test_sealed_record_and_tamper(self):
        record = self.record()
        record.append("observation", {"known": None})
        result = record.finish({"decision": "accept"})
        recovered = inspect_record(record.path, receipt_sha256=result["receipt"]["sha256"])
        self.assertEqual(recovered["result"]["decision"], "accept")
        self.assertFalse(recovered["automatic_redispatch"])
        (record.path / "result.json").write_bytes(b'{"decision":"reject"}\n')
        with self.assertRaisesRegex(ValueError, "proof"):
            inspect_record(record.path)

    def test_no_clobber_normalized_alias_preserves_original(self):
        record = self.record()
        before = proof(record.path / "request.json")
        with self.assertRaises(FileExistsError):
            CaseRecord(self.root / "unused" / ".." / "case", {"id": "replacement"})
        self.assertEqual(proof(record.path / "request.json"), before)

    def test_partial_prefix_is_not_completion_or_redispatch(self):
        record = self.record()
        record.append("attempt_reserved", {"quote": {"input_tokens": 3}})
        with (record.path / "journal.jsonl").open("ab") as stream:
            stream.write(b'{"half":')
        recovered = inspect_record(record.path, allow_partial=True)
        self.assertEqual(recovered["status"], "partial")
        self.assertFalse(recovered["automatic_redispatch"])
        with self.assertRaisesRegex(ValueError, "Unterminated"):
            inspect_record(record.path)

    def test_request_journal_binding_rejects_relabel(self):
        record = self.record()
        (record.path / "request.json").write_bytes(b'{"id":"other"}')
        with self.assertRaisesRegex(ValueError, "Request/journal"):
            inspect_record(record.path, allow_partial=True)

    def test_size_limit_rejects_before_open_and_small_read_uses_actual_size(self):
        path = self.root / "small"
        path.write_bytes(b"abc")
        with patch.object(Path, "open", side_effect=AssertionError("must not open")):
            with self.assertRaisesRegex(ValueError, "oversized"):
                read_bytes(path, maximum=2)
        self.assertEqual(read_bytes(path, maximum=512 * 1024 * 1024), b"abc")

    def test_immutable_request_bound_by_hash(self):
        path = self.root / "input.json"
        pin = publish(path, {"rows": [[1, 2]]})
        value = checked_json(path, pin)
        self.assertEqual(digest(value), digest({"rows": [[1, 2]]}))
        with self.assertRaises(TypeError):
            value["rows"][0][0] = 9
        (self.root / "input.json").write_text('{"rows": [[3, 2]]}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "proof differs"):
            checked_json(path, pin)

    def test_reservation_denial_before_any_dispatch(self):
        record = self.record()
        account = Accounting(record, self.budget(max_calls=0))
        with self.assertRaises(BudgetDenied):
            account.reserve({"prompt": "fiction"}, {"input_tokens": 3, "output_tokens": 2, "cost_usd": 0})
        self.assertEqual(account.calls, 0)
        self.assertEqual(account.summary()["usage"]["input_tokens"], 0)

    def test_unknown_usage_retains_quote_and_stops_later_work(self):
        account = Accounting(self.record(), self.budget())
        quote = {"input_tokens": 3, "output_tokens": 2, "cost_usd": 0}
        account.reserve({"prompt": "fiction"}, quote)
        self.assertEqual(account.summary()["unresolved_calls"], 1)
        self.assertEqual(account.summary()["conservative_upper_usage"], quote)
        account.settle(outcome="interrupted")
        self.assertEqual(account.summary()["estimated_usage"], quote)
        self.assertEqual(account.summary()["measured_usage"]["input_tokens"], 0)
        with self.assertRaises(BudgetDenied):
            account.reserve({"prompt": "later"}, quote)

    def test_valid_overquote_is_measured_and_stops(self):
        account = Accounting(self.record(), self.budget())
        account.reserve({"prompt": "fiction"}, {"input_tokens": 3, "output_tokens": 2, "cost_usd": 0})
        account.settle(measured={"input_tokens": 4, "output_tokens": 2, "cost_usd": 0}, outcome="completed")
        self.assertEqual(account.summary()["measured_usage"]["input_tokens"], 4)
        self.assertTrue(account.stopped)
        with self.assertRaises(BudgetDenied):
            account.reserve({"prompt": "later"}, {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0})

    def test_timeout_capacity_and_journal_write_failure_prevent_reservation(self):
        record = self.record()
        now = [0.0]
        account = Accounting(record, self.budget(max_seconds=1), clock=lambda: now[0])
        now[0] = 1.0
        with self.assertRaises(BudgetDenied):
            account.reserve({}, {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0})
        other = CaseRecord(self.root / "other", {"id": "other"})
        account = Accounting(other, self.budget())
        with patch.object(other, "append", side_effect=OSError("fictional storage failure")):
            with self.assertRaises(OSError):
                account.reserve({}, {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0})
        self.assertEqual(account.calls, 0)
        self.assertIsNone(account.pending)

    def test_pending_call_cannot_be_repeated_and_bool_usage_rejects(self):
        account = Accounting(self.record(), self.budget())
        with self.assertRaises(ValueError):
            account.reserve({}, {"input_tokens": True, "output_tokens": 1, "cost_usd": 0})
        quote = {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0}
        account.reserve({}, quote)
        with self.assertRaises(RuntimeError):
            account.reserve({}, quote)
        self.assertEqual(account.calls, 1)


if __name__ == "__main__":
    unittest.main()
