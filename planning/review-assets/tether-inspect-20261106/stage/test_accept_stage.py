"""Fictional adverse-report tests; no production evaluation or source mutation."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("accept_stage_under_test", HERE/"accept_stage.py")
accept = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accept)


def runtime_fixture():
    statuses = ["completed"]*4+["budget_exhausted"]*3+["error"]*9+["timeout", "interrupted_unresolved", "unexecuted"]
    rows = [{"id": "fictional-"+str(i), "status": status} for i, status in enumerate(statuses)]
    review = {"status": "PASS", "freeze_sha256": "a"*64, "stage_seal_sha256": "b"*64,
        "preparation_sha256": "c"*64, "automatic_redispatch": False, "provider_cost_usd": 0,
        "logical_dispositions": rows, "status_counts": dict(accept.Counter(statuses)),
        "ordinary": {"status": "PASS", "scheduled": 16, "expected_fields_matched": 16},
        "IX06": {"status": "PASS", "provider_dispatches": 1, "unresolved_calls": 1},
        "IX08": {"status": "PASS", "owners": 1, "provider_dispatches": 1, "native_workers": 2}}
    return review, {"case_dispositions": copy.deepcopy(rows)}


def coverage_fixture():
    matrix = {"obligations": [{"id": "fictional-"+str(i), "frozen_case_ids": ["EP-fictional"]} for i in range(27)]}
    evidence = {"path": "fictional.json", "sha256": "d"*64, "bytes": 10}
    rows = [{"id": original["id"], "archive_result_status": "finite_archive_conformance_pass",
        "runtime_control_ids": [], "runtime_result_status": "archive_only_no_live_schema_equivalence_claim",
        "archive_results": {"scheduled_cells": 9, "full_conformance": 9,
            "by_arm": {arm: {"scheduled_cells": 3, "full_conformance": 3} for arm in accept.ARMS}},
        "actual_result_evidence": [evidence]} for original in matrix["obligations"]]
    coverage = {"schema_version": 1, "status": "complete_with_declared_gaps", "obligations": rows,
        "full_production_runtime_equivalence": False, "scientific_validation": False,
        "remaining_gaps": ["Fictional deliberate scope gap"],
        "runtime_cases": [], "runtime_status_counts": {},
        "evidence": {"primary_reconstruction": evidence, "runtime_reconstruction": dict(evidence, sha256="e"*64),
                     "primary_stage_seal_sha256": "f"*64, "runtime_stage_seal_sha256": "b"*64}}
    return coverage, matrix


class AcceptanceTests(unittest.TestCase):
    def test_rejects_failed_or_wrongly_anchored_runtime_review(self):
        review, runtime = runtime_fixture()
        accept.validate_runtime_review(review, runtime, "a"*64, "b"*64, "c"*64)
        for key, value in (("status", "FAIL"), ("freeze_sha256", "0"*64), ("automatic_redispatch", True)):
            changed = copy.deepcopy(review); changed[key] = value
            with self.assertRaises(ValueError):
                accept.validate_runtime_review(changed, runtime, "a"*64, "b"*64, "c"*64)
        changed = copy.deepcopy(review); changed["ordinary"]["expected_fields_matched"] = 15
        with self.assertRaises(ValueError):
            accept.validate_runtime_review(changed, runtime, "a"*64, "b"*64, "c"*64)

    def test_rejects_omitted_or_duplicate_runtime_dispositions(self):
        review, runtime = runtime_fixture()
        for rows in (review["logical_dispositions"][:-1], review["logical_dispositions"][:-1]+[review["logical_dispositions"][0]]):
            changed = copy.deepcopy(review); changed["logical_dispositions"] = rows
            with self.assertRaises(ValueError):
                accept.validate_runtime_review(changed, runtime, "a"*64, "b"*64, "c"*64)

    def test_coverage_requires_all_obligations_and_honest_scope(self):
        coverage, matrix = coverage_fixture()
        accept.validate_coverage(coverage, matrix, "d"*64, "e"*64, "f"*64, "b"*64, {})
        for field, value in (("status", "pending"), ("full_production_runtime_equivalence", True),
                             ("obligations", coverage["obligations"][:-1])):
            changed = copy.deepcopy(coverage); changed[field] = value
            with self.assertRaises(ValueError):
                accept.validate_coverage(changed, matrix, "d"*64, "e"*64, "f"*64, "b"*64, {})
        coverage["runtime_cases"] = [{"id": "invented", "actual_status": "completed", "independent_check": "PASS"}]
        coverage["runtime_status_counts"] = {"completed": 1}
        accept.validate_coverage(coverage, matrix, "d"*64, "e"*64, "f"*64, "b"*64, {"invented": "completed"})
        coverage["runtime_cases"][0]["actual_status"] = "unexecuted"
        with self.assertRaises(ValueError):
            accept.validate_coverage(coverage, matrix, "d"*64, "e"*64, "f"*64, "b"*64, {"invented": "completed"})

    def test_consumed_json_bytes_must_match_expected_hash(self):
        with tempfile.TemporaryDirectory(dir=accept.ROOT/"data/cache") as folder:
            path = Path(folder)/"report.json"
            path.write_text(json.dumps({"status": "PASS"}))
            pin = accept.proof(path)
            self.assertEqual(accept.read(path, expected_sha256=pin["sha256"])["status"], "PASS")
            path.write_text(json.dumps({"status": "FAIL"}))
            with self.assertRaises(ValueError):
                accept.read(path, expected_sha256=pin["sha256"])


if __name__ == "__main__":
    unittest.main()
