"""Fictional unit controls for the independent comparator (not benchmark scores)."""
from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.equal_policy import independent as iv
from experiments.equal_policy import independent_local as local
from experiments.equal_policy.independent_schema import PolicyError, decode


def availability(**changes):
    return dict(first_public_at='2019-01-01', release_public_at='2019-01-01', record_public_at='2019-01-01',
        annotation_public_at='2019-01-01', retrieved_at='2021-01-01', basis='dated_archive', uncertainty=None,
        known_public_by=None, evidence_ref=None) | changes


def case(**changes):
    return dict(schema_version=2, case_id='unit-case', task='T6', origin='2020-01-01', origin_at='2020-01-01T23:59:59.999999+00:00',
        hypothesis=dict(target_id='TARGET:X', indication_id='DISEASE:Y', target_namespace_version='targets-1',
            indication_namespace_version='diseases-1', intended_action='inhibit', modality='antibody', tissue=None,
            availability=availability()), program=None, endpoint=None) | changes


def observation(name='o1', **changes):
    return dict(observation_id=name, target_id='TARGET:X', indication_id='DISEASE:Y', program_id=None,
        category='genetics', source_kind='primary', statement='Fictional bounded observation.', status='observed',
        polarity='supports', mechanism_direction='uncertain', study_id='study-1', dependency_group='group-1',
        context=dict(species=None, ancestry=None, tissue=None, disease_state=None, intervention=None, comparator=None, cohort_ids=[]),
        quantitative=dict(effect=None, scale=None, standard_error=None, ci_lower=None, ci_upper=None, sample_size=None, adjusted_p_value=None),
        method=dict(code_id='fixture', version='1', parameters={}, qc_status='passed', limitations=[]),
        availability=availability(), features={}, feature_scope=None, input_refs=['raw'], computed_at=None,
        source_locator={}, source_metrics={}, missingness={}, publication_date=None, publication_year=None) | changes


def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))


def fake_runtime(root):
    """Fictional files only: importing these packages would deliberately fail."""
    site = root / 'fake-site-packages'
    for package, version in (('asof', '0.3.12'), ('tether', '0.5.1')):
        folder = site / package; folder.mkdir(parents=True)
        (folder / '__init__.py').write_text("__version__ = " + repr(version) + "\nraise AssertionError('must not import fixture')\n", encoding='utf-8')
        (folder / 'module.py').write_text('VALUE = 1\n', encoding='utf-8')
        dist = site / (package + '_target_agents-' + version + '.dist-info'); dist.mkdir()
        (dist / 'METADATA').write_text('Metadata-Version: 2.1\nName: ' + package + '-target-agents\nVersion: ' + version + '\n', encoding='utf-8')
    core = {p.name: iv.file_digest(p) for p in (site / 'asof').glob('*.py')}
    facade = {p.name: dict(path=p.name, sha256=iv.file_digest(p), bytes=p.stat().st_size) for p in (site / 'tether').glob('*.py')}
    proof = dict(schema_version=1, method='tether.launcher_code.v1', facade_version='0.5.1', core_version='0.3.12',
        installed_distributions={'tether-target-agents': '0.5.1', 'asof-target-agents': '0.3.12'}, code=facade)
    return dict(schema_version=1, versions=dict(tether='0.5.1', asof='0.3.12'), launcher_proof=proof,
        core_code_sha256=core, runtime_paths=dict(asof_file=str(site / 'asof/__init__.py'), tether_file=str(site / 'tether/__init__.py')))


def fixture(root, observations=None):
    c = case()
    raw = root / 'original.txt'
    raw.write_text('fictional original\n', encoding='utf-8')
    packet = root / 'evidence.json'
    write_json(packet, dict(schema_version=2, observations=observations or [observation()]))
    node = dict(source_id='raw', dataset_id='fictional', release_id='r1', path=raw.name,
        sha256=iv.file_digest(raw), role='reference', availability=availability(), temporal_classification='verified_historical',
        source_url='https://example.invalid/fictional', parents=[], computed_at=None, method_id=None, method_version=None,
        receipt_path=None, receipt_sha256=None)
    artifact = dict(artifact_id='packet', dataset_id='fictional', release_id='r1', path=packet.name,
        sha256=iv.file_digest(packet), role='agent_evidence', access_approved=True, temporal_classification='verified_historical',
        availability=availability(), source_url='https://example.invalid/packet', input_refs=['raw'])
    snapshot = dict(schema_version=2, snapshot_id='snapshot', profile='synthetic_demo', origin=c['origin'],
        origin_at=c['origin_at'], allow_reconstructed=False, artifacts=[artifact], sources=[node], raw_root=str(root), coverage={})
    return c, snapshot


def grounded(o):
    return dict(observation=o, citation=dict(artifact_id='p', dataset_id='d', release_id='r', artifact_sha256='0' * 64, source_url='x'))


