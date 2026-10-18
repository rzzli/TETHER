import copy
from pathlib import Path
import tempfile
import unittest

from asof.serde import ContractError, read_json, sha256_file, write_json
from tools.feasibility.chronology_policy import validate_protocol, validate_frozen, utc


class ChronologyPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = read_json(Path('planning/protocols/evaluation-v0.1.json'))

    def test_valid_protocol_does_not_certify_lock_or_science(self):
        answer = validate_protocol(self.policy)
        self.assertEqual(answer['status'], 'valid_frozen_local_protocol')
        self.assertFalse(answer['clinical_ready'])
        self.assertFalse(answer['public_registration'])

    def test_later_contributor_or_missing_reviewer_rejected(self):
        p = copy.deepcopy(self.policy)
        p['models'][0]['released_at_upper_bound'] = '2025-01-02T00:00:00Z'
        with self.assertRaises(ContractError): validate_protocol(p)
        p = copy.deepcopy(self.policy); p['models'][0]['roles'].remove('reviewer')
        with self.assertRaises(ContractError): validate_protocol(p)

    def test_mutable_revision_or_later_finetune_rejected(self):
        for field, value in [('revision', 'main'), ('later_finetune_permitted', True)]:
            p = copy.deepcopy(self.policy); p['models'][0][field] = value
            with self.assertRaises(ContractError): validate_protocol(p)

    def test_future_evaluator_or_current_annotation_predictors_rejected(self):
        for field, value in [('released_at_upper_bound', '2025-09-01T00:00:00Z'),
                             ('evaluator_only', True), ('current_version_fallback', True)]:
            p = copy.deepcopy(self.policy); p['clinical']['predictor_sources'][0][field] = value
            with self.assertRaises(ContractError): validate_protocol(p)

    def test_incomplete_gates_and_unearned_lock_or_public_registration_rejected(self):
        p = copy.deepcopy(self.policy); del p['clinical']['activation_gates']['independent_labels']
        with self.assertRaises(ContractError): validate_protocol(p)
        p = copy.deepcopy(self.policy); p['clinical']['lock_status'] = 'locked'
        with self.assertRaises(ContractError): validate_protocol(p)
        p = copy.deepcopy(self.policy); p['registration']['publicly_registered'] = True
        with self.assertRaises(ContractError): validate_protocol(p)

    def test_timezone_and_order_are_explicit(self):
        for value in ['2025-01-01', '2025-01-01T00:00:00-08:00', None]:
            with self.assertRaises(ContractError): utc(value)
        p = copy.deepcopy(self.policy); p['clinical']['endpoint_at'] = p['clinical']['origin_at']
        with self.assertRaises(ContractError): validate_protocol(p)

    def test_frozen_proofs_detect_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root / 'proof'; source.write_bytes(b'original')
            protocol = root / 'p.json'; write_json(protocol, self.policy)
            freeze = root / 'f.json'; write_json(freeze, {'protocol': {'sha256': sha256_file(protocol)},
                'proofs': [{'path': str(source), 'sha256': sha256_file(source)}]})
            self.assertFalse(validate_frozen(protocol, freeze)['clinical_ready'])
            source.write_bytes(b'changed')
            with self.assertRaises(ContractError): validate_frozen(protocol, freeze)
