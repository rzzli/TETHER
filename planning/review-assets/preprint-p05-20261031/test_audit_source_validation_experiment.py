"""Fictional-only auditor regressions; no actual native source/study reads."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("independent_experiment_auditor", ROOT / "tools/science/audit_source_validation_experiment.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
a, s, r = audit.a, audit.s, audit.r


def fictional_memory(key):
    case, docs = audit.fixture_documents(key)
    observed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    nodes, source_bytes, receipts, anchors, catalog = [], {}, {}, [], {"schema_version": 1, "datasets": []}
    for name, doc in docs.items():
        clean = a.wire(doc) + b"\n"
        source_bytes[name] = clean + (b" " if key == "F01" and name == "gwas" else b"")
        receipt = {"status": "completed", "dataset_id": "fiction_" + name, "release_id": "25.09", "relative_path": name + ".json", "sha256": a.sha(clean), "bytes": len(clean), "url": "https://example.invalid/" + name, "completed_at_utc": observed.isoformat()}
        receipts[name] = a.wire(receipt) + b"\n"
        role = "evaluation_only" if name == "forbidden" else "reference" if name == "mapping" else "agent_evidence"
        avail = audit.Availability(None, None, None, None, observed.date(), "public_download_receipt", "fictional only", observed, a.sha(receipts[name]))
        node = audit.SourceNode("fiction-" + name, "fiction_" + name, "25.09", name + ".json", a.sha(clean), role, avail, audit.TemporalClass.CONTEMPORARY, receipt["url"], receipt_path=name + ".receipt.json", receipt_sha256=a.sha(receipts[name]))
        if key == "F02" and name == "gwas":
            node = audit.SourceNode(node.source_id, node.dataset_id, node.release_id, node.path, node.sha256, node.role, node.availability, node.temporal_classification, node.source_url,
                parents=("fiction-forbidden",), computed_at=observed, method_id="fiction-derived", method_version="1", receipt_path=node.receipt_path, receipt_sha256=node.receipt_sha256)
        nodes.append(node)
        anchors.extend(({"path": name + ".json", "sha256": a.sha(clean), "bytes": len(clean)}, {"path": name + ".receipt.json", "sha256": a.sha(receipts[name]), "bytes": len(receipts[name])}))
        catalog["datasets"].append({"dataset_id": "fiction_" + name, "roles": [role]})
    groups = audit.json_groups(case, docs, declared_subset=key == "F04")
    task = s.expected_task(case, groups)
    records = [{"record_key": rec["record_key"], **row} for rec, row in zip(task["records"], groups["gwas_credible_sets"] + groups["credible_set"])]
    packet = {"neutral_task": task, "source_records": records}
    snapshot = audit.Snapshot(2, "fiction-" + key, audit.Profile.CONTEMPORARY, r.utc(s.CUTOFF).date(), False, (), tuple(nodes), str(ROOT / "data/cache/fictional-auditor-memory" / key / "originals"), {"scope": "fictional_JSON_only"}, r.utc(s.CUTOFF))
    scenario = {"scenario_id": key, "case": case, "task": task, "snapshot": audit.encode(snapshot), "catalog": catalog, "original_source_anchors": anchors}
    rows = {record["record_key"]: record["values"] for record in records}
    facts, _ = audit.projected_facts(task, rows, {n.source_id: n for n in nodes}, permit_boolean_measurement=True)
    raw = audit.candidate_bytes(task, facts, key)
    return scenario, packet, source_bytes, receipts, raw


def evidence(key):
    return audit.fixture_evidence(*fictional_memory(key))


class IndependentAuditorTests(unittest.TestCase):
    def test_schedule_counts_unique_and_paired(self):
        outputs, decisions = audit.fixed_schedule()
        self.assertEqual((len(outputs), len(decisions)), (38, 90))
        self.assertEqual(len({o['cell_id'] for o in outputs}), 38)
        self.assertEqual(len({d['decision_id'] for d in decisions}), 90)
        self.assertEqual(sum(o['stratum'] == 'native' for o in outputs), 24)
        self.assertEqual(sum(d['output_cell_id'].startswith('N-') for d in decisions), 48)

    def test_four_valid_ten_fault_controls_have_independent_stage_truth(self):
        first = {"F01": "G0", "F02": "G1", "F03": "G2", "F04": "G2", "F09": "G3"}
        for key in audit.SCENARIOS:
            with self.subTest(key=key):
                result = evidence(key)
                valid = key.startswith('C')
                self.assertEqual(result['truth'], 'VALID_REPORT' if valid else 'INVALID')
                full = result['decisions']['FULL']
                self.assertEqual(full['verdict'], 'admitted' if valid else 'rejected')
                self.assertEqual(full['first_failure_stage'], None if valid else first.get(key, 'G4'))
                self.assertEqual(result['decisions']['WITHOUT_WRAPPER']['verdict'], 'admitted' if valid or key in ('F03', 'F04') else 'rejected')
                self.assertEqual(result['decisions']['WIRE_ONLY']['verdict'], 'rejected' if key in ('F01', 'F08', 'F10') else 'admitted')

    def test_clean_literal_scoring_contributions(self):
        result = evidence('C01')
        self.assertTrue(result['strict_exact_report'])
        self.assertEqual(result['score']['primary']['coverage'], 1.0)
        self.assertEqual(result['score']['primary']['passes'], {'60': True, '80': True, '100': True})
        row = result['fact_accounting']['families']['reported_measurement']
        self.assertEqual((row['requested'], row['answerable'], row['matched'], row['omitted'], row['false_asserted']), (4, 4, 4, 0, 0))

    def test_missing_null_absent_empty_stay_distinct(self):
        result = evidence('C02')
        facts = {f['field']: f for f in result['reference']['facts'] if f['family'] == 'reported_measurement'}
        self.assertEqual(facts['beta']['unknown_reason'], 'null_source_value')
        self.assertEqual(facts['standardError']['unknown_reason'], 'field_not_in_schema')
        self.assertEqual(facts['pValueMantissa']['unknown_reason'], 'empty_source_value')
        self.assertIs(type(facts['pValueExponent']['value']), int)
        self.assertEqual(result['score']['measurement_answerable_facts'], 1)
        self.assertEqual(result['fact_accounting']['families']['reported_measurement']['correct_unknown'], 3)

    def test_multiplicity_retains_negative_native_standard_error(self):
        result = evidence('C03')
        facts = [f for f in result['reference']['facts'] if f['field'] == 'standardError']
        self.assertEqual([f['value'] for f in facts], [0.25, -0.5])
        self.assertEqual(result['score']['family_scores']['reported_measurement']['answerable_groups'], 2)
        self.assertEqual(result['reference']['method']['scientific_validation'], 'not_established')

    def test_zero_measurements_is_valid_exact_but_not_completion(self):
        result = evidence('C04')
        self.assertTrue(result['strict_exact_report'])
        self.assertEqual(result['decisions']['FULL']['verdict'], 'admitted')
        self.assertIsNone(result['score']['primary']['coverage'])
        self.assertEqual(result['score']['primary']['passes'], {'60': None, '80': None, '100': None})
        self.assertFalse(result['score']['completion'])

    def test_stale_source_anchor_is_not_repaired_by_observed_fixture_hash(self):
        result = evidence('F01')
        self.assertEqual(result['statuses']['G0'], 'rejected')
        self.assertEqual(result['schema_status'], 'pass')
        self.assertIsNone(result['score'])
        self.assertEqual(result['decisions']['WIRE_ONLY']['verdict'], 'rejected')

    def test_forbidden_ancestor_has_no_reference_but_schema_valid_output(self):
        result = evidence('F02')
        self.assertEqual(result['statuses']['G1'], 'rejected')
        self.assertIsNone(result['reference'])
        self.assertEqual(result['schema_status'], 'pass')

    def test_future_release_is_wrapper_only_fault(self):
        result = evidence('F03')
        self.assertEqual(result['statuses']['G2'], 'rejected')
        self.assertEqual(result['statuses']['G3'], 'pass')
        self.assertEqual(result['decisions']['WITHOUT_WRAPPER']['verdict'], 'admitted')
        self.assertFalse(result['full_verified_exact'])

    def test_omitted_eligible_physical_row_rejects_complete_inventory_claim(self):
        result = evidence('F04')
        self.assertEqual(result['statuses']['G2'], 'rejected')
        self.assertEqual(result['statuses']['G3'], 'pass')

    def test_wrong_value_and_binding_each_lose_component_credit(self):
        for key in ('F05', 'F06'):
            with self.subTest(key=key):
                result = evidence(key)
                self.assertEqual(result['score']['primary']['coverage'], 0.75)
                self.assertFalse(result['score']['completion'])
                row = result['fact_accounting']['families']['reported_measurement']
                self.assertEqual((row['matched'], row['false_asserted'], row['false_asserted_values']), (3, 1, 1))

    def test_wrong_unknown_reason_does_not_gain_measurement_credit(self):
        result = evidence('F07')
        self.assertEqual(result['score']['primary']['coverage'], 1.0)
        self.assertFalse(result['score']['completion'])
        row = result['fact_accounting']['families']['reported_measurement']
        self.assertEqual((row['correct_unknown'], row['false_asserted']), (2, 0))

    def test_duplicate_key_is_rejected_before_scoring(self):
        result = evidence('F08')
        self.assertEqual(result['score']['terminal'], 'malformed')
        self.assertEqual(result['score']['failure_reason'], 'ContractError: Duplicate JSON key: status')

    def test_native_boolean_is_not_coerced_to_integer(self):
        result = evidence('F09')
        self.assertEqual(result['statuses']['G3'], 'rejected')
        self.assertEqual(result['schema_status'], 'pass')
        self.assertIsNone(result['score'])

    def test_full_oversize_bytes_are_retained_but_not_accepted(self):
        scenario, packet, sources, receipts, raw = fictional_memory('F10')
        self.assertEqual(len(raw), 262145)
        result = audit.fixture_evidence(scenario, packet, sources, receipts, raw)
        self.assertEqual(result['score']['failure_reason'], 'ContractError: Retained output exceeds 256 KiB')

    def test_always_abstain_has_no_unsupported_assertions_and_no_completion(self):
        ref = evidence('C01')['reference']
        raw = a.wire(audit.wire_projection(ref['method']['task'], ref['facts'], abstain=True))
        score, exact, accounting = audit.independent_score(ref, raw, 'abstain')
        self.assertFalse(exact)
        self.assertFalse(score['completion'])
        self.assertEqual(score['critical_errors'], [])
        self.assertEqual(score['primary']['coverage'], 0)
        self.assertEqual(accounting['families']['reported_measurement']['omitted'], 4)

    def test_nonreturn_partial_bytes_never_rescue_failure(self):
        ref = evidence('C01')['reference']
        raw = a.wire(audit.wire_projection(ref['method']['task'], ref['facts']))
        for terminal in ('failed', 'timeout', 'interrupted', 'unexecuted'):
            with self.subTest(terminal=terminal):
                score, exact, accounting = audit.independent_score(ref, raw, 'nonreturn', terminal)
                self.assertEqual(score['adapter_status'], 'not_attempted')
                self.assertFalse(exact)
                self.assertIsNone(score['primary']['coverage'])

    def test_duplicate_fact_unknown_id_and_wrong_unit_are_critical(self):
        ref = evidence('C01')['reference']
        base = audit.wire_projection(ref['method']['task'], ref['facts'])
        for mutation in ('duplicate', 'unknown_id', 'unit'):
            doc = deepcopy(base)
            if mutation == 'duplicate': doc['facts'].append(deepcopy(doc['facts'][0]))
            if mutation == 'unknown_id': doc['facts'][0]['fact_id'] = 'fact:unrecognized'
            if mutation == 'unit': doc['facts'][0]['unit'] = 'invented-unit'
            score, exact, _ = audit.independent_score(ref, a.wire(doc), mutation)
            self.assertFalse(exact)
            self.assertTrue(score['critical_errors'])
            self.assertFalse(score['completion'])

    def test_numeric_types_and_signed_zero_are_exact(self):
        ref = deepcopy(evidence('C01')['reference'])
        doc = audit.wire_projection(ref['method']['task'], ref['facts'])
        emitted = next(f for f in doc['facts'] if f['source']['field'] == 'pValueMantissa')
        emitted['value'] = 2
        score, exact, _ = audit.independent_score(ref, a.wire(doc), 'int-float')
        self.assertFalse(exact)
        self.assertTrue(score['critical_errors'])
        fact = next(f for f in ref['facts'] if f['field'] == 'beta')
        fact['value'] = -0.0
        doc = audit.wire_projection(ref['method']['task'], ref['facts'])
        next(f for f in doc['facts'] if f['source']['field'] == 'beta')['value'] = 0.0
        self.assertFalse(audit.independent_score(ref, a.wire(doc), 'signed-zero')[1])

    def test_strict_parser_rejects_nonfinite_unicode_and_bad_shape(self):
        ref = evidence('C01')['reference']; task = ref['method']['task']
        for raw in (b'{"x":NaN}', b'{}', b'[]', b'not-json'):
            self.assertEqual(audit.parse_wire(raw, task)['status'], 'malformed')
        doc = audit.wire_projection(task, ref['facts']); doc['facts'][0]['value'] = '\ud800'
        raw = __import__('json').dumps(doc).encode()
        self.assertEqual(audit.parse_wire(raw, task)['status'], 'malformed')

    def test_wire_accepts_bom_like_frozen_core(self):
        ref = evidence('C01')['reference']; doc = audit.wire_projection(ref['method']['task'], ref['facts'])
        self.assertEqual(audit.parse_wire(b'\xef\xbb\xbf'+a.wire(doc), ref['method']['task'])['status'], 'scorable')

    def test_policy_no_decision_is_not_rejection(self):
        statuses = dict.fromkeys(audit.STAGES, 'unexecuted')
        self.assertEqual(audit.policy_decision(statuses, 'pass', 'FULL')['verdict'], 'no_decision')
        statuses['G0'] = 'rejected'
        self.assertEqual(audit.policy_decision(statuses, 'pass', 'WIRE_ONLY')['verdict'], 'rejected')


class ActualProducerFictionalComparison(unittest.TestCase):
    """Producer outputs are comparison targets, never the expected-fact oracle."""
    @classmethod
    def setUpClass(cls):
        cache = ROOT / 'data/cache'
        cls.temp = tempfile.TemporaryDirectory(prefix='p05-independent-auditor-fictional-', dir=cache)
        cls.base = Path(cls.temp.name).resolve()
        assert cls.base.is_relative_to(cache.resolve())
        spec = importlib.util.spec_from_file_location('fictional_producer_comparison_only', ROOT / 'tools/science/run_source_validation_experiment.py')
        cls.producer = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.producer)
        cls.fixture = cls.base / 'fixtures'
        cls.manifest = cls.producer.author_fictional_fixtures(cls.fixture)
        cls.output = cls.base / 'comparison'; cls.output.mkdir()

    @classmethod
    def tearDownClass(cls):
        assert cls.base.is_relative_to((ROOT/'data/cache').resolve())
        cls.temp.cleanup()

    def test_all14_real_guard_score_accounting_and_policy_comparisons(self):
        producer = self.producer
        for key in audit.SCENARIOS:
            with self.subTest(key=key):
                bounds = producer.Bounds(self.output)
                scenario, packet = producer.load_fictional(self.fixture, key, self.manifest, bounds)
                actual_raw = producer.fictional_candidate(packet, key)
                _, blueprint = audit.fixture_documents(key)
                sources = {n:(self.fixture/key/'originals'/(n+'.json')).read_bytes() for n in blueprint}
                receipts = {n:(self.fixture/key/'originals'/(n+'.receipt.json')).read_bytes() for n in blueprint}
                expected = audit.fixture_evidence(scenario, packet, sources, receipts, actual_raw, fixture_root=self.fixture)
                actual = producer.evaluate_fictional(scenario, packet, actual_raw, bounds, approved_fixture_root=self.fixture)
                self.assertEqual({k:v['status'] for k,v in actual['stages'].items()}, expected['statuses'])
                self.assertEqual(actual['stages']['G4']['schema_status'], expected['schema_status'])
                self.assertTrue(s.same(audit.encode(actual['score']), expected['score']))
                self.assertTrue(s.same(actual['fact_accounting'], expected['fact_accounting']))
                self.assertEqual(actual['raw_terminal'], expected['raw_terminal'])
                for decision in actual['decisions']:
                    semantic = expected['decisions'][decision['policy']]
                    self.assertEqual({k:decision[k] for k in semantic}, semantic)


if __name__ == '__main__':
    unittest.main()
