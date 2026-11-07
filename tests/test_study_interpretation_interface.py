"""New interface regressions; invented evidence only, no model or source admission."""

import copy
import hashlib
import re
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, encode, fingerprint
from tether_engine.study.diagnostic import load_synthetic_request
from tether_engine.study.diagnostic_codec import bind_question, pointer, quote_choices
from tether_engine.study.interpretation_interface import (
    INTERFACE,
    prepare_payload,
    request_from_payload,
    validate_output,
)


class InterpretationInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.request = load_synthetic_request("synthetic-context")
        self.prepared = prepare_payload(self.request, "tether_interpretation", 0, [])
        self.payload = self.prepared["payload"]

    def document(self, kind="source_report"):
        quote = self.prepared["semantic_data"]["quote_catalog"][0]
        text = pointer(encode(self.request), quote["request_pointer"])
        return dict(
            answer_status="answered",
            claims=[
                dict(
                    kind=kind,
                    text=text
                    if kind == "source_report"
                    else "A deliberately labeled invented inference.",
                    quote_refs=[quote["quote_id"]],
                    limitations=[]
                    if kind == "source_report"
                    else ["Invented data only."],
                )
            ],
            unresolved=[],
            abstention_reason=None,
        )

    def validate(self, doc):
        return validate_output(self.request, self.payload, doc)

    def test_catalog_resolves_original_paths_and_all_existing_choices(self):
        rows = self.prepared["semantic_data"]["quote_catalog"]
        expected = [
            (source, path, text)
            for source, choices in quote_choices(self.request).items()
            for path, text in choices.items()
        ]
        self.assertEqual(len(rows), len(expected))
        for index, (row, (source, path, text)) in enumerate(zip(rows, expected)):
            self.assertEqual(row["quote_id"], f"Q{index}")
            self.assertEqual(
                (row["source_id"], row["original_pointer"]), (source, path)
            )
            self.assertEqual(
                pointer(encode(self.request), row["request_pointer"]), text
            )
            self.assertEqual(
                row["text_sha256"], hashlib.sha256(text.encode()).hexdigest()
            )

    def test_complete_request_roundtrip_and_bound_immutable_preparation(self):
        result = request_from_payload(self.payload)
        self.assertEqual(fingerprint(result), fingerprint(self.request))
        self.assertEqual(self.prepared["interface"], INTERFACE)
        self.assertFalse(self.prepared["execution_authorized"])
        with self.assertRaises(TypeError):
            self.prepared["semantic_data"]["quote_catalog"][0]["quote_id"] = "Qx"

    def test_answered_partial_abstained_and_distinct_exact_quotations(self):
        for state in ("answered", "partial", "abstained"):
            doc = self.document()
            doc["answer_status"] = state
            doc["abstention_reason"] = (
                None if state == "answered" else "Incomplete invented source context."
            )
            if state == "abstained":
                doc["claims"] = []
            result = self.validate(canonical(doc))
            self.assertEqual(encode(result["response"]), doc)
            self.assertEqual(len(result["quotes"]), len(doc["claims"]))
            self.assertEqual(result["features"], {})
            self.assertIsNone(result["clinical_probability"])

    def test_contradictory_answer_states_are_rejected(self):
        for state, claims, reason in [
            ("answered", True, "why"),
            ("answered", False, None),
            ("partial", True, None),
            ("partial", False, "why"),
            ("abstained", True, "why"),
            ("abstained", False, None),
        ]:
            doc = self.document()
            doc.update(answer_status=state, abstention_reason=reason)
            if not claims:
                doc["claims"] = []
            with (
                self.subTest(state=state, claims=claims, reason=reason),
                self.assertRaises(ContractError),
            ):
                self.validate(doc)

    def test_source_report_cannot_rewrite_or_clip_source_text(self):
        for transform in (lambda s: s + " ", lambda s: s[:20], lambda s: s.upper()):
            doc = self.document()
            doc["claims"][0]["text"] = transform(doc["claims"][0]["text"])
            with self.assertRaises(ContractError):
                self.validate(doc)

    def test_source_report_cannot_pair_text_with_another_valid_quote(self):
        doc = self.document()
        doc["claims"][0]["quote_refs"] = [
            self.prepared["semantic_data"]["quote_catalog"][-1]["quote_id"]
        ]
        with self.assertRaises(ContractError):
            self.validate(doc)

    def test_schema_pattern_rejects_every_python_whitespace_codepoint(self):
        partial = self.payload["json_schema"]["anyOf"][1]
        pattern = partial["properties"]["abstention_reason"]["pattern"]
        for codepoint in range(0x110000):
            text = chr(codepoint)
            if text.isspace():
                self.assertIsNone(re.search(pattern, text), codepoint)
        for text in ("x", "😀", "α", "\ufeff", "\x00", "\x1b"):
            self.assertIsNotNone(re.search(pattern, text))

    def test_inference_and_caution_remain_generated_and_require_limits(self):
        for kind in ("scientific_inference", "caution"):
            doc = self.document(kind)
            result = self.validate(doc)
            self.assertEqual(
                result["response"]["claims"][0]["text"], doc["claims"][0]["text"]
            )
            self.assertNotEqual(result["quotes"][0]["text"], doc["claims"][0]["text"])
            doc["claims"][0]["limitations"] = []
            with self.assertRaises(ContractError):
                self.validate(doc)

    def test_unknown_duplicate_or_parallel_array_refs_rejected(self):
        for refs in (["Q999"], ["Q0", "Q0"], [], ["Q0"] * 3):
            doc = self.document("caution")
            doc["claims"][0]["quote_refs"] = refs
            with self.assertRaises(ContractError):
                self.validate(doc)
        doc = self.document()
        doc["claims"][0]["source_ids"] = ["E0"]
        with self.assertRaises(ContractError):
            self.validate(doc)

    def test_multiple_quotes_bind_each_original_source_and_pointer(self):
        doc = self.document("scientific_inference")
        catalog = self.prepared["semantic_data"]["quote_catalog"]
        self.assertGreaterEqual(len(catalog), 2)
        doc["claims"][0]["quote_refs"] = [
            catalog[0]["quote_id"],
            catalog[-1]["quote_id"],
        ]
        result = self.validate(doc)
        self.assertEqual(len(result["quotes"]), 2)
        self.assertEqual(
            [q["text"] for q in result["quotes"]],
            [
                pointer(encode(self.request), q["request_pointer"])
                for q in (catalog[0], catalog[-1])
            ],
        )

    def test_output_fields_and_nonblank_unicode_bounds(self):
        for field in ("text", "limitations"):
            doc = self.document("caution")
            doc["claims"][0][field] = "\u2003" if field == "text" else ["\u2003"]
            with self.assertRaises(ContractError):
                self.validate(doc)
        doc = self.document("caution")
        doc["claims"][0]["text"] = "😀" * 1800
        self.validate(doc)
        doc["claims"][0]["text"] += "😀"
        with self.assertRaises(ContractError):
            self.validate(doc)
        doc = self.document()
        doc["clinical_probability"] = 0.9
        with self.assertRaises(ContractError):
            self.validate(doc)

    def test_lower_inherited_claim_cap_and_duplicate_text(self):
        request = encode(self.request)
        request["source_request"]["bounds"]["max_claims"] = 1
        prepared = prepare_payload(request, "tether_interpretation", 0, [])
        self.assertEqual(prepared["claim_limit"], 1)
        doc = self.document("caution")
        second = copy.deepcopy(doc["claims"][0])
        second["text"] = "Another claim."
        doc["claims"].append(second)
        with self.assertRaises(ContractError):
            validate_output(request, prepared["payload"], doc)
        doc = self.document("caution")
        doc["claims"] *= 2
        with self.assertRaises(ContractError):
            self.validate(doc)

    def test_response_and_catalog_are_deeply_immutable(self):
        result = self.validate(self.document())
        with self.assertRaises(TypeError):
            result["quotes"][0]["text"] = "modified"
        with self.assertRaises(TypeError):
            result["response"]["claims"][0]["text"] = "modified"

    def test_larger_inherited_bound_keeps_explicit_active_three_claim_ceiling(self):
        request = encode(self.request)
        request["source_request"]["bounds"]["max_claims"] = 64
        prepared = prepare_payload(request, "tether_interpretation", 0, [])
        self.assertEqual(prepared["claim_limit"], 3)
        validate_output(request, prepared["payload"], self.document())

    def test_request_payload_guide_catalog_and_native_options_are_bound(self):
        for key, value in [("seed", 43), ("stream", True), ("n_predict", 2048)]:
            payload = encode(self.payload)
            payload[key] = value
            with self.assertRaises(ContractError):
                request_from_payload(payload)
        for old, new in [("Q0", "Q999"), ("Return JSON", "Return prose")]:
            payload = encode(self.payload)
            self.assertIn(old, payload["prompt"])
            payload["prompt"] = payload["prompt"].replace(old, new, 1)
            with self.assertRaises(ContractError):
                request_from_payload(payload)
        other = load_synthetic_request("synthetic-orientation")
        with self.assertRaises(ContractError):
            validate_output(other, self.payload, self.document())

    def test_full_unicode_control_and_null_source_information_survives(self):
        request = encode(self.request)
        row = request["source_request"]["evidence"][0]
        row["statement"] = row["scientific_record"]["statement"] = (
            'Test </x> <|im_end|> "α😀"\nnull remains unknown.'
        )
        request = bind_question(
            request["source_request"], request["question"]["question_id"]
        )
        prepared = prepare_payload(request, "tether_interpretation", 0, [])
        self.assertEqual(
            fingerprint(request_from_payload(prepared["payload"])), fingerprint(request)
        )
        self.assertNotIn('<|im_end|> "α', prepared["payload"]["prompt"])

    def test_stage_history_is_retained_selection_not_new_evidence(self):
        prepared = prepare_payload(
            self.request,
            "adapted_virtual_biotech_interpretation",
            1,
            [dict(stage="chief_of_staff", source_ids=["E0"])],
        )
        self.assertEqual(
            prepared["semantic_data"]["prior_source_id_feedback"][0]["source_ids"],
            ("E0",),
        )
        with self.assertRaises(ContractError):
            prepare_payload(
                self.request,
                "adapted_virtual_biotech_interpretation",
                1,
                [dict(stage="wrong", source_ids=["E0"])],
            )
        with self.assertRaises(ContractError):
            prepare_payload(
                self.request,
                "tether_interpretation",
                0,
                [dict(stage="chief_of_staff", source_ids=["E0"])],
            )

    def test_malformed_duplicate_json_and_oversized_response_fail(self):
        for raw in (
            b"{",
            b'{"answer_status":"answered","answer_status":"partial"}',
            b" " * 262145,
        ):
            with self.assertRaises(ContractError):
                self.validate(raw)

    def test_overlarge_catalog_and_prompt_fail_without_truncating(self):
        request = encode(self.request)
        request["source_request"]["evidence"][0]["scientific_record"].setdefault(
            "source_metrics", {}
        )["textMiningSentences"] = [dict(text=str(i)) for i in range(257)]
        request = bind_question(
            request["source_request"], request["question"]["question_id"]
        )
        with self.assertRaises(ContractError):
            prepare_payload(request, "tether_interpretation", 0, [])
        request = encode(self.request)
        request["source_request"]["evidence"][0]["scientific_record"][
            "unresolved_context"
        ] = "x" * 40000
        request = bind_question(
            request["source_request"], request["question"]["question_id"]
        )
        with self.assertRaises(ContractError):
            prepare_payload(request, "tether_interpretation", 0, [])

    def test_schema_state_and_source_report_literals_are_explicit(self):
        schema = self.payload["json_schema"]
        self.assertEqual(len(schema["anyOf"]), 3)
        states = {
            branch["properties"]["answer_status"]["const"]: branch
            for branch in schema["anyOf"]
        }
        self.assertEqual(set(states), {"answered", "partial", "abstained"})
        self.assertEqual(
            states["answered"]["properties"]["abstention_reason"], {"type": "null"}
        )
        self.assertEqual(states["abstained"]["properties"]["claims"]["maxItems"], 0)
        self.assertEqual(states["partial"]["properties"]["claims"]["minItems"], 1)

    def test_preparation_and_validation_never_dispatch(self):
        with (
            patch("subprocess.Popen", side_effect=AssertionError("No dispatch")),
            patch("socket.socket", side_effect=AssertionError("No sockets")),
        ):
            prepared = prepare_payload(self.request, "tether_interpretation", 0, [])
            validate_output(self.request, prepared["payload"], self.document())


if __name__ == "__main__":
    unittest.main()
