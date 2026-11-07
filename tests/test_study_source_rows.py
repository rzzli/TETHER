import unittest
from datetime import date, datetime, timezone
from tether_engine.study.source_rows import reconstruct_observation, verify_observation
from tether_engine.serde import ContractError, encode
from tether_engine.contracts import Availability


class SourceRowsTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "id": "id1",
            "targetId": "ENSG1",
            "diseaseId": "EFO1",
            "datasourceId": "europepmc",
            "datatypeId": "literature",
            "score": 0.4,
            "textMiningSentences": [{"text": "An invented source statement."}],
        }
        self.kw = dict(
            symbol="GENE",
            disease_name="Disease",
            locator={"source_id": "raw1", "row_group": 0, "row": 3},
            mapping_refs=("map1",),
            availability=Availability(
                None, None, None, None, date(2025, 1, 1), "fixture", None
            ),
            cutoff=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    def test_whole_record_mutations_rejected(self):
        original = reconstruct_observation(self.row, **self.kw)
        verify_observation(original, self.row, **self.kw)
        for field, value in [
            ("source_kind", "fabricated"),
            ("features", {"made_up": 1.0}),
            ("publication_year", 2010),
        ]:
            document = encode(original)
            document[field] = value
            with self.assertRaises(ContractError):
                verify_observation(document, self.row, **self.kw)

    def test_method_metadata_not_partially_verified(self):
        document = encode(reconstruct_observation(self.row, **self.kw))
        document["method"]["limitations"] = ["changed"]
        with self.assertRaises(ContractError):
            verify_observation(document, self.row, **self.kw)

    def test_clinical_and_future_rows_rejected(self):
        for extra in [
            {"datasourceId": "chembl"},
            {"clinicalStatus": "x"},
            {"publicationYear": 2027},
        ]:
            with self.assertRaises(ContractError):
                reconstruct_observation(dict(self.row, **extra), **self.kw)

    def test_complete_field_matrix_rejects_every_mutation(self):
        original = encode(reconstruct_observation(self.row, **self.kw))
        import copy

        mutations = {
            "context": dict(original["context"], species="invented"),
            "missingness": dict(original["missingness"], species="omitted"),
            "feature_scope": "wrong-scope",
            "study_id": "invented-study",
            "availability": dict(original["availability"], basis="changed"),
            "source_locator": dict(original["source_locator"], row=4),
            "source_metrics": dict(original["source_metrics"], score=9),
            "input_refs": ["other"],
            "target_id": "foreign",
            "program_id": "program",
            "computed_at": "2025-01-01T00:00:00Z",
            "method": dict(
                original["method"],
                parameters=dict(
                    original["method"]["parameters"], interpretation_scope="causal"
                ),
            ),
        }
        for field, value in mutations.items():
            with self.subTest(field=field), self.assertRaises(ContractError):
                changed = copy.deepcopy(original)
                changed[field] = value
                verify_observation(changed, self.row, **self.kw)
        changed = copy.deepcopy(original)
        changed["method"]["parameters"]["projection"].reverse()
        with self.assertRaises(ContractError):
            verify_observation(changed, self.row, **self.kw)

    def test_strings_and_nulls_preserved_without_inference(self):
        row = dict(
            self.row,
            ancestry={"unresolved": "x"},
            studyId="s",
            cohortId="c",
            publicationDate="2025-03-02",
            publicationYear=2025,
        )
        obs = encode(reconstruct_observation(row, **self.kw))
        self.assertEqual(obs["source_metrics"]["ancestry"], row["ancestry"])
        self.assertIsNone(obs["context"]["ancestry"])
        self.assertEqual(obs["missingness"]["ancestry"], "unresolved_provider_value")
        self.assertEqual(obs["study_id"], "europepmc:s")
        self.assertEqual(obs["dependency_group"], "europepmc:cohort:c")
        self.assertEqual(obs["publication_date"], "2025-03-02")


class ProjectedRowTests(unittest.TestCase):
    def test_arrow_batches_convert_only_selected_row(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from tether_engine.study.source_rows import parquet_row

        conversions = []
        calls = []

        class Batch:
            def __init__(self, start, count):
                self.start = start
                self.num_rows = count

            def slice(self, start, count):
                return Batch(self.start + start, count)

            def to_pylist(self):
                conversions.append((self.start, self.num_rows))
                return [
                    {"id": str(i)}
                    for i in range(self.start, self.start + self.num_rows)
                ]

        class Parquet:
            num_row_groups = 1
            schema_arrow = SimpleNamespace(names=["id", "clinicalStatus"])

            def iter_batches(self, **kwargs):
                calls.append(kwargs)
                return iter([Batch(0, 4), Batch(4, 4)])

        with patch(
            "tether_engine.study.source_rows.arrow",
            return_value=SimpleNamespace(ParquetFile=lambda path: Parquet()),
        ):
            result = parquet_row(
                "approved",
                {"row_group": 0, "row": 5},
                ("id",),
                deadline_check=lambda: None,
            )
        self.assertEqual(result, {"id": "5"})
        self.assertEqual(conversions, [(5, 1)])
        self.assertEqual(calls[0]["columns"], ["id"])
        self.assertEqual(calls[0]["row_groups"], [0])

    def test_row_reader_rejects_bad_locator_and_missing_column(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from tether_engine.study.source_rows import parquet_row

        parquet = SimpleNamespace(
            num_row_groups=1, schema_arrow=SimpleNamespace(names=["id"])
        )
        with patch(
            "tether_engine.study.source_rows.arrow",
            return_value=SimpleNamespace(ParquetFile=lambda path: parquet),
        ):
            for locator, columns in [
                ({"row_group": True, "row": 0}, ("id",)),
                ({"row_group": 1, "row": 0}, ("id",)),
                ({"row_group": 0, "row": 0}, ("absent",)),
                ({"row_group": 0, "row": 0}, ("id", "id")),
            ]:
                with self.assertRaises(ContractError):
                    parquet_row(
                        "approved", locator, columns, deadline_check=lambda: None
                    )
