import shutil
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from asof.agents import ExtractiveBackend
from asof.artifacts import verify_run
from asof.chrono import load_snapshot
from asof.contracts import Case, Category
from asof.ledger import EvidenceLedger
from asof.serde import ContractError, decode, read_json, write_json, sha256_file
from asof.workflow import run_workflow

ROOT = Path(__file__).resolve().parents[1]


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'src/asof/demo/v2', self.root / 'fixture')
        self.fixture = self.root / 'fixture'
        self.case = decode(Case, read_json(self.fixture / 'case.json'))
        self.store = load_snapshot(self.fixture / 'snapshot.json', self.case)

    def test_shared_invalid_context_fails_before_dispatch(self):
        class Capture(ExtractiveBackend):
            calls = 0
            def select(self, request):
                self.calls += 1
                return super().select(request)
        for change in ({'program_id': ''}, {'molecule_id': ''}, {'mapping_confidence': 2.0},
                       {'mapping_confidence': -1.0}, {'mapping_confidence': float('nan')},
                       {'eligible_since': self.case.origin + timedelta(days=1)},
                       {'phase_at_origin': -1}, {'status_at_origin': ''}):
            with self.subTest(change=change):
                case = replace(self.case, task='T6', endpoint=None, program=replace(self.case.program, **change))
                backend = Capture()
                with self.assertRaises(ContractError):
                    run_workflow(case, self.store, backend)
                self.assertEqual(backend.calls, 0)

    def test_withdrawn_dated_t6_is_valid_but_t1_is_not(self):
        program = replace(self.case.program, status_at_origin='withdrawn', phase_at_origin=3)
        case = replace(self.case, task='T6', endpoint=None, program=program)
        result = run_workflow(case, self.store, ExtractiveBackend())
        self.assertEqual(result.status, 'completed')
        self.assertIsNone(result.prediction.probability)
        with self.assertRaises(ContractError):
            replace(self.case, program=program).validate()

    def test_zero_confidence_cannot_admit_program_claims(self):
        packet = read_json(self.fixture / 'evidence.json')
        packet['observations'][0]['program_id'] = self.case.program.program_id
        write_json(self.fixture / 'evidence.json', packet)
        snap = read_json(self.fixture / 'snapshot.json')
        snap['artifacts'][0]['sha256'] = sha256_file(self.fixture / 'evidence.json')
        write_json(self.fixture / 'snapshot.json', snap)
        case = replace(self.case, task='T6', endpoint=None,
                       program=replace(self.case.program, mapping_confidence=0))
        store = load_snapshot(self.fixture / 'snapshot.json', case)
        self.assertFalse(any(r.observation.program_id for r in store.query(case, Category.GENETICS)))
        with self.assertRaises(ContractError):
            EvidenceLedger(case, store).append(Category.GENETICS, packet['observations'][0]['observation_id'])
        self.assertTrue(any(e.reason == 'unresolved_program_mapping' for e in store.exclusions))


class PortableLegacyTests(unittest.TestCase):
    def test_required_golden_fixture_verifies_after_relocation(self):
        source = ROOT / 'tests/fixtures/legacy-v1'
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'archived'
            shutil.copytree(source, target)
            anchor = (target / 'receipt.sha256').read_text().strip()
            result = verify_run(target, anchor)
            self.assertEqual(result['semantic_consistency'], 'unavailable_legacy_v1')
            self.assertEqual(result['source_binding'], 'current_originals')
            (target / 'source.json').write_text('{}')
            with self.assertRaises(ContractError):
                verify_run(target, anchor)
