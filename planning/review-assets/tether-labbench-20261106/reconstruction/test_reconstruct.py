"""Fictional independent-score controls; no actual answer-containing input read."""
import ast
import base64
import copy
import json
from pathlib import Path
import random
import string
import tempfile
import unittest
from unittest.mock import patch

import reconstruct as r

ROOT = Path(__file__).resolve().parents[4]
OFFICIAL = ROOT/"data/raw/labbench_public/20261106-attempt01/github/labbench"


def native_functions():
    """Only two pinned public code functions, no dataset/evaluator imports."""
    assert r.sha((OFFICIAL/"utils.py").read_bytes()) == "b8fad09d2670ea6eac7c709f6f59e66d4d6428d0ad2742da3ddd371a008a455e"
    assert r.sha((OFFICIAL/"evaluator.py").read_bytes()) == "a5e7a308b25ae36eacae7a064b6c3d4b352ddf92071886cae5efcf4d03e5e918"
    utils = ast.parse((OFFICIAL/"utils.py").read_text(encoding="utf-8"))
    evaluator = ast.parse((OFFICIAL/"evaluator.py").read_text(encoding="utf-8"))
    shuffle = next(node for node in utils.body if isinstance(node, ast.FunctionDef) and node.name == "randomize_choices")
    cls = next(node for node in evaluator.body if isinstance(node, ast.ClassDef) and node.name == "Evaluator")
    metrics = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "compute_metrics")
    metrics.decorator_list = []
    namespace = {"random": random.Random(r.SEED), "ALPHABET": string.ascii_uppercase, "REFUSE_CHOICE": r.REFUSAL}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[shuffle, metrics], type_ignores=[])),
                 "<pinned-original-functions>", "exec"), namespace)
    return namespace


def fixtures(n=8):
    native = native_functions()
    originals, queries, keys = [], [], []
    for i in range(n):
        original = {"id": "fictional-"+str(i), "question": "Invented item "+str(i)+"?",
                    "ideal": "null" if i == 0 else "correct-"+str(i), "distractors": ["wrong", "wrong"]}
        choices, correct, unsure = native["randomize_choices"](original["ideal"], original["distractors"])
        originals.append(original)
        queries.append({"id": original["id"], "question": original["question"], "choices": choices})
        keys.append({"id": original["id"], "answer_index": string.ascii_uppercase.index(correct),
                     "unsure_index": string.ascii_uppercase.index(unsure)})
    return originals, queries, keys


def record(query, index=None, checker="not_run", state="produced"):
    return {"id": query["id"], "producer_status": state, "check_status": checker,
            "prediction": {"answer_index": index, "evidence_ids": ["fictional-source"]} if state == "produced" else None,
            "reason": None if checker == "accepted" else "fictional reason"}


def mixed():
    originals, queries, keys = fixtures()
    wrong = next(i for i in range(4) if i not in (keys[2]["answer_index"], keys[2]["unsure_index"]))
    records = [record(queries[0], keys[0]["answer_index"], "accepted"),
               record(queries[1], keys[1]["answer_index"], "rejected"),
               record(queries[2], wrong, "accepted"),
               record(queries[3], keys[3]["unsure_index"], "accepted"),
               record(queries[4], state="parse_failure"), record(queries[5], state="timeout"),
               record(queries[6], state="unexecuted"), record(queries[7], keys[7]["answer_index"], "error")]
    return originals, queries, keys, records


def write(root, name, value):
    path = root/name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True).encode()+b"\n"
    path.write_bytes(raw)
    return {"path": name, "sha256": r.sha(raw), "bytes": len(raw)}


def reseal(root):
    inventory = {}
    for path in root.rglob("*"):
        if path.is_file() and path.name != "SEALED.json":
            raw = path.read_bytes()
            inventory[path.relative_to(root).as_posix()] = {"sha256": r.sha(raw), "bytes": len(raw)}
    manifest_sha = r.sha((root/"manifest.json").read_bytes())
    proof = write(root, "SEALED.json", {"kind": "labbench_generation", "status": "completed",
                  "manifest_sha256": manifest_sha, "outputs": inventory})
    return proof["sha256"]


