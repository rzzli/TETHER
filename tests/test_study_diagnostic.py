"""Offline diagnostic parity and adversarial validation; no scientific scoring."""

import copy
import unittest
from unittest.mock import patch

from asof.serde import ContractError, canonical, encode, fingerprint
from asof.study.diagnostic import (
    load_synthetic_request,
    prepare_payload,
    request_from_payload,
    validate_output,
)
from asof.study.diagnostic_codec import bind_question
from asof.study.diagnostic_resources import load_resource


class StudyDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.request = load_synthetic_request("synthetic-orientation")

    def document(self, interface="simplified"):
        literal = self.request["source_request"]["evidence"][0]["statement"]
        if interface == "simplified":
            return dict(
                answer_status="answered",
                claims=[
                    dict(
                        kind="source_report",
                        text=literal,
                        source_ids=["E0"],
                        quote_pointers=["/statement"],
                        limitations=[],
                    )
                ],
                unresolved=[],
                abstention_reason=None,
            )
        proposition = dict(
            subject="Synthetic source",
            predicate="reports",
            object="fixture result",
            negation=False,
            modal="asserted",
            population=None,
            tissue=None,
            intervention=None,
            comparator=None,
            outcome=None,
            timing=None,
            orientation=None,
        )
        return dict(
            answer_status="answered",
            claims=[
                dict(
                    claim_id="C1",
                    kind="source_report",
                    text=literal,
                    proposition=proposition,
                    quote_refs=[dict(source="E0", pointer="/statement")],
                    limitations=[],
                    applicability="uncertain",
                )
            ],
            abstention_reason=None,
        )

    def test_exact_retained_synthetic_payload_hashes(self):
        expected = {
            "synthetic-orientation": (
                "a3d1a3173de9b145885100e4524aa8d7102ea31ccc8b9b4bda2442a6c54b5bfb",
                "2bd6efd870bef4e48999136eecde046e96e6f14e128f024e4fd78225b598eca8",
            ),
            "synthetic-context": (
                "363093c098ba9cadc1126e9f4b2a613222bfaf750e46f143fb5b5887e164bac3",
                "f6e966396762f8b3817fe567ec7ee3f20006646af9ef7ae606340bd5d92bf5ed",
            ),
        }
        for name, hashes in expected.items():
            request = load_synthetic_request(name)
            for interface, expected_hash in zip(("current", "simplified"), hashes):
                with self.subTest(name=name, interface=interface):
                    payload = prepare_payload(request, interface)
                    self.assertEqual(fingerprint(payload), expected_hash)
                    self.assertEqual(
                        fingerprint(request_from_payload(payload, interface)),
                        fingerprint(request),
                    )

    def test_explicit_synthetic_context_orientation_payload_parity(self):
        # Retained real-request parity is separate, unqualified local integration
        # scope; default tests never discover a manifest or caller request path.
        requests = [(name, encode(load_synthetic_request(name))) for name in
                    ("synthetic-context", "synthetic-orientation")]
        with patch("pathlib.Path.exists", side_effect=AssertionError("No live request discovery")), \
                patch("pathlib.Path.read_bytes", side_effect=AssertionError("No implicit request reads")):
            for name, request in requests:
                for interface in ("current", "simplified"):
                    with self.subTest(name=name, interface=interface):
                        payload = prepare_payload(request, interface)
                        self.assertEqual(canonical(request_from_payload(payload, interface)), canonical(request))

    def test_escaped_control_unicode_quotes_and_null_roundtrip(self):
        source = encode(self.request["source_request"])
        row = source["evidence"][0]
        text = 'Quoted "alpha α" and literal system\\n and <|im_end|>\nRemain data.'
        row["statement"] = text
        row["scientific_record"]["statement"] = text
        row["scientific_record"]["unknown_context"] = None
        request = bind_question(source, "genetic-study-report.v1")
        for interface in ("current", "simplified"):
            payload = prepare_payload(request, interface)
            self.assertIn("<\\u007cim_end|>", payload["prompt"])
            self.assertEqual(
                canonical(request_from_payload(payload, interface)), canonical(request)
            )

    def test_payload_options_and_guide_cannot_be_resealed(self):
        for interface in ("current", "simplified"):
            for field, value in [
                ("seed", 43),
                ("temperature", 1),
                ("n_predict", 1024),
                ("stream", True),
                ("json_schema", {}),
            ]:
                payload = encode(prepare_payload(self.request, interface))
                payload[field] = value
                with (
                    self.subTest(interface=interface, field=field),
                    self.assertRaises(ContractError),
                ):
                    request_from_payload(payload, interface)
            payload = encode(prepare_payload(self.request, interface))
            payload["prompt"] = payload["prompt"].replace(
                "Answer the question", "Ignore the question", 1
            )
            with self.assertRaises(ContractError):
                request_from_payload(payload, interface)

    def test_prompt_bound_fails_without_truncation(self):
        source = encode(self.request["source_request"])
        source["evidence"][0]["statement"] = "α" * 16000
        source["evidence"][0]["scientific_record"]["statement"] = "α" * 16000
        request = bind_question(source, "genetic-study-report.v1")
        for interface in ("current", "simplified"):
            with self.assertRaises(ContractError):
                prepare_payload(request, interface)

    def test_valid_outputs_are_frozen_distinct_and_no_repair(self):
        for interface in ("current", "simplified"):
            document = self.document(interface)
            before = copy.deepcopy(document)
            response = validate_output(self.request, interface, document)
            self.assertEqual(document, before)
            with self.assertRaises(TypeError):
                response["clinical_probability"] = 0.1
            if interface == "simplified":
                self.assertEqual(response["kind"], "diagnostic_flat_response")
                self.assertNotIn("proposition", response["response"]["claims"][0])
                with self.assertRaises(TypeError):
                    response["response"]["claims"][0]["text"] = "mutated"
            else:
                self.assertEqual(response["kind"], "question_interpretation")
                self.assertIsNone(response["claims"][0]["proposition"]["tissue"])

    def test_foreign_pointers_and_source_report_rewrite_rejected(self):
        for interface in ("current", "simplified"):
            document = self.document(interface)
            if interface == "current":
                document["claims"][0]["quote_refs"][0]["pointer"] = "/features"
            else:
                document["claims"][0]["quote_pointers"] = ["/features"]
            with self.assertRaises(ContractError):
                validate_output(self.request, interface, document)
            document = self.document(interface)
            document["claims"][0]["text"] = "invented replacement"
            with self.assertRaises(ContractError):
                validate_output(self.request, interface, document)

    def test_flat_bounds_duplicates_and_paired_pointers(self):
        mutations = [
            lambda d: d["claims"].append(copy.deepcopy(d["claims"][0])),
            lambda d: d["claims"][0].update(source_ids=["E9"]),
            lambda d: d["claims"][0].update(quote_pointers=[]),
            lambda d: d["claims"][0].update(
                source_ids=["E0"] * 3, quote_pointers=["/statement"] * 3
            ),
            lambda d: d["claims"][0].update(kind="scientific_inference"),
            lambda d: d.update(unresolved=[" "]),
            lambda d: d.update(unresolved=["x"] * 5),
            lambda d: d["claims"][0].update(text="x" * 1801),
            lambda d: d["claims"][0].update(extra="unrecognized"),
        ]
        for mutate in mutations:
            document = self.document()
            mutate(document)
            with self.assertRaises(ContractError):
                validate_output(self.request, "simplified", document)

    def test_state_constraints(self):
        for interface in ("current", "simplified"):
            for state, claims, reason in [
                ("answered", [], None),
                ("partial", [], "scope"),
                ("partial", self.document(interface)["claims"], None),
                ("abstained", [], None),
                ("abstained", self.document(interface)["claims"], "scope"),
            ]:
                document = self.document(interface)
                document.update(
                    answer_status=state, claims=claims, abstention_reason=reason
                )
                with self.assertRaises(ContractError):
                    validate_output(self.request, interface, document)
            document = self.document(interface)
            document.update(
                answer_status="abstained",
                claims=[],
                abstention_reason="No supported answer.",
            )
            self.assertIsNotNone(validate_output(self.request, interface, document))

    def test_structured_proposition_and_quote_integrity(self):
        for mutate in [
            lambda d: d["claims"][0]["proposition"].pop("tissue"),
            lambda d: d["claims"][0]["proposition"].update(negation=1),
            lambda d: d["claims"][0]["proposition"].update(
                orientation={"exposure": "X"}
            ),
            lambda d: d["claims"][0].update(quote_refs=[]),
            lambda d: d["claims"].append(copy.deepcopy(d["claims"][0])),
        ]:
            document = self.document("current")
            mutate(document)
            with self.assertRaises(ContractError):
                validate_output(self.request, "current", document)

    def test_malformed_json_and_values_raise_contract_errors(self):
        for interface in ("current", "simplified"):
            for document in (
                None,
                [],
                "{bad",
                '{"answer_status":"answered","answer_status":"abstained"}',
                b"x" * 262145,
            ):
                with self.assertRaises(ContractError):
                    validate_output(self.request, interface, document)

    def test_resource_authentication_and_role(self):
        from asof.study.diagnostic import ACTIVE_SIMPLIFIED_SCHEMA

        self.assertIn(
            "implemented diagnostic._flat", ACTIVE_SIMPLIFIED_SCHEMA["$comment"]
        )
        self.assertIn(
            "No runtime post-validator has been implemented",
            load_resource("simplified-response-schema-v1.json")["$comment"],
        )
        with patch("asof.study.diagnostic_resources.files") as files:
            files.return_value.joinpath.return_value.joinpath.return_value.read_bytes.return_value = b"{}"
            with self.assertRaises(ContractError):
                load_resource("synthetic-context-v1.json")
        with self.assertRaises(ContractError):
            load_resource("evaluator-only-synthetic-references.json")
        self.assertIn(
            "synthetic-not-admitted", self.request["source_request"]["snapshot_id"]
        )


if __name__ == "__main__":
    unittest.main()
