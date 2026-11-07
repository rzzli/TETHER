"""Invented-format regression fixtures for authored contemporary T6 case packs."""
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tether_engine import ingest
from tether_engine.cli import main, parser
from tether_engine.contracts import Case
from tether_engine.ingest import PILOT, _case_definitions, _load_case_pack, build_snapshot
from tether_engine.journal import inspect_run, read_chain
from tether_engine.serde import ContractError, decode, read_json, sha256_file, write_json
from tests import test_v02_ingest as fixtures


def scope(**changes):
    return {"symbol": "CD276", "disease_id": "EFO_0003060", "intended_action": "inhibit",
            "modality": "antibody", "tissue": None, **changes}


def pack(*cases):
    return {"schema_version": 1, "cases": list(cases or (scope(),))}


class CasePackContractTests(unittest.TestCase):
    def test_scopes_distinguish_action_modality_and_explicit_tissue(self):
        definitions = _case_definitions(pack(scope(), scope(intended_action="activate"),
            scope(modality="adc"), scope(tissue="reported lung"),
            scope(intended_action="antigen_directed_cell_killing", modality="car_t")))
        self.assertEqual(len({row.case_id for row in definitions}), 5)
        self.assertEqual(definitions[3].tissue, "reported lung")
        self.assertIsNone(definitions[0].tissue)

    def test_duplicate_scope_or_case_identifier_is_rejected(self):
        for rows in ((scope(case_id="one"), scope(case_id="two")),
                     (scope(case_id="same"), scope(case_id="same", modality="adc"))):
            with self.subTest(rows=rows), self.assertRaisesRegex(ContractError, "Duplicate"):
                _case_definitions(pack(*rows))

    def test_missing_scope_fields_do_not_get_inferred(self):
        for field in scope():
            value = scope()
            del value[field]
            with self.subTest(field=field), self.assertRaises(ContractError):
                _case_definitions(pack(value))

    def test_invalid_ids_values_and_clinical_profiles_are_rejected(self):
        invalid = [scope(symbol="CD276/escape"), scope(disease_id="breast cancer"),
            scope(disease_id=""), scope(intended_action=" Inhibit"), scope(modality="ADC"),
            scope(tissue=""), scope(tissue=False), scope(case_id="../escape"),
            scope(target_id=None), scope(hgnc_id=""), scope(task="T1"),
            scope(profile="historical"), scope(program={"program_id": "not-allowed"}),
            scope(endpoint={"name": "not-allowed"})]
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(ContractError):
                _case_definitions(pack(row))
        for document in ({"schema_version": True, "cases": [scope()]},
                         {"schema_version": 1, "cases": []},
                         {**pack(), "profile": "historical"}):
            with self.subTest(document=document), self.assertRaises(ContractError):
                _case_definitions(document)

    def test_bytes_and_external_anchor_are_checked_without_normalizing_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frozen.json"
            document = {**pack(), "notes": {"authored_context": "preserve Unicode α and newlines"}}
            write_json(path, document)
            definitions, payload, digest = _load_case_pack(path, sha256_file(path))
            self.assertEqual(payload, path.read_bytes())
            self.assertEqual(digest, sha256_file(path))
            self.assertEqual(len(definitions), 1)
            with self.assertRaisesRegex(ContractError, "frozen SHA-256"):
                _load_case_pack(path, "0" * 64)

    def test_cli_explicit_case_pack_is_optional_and_forwarded(self):
        args = ["build-snapshot", "--manifest", "input.json", "--catalog", "catalog.json",
                "--output", "output"]
        self.assertIsNone(parser().parse_args(args).cases)
        with patch("tether_engine.ingest.build_snapshot", return_value={"status": "fixture"}) as build:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(args + ["--cases", "cases.json", "--cases-sha256", "1" * 64]), 0)
        self.assertEqual(build.call_args.kwargs["cases_path"], Path("cases.json"))
        self.assertEqual(build.call_args.kwargs["cases_sha256"], "1" * 64)


