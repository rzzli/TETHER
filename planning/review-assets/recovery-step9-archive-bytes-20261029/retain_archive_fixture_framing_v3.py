"""Finite fixture encoding/source-delta checks, not an archive graph checker."""
import hashlib
import json
from pathlib import Path
import time
import unittest

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json"
FREEZE = HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FREEZE-v3.json"
PROOF = HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FRAMING-PROOF-v3.json"


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def file_bytes(case):
    return {row["locator"]: bytes.fromhex(row["raw_hex"]) for row in case["captured"]["run_files"]}


def main():
    started = time.monotonic()
    if PROOF.exists(): raise FileExistsError(PROOF)
    frozen = json.loads(FREEZE.read_bytes())
    current = json.loads(FIXTURES.read_bytes())
    previous = json.loads((HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v2.json").read_bytes())
    first = json.loads((HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v1.json").read_bytes())
    cases = {row["id"]: row for row in current["cases"]}
    old = {row["id"]: row for row in previous["cases"]}
    changed_by_case = {}

    class Framing(unittest.TestCase):
        def test_declared_new_pins_and_preserved_predecessors(self):
            for name in ("contract", "contract_freeze", "framing", "author", "fixtures", "predecessor_fixtures",
                         "fixture_finding", "independent_fixture_findings"):
                self.assertEqual(pin(Path(frozen[name]["path"])), frozen[name])
            self.assertEqual(pin(HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v1.json")["sha256"],
                             "a911988fe787ba773901ecde2c48703a6dc1127c6434698aa26dadf81715a4bc")
            self.assertEqual(pin(HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v2.json")["sha256"],
                             "046cd4c4cfb325f7c44030db58ded081d79396878a8143688df6fa9db9cb535e")

        def test_encoding_and_finite_counts_only(self):
            self.assertEqual(len(current["cases"]), 32)
            self.assertEqual(len(cases), 32)
            self.assertTrue(all("argv_" + str(index) in cases for index in range(9)))
            for case in current["cases"]:
                capture = case["captured"]
                protocol = bytes.fromhex(capture["protocol_hex"])
                authority = bytes.fromhex(capture["authority_hex"])
                self.assertEqual(len(json.loads(protocol)), 31)
                self.assertEqual(len(json.loads(authority)), 18)
                self.assertEqual(len(file_bytes(case)), len(capture["run_files"]))
                self.assertLess(len(protocol) + len(authority) + sum(map(len, file_bytes(case).values())), 33554432)
                for item in capture["run_files"]:
                    self.assertEqual(bytes.fromhex(item["raw_hex"]).hex(), item["raw_hex"])

        def test_only_approved_source_literal_and_dependent_byte_changes(self):
            self.assertEqual([row["id"] for row in current["cases"]], [row["id"] for row in previous["cases"]])
            allowed = {"post-lease-cleanup.json", "terminal-seal.json", "late-failure.json", "after-seal-failure.json"}
            for identity, case in cases.items():
                self.assertEqual(case["bindings"], old[identity]["bindings"])
                self.assertEqual(case["expected_projection"], old[identity]["expected_projection"])
                for name in ("protocol_hex", "authority_hex"):
                    self.assertEqual(case["captured"][name], old[identity]["captured"][name])
                a, b = file_bytes(case), file_bytes(old[identity])
                self.assertEqual(a.keys(), b.keys())
                changed = {name for name in a if a[name] != b[name]}
                extra = {"failure.json", "terminal-publication-error.json"} if identity == "publication_after_receipt" else set()
                self.assertLessEqual(changed, allowed | extra)
                if identity == "early_initialization": self.assertEqual(changed, set())
                changed_by_case[identity] = sorted(changed)
                for outcome in json.loads(a["post-lease-cleanup.json"])["outcomes"]:
                    self.assertEqual(outcome["validation"], "passed")
                if identity == "exception_after_terminal":
                    self.assertEqual(json.loads(a["late-failure.json"])["close_outcomes"][0]["validation"], "passed")

        def test_publication_phase_and_unmodified_earlier_report_receipt(self):
            new, before = file_bytes(cases["publication_after_receipt"]), file_bytes(old["publication_after_receipt"])
            self.assertEqual(new["parent-report.json"], before["parent-report.json"])
            self.assertEqual(new["receipt.json"], before["receipt.json"])
            report = json.loads(new["parent-report.json"])
            self.assertEqual(report["status"], "recognition_observations_retained_independent_qualification_pending")
            self.assertEqual(report["finalization_errors"], [])
            marker = json.loads(new["failure.json"])
            error = json.loads(new["terminal-publication-error.json"])
            cleanup = json.loads(new["post-lease-cleanup.json"])
            for row in (marker, error["publication_error"], error["primary_failure"], error["finalization_errors"][0], cleanup["primary_failure"]):
                self.assertEqual(row["phase"], "terminal_publication")

        def test_entire_early_unknown_projection_and_maps(self):
            files = file_bytes(cases["early_initialization"])
            expected = {"parent-reservation.json", "failure.json", "parent-report.json", "receipt.json",
                        "post-lease-cleanup.json", "terminal-seal.json"}
            self.assertEqual(set(files), expected)
            report = json.loads(files["parent-report.json"])
            self.assertNotIn("returncode", report)
            self.assertNotIn("reaped", report)
            self.assertIs(report["call_return_observed"], False)
            self.assertEqual(report["failure"], {"error_class": "OSError", "error": "synthetic constructor stop"})
            self.assertEqual(json.loads(files["failure.json"])["phase"], "parent_reservation_or_journal_initialization")
            cleanup = json.loads(files["post-lease-cleanup.json"])
            self.assertEqual(cleanup["outcomes"], [])
            self.assertEqual(cleanup["close_errors"], [])
            self.assertEqual(set(json.loads(files["receipt.json"])["outputs"]), {"parent-reservation.json", "failure.json", "parent-report.json"})
            self.assertEqual(set(json.loads(files["terminal-seal.json"])["outputs"]), expected - {"terminal-seal.json"})
            self.assertEqual(cases["early_initialization"]["expected_projection"]["captured_graph_status"], "incomplete_captured_graph")
            for case in current["cases"]:
                for name in ("profile_qualified", "originals_authenticated", "actual_directory_complete", "source_qualified"):
                    self.assertIs(case["expected_projection"][name], False)
            # V1's wrong fields/outcome remain visibly retained, not rewritten.
            earlier = next(row for row in first["cases"] if row["id"] == "early_initialization")
            self.assertIn("returncode", json.loads(file_bytes(earlier)["parent-report.json"]))
            self.assertEqual(len(json.loads(file_bytes(earlier)["post-lease-cleanup.json"])["outcomes"]), 1)

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Framing))
    elapsed = time.monotonic() - started
    proof = dict(schema_version=1, status="fixture_framing_and_narrow_source_delta_passed" if result.wasSuccessful() and elapsed < 20 else "failed",
        fixtures=pin(FIXTURES), freeze=pin(FREEZE), recorder=pin(Path(__file__).resolve()),
        methods=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        failure_details=[dict(test=str(case), traceback=trace) for case, trace in result.failures + result.errors],
        cases=32, argv_derivations=9, changed_run_files_by_case=changed_by_case,
        early_source_projection="RunJournal constructor raises before execution journal return; outer reservation only, no API/Owner/leases. Selected incomplete report projection, not complete source/resource evidence.",
        elapsed_seconds=elapsed, maximum_seconds=20, expected_graph_results_are_authored_not_observed=True,
        actual_archive_graph_checks=0, archive_checker_implemented=False, actual_old_runs_replayed=0,
        source_closure_qualification=False, SDK_native_payload_operations=0, profile_qualified=False)
    with PROOF.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(proof, out, indent=2); out.write("\n")
    print(json.dumps(dict(status=proof["status"], methods=result.testsRun, cases=32, proof_sha256=pin(PROOF)["sha256"])))
    return 0 if proof["status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
