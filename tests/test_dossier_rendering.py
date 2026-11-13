"""Literal source rendering and archived-format compatibility; fictional inputs only."""
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from tether_engine.agents import ExtractiveBackend
from tether_engine import artifacts
from tether_engine.chrono import Exclusion, load_snapshot
from tether_engine.contracts import Case
from tether_engine.scorer import ScorerArtifact
from tether_engine.serde import ContractError, decode, read_json, sha256_file, write_json
from tether_engine.workflow import run_workflow


class DossierRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = Path(__file__).resolve().parents[1] / 'src/tether_engine/demo/v2'
        case = decode(Case, read_json(fixture / 'case.json'))
        model = decode(ScorerArtifact, read_json(fixture / 'scorer.json'))
        cls.model = model
        cls.store = load_snapshot(fixture / 'snapshot.json', case)
        cls.result = run_workflow(case, cls.store, ExtractiveBackend(), model)

    def changed_record(self, **changes):
        claim = self.result.claims[0]
        evidence = replace(claim.evidence, observation=replace(claim.evidence.observation, **changes))
        return replace(self.result, claims=(replace(claim, evidence=evidence),))

    def changed_store(self, **snapshot_changes):
        return SimpleNamespace(snapshot=replace(self.store.snapshot, **snapshot_changes), exclusions=self.store.exclusions)

    def test_source_statement_cannot_create_html_links_images_or_headings(self):
        statement = '<img src=x onerror=alert(1)> [click](javascript:alert(1)) ![image](https://invalid.test/)\n# forged\n> nested'
        text = artifacts.dossier(self.changed_record(statement=statement), self.store)
        self.assertNotIn('<img', text)
        self.assertNotIn('[click](', text)
        self.assertNotIn('![image](', text)
        self.assertIn('&lt;img', text)
        self.assertIn('> \\# forged\n> &gt; nested', text)

    def test_crlf_and_carriage_return_cannot_escape_the_quote(self):
        text = artifacts.dossier(self.changed_record(statement='first\r\n<script>bad</script>\r# forged'), self.store)
        self.assertNotIn('\r', text)
        self.assertIn('> first\n> &lt;script&gt;bad&lt;\\/script&gt;\n> \\# forged', text)

    def test_plain_unicode_remains_plain_and_ledger_is_unchanged(self):
        statement = 'αβ 中文 café with ordinary words\nSecond line'
        result = self.changed_record(statement=statement)
        before = result.claims[0].evidence.observation.statement
        rendered = artifacts.dossier(result, self.store)
        self.assertIn('> αβ 中文 café with ordinary words\n> Second line', rendered)
        self.assertEqual(result.claims[0].evidence.observation.statement, before)

    def test_limitations_missingness_and_identifiers_are_literal(self):
        record = self.result.claims[0].evidence.observation
        result = self.changed_record(method=replace(record.method, limitations=('<svg onload=x>',)),
                                     missingness={'<b>field</b>': '[click](javascript:x)'},
                                     dependency_group='<iframe src=x>')
        result = replace(result, case=replace(result.case, case_id='<script>case</script>'))
        text = artifacts.dossier(result, self.store)
        for token in ('<svg', '<b>', '<iframe', '<script>', '[click]('): self.assertNotIn(token, text)

    def test_table_text_cannot_add_cells_or_rows(self):
        store = self.changed_store(coverage={'interpretation_scope': 'resource_annotation_only',
            'hypothesis_qualification': {'genotype|extra': {'value': 'x|y\n| forged | cell |'}}})
        text = artifacts.dossier(self.result, store)
        line = next(line for line in text.splitlines() if line.startswith('| genotype'))
        self.assertIn('genotype\\|extra', line)
        self.assertIn('x\\|y&#10;\\| forged \\| cell \\|', line)
        self.assertFalse(any(line.startswith('| forged') for line in text.splitlines()))

    def test_json_backticks_cannot_close_the_code_span(self):
        text = artifacts.dossier(self.changed_record(source_metrics={'literal': '` <img src=x> `` [click](javascript:x)'}), self.store)
        line = next(line for line in text.splitlines() if line.startswith('Provider metrics'))
        self.assertTrue(line.startswith('Provider metrics (descriptive): ``` '))
        self.assertTrue(line.endswith(' ```.'))
        self.assertEqual(line.count('```'), 2)

    def test_coverage_exclusion_and_abstention_text_are_literal(self):
        coverage = {name: dict(value) for name, value in self.result.coverage.items()}
        first = next(iter(coverage))
        coverage[first]['status'] = '<img src=x>'
        coverage[first]['nonobserved'] = [{'status': 'unknown', 'observation_id': '<id>', 'reason': '<svg onload=x>'}]
        result = replace(self.result, coverage=coverage, prediction=replace(self.result.prediction,
            probability=None, contributions={}, reason='<script>reason</script>'))
        store = SimpleNamespace(snapshot=self.store.snapshot, exclusions=(Exclusion('<id>', '<level>', '<svg>'),))
        text = artifacts.dossier(result, store)
        for token in ('<img', '<id>', '<svg', '<script>', '<level>'): self.assertNotIn(token, text)

    def test_statement_and_limitation_wrong_types_raise_contract_errors(self):
        record = self.result.claims[0].evidence.observation
        cases = [self.changed_record(statement=7), self.changed_record(statement={'SECRET': 'value'}),
                 self.changed_record(method=replace(record.method, limitations='SECRET wrong sequence')),
                 self.changed_record(method=replace(record.method, limitations=(None,))),
                 self.changed_record(statement='null\x00byte'),
                 self.changed_record(statement='unpaired\ud800surrogate')]
        for result in cases:
            with self.assertRaises(ContractError) as caught: artifacts.dossier(result, self.store)
            self.assertNotIn('SECRET', str(caught.exception))

    def test_malformed_metrics_and_missingness_do_not_leak_or_coerce(self):
        cases = [self.changed_record(source_metrics=['SECRET']), self.changed_record(source_metrics={1: 'SECRET'}),
                 self.changed_record(source_metrics={'secret': float('nan')}),
                 self.changed_record(missingness={'field': 9}), self.changed_record(missingness=['SECRET'])]
        for result in cases:
            with self.assertRaises(ContractError) as caught: artifacts.dossier(result, self.store)
            self.assertNotIn('SECRET', str(caught.exception))

    def test_malformed_coverage_shapes_raise_contract_errors(self):
        for coverage in (None, [], {'interpretation_scope': 'resource_annotation_only', 'hypothesis_qualification': []},
                         {'interpretation_scope': 'resource_annotation_only', 'hypothesis_qualification': {'x': []}},
                         {'interpretation_scope': 'resource_annotation_only', 'hypothesis_qualification': {'x': {}}}):
            store = SimpleNamespace(snapshot=SimpleNamespace(coverage=coverage), exclusions=())
            with self.assertRaises(ContractError): artifacts.dossier(self.result, store)
        for coverage in ([], {'genetics': []}, {'genetics': {'status': 'ready'}}):
            with self.assertRaises(ContractError): artifacts.dossier(replace(self.result, coverage=coverage), self.store)

    def test_legacy_plain_demo_has_exact_previous_bytes(self):
        payload = artifacts.dossier_for_format(self.result, self.store, None).encode('utf-8')
        self.assertEqual(hashlib.sha256(payload).hexdigest(), '427874e1bee2a5c975a019dd5e774494b37193aa2e4490dbf01f7d25050e25a3')

    def test_format_dispatch_is_explicit_and_does_not_upgrade_archived_text(self):
        result = self.changed_record(statement='<b>archive</b>')
        self.assertIn('<b>archive</b>', artifacts.dossier_for_format(result, self.store, None))
        self.assertNotIn('<b>', artifacts.dossier_for_format(result, self.store, artifacts.DOSSIER_FORMAT))
        for value in ('unknown', '', 1, False, []):
            with self.assertRaises(ContractError): artifacts.dossier_for_format(result, self.store, value)

    def test_write_run_seals_new_format_and_prior_format_still_verifies(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            artifacts.write_run(output, self.result, self.store, self.model)
            run = read_json(output / 'run.json')
            self.assertEqual(run['dossier_format'], artifacts.DOSSIER_FORMAT)
            self.assertEqual(artifacts.verify_run(output)['byte_integrity'], 'verified')
            # A prior producer's sealed original bytes have no renderer field.
            # This fixture retains all semantic inputs and changes only that
            # presentation envelope, then pins the exact resulting bytes.
            del run['dossier_format']; write_json(output / 'run.json', run)
            (output / 'dossier.md').write_bytes(artifacts.dossier_for_format(self.result, self.store, None).encode())
            receipt = read_json(output / 'receipt.json')
            receipt['outputs'].update({name: sha256_file(output / name) for name in ('run.json', 'dossier.md')})
            write_json(output / 'receipt.json', receipt)
            self.assertEqual(artifacts.verify_run(output)['byte_integrity'], 'verified')
            run['dossier_format'] = 'unsupported'; write_json(output / 'run.json', run)
            receipt['outputs']['run.json'] = sha256_file(output / 'run.json')
            write_json(output / 'receipt.json', receipt)
            with self.assertRaisesRegex(ContractError, 'rendering format'): artifacts.verify_run(output)

    def test_metadata_nesting_and_bool_counts_are_rejected(self):
        nested = 'value'
        for _ in range(34): nested = [nested]
        with self.assertRaises(ContractError): artifacts.dossier(self.changed_record(source_metrics={'nested': nested}), self.store)
        coverage = {name: dict(value) for name, value in self.result.coverage.items()}
        coverage[next(iter(coverage))]['selected_observations'] = True
        with self.assertRaises(ContractError): artifacts.dossier(replace(self.result, coverage=coverage), self.store)


if __name__ == '__main__': unittest.main()
