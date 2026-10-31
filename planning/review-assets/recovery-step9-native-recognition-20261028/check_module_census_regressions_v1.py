"""Regression-first static/dataflow probes; no C++ or Win32 execution."""
from pathlib import Path
import hashlib
import json
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "typed_public_c_recognizer_v6.cpp"
PROOF = HERE / "SELF-MODULE-CENSUS-REGRESSIONS-BEFORE-v1.json"


class Regressions(unittest.TestCase):
    def test_successful_first_and_next_count_before_publication(self):
        source = SOURCE.read_text()
        for api, end in (("BOOL found = Module32FirstW", "reason = found ?"),
                         ("found = Module32NextW", "if (!found)")):
            block = source[source.index(api):]
            block = block[:block.index(end)]
            self.assertIn("if (found) ++seen;", block)
            self.assertLess(block.index("if (found) ++seen;"), block.index("result("))
        self.assertNotIn("++seen; if (rows.size()", source)

    def test_comparison_requires_lossless_retained_inputs(self):
        source = SOURCE.read_text()
        begin = source.index("bool comparable =")
        block = source[begin:source.index("const char* category", begin)]
        for required in ("row.name_terminated", "row.name.size() <= MODULE_DIAGNOSTIC_NAME_UNITS",
                         "row.path.size() <= MODULE_DIAGNOSTIC_PATH_UNITS", "system_complete"):
            self.assertIn(required, block)
        self.assertIn('comparable ? json_bool(basename_match) : "null"', source)
        self.assertIn('comparable ? json_bool(system_match) : "null"', source)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Regressions))
    proof = dict(status="passed" if result.wasSuccessful() else "failed_expected_regression_first",
                 source=str(SOURCE), source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                 checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 tests_run=result.testsRun, failures=[str(item) for item in result.failures],
                 errors=[str(item) for item in result.errors], actual_children=0,
                 scope="Static source ordering/retained-input regression; not compiled native execution")
    with PROOF.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(proof, output, indent=2)
        output.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
