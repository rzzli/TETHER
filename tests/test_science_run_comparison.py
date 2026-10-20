"""Launcher contract and ownership checks using synthetic files and mock processes."""
from copy import deepcopy
from contextlib import contextmanager, ExitStack
from dataclasses import replace
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

from asof.chrono import load_snapshot
from asof.contracts import Case, Category, EvidenceStatus
from asof.serde import ContractError, decode, encode, fingerprint, read_json, sha256_file, write_json
from asof.workflow import Budget
from asof.journal import RunJournal, read_chain
from tools.science import run_comparison as launcher


ROOT = Path(__file__).resolve().parents[1]


class RunComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def plan_fixture(self):
        output = self.root/'runs'/'comparison'; output.mkdir(parents=True)
        bundle = self.root/'data'/'derived'/'source'; bundle.mkdir(parents=True)
        receipt = self.root/'receipt.json'; write_json(receipt, {'fixture': 'no native assets'})
        shutil.copyfile(receipt, output/'model-acquisition.json')
        write_json(output/'catalog-policy.json', {'fixture': 'catalog'})
        write_json(output/'role-policy.json', {'fixture': 'policy'})
        arms = ['asof', 'adapted_virtual_biotech', 'lexical', 'provider_score', 'no_literature', 'no_perturbation']
        protocol = {'protocol_id': 'science7-matched-source-bounded-t6-v0.1', 'source_bundle': 'data/derived/source',
            'arms': arms, 'budget_per_case_per_arm': encode(Budget()),
            'candidate_world': {'maximum_total_observations_per_case': None, 'seed': None},
            'local_backend': {'acquisition_receipt_sha256': sha256_file(receipt)}}
        cases = []
        for index in range(10):
            identity = 'fixture-' + str(index)
            directory = bundle/identity; directory.mkdir()
            write_json(directory/'case.json', {'case_id': identity})
            write_json(directory/'snapshot.json', {'fixture': identity})
            cases.append({'case_id': identity, 'case': launcher.pin(directory/'case.json'),
                'snapshot': launcher.pin(directory/'snapshot.json'), 'selection': {}, 'source_proofs': []})
        write_json(bundle/'build-report.json', {'cases': [{'case_id': row['case_id']} for row in cases]})
        protocol['source_build_report_sha256'] = sha256_file(bundle/'build-report.json')
        protocol_path = self.root/'protocol.json'; write_json(protocol_path, protocol)
        source = self.root/'engine.py'; source.write_text('# synthetic fixture\n')
        archive = output/'executed-code'/'engine.py'; archive.parent.mkdir()
        shutil.copyfile(source, archive)
        plan = {'schema_version': 1, 'root': str(output), 'provider_spend_usd': 0, 'evaluator_inputs_opened': False,
            'protocol': launcher.pin(protocol_path), 'source_build': launcher.pin(bundle/'build-report.json'),
            'catalog': launcher.pin(output/'catalog-policy.json'), 'role_policy': launcher.pin(output/'role-policy.json'),
            'model_receipt': launcher.pin(output/'model-acquisition.json'), 'original_model_receipt': launcher.pin(receipt),
            'arms': arms, 'budget': protocol['budget_per_case_per_arm'], 'backend': protocol['local_backend'],
            'candidate_world': protocol['candidate_world'], 'cases': cases, 'code': [launcher.pin(source)]}
        plan['execution_order'] = [{'case_id': row['case_id'], 'arms': arms[i % len(arms):]+arms[:i % len(arms)]}
                                   for i, row in enumerate(cases)]
        return plan, output

    def validate(self, plan):
        with patch.object(launcher, 'ROOT', self.root), patch.object(launcher, 'CODE_FILES', ('engine.py',)):
            return launcher.validate_plan(plan)

    def test_valid_synthetic_plan_binds_complete_fixed_recipe(self):
        plan, _ = self.plan_fixture()
        self.assertEqual(self.validate(plan), {'status': 'plan_valid', 'cases': 10, 'arms': 6})

    def test_plan_recipe_boundary_and_membership_changes_rejected(self):
        plan, _ = self.plan_fixture()
        mutations = [lambda p: p.update(evaluator_inputs_opened=True), lambda p: p.update(provider_spend_usd=1),
            lambda p: p.update(arms=p['arms'][:-1]), lambda p: p['budget'].update(max_calls=17),
            lambda p: p['candidate_world'].update(seed=7), lambda p: p['backend'].update(seed=7),
            lambda p: p['cases'].reverse(), lambda p: p['cases'].__setitem__(1, deepcopy(p['cases'][0])),
            lambda p: p['execution_order'][0]['arms'].reverse(), lambda p: p['execution_order'].reverse()]
        for mutate in mutations:
            changed = deepcopy(plan); mutate(changed)
            with self.subTest(change=repr(mutate)), self.assertRaises(ContractError):
                self.validate(changed)

    def test_plan_requires_exact_source_paths_and_local_manifest_paths(self):
        plan, output = self.plan_fixture()
        alternate = output/'substitute.json'; write_json(alternate, {'substitute': True})
        for field in ('catalog', 'role_policy', 'model_receipt', 'source_build'):
            changed = deepcopy(plan); changed[field] = launcher.pin(alternate)
            with self.subTest(field=field), self.assertRaises(ContractError): self.validate(changed)
        changed = deepcopy(plan); changed['cases'][0]['case'] = launcher.pin(alternate)
        with self.assertRaises(ContractError): self.validate(changed)

    def test_unsafe_output_and_mutated_source_or_code_archive_rejected(self):
        plan, output = self.plan_fixture()
        changed = deepcopy(plan); changed['root'] = str(self.root/'outside')
        with self.assertRaises(ContractError): self.validate(changed)
        (output/'executed-code'/'engine.py').write_text('# rewritten archive\n')
        with self.assertRaises(ContractError): self.validate(plan)
        with self.assertRaises(ContractError): launcher.prepare(self.root/'outside')
        self.assertFalse((self.root/'outside').exists())

    def test_check_pin_rejects_digest_size_and_missing_file(self):
        path = self.root/'payload'; path.write_bytes(b'approved')
        pin = launcher.pin(path)
        self.assertEqual(launcher.check_pin(pin), path)
        path.write_bytes(b'mutation')
        with self.assertRaises(ContractError): launcher.check_pin(pin)
        pin = launcher.pin(path); pin['bytes'] += 1
        with self.assertRaises(ContractError): launcher.check_pin(pin)
        path.unlink()
        with self.assertRaises(ContractError): launcher.check_pin(pin)

    def fixture_store(self):
        directory = self.root/'source-fixture'
        shutil.copytree(ROOT/'src/asof/demo/v2', directory)
        packet = read_json(directory/'evidence.json')
        for row in packet['observations']: row['features'] = {}
        write_json(directory/'evidence.json', packet)
        snapshot = read_json(directory/'snapshot.json')
        snapshot['artifacts'][0]['sha256'] = sha256_file(directory/'evidence.json')
        write_json(directory/'snapshot.json', snapshot)
        case = replace(decode(Case, read_json(directory/'case.json')), task='T6', endpoint=None)
        return case, load_snapshot(directory/'snapshot.json', case)

    def test_source_world_is_all_observed_rows_with_nonobserved_states_retained(self):
        case, full = self.fixture_store()
        original = tuple(r for category in Category for r in full.query(case, category))
        before = fingerprint(original)
        selected, manifest = launcher.selected_store(case, full)
        expected = [r for category in Category for r in full.query(case, category)
                    if r.observation.status == EvidenceStatus.OBSERVED]
        self.assertEqual(manifest['candidate_ids'], sorted(r.observation.observation_id for r in expected))
        self.assertEqual(manifest['full_admitted_observed'], manifest['selected_observed'])
        self.assertEqual(fingerprint(tuple(r for category in Category for r in full.query(case, category))), before)
        self.assertEqual(tuple(r for category in Category for r in selected.query(case, category)), original)
        for maximum, seed in ((5, None), (None, 1), (5, 1)):
            with self.assertRaises(ContractError): launcher.selected_store(case, full, maximum, seed)

    def test_nonempty_prediction_features_never_enter_real_candidate_world(self):
        from asof.chrono import EvidenceStore
        case, full = self.fixture_store()
        row = next(r for category in Category for r in full.query(case, category)
                   if r.observation.status == EvidenceStatus.OBSERVED)
        changed = replace(row, observation=replace(row.observation, features={'leaked': 0.8}))
        modified = EvidenceStore(full.snapshot, (changed,), (), full.source_proofs, full.catalog_policy)
        with self.assertRaises(ContractError): launcher.selected_store(case, modified)

    def test_plan_fingerprint_failure_occurs_before_execution_reservation(self):
        plan, output = self.plan_fixture()
        plan_path = output/'run-plan.json'; write_json(plan_path, plan)
        with self.assertRaises(ContractError): launcher.execute(plan_path, 'f'*64)
        self.assertFalse((output/'execution').exists())

    def test_case_reload_binds_source_proofs_and_complete_candidate_identity(self):
        case, full = self.fixture_store()
        case_path = self.root/'source-fixture'/'case.json'; write_json(case_path, encode(case))
        _, selection = launcher.selected_store(case, full)
        row = {'case_id': case.case_id, 'case': launcher.pin(case_path),
            'snapshot': launcher.pin(self.root/'source-fixture'/'snapshot.json'),
            'source_proofs': encode(full.source_proofs), 'selection': selection}
        plan = {'catalog': {'path': str(self.root/'catalog.json')},
                'candidate_world': {'maximum_total_observations_per_case': None, 'seed': None}}
        with patch.object(launcher, 'load_snapshot', return_value=full):
            reloaded, _ = launcher._load_case(plan, row)
            self.assertEqual(reloaded, case)
            changed = deepcopy(row); changed['source_proofs'].append({'unapproved': 'evaluator-source'})
            with self.assertRaisesRegex(ContractError, 'source proof'): launcher._load_case(plan, changed)
            changed = deepcopy(row); changed['selection']['candidate_ids'].pop()
            with self.assertRaisesRegex(ContractError, 'candidate world'): launcher._load_case(plan, changed)
            case_path.write_text('{}')
            with self.assertRaisesRegex(ContractError, 'pinned bytes'): launcher._load_case(plan, row)

    def test_case_reload_rejects_same_id_source_content_substitution(self):
        from asof.chrono import EvidenceStore
        case, full = self.fixture_store()
        case_path = self.root/'source-fixture'/'case.json'; write_json(case_path, encode(case))
        _, selection = launcher.selected_store(case, full)
        row = {'case_id': case.case_id, 'case': launcher.pin(case_path),
            'snapshot': launcher.pin(self.root/'source-fixture'/'snapshot.json'),
            'source_proofs': encode(full.source_proofs), 'selection': selection}
        plan = {'catalog': {'path': str(self.root/'catalog.json')},
                'candidate_world': {'maximum_total_observations_per_case': None, 'seed': None}}
        records = tuple(r for category in Category for r in full.query(case, category))
        index = next(i for i, r in enumerate(records) if r.observation.status == EvidenceStatus.OBSERVED)
        source = records[index]
        substitutions = [
            replace(source, observation=replace(source.observation, statement='substituted source statement')),
            replace(source, observation=replace(source.observation,
                context=replace(source.observation.context, species='substituted species'))),
            replace(source, citation=replace(source.citation, artifact_sha256='f'*64)),
            replace(source, observation=replace(source.observation, missingness={'study_scope':'unavailable'}))]
        for changed in substitutions:
            with self.subTest(content=fingerprint(changed)):
                mutated = records[:index] + (changed,) + records[index+1:]
                store = EvidenceStore(full.snapshot, mutated, full.exclusions, full.source_proofs, full.catalog_policy)
                store.snapshot_base = full.snapshot_base
                with patch.object(launcher, 'load_snapshot', return_value=store):
                    with self.assertRaisesRegex(ContractError, 'candidate world'):
                        launcher._load_case(plan, row)

    def test_model_verification_detects_changed_weights_and_native_runtime(self):
        model_root = self.root/'model'; runtime = model_root/'runtime'; runtime.mkdir(parents=True)
        server = runtime/'llama-server.exe'; server.write_bytes(b'synthetic native bytes')
        weights = model_root/'weights.gguf'; weights.write_bytes(b'synthetic weight bytes')
        receipt = {'root': str(model_root), 'items': [{'name': 'weights.gguf', 'bytes': weights.stat().st_size,
                    'sha256': sha256_file(weights)}],
            'runtime_files': [{'path': 'runtime/llama-server.exe', 'sha256': sha256_file(server)}]}
        self.assertEqual(launcher.verify_model(receipt), (server, weights))
        weights.write_bytes(b'changed weights')
        with self.assertRaises(ContractError): launcher.verify_model(receipt)
        weights.write_bytes(b'synthetic weight bytes'); server.write_bytes(b'changed native bytes')
        with self.assertRaises(ContractError): launcher.verify_model(receipt)

    def test_listener_ownership_failure_stops_only_owned_process_and_forbids_repeat(self):
        plan, output = self.plan_fixture()
        plan_path = output/'run-plan.json'; write_json(plan_path, plan)
        server = self.root/'llama-server.exe'; server.write_bytes(b'synthetic not executable')
        model = self.root/'model.gguf'; model.write_bytes(b'synthetic not weights')
        process = Mock(pid=123456)
        process.poll.side_effect = lambda: 0 if process.terminate.called else None
        health = io.BytesIO(b'{}'); health.status = 200
        opener = Mock(); opener.open.return_value = health
        with patch.object(launcher, 'ROOT', self.root), patch.object(launcher, 'CODE_FILES', ('engine.py',)), \
             patch.object(launcher, 'verify_model', return_value=(server, model)), \
             patch.object(launcher.socket, 'socket'), patch.object(launcher.subprocess, 'Popen', return_value=process) as popen, \
             patch.object(launcher.urllib.request, 'build_opener', return_value=opener), \
             patch.object(launcher, '_owned_listener', return_value=False), patch.object(launcher, 'port_closed', return_value=True), \
             patch.object(launcher, 'peak_memory_bytes', return_value=0):
            with self.assertRaisesRegex(ContractError, 'ownership'): launcher.execute(plan_path, sha256_file(plan_path))
            self.assertEqual(popen.call_count, 1)
            argv = popen.call_args.args[0]
            self.assertIn('--offline', argv); self.assertIn('--no-webui', argv)
            self.assertEqual(argv[argv.index('--host')+1], '127.0.0.1')
            process.terminate.assert_called_once(); process.wait.assert_called_once()
            self.assertEqual(read_json(output/'execution-report.json')['status'], 'failed')
            self.assertFalse((output/'predictions-seal.json').exists())
            with self.assertRaises(FileExistsError): launcher.execute(plan_path, sha256_file(plan_path))
            self.assertEqual(popen.call_count, 1)

    @contextmanager
    def synthetic_execution(self, first_status='completed'):
        """Exercise launcher control flow with no subprocess, HTTP request or inference."""
        from tools.science import comparison_workflow as engine
        plan, output = self.plan_fixture()
        plan['backend'] = {'retrieval': {'max_records': 12, 'max_request_bytes': 12000,
            'wire_format': 'asof-shared-scientific-fields-v1'}, 'max_output_tokens': 256,
            'timeout_seconds': 2, 'seed': 123}
        plan['execution_order'] = [{'case_id': plan['cases'][0]['case_id'], 'arms': ['asof', 'lexical']}]
        write_json(output/'model-acquisition.json', {'revision': 'synthetic-only', 'items': []})
        plan['model_receipt'] = launcher.pin(output/'model-acquisition.json')
        plan_path = output/'run-plan.json'; write_json(plan_path, plan)
        preparation = RunJournal(output/'prepare', kind='build')
        preparation.append('plan_frozen', plan_sha256=sha256_file(plan_path)); preparation.close()
        case, store = self.fixture_store()
        server = self.root/'server.exe'; server.write_bytes(b'nonexecutable synthetic runtime')
        model = self.root/'weights.gguf'; model.write_bytes(b'synthetic nonmodel bytes')
        process = Mock(pid=123456)
        process.poll.side_effect = lambda: 0 if process.terminate.called else None
        health = io.BytesIO(b'{}'); health.status = 200
        opener = Mock(); opener.open.return_value = health

        def arm_result(case, store, backend, budget, arm, folder, role_policy):
            folder.mkdir(parents=True)
            result = {'arm': arm, 'status': first_status if arm == 'asof' else 'completed',
                'features': {}, 'probability': None, 'claims': [], 'calls': 0,
                'usage': {'input_tokens': 0, 'output_tokens': 0, 'cost_usd': 0}}
            write_json(folder/'result.json', result); write_json(folder/'seal.json', {'synthetic': True})
            return result

        with ExitStack() as stack:
            for target, name, value in [
                (launcher, 'validate_plan', Mock(return_value={'status': 'plan_valid'})),
                (launcher, 'verify_model', Mock(return_value=(server, model))),
                (launcher, '_load_case', Mock(return_value=(case, store))),
                (launcher, 'LocalSelectionBackend', Mock()),
                (launcher, '_owned_listener', Mock(return_value=True)),
                (launcher, 'port_closed', Mock(return_value=True)),
                (launcher, 'peak_memory_bytes', Mock(return_value=0)),
                (launcher.socket, 'socket', MagicMock()),
                (launcher.subprocess, 'Popen', Mock(return_value=process)),
                (launcher.urllib.request, 'build_opener', Mock(return_value=opener)),
                (engine, 'verify_case', Mock(return_value={'status': 'verified'})),
                (engine, 'run_case', Mock(side_effect=arm_result))]:
                stack.enter_context(patch.object(target, name, value))
            yield plan_path, output, engine.run_case, process

    def test_success_seal_binds_all_six_execution_files_after_shutdown(self):
        with self.synthetic_execution(first_status='budget_exhausted') as (plan_path, output, run, process):
            report = launcher.execute(plan_path, sha256_file(plan_path))
            self.assertEqual(report['status'], 'all_paired_runs_verified')
            self.assertEqual(run.call_count, 2)
            process.terminate.assert_called_once(); process.wait.assert_called_once()
            seal = read_json(output/'predictions-seal.json')
            expected = {'execution_journal': 'execution/journal.jsonl', 'server_command': 'server-command.json',
                'model_config': 'model-config.json', 'native_stdout': 'server.stdout.log',
                'native_stderr': 'server.stderr.log', 'preparation_journal': 'prepare/journal.jsonl'}
            self.assertEqual(set(seal['execution_proofs']), set(expected))
            for name, relative in expected.items():
                proof = seal['execution_proofs'][name]
                self.assertEqual(Path(proof['path']), output/relative)
                self.assertTrue(Path(proof['path']).is_absolute())
                self.assertEqual(launcher.check_pin(proof), output/relative)
                self.assertEqual(proof, launcher.pin(output/relative))
            events = read_chain(Path(seal['execution_proofs']['execution_journal']['path']))
            self.assertEqual(events[-1]['event'], 'execution_terminal')
            self.assertTrue(events[-1]['details']['server_stopped'])
            stdout = output/'server.stdout.log'; stdout.write_bytes(b'changed after seal')
            with self.assertRaisesRegex(ContractError, 'pinned bytes'):
                launcher.check_pin(seal['execution_proofs']['native_stdout'])

    def test_failed_or_interrupted_arm_stops_before_any_next_dispatch(self):
        parent = self.root
        for status in ('failed', 'interrupted'):
            self.root = parent/status; self.root.mkdir()
            with self.subTest(status=status), self.synthetic_execution(status) as (plan_path, output, run, process):
                with self.assertRaisesRegex(ContractError, 'Comparison arm '+status):
                    launcher.execute(plan_path, sha256_file(plan_path))
                self.assertEqual(run.call_count, 1)
                process.terminate.assert_called_once()
                report = read_json(output/'execution-report.json')
                self.assertEqual(report['status'], 'failed')
                self.assertEqual(report['cases'][0]['arms'][0]['status'], status)
                events = read_chain(output/'execution/journal.jsonl')
                self.assertEqual(sum(e['event'] == 'arm_started' for e in events), 1)
                self.assertTrue(any(e['event'] == 'arm_terminal_failure' for e in events))
                self.assertFalse((output/'predictions-seal.json').exists())
                with self.assertRaises(FileExistsError): launcher.execute(plan_path, sha256_file(plan_path))
                self.assertEqual(run.call_count, 1)
        self.root = parent

    def test_prediction_seal_helper_requires_complete_proof_inventory_and_terminal_success(self):
        output = self.root/'seal-fixture'; output.mkdir()
        plan = output/'run-plan.json'; write_json(plan, {'synthetic': True})
        report = {'status': 'all_paired_runs_verified', 'server_stopped': True, 'cases': []}
        write_json(output/'execution-report.json', report)
        for relative in launcher.EXECUTION_PROOF_FILES.values():
            file = output/relative; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(b'fixture')
        for changes in ({'status': 'failed'}, {'server_stopped': False}):
            with self.assertRaises(ContractError): launcher._write_predictions_seal(output, plan, report | changes)
        self.assertFalse((output/'predictions-seal.json').exists())
        (output/'prepare/journal.jsonl').unlink()
        with self.assertRaises(FileNotFoundError): launcher._write_predictions_seal(output, plan, report)
        self.assertFalse((output/'predictions-seal.json').exists())


if __name__ == '__main__':
    unittest.main()
