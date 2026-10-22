"""Independent exact-version, execution-seal and recipe regressions, offline."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from asof.serde import ContractError, canonical, fingerprint
from tools.science.registry_documents import verify_document
from tests import test_science_registry_documents as fixtures


class RegistryDocumentPeerTests(unittest.TestCase):
    def downloaded(self, root):
        return fixtures.RegistryDocumentTests().downloaded(root)

    def load(self, path):
        return json.loads(path.read_text(encoding='utf-8'))

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def reseal_receipt_and_journal(self, output, receipt):
        """Model an internally consistent but policy-ineligible fetch recipe."""
        receipt['control_sha256'] = hashlib.sha256((output / 'control.json').read_bytes()).hexdigest()
        self.write(output / 'receipt.json', receipt)
        events = [json.loads(line) for line in (output / 'journal.jsonl').read_text(encoding='utf-8').splitlines()]
        events[-1]['details']['receipt_sha256'] = hashlib.sha256((output / 'receipt.json').read_bytes()).hexdigest()
        previous = None
        for event in events:
            event.pop('sha256')
            event['previous_sha256'] = previous
            event['sha256'] = fingerprint(event)
            previous = event['sha256']
        (output / 'journal.jsonl').write_bytes(b''.join(canonical(event) + b'\n' for event in events))

    def test_same_size_body_and_receipt_rewrite_cannot_replace_committed_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request, output = self.downloaded(root)
            receipt = self.load(output / 'receipt.json')
            path = Path(receipt['body']['path'])
            body = path.read_bytes()
            changed = b'%PDF-1.7\n' + b'X' * (len(body) - 9)
            self.assertEqual(len(changed), len(body))
            path.write_bytes(changed)
            receipt['body']['sha256'] = hashlib.sha256(changed).hexdigest()
            self.write(output / 'receipt.json', receipt)
            with self.assertRaises(ContractError):
                verify_document(request, output, root)

    def test_missing_truncated_or_nonterminal_journal_cannot_finalize(self):
        for attack in ('missing', 'truncated', 'nonterminal'):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                request, output = self.downloaded(root)
                journal = output / 'journal.jsonl'
                lines = journal.read_bytes().splitlines(keepends=True)
                if attack == 'missing':
                    journal.unlink()
                elif attack == 'truncated':
                    journal.write_bytes(b''.join(lines[:-1]) + lines[-1][:len(lines[-1]) // 2])
                else:
                    journal.write_bytes(b''.join(lines[:-1]))
                with self.assertRaises((ContractError, FileNotFoundError)):
                    verify_document(request, output, root)

    def test_valid_chain_cannot_admit_weakened_frozen_control_recipe(self):
        changes = [('expected_sha256', '0' * 64), ('expected_format', 'html'),
                   ('max_bytes', 32 * 1024 * 1024), ('max_bytes', 1),
                   ('max_elapsed_seconds', 121), ('request_timeout_seconds', 41)]
        for field, value in changes:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                request, output = self.downloaded(root)
                control = self.load(output / 'control.json')
                control[field] = value
                self.write(output / 'control.json', control)
                receipt = self.load(output / 'receipt.json')
                self.reseal_receipt_and_journal(output, receipt)
                with self.assertRaises(ContractError):
                    verify_document(request, output, root)

    def test_alternative_version_url_cannot_substitute_with_a_consistent_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request, output = self.downloaded(root)
            other_url = request['url'].replace('_002.pdf', '_003.pdf')
            control = self.load(output / 'control.json')
            control['url'] = other_url
            self.write(output / 'control.json', control)
            receipt = self.load(output / 'receipt.json')
            receipt.update(requested_url=other_url, response_url=other_url)
            self.reseal_receipt_and_journal(output, receipt)
            with self.assertRaises(ContractError):
                verify_document(request, output, root)

    def test_unknown_prior_hash_is_valid_without_authenticity_or_truth_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request, output = self.downloaded(root)
            self.assertIsNone(request['expected_sha256'])
            result = verify_document(request, output, root)
            self.assertEqual(result['status'], 'source_linked_original_received')
            self.assertFalse(result['historical_availability_qualified'])
            self.assertFalse(result['prospective_authenticity_qualified'])
            self.assertFalse(result['clinical_scope_qualified'])
            self.assertFalse(result['clinical_label_contribution'])
