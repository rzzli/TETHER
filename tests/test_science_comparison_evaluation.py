"""Post-seal and scientific-scope regressions; no model server or inference."""
from copy import deepcopy
from dataclasses import replace
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.chrono import EvidenceStore, load_snapshot
from asof.contracts import Case, Category, EvidenceStatus
from asof.serde import ContractError, canonical, decode, encode, fingerprint, read_json, sha256_file, write_json
from tools.science.comparison_evaluation import evaluate, evaluate_case, reference_bindings, _read_pinned
from tools.science.comparison_evaluation import audit_selected_rows, select_original_audit_rows
from tools.science.comparison_evaluation import _configuration_binding


ROOT = Path(__file__).resolve().parents[1]
BUILD_HASH = 'd' * 64


def fixture_receipt(folder, config):
    """Hash tiny invented weight/native files; never execute either file."""
    from tools.science.run_comparison import pin
    model_root = folder/'invented-model'; (model_root/'runtime').mkdir(parents=True)
    model = model_root/'fixture.gguf'; model.write_bytes(b'INVENTED WEIGHT FIXTURE, NOT A MODEL')
    native = model_root/'runtime/llama-server.exe'; native.write_bytes(b'INVENTED NATIVE FIXTURE, NEVER EXECUTED')
    receipt = folder/'model-acquisition.json'
    write_json(receipt, {'root': str(model_root.resolve()), 'revision': 'invented-fixture',
        'items': [{'name': 'fixture.gguf', 'sha256': sha256_file(model), 'bytes': model.stat().st_size}],
        'runtime_files': [{'path': 'runtime/llama-server.exe', 'sha256': sha256_file(native)}]})
    config['model_id'] = 'Qwen/Qwen2.5-14B-Instruct-GGUF@invented-fixture'
    config['model_provenance'] = {'weights_sha256': {'fixture.gguf': sha256_file(model)},
        'runtime_sha256': sha256_file(native), 'acquisition_receipt_sha256': sha256_file(receipt)}
    return pin(receipt)


def fixture_code(folder):
    from tools.science.run_comparison import pin
    path = ROOT/'tools/science/comparison_workflow.py'
    archive = folder/'executed-code/tools/science/comparison_workflow.py'
    archive.parent.mkdir(parents=True); archive.write_bytes(path.read_bytes())
    return [pin(path)]


def fixture_launcher(folder, plan_path, cases, receipt):
    from asof.journal import RunJournal
    from tools.science.run_comparison import pin
    model_root = Path(read_json(Path(receipt['path']))['root'])
    native, model = model_root/'runtime/llama-server.exe', model_root/'fixture.gguf'
    write_json(folder/'server-command.json', {'argv': [str(native), '--model', str(model),
        '--host', '127.0.0.1', '--port', '55581', '--ctx-size', '16384', '--parallel', '1',
        '--n-gpu-layers', '99', '--threads', '8', '--alias', 'asof-science7-qwen25-14b', '--no-webui', '--offline'],
        'runtime_sha256': sha256_file(native)})
    (folder/'server.stdout.log').write_bytes(b'Invented fixture; no native process ran.\n')
    (folder/'server.stderr.log').write_bytes(b'')
    preparation = RunJournal(folder/'prepare', kind='build')
    preparation.append('plan_frozen', plan_sha256=sha256_file(plan_path)); preparation.close()
    execution = RunJournal(folder/'execution', kind='build')
    execution.append('model_verification_started')
    execution.append('model_verification_passed', server_sha256=sha256_file(native))
    execution.append('server_started', pid=123); execution.append('server_ready', pid=123)
    for case in cases:
        for arm in case['arms']:
            execution.append('arm_started', case_id=case['case_id'], arm=arm['arm'])
            execution.append('arm_verified', case_id=case['case_id'], arm=arm['arm'],
                             status=arm['status'], result_sha256=arm['result']['sha256'])
        execution.append('paired_case_source_reverified', case_id=case['case_id'])
    execution.append('execution_terminal', status='all_paired_runs_verified', server_stopped=True)
    execution.close()
    return {name: pin(folder/path) for name, path in {
        'execution_journal': 'execution/journal.jsonl', 'preparation_journal': 'prepare/journal.jsonl',
        'model_config': 'model-config.json', 'server_command': 'server-command.json',
        'native_stdout': 'server.stdout.log', 'native_stderr': 'server.stderr.log'}.items()}


class ComparisonEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        folder = ROOT/'src/asof/demo/v2'
        self.case = replace(decode(Case, read_json(folder/'case.json')), task='T6', endpoint=None)
        original = load_snapshot(folder/'snapshot.json', self.case)
        raw_node = original.snapshot.sources[0]
        self.raw_id, self.raw_hash, self.raw_url = raw_node.source_id, raw_node.sha256, raw_node.source_url
        records = []
        for category in Category:
            for record in original.query(self.case, category):
                observation = replace(record.observation, features={},
                    method=replace(record.observation.method, parameters={'source_row_sha256': fingerprint(record.observation.observation_id)}),
                    source_locator={'source_id': self.raw_id, 'row_group': 0, 'row': len(records), 'datasource_id': 'synthetic'})
                records.append(replace(record, observation=observation))
        self.store = EvidenceStore(original.snapshot, tuple(records), (), original.source_proofs)
        self.ids = {r.observation.category.value: r.observation.observation_id for r in records}

    def result(self):
        selections = {c.value: [self.ids[c.value]] if c in (Category.GENETICS, Category.LITERATURE) else [] for c in Category}
        coverage = {}
        for category in Category:
            records = self.store.query(self.case, category)
            observed = [r.observation.observation_id for r in records if r.observation.status == EvidenceStatus.OBSERVED]
            coverage[category.value] = {'status': 'completed', 'available_in_collected_case_world': len(observed),
                'nonobserved': [{'observation_id': r.observation.observation_id, 'status': r.observation.status.value}
                    for r in records if r.observation.status != EvidenceStatus.OBSERVED],
                'selected': len(selections[category.value]), 'retrieval': {'selected_ids': observed}}
        claims = []
        for category, ids in selections.items():
            for identity in ids:
                record = self.store.lookup(identity)
                claims.append({'category': category, 'observation_id': identity,
                    'evidence': encode(record), 'source_claim_sha256': fingerprint(record)})
        return {'case_id': self.case.case_id, 'case_sha256': fingerprint(self.case),
            'hypothesis_sha256': self.case.hypothesis.key, 'arm': 'asof', 'status': 'completed',
            'features': {}, 'probability': None, 'provider_spend_usd': 0, 'claims': claims,
            'selections': selections, 'coverage': coverage, 'calls': 2, 'elapsed_seconds': 1.0,
            'usage': {'input_tokens': 20, 'output_tokens': 4, 'cost_usd': 0},
            'measured_usage': {'input_tokens': 20, 'output_tokens': 4, 'cost_usd': 0},
            'estimated_usage': {'input_tokens': 0, 'output_tokens': 0, 'cost_usd': 0}}

    def reference(self, category='genetics', answer='supported'):
        identity = self.ids[category]
        observation = encode(self.store.lookup(identity).observation)
        return {'schema_version': 1, 'role': 'evaluation_only', 'reference_id': self.case.case_id+':'+identity,
            'case_id': self.case.case_id, 'hypothesis_sha256': self.case.hypothesis.key,
            'source_row_sha256': observation['method']['parameters']['source_row_sha256'],
            'statement': observation['statement'], 'answer': answer,
            'context': {'observed': observation['context'], 'source_metrics': observation['source_metrics'],
                        'missingness': observation['missingness'], 'adjudicated_limits': 'Synthetic fixture only'},
            'source_evidence': [{'artifact_sha256': self.raw_hash, 'locator': observation['source_locator'],
                                 'url': self.raw_url, 'retrieved_at': '2026-10-19'}],
            'reviews': [{'reviewer_id': str(i), 'reviewer_kind': 'ai_agent', 'blinded_to_arm_outputs': True,
                         'model_provenance': {'execution_id': str(i), 'model_id': 'synthetic'}} for i in (1, 2)],
            'adjudication': {'rationale': 'Synthetic source-reference test', 'independence_evidence': None},
            'reference_level': 'ai_source_adjudicated', 'validation_claim': 'source_grounded_ai_reference',
            'version_applicability': {'status': 'exact', 'snapshot_id': BUILD_HASH}}

    def assess(self, result=None, refs=None):
        return evaluate_case(self.case, self.store, result or self.result(), refs if refs is not None else [self.reference()], BUILD_HASH)

    def test_unreviewed_selection_is_unknown_not_incorrect(self):
        result = self.assess()
        self.assertEqual(1, result['categories']['genetics']['supported'])
        self.assertEqual(1, result['categories']['literature']['unreviewed_unknown'])
        self.assertEqual(0, result['categories']['literature']['contradicted'])
        self.assertEqual(1, result['categories']['literature']['exact_normalized_copies'])
        self.assertEqual('not_established', result['claims'][0]['scientific_truth'])

    def test_uncertain_unavailable_and_contradicted_annotations_are_distinct(self):
        for answer in ('contradicted', 'uncertain', 'unavailable'):
            category = self.assess(refs=[self.reference(answer=answer)])['categories']['genetics']
            self.assertEqual(1, category[answer]); self.assertEqual(0, category['supported'])
        self.assertIsNone(self.result()['probability'])

    def test_context_metrics_missingness_statement_and_claim_hash_are_exact(self):
        for field in ('statement', 'context', 'source_metrics', 'missingness'):
            result = self.result()
            result['claims'][0]['evidence']['observation'][field] = 'tampered' if field == 'statement' else {'invented': 'later interpretation'}
            with self.assertRaises(ContractError): self.assess(result)
        result = self.result(); result['claims'][0]['source_claim_sha256'] = 'a'*64
        with self.assertRaises(ContractError): self.assess(result)

    def test_Q1_join_rejects_wrong_case_hypothesis_source_row_and_build(self):
        for field, value in (('hypothesis_sha256', 'a'*64), ('source_row_sha256', 'a'*64),
                             ('statement', 'new biological assertion')):
            reference = self.reference(); reference[field] = value
            with self.assertRaises(ContractError): self.assess(refs=[reference])
        reference = self.reference(); reference['version_applicability']['snapshot_id'] = self.store.snapshot.snapshot_id
        with self.assertRaises(ContractError): self.assess(refs=[reference])
        # The qualified assembler names the build SHA, not per-case snapshot ID.
        self.assertTrue(reference_bindings(self.case, self.store, [self.reference()], BUILD_HASH))

    def test_Q1_join_rejects_context_locator_and_raw_source_hash_drift(self):
        for context in ('observed', 'source_metrics', 'missingness'):
            reference = self.reference(); reference['context'][context] = {'fabricated': 'fact'}
            with self.assertRaises(ContractError): self.assess(refs=[reference])
        for field, value in (('artifact_sha256', 'a'*64), ('locator', {'row': 999})):
            reference = self.reference(); reference['source_evidence'][0][field] = value
            with self.assertRaises(ContractError): self.assess(refs=[reference])

    def test_inapplicable_reference_and_no_reference_are_not_negative(self):
        reference = self.reference(); reference['version_applicability']['status'] = 'stale'
        category = self.assess(refs=[reference])['categories']['genetics']
        self.assertEqual(1, category['reference_not_applicable_unknown'])
        self.assertEqual(0, category['selected_Q1_overlap'])
        self.assertEqual(1, self.assess(refs=[])['categories']['genetics']['unreviewed_unknown'])

    def test_category_retrieval_selection_and_world_counts_cannot_be_rebound(self):
        for mutation in ('count', 'retrieval', 'category', 'selection', 'duplicate'):
            result = self.result()
            if mutation == 'count': result['coverage']['genetics']['available_in_collected_case_world'] = 999
            if mutation == 'retrieval': result['coverage']['genetics']['retrieval']['selected_ids'] = []
            if mutation == 'category': result['claims'][0]['category'] = 'safety'
            if mutation == 'selection': result['selections']['genetics'] = []
            if mutation == 'duplicate': result['claims'].append(deepcopy(result['claims'][0]))
            with self.assertRaises(ContractError): self.assess(result)

    def test_no_clinical_probability_or_independent_truth_upgrade(self):
        result = self.result(); result['probability'] = 0.7
        with self.assertRaises(ContractError): self.assess(result)
        reference = self.reference(); reference['reference_level'] = 'independently_adjudicated'
        with self.assertRaises(ContractError): self.assess(refs=[reference])
        result = self.assess()
        self.assertNotIn('auroc', result); self.assertNotIn('brier', result); self.assertNotIn('p_value', result)

    def test_zero_call_configuration_still_binds_model_retrieval_and_budget(self):
        plan = {'budget': {'max_calls': 16},'backend':{'selection_policy':'science7-prior-stage-output-schema-v1'}}
        config = {'retrieval': {'max_records': 12}, 'model_id': 'pinned-fixture'}
        result = {'calls': 0, 'arm': 'lexical', 'configuration': {'budget': deepcopy(plan['budget']),
            'retrieval': deepcopy(config['retrieval']), 'backend_id': 'local-structured-selection-v1',
            'backend_provenance': {'config': deepcopy(config),'selection_policy':'science7-prior-stage-output-schema-v1'}}}
        _configuration_binding(result, plan, config)
        for field in ('budget', 'retrieval', 'backend_id', 'backend_provenance'):
            changed = deepcopy(result); changed['configuration'][field] = 'unmatched' if field == 'backend_id' else {}
            with self.subTest(field=field), self.assertRaises(ContractError):
                _configuration_binding(changed, plan, config)

    def test_external_seal_mismatch_stops_before_reference_open_and_retains_failure(self):
        seal = self.root/'predictions-seal.json'; write_json(seal, {'role': 'bad'})
        references = self.root/'never-open-reference.json'
        with patch('tools.science.comparison_evaluation._read_pinned', wraps=_read_pinned) as opened:
            with self.assertRaises(ContractError):
                evaluate(seal, 'a'*64, references, 'b'*64, self.root/'evaluation')
        self.assertEqual(1, opened.call_count)
        self.assertTrue((self.root/'evaluation/failure.json').is_file())
        self.assertTrue((self.root/'evaluation/seal.json').is_file())
        with self.assertRaises(FileExistsError):
            evaluate(seal, sha256_file(seal), references, 'b'*64, self.root/'evaluation')

    def test_matching_digest_does_not_make_unsealed_or_answer_exposed_predictions_valid(self):
        for index, body in enumerate(({'schema_version': 1, 'role': 'draft'},
                {'schema_version': 1, 'role': 'sealed_predictions_before_evaluator_join',
                 'evaluator_answers_opened_by_launcher': True, 'clinical_probabilities': None})):
            path = self.root/f'seal-{index}.json'; write_json(path, body)
            with self.assertRaises(ContractError):
                evaluate(path, sha256_file(path), self.root/'missing-answers.json', 'a'*64, self.root/f'out-{index}')

    def test_original_row_selection_uses_only_distinct_final_claims_and_never_substitutes(self):
        claims = self.result()['claims']
        seen = set()
        selected = select_original_audit_rows(claims + [deepcopy(claims[0])], self.case.case_id, seen)
        self.assertEqual(2, len(selected)); self.assertEqual(2, len(seen))
        self.assertEqual([], select_original_audit_rows(claims, self.case.case_id, seen))
        self.assertEqual([], select_original_audit_rows([], self.case.case_id, set()))
        self.assertEqual(1, len(select_original_audit_rows(claims[:1], self.case.case_id, set())))

    def test_original_audit_requires_completed_matching_evaluation_before_sources(self):
        report = self.root/'bad-evaluation.json'
        write_json(report, {'role': 'evaluation_only', 'status': 'draft'})
        with self.assertRaises(ContractError):
            audit_selected_rows(self.root/'unopened-predictions.json', 'a'*64,
                report, sha256_file(report), self.root/'original-audit')
        self.assertTrue((self.root/'original-audit/failure.json').is_file())

    def test_complete_synthetic_six_arm_postseal_integration_without_inference(self):
        from tools.science.role_backend import RoleSelectionBackend
        from asof.workflow import Budget
        from tools.science.comparison_workflow import run_case, verify_case, ARMS
        from tests.test_science_comparison_workflow import NativeFixture, synthetic_policy
        folder = self.root/'predictions'; folder.mkdir()
        def pinned(path):
            return {'path': str(path.resolve()), 'sha256': sha256_file(path), 'bytes': path.stat().st_size}
        config = {'schema_version': 1, 'endpoint': 'http://127.0.0.1:55581', 'model_id': 'synthetic-only',
            'model_provenance': {'weights_sha256': {'fixture': 'a'*64}, 'runtime_sha256': 'b'*64},
            'retrieval': {'max_records': 12, 'max_request_bytes': 12000, 'wire_format': 'asof-shared-scientific-fields-v1'},
            'max_output_tokens': 256, 'timeout_seconds': 2, 'seed': 123}
        receipt = fixture_receipt(folder, config)
        config_path = folder/'model-config.json'; write_json(config_path, config)
        policy = synthetic_policy(); policy_path = folder/'role-policy.json'; write_json(policy_path, policy)
        proofs = {}
        for name in ('protocol', 'source_build', 'catalog'):
            path = folder/(name+'.json'); write_json(path, {'kind': 'synthetic-only'})
            proofs[name] = pinned(path)
        proofs['role_policy'] = pinned(policy_path)
        proofs['model_receipt'] = receipt; proofs['original_model_receipt'] = receipt
        plan = dict(proofs, backend={'selection_policy':'science7-prior-stage-output-schema-v1'},root=str(folder.resolve()), arms=list(ARMS), code=fixture_code(folder), budget=encode(Budget(max_calls=50)),
                    cases=[{'case_id': self.case.case_id, 'case': pinned(config_path), 'snapshot': pinned(policy_path)}],
                    execution_order=[{'case_id': self.case.case_id, 'arms': list(ARMS)}])
        plan_path = folder/'run-plan.json'; write_json(plan_path, plan)
        arm_rows = []
        for arm in ARMS:
            backend = RoleSelectionBackend(config_path); backend.opener = NativeFixture()
            arm_path = folder/'arms'/self.case.case_id/arm
            result = run_case(self.case, self.store, backend, Budget(max_calls=50), arm, arm_path, policy)
            verification = verify_case(arm_path, self.case, self.store, config, policy)
            verification_path = arm_path.parent/(arm+'-verification.json'); write_json(verification_path, verification)
            arm_rows.append({'arm': arm, 'path': str(arm_path.resolve()), 'result': pinned(arm_path/'result.json'),
                'seal': pinned(arm_path/'seal.json'), 'verification': pinned(verification_path),
                'status': result['status'], 'calls': result['calls'], 'usage': result['usage']})
        case_rows = [{'case_id': self.case.case_id, 'arms': arm_rows}]
        execution_path = folder/'execution-report.json'
        write_json(execution_path, {'status': 'all_paired_runs_verified', 'plan_sha256': sha256_file(plan_path),
            'server_stopped': True, 'owned_loopback_port_closed': True, 'cases': case_rows})
        seal_path = folder/'predictions-seal.json'
        write_json(seal_path, {'schema_version': 1, 'role': 'sealed_predictions_before_evaluator_join',
            'evaluator_answers_opened_by_launcher': False, 'clinical_probabilities': None,
            'plan': pinned(plan_path), 'execution_report': pinned(execution_path), 'cases': case_rows,
            'execution_proofs': fixture_launcher(folder, plan_path, case_rows, receipt)})
        reference = self.reference(); reference['version_applicability']['snapshot_id'] = proofs['source_build']['sha256']
        reference_path = self.root/'references.json'
        write_json(reference_path, {'schema_version': 1, 'role': 'evaluation_only', 'references': [reference]})
        # Production fixed-ten membership/source-admission logic is separately
        # exercised by launcher tests; only that fixture boundary is substituted.
        with patch('tools.science.run_comparison.validate_plan', return_value={'status': 'synthetic-plan'}), \
             patch('tools.science.run_comparison._load_case', return_value=(self.case, self.store)), \
             patch('tools.science.comparison_evaluation._source_input_proofs', return_value=[]), \
             patch('tools.science.comparison_evaluation._expected_config', return_value=config):
            original_seal, original_execution = read_json(seal_path), read_json(execution_path)
            # Even an externally repinned malformed seal must fail before the
            # evaluator opens reference answers.
            for index, mutation in enumerate(('missing_arm', 'duplicate_arm', 'wrong_case', 'result_path', 'running_server')):
                changed, execution = deepcopy(original_seal), deepcopy(original_execution)
                if mutation == 'missing_arm': changed['cases'][0]['arms'].pop()
                if mutation == 'duplicate_arm': changed['cases'][0]['arms'].append(deepcopy(changed['cases'][0]['arms'][0]))
                if mutation == 'wrong_case': changed['cases'][0]['case_id'] = 'unplanned-case'
                if mutation == 'result_path': changed['cases'][0]['arms'][0]['result']['path'] = str(reference_path)
                if mutation == 'running_server': execution['server_stopped'] = False
                execution['cases'] = changed['cases']
                write_json(execution_path, execution); changed['execution_report'] = pinned(execution_path)
                write_json(seal_path, changed)
                with patch('tools.science.comparison_evaluation._read_pinned', wraps=_read_pinned) as opened:
                    with self.assertRaises(ContractError):
                        evaluate(seal_path, sha256_file(seal_path), reference_path,
                                 sha256_file(reference_path), self.root/f'rejected-{index}')
                self.assertNotIn(str(reference_path), [str(call.args[0]) for call in opened.call_args_list])
            write_json(execution_path, original_execution); write_json(seal_path, original_seal)
            report = evaluate(seal_path, sha256_file(seal_path), reference_path,
                              sha256_file(reference_path), self.root/'postseal-evaluation')
        self.assertEqual(6, len(report['per_arm']))
        self.assertEqual(15, len(report['paired_selection_overlap']))
        self.assertEqual(4, len(report['evaluation_code']))
        for row in report['evaluation_code']:
            self.assertEqual(row['source']['sha256'], sha256_file(Path(row['archive']['path'])))
        self.assertIsNone(report['clinical_metrics']); self.assertIsNone(report['probabilities'])
        adapted = next(r for r in report['per_arm'] if r['arm'] == 'adapted_virtual_biotech')
        simple = next(r for r in report['per_arm'] if r['arm'] == 'asof')
        self.assertGreater(adapted['calls'], simple['calls'])
        self.assertGreater(simple['counts']['unreviewed_unknown'], 0)
        self.assertEqual(simple['counts']['selected_claims'], simple['counts']['exact_normalized_copies'])


