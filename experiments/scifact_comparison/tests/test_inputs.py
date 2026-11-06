import copy
import unittest

from experiments.scifact_comparison.inputs import (
    build_condition, build_primary, digest, map_rationale, validate_requests,
)


def fixture():
    queries = [dict(id=10, claim='Fictional protein Q reduces signal Z.')]
    corpus = [dict(doc_id=20, title='Fictional study', abstract=['Background.', 'Signal Z fell.', 'Replication agreed.']),
              dict(doc_id=21, title='Unrelated study', abstract=['A blue telescope was stored.'])]
    retrieved = [dict(doc_id=d['doc_id'], rank=i+1, score=.5/(i+1), document_sha256=digest(d))
                 for i, d in enumerate(corpus)]
    candidates = [dict(cell_id='10', status='completed', result=dict(retrieved=retrieved))]
    references = [dict(id=10, claim=queries[0]['claim'], evidence={
        '20': [dict(label='SUPPORT', sentences=[1]), dict(label='SUPPORT', sentences=[2])]},
        cited_doc_ids=[20])]
    return queries, corpus, candidates, references


class InputTests(unittest.TestCase):
    def setUp(self):
        self.q, self.c, self.b, self.g = fixture()
        self.p, self.retrieval = build_primary(self.q, self.c, self.b, [10], expected_k=2)

    def condition(self, name):
        return build_condition(self.p, name, references=self.g if name in ('rationale_only', 'evidence_removal') else None,
                               expected_k=2)

    def test_primary_exact_and_copied(self):
        requests, lineage = self.condition('primary')
        self.assertEqual(requests, self.p)
        requests[0]['documents'][0]['abstract'][0] = 'Changed'
        self.assertEqual(self.c[0]['abstract'][0], 'Background.')
        self.assertEqual(self.p[0]['documents'][0]['abstract'][0], 'Background.')
        self.assertIsNone(lineage[0]['documents'][0]['annotated_rationale_applicable'])

    def test_union_all_rationales_preserves_order(self):
        requests, lineage = self.condition('rationale_only')
        self.assertEqual(requests[0]['documents'][0]['abstract'], self.c[0]['abstract'][1:])
        self.assertEqual([s['original_index'] for s in lineage[0]['documents'][0]['sentences']], [1, 2])
        self.assertEqual(requests[0]['documents'][1], self.c[1])

    def test_removal_and_title_preserved(self):
        requests, lineage = self.condition('evidence_removal')
        self.assertEqual(requests[0]['documents'][0]['abstract'], ['Background.'])
        self.assertEqual(requests[0]['documents'][0]['title'], self.c[0]['title'])
        self.assertEqual(lineage[0]['documents'][1]['reason'], 'unchanged_no_annotated_evidence')

    def test_empty_is_unavailable_not_placeholder(self):
        self.g[0]['evidence']['20'] = [dict(label='SUPPORT', sentences=[0, 1, 2])]
        requests, lineage = self.condition('evidence_removal')
        self.assertEqual(requests[0]['documents'][0]['abstract'], [])
        self.assertEqual(lineage[0]['documents'][0]['disposition'], 'input_unavailable')

    def test_synthetic_never_source(self):
        for name in ('irrelevant_context', 'constructed_conflict'):
            requests, lineage = self.condition(name)
            doc = lineage[0]['documents'][0]
            self.assertEqual(requests[0]['documents'][0]['abstract'][:-1], self.c[0]['abstract'])
            self.assertIsNone(doc['sentences'][-1]['original_index'])
            mapped = map_rationale(dict(abstract_id=20, predicted_rationale=[1, 3]), doc)
            self.assertEqual(mapped['original_sentence_indices'], [1])
            self.assertEqual(len(mapped['synthetic_selections']), 1)
            self.assertNotEqual(doc['input_document_sha256'], doc['source_document_sha256'])

    def test_mapping_after_deletion(self):
        _, lineage = self.condition('rationale_only')
        mapped = map_rationale(dict(abstract_id=20, predicted_rationale=[0]), lineage[0]['documents'][0])
        self.assertEqual(mapped, dict(original_sentence_indices=[1], synthetic_selections=[]))

    def test_references_cannot_enter_primary_or_context_conditions(self):
        for name in ('primary', 'irrelevant_context', 'constructed_conflict'):
            with self.assertRaisesRegex(ValueError, 'References required only'):
                build_condition(self.p, name, references=self.g, expected_k=2)

    def test_references_required_for_masks(self):
        with self.assertRaises(ValueError):
            build_condition(self.p, 'evidence_removal', expected_k=2)

    def test_query_label_rejected(self):
        self.q[0]['label'] = 'SUPPORT'
        with self.assertRaisesRegex(ValueError, 'label-free'):
            build_primary(self.q, self.c, self.b, [10], expected_k=2)

    def test_worker_request_extra_metadata_rejected(self):
        self.p[0]['gold_mask'] = [1]
        with self.assertRaisesRegex(ValueError, 'exclude annotations'):
            validate_requests(self.p, expected_k=2)

    def test_tampered_source_rejected(self):
        self.c[0]['abstract'][0] = 'Tampered'
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            build_primary(self.q, self.c, self.b, [10], expected_k=2)

    def test_wrong_rank_rejected(self):
        self.b[0]['result']['retrieved'][0]['rank'] = 2
        with self.assertRaisesRegex(ValueError, 'rank'):
            build_primary(self.q, self.c, self.b, [10], expected_k=2)

    def test_duplicate_retrieval_rejected(self):
        self.b[0]['result']['retrieved'][1] = dict(self.b[0]['result']['retrieved'][0], rank=2)
        with self.assertRaisesRegex(ValueError, 'duplicate document'):
            build_primary(self.q, self.c, self.b, [10], expected_k=2)

    def test_wrong_schedule_rejected(self):
        with self.assertRaisesRegex(ValueError, 'membership'):
            build_primary(self.q, self.c, self.b, [11], expected_k=2)

    def test_wrong_reference_id_rejected(self):
        self.g[0]['id'] = 11
        with self.assertRaisesRegex(ValueError, 'Reference membership'):
            self.condition('rationale_only')

    def test_invalid_reference_index_rejected(self):
        for index in (True, -1, 3):
            self.g[0]['evidence']['20'][0]['sentences'] = [index]
            with self.assertRaisesRegex(ValueError, 'out of bounds'):
                self.condition('rationale_only')

    def test_empty_reference_set_rejected(self):
        self.g[0]['evidence']['20'][0]['sentences'] = []
        with self.assertRaisesRegex(ValueError, 'Empty rationale'):
            self.condition('rationale_only')

    def test_bad_prediction_mapping_rejected(self):
        _, lineage = self.condition('rationale_only')
        doc = lineage[0]['documents'][0]
        for indices in ([2], [True], [0, 0], [1, 0]):
            with self.assertRaises(ValueError):
                map_rationale(dict(abstract_id=20, predicted_rationale=indices), doc)

    def test_constructed_inputs_do_not_mutate_originals(self):
        before = copy.deepcopy((self.p, self.g))
        for name in ('primary', 'rationale_only', 'evidence_removal', 'irrelevant_context', 'constructed_conflict'):
            self.condition(name)
        self.assertEqual(before, (self.p, self.g))


if __name__ == '__main__':
    unittest.main()
