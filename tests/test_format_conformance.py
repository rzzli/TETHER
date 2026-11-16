"""Public wire-format controls, constructed without the production serializer."""
import hashlib
import ast
import copy
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.journal import parse_chain
from tether_engine.serde import ContractError
from tools import independent_verify as second

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'src/tether_engine/demo/v2'
VECTORS = json.loads((ROOT / 'tests/fixtures/format_conformance_v1.json').read_text(encoding='utf-8'))


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def one_event(sequence=0):
    record = dict(sequence=sequence, event='plan', details={}, previous_sha256=None)
    record['sha256'] = hashlib.sha256(wire(record)).hexdigest()
    return wire(record) + b'\n'


class JournalWireConformanceTests(unittest.TestCase):
    def test_integer_sequence_positive_control(self):
        events = parse_chain(one_event())
        self.assertEqual(len(events), 1)
        self.assertIs(type(events[0]['sequence']), int)

    def test_boolean_sequence_is_not_an_integer_counter(self):
        with self.assertRaisesRegex(ContractError, 'hash-chain'):
            parse_chain(one_event(False))

    def test_integral_float_sequence_is_not_an_integer_counter(self):
        with self.assertRaisesRegex(ContractError, 'hash-chain'):
            parse_chain(one_event(0.0))

    def test_public_wire_vectors_agree_in_both_implementations(self):
        for vector in VECTORS['journal']:
            with self.subTest(vector=vector['id']):
                raw = vector['payload_utf8'].encode('utf-8')
                if vector['expected'] == 'accept':
                    self.assertEqual(json.loads(wire(parse_chain_as_json(raw))), second.chain(raw))
                else:
                    with self.assertRaises(ContractError):
                        parse_chain(raw)
                    with self.assertRaises(second.Rejected) as error:
                        second.chain(raw)
                    self.assertEqual(error.exception.reason, vector['reason'])

    def test_literal_canonical_vectors_and_numeric_distinctions(self):
        from tether_engine.serde import canonical
        vectors = json.loads((ROOT / 'tests/fixtures/portable_bundle_canonical.json').read_text(encoding='utf-8'))
        for vector in vectors['vectors']:
            with self.subTest(vector=vector['name']):
                raw = bytes.fromhex(vector['utf8_hex'])
                self.assertEqual(second.canonical(vector['input']), raw)
                self.assertEqual(canonical(vector['input']), raw)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), vector['sha256'])
        self.assertNotEqual(second.fp(1), second.fp(1.0))
        self.assertNotEqual(second.fp(-0.0), second.fp(0.0))

    def test_deterministic_generated_order_and_omission_controls(self):
        rng = random.Random(9017)
        for trial in range(40):
            rows = []
            for index in range(rng.randint(3, 12)):
                row = dict(sequence=index, event='fixture', details={'trial': trial, 'value': rng.randrange(100000)},
                           previous_sha256=rows[-1]['sha256'] if rows else None)
                row['sha256'] = hashlib.sha256(wire(row)).hexdigest()
                rows.append(row)
            raw = b'\n'.join(wire(r) for r in rows)
            self.assertEqual(len(parse_chain(raw)), len(second.chain(raw)))
            index = rng.randrange(len(rows) - 1)
            swapped = rows[:]
            swapped[index], swapped[index + 1] = swapped[index + 1], swapped[index]
            missing = rows[:index] + rows[index + 1:]
            for altered in (swapped, missing):
                raw = b'\n'.join(wire(r) for r in altered)
                with self.assertRaises(ContractError): parse_chain(raw)
                with self.assertRaises(second.Rejected): second.chain(raw)

    def test_json_parser_rejects_ambiguous_numbers_keys_and_unicode(self):
        from tether_engine.serde import parse_json
        for raw in (b'{"x":1,"x":2}', b'NaN', b'1e999', b'"\\ud800"', b'\xff'):
            with self.subTest(raw=raw):
                with self.assertRaises(ContractError): parse_json(raw)
                with self.assertRaises(second.Rejected): second.parse(raw)
        self.assertEqual(second.parse(b'\xef\xbb\xbf{"valid":true}'), {'valid': True})
        with self.assertRaises(second.Rejected): second.parse(b'[' * 129 + b'0' + b']' * 129)

    def test_logical_paths_agree_on_public_reserved_name_rules(self):
        from tether_engine.bundle_files import logical_parts
        for path in ('inputs.json', 'packets/evidence-α.json'):
            self.assertEqual(tuple(second.logical(path)), logical_parts(path))
        for path in ('../x', 'packets/a/..', 'CONIN$', 'COM0.bin', 'NUL .txt',
                     'e\u0301', 'foo:bar', 'foo\\bar', '/root', 'a//b', '\ud800'):
            with self.subTest(path=repr(path)):
                with self.assertRaises(ContractError): logical_parts(path)
                with self.assertRaises(second.Rejected): second.logical(path)


