"""Three views share their hypothesis/origin without laundering source lineage."""
from copy import deepcopy
import unittest

from tether_engine.serde import ContractError, fingerprint
from tools.science.research_views import build_views


class ResearchViewTests(unittest.TestCase):
    def setUp(self):
        self.case = dict(case_id='case', target_id='ENSG-fixture', indication_id='EFO-fixture',
                         target_namespace_version='old', indication_namespace_version='old',
                         intended_action='inhibit', modality='antibody', tissue=None)
        def source(key, release, purpose, when, parents=()):
            return dict(artifact_id=key, sha256=fingerprint(key), release=release,
                        role='reference', purpose=purpose, available_by=when, parents=list(parents),
                        datasource='gene_burden' if purpose == 'nonclinical_evidence' else None)
        self.frame = dict(schema_version=1, view_policy_id='fixture.v1',
                          decision_origin='2025-01-01T00:00:00Z', hypotheses=[self.case],
                          method_sha256=fingerprint('fixture-fixed-method'),
                          sources=[source('old', '24.09', 'nonclinical_evidence', '2024-09-19T00:00:00Z', ['mapping']),
                                   source('new', '25.09', 'nonclinical_evidence', '2025-09-30T00:00:00Z', ['mapping']),
                                   source('mapping', '24.09', 'identifier_mapping', '2024-09-19T00:00:00Z')],
                          views={'archived': ['old'], 'current_filtered': ['new'], 'current_unfiltered': ['new']},
                          filter_field='publicationDate', max_rows=100, max_selected_rows=100)

    def row(self, source='new', date='2024-06-01', identity='r1', **values):
        return dict(source_id=source, row_group=0, row_index=0,
                    values=dict(id=identity, datasourceId='gene_burden', datatypeId='genetic_association',
                                targetId='ENSG-fixture', diseaseId='EFO-fixture', publicationDate=date, **values))

    def run_views(self, rows=()):
        return build_views(self.frame, rows, expected_frame_sha256=fingerprint(self.frame))

    def test_three_views_same_origin_scope_and_truthful_temporal_verdict(self):
        result = self.run_views([self.row('old'), self.row()])
        views = result['views']
        self.assertEqual([len(views[k]['records']) for k in self.frame['views']], [1, 1, 1])
        self.assertEqual({v['decision_origin'] for v in views.values()}, {self.frame['decision_origin']})
        self.assertEqual(len({v['case_universe_sha256'] for v in views.values()}), 1)
        self.assertEqual(views['archived']['temporal_verdict'], 'eligible_by_declared_lineage')
        self.assertEqual(views['current_filtered']['temporal_verdict'], 'later_information')
        self.assertEqual(views['current_unfiltered']['temporal_verdict'], 'later_information')
        self.assertEqual(result['integrity_verdict'], 'requires_external_source_byte_verification')

    def test_filter_retains_unknowns_only_in_unfiltered_and_counts_them(self):
        rows = [self.row(date='2024'), self.row(date='2025', identity='r2'),
                self.row(date=None, identity='r3'), self.row(date='malformed', identity='r4')]
        for i, row in enumerate(rows): row['row_index'] = i
        views = self.run_views(rows)['views']
        self.assertEqual(len(views['current_filtered']['records']), 1)
        self.assertEqual(len(views['current_unfiltered']['records']), 4)
        self.assertEqual(views['current_filtered']['coverage']['date_not_comparable'], 2)
        self.assertEqual(views['current_filtered']['coverage']['date_rejected'], 3)

    def test_future_mapping_denies_archive_before_consuming_rows(self):
        self.frame['sources'][2]['available_by'] = '2025-01-02T00:00:00Z'
        def forbidden():
            self.fail('Rows read before lineage check'); yield
        with self.assertRaisesRegex(ContractError, 'Archived lineage'): self.run_views(forbidden())

    def test_evaluator_and_clinical_parents_cannot_be_laundered(self):
        for field, value in (('role', 'evaluation_only'), ('purpose', 'clinical_outcomes')):
            with self.subTest(field=field):
                prior = self.frame['sources'][2][field]
                self.frame['sources'][2][field] = value
                with self.assertRaisesRegex(ContractError, 'Forbidden research ancestor'): self.run_views()
                self.frame['sources'][2][field] = prior

    def test_missing_cyclic_and_unused_lineage_fail(self):
        self.frame['sources'][0]['parents'] = ['absent']
        with self.assertRaisesRegex(ContractError, 'Missing'): self.run_views()
        self.frame['sources'][0]['parents'] = ['mapping']
        self.frame['sources'][2]['parents'] = ['old']
        with self.assertRaisesRegex(ContractError, 'cycle'): self.run_views()
        self.frame['sources'][2]['parents'] = []
        self.frame['sources'].append({**self.frame['sources'][2], 'artifact_id': 'unused'})
        with self.assertRaisesRegex(ContractError, 'Unused'): self.run_views()

    def test_current_arms_cannot_select_different_inputs(self):
        self.frame['views']['current_filtered'] = ['old']
        with self.assertRaisesRegex(ContractError, 'same source'): self.run_views()

    def test_wrong_frame_anchor_denied(self):
        with self.assertRaisesRegex(ContractError, 'frame anchor'):
            build_views(self.frame, [], expected_frame_sha256='0'*64)

    def test_unknown_source_and_repeated_locator_fail(self):
        with self.assertRaisesRegex(ContractError, 'source'): self.run_views([self.row('ungranted')])
        with self.assertRaisesRegex(ContractError, 'locator'): self.run_views([self.row(), self.row()])

    def test_duplicate_and_conflicting_ids_not_double_counted(self):
        rows = [self.row(), self.row(), self.row(identity='r2'), self.row(identity='r2', beta=1)]
        for i, row in enumerate(rows): row['row_index'] = i
        views = self.run_views(rows)['views']
        coverage = views['current_unfiltered']['coverage']
        self.assertEqual(coverage['duplicate_rows'], 1)
        self.assertEqual(coverage['conflicting_rows'], 2)
        self.assertEqual(coverage['accepted_rows'], 1)
        self.assertEqual(coverage['selected_rows'], 4)

    def test_clinical_fields_scores_and_unvalidated_features_not_exported(self):
        result = self.run_views([self.row(clinicalPhase=4, score=1, stoppedReason='fixture')])
        record = result['views']['current_unfiltered']['records'][0]
        self.assertFalse({'clinicalPhase', 'score', 'stoppedReason'} & set(record['values']))
        self.assertEqual(record['features'], {})
        self.assertIsNone(record['probability'])

    def test_unknown_and_unmatched_rows_are_not_biological_absence(self):
        row = self.row(); row['values']['targetId'] = 'unmapped'
        result = self.run_views([row])['views']['current_unfiltered']
        self.assertEqual(result['coverage']['outside_case_universe'], 1)
        self.assertEqual(result['coverage']['accepted_rows'], 0)
        self.assertEqual(result['case_coverage']['case']['interpretation'], 'no_selected_input_not_biological_absence')

    def test_hypothesis_action_modality_and_tissue_are_preserved(self):
        self.frame['hypotheses'].append({**self.case, 'case_id': 'second', 'intended_action': 'activate',
                                         'modality': 'peptide', 'tissue': 'fixture tissue'})
        result = self.run_views([self.row()])['views']['current_unfiltered']
        self.assertEqual(result['coverage']['accepted_rows'], 1)
        self.assertEqual(result['coverage']['case_records'], 2)
        self.assertNotEqual(result['hypotheses'][0]['hypothesis_sha256'], result['hypotheses'][1]['hypothesis_sha256'])

    def test_limits_and_unknown_publication_do_not_silently_drop_rows(self):
        self.frame['max_rows'] = 1
        row = self.row(identity='second'); row['row_index'] = 1
        with self.assertRaisesRegex(ContractError, 'row budget'): self.run_views([self.row(), row])
        self.frame['max_rows'] = 100
        self.frame['max_selected_rows'] = 1
        with self.assertRaisesRegex(ContractError, 'selected-row budget'): self.run_views([self.row(), row])

    def test_production_temporal_gate_still_rejects_modern_ancestors(self):
        from datetime import date
        from tether_engine.contracts import Availability
        from tether_engine.provenance import check_role
        from tether_engine.temporal import utc_instant
        for source, expected in ((self.frame['sources'][0], None),
                                  (self.frame['sources'][1], 'available_after_origin')):
            availability = Availability(None, None, None, None, date(2026, 11, 15),
                                        'fixture_release_bound', None,
                                        utc_instant(source['available_by']), source['sha256'])
            self.assertEqual(availability.exclusion(utc_instant(self.frame['decision_origin'])), expected)
        with self.assertRaisesRegex(ContractError, 'Evaluator'):
            check_role('ot_evidence', 'evaluation_only', None)

    def test_archive_unknown_publication_is_not_invented_but_future_is_excluded(self):
        old = self.row('old', date=None)
        future = self.row('old', date='2026', identity='future'); future['row_index'] = 1
        result = self.run_views([old, future])['views']['archived']
        self.assertEqual(result['coverage']['accepted_rows'], 1)
        self.assertEqual(result['coverage']['date_rejected'], 1)
        self.assertIsNone(result['records'][0]['values']['publicationDate'])

    def test_outputs_do_not_alias_frame_or_input_rows(self):
        row = self.row(literature=['fixture-paper'])
        original = deepcopy(self.frame)
        result = self.run_views([row])
        self.assertEqual(self.frame, original)
        row['values']['literature'].append('later-mutation')
        self.frame['sources'][0]['role'] = 'evaluation_only'
        self.assertEqual(result['views']['current_unfiltered']['records'][0]['values']['literature'], ['fixture-paper'])
        self.assertEqual(result['views']['archived']['lineage'][1]['role'], 'reference')

    def test_known_drug_mislabeled_as_nonclinical_file_is_failed_qc(self):
        row = self.row(); row['values']['datatypeId'] = 'known_drug'
        result = self.run_views([row])['views']['current_unfiltered']
        self.assertEqual(result['coverage']['failed_qc_rows'], 1)
        self.assertEqual(result['coverage']['accepted_rows'], 0)

    def test_inconsistent_publication_year_is_failed_qc(self):
        result = self.run_views([self.row(publicationYear=2026)])['views']['current_unfiltered']
        self.assertEqual(result['coverage']['failed_qc_rows'], 1)
        self.assertEqual(result['coverage']['accepted_rows'], 0)

    def test_future_year_alone_is_excluded_from_archive_without_imputation(self):
        result = self.run_views([self.row('old', date=None, publicationYear=2026)])['views']['archived']
        self.assertEqual(result['coverage']['date_rejected'], 1)
        self.assertEqual(result['coverage']['accepted_rows'], 0)

    def test_caller_cannot_label_a_contemporary_release_as_the_archived_view(self):
        self.frame['views']['archived'] = ['new']
        with self.assertRaisesRegex(ContractError, 'Archived lineage'): self.run_views()

    def test_deep_lineage_has_an_explicit_limit_before_row_access(self):
        self.frame['sources'][2]['parents'] = ['depth-0']
        for i in range(65):
            self.frame['sources'].append({**self.frame['sources'][2], 'artifact_id': f'depth-{i}',
                                         'parents': [f'depth-{i+1}'] if i < 64 else []})
        with self.assertRaisesRegex(ContractError, 'depth limit'): self.run_views()


if __name__ == '__main__':
    unittest.main()
