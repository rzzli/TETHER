"""Fictional SciFact projection/privacy/path failures; no production answers."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, parse_json
from tether_engine.journal import read_chain
from experiments.scifact.data_views import (load_archive, projected_products, prepare_release,
                                            verify_preparation, load_product, digest, jsonl_bytes)


def fixture_rows():
    corpus = [{"doc_id": i, "title": f"Document {i}", "abstract": [f"Sentence {i} a", f"Sentence {i} b"], "structured": False}
              for i in range(1, 43)]
    train = [{"id": i, "claim": f"Claim {i}", "evidence": {str(i): [{"label": "SUPPORT" if i % 2 else "CONTRADICT", "sentences": [0]}]}, "cited_doc_ids": [i]}
             for i in range(1, 31)]
    dev = [{"id": 100, "claim": "Development statement", "evidence": {}, "cited_doc_ids": [40]}]
    test = [{"id": 200, "claim": "Unlabelled test statement"}]
    return corpus, train, dev, test


def write_tar(path, rows=None, extras=(), replacements=None):
    rows = rows or fixture_rows()
    names = ["data/corpus.jsonl", "data/claims_train.jsonl", "data/claims_dev.jsonl", "data/claims_test.jsonl"]
    contents = {name: jsonl_bytes(value) for name, value in zip(names, rows)}
    contents.update(replacements or {})
    with tarfile.open(path, "w:gz") as archive:
        for name, raw in contents.items():
            member = tarfile.TarInfo(name); member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
        for member, raw in extras:
            archive.addfile(member, io.BytesIO(raw) if raw is not None else None)
    return path


def acquisition(root, archive):
    raw = archive.read_bytes()
    receipt = archive.with_suffix(".receipt.json")
    data = {"status": "downloaded_not_parsed", "sha256": digest(raw), "bytes": len(raw), "path": str(archive.resolve()),
            "url": "https://example.invalid/public.tar.gz", "finished_at_utc": "2026-01-02T00:00:00+00:00"}
    receipt.write_bytes(canonical(data)+b"\n")
    record = root / "acquisition.json"
    # Acquisition lookup deliberately uses the official basename, so use that name in fixtures.
    record.write_bytes(canonical({"originals": [{"file": str(archive.resolve()), "bytes": len(raw), "sha256": digest(raw),
                     "receipt_file": str(receipt.resolve()), "receipt_sha256": digest(receipt.read_bytes()), "source_url": data["url"]}]}))
    return record


class DataViewsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "scifact-data.tar.gz"

    def load(self, rows=None, extras=(), replacements=None):
        write_tar(self.archive, rows, extras, replacements)
        return load_archive(self.archive, digest(self.archive.read_bytes()))

    def test_valid_projection_retains_text_and_indices_but_no_reference_fields(self):
        loaded = self.load()
        products, split = projected_products(loaded)
        corpus = [parse_json(line) for line in products["corpus"]["bytes_value"].splitlines()]
        queries = [parse_json(line) for line in products["queries_dev"]["bytes_value"].splitlines()]
        self.assertEqual(set(corpus[0]), {"doc_id", "title", "abstract"})
        self.assertEqual(set(queries[0]), {"id", "claim"})
        self.assertEqual(loaded.bindings["corpus"]["1"]["line_1based"], 1)
        self.assertEqual(loaded.schema_exclusions["corpus"]["structured"], 42)
        self.assertEqual(split["counts"]["dev"], 1)

    def test_label_and_citation_mutations_leave_public_dev_view_unchanged(self):
        before, _ = projected_products(self.load())
        rows = copy.deepcopy(fixture_rows())
        rows[2][0]["evidence"] = {"41": [{"label": "CONTRADICT", "sentences": [1]}]}
        rows[2][0]["cited_doc_ids"] = [41]
        after, _ = projected_products(self.load(rows))
        for key in ("corpus", "queries_dev"):
            self.assertEqual(before[key]["bytes_value"], after[key]["bytes_value"])
        self.assertNotEqual(before["references_dev"]["bytes_value"], after["references_dev"]["bytes_value"])

    def test_claim_and_source_changes_alter_only_appropriate_public_products(self):
        before, _ = projected_products(self.load())
        rows = copy.deepcopy(fixture_rows()); rows[2][0]["claim"] = "Changed query"
        after, _ = projected_products(self.load(rows))
        self.assertNotEqual(before["queries_dev"]["bytes_value"], after["queries_dev"]["bytes_value"])
        self.assertEqual(before["corpus"]["bytes_value"], after["corpus"]["bytes_value"])
        rows[0][0]["abstract"][1] = "Changed original sentence"
        after2, _ = projected_products(self.load(rows))
        self.assertNotEqual(after["corpus"]["bytes_value"], after2["corpus"]["bytes_value"])

    def test_nested_loaded_mappings_are_immutable(self):
        loaded = self.load()
        with self.assertRaises(TypeError): loaded.claims["dev"][0]["claim"] = "changed"
        with self.assertRaises(TypeError): loaded.corpus[1]["abstract"][0] = "changed"

    def test_repeated_cited_document_preserved_and_reported(self):
        rows=copy.deepcopy(fixture_rows()); rows[2][0]["cited_doc_ids"]=[40,40]
        loaded=self.load(rows); products,_=projected_products(loaded)
        self.assertEqual(loaded.claims["dev"][0]["cited_doc_ids"],(40,40))
        self.assertEqual(loaded.diagnostics[0]["kind"],"duplicate_cited_document_preserved")
        reference=parse_json(products["references_dev"]["bytes_value"].splitlines()[0])
        self.assertEqual(reference["cited_doc_ids"],[40,40])

    def test_unknown_fields_are_enumerated_and_excluded(self):
        rows = copy.deepcopy(fixture_rows()); rows[2][0]["secret_answer"] = "SENTINEL"
        loaded = self.load(rows); products, _ = projected_products(loaded)
        self.assertEqual(loaded.schema_exclusions["claims"]["dev"]["secret_answer"], 1)
        self.assertNotIn(b"SENTINEL", products["queries_dev"]["bytes_value"])

    def test_archive_hash_and_length_fail(self):
        self.load()
        with self.assertRaises(ContractError): load_archive(self.archive, "0"*64)
        with self.assertRaises(ContractError): load_archive(self.archive, digest(self.archive.read_bytes()), 1)

    def test_traversal_absolute_windows_and_unknown_member_rejected(self):
        for name in ("../escape", "/abs", "C:/escape", "data\\escape", "data/unapproved.jsonl"):
            with self.subTest(name=name):
                member=tarfile.TarInfo(name); member.size=1
                with self.assertRaises(ContractError): self.load(extras=[(member,b"x")])

    def test_duplicate_and_link_members_rejected(self):
        member=tarfile.TarInfo("data/corpus.jsonl"); member.size=1
        with self.assertRaises(ContractError): self.load(extras=[(member,b"x")])
        member=tarfile.TarInfo("data/cross_validation/fold_1/claims_train_1.jsonl")
        member.type=tarfile.SYMTYPE; member.linkname="../../other"
        with self.assertRaises(ContractError): self.load(extras=[(member,None)])

    def test_expanded_size_limit_rejects_without_extracting(self):
        write_tar(self.archive)
        with patch("experiments.scifact.data_views.MAX_EXPANDED", 3):
            with self.assertRaises(ContractError): load_archive(self.archive,digest(self.archive.read_bytes()))

    def test_duplicate_json_keys_nonfinite_and_blank_rows_rejected(self):
        for payload in (b'{"id":100,"id":101,"claim":"x"}\n', b'{"id":NaN}\n', b'\n'):
            with self.subTest(payload=payload):
                with self.assertRaises(ContractError): self.load(replacements={"data/claims_dev.jsonl":payload})

    def test_duplicate_native_ids_and_boolean_ids_rejected(self):
        rows=copy.deepcopy(fixture_rows()); rows[2][0]["id"]=rows[1][0]["id"]
        with self.assertRaises(ContractError): self.load(rows)
        rows=copy.deepcopy(fixture_rows()); rows[0][0]["doc_id"]=True
        with self.assertRaises(ContractError): self.load(rows)

    def test_unknown_doc_invalid_sentence_and_conflicting_or_overlapping_rationale_rejected(self):
        cases=[{"99999":[{"label":"SUPPORT","sentences":[0]}]},
               {"1":[{"label":"SUPPORT","sentences":[2]}]},
               {"1":[{"label":"SUPPORT","sentences":[0]},{"label":"CONTRADICT","sentences":[1]}]},
               {"1":[{"label":"SUPPORT","sentences":[0]},{"label":"SUPPORT","sentences":[0,1]}]}]
        for evidence in cases:
            with self.subTest(evidence=evidence):
                rows=copy.deepcopy(fixture_rows()); rows[1][0]["evidence"]=evidence
                with self.assertRaises(ContractError): self.load(rows)

    def test_full_prepare_reconstruct_and_purpose_controls(self):
        self.load(); source=acquisition(self.root,self.archive); output=self.root/"prepared"
        report=prepare_release(source,output)
        manifest=verify_preparation(output,report["manifest_sha256"])
        self.assertEqual(load_product(output,manifest,"queries_dev","predict")[0]["id"],100)
        with self.assertRaises(ContractError): load_product(output,manifest,"references_dev","predict")
        with self.assertRaises(ContractError): load_product(output,manifest,"fit_pairs","predict")
        self.assertFalse(report["native_scoring"])

    def test_reanchored_permission_laundering_fails_reprojection(self):
        self.load(); source=acquisition(self.root,self.archive); output=self.root/"prepared"
        report=prepare_release(source,output)
        path=output/"manifest.json"; manifest=parse_json(path.read_bytes())
        manifest["products"]["references_dev"]["purposes"].append("predict")
        path.write_bytes(canonical(manifest)+b"\n")
        with self.assertRaisesRegex(ContractError,"authority mismatch"):
            verify_preparation(output,digest(path.read_bytes()))

    def test_source_change_and_receipt_change_fail(self):
        self.load(); source=acquisition(self.root,self.archive); output=self.root/"prepared"
        report=prepare_release(source,output)
        self.archive.write_bytes(self.archive.read_bytes()+b"altered")
        with self.assertRaises(ContractError): verify_preparation(output,report["manifest_sha256"])

    def test_caller_cannot_grant_extra_product_purpose(self):
        self.load(); source=acquisition(self.root,self.archive); output=self.root/"prepared"
        report=prepare_release(source,output)
        manifest=parse_json((output/"manifest.json").read_bytes())
        manifest["products"]["references_dev"]["purposes"].append("predict")
        with self.assertRaisesRegex(ContractError,"Consumer manifest"):
            load_product(output,manifest,"references_dev","predict")

    def test_omitted_projector_proof_rejected_even_with_new_anchor(self):
        self.load(); source=acquisition(self.root,self.archive); output=self.root/"prepared"
        prepare_release(source,output)
        path=output/"manifest.json"; manifest=parse_json(path.read_bytes())
        manifest["source_pins"]={}
        path.write_bytes(canonical(manifest)+b"\n")
        with self.assertRaisesRegex(ContractError,"code proof"):
            verify_preparation(output,digest(path.read_bytes()))

    def test_report_feasibility_and_terminal_accounting_must_reconcile(self):
        self.load(); source=acquisition(self.root,self.archive); output=self.root/"prepared"
        report=prepare_release(source,output)
        path=output/"build-report.json"; original=parse_json(path.read_bytes())
        for field,value in (("pair_label_counts",{}),("split_counts",{}),("diagnostics",["invented"]),("native_scoring",True),("elapsed_seconds",-1)):
            altered=copy.deepcopy(original); altered[field]=value; path.write_bytes(canonical(altered)+b"\n")
            with self.subTest(field=field),self.assertRaises(ContractError):
                verify_preparation(output,report["manifest_sha256"])
        path.write_bytes(canonical(original)+b"\n")

    def test_interruption_retains_terminal_journal(self):
        self.load(); source=acquisition(self.root,self.archive); output=self.root/"interrupted"
        with patch("experiments.scifact.data_views.load_archive",side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): prepare_release(source,output)
        self.assertEqual(read_chain(output/"journal.jsonl")[-1]["event"],"build_interrupted")

    def test_collision_preserves_first_attempt(self):
        self.load(); source=acquisition(self.root,self.archive); output=self.root/"prepared"
        prepare_release(source,output); before=(output/"manifest.json").read_bytes()
        with self.assertRaises(FileExistsError): prepare_release(source,output)
        self.assertEqual(before,(output/"manifest.json").read_bytes())

    def test_write_failure_retains_terminal_journal(self):
        self.load(); source=acquisition(self.root,self.archive); output=self.root/"failed"
        with patch("experiments.scifact.data_views.publish_bytes",side_effect=OSError("injected write failure")):
            with self.assertRaises(OSError): prepare_release(source,output)
        events=read_chain(output/"journal.jsonl")
        self.assertEqual(events[-1]["event"],"build_failed")
        self.assertEqual(events[-1]["details"]["stage"],"projection_and_split")

    def test_apple_metadata_ignored_without_becoming_product(self):
        member=tarfile.TarInfo("._data"); member.size=3
        loaded=self.load(extras=[(member,b"abc")])
        self.assertEqual(loaded.inventory[-1]["disposition"],"apple_metadata")
        self.assertNotIn("._data",loaded.members)


if __name__ == "__main__": unittest.main()
