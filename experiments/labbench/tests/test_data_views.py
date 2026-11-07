from pathlib import Path
import hashlib
import json
import random
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

from tether_engine.serde import ContractError, canonical, fingerprint
from experiments.labbench import data_views as views


def fictional_rows():
    return [{"id": str(UUID(int=i+1)), "question": f"Fictional query {i}: which flower glows?",
             "ideal": f"blue flower {i}", "distractors": ["green flower", "red flower"],
             "canary": "fixture-only", "tag": "fictional", "version": "v1", "sources": ["https://example.invalid/hidden"],
             "key-passage": "hidden answer passage", "is_opensource": True} for i in range(2)]


def original_fixture(root):
    root.mkdir()
    target = root / views.ORIGINAL
    target.parent.mkdir(parents=True)
    body = b"".join(canonical(row)+b"\n" for row in fictional_rows())
    target.write_bytes(body)
    receipt = {"schema_version": 1, "files": [{"path": views.ORIGINAL, "status": 200,
                "bytes": len(body), "sha256": views.digest(body)}], "github_revision": "fictional", "hf_revision": "fictional"}
    payload = canonical(receipt)+b"\n"
    (root/"ACQUISITION.json").write_bytes(payload)
    return views.digest(payload)


class ProjectionTests(unittest.TestCase):
    def test_native_shuffle_reference_and_hidden_fields(self):
        rows = fictional_rows()
        result = views.project_rows(b"\n".join(canonical(x) for x in rows), expected_count=2)
        rng = random.Random(views.SEED)
        for row, query, ref in zip(rows, result["queries"], result["references"]):
            values = [row["ideal"], views.REFUSE_CHOICE, *row["distractors"]]
            perm = list(range(len(values))); rng.shuffle(perm)
            self.assertEqual(list(query["choices"]), [f"({chr(65+i)}) {values[p]}" for i,p in enumerate(perm)])
            self.assertEqual(ref["answer_index"], perm.index(0))
            self.assertEqual(ref["unsure_index"], perm.index(1))
            self.assertEqual(set(query), {"id", "question", "choices"})
        self.assertEqual(result["diagnostics"]["field_presence"]["id"], 2)
        self.assertEqual(result["diagnostics"]["field_presence"]["sources"], 2)
        with self.assertRaises(TypeError): result["queries"][0]["choices"][0] = "mutated"

    def test_schema_duplicates_and_count_fail_closed(self):
        for mutate in (lambda rows: rows[0].update(extra="hidden"), lambda rows: rows[1].update(id=rows[0]["id"]),
                       lambda rows: rows[0].update(distractors=[rows[0]["ideal"]]),
                       lambda rows: rows[0].update(id=True)):
            rows = fictional_rows(); mutate(rows)
            with self.assertRaises(ContractError): views.project_rows(b"\n".join(canonical(x) for x in rows),expected_count=2)
        with self.assertRaises(ContractError): views.project_rows(canonical(fictional_rows()[0]),expected_count=2)
        with self.assertRaises(ContractError): views.project_rows(b'{"id":1,"id":2}',expected_count=1)

    def test_native_duplicate_distractors_keep_all_indexed_options(self):
        rows=fictional_rows();rows[0]["distractors"]=["same wrong text","same wrong text"]
        result=views.project_rows(b"\n".join(canonical(row) for row in rows),expected_count=2)
        query=result["queries"][0]
        self.assertEqual(len(query["choices"]),4)
        self.assertEqual(sum(choice[4:]=="same wrong text" for choice in query["choices"]),2)
        self.assertEqual(result["diagnostics"]["duplicate_distractor_text_rows"],1)
        ref=result["references"][0]
        self.assertEqual(query["choices"][ref["answer_index"]][4:],rows[0]["ideal"])

    def test_sealed_preparation_rechecks_parents_and_purposes(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp); sha=original_fixture(base/"original")
            manifest=views.prepare_views(base/"original",base/"out",expected_receipt_sha256=sha,expected_count=2)
            digest=views.digest((base/"out/manifest.json").read_bytes())
            self.assertEqual(views.verify_views(base/"out",digest),manifest)
            queries=views.load_queries(base/"out/queries.json",manifest["products"]["queries"]["sha256"])
            self.assertEqual(len(queries),2)
            with self.assertRaises(FileExistsError): views.prepare_views(base/"original",base/"out",expected_receipt_sha256=sha,expected_count=2)
            (base/"original"/views.ORIGINAL).write_text("changed")
            with self.assertRaises(ContractError): views.verify_views(base/"out",digest)

    def test_consumed_bytes_are_the_verified_capture(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp); sha=original_fixture(base/"original")
            original_verify=views.verify_originals
            def raced(*args,**kwargs):
                verified=original_verify(*args,**kwargs)
                rows=fictional_rows(); rows[0]["question"]="SUBSTITUTED AFTER VERIFICATION"
                (base/"original"/views.ORIGINAL).write_bytes(b"\n".join(canonical(x) for x in rows))
                return verified
            with patch.object(views,"verify_originals",side_effect=raced):
                views.prepare_views(base/"original",base/"out",expected_receipt_sha256=sha,expected_count=2)
            queries=json.loads((base/"out/queries.json").read_bytes())
            self.assertEqual(queries[0]["question"],fictional_rows()[0]["question"])

    def test_failure_is_retained_without_restarting(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp); sha=original_fixture(base/"original")
            with self.assertRaises(ContractError): views.prepare_views(base/"original",base/"failed",expected_receipt_sha256="0"*64,expected_count=2)
            self.assertTrue((base/"failed/FAILED.json").is_file())
            self.assertIn('build_failed',(base/"failed/journal.jsonl").read_text())
            self.assertFalse((base/"failed/COMPLETE.json").exists())

    def test_resealed_revision_contradiction_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp); sha=original_fixture(base/"original")
            views.prepare_views(base/"original",base/"out",expected_receipt_sha256=sha,expected_count=2)
            root=base/"out"; manifest=json.loads((root/"manifest.json").read_bytes())
            manifest["github_revision"]="different_revision"
            raw=canonical(manifest)+b"\n"; digest=views.digest(raw)
            (root/"manifest.json").write_bytes(raw)
            events=[json.loads(line) for line in (root/"journal.jsonl").read_bytes().splitlines()]
            events[-1]["details"]["manifest_sha256"]=digest
            events[-1].pop("sha256");events[-1]["sha256"]=fingerprint(events[-1])
            journal=b"".join(canonical(event)+b"\n" for event in events)
            (root/"journal.jsonl").write_bytes(journal)
            (root/"COMPLETE.json").write_bytes(canonical({"manifest_sha256":digest,"journal_sha256":views.digest(journal)})+b"\n")
            with self.assertRaises(ContractError):views.verify_views(root,digest)


if __name__ == "__main__": unittest.main()
