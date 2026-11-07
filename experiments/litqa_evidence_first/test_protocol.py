"""Prospective protocol boundaries over unrelated invented control metadata."""
from datetime import datetime, timedelta, timezone
import copy
import unittest
from unittest.mock import patch

from tether_engine.serde import encode, freeze
from tether_engine.journal import RunJournal, read_chain
from . import contracts as c, run
from . import test_run as fixtures


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ControllerTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.frame = self.fixture.frame
        self.value = self.fixture.value
        self.declared = encode(c.read(self.frame['protocol']))
        self.sequence = 0

    def check(self, value):
        self.sequence += 1
        frame = dict(self.frame, protocol=c.write(
            self.fixture.root / f'protocol-boundary-{self.sequence}.json', value))
        return run.protocol(frame, self.value)

    def test_reference_anchor_is_metadata_only(self):
        reference = self.declared['original_inputs']
        read, capture = c.read, c.capture
        def closed_read(proof, *args, **kwargs):
            self.assertNotEqual(proof['path'], reference['path'], 'Reference answers opened during admission')
            return read(proof, *args, **kwargs)
        def closed_capture(path, *args, **kwargs):
            self.assertNotEqual(str(path), reference['path'], 'Reference bytes opened during admission')
            return capture(path, *args, **kwargs)
        with patch.object(c, 'read', side_effect=closed_read), patch.object(c, 'capture', side_effect=closed_capture):
            self.assertEqual(run.protocol(self.frame, self.value)['original_inputs'], reference)

    def test_declared_time_requires_existing_utc(self):
        for value in ('2026-01-01T00:00:00', '2026-01-01T01:00:00+01:00',
                      (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(dict(self.declared, created_at_utc=value))

    def test_reference_proof_cannot_be_replaced_by_an_untyped_hint(self):
        original = self.declared['original_inputs']
        for field, value in (('sha256', 'not-a-digest'), ('sha256', 'A' * 64),
                             ('bytes', True), ('bytes', 0), ('path', 'relative.json')):
            changed = copy.deepcopy(self.declared)
            changed['original_inputs'] = dict(original, **{field: value})
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.check(changed)

    def test_schema_and_approval_numbers_are_not_booleans(self):
        with self.assertRaises(ValueError):
            self.check(dict(self.declared, schema_version=True))
        approval = encode(c.read(self.declared['owner_approval']))
        for key in ('total_generations_cap', 'production_generations_cap', 'qualification_generations_cap',
                    'provider_cost_usd', 'new_source_http_requests'):
            changed = dict(approval, **{key: False})
            proof = c.write(self.fixture.root / f'approval-boundary-{key}.json', changed)
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(dict(self.declared, owner_approval=proof))

    def test_unrelated_approval_cannot_authorize_the_control_bank(self):
        approval = encode(c.read(self.declared['owner_approval']))
        proposal = c.write(self.fixture.root / 'different-proposal.json', {'scope': 'Other experiment'})
        approval['proposal'] = encode(proposal)
        anchor = c.write(self.fixture.root / 'different-approval.json', approval)
        with self.assertRaisesRegex(ValueError, 'Control bank'):
            self.check(dict(self.declared, owner_approval=anchor))

    def test_production_admission_uses_its_recorded_start_for_qualification(self):
        from . import reconstruct
        frame = dict(self.frame, purpose='production', qualification={'invented': 'external qualifier anchor'})
        value = freeze(dict(self.value, purpose='production', parent={
            'inspection': self.fixture.fixture.parent['original_inspection']}))
        journal = RunJournal(self.fixture.output, kind='build')
        journal.close()
        started = read_chain(self.fixture.output / 'journal.jsonl')[0]['details']['created_at_utc']
        with patch.object(run.release, 'verify', return_value={}), \
             patch.object(reconstruct, 'accept_qualification', return_value={}) as check:
            run.admit(frame, value)
        self.assertEqual(check.call_args.kwargs['production_started_at'], started)


if __name__ == '__main__':
    unittest.main()
