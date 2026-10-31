"""Independent geometry probes; synthetic labels/pieces, no tokenizer/model I/O."""
import copy
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
ORACLE = HERE.parent / "recovery-step9-utf8-oracle-20261029" / "strict_utf8_oracle_v1.py"


def load(name, path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError("Pinned new engineering source changed")
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader=None))
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


oracle = load("strict_utf8_oracle_v1", ORACLE, "4e5d36afa001339735a349a8ebab88a312cde1cb57fa43336e38ee4195134c21")
a = load("peer_analyzer", HERE / "unicode_piece_analyzer_v1.py", "537a780a3d2d3b95d5fe4976cd8a073cf528db908badf3edf3e861e729ff8f9d")
CATEGORIES = ("pending_width2", "pending_width3", "pending_width4", "same_piece_complete_scalar_then_pending")


def case(raw, ordinal=0, **flags):
    return dict(id="synthetic-" + str(ordinal), ordinal=ordinal, raw_bytes=raw,
                native_byte_eligible=flags.get("native_byte_eligible", True),
                generation_member=flags.get("generation_member", True),
                semantic_eligible=flags.get("semantic_eligible", True))


def ledger(raw, lengths):
    at, spellings = 0, []
    for length in lengths:
        spellings.append(raw[at:at + length].hex()); at += length
    assert at == len(raw)
    return dict(token_ids=tuple(1 + i % 80 for i in range(len(lengths))),
                piece_byte_lengths=tuple(lengths), piece_hex=tuple(spellings))


def expected_geometry(widths, lengths):
    """Brute intervals from authored scalar widths, no decoder/bisect/analyzer."""
    intervals, at = [], 0
    for width in widths:
        intervals.append((at, at + width, width)); at += width
    total = at
    counts = dict.fromkeys(CATEGORIES, 0)
    matrix = [[0 for _ in range(3)] for _ in range(4)]
    boundaries, start = [], 0
    for ordinal, length in enumerate(lengths):
        end = start + length
        row = dict(token_ordinal=ordinal, start=start, end=end, pending_start=None,
                   pending_end=None, complete_widths=[], witnesses=[], classes=[])
        pending = [r for r in intervals if length > 0 and end < total and r[0] < end < r[1]]
        if pending:
            left, right, width = pending[0]
            row.update(pending_start=left, pending_end=right)
            row["classes"].append(CATEGORIES[width - 2]); counts[CATEGORIES[width - 2]] += 1
            witnesses = [(u, v, w) for u, v, w in intervals if start <= u < v <= left]
            kinds = sorted(set(w for _, _, w in witnesses))
            if kinds:
                row["classes"].append(CATEGORIES[3]); counts[CATEGORIES[3]] += 1
                row["complete_widths"] = kinds
                for kind in kinds:
                    u, v, _ = min(r for r in witnesses if r[2] == kind)
                    row["witnesses"].append([kind, u, v]); matrix[kind - 1][width - 2] += 1
        boundaries.append(row); start = end
    return boundaries, counts, matrix


