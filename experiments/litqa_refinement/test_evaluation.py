"""Invented full-stage joins and evaluator authority; no actual task keys."""
import copy
from dataclasses import replace
import inspect
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, encode, freeze
from experiments.labbench import evaluate as scorer_module, tether_adapter
from experiments.labbench.tests import test_model as model_fixtures
from experiments.litqa_comparison.tests import test_replay as replay_fixtures
from . import evaluation as e, model, pipeline, schedule, selection, source_evaluation
from . import test_pipeline as pipeline_fixtures, test_collection as source_fixtures
from . import transport
from . import test_native_evaluation as native_fixtures


def native_caller(nf, *, owner=None, alias=None):
    """Invented transport with genuine reserved cells and retained native bytes.

    nf is a test_replay.ReplayTests fixture. Only native/HTTP responses and
    process ownership are fictional; no scientific reader or gate is mocked.
    """
    owner = nf.f.owner if owner is None else owner
    alias = nf.alias if alias is None else alias
    def caller(descriptor, output, deadline):
        value = encode(descriptor)
        if value['task'] == 'critic':
            _, payload = model.make_critic_request(value['query'], value['prior'], value['sources'], value['model_provenance'])
            decoded = dict(support='not_assessable' if value['prior']['prediction'] is None else 'insufficient',
                           evidence_ids=[], criticism='Direct evidence is missing.', queries=[['Lumarin'], ['color']])
        else:
            payload = value['prepared_member']['payload']
            decoded = dict(answer_index=0, evidence_ids=[value['sources'][0]['source_id']] if value['sources'] else [])
        nf.f.payload = payload
        body = nf.f.native_body(content=canonical(decoded).decode(), model=alias)
        with patch.object(transport.native, '_check_owner', return_value=12345), \
             patch.object(transport.native, '_watchdog', return_value=model_fixtures.Timer()), \
             patch.object(transport.mcq, 'tokenize_once', side_effect=lambda *a, **k: native_fixtures.tokenize(nf, *a, **k)), \
             nf.f.transport(model_fixtures.Response(body)):
            return pipeline.NativeCaller(owner, alias)(descriptor, output, deadline)
    return caller


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = pipeline_fixtures.PipelineTests('runTest'); cls.fixture.setUp()
        cls.native = replay_fixtures.ReplayTests('runTest'); cls.native.setUp()
        cls.addClassCleanup(cls.fixture.doCleanups); cls.addClassCleanup(cls.native.doCleanups)
        f, nf = cls.fixture, cls.native
        caller = native_caller(nf)
        phases, parents = {}, {}
        for phase in e.PHASES:
            output = f.base/phase
            with patch.object(pipeline.collection.acquisition.legacy, 'fetch_http', side_effect=source_fixtures.fetcher(('PMC8',))):
                pipeline.execute(phase, f.baseline, output, purpose='fictional_qualification', seconds=120,
                    parents={key: parents[key] for key in schedule.PARENTS[phase]},
                    cutoff='2099-01-01T00:00:00+00:00' if phase == 'pair_prepare' else None,
                    model_provenance=nf.f.model, call_model=caller)
            parent = dict(root=str(output), receipt_sha256=e.native.proof(output/'STAGE-RECEIPT.json')['sha256'])
            parents[phase] = parent
            report = e.n.load(output/'REPORT.json')
            phases[phase] = dict(root=str(output), rows=report['rows'], report=report, inputs=e.n.load(output/'INPUTS.json'))
        info = dict(model_provenance=encode(nf.f.model), alias=nf.alias, owner_pid=12345,
                    endpoint='http://127.0.0.1:'+str(nf.f.spec.port))
        code = [e.native.proof(Path(module.__file__)) for module in (model, selection, tether_adapter)]
        cls.envelope = dict(root=str(f.base), root_receipt_sha256='a'*64, started_at_utc='2090-01-01T00:00:00Z',
            frame=dict(purpose='fictional_qualification', schedule=list(f.baseline.manifest['schedule']),
                model_provenance=encode(nf.f.model), code_files=code),
            phases=phases, baseline=encode(f.baseline.manifest), model_contexts={k: info for k in ('critic', 'repair', 'removal')},
            resources=dict(scope='fictional envelope resources', baseline_resources=[dict(id=q['id'],
                logical_model_usage=dict(generation_calls=1, measured_input_tokens=50, measured_output_tokens=12,
                    reserved_input_tokens=100, reserved_output_tokens=256, provider_cost_usd=0),
                logical_http_usage=dict(requests=2, measured_response_bytes=20, safety_accounted_bytes=20,
                    unknown_transfer_upper_bytes=0)) for q in f.baseline.queries]), baseline_acceptance=dict(fictional_only=True),
            supervised_root_verified=True, actor_roles_verified=True, baseline_verified=True)
        cls.report = e.join_stages(cls.envelope)

    def capability(self):
        root, receipt = self.envelope['root'], self.envelope['root_receipt_sha256']
        report, envelope = freeze(copy.deepcopy(self.report)), freeze(copy.deepcopy(self.envelope))
        digest = e.fingerprint(dict(root=root, receipt_sha256=receipt, report=report, envelope=envelope))
        value = e.VerifiedRefinement(root, receipt, report, envelope, digest, e._AUTHORITY, copy.deepcopy(self.envelope))
        # This unit fixture has reconstructed stages but intentionally mocks
        # only outer supervision. Full integration obtains actual issuance.
        e._ISSUED[id(value)] = value
        return value

    def authority(self, *, late=False):
        folder = self.fixture.base/self._testMethodName; folder.mkdir()
        note = folder/'protocol.md'; note.write_text('Explicit invented implementation protocol.')
        addendum = folder/'endpoints.md'; addendum.write_text('Explicit invented prospective endpoint statement.')
        contract = e.endpoint_contract('2100-01-01T00:00:00Z' if late else '2080-01-01T00:00:00Z',
            e.native.proof(note), e.native.proof(addendum))
        endpoint = folder/'ENDPOINTS.json'; endpoint.write_bytes(canonical(contract))
        queries = self.report['queries']
        values = dict(kind='sc05_fictional_evaluation_inputs_v1', role='evaluation_only', queries=queries,
            references=[dict(id=q['id'], answer_index=0, unsure_index=2) for q in queries],
            groups=[[q['id']] for q in queries], annotations={q['id']: [] for q in queries})
        keys = folder/'KEYS.json'; keys.write_bytes(canonical(values))
        scorer = scorer_module.evaluate_schedule
        dep_paths = {inspect.getsourcefile(scorer.__globals__[name]) for name in
                     ('freeze', 'evidence_ids', 'validate_prediction', 'validate_query', 'visible_unsure_index')}
        authority = dict(kind='sc05_refinement_evaluation_authority_v1', role='evaluation_only', purpose='fictional_qualification',
            created_at_utc='2099-01-01T00:00:00Z', producer=dict(root=self.envelope['root'], receipt_sha256='a'*64),
            baseline_acceptance=self.envelope['baseline_acceptance'], original_inputs=e.native.proof(keys),
            endpoint_freeze=e.native.proof(endpoint), native_scorer=e.native.proof(Path(scorer_module.__file__)),
            native_scorer_dependencies=[e.native.proof(Path(p)) for p in sorted(dep_paths)], native_scorer_archive=None)
        path = folder/'AUTHORITY.json'; path.write_bytes(canonical(authority))
        return e.native.proof(path), authority

    def test_full_two_case_join_accounts_every_call_and_mechanical_removal(self):
        out = self.report
        self.assertEqual(out['incremental_resources']['physical_totals']['generation_calls'], 6)
        self.assertTrue(out['source_lineage_checked']); self.assertTrue(out['native_calls_checked'])
        self.assertEqual(len(out['case_products']), 2)
        self.assertTrue(all(row['check_status'] == 'accepted' for row in out['records']['repair']))
        self.assertTrue(all(row['check_status'] == 'rejected' for row in out['records']['removal']))
        self.assertEqual(out['evidence_ids']['removal'], {q['id']: [] for q in out['queries']})
        self.assertFalse(out['scientific_support_verified'])
        resources = out['logical_resources']['conditions']
        self.assertEqual(resources['one_pass']['model_usage']['generation_calls'], 2)
        self.assertEqual(resources['critique_only']['model_usage']['generation_calls'], 4)
        self.assertEqual(resources['repair']['model_usage']['generation_calls'], 6)
        self.assertEqual(resources['removal']['model_usage']['generation_calls'], 6)
        self.assertTrue(resources['removal']['refinement_source_control_overhead'])
        self.assertFalse(resources['removal']['refinement_source_information_dependency'])

    def test_reordered_missing_and_duplicate_physical_identity_rejected(self):
        for kind in ('missing', 'reorder', 'duplicate'):
            env = copy.deepcopy(self.envelope)
            if kind == 'missing': env['phases']['repair']['rows'].pop()
            if kind == 'reorder': env['phases']['repair']['rows'].reverse()
            if kind == 'duplicate': env['phases']['repair']['rows'][0]['execution_id'] = env['phases']['critic']['rows'][0]['execution_id']
            with self.subTest(kind=kind), self.assertRaises(ValueError): e.join_stages(env)

    def test_semantic_selection_and_final_disposition_substitution_rejected(self):
        for kind in ('selection', 'disposition', 'accounting'):
            env = copy.deepcopy(self.envelope)
            if kind == 'selection': env['phases']['critic']['rows'][0]['product']['semantic_selection']['decision'] = 'keep'
            if kind == 'disposition': env['phases']['removal']['rows'][0]['product']['disposition']['check_status'] = 'accepted'
            if kind == 'accounting': env['phases']['repair']['rows'][0]['accounting']['measured_input_tokens'] = 49
            with self.subTest(kind=kind), self.assertRaises(ValueError): e.join_stages(env)

    def test_extra_stage_product_fields_and_contradictory_reason_rejected(self):
        for phase in ('critic', 'repair', 'removal'):
            for change in ('extra', 'reason'):
                env = copy.deepcopy(self.envelope)
                row = env['phases'][phase]['rows'][0]
                if change == 'extra': row['product']['reference_answer'] = 0
                else: row['reason'] = 'claims failure despite completed native call'
                with self.subTest(phase=phase, change=change), self.assertRaises(ValueError): e.join_stages(env)

    def test_unverified_or_mutated_capability_fails_before_reference_reader(self):
        good = self.capability()
        for value in (dict(self.report), replace(good, _authority=None), replace(good, receipt_sha256='b'*64)):
            with patch.object(e, '_inputs', side_effect=AssertionError('keys must not open')) as reader:
                with self.assertRaises(ValueError): e.evaluate(value, {}, native_scorer=scorer_module.evaluate_schedule)
                reader.assert_not_called()
        with self.assertRaises(TypeError): good.report['records']['repair'][0]['prediction']['answer_index'] = 1

    def test_independent_native_score_agreement_and_undefined_precision(self):
        descriptor, _ = self.authority(); value = self.capability()
        # Outer-supervision qualification is deliberately isolated from this
        # evaluator-only unit test. Full envelope tests use actual retained records.
        fake = SimpleNamespace(revalidate=lambda envelope: envelope)
        with patch.dict(sys.modules, {'experiments.litqa_refinement.envelopes': fake}):
            result = e.evaluate(value, descriptor, native_scorer=scorer_module.evaluate_schedule)
        self.assertTrue(result['provenance_validated'])
        self.assertEqual(result['native_agreement']['generated_conditions_checked'], 3)
        self.assertEqual(result['native']['repair']['counts']['raw_correct'], 2)
        self.assertIsNone(result['conditions']['critique_only']['statistical_retained_precision'])
        self.assertEqual(result['removal_diagnostic']['native']['counts']['correct_and_admitted'], 0)
        self.assertEqual(result['source_context_changes'], dict(scheduled_count=2, changed=2, unchanged=0, unavailable_refinement=0))
        self.assertEqual(result['original_source_metrics']['selected']['scheduled_count'], 2)
        self.assertEqual(result['logical_condition_resources']['conditions']['repair']['model_usage']['generation_calls'], 6)

    def test_late_endpoint_declaration_blocks_keys(self):
        descriptor, _ = self.authority(late=True); value = self.capability()
        fake = SimpleNamespace(revalidate=lambda envelope: envelope)
        with patch.dict(sys.modules, {'experiments.litqa_refinement.envelopes': fake}), \
             patch.object(e, '_inputs', side_effect=AssertionError('keys must not open')) as reader:
            with self.assertRaisesRegex(ValueError, 'precede benchmark'): e.evaluate(value, descriptor, native_scorer=scorer_module.evaluate_schedule)
            reader.assert_not_called()

    def test_authority_role_baseline_and_loaded_scorer_dependencies_cannot_change(self):
        descriptor, authority = self.authority(); value = self.capability()
        path = Path(descriptor['path']); original = path.read_bytes()
        fake = SimpleNamespace(revalidate=lambda envelope: envelope)
        for kind in ('role', 'baseline', 'dependencies', 'producer'):
            changed = copy.deepcopy(authority)
            if kind == 'role': changed['role'] = 'agent_evidence'
            if kind == 'baseline': changed['baseline_acceptance'] = {}
            if kind == 'dependencies': changed['native_scorer_dependencies'].pop()
            if kind == 'producer': changed['producer']['receipt_sha256'] = 'b'*64
            path.write_bytes(canonical(changed)); current = e.native.proof(path)
            with patch.dict(sys.modules, {'experiments.litqa_refinement.envelopes': fake}), \
                 patch.object(e, '_inputs', side_effect=AssertionError('keys must not open')) as reader:
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    e.evaluate(value, current, native_scorer=scorer_module.evaluate_schedule)
                reader.assert_not_called()
        path.write_bytes(original)

    def test_missing_reference_case_remains_error_not_reduced_cohort(self):
        descriptor, authority = self.authority(); value = self.capability()
        keys = Path(authority['original_inputs']['path']); content = e.n.load(keys)
        content['references'].pop(); keys.write_bytes(canonical(content))
        authority['original_inputs'] = e.native.proof(keys)
        path = Path(descriptor['path']); path.write_bytes(canonical(authority))
        fake = SimpleNamespace(revalidate=lambda envelope: envelope)
        with patch.dict(sys.modules, {'experiments.litqa_refinement.envelopes': fake}):
            with self.assertRaisesRegex(ValueError, 'Complete ordered references'):
                e.evaluate(value, e.native.proof(path), native_scorer=scorer_module.evaluate_schedule)


class CapabilityTests(unittest.TestCase):
    def test_private_field_copy_cannot_issue_an_unverified_result(self):
        report = freeze(dict(unverified=True)); envelope = freeze(dict(unverified=True))
        identity = dict(root='invented-unverified', receipt_sha256='a'*64, report=report, envelope=envelope)
        forged = e.VerifiedRefinement(identity['root'], identity['receipt_sha256'], report, envelope,
            e.fingerprint(identity), e._AUTHORITY, envelope)
        with self.assertRaisesRegex(ValueError, 'capability'): e._trusted(forged)


if __name__ == '__main__':
    unittest.main()
