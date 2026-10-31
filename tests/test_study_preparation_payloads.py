"""Pure preparation does not admit sources or activate execution."""

import unittest

from asof.serde import ContractError, canonical, encode
from asof.study.diagnostic import load_synthetic_request
from asof.study.preparation_payloads import prepare_payloads


class PreparationPayloadTests(unittest.TestCase):
    def test_complete_request_and_aligned_caps(self):
        for bound in (2, 3, 12):
            request = encode(load_synthetic_request("synthetic-orientation"))
            request["source_request"]["bounds"]["max_claims"] = bound
            before = canonical(request)
            cells = prepare_payloads(request)
            self.assertEqual(len(cells), 6)
            self.assertEqual(canonical(request), before)
            for cell in cells:
                data = cell["semantic_data"]
                self.assertEqual(canonical(data["original_request"]), before)
                cap = min(3, bound)
                self.assertIn(
                    f"Active limits: {cap} claims;", cell["payload"]["prompt"]
                )
                self.assertEqual(
                    cell["payload"]["json_schema"]["properties"]["claims"]["maxItems"],
                    cap,
                )
                self.assertEqual(cell["claim_limit"], cap)
                self.assertFalse(cell["execution_authorized"])
                self.assertEqual(
                    cell["history_scope"], "exact_hypothetical_only_not_a_token_maximum"
                )

    def test_hypothetical_history_is_original_aliases_only(self):
        request = load_synthetic_request("synthetic-context")
        cells = prepare_payloads(request)
        self.assertEqual(
            [len(c["semantic_data"]["prior_source_id_feedback"]) for c in cells],
            [0, 0, 1, 2, 3, 4],
        )
        for cell in cells:
            for history in cell["semantic_data"]["prior_source_id_feedback"]:
                self.assertEqual(set(history), {"stage", "source_ids"})
                self.assertEqual(tuple(history["source_ids"]), ("E0", "E1"))

    def test_no_source_truncation_on_size_failure(self):
        request = encode(load_synthetic_request("synthetic-orientation"))
        request["source_request"]["instructions"] += "x" * 40000
        with self.assertRaises(ContractError):
            prepare_payloads(request)


if __name__ == "__main__":
    unittest.main()
