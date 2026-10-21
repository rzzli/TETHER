"""Independent adversarial role-boundary checks, using invented source responses."""
from copy import deepcopy
import io
from itertools import combinations
import json
import unittest

from asof.agents import SpecialistRequest
from asof.chrono import load_snapshot
from asof.local_model import LocalSelectionBackend
from asof.serde import ContractError, canonical, decode, fingerprint, read_json, sha256_file, write_json
from asof.workflow import Budget
from tests import test_science_comparison_workflow as workflow_fixtures
from tests import test_science_role_backend as backend_fixtures
from tools.science.comparison_workflow import run_case, verify_case
from tools.science.role_backend import ROLE_SELECTION_POLICY, role_allowed_ids, role_selection_payload
from asof.wire import FORMAT


class LegacySubsetViolation:
    """A two-ID proposal, one-ID reviewer, then an invalid two-ID synthesis."""
    def __init__(self):
        self.count = 0

    def open(self, request, timeout):
        self.count += 1
        payload = json.loads(request.data)
        ids = payload['json_schema']['properties']['observation_ids']['items']['enum']
        selected = ids[:1] if self.count == 4 else ids[:2]
        return io.BytesIO(canonical({'content': json.dumps({'observation_ids': selected}),
            'tokens_evaluated': 10, 'tokens_predicted': 5, 'truncated': False}))


class RoleConstraintPeerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = workflow_fixtures.ComparisonWorkflowTests('test_adapted_executes_five_real_stages_and_exact_source_claims')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def legacy_failure(self):
        fixture = self.fixture
        packet = read_json(fixture.fixture/'evidence.json')
        extra = deepcopy(packet['observations'][0])
        extra['observation_id'] = 'peer-invented-second-source-id'
        packet['observations'].append(extra)
        write_json(fixture.fixture/'evidence.json', packet)
        snapshot = read_json(fixture.fixture/'snapshot.json')
        snapshot['artifacts'][0]['sha256'] = sha256_file(fixture.fixture/'evidence.json')
        write_json(fixture.fixture/'snapshot.json', snapshot)
        fixture.store = load_snapshot(fixture.fixture/'snapshot.json', fixture.case)
        policy = deepcopy(fixture.policy)
        policy.pop('output_constraint_policy')
        backend = LocalSelectionBackend(fixture.config_path)
        backend.opener = LegacySubsetViolation()
        output = fixture.root/'legacy-failed-review-chain'
        result = run_case(fixture.case, fixture.store, backend, Budget(),
                          'adapted_virtual_biotech', output, policy)
        self.assertEqual('failed', result['status'])
        self.assertEqual([], result['claims'])
        self.assertEqual(5, result['calls'])
        return output, policy

    def test_legacy_completed_native_invalid_subset_failure_still_verifies(self):
        output, policy = self.legacy_failure()
        verified = verify_case(output, self.fixture.case, self.fixture.store, self.fixture.config, policy)
        self.assertEqual('verified', verified['status'])

    def test_new_policy_rejects_resealed_completed_response_outside_decoding_scope(self):
        output, policy = self.legacy_failure()
        policy['output_constraint_policy'] = 'native_json_schema_reviewed_subset_v1'
        write_json(output/'role-policy.json', policy)
        result = read_json(output/'result.json')
        result['configuration']['role_policy_sha256'] = fingerprint(policy)
        result['configuration']['backend_provenance']['selection_policy'] = ROLE_SELECTION_POLICY
        write_json(output/'result.json', result)
        execution = read_json(output/'backend-execution.json')
        for attempt in execution['attempts']:
            record = attempt['record']
            request = decode(SpecialistRequest, record['request'])
            record['payload'] = role_selection_payload(request, self.fixture.config['max_output_tokens'],
                self.fixture.config['seed'], self.fixture.config['retrieval']['wire_format'])
            record['payload_sha256'] = fingerprint(record['payload'])
        write_json(output/'backend-execution.json', execution)
        def update(event):
            if event['event'] == 'comparison_plan':
                event['details']['configuration'] = result['configuration']
        self.fixture.rebind(output, update)
        with self.assertRaises(ContractError):
            verify_case(output, self.fixture.case, self.fixture.store, self.fixture.config, policy)

    def test_reviewer_uses_last_proposal_and_full_candidate_packet(self):
        fixture = backend_fixtures.RoleBackendTests('test_default_adapter_payload_hook_and_quote_remain_exact')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        a, b, c = fixture.visible
        # Pre-review chief/delegation IDs do not restrict specialist freedom.
        request = fixture.request('scientific_reviewer', [[a], [a], [b, c]])
        self.assertEqual((b, c), role_allowed_ids(request))
        for previous in ([], [a], [b], [a, b], [c]):
            request = fixture.request('coordinator_synthesize', [[a], [b], [a, b, c], previous])
            self.assertEqual(tuple(x for x in fixture.visible if x in previous), role_allowed_ids(request))
            self.assertEqual(fixture.payload(request)['prompt'],
                             LocalSelectionBackend(fixture.path).payload_for(request)['prompt'])

    def test_every_three_candidate_subset_enforces_native_and_parser_boundary(self):
        fixture = backend_fixtures.RoleBackendTests('test_default_adapter_payload_hook_and_quote_remain_exact')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        visible = list(fixture.visible)
        subsets = [list(ids) for size in range(4) for ids in combinations(visible, size)]
        for stage in ('scientific_reviewer', 'coordinator_synthesize'):
            for allowed in subsets:
                choices = [visible, visible, allowed] if stage == 'scientific_reviewer' else [visible]*3+[allowed]
                request = fixture.request(stage, choices)
                for wire in ('canonical', FORMAT):
                    payload = role_selection_payload(request, 256, 123, wire)
                    output = payload['json_schema']['properties']['observation_ids']
                    self.assertEqual(len(allowed), output['maxItems'])
                    if allowed:
                        self.assertEqual(allowed, output['items']['enum'])
                    self.assertEqual(fixture.visible, tuple(row.observation_id for row in request.evidence))
                self.assertEqual(tuple(allowed), fixture.backend(allowed).select(request).observation_ids)
                for forbidden in set(visible)-set(allowed):
                    backend = fixture.backend([forbidden])
                    with self.assertRaises(ContractError):
                        backend.select(request)
                    self.assertEqual('failed', backend.records[0]['status'])


if __name__ == '__main__':
    unittest.main()
