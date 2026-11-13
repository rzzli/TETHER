"""Published-count conservation and dependency-free arithmetic replay."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.temporal_audit import replay


class TemporalAuditReplayTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(replay.SOURCE.read_bytes())

    def test_comparisons_and_denominators(self):
        result = replay.calculate(self.document)
        self.assertEqual(len(result["archive"]), 12)
        primary = [cell for cell in result["archive"] if cell["field"] == "evidenceDate"]
        self.assertEqual([round(row["jaccard"], 4) for row in primary],
                         [0.4640, 0.7102, 0.3889, 0.5131, 0.7407, 0.8011])
        self.assertEqual([round(row["jaccard"], 4) for row in result["expression_full_modern"]], [0.8590, 0.9257])
        self.assertEqual([row["eligible"] for row in result["endpoint"]], [6365, 6365, 7612, 7612])
        self.assertEqual([row["found_ids"] for row in result["registry"]], [209, 226, 225])
        self.assertEqual([row["joint_start"] for row in result["registry"]], [185, 221, 218])
        self.assertEqual([row["exact_names"] for row in result["registry"]], [118, 130, 129])

    def test_conservation_mutations_are_rejected(self):
        controls = [lambda d: d["archive"][0].update(shared=80000),
                    lambda d: d["archive"][0]["date_counts"].update(null=1),
                    lambda d: d["archive"].__setitem__(0, d["archive"][1]),
                    lambda d: d["archive"][0].update(cutoff="2023-01-01"),
                    lambda d: d["endpoint"][1].update(no_record=0),
                    lambda d: d["registry"][2].update(found_links=299),
                    lambda d: d["registry"][0].update(exact_names=299),
                    lambda d: d["flow"].update(reserve=0),
                    lambda d: d["qualification"].update(clinical_labels=False)]
        for index, mutate in enumerate(controls):
            with self.subTest(index=index):
                bad = copy.deepcopy(self.document)
                mutate(bad)
                with self.assertRaises(ValueError):
                    replay.calculate(bad)

    def test_outputs_are_exact_and_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = (Path(folder) / value for value in ("first", "second"))
            summary = replay.replay(first)
            self.assertEqual(summary, replay.replay(second))
            for file in first.iterdir():
                self.assertEqual(file.read_bytes(), (second / file.name).read_bytes())
            for name, digest in summary["artifacts"].items():
                self.assertEqual(hashlib.sha256((first / name).read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                replay.replay(first)

    def test_modified_input_stops_before_output_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            wrong, output = root / "aggregates.json", root / "output"
            wrong.write_bytes(replay.SOURCE.read_bytes() + b"\n")
            with patch.object(replay, "SOURCE", wrong), self.assertRaisesRegex(ValueError, "digest mismatch"):
                replay.replay(output)
            self.assertFalse(output.exists())
