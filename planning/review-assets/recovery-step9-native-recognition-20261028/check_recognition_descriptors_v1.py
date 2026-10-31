"""Metadata/header binding checks. Never touch any described CPU/GGUF/pack file."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
DESC = HERE / "RECOGNITION-RUNTIME-PIN-DESCRIPTOR-v1.json"
HEADER = HERE / "recognition_runtime_pins_v1.hpp"
CONTRACT = HERE / "RECOGNITION-EXECUTION-CONTRACT-v1.json"
DATA = json.loads(DESC.read_bytes())
TEXT = HEADER.read_text(encoding="utf-8")
EXPECTED = json.loads(CONTRACT.read_bytes())
PROOF = HERE / "RECOGNITION-DESCRIPTOR-PURE-PROOF-v1.json"


def validate(data, text):
    if data["observed_version"] != EXPECTED["observed_version"] or data["observed_version"] != "0.7.0-dev":
        raise ValueError("Accepted version binding")
    if data["module_policy_sha256"] != EXPECTED["module_policy_sha256"]:
        raise ValueError("Recognition phase binding")
    entries = re.findall(r'\{L"((?:[^"\\]|\\.)*)", "([0-9a-f]{64})", ([0-9]+)ull\}', text)
    parsed = [dict(path=json.loads('"' + path + '"'), sha256=sha, bytes=int(size)) for path, sha, size in entries]
    if parsed[-3:] != EXPECTED["ordered_shard_descriptors"]:
        raise ValueError("Exact ordered three descriptors")
    described = [dict(path=row["path_or_name"], bytes=row["bytes"], sha256=row["sha256"]) for row in data["ordered_shard_descriptors"]]
    if described != EXPECTED["ordered_shard_descriptors"]:
        raise ValueError("Descriptor order/identity")
    cpu = next(row for row in parsed if row["path"] == "ggml-cpu-x64.dll")
    expected_cpu = EXPECTED["CPU_descriptor"]
    if cpu["bytes"] != expected_cpu["bytes"] or cpu["sha256"] != expected_cpu["sha256"]:
        raise ValueError("CPU metadata identity")
    if data["CPU_descriptor"]["bytes"] != cpu["bytes"] or data["CPU_descriptor"]["sha256"] != cpu["sha256"]:
        raise ValueError("CPU descriptor differs")
    if data["pack"]["sha256"] != "f75ab9937c57b5f03c2234643a8a9c91cda852ca0cca0de0478369f793e57e5f" or data["pack"]["bytes"] != 259867:
        raise ValueError("Frozen pack descriptor")
    if next(row for row in parsed if row["path"] == data["pack"]["path"]) != data["pack"]:
        raise ValueError("Header pack binding")
    if not all(value is False for value in data["authority"].values()) or any(data["activity"].values()):
        raise ValueError("Metadata is not execution/identity revalidation")
    if data["cooperative_work_ms"] != 117000 or 'R09_COOPERATIVE_WORK_MS = 117000ull' not in text:
        raise ValueError("Work clock changed")
    if 'R09_EXPECTED_LLAMA_VERSION[] = "0.7.0-dev"' not in text or 'R09_RECOGNITION_ENABLED = true' not in text:
        raise ValueError("Prospective header differs")
    return True


class Cases(unittest.TestCase):
    def test_valid_descriptor_without_filesystem_calls(self):
        with patch("builtins.open", side_effect=AssertionError("No payload opens")), \
             patch.object(io, "open", side_effect=AssertionError("No payload opens")), \
             patch.object(Path, "stat", side_effect=AssertionError("No payload stats")):
            self.assertTrue(validate(DATA, TEXT))

    def test_wrong_version_policy_and_authority_rejected(self):
        for field, value in (("observed_version", "newer"), ("module_policy_sha256", "0" * 64), ("cooperative_work_ms", 120000)):
            data = deepcopy(DATA); data[field] = value
            with self.assertRaises(ValueError): validate(data, TEXT)
        data = deepcopy(DATA); data["authority"]["payload_access"] = True
        with self.assertRaises(ValueError): validate(data, TEXT)

    def test_order_hash_size_and_count_are_not_substitutable(self):
        for mutate in (lambda rows: rows.reverse(), lambda rows: rows.pop(),
                       lambda rows: rows[0].update(sha256="0" * 64), lambda rows: rows[0].update(bytes=1)):
            data = deepcopy(DATA); mutate(data["ordered_shard_descriptors"])
            with self.assertRaises(ValueError): validate(data, TEXT)

    def test_header_identity_not_just_descriptor_claims(self):
        for old, new in (("d402f7ff", "00000000"), ("a09ea5e7", "00000000"), ('"0.7.0-dev"', '"0.8.0"')):
            with self.assertRaises(ValueError): validate(DATA, TEXT.replace(old, new))

    def test_original_ABI_header_remains_unchanged_disabled(self):
        original = Path(DATA["basis_header"]["path"])
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), DATA["basis_header"]["sha256"])
        self.assertIn("R09_RECOGNITION_ENABLED = false", original.read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(HEADER.read_bytes()).hexdigest(), DATA["header"]["sha256"])


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    proof = dict(schema_version=1, status="passed" if result.wasSuccessful() else "failed", tests=result.testsRun,
                 failures=[str(x) for x in result.failures], errors=[str(x) for x in result.errors],
                 checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 descriptor_sha256=hashlib.sha256(DESC.read_bytes()).hexdigest(), header_sha256=hashlib.sha256(HEADER.read_bytes()).hexdigest(),
                 contract_sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
                 CPU_GGUF_pack_payload_stat_open_hash=0, compiler_calls=0, SDK_constructors=0, children=0,
                 scope="Exact metadata-only bindings and in-memory negatives; no asset identity freshness or execution permission")
    with PROOF.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(proof, output, indent=2)
        output.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
