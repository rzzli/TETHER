"""Production frame admission uses real immutable metadata reads, no models."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

from tether_engine.serde import canonical, encode
from experiments.litqa_refinement import run as r


class ProductionQualificationTests(unittest.TestCase):
    def setUp(self):
        folder = r.ROOT / 'data/cache/sc05-production-frame-controls'
        folder.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=folder)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / 'unused-production-output'
        self.path = self.root / 'FRAME.json'
        self.qualification_path = self.root / 'NATIVE-QUALIFICATION.json'
        receipt_path = self.root / 'invented-model-receipt.json'
        receipt_path.write_bytes(canonical({'fixture': 'metadata only, no model assets'}))
        license_path = self.root / 'invented-license.txt'
        license_path.write_text('Invented fixture only; no model is present.', encoding='utf-8')
        self.receipt = r.proof(receipt_path)
        self.pins = [r.proof(r.__file__)]
        self.provenance = {'fixture': 'invented model', 'source': self.receipt}
        self.qualification = {
            'kind': 'sc05_refinement_native_qualification_v1', 'status': 'passed',
            'code_files': self.pins, 'model_provenance': self.provenance,
            'native_tasks': ['critic', 'repair', 'removal'], 'automatic_retry': False,
            'checks': {'fixture_only': True},
        }
        self.frame = {
            'schema_version': 1, 'kind': r.KIND, 'purpose': 'production',
            'schedule': [str(UUID(int=i)) for i in range(1, 200)],
            'baseline': {'root': str(self.root / 'absent-baseline'), 'receipt_sha256': 'a' * 64},
            'interpreter': r.proof(sys.executable), 'code_files': self.pins,
            'phase_seconds': {phase: 600 for phase in r.schedule.PHASES},
            'port': 55631, 'alias': 'tether-sc05-refinement-qwen14b-v1',
            'model_receipt': self.receipt, 'model_license': r.proof(license_path),
            'model_spec': {'fixture_only': True}, 'model_provenance': self.provenance,
            'generation_configuration': encode(r.model.CONFIG), 'qualification': None,
            'provider_spend_usd': 0, 'automatic_retry': False, 'output': str(self.output),
        }

    def write_inputs(self):
        self.qualification_path.write_bytes(canonical(self.qualification))
        self.frame['qualification'] = r.proof(self.qualification_path)
        self.path.write_bytes(canonical(self.frame))
        return r.proof(self.path)['sha256']

    def admit(self, *, execute=False):
        digest = self.write_inputs()
        # Only the invented model identity and narrowed code closure are fixture
        # inputs. capture(), pipeline.read(), parsing and freezing are all real.
        with patch.object(r, 'MODEL_RECEIPT', self.receipt['sha256']), \
             patch.object(r, 'code_files', return_value=self.pins):
            if execute:
                return r.execute(self.path, digest, output=self.output)
            return r.load_frame(self.path, digest, self.output)

    def assert_rejected_without_dispatch(self):
        with patch.object(r, 'supervise_command') as dispatch, \
             patch.object(r.native_model, 'make_server_spec') as server, \
             patch.object(r.projection, 'verify_baseline_projection') as baseline:
            with self.assertRaises((ValueError, KeyError, TypeError)):
                self.admit(execute=True)
            dispatch.assert_not_called()
            server.assert_not_called()
            baseline.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_full_production_frame_accepts_real_frozen_native_task_metadata(self):
        with patch.object(r, 'supervise_command') as dispatch, \
             patch.object(r.projection, 'verify_baseline_projection') as baseline:
            frame, proof, output = self.admit()
            qualification = r.capture(frame['qualification'])
        self.assertEqual(qualification['native_tasks'], ('critic', 'repair', 'removal'))
        self.assertIsInstance(qualification['native_tasks'], tuple)
        self.assertEqual(frame['schedule'], tuple(self.frame['schedule']))
        self.assertEqual(len(frame['schedule']), 199)
        self.assertEqual(proof['sha256'], r.proof(self.path)['sha256'])
        self.assertEqual(output, self.output)
        dispatch.assert_not_called()
        baseline.assert_not_called()
        self.assertFalse(output.exists())

    def test_task_order_membership_type_and_missing_field_are_rejected(self):
        original = encode(self.qualification)
        for tasks in (['repair', 'critic', 'removal'], ['critic', 'repair'],
                      ['critic', 'repair', 'repair'], ['critic', 'repair', 'removal', 'extra'],
                      'critic,repair,removal', {'critic': 1, 'repair': 2, 'removal': 3}, None):
            with self.subTest(tasks=tasks):
                self.qualification = dict(original, native_tasks=tasks)
                self.assert_rejected_without_dispatch()
        self.qualification = dict(original)
        self.qualification.pop('native_tasks')
        self.assert_rejected_without_dispatch()

    def test_invalid_qualification_schema_status_retry_source_and_model_fail(self):
        changes = (
            ('kind', 'sc05_refinement_native_controls_result_v1'),
            ('status', 'failed'), ('automatic_retry', True),
            ('code_files', []), ('model_provenance', {'fixture': 'different model'}),
        )
        original = encode(self.qualification)
        for field, value in changes:
            with self.subTest(field=field):
                self.qualification = dict(original, **{field: value})
                self.assert_rejected_without_dispatch()

    def test_invalid_frame_schema_schedule_retry_source_and_model_fail(self):
        original = encode(self.frame)
        changes = (
            ('schema_version', 2), ('schedule', self.frame['schedule'][:-1]),
            ('automatic_retry', True), ('code_files', []),
            ('model_provenance', {'fixture': 'different model'}),
            ('model_receipt', dict(self.receipt, sha256='0' * 64)),
        )
        for field, value in changes:
            with self.subTest(field=field):
                self.frame = dict(original, **{field: value})
                self.assert_rejected_without_dispatch()

    def test_qualification_bytes_changed_after_anchor_are_rejected(self):
        digest = self.write_inputs()
        self.qualification_path.write_bytes(canonical(dict(self.qualification, status='failed')))
        with patch.object(r, 'MODEL_RECEIPT', self.receipt['sha256']), \
             patch.object(r, 'code_files', return_value=self.pins), \
             patch.object(r, 'supervise_command') as dispatch, \
             patch.object(r.native_model, 'make_server_spec') as server:
            with self.assertRaisesRegex(ValueError, 'proof changed'):
                r.execute(self.path, digest, output=self.output)
        dispatch.assert_not_called()
        server.assert_not_called()
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
