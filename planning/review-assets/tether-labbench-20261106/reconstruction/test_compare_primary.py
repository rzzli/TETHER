"""No actual score/reference files are opened by this qualification."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import compare_primary as comparison
from test_reconstruct import ROOT, mixed, write
import reconstruct as r


def seal_evaluation(root, generation_sha):
    outputs = {p.name: {"path": p.name, "sha256": r.sha(p.read_bytes()), "bytes": len(p.read_bytes())}
               for p in root.iterdir() if p.name not in ("SEALED.json", "journal.jsonl")}
    journal = b'{"fictional":"sealed evaluation journal"}\n'
    (root/"journal.jsonl").write_bytes(journal)
    return write(root, "SEALED.json", {"kind": "labbench_native_evaluation", "status": "completed",
        "outputs": outputs, "journal_sha256": r.sha(journal),
        "input_anchors": {"root": "fictional-generation", "external_sealed_sha256": generation_sha}})["sha256"]


class ComparisonTests(unittest.TestCase):
    def test_valid_and_resealed_contradictory_primary_aggregates(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data/cache") as directory:
            root = Path(directory)
            _, queries, keys, rows = mixed()
            independent = r.calculate(queries, keys, rows)
            independent.update(status="pass", preparation_reference_comparison=True, generation_status="completed",
                               generation_sealed_sha256="1"*64)
            independent_proof = write(root, "independent.json", independent)
            evaluation = root/"evaluation"
            evaluation.mkdir()
            write(evaluation, "REPORT.json", independent)
            write(evaluation, "input-provenance.json", {"generation": {"external_sealed_sha256": "1"*64}})
            seal_sha = seal_evaluation(evaluation, "1"*64)
            result = comparison.compare(root/"independent.json", independent_proof["sha256"], evaluation, seal_sha)
            self.assertTrue(result["primary_evaluation_comparison"])
            self.assertFalse(result["reference_files_reopened"])
            bad = copy.deepcopy(independent)
            bad["counts"]["accepted"] += 1
            write(evaluation, "REPORT.json", bad)
            resealed = seal_evaluation(evaluation, "1"*64)
            with self.assertRaisesRegex(ValueError, "counts"):
                comparison.compare(root/"independent.json", independent_proof["sha256"], evaluation, resealed)
            with self.assertRaisesRegex(ValueError, "hash"):
                comparison.compare(root/"independent.json", "0"*64, evaluation, resealed)
            write(evaluation, "REPORT.json", independent)
            wrong_generation = seal_evaluation(evaluation, "2"*64)
            with self.assertRaisesRegex(ValueError, "generation identity"):
                comparison.compare(root/"independent.json", independent_proof["sha256"], evaluation, wrong_generation)


if __name__ == "__main__":
    unittest.main()
