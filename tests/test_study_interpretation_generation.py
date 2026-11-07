"""Prospective pure v3 contracts; synthetic data only, no native execution."""

import copy
import hashlib
import json
import re
import unittest
from collections.abc import Mapping
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, encode, fingerprint
from tether_engine.study import (
    authority_four_arm,
    interpretation_interface,
    native_interpretation,
)
from tether_engine.study.diagnostic import load_synthetic_request
from tether_engine.study.diagnostic_codec import bind_question, pointer, quote_choices
from tether_engine.study.fixed_evidence import load_plan
from tether_engine.study.interpretation_grammar import GENERATOR, build_grammar
from tether_engine.study.interpretation_generation import (
    INTERFACE,
    prepare_payload,
    request_from_payload,
    validate_output,
)


def grammar_graph(grammar):
    """Independent structural oracle; deliberately not a native recognizer.

    Ignore literal/character-class content before collecting references. This
    checks finite, closed productions without assuming generator rule names.
    """
    graph = {}
    # Unicode line separators may be valid literal content; GBNF productions
    # here are separated by the actual ASCII newline only.
    for line in grammar.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, expression = line.split("::=", 1)
        name = name.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9-]*", name) or name in graph:
            raise AssertionError("Invalid or duplicate grammar rule")
        outside, index = [], 0
        while index < len(expression):
            character = expression[index]
            if character == "#":
                break
            if character in ('"', "["):
                end = '"' if character == '"' else "]"
                index += 1
                while index < len(expression):
                    if expression[index] == "\\":
                        index += 2
                    elif expression[index] == end:
                        index += 1
                        break
                    else:
                        index += 1
                else:
                    raise AssertionError("Unterminated grammar literal/class")
                outside.append(" ")
            else:
                outside.append(character)
                index += 1
        outside = "".join(outside)
        if "*" in outside or "+" in outside:
            raise AssertionError("Unbounded grammar repetition")
        graph[name] = set(re.findall(r"[A-Za-z_][A-Za-z_0-9-]*", outside))
    if "root" not in graph:
        raise AssertionError("Missing root production")
    if any(references - graph.keys() for references in graph.values()):
        raise AssertionError("Unresolved grammar reference")
    visiting, visited = set(), set()

    def visit(name):
        if name in visiting:
            raise AssertionError("Recursive grammar is not finite construction")
        if name not in visited:
            visiting.add(name)
            for child in graph[name]:
                visit(child)
            visiting.remove(name)
            visited.add(name)

    for name in graph:
        visit(name)
    return graph


def assert_deeply_frozen(test, value):
    if isinstance(value, Mapping):
        before = fingerprint(value)
        with test.assertRaises(TypeError):
            value["__mutation_probe__"] = True
        test.assertEqual(fingerprint(value), before)
        for child in value.values():
            assert_deeply_frozen(test, child)
    elif isinstance(value, (list, tuple)):
        test.assertIsInstance(value, tuple)
        for child in value:
            assert_deeply_frozen(test, child)