class ReconstructionTests(unittest.TestCase):
    def test_mapping_matches_pinned_native_and_preserves_duplicates_and_null(self):
        originals, queries, keys = fixtures()
        self.assertEqual(r.reconstruct_keys(originals, queries), keys)
        self.assertEqual(queries[0]["choices"][keys[0]["answer_index"]][4:], "null")
        self.assertNotEqual(keys[0]["answer_index"], keys[0]["unsure_index"])

    def test_permutation_order_and_ideal_collisions_fail(self):
        originals, queries, _ = fixtures()
        changed = copy.deepcopy(queries)
        changed[0]["choices"][0], changed[0]["choices"][1] = changed[0]["choices"][1], changed[0]["choices"][0]
        with self.assertRaisesRegex(ValueError, "permutation"):
            r.reconstruct_keys(originals, changed)
        originals[0]["ideal"] = r.REFUSAL
        with self.assertRaisesRegex(ValueError, "collision"):
            r.reconstruct_keys(originals, queries)

    def test_hand_counts_and_original_metric_parity(self):
        _, queries, keys, records = mixed()
        value = r.calculate(queries, keys, records)
        self.assertEqual(value["raw_metrics"], {"accuracy": 3/8, "precision": 3/4, "coverage": 4/8})
        self.assertEqual(value["checked_metrics"], {"accuracy": 1/8, "precision": 1/2, "coverage": 2/8})
        expected = {"produced": 5, "producer_failures": 3, "accepted": 3, "rejected": 1,
                    "check_errors": 1, "check_not_run": 3, "raw_answered": 4, "checked_answered": 2,
                    "raw_correct": 3, "correct_and_admitted": 1, "correct_but_rejected": 1,
                    "correct_not_admitted": 2, "native_unsure": 1, "accepted_unsure": 1,
                    "incorrect_and_admitted": 2, "incorrect_substantive_and_admitted": 1,
                    "parse_failures": 1, "produced_or_parse_failure": 6}
        self.assertEqual(value["counts"], expected)
        native = native_functions()["compute_metrics"]
        for result, correct, sure in (("raw_metrics", (1, 1, 0, 0, 0, 0, 0, 1), (1, 1, 1, 0, 0, 0, 0, 1)),
                                      ("checked_metrics", (1, 0, 0, 0, 0, 0, 0, 0), (1, 0, 1, 0, 0, 0, 0, 0))):
            self.assertEqual(native([{"correct": bool(c), "sure": bool(s)} for c, s in zip(correct, sure)]),
                             {**value[result], "n_total": 8})

    def test_all_unsure_undefined_precision_and_missing_cases(self):
        _, queries, keys = fixtures()
        records = [record(q, k["unsure_index"], "accepted") for q, k in zip(queries, keys)]
        value = r.calculate(queries, keys, records)
        self.assertFalse(value["raw_precision_defined"])
        self.assertEqual(value["raw_metrics"], {"accuracy": 0.0, "precision": 0.0, "coverage": 0.0})
        self.assertEqual(value["counts"]["accepted_unsure"], 8)
        with self.assertRaisesRegex(ValueError, "Missing"):
            r.calculate(queries, keys, records[:-1])

    def test_strict_json_and_candidate_controls(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            r.parse('{"answer_index":0,"answer_index":1}')
        for bad in ({"answer_index": True, "evidence_ids": []}, {"answer_index": 4, "evidence_ids": []},
                    {"answer_index": 1, "evidence_ids": ["x", "x"]},
                    {"answer_index": 1, "evidence_ids": ["x"]},
                    {"answer_index": 1, "evidence_ids": [], "other": 1}):
            with self.assertRaises(ValueError):
                r.validate_answer(bad, 4, [])

    def test_native_response_requires_exact_original_body(self):
        content = {"answer_index": 2, "evidence_ids": ["fictional-source"]}
        body = json.dumps({"content": json.dumps(content)}).encode()
        wrapper = {"http_status": 200, "complete": True, "error_class": None,
                   "body_base64": base64.b64encode(body).decode(), "body_sha256": r.sha(body)}
        self.assertEqual(r.native_response(wrapper), content)
        wrapper["body_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "body hash"):
            r.native_response(wrapper)

    def test_source_code_has_no_project_imports(self):
        tree = ast.parse(Path(r.__file__).read_text(encoding="utf-8"))
        allowed = {"argparse", "base64", "collections", "datetime", "hashlib", "json", "pathlib", "random", "string", "time"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(n.name in allowed for n in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed)

    def test_dependence_and_analytical_controls_are_not_executed_samples(self):
        originals, queries, _ = fixtures(4)
        originals[0]["sources"] = ["https://example.org/fictional-1"]
        originals[1]["sources"] = ["https://example.org/fictional-1"]
        originals[2]["question"] = originals[1]["question"]
        observed = r.dependence(originals)
        self.assertEqual(observed["observed_component_sizes"], [3, 1])
        self.assertEqual(observed["scheduled_question_count"], 4)
        controls = r.analytical_controls(queries)
        self.assertFalse(controls["executed"])
        self.assertEqual(controls["uniform_all_choices"]["expected_accuracy"], 0.25)
        self.assertEqual(controls["uniform_all_choices"]["expected_coverage"], 0.75)
        self.assertEqual(controls["always_unsure"]["accuracy"], 0.0)

    def test_fictional_sealed_pipeline_and_preseal_reference_exclusion(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data/cache") as directory:
            outer = Path(directory)
            root = outer/"generation"
            root.mkdir()
            originals, queries, keys = fixtures(2)
            records = [record(q, k["answer_index"], "accepted") for q, k in zip(queries, keys)]
            cases = []
            for ordinal, row in enumerate(records):
                prefix = "cases/"+str(ordinal)+"/"
                candidate = row["prediction"]
                body = json.dumps({"content": json.dumps(candidate)}).encode()
                artifacts = {"candidate": write(root, prefix+"candidate.json", candidate),
                    "session_response": write(root, prefix+"response.json", candidate),
                    "sources": write(root, prefix+"sources.json", [{"source_id": "fictional-source"}]),
                    "decision": write(root, prefix+"decision.json", {"accepted": True}),
                    "raw_response": write(root, prefix+"raw.json", {"http_status": 200, "complete": True,
                        "error_class": None, "body_base64": base64.b64encode(body).decode(), "body_sha256": r.sha(body)})}
                cases.append({"ordinal": ordinal, "id": row["id"], "disposition": row, "artifacts": artifacts})
            manifest = {"status": "completed", "schedule": [q["id"] for q in queries],
                "queries": write(root, "queries.json", queries), "dispositions": write(root, "dispositions.json", records),
                "case_index": write(root, "case-index.json", cases)}
            write(root, "manifest.json", manifest)
            sealed = reseal(root)
            original = outer/"original.jsonl"
            original.write_text("\n".join(json.dumps(o) for o in originals), encoding="utf-8")
            reference = outer/"references.json"
            reference.write_text(json.dumps(keys), encoding="utf-8")
            original_sha = r.sha(original.read_bytes())
            result = r.reconstruct(root, sealed, original, original_sha, expected_count=2,
                references_path=reference, references_sha=r.sha(reference.read_bytes()))
            self.assertEqual(result["raw_metrics"]["accuracy"], 1.0)
            self.assertEqual(result["paired_original_candidates"], 2)
            real_read = r.read
            def no_reference(path, *args, **kwargs):
                self.assertNotEqual(Path(path), original, "Opened reference before valid seal")
                return real_read(path, *args, **kwargs)
            with patch.object(r, "read", side_effect=no_reference):
                with self.assertRaisesRegex(ValueError, "hash"):
                    r.reconstruct(root, "0"*64, original, original_sha, expected_count=2)
            changed = copy.deepcopy(records)
            changed[0]["prediction"]["answer_index"] = keys[0]["unsure_index"]
            manifest["dispositions"] = write(root, "dispositions.json", changed)
            cases[0]["disposition"] = changed[0]
            manifest["case_index"] = write(root, "case-index.json", cases)
            write(root, "manifest.json", manifest)
            changed_seal = reseal(root)
            with self.assertRaisesRegex(ValueError, "Candidate/native"):
                r.reconstruct(root, changed_seal, original, original_sha, expected_count=2)


if __name__ == "__main__":
    unittest.main()
