"""Fictional retained-byte adapter controls; no sources or generated candidates."""

import hashlib
import math
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, encode
from tether_engine.study.source_fact_adapters import adapt_output


TASK_ID = "fictional-reporting-task"
TASK_SHA256 = "a" * 64


def fact(**updates):
    return dict(
        fact_id="fictional-fact-a",
        value=3.0,
        unit=None,
        source=dict(
            source_id="fictional-source",
            sha256="b" * 64,
            release_id="fictional-release-1",
            locator=dict(format="json", pointer="/records/0"),
            field="beta",
        ),
        unknown_reason=None,
    ) | updates


def document(**updates):
    return dict(
        schema_version=1,
        task_id=TASK_ID,
        task_sha256=TASK_SHA256,
        status="answered",
        facts=[fact()],
        collection_status="selected_records",
        reason=None,
    ) | updates


def legacy_document(**updates):
    return dict(
        answer_status="answered",
        claims=[dict(kind="source_report", text="Invented exact text.",
                     quote_refs=["Q0"], limitations=[])],
        unresolved=[],
        abstention_reason=None,
    ) | updates


class SourceFactAdapterTests(unittest.TestCase):
    def adapt(self, doc, *, wire_format="typed_facts_v1"):
        raw = doc if isinstance(doc, bytes) else canonical(doc)
        return adapt_output(raw, wire_format=wire_format,
                            task_id=TASK_ID, task_sha256=TASK_SHA256)

    def malformed(self, doc, *, wire_format="typed_facts_v1"):
        result = self.adapt(doc, wire_format=wire_format)
        self.assertEqual(result["status"], "malformed")
        self.assertIsNone(result["output"])
        self.assertIsInstance(result["error"], str)
        self.assertTrue(result["error"].strip())
        return result

    def test_retained_bytes_hash_and_deeply_immutable_output(self):
        raw = b" \n" + canonical(document()) + b"\n"
        result = self.adapt(raw)
        self.assertEqual(set(result), {"status", "output", "raw_sha256", "raw_bytes",
                                       "error", "wire_format"})
        self.assertEqual(result["status"], "scorable")
        self.assertIsNone(result["error"])
        self.assertEqual(result["wire_format"], "typed_facts_v1")
        self.assertEqual(result["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["raw_bytes"], len(raw))
        self.assertEqual(encode(result["output"]), document())
        with self.assertRaises(TypeError):
            result["output"]["facts"][0]["source"]["field"] = "repaired"
        with self.assertRaises(TypeError):
            result["status"] = "changed"

    def test_adapter_preserves_omissions_duplicates_conflicts_and_wrong_facts(self):
        emitted = [fact(), fact(), fact(value=-9), fact(fact_id="unknown-fact")]
        result = self.adapt(document(facts=emitted))
        self.assertEqual(result["status"], "scorable")
        self.assertEqual(encode(result["output"]["facts"]), emitted)
        self.assertEqual(len(result["output"]["facts"]), 4)

    def test_native_value_types_order_and_signed_zero_remain_distinct(self):
        values = [True, 1, 1.0, -0.0, 0.0, " α ", [2, 1], {"x": [False, None]}]
        result = self.adapt(document(facts=[fact(value=v) for v in values]))
        self.assertEqual(result["status"], "scorable")
        actual = [row["value"] for row in result["output"]["facts"]]
        self.assertIs(type(actual[0]), bool)
        self.assertIs(type(actual[1]), int)
        self.assertIs(type(actual[2]), float)
        self.assertEqual(math.copysign(1, actual[3]), -1)
        self.assertEqual(math.copysign(1, actual[4]), 1)
        self.assertEqual(encode(actual), values)

    def test_status_reason_fact_matrix(self):
        for status, facts, reason in (
            ("answered", [fact()], None),
            ("partial", [fact()], "One fictional field omitted."),
            ("abstained", [], "No report attempted."),
            ("insufficient_input", [], "The selected collection is incomplete."),
        ):
            with self.subTest(status=status):
                self.assertEqual(self.adapt(document(status=status, facts=facts,
                    reason=reason))["status"], "scorable")
        for updates in (
            dict(status="answered", facts=[]),
            dict(status="answered", reason="unexpected"),
            dict(status="partial", reason=None),
            dict(status="partial", facts=[], reason="partial"),
            dict(status="abstained", reason="why"),
            dict(status="abstained", facts=[], reason=None),
            dict(status="insufficient_input", facts=[], reason="\u2003"),
            dict(status="other"), dict(status=True),
        ):
            with self.subTest(updates=updates):
                self.malformed(document(**updates))

    def test_all_declared_collection_states_preserved_without_inference(self):
        for state in ("selected_records", "zero_matches_selected_collection",
                      "incomplete", "failed_qc"):
            result = self.adapt(document(collection_status=state))
            self.assertEqual(result["status"], "scorable")
            self.assertEqual(result["output"]["collection_status"], state)
        for state in ("biological_absence", None, True, []):
            self.malformed(document(collection_status=state))

    def test_explicit_unknown_requires_null_and_nonblank_reason(self):
        unknown = fact(value=None, unknown_reason="native_null")
        result = self.adapt(document(facts=[unknown]))
        self.assertEqual(result["status"], "scorable")
        self.assertEqual(encode(result["output"]["facts"]), [unknown])
        for value, reason in ((None, None), (None, ""), (None, " \u2003"),
                              (3, "native_null"), (False, "unknown"),
                              ([], "unknown"), ({}, "unknown"), (None, 3)):
            with self.subTest(value=value, reason=reason):
                self.malformed(document(facts=[fact(value=value, unknown_reason=reason)]))

    def test_exact_top_and_fact_shapes_strict_schema_and_task_binding(self):
        for doc in ([], None, {}, document(schema_version=True),
                    document(schema_version=1.0), document(task_id="another-task"),
                    document(task_sha256="c" * 64), document(facts={}),
                    document(extra="unexpected")):
            self.malformed(doc)
        for key in document():
            doc = document()
            del doc[key]
            self.malformed(doc)
        for item in (fact(extra=1), {k: v for k, v in fact().items() if k != "unit"},
                     None, 2, fact(fact_id="\u2003"), fact(unit=""), fact(unit=1)):
            self.malformed(document(facts=[item]))

    def test_source_binding_preserved_and_structurally_checked_only(self):
        item = fact()
        item["source"].update(source_id="unrecognized-but-emitted", field="reportedField")
        result = self.adapt(document(facts=[item]))
        self.assertEqual(result["status"], "scorable")
        self.assertEqual(encode(result["output"]["facts"][0]), item)
        for update in (dict(extra=1), dict(sha256="B" * 64), dict(sha256="x" * 64),
                       dict(source_id=""), dict(release_id=None), dict(field="\n")):
            item = fact()
            item["source"].update(update)
            self.malformed(document(facts=[item]))
        for key in fact()["source"]:
            item = fact()
            del item["source"][key]
            self.malformed(document(facts=[item]))

    def test_json_and_parquet_locators_are_exact_with_strict_integer_indices(self):
        valid = [dict(format="json", pointer=""),
                 dict(format="json", pointer="/records/a~1b/~0"),
                 dict(format="parquet", row_group=0, row=0)]
        invalid = [dict(format="json", pointer="records/0"),
                   dict(format="json", pointer="/~2"),
                   dict(format="json", pointer="/~"),
                   dict(format="json", pointer="", row=1),
                   dict(format="parquet", row_group=True, row=0),
                   dict(format="parquet", row_group=0, row=-1),
                   dict(format="parquet", row_group=0, row=1.0),
                   dict(format="parquet", row=1), dict(format="csv", row=0)]
        for locator in valid:
            item = fact()
            item["source"]["locator"] = locator
            self.assertEqual(self.adapt(document(facts=[item]))["status"], "scorable")
        for locator in invalid:
            item = fact()
            item["source"]["locator"] = locator
            self.malformed(document(facts=[item]))

    def test_parse_failures_duplicate_keys_nonfinite_and_invalid_unicode_are_terminal(self):
        for raw in (b"{", b"\xff", b"null", b"true", b"{\"x\":1,\"x\":2}",
                    b'{"\\ud800":1,"\\ud800":2}',
                    canonical(document()).replace(b'"value":3.0', b'"value":NaN'),
                    canonical(document()).replace(b'"value":3.0', b'"value":Infinity'),
                    canonical(document()).replace(b'"value":3.0', b'"value":1e400'),
                    canonical(document()).replace(b'"value":3.0', b'"value":"\\ud800"')):
            with self.subTest(raw=raw[:40]):
                result = self.malformed(raw)
                self.assertEqual(result["raw_sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual(result["raw_bytes"], len(raw))
                self.assertIsInstance(canonical(result), bytes)

    def test_byte_fact_string_node_and_depth_bounds_fail_without_truncation(self):
        raw = canonical(document())
        self.assertEqual(self.adapt(raw + b" " * (262144 - len(raw)))["status"], "scorable")
        self.malformed(raw + b" " * (262145 - len(raw)))
        self.assertEqual(self.adapt(document(facts=[fact()] * 512))["status"], "scorable")
        self.malformed(document(facts=[fact()] * 513))
        self.assertEqual(self.adapt(document(facts=[fact(value="x" * 8192)]))["status"], "scorable")
        self.malformed(document(facts=[fact(value="x" * 8193)]))
        self.malformed(document(facts=[fact(fact_id="x" * 513)]))
        self.malformed(document(facts=[fact(unknown_reason="x" * 1801, value=None)]))
        self.malformed(document(facts=[fact(value=[0] * 4097)]))
        self.malformed(document(facts=[fact(value=[list(range(1024)) for _ in range(5)])]))
        deep = 1
        for _ in range(18):
            deep = [deep]
        self.malformed(document(facts=[fact(value=deep)]))

    def test_legacy_prose_and_quotes_never_create_typed_fact_credit(self):
        doc = legacy_document()
        doc["claims"][0]["text"] = '{"beta":0.4,"pvalue":0.01}'
        result = self.adapt(doc, wire_format="interpretation_v2")
        self.assertEqual(result["status"], "unscorable_legacy")
        self.assertIsNone(result["output"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["wire_format"], "interpretation_v2")
        for status in ("partial", "abstained"):
            doc = legacy_document(answer_status=status, abstention_reason="Fictional limit.")
            if status == "abstained":
                doc["claims"] = []
            self.assertEqual(self.adapt(doc, wire_format="interpretation_v2")["status"],
                             "unscorable_legacy")

    def test_malformed_legacy_shapes_states_and_inference_limits_fail(self):
        for doc in (legacy_document(extra=1), legacy_document(claims=[]),
                    legacy_document(answer_status="abstained"),
                    legacy_document(unresolved="unknown")):
            self.malformed(doc, wire_format="interpretation_v2")
        for change in (dict(extra=1), dict(kind="other"), dict(text=" "),
                       dict(quote_refs=[]), dict(quote_refs=["Q0", "Q0"]),
                       dict(kind="scientific_inference", limitations=[]),
                       dict(quote_refs=["Q0", "Q1"])):
            doc = legacy_document()
            doc["claims"][0].update(change)
            self.malformed(doc, wire_format="interpretation_v2")

    def test_configuration_errors_raise_without_dispatch_or_source_reads(self):
        raw = canonical(document())
        for config in (dict(wire_format="other"), dict(task_id=""),
                       dict(task_sha256="invalid")):
            with self.assertRaises(ContractError):
                adapt_output(raw, **(dict(wire_format="typed_facts_v1", task_id=TASK_ID,
                                         task_sha256=TASK_SHA256) | config))
        with self.assertRaises(ContractError):
            adapt_output(raw.decode(), wire_format="typed_facts_v1", task_id=TASK_ID,
                         task_sha256=TASK_SHA256)
        with patch("builtins.open", side_effect=AssertionError("No reads")), \
             patch("pathlib.Path.open", side_effect=AssertionError("No reads")), \
             patch("socket.socket", side_effect=AssertionError("No network")), \
             patch("subprocess.Popen", side_effect=AssertionError("No dispatch")):
            self.assertEqual(self.adapt(raw)["status"], "scorable")
            self.assertEqual(self.adapt(legacy_document(),
                wire_format="interpretation_v2")["status"], "unscorable_legacy")


if __name__ == "__main__":
    unittest.main()
