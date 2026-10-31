"""Independent source/pure review; synthetic frozen bytes only, no old replay."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).parent
SOURCE = HERE / "captured_journal_v1.py"
data = SOURCE.read_bytes()
assert hashlib.sha256(data).hexdigest() == "5b86f70a57dd1b51d7fe74829b032ddd954f656075ec585c062d5c6dc5e3cf37"
spec = importlib.util.spec_from_file_location("peer_journal", SOURCE)
m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m
exec(compile(data, str(SOURCE), "exec"), m.__dict__)
fixture_raw = (HERE / "CAPTURED-JOURNAL-FIXTURES-v1.json").read_bytes()
assert hashlib.sha256(fixture_raw).hexdigest() == "1448873002dc5350be8ca835254ff283b734d04bda88382273b1c4b4319fe28c"
FIXTURES = json.loads(fixture_raw)["cases"]
FALSE_POSITIVES = []


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def encode(items):
    prior = None; lines = []
    for index, (event, details) in enumerate(items):
        row = dict(sequence=index, event=event, details=details, previous_sha256=prior)
        prior = hashlib.sha256(canonical(row)).hexdigest(); row["sha256"] = prior
        lines.append(canonical(row) + b"\n")
    return b"".join(lines)


def base():
    return bytes.fromhex(FIXTURES[0]["raw_hex"]), copy.deepcopy(FIXTURES[0]["bindings"])


def events(raw):
    return [(row["event"], row["details"]) for row in (json.loads(line) for line in raw.split(b"\n") if line)]


class PeerChecks(unittest.TestCase):
    def test_thirty_frozen_chain_and_policy_expectations(self):
        self.assertEqual(len(FIXTURES), 30)
        for fixture in FIXTURES:
            with self.subTest(fixture=fixture["id"]):
                raw = bytes.fromhex(fixture["raw_hex"]) if fixture["kind"] == "literal" else bytes.fromhex(fixture["recipe"]["byte_hex"]) * fixture["recipe"]["repeat"]
                self.assertEqual(len(raw), fixture["bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), fixture["sha256"])
                for native, expected in ((False, fixture["expected_chain_valid"]), (True, fixture["expected_native_complete"])):
                    try:
                        result = m.check_native_v7(raw, fixture["bindings"], check=lambda: None) if native else m.check_chain(raw, check=lambda: None)
                    except m.CapturedJournalError:
                        accepted = False
                    else:
                        accepted = True
                        self.assertFalse(result["profile_qualified"])
                        self.assertFalse(result["resource_semantics_validated"])
                    self.assertEqual(accepted, expected)

    def assert_source_reject(self, label, raw, bindings):
        try:
            result = m.check_native_v7(raw, bindings, check=lambda: None)
        except m.CapturedJournalError:
            return
        FALSE_POSITIVES.append(dict(id=label, status=result["status"], source_order_validated=result["source_order_validated"],
                                    profile_qualified=result["profile_qualified"], resource_semantics_validated=result["resource_semantics_validated"]))
        self.fail("Contradictory terminal observation was accepted: " + label)

    def test_terminal_completeness_does_not_override_nested_failures_or_counts(self):
        def missing(binding):
            drain = binding["parent_report"]["terminal_observation"]["observations"]["capture_drain"]["stdout"]
            del drain["status"]; del drain["polls_reserved"]
        changes = (
            ("terminal_errors_nonempty", lambda b: b["parent_report"]["terminal_observation"].update(errors=[dict(error_class="RuntimeError", error="synthetic terminal failure")])),
            ("drain_failed_status", lambda b: b["parent_report"]["terminal_observation"]["observations"]["capture_drain"]["stdout"].update(status="failed")),
            ("drain_bool_polls_reserved", lambda b: b["parent_report"]["terminal_observation"]["observations"]["capture_drain"]["stdout"].update(polls_reserved=True)),
            ("drain_missing_status_and_count", missing))
        for label, change in changes:
            with self.subTest(fault=label):
                raw, bindings = base(); change(bindings)
                self.assert_source_reject(label, raw, bindings)

    def test_observed_EOF_requires_terminal_none_availability(self):
        raw, bindings = base(); items = events(raw)
        drain = bindings["parent_report"]["terminal_observation"]["observations"]["capture_drain"]["stdout"]
        drain.update(status="observed_pipe_EOF", polls_reserved=1,
                     calls=[dict(poll=1, status="returned", attempt_reserved=True, call_attempted=True, return_observed=True, value=0)])
        index = next(i for i, (name, _) in enumerate(items) if name == "detached_ABI_terminal_call_reserved")
        items.insert(index, ("detached_ABI_terminal_call_reserved", dict(observation="capture_available_stdout")))
        raw = encode(items); bindings["journal_sha256"] = hashlib.sha256(raw).hexdigest()
        self.assertTrue(m.check_chain(raw, check=lambda: None)["chain_integrity_validated"])
        self.assert_source_reject("observed_EOF_without_None_availability", raw, bindings)

    def test_rechained_source_order_reference_and_bool_attacks_reject(self):
        for attack in ("duplicate_resume", "unknown_event", "wrong_protocol", "bool_resume_binding"):
            raw, bindings = base(); items = events(raw)
            if attack == "duplicate_resume":
                index = next(i for i, (name, _) in enumerate(items) if name == "abi_resume_returned")
                items.insert(index + 1, copy.deepcopy(items[index]))
            elif attack == "unknown_event": items.insert(2, ("application_dispatch", {}))
            elif attack == "wrong_protocol": bindings["protocol_sha256"] = "0" * 64
            else: bindings["parent_report"]["resumption"]["previous_suspend_count"] = True
            raw = encode(items); bindings["journal_sha256"] = hashlib.sha256(raw).hexdigest()
            self.assertTrue(m.check_chain(raw, check=lambda: None)["chain_integrity_validated"])
            with self.assertRaises(m.CapturedJournalError): m.check_native_v7(raw, bindings, check=lambda: None)

    def test_raw_LF_canonical_scalar_and_bool_framing(self):
        raw = encode([("run_reserved", {"text": "A\u0085B\u2028C\u2029D"})])
        self.assertEqual(m.check_chain(raw, check=lambda: None)["events"], 1)
        for bad in (raw[:-1], b"\xef\xbb\xbf" + raw, raw.replace(b"\n", b"\r\n"), raw + b"\n",
                    raw.replace(b'"event":', b'"event":"duplicate","event":', 1)):
            with self.assertRaises(m.CapturedJournalError): m.check_chain(bad, check=lambda: None)
        row = dict(sequence=True, event="run_reserved", details={}, previous_sha256=None)
        row["sha256"] = hashlib.sha256(canonical(row)).hexdigest()
        with self.assertRaises(m.CapturedJournalError): m.check_chain(canonical(row) + b"\n", check=lambda: None)

    def test_deadline_same_exception_and_no_late_return(self):
        raw, bindings = base()
        for native in (False, True):
            invoke = (lambda check: m.check_native_v7(raw, bindings, check=check)) if native else (lambda check: m.check_chain(raw, check=check))
            count = [0]
            def tick(): count[0] += 1
            invoke(tick)
            for boundary in (1, count[0] // 2, count[0]):
                error = KeyboardInterrupt("synthetic same owner cutoff"); seen = [0]
                def cutoff():
                    seen[0] += 1
                    if seen[0] == boundary: raise error
                try: invoke(cutoff)
                except BaseException as caught: self.assertIs(caught, error)
                else: self.fail("Late validation returned a result")

    def test_immutability_input_detachment_and_no_filesystem_callback(self):
        raw, bindings = base(); before = copy.deepcopy(bindings)
        with mock.patch("builtins.open", side_effect=AssertionError("No filesystem operation")):
            result = m.check_native_v7(raw, bindings, check=lambda: None)
            chain = m.check_chain(raw, check=lambda: None)
        self.assertEqual(bindings, before)
        with self.assertRaises(TypeError): chain["records"][0]["details"]["owner_pid"] = 0
        with self.assertRaises(TypeError): result["record_references"][0]["kind"] = "changed"
        bindings["parent_report"]["status"] = "changed"
        self.assertNotEqual(result["source_terminal_status"], "changed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