class PeerChecks(unittest.TestCase):
    def test_all_fifteen_frozen_literal_vectors(self):
        raw = (HERE / "UNICODE-PIECE-ANALYZER-VECTORS-v1.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "150a6f0597c226f9aaddcb3f6a3506e9a0513a5cdd2f7da839b25cf56c0f9a79")
        vectors = json.loads(raw)["vectors"]; self.assertEqual(len(vectors), 15)
        for vector in vectors:
            with self.subTest(vector=vector["id"]):
                cases = tuple({("raw_bytes" if k == "raw_hex" else k): (bytes.fromhex(v) if k == "raw_hex" else v)
                               for k, v in row.items()} for row in vector["cases"])
                ledgers = tuple(None if row is None else {k: tuple(v) for k, v in row.items()} for row in vector["ledgers"])
                if vector["expected_exception"]:
                    with self.assertRaises(ValueError) as caught:
                        a.analyze(cases, ledgers, vector["vocabulary_size"], tuple(vector["eog_ids"]))
                    if vector["exception_message"] is not None:
                        self.assertEqual(str(caught.exception), vector["exception_message"])
                else:
                    self.assertEqual(a.analyze(cases, ledgers, vector["vocabulary_size"], tuple(vector["eog_ids"])).to_dict(), vector["expected"])

    def test_independent_all_partitions_of_four_authored_scalar_sequences(self):
        documents = (("¢€".encode(), (2, 3)), ("€😀".encode(), (3, 4)),
                     ("A¢¢€".encode(), (1, 2, 2, 3)), ("¢A😀".encode(), (2, 1, 4)))
        tested = 0
        for raw, widths in documents:
            for mask in range(1 << (len(raw) - 1)):
                cuts = [0] + [i for i in range(1, len(raw)) if mask & (1 << (i - 1))] + [len(raw)]
                lengths = [r - l for l, r in zip(cuts, cuts[1:])]
                expected_rows, counts, matrix = expected_geometry(widths, lengths)
                result = a.analyze((case(raw),), (ledger(raw, lengths),), 100, (99,)).to_dict()
                self.assertEqual(result["cases"][0]["boundaries"], expected_rows)
                self.assertEqual(result["counts"], counts)
                self.assertEqual(result["matrix"], matrix)
                tested += 1
        self.assertEqual(tested, 272)

    def test_empty_pieces_keep_witnesses_and_original_selection_ordinals(self):
        raw = "A😀B".encode(); lengths = (0, 0, 2, 0, 3, 1, 0)
        rows, counts, matrix = expected_geometry((1, 4, 1), lengths)
        result = a.analyze((case(raw),), (ledger(raw, lengths),), 100, (99,)).to_dict()
        self.assertEqual(result["cases"][0]["boundaries"], rows)
        self.assertEqual(result["counts"], counts); self.assertEqual(result["matrix"], matrix)
        self.assertEqual(result["cases"][0]["zero_piece_count"], 4)
        self.assertEqual(result["selected_prefixes"], [dict(case_ordinal=0, token_ordinal=2, take_tokens=3,
            byte_cut=2, classes=[CATEGORIES[2], CATEGORIES[3]])])
        self.assertEqual(result["selectors"][CATEGORIES[2]], result["selectors"][CATEGORIES[3]])

    def test_each_matrix_cell_and_class_priority_first_selection(self):
        scalar = {1: b"A", 2: "¢".encode(), 3: "€".encode(), 4: "😀".encode()}
        for complete_width in range(1, 5):
            for pending_width in range(2, 5):
                raw = scalar[complete_width] + scalar[pending_width]
                lengths = (complete_width + 1, pending_width - 1)
                result = a.analyze((case(raw),), (ledger(raw, lengths),), 100, (99,)).to_dict()
                expected = [[0] * 3 for _ in range(4)]; expected[complete_width - 1][pending_width - 2] = 1
                self.assertEqual(result["matrix"], expected)
                self.assertEqual(result["cases"][0]["boundaries"][0]["witnesses"], [[complete_width, 0, complete_width]])
        raw = ("A😀B".encode(), "A€B".encode(), "A¢B".encode())
        cases = tuple(case(body, ordinal) for ordinal, body in enumerate(raw))
        pieces = tuple(ledger(body, (2, len(body) - 2)) for body in raw)
        result = a.analyze(cases, pieces, 100, (99,)).to_dict()
        self.assertEqual([p["case_ordinal"] for p in result["selected_prefixes"]], [2, 1, 0])
        self.assertEqual(result["selectors"], dict(zip(CATEGORIES, (0, 1, 2, 2))))

    def test_unknown_population_suppresses_all_totals_and_selectors(self):
        cases = (case("A¢B".encode(), 0), case("A€B".encode(), 1), case("A😀B".encode(), 2))
        ledgers = (ledger(cases[0]["raw_bytes"], (2, 2)), None, ledger(cases[2]["raw_bytes"], (2, 4)))
        result = a.analyze(cases, ledgers, 100, (99,)).to_dict()
        for key in ("counts", "matrix", "selectors", "selected_prefixes", "required_available"):
            self.assertIsNone(result[key])
        self.assertEqual(result["unknown_population_ordinals"], [1])
        self.assertEqual(result["known_counts_lower_bound"][CATEGORIES[3]], 2)
        self.assertFalse(result["all_case_QC_complete"])

    def test_excluded_qc_unknown_never_becomes_measured_absence_or_profile_pass(self):
        cases = tuple(case(raw, i) for i, raw in enumerate(("A¢B".encode(), "A€B".encode(), "A😀B".encode())))
        cases += (case(b"X", 3, semantic_eligible=False), case(b"\0", 4, native_byte_eligible=False))
        ledgers = tuple(ledger(c["raw_bytes"], (2, len(c["raw_bytes"]) - 2)) for c in cases[:3]) + (None, None)
        result = a.analyze(cases, ledgers, 100, (99,)).to_dict()
        self.assertTrue(result["coverage_complete"]); self.assertTrue(result["required_available"])
        self.assertFalse(result["all_case_QC_complete"])
        self.assertIsNone(result["cases"][3]["counts"])
        self.assertEqual(result["cases"][4]["qc_status"], "harness_ineligible")
        self.assertNotIn("profile_qualified", result)

    def test_input_result_and_serialization_container_immutability(self):
        cases = (case("A¢B".encode()),); ledgers = (ledger(cases[0]["raw_bytes"], (2, 2)),)
        original = copy.deepcopy((cases, ledgers))
        analysis = a.analyze(cases, ledgers, 100, (99,)); expected = analysis.to_dict()
        self.assertEqual((cases, ledgers), original)
        cases[0]["semantic_eligible"] = False
        ledgers[0]["token_ids"] = ()
        self.assertEqual(analysis.to_dict(), expected)
        changed = analysis.to_dict(); changed["cases"][0]["boundaries"][0]["classes"].clear()
        changed["selected_prefixes"][0]["classes"].clear()
        self.assertEqual(analysis.to_dict(), expected)
        with self.assertRaises(TypeError): analysis._data["coverage_complete"] = False
        with self.assertRaises(dataclasses.FrozenInstanceError): analysis._data = {}

    def test_fatal_schema_vs_per_case_unknown_without_normalization(self):
        c = case("¢".encode()); good = ledger(c["raw_bytes"], (1, 1))
        for bad in (dict(c, ordinal=True), dict(c, observed_member=True), dict(c, semantic_eligible=1)):
            with self.assertRaises(ValueError): a.analyze((bad,), (good,), 100, (99,))
        for bad in (dict(good, token_ids=(True, 2)), dict(good, piece_byte_lengths=(1, False)),
                    dict(good, piece_hex=("C2", "a2")), dict(good, piece_byte_lengths=[1, 1])):
            result = a.analyze((c,), (bad,), 100, (99,)).to_dict()
            self.assertEqual(result["cases"][0]["qc_status"], "unknown")
            self.assertIsNone(result["counts"]); self.assertIsNone(result["selectors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