class InterpretationGrammarContractTests(unittest.TestCase):
    def test_public_generator_identity_and_bound_immutable_artifact(self):
        self.assertEqual(GENERATOR, "strict-interpretation-gbnf-v1")
        artifact = build_grammar({"Q0": "Invented source."}, claim_limit=3)
        self.assertEqual(artifact["generator"], GENERATOR)
        self.assertEqual(
            artifact["grammar_bytes"], len(artifact["grammar"].encode("utf-8"))
        )
        self.assertEqual(
            artifact["grammar_sha256"],
            hashlib.sha256(artifact["grammar"].encode("utf-8")).hexdigest(),
        )
        self.assertEqual(tuple(artifact["quote_ids"]), ("Q0",))
        self.assertEqual(tuple(artifact["source_report_ids"]), ("Q0",))
        with self.assertRaises(TypeError):
            artifact["grammar"] = "rewritten"

    def test_public_preparation_interface_has_a_new_identity(self):
        self.assertEqual(INTERFACE, "source-quote-interpretation-v3-gbnf")

    def test_artifact_is_deterministic_and_owns_its_inputs(self):
        inputs = {"Q0": "First invented source.", "Q1": "Second invented source."}
        artifact = build_grammar(inputs, claim_limit=2)
        baseline = fingerprint(artifact)
        self.assertEqual(
            baseline,
            fingerprint(
                build_grammar(dict(reversed(list(inputs.items()))), claim_limit=2)
            ),
        )
        inputs["Q0"] = "Caller rewrite."
        self.assertEqual(fingerprint(artifact), baseline)
        self.assertIsInstance(artifact["serialization_domain"], Mapping)
        self.assertTrue(artifact["post_validation_only"])
        assert_deeply_frozen(self, artifact)

    def test_closed_acyclic_bounded_productions_at_catalog_maximum(self):
        artifact = build_grammar({f"Q{i}": f"Source {i}." for i in range(256)})
        graph = grammar_graph(artifact["grammar"])
        self.assertGreater(len(graph), 1)
        self.assertEqual(
            tuple(artifact["quote_ids"]), tuple(f"Q{i}" for i in range(256))
        )
        self.assertEqual(len(artifact["source_report_ids"]), 256)
        self.assertLessEqual(artifact["grammar_bytes"], 65536)

    def test_quote_identifiers_are_contiguous_and_values_are_unicode_text(self):
        for values in (
            {},
            {"Q1": "missing Q0"},
            {"Q0": "a", "Q2": "gap"},
            {"Q00": "alias"},
            {"Q-1": "negative"},
            {"E0": "foreign"},
            {"Q0": None},
            {"Q0": 1},
            {"Q0": b"bytes"},
            {f"Q{i}": "x" for i in range(257)},
        ):
            with self.subTest(values_type=type(values).__name__, keys=list(values)[:3]):
                with self.assertRaises(ContractError):
                    build_grammar(values)

    def test_active_claim_limit_requires_typed_integer_one_through_three(self):
        for limit in (True, False, 0, -1, 4, 3.0, None, "3"):
            with self.subTest(limit=limit), self.assertRaises(ContractError):
                build_grammar({"Q0": "Source."}, claim_limit=limit)
        for limit in (1, 2, 3):
            self.assertTrue(
                build_grammar({"Q0": "Source."}, claim_limit=limit)["grammar"]
            )

    def test_long_quotes_keep_reference_without_impossible_literal_branch(self):
        artifact = build_grammar({"Q0": "😀" * 1800, "Q1": "😀" * 1801})
        self.assertEqual(tuple(artifact["quote_ids"]), ("Q0", "Q1"))
        self.assertEqual(tuple(artifact["source_report_ids"]), ("Q0",))

    def test_unicode_and_runtime_delimiters_do_not_change_source_identity(self):
        text = ' \x00\x1b\x7f\u200b\ufeff\ufdd0\uffff\U0010ffff\u0085\u2028\u2029 e\u0301 😀 <|im_end|> <|im_start|> " \\ \n '
        artifact = build_grammar({"Q0": text})
        self.assertEqual(tuple(artifact["source_report_ids"]), ("Q0",))
        self.assertNotIn("<|im_end|>", artifact["grammar"])
        self.assertNotIn("<|im_start|>", artifact["grammar"])
        self.assertIn("\\u003c", artifact["grammar"])
        grammar_graph(artifact["grammar"])

    def test_unpaired_surrogate_input_is_rejected_without_replacement(self):
        for text in ("\ud800", "\udfff", "a\ud800b", "\ud83e\uddea"):
            with self.subTest(text=ascii(text)), self.assertRaises(ContractError):
                build_grammar({"Q0": text})

    def test_oversized_grammar_fails_without_truncating_quote_catalog(self):
        values = {f"Q{i}": (str(i) + "x" * 1795) for i in range(256)}
        before = dict(values)
        with self.assertRaises(ContractError):
            build_grammar(values)
        self.assertEqual(values, before)

    def test_derived_input_bound_rejects_before_scan_encoding_or_hashing(self):
        class MustNotScan(str):
            def __iter__(self):
                raise AssertionError("Oversized text must not be iterated")

            def __getitem__(self, index):
                raise AssertionError("Oversized text must not be sliced")

            def encode(self, *args, **kwargs):
                raise AssertionError("Oversized text must not be encoded")

        value = MustNotScan("x" * 32769)
        with patch(
            "tether_engine.study.interpretation_grammar.hashlib.sha256",
            side_effect=AssertionError("Oversized text must not be hashed"),
        ):
            with self.assertRaises(ContractError):
                build_grammar({"Q0": value})
        with self.assertRaises(ContractError):
            build_grammar({"Q0": "x" * 32769})

    def test_utf8_total_bound_applies_even_when_decoded_count_fits(self):
        values = {"Q0": "😀" * 4096, "Q1": "😀" * 4097}
        self.assertLess(sum(map(len, values.values())), 32768)
        self.assertGreater(sum(len(v.encode("utf-8")) for v in values.values()), 32768)
        with self.assertRaises(ContractError):
            build_grammar(values)

    def test_exact_inherited_input_byte_boundary_retains_long_quote_ids(self):
        for text in ("x" * 32768, "😀" * 8192):
            self.assertEqual(len(text.encode("utf-8")), 32768)
            artifact = build_grammar({"Q0": text})
            self.assertEqual(tuple(artifact["quote_ids"]), ("Q0",))
            self.assertEqual(tuple(artifact["source_report_ids"]), ())
            self.assertEqual(
                artifact["quote_text_sha256"]["Q0"],
                hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )


class InterpretationGenerationTests(unittest.TestCase):
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
                    text=text if kind == "source_report" else "Invented analysis.",
                    quote_refs=[quote["quote_id"]],
                    limitations=[]
                    if kind == "source_report"
                    else ["Invented data only."],
                )
            ],
            unresolved=[],
            abstention_reason=None,
        )

    def validate(self, document):
        return validate_output(self.request, self.payload, document)

    def changed_source(self, text):
        request = encode(self.request)
        row = request["source_request"]["evidence"][0]
        row["statement"] = row["scientific_record"]["statement"] = text
        return bind_question(
            request["source_request"], request["question"]["question_id"]
        )

    def test_new_payload_is_bound_preparation_only_and_archives_acceptance_schema(self):
        self.assertEqual(self.prepared["interface"], INTERFACE)
        self.assertFalse(self.prepared["execution_authorized"])
        self.assertEqual(self.prepared["native_conformance"], "unverified")
        self.assertIn("grammar", self.payload)
        self.assertNotIn("json_schema", self.payload)
        self.assertIn("acceptance_schema", self.prepared)
        self.assertEqual(
            self.payload["grammar"], self.prepared["generation_grammar"]["grammar"]
        )
        self.assertLessEqual(len(canonical(self.payload)), 65536)
        self.assertLessEqual(len(self.payload["prompt"].encode("utf-8")), 32768)
        self.assertEqual(
            fingerprint(request_from_payload(self.payload)), fingerprint(self.request)
        )
        self.assertEqual(self.prepared["payload_sha256"], fingerprint(self.payload))
        self.assertEqual(self.prepared["request_sha256"], fingerprint(self.request))

    def test_old_and_new_payload_reconstruction_are_separate(self):
        old = interpretation_interface.prepare_payload(
            self.request, "tether_interpretation", 0, []
        )
        with self.assertRaises(ContractError):
            interpretation_interface.request_from_payload(self.payload)
        with self.assertRaises(ContractError):
            request_from_payload(old["payload"])
        self.assertIn("json_schema", old["payload"])
        self.assertNotIn("grammar", old["payload"])
        self.assertEqual(
            fingerprint(interpretation_interface.request_from_payload(old["payload"])),
            fingerprint(self.request),
        )

    def test_existing_native_and_controller_routes_still_use_v2_by_default(self):
        self.assertIs(
            authority_four_arm.prepare_native_payload,
            interpretation_interface.prepare_payload,
        )
        self.assertEqual(
            native_interpretation.INTERFACE, interpretation_interface.INTERFACE
        )
        self.assertNotEqual(native_interpretation.INTERFACE, INTERFACE)

    def test_twelve_current_namespace_v2_fingerprints_and_catalogs_are_fixed(self):
        # New namespace pins for invented payloads; original pre-v3 fingerprints
        # remain unchanged in the immutable pre-migration checkpoint.
        expected = {
            "synthetic-context": (
                "c44006befe827b3a4c9d68124fa0e90dd1e6b7e654a48147fe5bc10ecf36666e",
                "74c709a691f5ab6e0b0dd85bb6ab9e60ddb29b1124146a6241a2d5b50318da6c",
                "ae993084816d871e3e264923791af5ba71611e820b40b7cced7b186e269c3e9a",
                "71e1dc896f57904b8ffef976eea9ec5d6f0a1ca79e8189ea15797f714a3c8573",
                "d7dca0b2b0a46cfeab28bdabfd82afcaeb5f156edd20ec01944aedf101a97a95",
                "e8d133d56eba8abe8467449c070916a3cd56880d961b2d1b04946cc5f3a3ba72",
            ),
            "synthetic-orientation": (
                "00f5a097293212e811f91af71fc9de68c728dec4986aa3b3204547d730584e71",
                "2dec321a6d17a8f4da31eba0cb03eef71a24a3fda4e98250f1004c1b98fdef00",
                "947ef0dac513e88addb0e504c31f65e89eb1ca9ebfc083fb5acfe14382348d80",
                "cc0b40d9693c3eab80c28941a19a699f67fb0047a1a061c7cd418ed19b6fe12d",
                "af9741d1c3e4560d1868f6339b656653cafa7bddb24f6806f8b5be52df7ea4f7",
                "f3825a203616946782ddfeae557e66428f4bab51ea4c8987de1a7b68cc5f2744",
            ),
        }
        plan = load_plan()
        checked = 0
        for fixture, fingerprints in expected.items():
            request = load_synthetic_request(fixture)
            aliases = list(quote_choices(request))
            observed = []
            for arm, stages in (
                ("tether_interpretation", plan["tether_stages"]),
                ("adapted_virtual_biotech_interpretation", plan["stage_order"]),
            ):
                for index, _ in enumerate(stages):
                    feedback = [
                        dict(stage=stage, source_ids=aliases)
                        for stage in stages[:index]
                    ]
                    prepared = interpretation_interface.prepare_payload(
                        request, arm, index, feedback
                    )
                    observed.append(prepared["payload_sha256"])
                    texts = {
                        row["quote_id"]: pointer(
                            encode(request), row["request_pointer"]
                        )
                        for row in prepared["semantic_data"]["quote_catalog"]
                    }
                    self.assertLessEqual(
                        sum(len(text.encode("utf-8")) for text in texts.values()), 32768
                    )
                    grammar = build_grammar(texts, claim_limit=prepared["claim_limit"])
                    self.assertEqual(tuple(grammar["quote_ids"]), tuple(texts))
                    checked += 1
            self.assertEqual(tuple(observed), fingerprints)
        self.assertEqual(checked, 12)

    def test_grammar_options_guide_and_catalog_tampering_are_rejected(self):
        for key, value in (
            ("grammar", self.payload["grammar"] + "\n# tampered"),
            ("seed", 43),
            ("stream", True),
            ("n_predict", 2048),
            ("json_schema", {}),
        ):
            payload = encode(self.payload)
            payload[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                request_from_payload(payload)
        for old, new in (("Q0", "Q999"), ("Return JSON", "Return prose")):
            payload = encode(self.payload)
            self.assertIn(old, payload["prompt"])
            payload["prompt"] = payload["prompt"].replace(old, new, 1)
            with self.assertRaises(ContractError):
                request_from_payload(payload)

    def test_finalized_response_binds_generation_contract_and_original_values(self):
        document = self.document()
        result = self.validate(canonical(document))
        self.assertEqual(result["kind"], "source_quote_interpretation_v3")
        self.assertEqual(result["interface"], INTERFACE)
        self.assertEqual(result["request_sha256"], fingerprint(self.request))
        self.assertEqual(result["payload_sha256"], fingerprint(self.payload))
        self.assertEqual(
            result["generation_contract_sha256"],
            fingerprint(self.prepared["generation_grammar"]),
        )
        self.assertEqual(encode(result["response"]), document)
        self.assertEqual(result["quotes"][0]["text"], document["claims"][0]["text"])
        self.assertEqual(result["features"], {})
        self.assertIsNone(result["clinical_probability"])
        self.assertEqual(result["scientific_validation"], "not_established")

    def test_preparation_and_response_are_recursively_immutable(self):
        before = fingerprint(self.prepared)
        document = self.document()
        result = self.validate(document)
        result_before = fingerprint(result)
        document["claims"][0]["text"] = "Caller mutation."
        assert_deeply_frozen(self, self.prepared)
        assert_deeply_frozen(self, result)
        self.assertEqual(fingerprint(self.prepared), before)
        self.assertEqual(fingerprint(result), result_before)

    def test_all_three_states_preserve_existing_semantics(self):
        for state in ("answered", "partial", "abstained"):
            document = self.document()
            document["answer_status"] = state
            document["abstention_reason"] = (
                None if state == "answered" else "Context unavailable."
            )
            if state == "abstained":
                document["claims"] = []
            with self.subTest(state=state):
                self.assertEqual(encode(self.validate(document)["response"]), document)

    def test_contradictory_states_and_blank_reasons_are_rejected(self):
        for state, claims, reason in (
            ("answered", True, "reason"),
            ("answered", False, None),
            ("partial", True, None),
            ("partial", False, "reason"),
            ("abstained", True, "reason"),
            ("abstained", False, None),
            ("partial", True, "\u001c\u0085\u2003"),
        ):
            document = self.document()
            document.update(answer_status=state, abstention_reason=reason)
            if not claims:
                document["claims"] = []
            with (
                self.subTest(state=state, claims=claims, reason=reason),
                self.assertRaises(ContractError),
            ):
                self.validate(document)

    def test_exact_source_literal_cannot_change_text_or_quote_pair(self):
        for transform in (lambda s: s + " ", lambda s: s.upper(), lambda s: s[:10]):
            document = self.document()
            document["claims"][0]["text"] = transform(document["claims"][0]["text"])
            with self.assertRaises(ContractError):
                self.validate(document)
        document = self.document()
        document["claims"][0]["quote_refs"] = [
            self.prepared["semantic_data"]["quote_catalog"][-1]["quote_id"]
        ]
        with self.assertRaises(ContractError):
            self.validate(document)

    def test_inference_and_caution_require_limitations_without_rewriting_text(self):
        for kind in ("scientific_inference", "caution"):
            document = self.document(kind)
            result = self.validate(document)
            self.assertEqual(
                result["response"]["claims"][0]["text"], "Invented analysis."
            )
            self.assertNotEqual(result["quotes"][0]["text"], "Invented analysis.")
            document["claims"][0]["limitations"] = []
            with self.assertRaises(ContractError):
                self.validate(document)

    def test_distinct_reference_orders_are_preserved(self):
        ids = [
            row["quote_id"] for row in self.prepared["semantic_data"]["quote_catalog"]
        ]
        self.assertGreaterEqual(len(ids), 2)
        for refs in ((ids[0], ids[-1]), (ids[-1], ids[0])):
            document = self.document("caution")
            document["claims"][0]["quote_refs"] = list(refs)
            result = self.validate(document)
            self.assertEqual(tuple(result["response"]["claims"][0]["quote_refs"]), refs)
            self.assertEqual(tuple(q["quote_id"] for q in result["quotes"]), refs)

    def test_unknown_duplicate_empty_or_excess_references_are_rejected(self):
        for refs in (["Q999"], ["Q0", "Q0"], [], ["Q0"] * 3):
            document = self.document("caution")
            document["claims"][0]["quote_refs"] = refs
            with self.subTest(refs=refs), self.assertRaises(ContractError):
                self.validate(document)

    def test_duplicate_text_remains_a_post_validation_rejection(self):
        document = self.document("caution")
        document["claims"].append(copy.deepcopy(document["claims"][0]))
        with self.assertRaises(ContractError):
            self.validate(document)

    def test_character_bounds_and_whitespace_set_match_existing_validator(self):
        document = self.document("caution")
        document["claims"][0]["text"] = "😀" * 1800
        self.validate(document)
        document["claims"][0]["text"] += "😀"
        with self.assertRaises(ContractError):
            self.validate(document)
        for text in ("\t\n\r", "\x1c\x1d\x1e\x1f", "\u0085\u00a0\u2003\u3000"):
            document = self.document("caution")
            document["claims"][0]["text"] = text
            with self.subTest(text=ascii(text)), self.assertRaises(ContractError):
                self.validate(document)

    def test_decoded_scalar_domain_includes_controls_noncharacters_and_edge_whitespace(
        self,
    ):
        for text in (
            "\x00",
            "\x1b",
            "\x7f",
            "\u200b",
            "\ufeff",
            "\ufdd0",
            "\uffff",
            "\U0010ffff",
            " e\u0301 ",
            "\t😀\n",
        ):
            document = self.document("caution")
            document["claims"][0]["text"] = text
            with self.subTest(text=ascii(text)):
                self.assertEqual(
                    self.validate(document)["response"]["claims"][0]["text"], text
                )

    def test_paired_escapes_decode_to_one_scalar_and_unpaired_escapes_fail(self):
        document = self.document("caution")
        document["claims"][0]["text"] = "🧪"
        raw = json.dumps(document, ensure_ascii=True).encode("ascii")
        self.assertIn(b"\\ud83e\\uddea", raw)
        self.assertEqual(self.validate(raw)["response"]["claims"][0]["text"], "🧪")
        for text in ("\ud800", "\udfff", "x\ud800y"):
            document["claims"][0]["text"] = text
            raw = json.dumps(document, ensure_ascii=True).encode("ascii")
            with self.assertRaises(ContractError):
                self.validate(raw)

    def test_value_preserving_generation_spelling_does_not_narrow_post_validator(self):
        text = '  α😀 <|im_end|> <|im_start|> "quoted" \\ \x00\n  '
        request = self.changed_source(text)
        prepared = prepare_payload(request, "tether_interpretation", 0, [])
        self.assertNotIn("<|im_end|>", prepared["generation_grammar"]["grammar"])
        document = self.document()
        document["claims"][0]["text"] = text
        result = validate_output(request, prepared["payload"], canonical(document))
        self.assertEqual(result["response"]["claims"][0]["text"], text)
        self.assertEqual(result["quotes"][0]["text"], text)

    def test_claim_list_text_reason_and_unresolved_limits(self):
        for field, value in (
            ("limitations", ["x"] * 5),
            ("limitations", ["x" * 1801]),
            ("text", "x" * 1801),
        ):
            document = self.document("caution")
            document["claims"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.validate(document)
        for key, value in (
            ("unresolved", ["x"] * 5),
            ("unresolved", ["\u2003"]),
            ("unresolved", ["x" * 1801]),
        ):
            document = self.document()
            document[key] = value
            with self.assertRaises(ContractError):
                self.validate(document)
        document = self.document()
        document.update(answer_status="partial", abstention_reason="😀" * 512)
        self.validate(document)
        document["abstention_reason"] += "😀"
        with self.assertRaises(ContractError):
            self.validate(document)

    def test_inherited_lower_cap_and_explicit_three_claim_ceiling(self):
        for inherited, expected in ((1, 1), (64, 3)):
            request = encode(self.request)
            request["source_request"]["bounds"]["max_claims"] = inherited
            prepared = prepare_payload(request, "tether_interpretation", 0, [])
            self.assertEqual(prepared["claim_limit"], expected)
            document = self.document("caution")
            document["claims"] = [
                dict(document["claims"][0], text=f"Claim {i}")
                for i in range(expected + 1)
            ]
            with self.assertRaises(ContractError):
                validate_output(request, prepared["payload"], document)

    def test_foreign_request_predictive_fields_and_malformed_json_are_rejected(self):
        with self.assertRaises(ContractError):
            validate_output(
                load_synthetic_request("synthetic-orientation"),
                self.payload,
                self.document(),
            )
        for field, value in (("features", {}), ("clinical_probability", 0.5)):
            document = self.document()
            document[field] = value
            with self.assertRaises(ContractError):
                self.validate(document)
        for raw in (
            b"{",
            b'{"answer_status":"answered","answer_status":"partial"}',
            b" " * 262145,
        ):
            with self.assertRaises(ContractError):
                self.validate(raw)

    def test_history_remains_bound_untrusted_selection(self):
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
        self.assertEqual(
            fingerprint(request_from_payload(prepared["payload"])),
            fingerprint(self.request),
        )
        with self.assertRaises(ContractError):
            prepare_payload(
                self.request,
                "tether_interpretation",
                0,
                [dict(stage="chief_of_staff", source_ids=["E0"])],
            )

    def test_overlarge_catalog_and_complete_original_fail_without_clipping(self):
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

    def test_pure_preparation_and_validation_never_dispatch_or_load_native_code(self):
        with (
            patch("subprocess.Popen", side_effect=AssertionError("No dispatch")),
            patch("socket.socket", side_effect=AssertionError("No socket")),
            patch("ctypes.CDLL", side_effect=AssertionError("No native DLL")),
        ):
            prepared = prepare_payload(self.request, "tether_interpretation", 0, [])
            validate_output(self.request, prepared["payload"], self.document())


if __name__ == "__main__":
    unittest.main()