@unittest.skipUnless(importlib.util.find_spec('pyarrow'), 'install the ingest extra for source-audit tests')
class OriginalSelectedRowAuditTests(unittest.TestCase):
    """Real receipt, mapping, normalization and Parquet path; invented sources."""
    from tests.test_v02_ingest import IngestTests as _Fixture
    setUp = _Fixture.setUp
    tearDown = _Fixture.tearDown
    save_manifest = _Fixture.save_manifest
    receipt = _Fixture.receipt
    evidence = _Fixture.evidence

    def prepare_predictions(self):
        from asof.ingest import build_snapshot
        from tools.science.role_backend import RoleSelectionBackend
        from asof.workflow import Budget
        from tests.test_v02_ingest import GENES
        from tests.test_science_comparison_workflow import NativeFixture, synthetic_policy
        from tools.science.comparison_workflow import ARMS, run_case, verify_case
        from tools.science.run_comparison import pin, selected_store
        self.evidence([dict(self.rows[0], id='selected-genetic'),
                       dict(self.rows[0], id='selected-literature', datatypeId='literature'),
                       dict(self.rows[0], id='unselected-genetic')])
        case_pack = self.root/'cases.json'
        write_json(case_pack, {'schema_version': 1, 'cases': [{'symbol': 'CD276', 'disease_id': 'EFO_0003060',
            'intended_action': 'inhibit', 'modality': 'antibody', 'tissue': None,
            'target_id': GENES['CD276'], 'hgnc_id': 'HGNC:fictional-0'}]})
        bundle = self.root/'bundle'
        build = build_snapshot(self.manifest, self.catalog, bundle, cases_path=case_pack,
                               cases_sha256=sha256_file(case_pack), packet_layout='bounded')
        self.case_folder = bundle/build['cases'][0]['case_id']
        self.case = decode(Case, read_json(self.case_folder/'case.json'))
        full = load_snapshot(self.case_folder/'snapshot.json', self.case, self.catalog)
        self.store, selection = selected_store(self.case, full)
        folder = self.root/'predictions'; folder.mkdir()
        self.config = {'schema_version': 1, 'endpoint': 'http://127.0.0.1:55581', 'model_id': 'synthetic-only',
            'model_provenance': {'weights_sha256': {'fixture': 'a'*64}, 'runtime_sha256': 'b'*64},
            'retrieval': {'max_records': 12, 'max_request_bytes': 12000, 'wire_format': 'asof-shared-scientific-fields-v1'},
            'max_output_tokens': 256, 'timeout_seconds': 2, 'seed': 123}
        receipt = fixture_receipt(folder, self.config)
        config_path = folder/'model-config.json'; write_json(config_path, self.config)
        roles = synthetic_policy(); role_path = folder/'role-policy.json'; write_json(role_path, roles)
        plan = {'backend':{'selection_policy':'science7-prior-stage-output-schema-v1'},'root': str(folder.resolve()), 'arms': list(ARMS), 'code': fixture_code(folder), 'budget': encode(Budget(max_calls=50)),
            'execution_order': [{'case_id': self.case.case_id, 'arms': list(ARMS)}],
            'source_build': pin(bundle/'build-report.json'), 'catalog': pin(self.catalog), 'role_policy': pin(role_path),
            'candidate_world': {'maximum_total_observations_per_case': None, 'seed': None},
            'cases': [{'case_id': self.case.case_id, 'case': pin(self.case_folder/'case.json'),
                       'snapshot': pin(self.case_folder/'snapshot.json'), 'selection': selection,
                       'source_proofs': encode(full.source_proofs)}]}
        for name in ('protocol',):
            path = folder/(name+'.json'); write_json(path, {'synthetic_fixture': True}); plan[name] = pin(path)
        plan['model_receipt'] = receipt; plan['original_model_receipt'] = receipt
        plan_path = folder/'run-plan.json'; write_json(plan_path, plan)
        arms = []
        for arm in ARMS:
            backend = RoleSelectionBackend(config_path); backend.opener = NativeFixture()
            arm_path = folder/'arms'/self.case.case_id/arm
            result = run_case(self.case, self.store, backend, Budget(max_calls=50), arm, arm_path, roles)
            verification = verify_case(arm_path, self.case, self.store, self.config, roles)
            verification_path = arm_path.parent/(arm+'-verification.json'); write_json(verification_path, verification)
            arms.append({'arm': arm, 'path': str(arm_path.resolve()), 'result': pin(arm_path/'result.json'),
                'seal': pin(arm_path/'seal.json'), 'verification': pin(verification_path),
                'status': result['status'], 'calls': result['calls'], 'usage': result['usage']})
        self.case_rows = [{'case_id': self.case.case_id, 'arms': arms}]
        execution_path = folder/'execution-report.json'
        write_json(execution_path, {'status': 'all_paired_runs_verified', 'plan_sha256': sha256_file(plan_path),
            'server_stopped': True, 'owned_loopback_port_closed': True, 'cases': self.case_rows})
        self.seal_path = folder/'predictions-seal.json'
        write_json(self.seal_path, {'schema_version': 1, 'role': 'sealed_predictions_before_evaluator_join',
            'evaluator_answers_opened_by_launcher': False, 'clinical_probabilities': None,
            'plan': pin(plan_path), 'execution_report': pin(execution_path), 'cases': self.case_rows,
            'execution_proofs': fixture_launcher(folder, plan_path, self.case_rows, receipt)})
        references = self.root/'references.json'; self.reference_path = references
        write_json(references, {'schema_version': 1, 'role': 'evaluation_only', 'references': []})
        self.seal_hash = sha256_file(self.seal_path)
        # Only fixed-ten production plan validation and a real model receipt are
        # substituted. Source admission and all six workflow verifiers execute.
        with patch('tools.science.run_comparison.validate_plan'), \
             patch('tools.science.comparison_evaluation._expected_config', return_value=self.config):
            evaluate(self.seal_path, self.seal_hash, references, sha256_file(references), self.root/'evaluation')
        self.evaluation_path = self.root/'evaluation/report.json'

    def run_audit(self, name='audit'):
        with patch('tools.science.run_comparison.validate_plan'), \
             patch('tools.science.comparison_evaluation._expected_config', return_value=self.config):
            return audit_selected_rows(self.seal_path, self.seal_hash, self.evaluation_path,
                                      sha256_file(self.evaluation_path), self.root/name)

    def test_full_postseal_audit_reads_only_final_selections_from_original_rows(self):
        self.prepare_predictions()
        report = self.run_audit()
        rows = read_json(self.root/'audit/original-row-audits.json')
        asof = next(arm for arm in self.case_rows[0]['arms'] if arm['arm'] == 'asof')
        selected_ids = {claim['observation_id'] for claim in read_json(Path(asof['result']['path']))['claims']}
        self.assertEqual(2, report['audited_rows'])
        self.assertEqual(selected_ids, {row['observation_id'] for row in rows})
        self.assertTrue(all(row['technical_result'] == 'passed' for row in rows))
        self.assertTrue(all('species' in row['missingness'] for row in rows))
        self.assertEqual(4, report['source_files_hashed'])
        self.assertEqual(0, report['new_AI_reference_answers'])
        self.assertTrue(all(row['receipt_sha256'] for row in report['source_proofs']))
        self.assertEqual(4, len(report['evaluation_code']))
        sealed_paths = {row['path'] for row in read_json(self.root/'audit/seal.json')['files']}
        self.assertTrue(all(row['archive']['path'] in sealed_paths for row in report['evaluation_code']))
        self.assertIsNone(report['clinical_metrics'])
        with self.assertRaises(FileExistsError): self.run_audit()

    def test_audit_rejects_report_membership_selected_scope_receipt_and_raw_drift(self):
        self.prepare_predictions()
        original = read_json(self.evaluation_path)
        for number, mutation in enumerate(('duplicate', 'missing', 'selection', 'hypothesis')):
            changed = deepcopy(original)
            if mutation == 'duplicate': changed['per_case_arm'].append(deepcopy(changed['per_case_arm'][0]))
            if mutation == 'missing': changed['per_case_arm'].pop()
            asof = next(row for row in changed['per_case_arm'] if row['arm'] == 'asof')
            if mutation == 'selection': asof['claims'] = []
            if mutation == 'hypothesis': asof['hypothesis_sha256'] = 'a'*64
            write_json(self.evaluation_path, changed)
            with self.subTest(mutation=mutation), self.assertRaises(ContractError): self.run_audit(f'reject-{number}')
        write_json(self.evaluation_path, original)
        snapshot = read_json(self.case_folder/'snapshot.json')
        source = next(row for row in snapshot['sources'] if row['dataset_id'] == 'ot_evidence')
        receipt = Path(snapshot['raw_root'])/source['receipt_path']
        receipt_bytes = receipt.read_bytes(); receipt.write_bytes(receipt_bytes+b' ')
        with self.assertRaises(ContractError): self.run_audit('receipt-drift')
        receipt.write_bytes(receipt_bytes)
        raw = Path(snapshot['raw_root'])/source['path']; raw.write_bytes(raw.read_bytes()+b' ')
        with self.assertRaises(ContractError): self.run_audit('raw-drift')

    def test_late_case_snapshot_raw_receipt_and_parsed_reference_drift_cannot_complete(self):
        self.prepare_predictions()
        snapshot = read_json(self.case_folder/'snapshot.json')
        raw = next(row for row in snapshot['sources'] if row['dataset_id'] == 'ot_evidence')
        targets = [self.case_folder/'case.json', self.case_folder/'snapshot.json',
                   Path(snapshot['raw_root'])/raw['path'], Path(snapshot['raw_root'])/raw['receipt_path'],
                   self.reference_path,
                   self.seal_path.parent/'arms'/self.case.case_id/'asof/backend-execution.json',
                   self.seal_path.parent/'arms'/self.case.case_id/'asof/journal.jsonl',
                   self.seal_path.parent/'arms'/self.case.case_id/'asof/executed-source.py',
                   self.seal_path.parent/'executed-code/tools/science/comparison_workflow.py',
                   self.seal_path.parent/'invented-model/fixture.gguf',
                   self.seal_path.parent/'arms'/self.case.case_id/'asof/unexpected-late-file.json']
        reference_hash = sha256_file(self.reference_path)
        for number, target in enumerate(targets):
            original = target.read_bytes() if target.exists() else None
            def mutate_after_answer_read(path, expected, size=None):
                value = _read_pinned(path, expected, size)
                if Path(path) == self.reference_path:
                    target.write_bytes((original or b'')+b' ')
                return value
            with self.subTest(target=target.name), \
                 patch('tools.science.run_comparison.validate_plan'), \
                 patch('tools.science.comparison_evaluation._expected_config', return_value=self.config), \
                 patch('tools.science.comparison_evaluation._read_pinned', side_effect=mutate_after_answer_read):
                with self.assertRaises(ContractError):
                    evaluate(self.seal_path, self.seal_hash, self.reference_path, reference_hash,
                             self.root/f'late-drift-{number}')
            self.assertFalse((self.root/f'late-drift-{number}'/'report.json').exists())
            if original is None: target.unlink()
            else: target.write_bytes(original)

    def test_trusted_launcher_proofs_model_bytes_and_PID_fail_before_answers(self):
        from asof.journal import read_chain
        from tools.science.run_comparison import pin
        self.prepare_predictions()
        original_seal = read_json(self.seal_path)
        folder = self.seal_path.parent
        command_path, execution_path = folder/'server-command.json', folder/'execution/journal.jsonl'
        original_command, original_events = command_path.read_bytes(), execution_path.read_bytes()
        weight = folder/'invented-model/fixture.gguf'; original_weight = weight.read_bytes()
        reference_hash = sha256_file(self.reference_path)
        for index, mutation in enumerate(('missing_proof', 'remote_host', 'PID', 'model_byte', 'not_offline', 'stage')):
            seal = deepcopy(original_seal)
            if mutation == 'missing_proof': seal['execution_proofs'].pop('native_stdout')
            if mutation in ('remote_host', 'not_offline'):
                command = read_json(command_path)
                if mutation == 'remote_host': command['argv'][command['argv'].index('--host')+1] = '0.0.0.0'
                else: command['argv'].remove('--offline')
                write_json(command_path, command); seal['execution_proofs']['server_command'] = pin(command_path)
            if mutation in ('PID', 'stage'):
                events = [encode(event) for event in read_chain(execution_path)]
                if mutation == 'stage': events[4], events[5] = events[5], events[4]
                previous = None
                for sequence, event in enumerate(events):
                    if mutation == 'PID' and event['event'] == 'server_ready': event['details']['pid'] = 456
                    event['sequence'] = sequence
                    event.pop('sha256'); event['previous_sha256'] = previous
                    event['sha256'] = fingerprint(event); previous = event['sha256']
                execution_path.write_bytes(b''.join(canonical(event)+b'\n' for event in events))
                seal['execution_proofs']['execution_journal'] = pin(execution_path)
            if mutation == 'model_byte': weight.write_bytes(original_weight+b' ')
            write_json(self.seal_path, seal)
            with self.subTest(mutation=mutation), patch('tools.science.run_comparison.validate_plan'), \
                 patch('tools.science.comparison_evaluation._expected_config', return_value=self.config), \
                 patch('tools.science.comparison_evaluation._read_pinned', wraps=_read_pinned) as opened:
                with self.assertRaises(ContractError):
                    evaluate(self.seal_path, sha256_file(self.seal_path), self.reference_path,
                             reference_hash, self.root/f'launcher-reject-{index}')
            self.assertNotIn(str(self.reference_path), [str(call.args[0]) for call in opened.call_args_list])
            command_path.write_bytes(original_command); execution_path.write_bytes(original_events)
            weight.write_bytes(original_weight); write_json(self.seal_path, original_seal)


if __name__ == '__main__':
    unittest.main()
