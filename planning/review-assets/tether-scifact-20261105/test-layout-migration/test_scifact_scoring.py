"""Hand-computable fictional SciFact controls; no production reference access."""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from asof.serde import ContractError, canonical
from experiments.scifact.native_contract import (
    MAX_PREDICTION_BYTES, parse_prediction, validate_prediction,
    validate_references, validate_schedule,
)
from experiments.scifact.evaluate import (
    EVALUATOR_SHA256, evaluate_schedule, materialize_official_evaluator,
    official_metrics, strict_correct, _safe_members,
)


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = ROOT / 'data/raw/scifact_public/20261105-attempt01'
REFERENCE_ROOT = ROOT / 'data/reference/scifact-evaluator-66feffc5'
CORPUS = {10: {'doc_id': 10, 'title': 'Fictional A',
               'abstract': [f'Fictional sentence {i}.' for i in range(7)]},
          20: {'doc_id': 20, 'title': 'Fictional B',
               'abstract': ['Independent invented sentence.']}}


def prediction(claim=1, label='SUPPORT', sents=(0,), doc='10'):
    return {'id': claim, 'evidence': {doc: {'label': label, 'sentences': list(sents)}}}


def reference(claim=1, label='SUPPORT', rationales=((0,),), doc='10'):
    return {'id': claim, 'evidence': {doc: [
        {'label': label, 'sentences': list(sents)} for sents in rationales]}}


def expected_metrics(abstract=(1, 1, 1), rationalized=(1, 1, 1),
                     selection=(1, 1, 1), label=(1, 1, 1)):
    return {f'{name}_{metric}': value
            for name, values in [('abstract_label_only', abstract),
                                 ('abstract_rationalized', rationalized),
                                 ('sentence_selection', selection),
                                 ('sentence_label', label)]
            for metric, value in zip(('precision', 'recall', 'f1'), values)}


class PredictionContractTests(unittest.TestCase):
    def assertRejected(self, value, message=None):
        with self.assertRaisesRegex(ContractError, message or '.'):
            validate_prediction(value, CORPUS, expected_claim_id=1)

    def test_copy_is_deeply_immutable_and_order_preserved(self):
        raw = prediction(sents=(2, 0, 1))
        result = validate_prediction(raw, CORPUS, expected_claim_id=1)
        raw['evidence']['10']['sentences'][0] = 6
        self.assertEqual(result['evidence']['10']['sentences'], (2, 0, 1))
        with self.assertRaises(TypeError):
            result['evidence']['10']['label'] = 'CONTRADICT'
        with self.assertRaises(TypeError):
            result['evidence']['10']['sentences'][0] = 6

    def test_native_empty_evidence_and_empty_rationale_are_legal(self):
        self.assertEqual(dict(validate_prediction({'id': 1, 'evidence': {}}, CORPUS)['evidence']), {})
        self.assertEqual(validate_prediction(prediction(sents=()), CORPUS)['evidence']['10']['sentences'], ())

    def test_semantically_wrong_but_well_formed_labels_are_not_rejected(self):
        self.assertEqual(validate_prediction(prediction(label='CONTRADICT'), CORPUS)['evidence']['10']['label'], 'CONTRADICT')

    def test_ids_and_expected_identity(self):
        for value in (True, -1, 1.0, '1', None):
            with self.subTest(value=value):
                self.assertRejected({'id': value, 'evidence': {}})
        self.assertRejected(prediction(claim=2), 'identity')

    def test_only_native_prediction_fields(self):
        for change in ({'answer': 'gold'}, {'cited_doc_ids': [10]}, {'evidence': None}):
            with self.subTest(change=change):
                self.assertRejected({**prediction(), **change})
        self.assertRejected({'id': 1})
        self.assertRejected([])

    def test_only_native_document_fields(self):
        for change in ({'confidence': .99}, {'label': 'NEI'}, {'label': 'support'},
                       {'sentences': '0'}, {'sentences': None}):
            raw = prediction(); raw['evidence']['10'].update(change)
            with self.subTest(change=change):
                self.assertRejected(raw)

    def test_native_document_ids_and_unknown_documents(self):
        for doc in (10, '010', '+10', ' 10', '-1', '1.0', '999'):
            with self.subTest(doc=doc):
                self.assertRejected(prediction(doc=doc))
        self.assertEqual(validate_prediction(prediction(doc='20'), CORPUS)['id'], 1)

    def test_sentence_ids(self):
        for sentences in ((True,), (-1,), (1.0,), ('1',), (7,), (0, 0)):
            with self.subTest(sentences=sentences):
                self.assertRejected(prediction(sents=sentences))

    def test_string_key_corpus_and_ambiguous_alias(self):
        self.assertEqual(validate_prediction(prediction(), {'10': CORPUS[10]})['id'], 1)
        with self.assertRaisesRegex(ContractError, 'alias'):
            validate_prediction(prediction(), {10: CORPUS[10], '10': CORPUS[10]})

    def test_parser_rejects_duplicate_keys_nonfinite_and_oversize(self):
        values = [b'{"id":1,"id":2,"evidence":{}}',
                  b'{"id":1,"evidence":{"10":{"label":"SUPPORT","label":"CONTRADICT","sentences":[0]}}}',
                  b'{"id":NaN,"evidence":{}}', b'\xff', b' ' * (MAX_PREDICTION_BYTES + 1)]
        for raw in values:
            with self.subTest(size=len(raw)):
                with self.assertRaises(ContractError):
                    parse_prediction(raw, CORPUS)
        self.assertEqual(parse_prediction(canonical(prediction()), CORPUS)['id'], 1)

    def test_schedule_requires_nonempty_unique_ordered_native_ids(self):
        self.assertEqual(validate_schedule([4, 1]), (4, 1))
        for invalid in ([], [1, 1], [True], ['1'], [-1], '123'):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ContractError):
                    validate_schedule(invalid)

    def test_gold_references_validate_order_and_known_metadata(self):
        gold = reference(); gold.update(claim='Fictional claim.', cited_doc_ids=[10, 20])
        result = validate_references([gold], CORPUS, [1])
        self.assertEqual(result[0]['id'], 1)
        with self.assertRaises(ContractError):
            validate_references([reference(claim=2)], CORPUS, [1])
        with self.assertRaises(ContractError):
            validate_references([gold, gold], CORPUS, [1, 2])

    def test_gold_rejects_mixed_labels_overlap_empty_and_bad_sentence(self):
        mixed = reference(rationales=((0,), (1,)))
        mixed['evidence']['10'][1]['label'] = 'CONTRADICT'
        for gold in [mixed, reference(rationales=((0, 1), (1, 2))),
                     reference(rationales=((),)), reference(rationales=((99,),)),
                     {'id': 1, 'evidence': {'10': []}}]:
            with self.subTest(gold=gold):
                with self.assertRaises(ContractError):
                    validate_references([gold], CORPUS, [1])

    def test_repeated_citation_metadata_is_preserved_not_scored_or_rejected(self):
        gold = reference()
        gold.update(claim='Fictional claim.', cited_doc_ids=[10, 10])
        result = validate_references([gold], CORPUS, [1])
        self.assertEqual(result[0]['cited_doc_ids'], (10, 10))
        self.assertEqual(result[0]['claim'], 'Fictional claim.')


class OfficialScorerQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Production archive is not opened: only the exact pinned scorer source.
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / 'official'
        cls.evaluator = materialize_official_evaluator(ARCHIVE_ROOT, cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assertMetrics(self, golds, preds, expected):
        actual = official_metrics(golds, preds, evaluator_path=self.evaluator)
        self.assertEqual(set(actual), set(expected))
        for name, value in expected.items():
            self.assertAlmostEqual(actual[name], value, places=12, msg=name)

    def test_materialization_preserves_exact_pinned_code_and_refuses_reuse(self):
        self.assertEqual(hashlib.sha256(self.evaluator.read_bytes()).hexdigest(), EVALUATOR_SHA256)
        self.assertTrue((self.output / 'LICENSE').is_file())
        self.assertTrue((self.output / 'MATERIALIZED.json').is_file())
        with self.assertRaises(FileExistsError):
            materialize_official_evaluator(ARCHIVE_ROOT, self.output)

    def test_perfect_support_and_contradiction(self):
        self.assertMetrics([reference(), reference(claim=2, label='CONTRADICT')],
                           [prediction(), prediction(claim=2, label='CONTRADICT')], expected_metrics())

    def test_empty_gold_and_empty_predictions_have_zero_native_f1(self):
        self.assertMetrics([{'id': 1, 'evidence': {}}], [{'id': 1, 'evidence': {}}],
                           expected_metrics(*([(0, 0, 0)] * 4)))

    def test_missing_document_has_zero_recall(self):
        self.assertMetrics([reference()], [{'id': 1, 'evidence': {}}],
                           expected_metrics(*([(0, 0, 0)] * 4)))

    def test_wrong_label_preserves_only_sentence_selection_credit(self):
        self.assertMetrics([reference()], [prediction(label='CONTRADICT')],
                           expected_metrics((0, 0, 0), (0, 0, 0), (1, 1, 1), (0, 0, 0)))

    def test_partial_multisentence_rationale_has_no_sentence_credit(self):
        self.assertMetrics([reference(rationales=((0, 1),))], [prediction(sents=(0,))],
                           expected_metrics((1, 1, 1), (0, 0, 0), (0, 0, 0), (0, 0, 0)))

    def test_alternative_rationales_use_total_sentence_denominator(self):
        self.assertMetrics([reference(rationales=((0, 1), (2,)))], [prediction(sents=(2,))],
                           expected_metrics((1, 1, 1), (1, 1, 1), (1, 1/3, .5), (1, 1/3, .5)))

    def test_first_three_order_matters_for_abstract_but_not_sentence_credit(self):
        gold = reference(rationales=((3, 4),))
        pred = prediction(sents=(0, 1, 2, 3, 4))
        self.assertMetrics([gold], [pred], expected_metrics((1, 1, 1), (0, 0, 0), (.4, 1, 4/7), (.4, 1, 4/7)))
        self.assertFalse(strict_correct(gold, pred))

    def test_long_rationale_cap_expands_to_shortest_gold_length(self):
        gold = reference(rationales=((0, 1, 2, 3),))
        pred = prediction(sents=(0, 1, 2, 3, 4))
        self.assertMetrics([gold], [pred], expected_metrics((1, 1, 1), (1, 1, 1), (.8, 1, 8/9), (.8, 1, 8/9)))
        self.assertTrue(strict_correct(gold, pred))

    def test_extra_wrong_document_penalizes_native_precision_and_strict_case(self):
        pred = prediction(); pred['evidence']['20'] = {'label': 'SUPPORT', 'sentences': [0]}
        self.assertMetrics([reference()], [pred], expected_metrics(*([(.5, 1, 2/3)] * 4)))
        self.assertFalse(strict_correct(reference(), pred))

    def test_order_or_missing_ids_are_not_silently_repaired(self):
        for preds in ([prediction(claim=2)], [], [prediction(), prediction()]):
            with self.subTest(preds=preds):
                with self.assertRaises(ContractError):
                    official_metrics([reference()], preds, evaluator_path=self.evaluator)

    def test_tampered_scorer_is_not_executed(self):
        path = Path(self.temp.name) / 'tampered.py'
        path.write_bytes(self.evaluator.read_bytes() + b'\nraise RuntimeError("wrong code")\n')
        with self.assertRaisesRegex(ContractError, 'scorer.*hash|hash.*scorer'):
            official_metrics([reference()], [prediction()], evaluator_path=path)

    def test_safe_source_members_reject_traversal_and_links(self):
        for name, link in [('../escape', False), ('/escape', False), ('a\\b', False),
                           ('C:/escape', False), ('safe/link', True)]:
            raw = io.BytesIO()
            with zipfile.ZipFile(raw, 'w') as z:
                item = zipfile.ZipInfo(name)
                item.filename = name  # Preserve raw backslash bytes on Windows.
                if link:
                    item.create_system = 3
                    item.external_attr = (0o120777 << 16)
                z.writestr(item, b'x')
            with zipfile.ZipFile(io.BytesIO(raw.getvalue())) as z:
                with self.assertRaises(ContractError):
                    _safe_members(z)

    def test_safe_source_members_reject_duplicate_paths(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as z:
            z.writestr('root/a', b'first')
            with self.assertWarns(UserWarning):
                z.writestr('root/a', b'second')
        with zipfile.ZipFile(io.BytesIO(raw.getvalue())) as z:
            with self.assertRaises(ContractError):
                _safe_members(z)

    def test_all_case_accounting_never_rewards_failure_placeholder(self):
        golds = [reference(), {'id': 2, 'evidence': {}}, {'id': 3, 'evidence': {}}, reference(claim=4)]
        records = [
            {'id': 1, 'producer_status': 'produced', 'check_status': 'accepted', 'prediction': prediction()},
            {'id': 2, 'producer_status': 'produced', 'check_status': 'accepted', 'prediction': {'id': 2, 'evidence': {}}},
            {'id': 3, 'producer_status': 'timeout', 'check_status': 'not_run', 'prediction': None, 'reason': 'Fictional timeout'},
            {'id': 4, 'producer_status': 'produced', 'check_status': 'rejected', 'prediction': prediction(claim=4), 'reason': 'Fictional source failure'},
        ]
        result = evaluate_schedule([1, 2, 3, 4], CORPUS, golds, records, evaluator_path=self.evaluator)
        self.assertEqual(result['scheduled_count'], 4)
        self.assertEqual(result['counts']['correct_and_admitted'], 2)
        self.assertEqual(result['counts']['correct_but_policy_rejected'], 1)
        self.assertEqual(result['counts']['successful_native_nei'], 1)
        self.assertEqual(result['rates']['correct_and_admitted_per_scheduled'], .5)
        self.assertIsNone(result['case_results'][2]['raw_strict_correct'])
        self.assertFalse(result['case_results'][2]['checked_strict_correct'])
        self.assertEqual(result['raw_metrics']['abstract_rationalized_f1'], 1)
        self.assertAlmostEqual(result['checked_metrics']['abstract_rationalized_f1'], 2/3)

    def test_missing_duplicate_or_out_of_order_record_fails(self):
        record = {'id': 1, 'producer_status': 'produced', 'check_status': 'accepted', 'prediction': prediction()}
        for records in ([], [record, record], [{**record, 'id': 2}]):
            with self.subTest(records=records):
                with self.assertRaises(ContractError):
                    evaluate_schedule([1], CORPUS, [reference()], records, evaluator_path=self.evaluator)

    def test_inconsistent_producer_check_dispositions_fail(self):
        base = {'id': 1, 'producer_status': 'produced', 'check_status': 'accepted', 'prediction': prediction()}
        mutations = [{'prediction': None}, {'producer_status': 'timeout', 'reason': 'failed'},
                     {'check_status': 'unknown'}, {'producer_status': 'unknown'},
                     {'cited_doc_ids': [10]}]
        for change in mutations:
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    evaluate_schedule([1], CORPUS, [reference()], [{**base, **change}], evaluator_path=self.evaluator)


if __name__ == '__main__':
    unittest.main()
