"""Frozen independent goldens plus API/QC/immutability component tests."""
import ast
import copy
import hashlib
import json
import sys
import time
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE = HERE.parent / "recovery-step9-utf8-oracle-20261029/strict_utf8_oracle_v1.py"
PINS = {
    "UNICODE-PIECE-ANALYZER-CONTRACT-v1.json": "05c214f42e9214691b5675cca58e67a6265dd069d2e7829f604df23c7ccca3e6",
    "UNICODE-PIECE-ANALYZER-VECTORS-v1.json": "150a6f0597c226f9aaddcb3f6a3506e9a0513a5cdd2f7da839b25cf56c0f9a79",
    "UNICODE-PIECE-ANALYZER-FREEZE-v1.json": "125d1474ed8498e7dd5bf00f7209fa36660d1326634e0e257b0b2c82f9578a10",
    "UNICODE-CONTROL-CORPUS-v1.json": "13e2c2f2900802729c0d39fa9b7851c56ab3db6afdc45c4b15c2f7f80bd6523c",
}


def pin(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load_source(name, path, expected=None):
    data = path.read_bytes()
    if expected is not None:
        assert hashlib.sha256(data).hexdigest() == expected
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def inputs(vector):
    cases = []
    for original in vector["cases"]:
        case = dict(original)
        case["raw_bytes"] = bytes.fromhex(case.pop("raw_hex"))
        cases.append(case)
    ledgers = tuple(None if item is None else {key: tuple(value) for key, value in item.items()}
                    for item in vector["ledgers"])
    return tuple(cases), ledgers, vector["vocabulary_size"], tuple(vector["eog_ids"])


class Checks(unittest.TestCase):
    def test_independent_frozen_goldens(self):
        for vector in VECTORS["vectors"]:
            with self.subTest(vector=vector["id"]):
                args = inputs(vector)
                if vector["expected_exception"] is not None:
                    with self.assertRaises(ValueError) as caught:
                        API.analyze(*args)
                    if vector["exception_message"] is not None:
                        self.assertEqual(str(caught.exception), vector["exception_message"])
                else:
                    self.assertEqual(API.analyze(*args).to_dict(), vector["expected"])

    def test_nested_immutability_and_serialization(self):
        result = API.analyze(*inputs(VECTORS["vectors"][0]))
        baseline = result.to_dict()
        with self.assertRaises((TypeError, AttributeError)):
            result._data["cases"][0]["counts"][API.CLASSES[0]] = 900
        with self.assertRaises((TypeError, AttributeError)):
            result._data["cases"][0]["matrix"][0][0] = 900
        with self.assertRaises((TypeError, AttributeError)):
            result._data = None
        exported = result.to_dict()
        exported["cases"][0]["boundaries"][0]["classes"].clear()
        exported["known_matrix_lower_bound"][0][0] = 900
        exported["selected_prefixes"].clear()
        self.assertEqual(result.to_dict(), baseline)
        self.assertEqual(json.loads(json.dumps(baseline)), baseline)

    def test_fatal_input_shape_caps_and_types(self):
        args = inputs(VECTORS["vectors"][0])
        altered = [(list(args[0]), *args[1:]), ((), (), 100, (99,)),
                   (args[0], list(args[1]), 100, (99,)),
                   (args[0], args[1][:-1], 100, (99,))]
        for vocab in (True, 0, 262145, 1.0):
            altered.append((args[0], args[1], vocab, (99,)))
        for eogs in ((), [99], (True,), (-1,), (100,), (99, 99), (99, 98)):
            altered.append((args[0], args[1], 100, eogs))
        for update in ({"ordinal": False}, {"ordinal": 9}, {"id": ""},
                       {"id": "\ud800"}, {"id": "x" * 129},
                       {"raw_bytes": b""}, {"raw_bytes": b"x" * 1025},
                       {"raw_bytes": bytearray(b"A")}, {"generation_member": 1},
                       {"observed_membership": True}):
            cases = copy.deepcopy(args[0])
            cases[0].update(update)
            altered.append((cases, *args[1:]))
        for item in altered:
            with self.subTest(shape=repr(item)[:120]), self.assertRaises(ValueError):
                API.analyze(*item)

    def test_bad_ledgers_are_unknown_without_zero_counts(self):
        cases, ledgers, vocab, eogs = inputs(VECTORS["vectors"][0])
        case = (dict(cases[0]),)
        original = ledgers[0]
        bad = [None, 1, {}, {**original, "extra": 1}]
        updates = [
            {"token_ids": [1, 2]}, {"token_ids": (1,)},
            {"token_ids": (True, 2)}, {"token_ids": (-1, 2)},
            {"token_ids": (100, 2)}, {"token_ids": (99, 2)},
            {"piece_byte_lengths": (True, 3)}, {"piece_byte_lengths": (5, 0)},
            {"piece_byte_lengths": (0, 0)}, {"piece_hex": ("41C2", "a242")},
            {"piece_hex": ("4 c2", "a242")}, {"piece_hex": ("4100", "a242")},
        ]
        bad.extend({**original, **update} for update in updates)
        bad.append({"token_ids": (1,) * 49,
                    "piece_byte_lengths": (2, 2) + (0,) * 47,
                    "piece_hex": ("41c2", "a242") + ("",) * 47})
        for ledger in bad:
            with self.subTest(ledger=ledger):
                result = API.analyze(case, (ledger,), vocab, eogs).to_dict()
                self.assertFalse(result["coverage_complete"])
                self.assertIsNone(result["counts"])
                self.assertIsNone(result["selectors"])
                self.assertEqual(result["cases"][0]["qc_status"], "unknown")
                self.assertIsNone(result["cases"][0]["zero_piece_count"])
                self.assertIsNone(result["cases"][0]["boundaries"])

    def test_eligible_invalid_utf8_or_NUL_cannot_pass(self):
        for raw in (b"\0", b"\xc0\xaf", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xe2\x82"):
            case = {"id": "bad", "ordinal": 0, "raw_bytes": raw,
                    "native_byte_eligible": True, "generation_member": True, "semantic_eligible": True}
            ledger = {"token_ids": (1,), "piece_byte_lengths": (len(raw),), "piece_hex": (raw.hex(),)}
            result = API.analyze((case,), (ledger,), 100, (99,)).to_dict()
            self.assertEqual(result["cases"][0]["qc_status"], "unknown")
            self.assertIsNone(result["required_available"])

    def test_no_mutation_or_state_between_calls(self):
        args = inputs(VECTORS["vectors"][0])
        original = copy.deepcopy(args)
        first = API.analyze(*args)
        self.assertEqual(args, original)
        self.assertEqual(API.analyze(*args).to_dict(), first.to_dict())
        before = first.to_dict()
        args[0][0]["generation_member"] = False
        args[1][0]["token_ids"] = (99, 99)
        self.assertEqual(first.to_dict(), before)

    def test_frozen_full_documents_with_synthetic_byte_pieces(self):
        # These are authored one-byte pieces with repeated integer label1, NOT
        # tokenizer observations. They intentionally cannot supply mixed tails.
        corpus = json.loads((HERE / "UNICODE-CONTROL-CORPUS-v1.json").read_bytes())
        cases, ledgers = [], []
        for row in corpus["cases"]:
            expected, raw = row["expected"], bytes.fromhex(row["raw_hex"])
            cases.append({"id": row["id"], "ordinal": row["ordinal"], "raw_bytes": raw,
                          "native_byte_eligible": expected["native_byte_eligible"],
                          "generation_member": expected["generation_grammar_membership"],
                          "semantic_eligible": expected["complete_v3_semantic_validation"]})
            ledgers.append(None if not expected["native_byte_eligible"] else
                           {"token_ids": (1,) * len(raw), "piece_byte_lengths": (1,) * len(raw),
                            "piece_hex": tuple(f"{value:02x}" for value in raw)})
        result = API.analyze(tuple(cases), tuple(ledgers), 100, (99,)).to_dict()
        self.assertTrue(result["coverage_complete"] and result["all_case_QC_complete"])
        self.assertEqual(sum(row["population"] for row in result["cases"]), 68)
        self.assertFalse(result["required_available"])
        self.assertEqual(result["counts"][API.CLASSES[3]], 0)
        self.assertTrue(all(result["counts"][category] > 0 for category in API.CLASSES[:3]))

    def test_source_has_only_declared_pure_dependencies(self):
        tree = ast.parse((HERE / "unicode_piece_analyzer_v1.py").read_bytes())
        modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertEqual(modules, {"bisect", "dataclasses", "types", "strict_utf8_oracle_v1"})
        self.assertFalse(any(isinstance(node, ast.Import) for node in ast.walk(tree)))
        forbidden = {"open", "exec", "eval", "compile", "__import__"}
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                             and node.func.id in forbidden for node in ast.walk(tree)))