@unittest.skipUnless(importlib.util.find_spec("pyarrow"), "install the ingest extra for adapter tests")
class ScienceCaseBuildTests(unittest.TestCase):
    # Reuse invented, receipt-backed format setup without inheriting its test cases.
    setUp = fixtures.IngestTests.setUp
    tearDown = fixtures.IngestTests.tearDown
    save_manifest = fixtures.IngestTests.save_manifest
    receipt = fixtures.IngestTests.receipt
    evidence = fixtures.IngestTests.evidence

    def case_file(self, document=None):
        path = self.root / "cases.json"
        write_json(path, document or pack())
        return path

    def test_default_original_ten_and_case_ids_remain_unchanged(self):
        output = self.root / "default"
        report = build_snapshot(self.manifest, self.catalog, output)
        expected = [f"{symbol.lower()}-{disease.lower()}-{action}-{modality}"
                    for symbol, disease, action, modality in PILOT]
        self.assertEqual([row["case_id"] for row in report["cases"]], expected)
        self.assertNotIn("case_pack", report)
        self.assertNotIn("case_pack", report["normalization_recipe"])
        self.assertFalse((output / "case-pack.json").exists())
        for case_id in expected:
            self.assertIsNone(read_json(output / case_id / "case.json")["hypothesis"]["tissue"])

    def test_custom_case_scopes_are_source_bound_and_archive_exact_metadata(self):
        document = {**pack(scope(target_id=fixtures.GENES["CD276"], hgnc_id="HGNC:fictional-0"),
            scope(intended_action="activate"), scope(modality="adc"), scope(tissue="lung")),
            "resolution_provenance": {"fixture": "invented test only"}}
        path = self.case_file(document)
        output = self.root / "custom"
        report = build_snapshot(self.manifest, self.catalog, output, cases_path=path,
                                cases_sha256=sha256_file(path), packet_layout="bounded")
        self.assertEqual(len(report["cases"]), 4)
        self.assertFalse(report["blocked_cases"])
        self.assertEqual((output / "case-pack.json").read_bytes(), path.read_bytes())
        self.assertEqual(report["case_pack"]["sha256"], sha256_file(path))
        self.assertEqual(report["normalization_recipe"]["case_pack"], report["case_pack"])
        self.assertEqual(len({row["hypothesis_key"] for row in report["cases"]}), 4)
        for item in report["cases"]:
            folder = output / item["case_id"]
            case = decode(Case, read_json(folder / "case.json"))
            case.validate()
            self.assertEqual(case.hypothesis.target_id, fixtures.GENES["CD276"])
            self.assertTrue(case.hypothesis.target_namespace_version.startswith("OpenTargets-25.09:target:"))
            self.assertTrue(case.hypothesis.indication_namespace_version.startswith("OpenTargets-25.09:disease:"))
            snapshot = read_json(folder / "snapshot.json")
            self.assertEqual(snapshot["coverage"]["case_pack"], report["case_pack"])
            self.assertFalse(snapshot["coverage"]["absence_claim"])
            for packet in item["packets"]:
                for observation in read_json(folder / packet["path"])["observations"]:
                    self.assertEqual(observation["features"], {})
                    self.assertIsNone(observation["context"]["tissue"])
        journal = read_chain(output / "journal.jsonl")
        event = next(row["details"] for row in journal if row["event"] == "build_case_pack_frozen")
        self.assertEqual(event["sha256"], report["case_pack"]["sha256"])

    def test_new_symbol_and_disease_not_in_default_pack_are_selected_explicitly(self):
        target_path = self.raw / "target.parquet"
        targets = self.pq.read_table(target_path).to_pylist()
        targets.append({"id": "ENSG00000000001", "approvedSymbol": "FRESH1", "approvedName": "Invented", "biotype": "protein_coding"})
        self.pq.write_table(self.pa.Table.from_pylist(targets), target_path)
        self.receipt(self.entries[0])
        disease_path = self.raw / "disease.parquet"
        diseases = self.pq.read_table(disease_path).to_pylist() + [{"id": "EFO_9999999", "name": "Invented fresh indication"}]
        self.pq.write_table(self.pa.Table.from_pylist(diseases), disease_path)
        self.receipt(self.entries[1])
        with (self.raw / "hgnc.tsv").open("a", encoding="utf-8", newline="") as stream:
            stream.write("HGNC:999999\tFRESH1\tApproved\tENSG00000000001\n")
        self.receipt(self.entries[3])
        self.evidence(self.rows + [{**self.rows[0], "id": "fictional-fresh-row", "targetId": "ENSG00000000001", "diseaseId": "EFO_9999999"}])
        output = self.root / "fresh"
        report = build_snapshot(self.manifest, self.catalog, output,
            cases_path=self.case_file(pack(scope(symbol="FRESH1", disease_id="EFO_9999999"))))
        self.assertEqual(len(report["cases"]), 1)
        self.assertEqual(report["cases"][0]["observations"], 1)
        self.assertEqual(report["counters"]["selected_rows"], 1)
        self.assertTrue(report["cases"][0]["case_id"].startswith("fresh1-efo_9999999"))

    def test_mismatched_declared_or_missing_canonical_ids_block_without_replacement(self):
        path = self.case_file(pack(scope(case_id="good"),
            scope(case_id="wrong-target", intended_action="activate", target_id="ENSG00000000000"),
            scope(case_id="wrong-hgnc", modality="adc", hgnc_id="HGNC:999999"),
            scope(case_id="missing-disease", disease_id="EFO_9999999")))
        report = build_snapshot(self.manifest, self.catalog, self.root / "blocked", cases_path=path)
        self.assertEqual([row["case_id"] for row in report["cases"]], ["good"])
        self.assertEqual({row["case_id"] for row in report["blocked_cases"]},
                         {"wrong-target", "wrong-hgnc", "missing-disease"})
        self.assertEqual(report["status"], "built_with_blocked_cases")

    def test_initial_anchor_failure_is_preserved_before_source_inspection(self):
        output = self.root / "bad-anchor"
        with patch("tether_engine.ingest._inspect") as inspect:
            with self.assertRaisesRegex(ContractError, "frozen SHA-256"):
                build_snapshot(self.manifest, self.catalog, output, cases_path=self.case_file(), cases_sha256="0" * 64)
        inspect.assert_not_called()
        self.assertEqual(read_json(output / "build-failure.json")["stage"], "case_pack_validation")
        self.assertEqual(inspect_run(output)["last_event"], "build_failed")

    def test_original_pack_mutation_during_build_is_rejected_and_original_copy_retained(self):
        path = self.case_file()
        original = path.read_bytes()
        inspect = ingest._inspect
        def mutate(*args):
            answer = inspect(*args)
            path.write_bytes(original + b" \n")
            return answer
        output = self.root / "mutated"
        with patch("tether_engine.ingest._inspect", side_effect=mutate):
            with self.assertRaisesRegex(ContractError, "Case pack changed"):
                build_snapshot(self.manifest, self.catalog, output, cases_path=path)
        self.assertEqual((output / "case-pack.json").read_bytes(), original)
        self.assertEqual(read_json(output / "build-failure.json")["stage"], "source_recheck")
        self.assertFalse((output / "build-report.json").exists())

    def test_archived_pack_mutation_is_rejected_even_if_original_is_unchanged(self):
        path = self.case_file()
        output = self.root / "archive-mutated"
        archive = ingest._archive_receipts
        def mutate(*args):
            archive(*args)
            (output / "case-pack.json").write_bytes(b"{}")
        with patch("tether_engine.ingest._archive_receipts", side_effect=mutate):
            with self.assertRaisesRegex(ContractError, "Case pack changed"):
                build_snapshot(self.manifest, self.catalog, output, cases_path=path)
        self.assertEqual(read_json(output / "build-failure.json")["stage"], "source_recheck")

    def test_duplicate_pack_failure_and_output_reservation_remain_inspectable(self):
        path = self.case_file(pack(scope(), scope(case_id="different-name")))
        output = self.root / "duplicate"
        with self.assertRaisesRegex(ContractError, "Duplicate complete"):
            build_snapshot(self.manifest, self.catalog, output, cases_path=path)
        before = (output / "journal.jsonl").read_bytes()
        with self.assertRaises((ContractError, FileExistsError)):
            build_snapshot(self.manifest, self.catalog, output, cases_path=path)
        self.assertEqual((output / "journal.jsonl").read_bytes(), before)
        self.assertEqual(inspect_run(output)["last_event"], "build_failed")