def parse_chain_as_json(raw):
    from tether_engine.serde import encode
    return encode(parse_chain(raw))


class IndependentFormatTests(unittest.TestCase):
    def setUp(self):
        from tether_engine.agents import ExtractiveBackend
        from tether_engine.artifacts import write_run
        from tether_engine.chrono import load_snapshot
        from tether_engine.contracts import Case
        from tether_engine.serde import decode, read_json
        from tether_engine.workflow import run_workflow
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.native = self.root / 'native'
        case = decode(Case, read_json(DEMO / 'case.json'))
        store = load_snapshot(DEMO / 'snapshot.json', case)
        self.case, self.store = case, store
        self.receipt_hash = write_run(self.native, run_workflow(case, store, ExtractiveBackend()), store, None)

    def primary(self, root=None, **kwargs):
        from tether_engine.artifacts import verify_run
        return verify_run(root or self.native, verify_sources=False, **kwargs)

    def documents(self, root):
        docs = {p.name: json.loads(p.read_text(encoding='utf-8')) for p in root.glob('*.json')}
        docs['trace'] = [json.loads(line) for line in (root / 'trace.jsonl').read_text(encoding='utf-8').splitlines()]
        return docs

    def reseal(self, root, docs):
        # Independent fixture serializer; resealing prevents a trivial byte-hash
        # failure from concealing the consistency relationship under test.
        previous = None
        for index, record in enumerate(docs['trace']):
            record.update(sequence=index, previous_sha256=previous)
            record.pop('sha256', None)
            record['sha256'] = hashlib.sha256(wire(record)).hexdigest()
            previous = record['sha256']
        trace = b''.join(wire(row) + b'\n' for row in docs['trace'])
        for name in ('trace.jsonl', 'journal.jsonl'): (root / name).write_bytes(trace)
        checksum = hashlib.sha256(wire(docs['inputs.json'])).hexdigest()
        docs['receipt.json']['input_fingerprint'] = docs['run.json']['input_fingerprint'] = checksum
        for name, value in docs.items():
            if name not in ('trace', 'receipt.json'):
                # Logical hashes sort keys; stored insertion order remains part
                # of the production dossier's declared display contract.
                (root / name).write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n',
                                         encoding='utf-8', newline='\n')
        receipt = docs['receipt.json']
        for name in receipt['outputs']: receipt['outputs'][name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
        (root / 'receipt.json').write_bytes(wire(receipt) + b'\n')

    def mutate(self, name, docs):
        receipt, run, trace = docs['receipt.json'], docs['run.json'], docs['trace']
        ready = next(s['category'] for s in run['plan'] if s['initial_status'] == 'ready')
        if name == 'output_omission': receipt['outputs'].pop('features.json')
        elif name == 'source_substitution': receipt['sources'][0]['sha256'] = '0' * 64
        elif name == 'source_omission':
            receipt['sources'] = [p for p in receipt['sources'] if p.get('role') is None]
        elif name == 'forged_coverage': run['coverage'][ready]['status'] = 'disabled'
        elif name == 'forged_call_count': run['calls'] += 1
        elif name == 'ledger_substitution': docs['ledger.json']['claims'][0]['evidence']['observation']['statement'] = 'Invented alteration'
        elif name == 'reordered_accounting':
            i = next(i for i, row in enumerate(trace) if row['event'] == 'dispatch')
            trace[i], trace[i+1] = trace[i+1], trace[i]
        elif name == 'omitted_finalize': trace.pop()
        elif name == 'omitted_commit':
            del trace[next(i for i, row in enumerate(trace) if row['event'] == 'claim_committed')]
        elif name == 'forged_finalize': trace[-1]['details']['status'] = 'failed'
        elif name == 'legacy_downgrade':
            receipt['software_version'] = '0.4.0'
            receipt.pop('admission_policy')
        else: raise AssertionError('Unknown public vector: ' + name)

    def test_supported_native_positive_and_no_source_reads(self):
        self.assertEqual(self.primary()['semantic_consistency'], 'verified')
        original = Path.open
        def guarded(path, *args, **kwargs):
            if not path.is_relative_to(self.native): raise AssertionError('Second checker opened an original')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', new=guarded):
            answer = second.verify(self.native, expected_sha256=self.receipt_hash)
        self.assertEqual(answer['assurance'], 'declared_completed_consistency')
        self.assertEqual(answer['external_anchor'], 'matched')
        self.assertEqual(answer['source_bytes'], 'not_checked')
        self.assertEqual(answer['scientific_validation'], 'not_established')

    def test_public_resealed_native_vectors_agree_for_specified_reasons(self):
        for vector in VECTORS['native_mutations']:
            with self.subTest(vector=vector['id']):
                root = self.root / vector['id']
                shutil.copytree(self.native, root)
                docs = self.documents(root)
                self.mutate(vector['id'], docs)
                self.reseal(root, docs)
                with self.assertRaisesRegex(ContractError, vector['production_reason']): self.primary(root)
                with self.assertRaises(second.Rejected) as error: second.verify(root)
                self.assertEqual(error.exception.reason, vector['secondary_reason'])

    def test_generated_forged_call_totals_never_receive_consistency_credit(self):
        docs = self.documents(self.native)
        for value in (True, 0.0, -1, 99999):
            altered = copy.deepcopy(docs)
            altered['run.json']['calls'] = value
            self.reseal(self.native, altered)
            with self.assertRaises(ContractError): self.primary()
            with self.assertRaises(second.Rejected) as error: second.verify(self.native)
            self.assertEqual(error.exception.reason, 'accounting')

    def test_decimal_usage_is_independently_summed_without_binary_rounding_drift(self):
        docs = self.documents(self.native)
        docs['run.json']['budget']['max_cost_usd'] = 1.0
        docs['inputs.json']['configuration']['budget']['max_cost_usd'] = 1.0
        calls = {}
        for row in docs['trace']:
            kind, detail = row['event'], row['details']
            if kind == 'plan': detail['configuration']['budget']['max_cost_usd'] = 1.0
            elif kind == 'dispatch':
                value = [0.1, 0.2][len(calls)] if len(calls) < 2 else 0.0
                calls[detail['attempt_id']] = value
                detail['reserved']['cost_usd'] = value
            elif kind == 'attempt_accounted': detail['usage']['cost_usd'] = calls[detail['attempt_id']]
            elif kind == 'review': detail['usage']['cost_usd'] = calls[detail['category'] + ':1']
        for key in ('usage', 'measured_usage'): docs['run.json'][key]['cost_usd'] = 0.3
        dossier = self.native / 'dossier.md'
        raw = dossier.read_bytes()
        self.assertIn(b'accounted cost: $0.0000', raw)
        self.assertIn(b'Measured cost: $0.0000', raw)
        dossier.write_bytes(raw.replace(b'accounted cost: $0.0000', b'accounted cost: $0.3000')
                           .replace(b'Measured cost: $0.0000', b'Measured cost: $0.3000'))
        self.reseal(self.native, docs)
        self.assertEqual(self.primary()['semantic_consistency'], 'verified')
        self.assertEqual(second.verify(self.native)['consistency'], 'verified_supported_completed_path')
        docs['run.json']['usage']['cost_usd'] = 0.1 + 0.2
        self.reseal(self.native, docs)
        with self.assertRaises(ContractError): self.primary()
        with self.assertRaises(second.Rejected) as error: second.verify(self.native)
        self.assertEqual(error.exception.reason, 'accounting')

    def test_explicit_legacy_bytes_cannot_gain_consistency(self):
        docs = self.documents(self.native)
        self.mutate('legacy_downgrade', docs)
        self.reseal(self.native, docs)
        with self.assertRaises(second.Rejected): second.verify(self.native, allow_legacy=True)
        answer = second.verify(self.native, allow_legacy=True, bytes_only=True)
        self.assertEqual(answer['consistency'], 'unavailable_legacy')
        self.assertEqual(self.primary(allow_legacy=True)['assurance'], 'byte_integrity')

    def test_unsupported_execution_returns_unavailable_instead_of_success(self):
        docs = self.documents(self.native)
        docs['run.json']['backend_id'] = 'recorded-selection-replay-v1'
        self.reseal(self.native, docs)
        with self.assertRaises(second.Unavailable) as error: second.verify(self.native)
        self.assertEqual(error.exception.reason, 'execution_profile_unavailable')
        self.assertEqual(second.verify(self.native, bytes_only=True)['assurance'], 'byte_integrity')

    def test_valid_budget_limited_run_is_explicitly_outside_second_checker_scope(self):
        from tether_engine.agents import ExtractiveBackend
        from tether_engine.artifacts import write_run
        from tether_engine.workflow import Budget, run_workflow
        output = self.root / 'budget-limited'
        result = run_workflow(self.case, self.store, ExtractiveBackend(), budget=Budget(max_calls=0))
        write_run(output, result, self.store, None)
        self.assertEqual(self.primary(output)['semantic_consistency'], 'verified')
        with self.assertRaises(second.Unavailable): second.verify(output)
        self.assertEqual(second.verify(output, bytes_only=True)['assurance'], 'byte_integrity')

    def test_bad_and_wrong_external_anchors_do_not_disable_anchoring(self):
        for value in ('', True, '0' * 63, '0' * 64):
            with self.subTest(anchor=value):
                with self.assertRaises(ContractError): self.primary(expected_receipt_sha256=value)
                with self.assertRaises(second.Rejected): second.verify(self.native, expected_sha256=value)
        self.assertEqual(second.verify(self.native, expected_sha256=self.receipt_hash.upper())['external_anchor'], 'matched')

    def make_bundle(self):
        from tether_engine.bundle import export_bundle
        output = self.root / 'bundle'
        export_bundle(self.native, output, source_roots=(DEMO,))
        return output

    def test_bundle_byte_agreement_and_explicit_replay_abstention(self):
        from tether_engine.bundle import verify_bundle
        root = self.make_bundle()
        expected = hashlib.sha256((root / 'bundle.json').read_bytes()).hexdigest()
        self.assertEqual(verify_bundle(root, replay=False)['byte_integrity'], 'verified')
        answer = second.verify(root, kind='bundle', bytes_only=True, expected_sha256=expected)
        self.assertEqual(answer['assurance'], 'byte_integrity')
        with self.assertRaises(second.Unavailable) as error: second.verify(root, kind='bundle')
        self.assertEqual(error.exception.reason, 'bundle_replay_unavailable')

    def test_bundle_substitution_omission_and_counter_shapes(self):
        from tether_engine.bundle import verify_bundle
        original = self.make_bundle()
        for name in ('omitted_object', 'substituted_bytes', 'boolean_size', 'traversal'):
            root = self.root / name
            shutil.copytree(original, root)
            manifest = json.loads((root / 'bundle.json').read_text())
            item = manifest['objects']['ledger.json']
            if name == 'omitted_object': manifest['objects'].pop('ledger.json')
            elif name == 'substituted_bytes': (root / 'objects/sha256' / item['sha256']).write_bytes(b'bad')
            elif name == 'boolean_size': item['bytes'] = True
            else: manifest['objects']['packets/../escape'] = copy.deepcopy(item)
            (root / 'bundle.json').write_bytes(wire(manifest) + b'\n')
            with self.subTest(vector=name):
                with self.assertRaises(ContractError): verify_bundle(root, replay=False)
                with self.assertRaises(second.Rejected): second.verify(root, kind='bundle', bytes_only=True)

    def test_hardlinked_bundle_objects_are_rejected(self):
        from tether_engine.bundle import verify_bundle
        root = self.make_bundle()
        member = next((root / 'objects/sha256').iterdir())
        os.link(member, self.root / 'extra-link')
        with self.assertRaises(ContractError): verify_bundle(root, replay=False)
        with self.assertRaises(second.Rejected) as error: second.verify(root, kind='bundle', bytes_only=True)
        self.assertEqual(error.exception.reason, 'linked_member')

    def test_checker_is_standalone_and_cannot_import_production(self):
        script = self.root / 'check.py'
        shutil.copyfile(ROOT / 'tools/independent_verify.py', script)
        tree = ast.parse(script.read_text())
        allowed = {'__future__', 'argparse', 'fractions', 'hashlib', 'json', 'math', 'os', 'pathlib', 're', 'stat', 'sys', 'unicodedata'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): self.assertTrue(all(a.name in allowed for a in node.names))
            if isinstance(node, ast.ImportFrom): self.assertIn(node.module, allowed)
        result = subprocess.run([sys.executable, '-I', '-B', str(script), str(self.native)], cwd=self.root,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)['assurance'], 'declared_completed_consistency')

    def test_reject_all_control_fails_positive_acceptance(self):
        def accept(checker):
            try: return checker(self.native).get('status') == 'passed'
            except second.Rejected: return False
        def reject_all(_): raise second.Rejected('deliberate_reject_all')
        self.assertTrue(accept(second.verify))
        self.assertFalse(accept(reject_all))


if __name__ == '__main__':
    unittest.main()
