"""Unscored fictional units for independent policy/outer envelope validation.

These construct data directly; they do not inspect corpus oracles or invoke
TETHER/tether_engine, a model, a server, or either paired-comparison runner.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.equal_policy import cases, policy_cases
from experiments.equal_policy import independent_policy as policy
from experiments.equal_policy.independent import PolicyError, validate_bundle
from tests.test_equal_policy_independent import fake_runtime


def write(path, value):
    payload = value if type(value) is bytes else policy.canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return policy.descriptor(path.name, payload)


def journal(items):
    result, previous = [], None
    for index, (event, details) in enumerate(items):
        value = dict(sequence=index, previous_sha256=previous, event=event,
                     at='2026-11-02T00:00:00+00:00', details=details)
        previous = policy.digest(value)
        result.append(policy.canonical(dict(value, sha256=previous)) + b'\n')
    return b''.join(result)


class IndependentPolicyUnits(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[2] / 'data/cache/independent-policy-unit'
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, unused=False):
        spec = dict(control_id='UNIT', operation='prepare_run', variant='artifact_policy_v2',
            preparation=dict(base='policy_t6', changes=[], after_seal=[],
                             recipe=dict(policy_recipe='none', omit_scorer=True)))
        bundle = self.root / 'bundle'
        request, _ = cases.write_source_bundle(bundle, spec)
        if unused:
            directory = bundle / 'input'
            snapshot = json.loads((directory / 'snapshot.json').read_bytes())
            node = copy.deepcopy(snapshot['sources'][0])
            node.update(source_id='unused-unit', path='unused-unit.json', receipt_path='unused-receipt.json',
                        source_url='https://fictional.invalid/unused-unit')
            payload = b'{"fictional":"unreferenced unit source"}\n'
            receipt = json.loads((directory / snapshot['sources'][0]['receipt_path']).read_bytes())
            receipt.update(receipt_id='unused-unit-receipt', relative_path=node['path'], url=node['source_url'],
                           sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
            write(directory / node['path'], payload); write(directory / node['receipt_path'], receipt)
            node['sha256'] = receipt['sha256']
            node['receipt_sha256'] = hashlib.sha256((directory / node['receipt_path']).read_bytes()).hexdigest()
            snapshot['sources'].append(node); write(directory / 'snapshot.json', snapshot)
        request, _ = policy_cases.prepare_policy_sources(bundle, spec, request)
        load = lambda key: json.loads((bundle / request['paths'][key]).read_bytes())
        scratch = self.root / 'scratch'; scratch.mkdir()
        return bundle, request, load, scratch

    def test_positive_preflight_retains_copies_without_modifying_sources(self):
        root, request, load, scratch = self.fixture()
        before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        result = validate_bundle(root, request, scratch_dir=scratch)
        self.assertEqual(result['decision'], 'accept', result)
        self.assertEqual(set(result['observables']), {'admitted_observation_ids', 'eligible_observation_ids', 'exclusions', 'scorer_preflight'})
        self.assertEqual(result['observables']['admitted_observation_ids'], ['obs-1'])
        self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()})
        record = json.loads((scratch / 'independent-policy/retention.json').read_bytes())
        self.assertGreaterEqual(record['source_rechecked'], 3)
        for name, proof in record['copies'].items():
            self.assertEqual(policy.descriptor(name, (scratch / 'independent-policy' / name).read_bytes()), proof)

    def test_no_scratch_reuse_and_no_scratch_inside_inputs(self):
        root, request, load, scratch = self.fixture()
        write(scratch / 'occupied', b'previous')
        self.assertEqual(validate_bundle(root, request, scratch_dir=scratch)['decision'], 'reject')
        inside = root / 'scratch'; inside.mkdir()
        self.assertEqual(validate_bundle(root, request, scratch_dir=inside)['decision'], 'reject')

    def test_dependency_cycle_and_overlap_are_rejected(self):
        _, _, load, _ = self.fixture()
        original = load('catalog_policy')
        for kind in ('cycle', 'overlap'):
            with self.subTest(kind=kind):
                value = copy.deepcopy(original)
                product = value['products'][0]
                product['input_dependencies'] = [product['dataset_id']]
                if kind == 'overlap': product['validation_dependencies'] = [product['dataset_id']]
                with self.assertRaises(PolicyError): policy.validate_document(value)

    def test_grant_closure_and_evaluator_roles_are_rejected(self):
        _, _, load, _ = self.fixture()
        original = load('catalog_policy')
        value = copy.deepcopy(original)
        value['uses'][0]['grants'] = [g for g in value['uses'][0]['grants'] if g['artifact_id'] != value['artifacts'][0]['artifact_id']]
        with self.assertRaises(PolicyError): policy.validate_document(value)
        value = copy.deepcopy(original)
        value['uses'][0]['grants'][0]['role'] = 'evaluation_only'
        with self.assertRaises(PolicyError): policy.validate_document(value)

    def test_frame_exact_inventory_and_roots_bind(self):
        _, request, load, _ = self.fixture()
        value, case, snapshot, roots = (load(k) for k in ('catalog_policy', 'case', 'snapshot', 'policy_roots'))
        use = request['options']['policy_use']; frame = request['anchors']['frame_sha256']
        with self.assertRaises(PolicyError): policy.bind(value, case, snapshot, policy.root_map(roots), use, '0' * 64)
        bad = copy.deepcopy(roots); bad['roots']['metadata'] = bad['roots']['raw']
        with self.assertRaises(PolicyError): policy.root_map(bad)
        bad = copy.deepcopy(value); bad['uses'][0]['grants'].append(copy.deepcopy(bad['uses'][0]['grants'][0]))
        with self.assertRaises(PolicyError): policy.bind(bad, case, snapshot, policy.root_map(roots), use, frame)

    def test_all_raw_receipt_relationships_and_alternate_basis(self):
        _, request, load, _ = self.fixture(unused=True)
        value, case, snapshot, roots = (load(k) for k in ('catalog_policy', 'case', 'snapshot', 'policy_roots'))
        decision, _, _, _ = policy.bind(value, case, snapshot, policy.root_map(roots), request['options']['policy_use'], request['anchors']['frame_sha256'])
        nodes = {n['source_id']: n for n in snapshot['sources']}
        for entry in decision['inventory']:
            if entry['receipt'] is None: continue
            node = nodes[entry['source_id']]
            receipt = json.loads((Path(roots['roots']['raw']) / entry['receipt']['relative_path']).read_bytes())
            policy.receipt_check(entry, node, policy.canonical(receipt))
            for field, changed in (('completed_at_utc', '2025-01-01T00:00:00Z'), ('url', 'https://fictional.invalid/different'), ('bytes', True)):
                with self.subTest(node=entry['source_id'], field=field):
                    wrong = {**receipt, field: changed}
                    with self.assertRaises(PolicyError): policy.receipt_check(entry, node, policy.canonical(wrong))
            changed_node = copy.deepcopy(node); changed_node['availability']['evidence_ref'] = 'a' * 64
            with self.assertRaises(PolicyError): policy.receipt_check(entry, changed_node, policy.canonical(receipt))
            later = {**receipt, 'completed_at_utc': '2025-01-01T00:00:00Z'}
            alternate = copy.deepcopy(node); alternate['availability']['basis'] = 'dated_original_release'
            alternate['availability']['evidence_ref'] = 'separately-retained-release-document'
            policy.receipt_check(entry, alternate, policy.canonical(later))

    def test_unreferenced_raw_future_receipt_rejects_preflight(self):
        root, request, load, scratch = self.fixture(unused=True)
        snapshot, document, roots = (load(k) for k in ('snapshot', 'catalog_policy', 'policy_roots'))
        node = next(n for n in snapshot['sources'] if n['source_id'] == 'unused-unit')
        path = Path(roots['roots']['raw']) / node['receipt_path']
        receipt = json.loads(path.read_bytes()); receipt['completed_at_utc'] = '2025-01-01T00:00:00Z'
        write(path, receipt); node['receipt_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        node['availability']['evidence_ref'] = node['receipt_sha256']
        artifact = next(a for a in document['artifacts'] if a['relative_path'] == node['path'])
        artifact['availability'] = copy.deepcopy(node['availability'])
        artifact['provenance']['receipt']['sha256'] = node['receipt_sha256']
        document['uses'][0]['snapshot_fingerprint'] = policy.digest(snapshot)
        write(root / request['paths']['snapshot'], snapshot); write(root / request['paths']['catalog_policy'], document)
        with patch.object(policy, 'prepare_core', side_effect=AssertionError('No subsequent admission after contradictory receipt')) as admission:
            result = validate_bundle(root, request, scratch_dir=scratch)
        self.assertEqual(result['decision'], 'reject', result)
        self.assertEqual(result['violated_obligations'], ['EP-POLICY-03'])
        admission.assert_not_called()

    def test_source_hash_and_provenance_bytes_are_checked(self):
        root, request, load, scratch = self.fixture()
        raw = Path(load('policy_roots')['roots']['raw']) / load('snapshot')['sources'][0]['path']
        raw.write_bytes(b'fictional change')
        result = validate_bundle(root, request, scratch_dir=scratch)
        self.assertEqual(result['decision'], 'reject', result)
        self.assertEqual(result['violated_obligations'], ['EP-POLICY-03'])

    def test_safe_bounded_stable_read_rejects_directory_overflow_and_bad_paths(self):
        path = self.root / 'x'; path.write_bytes(b'12345')
        with self.assertRaises(PolicyError): policy.stable(path, time.monotonic() + 5, 4)
        with self.assertRaises(PolicyError): policy.stable(self.root, time.monotonic() + 5)
        for name in ('../x', 'CON', 'x\\y', 'x:stream', 'x/./y'):
            with self.subTest(name=name), self.assertRaises(PolicyError): policy.relative(name)
        with self.assertRaises(PolicyError): policy.stable(path, time.monotonic() - 1)

    def test_process_limit_scalar_types(self):
        self.assertEqual(policy.validate_process_limits({})['timeout_seconds'], 3600)
        for value in ({'timeout_seconds': True}, {'max_output_bytes': True}, {'max_output_bytes': policy.NORMAL + 1}, {'timeout_seconds': 0}, {'timeout_seconds': float('nan')}):
            with self.subTest(value=value), self.assertRaises(PolicyError): policy.validate_process_limits(value)

    def test_stable_reader_rechecks_no_links_and_deadline_after_last_chunk(self):
        path = self.root / 'input'; path.write_bytes(b'unit')
        error = PolicyError('EP-IO-01', 'simulated post-read reparse')
        with patch.object(policy, 'no_links', side_effect=[path, error]), self.assertRaises(PolicyError):
            policy.stable(path, time.monotonic() + 5)
        with patch.object(policy.time, 'monotonic', side_effect=[0, 0, 10]), self.assertRaises(PolicyError):
            policy.stable(path, 5)


class IndependentOuterUnits(unittest.TestCase):
    setUp = IndependentPolicyUnits.setUp
    def outer(self):
        output = self.root / 'outer'; output.mkdir()
        limits = dict(timeout_seconds=10.0, max_output_bytes=1000)
        report = dict(schema_version=1, method='tether.process_envelope.v1', limits=limits,
            termination_reason='exited', execution_elapsed_seconds=1.0, total_elapsed_seconds=1.5,
            retained_stdout_bytes=2, retained_stderr_bytes=0, observed_stdout_bytes=2, observed_stderr_bytes=0,
            observed_counts_are_lower_bounds=False, pipe_eof=dict(stdout=True, stderr=True),
            process_started=True, process_reaped=True, cleanup_errors=[])
        common = dict(schema_version=1, method='tether.engine_presentation.v2', brand='TETHER', status='completed',
            role='evaluation_only', agent_visible=False, scientific_validation='not_established')
        trusted = fake_runtime(self.root)
        files = {'engine/dossier.md': b'# TETHER dossier: FICTIONAL\n', 'dossier.md': b'# TETHER dossier: FICTIONAL\n',
                 'engine/journal.jsonl': journal([('run_reserved', {})]), 'engine/trace.jsonl': b'{}\n',
                 'engine-stdout.txt': b'ok', 'engine-stderr.txt': b''}
        for name, value in files.items(): write(output / name, value)
        manifest = dict(common, command='run', invocation_sha256='b' * 64,
            engine=dict(path='engine', receipt_sha256='c' * 64),
            projection=dict(source='engine/dossier.md', target='dossier.md', transform='identity_dossier_v2'),
            launcher=trusted['launcher_proof'], artifacts={}, process_limits=limits, supervision=report, artifact_policy=None)
        self.seal_outer(output, manifest)
        return output, manifest, trusted

    def seal_outer(self, output, manifest, inventory=True):
        if inventory:
            manifest['artifacts'] = {p.relative_to(output).as_posix(): policy.descriptor(p.relative_to(output).as_posix(), p.read_bytes())
                for p in output.rglob('*') if p.is_file() and p.relative_to(output).as_posix() not in ('tether-manifest.json', 'tether-receipt.json', 'attempt/journal.jsonl')}
        raw = policy.canonical(manifest); manifest_sha = hashlib.sha256(raw).hexdigest(); write(output / 'tether-manifest.json', raw)
        trace = journal([('run_reserved', {}), ('tether_prepared', dict(command='run', launcher_proof_sha256=policy.digest(manifest['launcher']),
            process_limits=manifest['process_limits'], artifact_policy_requested=False)),
            ('engine_dispatch', dict(argv_sha256=manifest['invocation_sha256'], output='engine', process_limits=manifest['process_limits'])),
            ('engine_returned', dict(returncode=0, supervision=manifest['supervision'])),
            ('tether_completed', dict(manifest_sha256=manifest_sha, engine_receipt_sha256='c' * 64))])
        write(output / 'attempt/journal.jsonl', trace)
        common = {k: manifest[k] for k in ('schema_version', 'method', 'brand', 'status', 'role', 'agent_visible', 'scientific_validation')}
        write(output / 'tether-receipt.json', dict(common, manifest_sha256=manifest_sha,
            journal_sha256=hashlib.sha256(trace).hexdigest(), engine_receipt_sha256='c' * 64))

    def test_outer_success_uses_pinned_inner_identity_and_source_verifier(self):
        output, manifest, trusted = self.outer()
        inner = dict(semantic_consistency='verified', code_matches_current=True, status='completed')
        with patch.object(policy, 'verify_core', return_value=inner) as verify:
            result = policy.verify_outer(output, None, trusted)
        verify.assert_called_once_with(output / 'engine', 'c' * 64, trusted_runtime=trusted)
        self.assertEqual(result['verification']['source_binding'], 'current_originals')

    def test_outer_proof_checks_current_payload_inventory_and_distribution_each_call(self):
        output, manifest, trusted = self.outer()
        root = Path(trusted['runtime_paths']['tether_file']).parent
        original = (root / 'module.py').read_bytes()
        metadata = root.parent / 'tether_target_agents-0.6.0.dist-info/METADATA'
        original_metadata = metadata.read_bytes()
        inner = dict(semantic_consistency='verified', code_matches_current=True, status='completed')
        for mutation in ('content', 'add', 'remove', 'distribution'):
            with self.subTest(mutation=mutation), patch.object(policy, 'verify_core', return_value=inner):
                if mutation == 'content': (root / 'module.py').write_bytes(b'VALUE = 2\n')
                elif mutation == 'add': (root / 'extra.py').write_bytes(b'ADDED = True\n')
                elif mutation == 'remove': (root / 'module.py').unlink()
                else: metadata.write_bytes(original_metadata.replace(b'0.6.0', b'9.9.9'))
                with self.assertRaises(PolicyError): policy.verify_outer(output, None, trusted)
                (root / 'module.py').write_bytes(original); metadata.write_bytes(original_metadata)
                if (root / 'extra.py').exists(): (root / 'extra.py').unlink()
        # Comparison is to actual code, not merely the retained trusted proof.
        trusted['launcher_proof'] = {'historical': 'stale'}
        with patch.object(policy, 'verify_core', return_value=inner):
            self.assertEqual(policy.verify_outer(output, None, trusted)['verification']['status'], 'integrity_verified')

    def test_resealed_projection_and_process_count_rejected(self):
        output, manifest, trusted = self.outer()
        write(output / 'dossier.md', b'# TETHER dossier: changed\n')
        self.seal_outer(output, manifest)
        with self.assertRaises(PolicyError): policy.verify_outer(output, None, trusted)
        write(output / 'dossier.md', b'# TETHER dossier: FICTIONAL\n')
        manifest['supervision']['observed_stdout_bytes'] = 3
        self.seal_outer(output, manifest)
        with self.assertRaises(PolicyError): policy.verify_outer(output, None, trusted)

    def test_manifest_size_rejects_float_or_boolean_alias(self):
        output, manifest, trusted = self.outer()
        for value in (0.0, False):
            with self.subTest(value=value):
                manifest['artifacts']['engine-stderr.txt']['bytes'] = value
                self.seal_outer(output, manifest, inventory=False)
                with self.assertRaises(PolicyError): policy.verify_outer(output, None, trusted)

    def test_external_anchor_extra_directory_and_runtime_mismatch_rejected(self):
        output, manifest, trusted = self.outer()
        with self.assertRaises(PolicyError): policy.verify_outer(output, '0' * 64, trusted)
        (output / 'extra-empty').mkdir()
        with self.assertRaises(PolicyError): policy.verify_outer(output, None, trusted)
        (output / 'extra-empty').rmdir()
        with patch.object(policy, 'verify_core', return_value=dict(semantic_consistency='verified', code_matches_current=False, status='completed')):
            with self.assertRaises(PolicyError): policy.verify_outer(output, None, trusted)
        bad = {**trusted, 'schema_version': True}
        with self.assertRaises(PolicyError): policy.verify_outer(output, None, bad)

    def test_success_requires_strict_elapsed_bound_and_exact_stream_types(self):
        output, manifest, trusted = self.outer()
        report = manifest['supervision']; limits = manifest['process_limits']
        for key, value in (('execution_elapsed_seconds', 10), ('observed_stderr_bytes', False), ('process_reaped', False), ('total_elapsed_seconds', 0)):
            with self.subTest(key=key), self.assertRaises(PolicyError): policy.supervision({**report, key: value}, limits, 2, 0)

    def test_inspection_single_snapshot_preserves_unresolved_usage(self):
        output, manifest, trusted = self.outer()
        value = journal([('run_reserved', {}), ('dispatch', dict(attempt_id='pending', reserved=dict(input_tokens=10, output_tokens=5, cost_usd=0)))])
        write(output / 'engine/journal.jsonl', value + b'{partial')
        with patch.object(policy, 'stable', wraps=policy.stable) as reader:
            result = policy.inspect_outer(output)
        inner_calls = [x for x in reader.call_args_list if x.args[0] == output / 'engine/journal.jsonl']
        self.assertEqual(len(inner_calls), 1)
        self.assertEqual(result['engine']['unresolved_attempts'], ['pending'])
        self.assertEqual(result['engine']['estimated_upper_usage']['input_tokens'], 10)
        self.assertIn('never automatically repeat', result['recovery_action'])


if __name__ == '__main__':
    unittest.main()
