"""Self-contained invented Parquet inputs shared by ingestion tests.

This fixture is not a TestCase and contains no executed test methods. Biology,
receipts and labels are fictional; no provider originals are read.
"""
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from tether_engine.ingest import PILOT, InputFile, InputManifest, build_snapshot
from tether_engine.serde import sha256_file, write_json

GENES = {"CD276": "ENSG00000103855", "OSMR": "ENSG00000145623", "ERBB2": "ENSG00000141736",
         "PCSK9": "ENSG00000169174", "IL6R": "ENSG00000160712", "CFTR": "ENSG00000001626",
         "GLP1R": "ENSG00000112164", "SCN9A": "ENSG00000169432"}


class IngestFixture:
    def setUp(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        self.pa, self.pq = pa, pq
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw"
        self.raw.mkdir()
        self.catalog = self.root / "catalog.json"
        write_json(self.catalog, {"schema_version": 1, "datasets": [
            {"dataset_id": key, "roles": ["reference"] if key == "hgnc_symbols" else ["agent_evidence"]}
            for key in ("ot_target", "ot_disease", "ot_evidence", "hgnc_symbols", "tether_normalized_packets")]})
        target = [{"id": value, "approvedSymbol": key, "approvedName": "Fictional fixture", "biotype": "protein_coding"}
                  for key, value in GENES.items()]
        disease = [{"id": key, "name": "Fictional disease label " + key} for key in sorted({row[1] for row in PILOT})]
        self.pq.write_table(self.pa.Table.from_pylist(target), self.raw / "target.parquet")
        self.pq.write_table(self.pa.Table.from_pylist(disease), self.raw / "disease.parquet")
        self.rows = [{"id": f"fictional-{i}", "targetId": GENES[symbol], "diseaseId": disease,
                      "datasourceId": "eva", "datatypeId": "genetic_association", "score": 0.25 + i / 100,
                      "studyId": None, "cohortId": None, "ancestry": None, "cellType": None,
                      "publicationYear": None,
                      "clinicalStatus": "FORBIDDEN_OUTCOME_CONTENT", "studyStopReason": "FORBIDDEN_SAFETY_LABEL"}
                     for i, (symbol, disease, action, modality) in enumerate(PILOT)]
        self.pq.write_table(self.pa.Table.from_pylist(self.rows), self.raw / "evidence.parquet")
        with (self.raw / "hgnc.tsv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["hgnc_id", "symbol", "status", "ensembl_gene_id"], delimiter="\t")
            writer.writeheader()
            for i, (symbol, gene_id) in enumerate(GENES.items()):
                writer.writerow({"hgnc_id": f"HGNC:fictional-{i}", "symbol": symbol, "status": "Approved", "ensembl_gene_id": gene_id})
        self.manifest = self.root / "inputs.json"
        self.entries = [InputFile(dataset, release, filename, filename + ".receipt.json") for dataset, release, filename in (
            ("ot_target", "25.09", "target.parquet"), ("ot_disease", "25.09", "disease.parquet"),
            ("ot_evidence", "25.09", "evidence.parquet"), ("hgnc_symbols", "snapshot_2026-10-10", "hgnc.tsv"))]
        for entry in self.entries:
            self.receipt(entry)
        self.save_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def save_manifest(self, expected=None):
        write_json(self.manifest, InputManifest(2, str(self.raw), tuple(self.entries), expected or {
            entry.dataset_id: 1 for entry in self.entries}))

    def receipt(self, entry):
        path = self.raw / entry.relative_path
        write_json(self.raw / entry.receipt_path, {"status": "completed", "dataset_id": entry.dataset_id,
                   "release_id": entry.release_id, "relative_path": entry.relative_path,
                   "sha256": sha256_file(path), "bytes": path.stat().st_size,
                   "url": "https://ftp.ebi.ac.uk/fictional-fixture/" + path.name,
                   "completed_at_utc": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                   "fixture": "Invented format/contract test; not a real provider acquisition"})

    def evidence(self, rows):
        self.pq.write_table(self.pa.Table.from_pylist(rows), self.raw / "evidence.parquet")
        self.receipt(self.entries[2])

    def build(self):
        output = self.root / "snapshot"
        report = build_snapshot(self.manifest, self.catalog, output)
        return output, report