def main():
    global API, VECTORS
    started = time.monotonic()
    for name, expected in PINS.items():
        assert pin(HERE / name)["sha256"] == expected, name
    load_source("strict_utf8_oracle_v1", ORACLE,
                "4e5d36afa001339735a349a8ebab88a312cde1cb57fa43336e38ee4195134c21")
    API = load_source("unicode_piece_analyzer_v1", HERE / "unicode_piece_analyzer_v1.py")
    VECTORS = json.loads((HERE / "UNICODE-PIECE-ANALYZER-VECTORS-v1.json").read_bytes())
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    report = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if result.wasSuccessful() else "failed", "methods": result.testsRun,
        "failures": [str(case) + ": " + error for case, error in result.failures],
        "errors": [str(case) + ": " + error for case, error in result.errors],
        "source": pin(HERE / "unicode_piece_analyzer_v1.py"), "checker": pin(Path(__file__)),
        "oracle_dependency": pin(ORACLE), "frozen_pins": PINS,
        "independent_synthetic_scenarios": len(VECTORS["vectors"]),
        "full_frozen_documents_with_synthetic_one_byte_pieces": 84,
        "elapsed_seconds": time.monotonic() - started,
        "scope": "Pure supplied-piece geometry/QC/count/selector tests. Synthetic labels/pieces are not tokenizer or native observations; AST check is not hostile-code isolation.",
        "native_or_tokenizer_calls": 0, "old_profile_or_model_operations": 0,
        "native_row_fit_or_runtime_qualification": False,
    }
    output = HERE / "UNICODE-PIECE-ANALYZER-PURE-PROOF-v1.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "methods": result.testsRun, "sha256": pin(output)["sha256"]}))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
