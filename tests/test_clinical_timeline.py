import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.feasibility.build_clinical_timeline import timelines, build


class ClinicalTimelineTests(unittest.TestCase):
    def setUp(self):
        self.record = {'nct_id': 'NCT12345678', 'overall_status': 'Recruiting', 'phase': 'Phase 2',
                       'last_update_posted_date': '2022-12-01'}
        self.cases = [{'candidate_id': 'P01', 'drug_anchor': 'drug', 'target_anchor': 'target', 'origin_record': self.record}]

    def snapshot(self, day, status='Recruiting'):
        return {'snapshot_date': day, 'availability_basis': 'dump_date_public_time_unknown',
                'records': [{**self.record, 'overall_status': status}]}

    def test_missing_observation_does_not_invent_timing_or_censoring(self):
        snapshots = [self.snapshot('2023-01-01'), {**self.snapshot('2024-01-01'), 'records': []},
                     self.snapshot('2025-01-01', 'TERMINATED')]
        before = copy.deepcopy(snapshots)
        result = timelines(self.cases, snapshots, '2025-01-01')[0]
        self.assertEqual(result['observed_differences'], [])
        self.assertIsNone(result['clinical_outcome'])
        self.assertIsNone(result['censoring_date'])
        self.assertEqual(snapshots, before)

    def test_reversals_and_unknown_are_observations_not_first_events(self):
        snapshots = [self.snapshot('2023-01-01'), self.snapshot('2023-07-02', 'UNKNOWN'),
                     self.snapshot('2024-01-01', 'RECRUITING')]
        differences = timelines(self.cases, snapshots, '2025-01-01')[0]['observed_differences']
        self.assertEqual(len(differences), 2)
        self.assertTrue(all(x['clinical_event_date'] is None and not x['monotonicity_assumed'] for x in differences))
        self.assertEqual(differences[0]['later_observation'], '2023-07-02')

    def test_later_inputs_duplicates_and_out_of_order_rejected(self):
        for snapshots in [[self.snapshot('2026-01-01')],
                          [self.snapshot('2024-01-01'), self.snapshot('2023-01-01')],
                          [self.snapshot('2024-01-01'), self.snapshot('2024-01-01')]]:
            with self.assertRaises(ValueError): timelines(self.cases, snapshots, '2025-01-01')
        snapshot = self.snapshot('2024-01-01')
        snapshot['records'][0]['results_first_posted_date'] = '2024-01-02'
        with self.assertRaises(ValueError): timelines(self.cases, [snapshot], '2025-01-01')
        snapshot = self.snapshot('2024-01-01')
        snapshot['records'] *= 2
        with self.assertRaises(ValueError): timelines(self.cases, [snapshot], '2025-01-01')

    def test_phase_formatting_does_not_become_transition(self):
        second = self.snapshot('2024-01-01', 'RECRUITING')
        second['records'][0]['phase'] = 'PHASE2'
        result = timelines(self.cases, [self.snapshot('2023-01-01'), second], '2025-01-01')
        self.assertEqual(result[0]['observed_differences'], [])

    def test_build_requires_unchanged_sealed_extract_and_never_reuses_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected = root / 'selected.json'
            selected.write_text(json.dumps(self.cases), encoding='utf-8')
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            proof = root / 'evidence-manifest.json'
            proof.write_text(json.dumps({'files': [{'path': 'selected.json', 'sha256': digest(selected)}]}))
            item = {'snapshot_date': '2023-01-01', 'path': str(selected), 'sha256': digest(selected),
                    'evidence_manifest': str(proof), 'evidence_manifest_sha256': digest(proof),
                    'format': 'selected_cases', 'availability_basis': 'dump_date'}
            manifest = {'selected_path': str(selected), 'selected_sha256': digest(selected),
                        'endpoint': '2025-01-01', 'snapshots': [item]}
            self.assertEqual(build(manifest, root / 'good')['trials'], 1)
            with self.assertRaises(FileExistsError): build(manifest, root / 'good')
            selected.write_text(json.dumps([{**self.cases[0], 'drug_anchor': 'altered'}]))
            with self.assertRaisesRegex(ValueError, 'Frozen selection changed'):
                build(manifest, root / 'bad-selection')
            manifest['selected_sha256'] = digest(selected)
            item['sha256'] = digest(selected)
            with self.assertRaisesRegex(ValueError, 'Extract missing from sealed evidence'):
                build(manifest, root / 'bad-proof')
            proof.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Snapshot evidence anchor changed'):
                build(manifest, root / 'bad-anchor')
            self.assertFalse((root / 'bad-anchor').exists())


if __name__ == '__main__':
    unittest.main()
