"""Preserved failed source is data; archive exceptions must be exact and sealed."""

import unittest
from pathlib import Path

from asof.serde import ContractError
from tools import validate


ARCHIVE = "planning/review-assets/recovery-step9-native-recognition-20261028/check_recognition_module_policy_v1_before_syntax.py"


class ArchivedSyntaxGateTests(unittest.TestCase):
    def setUp(self):
        self.raw = (Path(__file__).resolve().parents[1] / ARCHIVE).read_bytes()

    def test_exact_failed_original_is_classified_as_nonexecutable_archive(self):
        self.assertEqual(validate.validate_python_artifact(ARCHIVE, self.raw), "archived_invalid_source")

    def test_changed_archive_is_not_silently_exempted(self):
        for raw in (self.raw + b"\n", b"pass\n"):
            with self.subTest(raw_size=len(raw)), self.assertRaises(ContractError):
                validate.validate_python_artifact(ARCHIVE, raw)

    def test_same_name_heuristic_or_same_bytes_at_another_path_is_not_exempt(self):
        for path in ("other_before_syntax.py", "src/asof/" + Path(ARCHIVE).name):
            with self.subTest(path=path), self.assertRaises(SyntaxError):
                validate.validate_python_artifact(path, self.raw)

    def test_active_source_must_parse_and_preserved_fixed_counterpart_parses(self):
        self.assertEqual(validate.validate_python_artifact("src/fictional.py", b"value = 1\n"), "active_python")
        with self.assertRaises(SyntaxError):
            validate.validate_python_artifact("src/fictional.py", b"value = r'broken\\'\n")
        corrected = ARCHIVE.replace("_before_syntax.py", ".py")
        raw = (Path(__file__).resolve().parents[1] / corrected).read_bytes()
        self.assertEqual(validate.validate_python_artifact(corrected, raw), "active_python")
