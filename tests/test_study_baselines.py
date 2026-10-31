"""Synthetic-only deterministic selection mechanics; never biological validation."""

import unittest

from asof.serde import ContractError, canonical, encode, fingerprint
from asof.study.baselines import (
    _select,
    _tokens,
    reviewer_view,
    run_baseline,
    verify_baseline,
)
from asof.study.diagnostic import load_synthetic_request


def policy(**updates):
    return (
        dict(
            schema_version=1,
            method="extractive",
            query=None,
            max_excerpts=3,
            max_quote_bytes=8192,
            max_request_bytes=65536,
            max_result_bytes=65536,
        )
        | updates
    )


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.request = load_synthetic_request("synthetic-context")

    def test_both_fixtures_and_methods_replay(self):
        for name in ("synthetic-context", "synthetic-orientation"):
            for p in (
                policy(),
                policy(method="lexical", query="human mouse liver risk"),
            ):
                req = load_synthetic_request(name)
                result = run_baseline(req, p)
                self.assertTrue(verify_baseline(req, p, result))
                self.assertEqual(result["scientific_answer_status"], "not_attempted")
                self.assertEqual(result["model_calls"], 0)
                self.assertEqual(result["generated_interpretations"], ())

    def test_quotes_reproduce_utf8_source(self):
        result = run_baseline(self.request, policy())
        records = {
            r["observation_id"]: r for r in self.request["source_request"]["evidence"]
        }
        for q in result["excerpts"]:
            text = records[q["observation_id"]]["scientific_record"]["statement"]
            self.assertEqual(q["text"], text)
            self.assertEqual(q["utf8_span"], (0, len(text.encode())))
            self.assertEqual(q["character_span"], (0, len(text)))
            self.assertEqual(q["pointer"], "/statement")

    def test_resealed_quote_and_trace_tampering_rejected(self):
        result = run_baseline(self.request, policy())
        for location in ("quote", "trace", "usage", "source"):
            bad = encode(result)
            if location == "quote":
                bad["excerpts"][0]["text"] += " false"
            if location == "trace":
                bad["selection_trace"][0]["disposition"] = "empty"
            if location == "usage":
                bad["model_calls"] = 1
            if location == "source":
                bad["excerpts"][0]["source_ref"]["kind"] = "evaluation_only"
            with self.assertRaises(ContractError):
                verify_baseline(self.request, policy(), bad)

    def test_changed_rehashed_source_rejected(self):
        req = encode(self.request)
        row = req["source_request"]["evidence"][0]
        row["statement"] = row["scientific_record"]["statement"] = (
            "Invented changed source"
        )
        row["admitted_sha256"] = fingerprint(row["scientific_record"])
        req["source_scope"]["observations"][0]["scientific_record_sha256"] = row[
            "admitted_sha256"
        ]
        with self.assertRaises(ContractError):
            run_baseline(req, policy())

    def test_evaluator_role_and_source_reference_rejected(self):
        for place in ("outer", "source", "reference"):
            req = encode(self.request)
            if place == "outer":
                req["role"] = "evaluation_only"
            elif place == "source":
                req["source_request"]["role"] = "evaluation_only"
            else:
                req["source_request"]["evidence"][0]["source_ref"]["role"] = (
                    "evaluation_only"
                )
            with self.assertRaises(ContractError):
                run_baseline(req, policy())

    def test_bad_admitted_fingerprint_rejected(self):
        req = encode(self.request)
        req["source_request"]["evidence"][0]["admitted_sha256"] = "0" * 64
        with self.assertRaises(ContractError):
            run_baseline(req, policy())

    def test_zero_overlap_and_zero_count_are_not_scientific_answers(self):
        for p, reason in (
            (policy(max_excerpts=0), "count_bound"),
            (policy(method="lexical", query=""), "zero_overlap"),
        ):
            r = run_baseline(self.request, p)
            self.assertEqual(r["extraction_state"], "empty")
            self.assertEqual(r["scientific_answer_status"], "not_attempted")
            self.assertTrue(
                all(t["disposition"] == reason for t in r["selection_trace"])
            )
            self.assertIsNone(r["coverage"]["missing_input_count"])
            self.assertFalse(r["coverage"]["absence_claim"])

    def test_strict_policy(self):
        for p in (
            policy(max_excerpts=True),
            policy(max_result_bytes=0),
            policy(query="unexpected"),
            policy(method="other"),
            policy(max_quote_bytes=8193),
            policy(extra=1),
        ):
            with self.assertRaises(ContractError):
                run_baseline(self.request, p)

    def test_request_and_full_envelope_byte_boundaries(self):
        n = len(canonical(self.request))
        run_baseline(self.request, policy(max_request_bytes=n))
        with self.assertRaises(ContractError):
            run_baseline(self.request, policy(max_request_bytes=n - 1))
        with self.assertRaises(ContractError):
            run_baseline(self.request, policy(max_result_bytes=100))
        p = policy(max_result_bytes=99999)
        for _ in range(4):
            p["max_result_bytes"] = len(canonical(run_baseline(self.request, p)))
        r = run_baseline(self.request, p)
        self.assertEqual(len(canonical(r)), p["max_result_bytes"])
        with self.assertRaises(ContractError):
            run_baseline(
                self.request, p | {"max_result_bytes": p["max_result_bytes"] - 1}
            )

    def test_deep_immutability_and_input_copy(self):
        p = policy()
        r = run_baseline(self.request, p)
        before = canonical(r)
        p["max_excerpts"] = 0
        with self.assertRaises(TypeError):
            r["excerpts"][0]["source_ref"]["kind"] = "changed"
        with self.assertRaises(TypeError):
            r["coverage"]["absence_claim"] = True
        self.assertEqual(canonical(r), before)

    def test_masked_projection_authenticates_and_excludes_method(self):
        r = run_baseline(self.request, policy())
        v = reviewer_view(r, "Candidate A")
        self.assertEqual(v["label"], "Candidate A")
        self.assertNotIn("policy", v)
        self.assertNotIn("selection_trace", v)
        self.assertNotIn("method", v)
        self.assertNotIn("score", v)
        bad = encode(r)
        bad["excerpts"][0]["text"] = "changed"
        with self.assertRaises(ContractError):
            reviewer_view(bad, "Candidate A")

    def test_unicode_ties_empty_and_duplicate_helper(self):
        rows = []
        for ident, text in (
            ("B", "ＣＡＦÉ α <b>x</b>"),
            ("A", "café α <b>x</b>"),
            ("C", ""),
            ("D", "café α <b>x</b>"),
        ):
            science = {"statement": text}
            rows.append(
                dict(
                    observation_id=ident,
                    scientific_record=science,
                    source_ref={"kind": "invented_unit_input"},
                    admitted_sha256=fingerprint(science),
                )
            )
        quotes, trace = _select(
            rows, policy(method="lexical", query="CAFÉ α", max_excerpts=3)
        )
        self.assertEqual([q["observation_id"] for q in quotes], ["A", "B", "D"])
        self.assertEqual(quotes[1]["text"], "ＣＡＦÉ α <b>x</b>")
        self.assertEqual(_tokens("ＣＡＦÉ"), _tokens("café"))
        self.assertEqual(
            next(t["disposition"] for t in trace if t["observation_id"] == "C"), "empty"
        )
        reverse, _ = _select(
            list(reversed(rows)),
            policy(method="lexical", query="CAFÉ α", max_excerpts=3),
        )
        self.assertEqual(quotes, reverse)

    def test_quote_byte_limit_does_not_clip(self):
        text = "éé"
        rows = [
            dict(
                observation_id="A",
                scientific_record={"statement": text},
                source_ref={},
                admitted_sha256="synthetic",
            )
        ]
        q, t = _select(rows, policy(max_quote_bytes=4))
        self.assertEqual(q[0]["text"], text)
        q, t = _select(rows, policy(max_quote_bytes=3))
        self.assertEqual(q, [])
        self.assertEqual(t[0]["disposition"], "too_large")


if __name__ == "__main__":
    unittest.main()