def claim(o):
    return dict(evidence=grounded(o))


def scorer(**changes):
    return dict(schema_version=2, model_id='fixture-scorer', kind='synthetic_demo', feature_schema=iv.FEATURE_SCHEMA,
        aggregation=iv.AGGREGATION, endpoint='phase_1_to_2', horizon_months=24, phases=[1], modalities=['antibody'],
        intended_actions=['inhibit'], target_namespace_versions=['targets-1'], indication_namespace_versions=['diseases-1'],
        training_origin_max='2018-01-01', training_label_available_max='2019-01-01', calibration_label_available_max=None,
        training_manifest_sha256='a' * 64, calibration='none', intercept=0.0, coefficients={'genetic_support': 2.0},
        required_features=['genetic_support'], missing_values={}, minimum_coverage=1.0) | changes


def chain(events):
    result = []
    for kind, detail in events:
        row = dict(sequence=len(result), event=kind, details=detail,
                   previous_sha256=result[-1]['sha256'] if result else None)
        row['sha256'] = iv.digest(row)
        result.append(row)
    return result


def sealed_fixture(root):
    """Hand-built no-claim run; expected semantics are fully specified here."""
    c, snapshot = fixture(root)
    admitted = iv.admit(c, snapshot, root)
    budget = dict(max_calls=16, max_input_tokens=32000, max_output_tokens=8000, max_cost_usd=0.0, max_seconds=300.0, max_retries=1)
    config = dict(budget=budget, disabled=['genetics'], review_enabled=True, backend_id='offline-extractive-v1',
        backend_provenance=None, hypothesis_key=iv.hypothesis_key(c), scorer_preflight='dossier_audit_has_no_clinical_probability')
    plan = [dict(category=name, observed_records=int(name == 'genetics'), initial_status='disabled' if name == 'genetics' else 'no_observed_evidence')
            for name in iv.CATEGORIES]
    coverage = {row['category']: dict(status=row['initial_status'], available_observations=row['observed_records'],
        selected_observations=0, nonobserved=[], source_coverage={}) for row in plan}
    features = iv.build_features(c, [])
    predicted = iv.prediction(c, 'synthetic_demo', features, None)
    events = chain([('plan', dict(steps=plan, configuration=config, snapshot_id='snapshot')),
        ('finalize', dict(status='completed', feature_sha256=iv.digest(features), prediction_sha256=iv.digest(predicted)))])
    inputs = dict(case=c, snapshot=snapshot, scorer=None, catalog_policy=None, configuration=config, snapshot_base=str(root), environment={})
    run = dict(schema_version=2, case_id=c['case_id'], snapshot_id='snapshot', profile='synthetic_demo',
        backend_id='offline-extractive-v1', input_fingerprint=iv.digest(inputs), budget=budget, calls=0,
        status='completed', usage=iv._zero_usage(), measured_usage=iv._zero_usage(), estimated_usage=iv._zero_usage(),
        plan=plan, coverage=coverage, exclusions=[])
    target = root / 'sealed'
    target.mkdir()
    for filename, value in {'inputs.json': inputs, 'run.json': run, 'ledger.json': dict(schema_version=2, claims=[]),
                            'features.json': features, 'prediction.json': predicted}.items():
        write_json(target / filename, value)
    raw_chain = b''.join(iv.canonical(event) + b'\n' for event in events)
    (target / 'journal.jsonl').write_bytes(raw_chain)
    (target / 'trace.jsonl').write_bytes(raw_chain)
    from experiments.equal_policy.independent_render import render_dossier
    (target / 'dossier.md').write_bytes(render_dossier(c, snapshot, run, [], predicted))
    receipt = dict(schema_version=2, input_fingerprint=iv.digest(inputs), sources=admitted['proofs'],
        admitted_fingerprints=admitted['admitted_fingerprints'], outputs={name: iv.file_digest(target / name) for name in iv.RUN_FILES}, code={})
    write_json(target / 'receipt.json', receipt)
    return target, run, inputs, events


class IndependentContractTests(unittest.TestCase):
    def test_missing_artifact_policy_control_fails_descriptor_before_io(self):
        descriptor = dict(schema_version=1, control_id='unit-policy-envelope', operation='prepare_run',
            variant='artifact_policy_v2', paths=dict(case='case.json', snapshot='snapshot.json',
                catalog='catalog.json', catalog_policy='policy.json', policy_roots='roots.json'),
            options=dict(policy_use='unit-use'), anchors=dict(frame_sha256='a' * 64))
        self.assertEqual(iv.descriptor_contract(descriptor), descriptor)
        for section, key in (('paths', 'catalog'), ('paths', 'catalog_policy'), ('paths', 'policy_roots'),
                             ('options', 'policy_use'), ('anchors', 'frame_sha256')):
            for missing in ('omitted', 'null'):
                changed = deepcopy(descriptor)
                if missing == 'omitted':
                    del changed[section][key]
                else:
                    changed[section][key] = None
                with self.subTest(section=section, key=key, missing=missing), self.assertRaises(PolicyError):
                    iv.descriptor_contract(changed)

    def test_no_product_imports_in_independent_modules(self):
        for path in Path('experiments/equal_policy').glob('independent*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [name.name for name in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or '']
                else:
                    continue
                self.assertFalse(any(name.split('.')[0] in ('asof', 'tether') for name in modules), path)

    def test_duplicate_json_and_nonfinite_are_rejected(self):
        for payload in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff'):
            with self.subTest(payload=payload), self.assertRaises(PolicyError):
                iv.parse(payload)

    def test_strict_types_defaults_and_utc_normalization(self):
        c = case()
        c['origin_at'] = '2020-01-02T01:59:59.999999+02:00'
        c = decode('Case', c)
        self.assertEqual(c['origin_at'], '2020-01-01T23:59:59.999999+00:00')
        self.assertEqual(decode('Budget', {})['max_calls'], 16)
        for bad in (True, 1.2, '3'):
            with self.subTest(bad=bad), self.assertRaises(PolicyError):
                decode('Usage', dict(input_tokens=bad, output_tokens=0, cost_usd=0))
        with self.assertRaises(PolicyError):
            decode('Case', c | {'extra': 1})

    def test_t6_future_program_is_invalid_before_execution(self):
        c = case(program=dict(program_id='p', molecule_id='m', sponsor='s', phase_at_origin=3,
            status_at_origin='unknown', eligible_since='2019-01-01', mapping_confidence=1.0, trial_ids=[],
            availability=availability(record_public_at='2020-01-02')))
        with self.assertRaisesRegex(PolicyError, 'Unavailable program'):
            iv.validate_case(decode('Case', c))

    def test_t1_endpoint_and_confidence_are_checked(self):
        program = dict(program_id='p', molecule_id='m', sponsor='s', phase_at_origin=1, status_at_origin='active',
            eligible_since='2019-01-01', mapping_confidence=1.0, trial_ids=[], availability=availability())
        c = case(task='T1', program=program, endpoint=dict(name='phase_1_to_2', horizon_months=24))
        iv.validate_case(c)
        for changed in (dict(name='phase_2_to_3', horizon_months=24), dict(name='phase_1_to_2', horizon_months=0)):
            with self.subTest(endpoint=changed), self.assertRaises(PolicyError):
                iv.validate_case(c | {'endpoint': changed})

    def test_availability_precision_and_receipt_bound(self):
        self.assertEqual(iv.availability_reason(availability(record_public_at='2020-01-01'), '2020-01-01T12:00:00+00:00'), 'available_after_origin')
        available = availability(first_public_at=None, release_public_at=None, record_public_at=None, annotation_public_at=None,
            known_public_by='2020-01-01T12:00:00+00:00', evidence_ref='a' * 64)
        self.assertIsNone(iv.availability_reason(available, '2020-01-01T12:00:00+00:00'))
        self.assertEqual(iv.availability_reason(available | {'evidence_ref': None}, '2020-01-01T12:00:00+00:00'), 'availability_proof_invalid')

    def test_numeric_features_require_scope_and_qc(self):
        o = observation(features={'genetic_support': 0.5}, feature_scope=iv.hypothesis_key(case()))
        iv.observation_validity(o)
        for changes in ({'feature_scope': None}, {'status': 'not_measured'}, {'source_kind': 'clinical'}, {'features': {'direction_alignment': 1.1}}):
            with self.subTest(changes=changes), self.assertRaises(PolicyError):
                iv.observation_validity(o | changes)


class IndependentSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case, self.snapshot = fixture(self.root)

    def test_normal_source_admission_and_proof_closure(self):
        result = iv.admit(self.case, self.snapshot, self.root)
        self.assertEqual(list(result['records']), ['o1'])
        self.assertEqual({p['artifact_id'] for p in result['proofs']}, {'packet', 'raw'})

    def test_future_source_excludes_without_opening_packet(self):
        self.snapshot['sources'][0]['availability']['annotation_public_at'] = '2021-01-01'
        (self.root / 'evidence.json').unlink()
        result = iv.admit(self.case, self.snapshot, self.root)
        self.assertEqual(result['records'], {})
        self.assertEqual(result['exclusions'], [dict(item_id='packet', level='artifact', reason='available_after_origin')])

    def test_evaluator_parent_rejects_even_if_unused(self):
        node = deepcopy(self.snapshot['sources'][0])
        node.update(source_id='unused', role='evaluation_only')
        self.snapshot['sources'].append(node)
        with self.assertRaises(PolicyError):
            iv.admit(self.case, self.snapshot, self.root)

    def test_cycle_and_missing_ancestors_reject(self):
        for parent in ('raw', 'missing'):
            changed = deepcopy(self.snapshot)
            changed['sources'][0].update(parents=[parent], computed_at='2021-01-01T00:00:00+00:00', method_id='f', method_version='1')
            with self.subTest(parent=parent), self.assertRaises(PolicyError):
                iv.admit(self.case, changed, self.root)

    def test_new_computation_old_inputs_is_permitted(self):
        derived = deepcopy(self.snapshot['sources'][0])
        derived.update(source_id='computed', parents=['raw'], computed_at='2026-01-01T00:00:00+00:00', method_id='f', method_version='1',
            availability=availability(record_public_at='2026-01-01'))
        self.snapshot['sources'].append(derived)
        self.snapshot['artifacts'][0]['input_refs'] = ['computed']
        result = iv.admit(self.case, self.snapshot, self.root)
        self.assertEqual(list(result['records']), ['o1'])

    def test_publication_future_excludes_observation(self):
        self.case, self.snapshot = fixture(self.root, [observation(publication_year=2021)])
        result = iv.admit(self.case, self.snapshot, self.root)
        self.assertEqual(result['exclusions'][0]['reason'], 'publication_after_origin')
        self.assertEqual(len(result['proofs']), 2)

    def test_duplicate_observation_rejects(self):
        self.case, self.snapshot = fixture(self.root, [observation(), observation()])
        with self.assertRaises(PolicyError):
            iv.admit(self.case, self.snapshot, self.root)

    def test_receipt_backdated_download_is_rejected(self):
        node = self.snapshot['sources'][0]
        receipt = dict(status='completed', sha256=node['sha256'], dataset_id=node['dataset_id'], release_id=node['release_id'],
            relative_path=node['path'], bytes=(self.root / node['path']).stat().st_size, url=node['source_url'],
            completed_at_utc='2020-01-02T00:00:00+00:00')
        path = self.root / 'receipt.json'
        write_json(path, receipt)
        node.update(receipt_path=path.name, receipt_sha256=iv.file_digest(path))
        node['availability'] = availability(first_public_at=None, release_public_at=None, record_public_at=None, annotation_public_at=None,
            basis='public_download_receipt', known_public_by='2020-01-01T00:00:00+00:00', evidence_ref=node['receipt_sha256'])
        with self.assertRaisesRegex(PolicyError, 'Receipt availability'):
            iv.admit(self.case, self.snapshot, self.root)

    def test_core_unused_raw_bytes_are_not_claimed_verified(self):
        node = deepcopy(self.snapshot['sources'][0])
        node.update(source_id='unused', path='not-present.txt')
        self.snapshot['sources'].append(node)
        result = iv.admit(self.case, self.snapshot, self.root)
        self.assertNotIn('unused', {p['artifact_id'] for p in result['proofs']})


class IndependentFeatureTests(unittest.TestCase):
    def test_transitive_dependence_and_conflicts(self):
        c = case()
        a = observation('a', features={'genetic_support': 0.2}, feature_scope=iv.hypothesis_key(c))
        b = observation('b', features={'genetic_support': 0.8}, feature_scope=iv.hypothesis_key(c), study_id='study-2')
        b['context']['cohort_ids'] = ['cohort']
        d = observation('d', features={'genetic_support': 0.8}, feature_scope=iv.hypothesis_key(c), study_id='study-3', dependency_group='other')
        d['context']['cohort_ids'] = ['cohort']
        vector = iv.build_features(c, [claim(a), claim(b), claim(d)])['values']['genetic_support']
        self.assertEqual(vector['status'], 'conflicting')
        self.assertEqual(vector['excluded_groups'], ['group-1'])
        self.assertEqual(vector['dependency_groups'], 0)

    def test_opposite_action_remains_visible_but_features_inapplicable(self):
        c = case()
        o = observation(features={'genetic_support': 0.2}, feature_scope=iv.hypothesis_key(c))
        c['hypothesis']['intended_action'] = 'activate'
        vector = iv.build_features(c, [claim(o)])['values']['genetic_support']
        self.assertIsNone(vector['value'])
        self.assertEqual(vector['missing_reasons'], ['outside_applicability'])
        self.assertTrue(iv.permitted(c, grounded(o)))

    def test_feature_mean_uses_unique_groups(self):
        c = case()
        records = [observation(str(i), features={'genetic_support': value}, feature_scope=iv.hypothesis_key(c),
            dependency_group=group, study_id=None) for i, (group, value) in enumerate((('a', 0.1), ('a', 0.1), ('b', 0.3)))]
        feature = iv.build_features(c, [claim(o) for o in records])['values']['genetic_support']
        self.assertEqual(feature['value'], 0.2)
        self.assertEqual(feature['dependency_groups'], 2)
        self.assertEqual(feature['observation_ids'], ['0', '1', '2'])

    def test_t6_probability_withheld(self):
        c = case()
        result = iv.prediction(c, 'contemporary_assessment', iv.build_features(c, []), None)
        self.assertEqual(result['status'], 'audit_only')
        self.assertIsNone(result['probability'])

    def test_scorer_known_contribution_and_missingness(self):
        c = case(task='T1', program=dict(program_id='p', molecule_id='m', sponsor='s', phase_at_origin=1,
            status_at_origin='active', eligible_since='2019-01-01', mapping_confidence=1.0, trial_ids=[], availability=availability()),
            endpoint=dict(name='phase_1_to_2', horizon_months=24))
        o = observation(features={'genetic_support': 0.5}, feature_scope=iv.hypothesis_key(c))
        result = iv.prediction(c, 'synthetic_demo', iv.build_features(c, [claim(o)]), scorer())
        self.assertAlmostEqual(result['probability'], 0.7310585786300049)
        self.assertEqual(result['contributions']['genetic_support']['log_odds'], 1.0)
        missing = iv.prediction(c, 'synthetic_demo', iv.build_features(c, []), scorer())
        self.assertEqual(missing['reason'], 'required_features_missing')
        self.assertIsNone(missing['probability'])

    def test_scorer_invalid_cutoff_fails_even_t6(self):
        with self.assertRaises(PolicyError):
            iv.scorer_preflight(case(), 'synthetic_demo', scorer(training_label_available_max='2020-01-01'))


class IndependentArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run_dir, self.run, self.inputs, self.events = sealed_fixture(self.root)

    def reseal(self, name, value):
        write_json(self.run_dir / name, value)
        receipt = iv.read_json(self.run_dir / 'receipt.json')
        receipt['outputs'][name] = iv.file_digest(self.run_dir / name)
        write_json(self.run_dir / 'receipt.json', receipt)

    def test_valid_sealed_source_inclusive_run(self):
        result = iv.verify_core(self.run_dir)
        self.assertEqual(result['semantic_consistency'], 'verified')
        self.assertEqual(result['admitted_observation_ids'], ['o1'])
        self.assertEqual(result['selected_observation_ids'], [])
        self.assertEqual(result['calls'], 0)

    def test_rehashed_run_accounting_tamper_rejects(self):
        self.run['calls'] = 1
        self.reseal('run.json', self.run)
        with self.assertRaisesRegex(PolicyError, 'accounting'):
            iv.verify_core(self.run_dir)

    def test_omitted_raw_parent_proof_rejects_without_anchor(self):
        receipt = iv.read_json(self.run_dir / 'receipt.json')
        receipt['sources'] = [row for row in receipt['sources'] if row['artifact_id'] != 'raw']
        write_json(self.run_dir / 'receipt.json', receipt)
        with self.assertRaisesRegex(PolicyError, 'proof closure'):
            iv.verify_core(self.run_dir)

    def test_rehashed_feature_and_prediction_tampers_reject(self):
        features = iv.read_json(self.run_dir / 'features.json')
        features['values']['genetic_support']['value'] = 0.8
        self.reseal('features.json', features)
        with self.assertRaisesRegex(PolicyError, 'feature mismatch'):
            iv.verify_core(self.run_dir)

    def test_rehashed_dossier_tamper_is_not_accepted(self):
        (self.run_dir / 'dossier.md').write_text('changed', encoding='utf-8')
        receipt = iv.read_json(self.run_dir / 'receipt.json')
        receipt['outputs']['dossier.md'] = iv.file_digest(self.run_dir / 'dossier.md')
        write_json(self.run_dir / 'receipt.json', receipt)
        with self.assertRaisesRegex(PolicyError, 'Dossier'):
            iv.verify_core(self.run_dir)

    def test_recovery_retains_unresolved_and_ignores_only_partial_tail(self):
        events = chain([('run_reserved', {}), ('dispatch', dict(attempt_id='genetics:1', reserved=dict(input_tokens=10, output_tokens=20, cost_usd=0)))])
        (self.run_dir / 'journal.jsonl').write_bytes(b''.join(iv.canonical(event) + b'\n' for event in events) + b'{"incomplete":')
        result = iv.inspect_core(self.run_dir)
        self.assertEqual(result['unresolved_attempts'], ['genetics:1'])
        self.assertEqual(result['estimated_upper_usage']['input_tokens'], 10)
        self.assertEqual(result['durable_events'], 2)
        self.assertIn('never automatically repeat', result['recovery_action'])

    def test_recovery_parses_captured_bytes_without_reopening(self):
        events = chain([('run_reserved', {}), ('dispatch', dict(attempt_id='pending', reserved=dict(input_tokens=10, output_tokens=5, cost_usd=0)))])
        payload = b''.join(iv.canonical(event) + b'\n' for event in events) + b'{partial'
        def capture(path):
            path.write_bytes(b'changed after completed stable capture')
            return payload
        with patch.object(iv, 'bounded_stable_bytes', side_effect=capture) as reader:
            result = iv.inspect_core(self.run_dir)
        reader.assert_called_once_with(self.run_dir / 'journal.jsonl')
        self.assertEqual(result['unresolved_attempts'], ['pending'])
        self.assertEqual(result['estimated_upper_usage']['input_tokens'], 10)

    def test_internal_crash_is_error_and_not_policy_rejection(self):
        descriptor = dict(schema_version=1, control_id='unit', variant='core_v2_catalog1', operation='prepare_run',
                          paths=dict(case='case.json', snapshot='snapshot.json'), options={}, anchors={})
        with patch.object(iv, 'prepare_core', side_effect=KeyError('programmer_error')):
            result = iv.validate_bundle(self.root, descriptor)
        self.assertEqual(result['decision'], 'error')
        self.assertEqual(result['violated_obligations'], [])

    def test_preparation_has_no_synthetic_execution_metrics(self):
        write_json(self.root / 'case.json', self.inputs['case'])
        write_json(self.root / 'snapshot.json', self.inputs['snapshot'])
        result = iv.validate_bundle(self.root, dict(schema_version=1, control_id='unit', variant='core_v2_catalog1',
            operation='prepare_run', paths=dict(case='case.json', snapshot='snapshot.json'), options=dict(budget={'max_calls': 0}), anchors={}))
        self.assertEqual(result['decision'], 'accept')
        self.assertEqual(set(result['observables']), {'admitted_observation_ids', 'eligible_observation_ids', 'exclusions', 'scorer_preflight'})

    def selected_run(self):
        source = iv.admit(self.inputs['case'], self.inputs['snapshot'], self.root)
        evidence = source['records']['o1']
        accepted = dict(claim_id='claim-' + iv.digest(dict(case=self.inputs['case']['case_id'], evidence=evidence))[:20],
            specialist='genetics', evidence=evidence, extraction_mode='verbatim_source_selection', admitted_fingerprint=iv.digest(evidence))
        self.inputs['configuration']['disabled'] = []
        self.run['plan'][0]['initial_status'] = 'ready'
        self.run['coverage']['genetics'].update(status='completed', selected_observations=1)
        self.run['calls'] = 1
        self.run['input_fingerprint'] = iv.digest(self.inputs)
        feature = iv.build_features(self.inputs['case'], [accepted])
        predicted = iv.prediction(self.inputs['case'], 'synthetic_demo', feature, None)
        usage = iv._zero_usage()
        events = chain([('plan', dict(steps=self.run['plan'], configuration=self.inputs['configuration'], snapshot_id='snapshot')),
            ('dispatch', dict(category='genetics', attempt=1, attempt_id='genetics:1', reserved=usage, request_sha256='0' * 64)),
            ('attempt_accounted', dict(attempt_id='genetics:1', usage=usage, basis='adapter_reported')),
            ('review', dict(category='genetics', selected=['o1'], usage=usage, problems=[])),
            ('claim_committed', dict(claim=accepted)),
            ('finalize', dict(status='completed', feature_sha256=iv.digest(feature), prediction_sha256=iv.digest(predicted)))])
        for name, value in {'inputs.json': self.inputs, 'run.json': self.run,
                            'ledger.json': dict(schema_version=2, claims=[accepted]), 'features.json': feature,
                            'prediction.json': predicted}.items():
            write_json(self.run_dir / name, value)
        raw = b''.join(iv.canonical(e) + b'\n' for e in events)
        (self.run_dir / 'journal.jsonl').write_bytes(raw)
        (self.run_dir / 'trace.jsonl').write_bytes(raw)
        from experiments.equal_policy.independent_render import render_dossier
        (self.run_dir / 'dossier.md').write_bytes(render_dossier(self.inputs['case'], self.inputs['snapshot'], self.run, [accepted], predicted))
        receipt = iv.read_json(self.run_dir / 'receipt.json')
        receipt['input_fingerprint'] = iv.digest(self.inputs)
        receipt['outputs'] = {name: iv.file_digest(self.run_dir / name) for name in iv.RUN_FILES}
        write_json(self.run_dir / 'receipt.json', receipt)
        return accepted, events

    def test_selected_claim_is_source_bound_and_reviewed(self):
        self.selected_run()
        result = iv.verify_core(self.run_dir)
        self.assertEqual(result['selected_observation_ids'], ['o1'])
        self.assertEqual(result['calls'], 1)

    def test_rehashed_source_claim_mutation_is_rejected(self):
        accepted, _ = self.selected_run()
        accepted['evidence']['observation']['statement'] = 'invented interpretation'
        accepted['admitted_fingerprint'] = iv.digest(accepted['evidence'])
        self.reseal('ledger.json', dict(schema_version=2, claims=[accepted]))
        with self.assertRaisesRegex(PolicyError, 'source binding'):
            iv.verify_core(self.run_dir)

    def test_journal_claim_must_equal_ledger_even_with_valid_chain(self):
        _, events = self.selected_run()
        events[4]['details']['claim']['evidence']['observation']['statement'] = 'not the ledger statement'
        rebuilt = chain([(event['event'], event['details']) for event in events])
        for name in ('journal.jsonl', 'trace.jsonl'):
            (self.run_dir / name).write_bytes(b''.join(iv.canonical(e) + b'\n' for e in rebuilt))
        receipt = iv.read_json(self.run_dir / 'receipt.json')
        for name in ('journal.jsonl', 'trace.jsonl'):
            receipt['outputs'][name] = iv.file_digest(self.run_dir / name)
        write_json(self.run_dir / 'receipt.json', receipt)
        with self.assertRaisesRegex(PolicyError, 'Journal claims'):
            iv.verify_core(self.run_dir)

    def test_bare_core_code_mismatch_is_diagnostic_not_rejection(self):
        result = iv.verify_core(self.run_dir, trusted_runtime=fake_runtime(self.root))
        self.assertFalse(result['code_matches_current'])

    def test_core_code_compares_actual_payload_each_call_not_historical_manifest(self):
        trusted = fake_runtime(self.root)
        receipt = iv.read_json(self.run_dir / 'receipt.json')
        receipt['code'] = trusted['core_code_sha256']
        write_json(self.run_dir / 'receipt.json', receipt)
        self.assertTrue(iv.verify_core(self.run_dir, trusted_runtime=trusted)['code_matches_current'])
        module = Path(trusted['runtime_paths']['asof_file']).parent / 'module.py'
        original = module.read_bytes()
        for mutation in ('content', 'add', 'remove'):
            with self.subTest(mutation=mutation):
                extra = module.with_name('extra.py')
                if mutation == 'content': module.write_bytes(b'VALUE = 2\n')
                elif mutation == 'add': extra.write_bytes(b'ADDED = True\n')
                else: module.unlink()
                self.assertFalse(iv.verify_core(self.run_dir, trusted_runtime=trusted)['code_matches_current'])
                module.write_bytes(original)
                if extra.exists(): extra.unlink()
        # A stale manifest cannot turn current matching bytes into a mismatch.
        trusted['core_code_sha256'] = {'fictional_old.py': '0' * 64}
        self.assertTrue(iv.verify_core(self.run_dir, trusted_runtime=trusted)['code_matches_current'])


class IndependentLocalTests(unittest.TestCase):
    def test_malformed_content_or_counts_are_not_validated_usage(self):
        base = dict(truncated=False, content='{"observation_ids":["a"]}', tokens_evaluated=10, tokens_predicted=4)
        for changes in ({'tokens_evaluated': True}, {'tokens_predicted': -1}, {'content': 'not json'}, {'truncated': True}):
            with self.subTest(changes=changes), self.assertRaises(PolicyError):
                local.parse_response(base | changes, ['a'], 3)
        selected, usage = local.parse_response(base, ['a'], 3)
        self.assertEqual(selected, ['a'])
        self.assertEqual(iv.canonical(usage), b'{"cost_usd":0,"input_tokens":10,"output_tokens":4}')

    def test_bounded_retrieval_whole_records_and_literal_order(self):
        c = case()
        records = [grounded(observation('b', statement='no token match')), grounded(observation('a', statement='TARGET inhibit antibody'))]
        request = local.make_request(c, 'genetics', records, [])
        bounded, audit = local.bound_request(request, dict(max_records=1, max_request_bytes=12000))
        self.assertEqual(audit['selected_ids'], ['a'])
        self.assertEqual(audit['excluded'], [dict(observation_id='b', reason='record_count_cap')])
        self.assertEqual(bounded['evidence'][0], request['evidence'][1])

    def test_shared_wire_preserves_float_spelling_and_nulls(self):
        request = dict(case_json='{}', category='genetics', instructions='x', feedback=[], evidence=[
            dict(observation_id='a', statement='s', source_ref='p', scientific_record_json='{"observation_id":"a","q":-0.0,"statement":"s","x":null}'),
            dict(observation_id='b', statement='s', source_ref='p', scientific_record_json='{"observation_id":"b","q":0.0,"statement":"s","x":null}')])
        wire = iv.parse(local.request_bytes(request, local.FORMAT))
        self.assertEqual(wire['common_scientific_fields'], {'x': None})
        self.assertIn(b'"q":-0.0', local.request_bytes(request, local.FORMAT))

    def archive(self, *, over=False, malformed=False, wire='canonical'):
        c = case()
        records = {'o1': grounded(observation())}
        config = dict(max_output_tokens=32, seed=17, retrieval=dict(max_records=3, max_request_bytes=12000, wire_format=wire))
        request = local.make_request(c, 'genetics', list(records.values()), [])
        bounded, audit = local.bound_request(request, config['retrieval'])
        payload = local.payload_for(bounded, 32, 17, wire)
        quote = dict(input_tokens=len(payload['prompt'].encode('utf-8')) + 32, output_tokens=32, cost_usd=0)
        response = dict(content='{"observation_ids":["o1"]}', truncated=False,
            tokens_evaluated=quote['input_tokens'] + 1 if over else 10, tokens_predicted=4)
        if malformed:
            response['tokens_evaluated'] = True
        usage = quote if malformed else dict(input_tokens=response['tokens_evaluated'], output_tokens=4, cost_usd=0)
        entry = dict(request=bounded, request_sha256=iv.digest(bounded), payload=payload, payload_sha256=iv.digest(payload),
            response=response, response_sha256=iv.digest(response), status='failed' if over or malformed else 'completed')
        if over:
            entry.update(measured_usage=usage, failure_kind='usage_reservation_exceeded')
        elif not malformed:
            entry.update(measured_usage=usage, selection=['o1'])
        events = [('bounded_retrieval', dict(category='genetics', attempt=1, **audit)),
            ('dispatch', dict(category='genetics', attempt=1, attempt_id='genetics:1', reserved=quote, request_sha256=iv.digest(bounded))),
            ('attempt_accounted', dict(attempt_id='genetics:1', usage=usage,
                basis='quoted_upper_bound_not_measured' if malformed else 'adapter_reported'))]
        if over:
            events.append(('backend_usage_contract_violated', dict(category='genetics', usage=usage)))
        elif not malformed:
            events.append(('review', dict(category='genetics', selected=['o1'], problems=[], usage=usage)))
        return dict(schema_version=1, attempts=[entry]), chain(events), dict(backend_provenance=dict(config=config)), c, dict(records=records)

    def test_local_valid_archive_both_wire_forms(self):
        for wire in ('canonical', local.FORMAT):
            with self.subTest(wire=wire):
                local.verify_local(*self.archive(wire=wire))

    def test_local_overquote_is_measured_and_terminal(self):
        local.verify_local(*self.archive(over=True))
        document, events, configuration, c, source = self.archive(over=True)
        document['attempts'][0].pop('measured_usage')
        with self.assertRaises(PolicyError):
            local.verify_local(document, events, configuration, c, source)

    def test_local_malformed_response_remains_estimated(self):
        local.verify_local(*self.archive(malformed=True))
        document, events, configuration, c, source = self.archive(malformed=True)
        document['attempts'][0]['measured_usage'] = dict(input_tokens=10, output_tokens=4, cost_usd=0)
        with self.assertRaises(PolicyError):
            local.verify_local(document, events, configuration, c, source)

    def test_local_mismatched_account_and_payload_are_rejected(self):
        for changed in ('account', 'payload', 'response'):
            document, events, configuration, c, source = self.archive()
            if changed == 'account':
                events[2]['details']['usage']['input_tokens'] = 99
            elif changed == 'payload':
                document['attempts'][0]['payload']['seed'] = 99
            else:
                document['attempts'][0]['response']['tokens_predicted'] = 2
            with self.subTest(changed=changed), self.assertRaises(PolicyError):
                local.verify_local(document, events, configuration, c, source)

    def test_replay_archive_reconstructs_request_without_original_file(self):
        c, source = case(), dict(records={'o1': grounded(observation())})
        request = local.make_request(c, 'genetics', list(source['records'].values()), [])
        usage = dict(input_tokens=10, output_tokens=4, cost_usd=0.0)
        replay = dict(schema_version=2, responses={'genetics': [dict(request_sha256=iv.digest(request),
            selection=dict(observation_ids=['o1'], usage=usage))]})
        configuration = dict(backend_provenance=dict(document=replay, path='unavailable-original.json', sha256='d' * 64))
        events = chain([('dispatch', dict(category='genetics', attempt_id='genetics:1', request_sha256=iv.digest(request), reserved=usage)),
            ('attempt_accounted', dict(attempt_id='genetics:1', usage=usage, basis='adapter_reported')),
            ('review', dict(category='genetics', selected=['o1'], usage=usage, problems=[]))])
        local.verify_replay(events, configuration, c, source)
        replay['responses']['genetics'][0]['request_sha256'] = '0' * 64
        with self.assertRaisesRegex(PolicyError, 'Replay/request'):
            local.verify_replay(events, configuration, c, source)


if __name__ == '__main__':
    unittest.main()
