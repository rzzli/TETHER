"""Independent resealing probes of relocated archive verification."""
import hashlib
import unittest

from tether_engine.archive.paths import ArchiveResolver
from tether_engine.serde import ContractError, read_json, write_json
from tests import test_archive_core as fixtures


class ArchiveCorePeerTests(unittest.TestCase):
    setUp = fixtures.ArchiveCoreTests.setUp
    relocate = fixtures.ArchiveCoreTests.relocate
    verify = fixtures.ArchiveCoreTests.verify

    def reseal(self, name, update):
        """Re-anchor deliberately altered outputs so tests reach semantic checks."""
        relocated = hasattr(self, 'resolver')
        path = self.resolver.resolve(str(self.output / name)) if relocated else self.output / name
        document = read_json(path)
        update(document)
        write_json(path, document)
        receipt_path = self.resolver.resolve(str(self.output / 'receipt.json')) if relocated else self.output / 'receipt.json'
        if name != 'receipt.json':
            receipt = read_json(receipt_path)
            receipt['outputs'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
            write_json(receipt_path, receipt)
        for item in self.files if relocated else ():
            physical = self.resolver.layout_path(item['logical_path'])
            item.update(sha256=hashlib.sha256(physical.read_bytes()).hexdigest(), bytes=physical.stat().st_size)
        self.anchor = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        if relocated:
            self.resolver = ArchiveResolver(self.bindings, self.files)

    def test_resealed_omitted_parent_proof_fails_inventory(self):
        def omit(receipt):
            parent = next(i for i,p in enumerate(receipt['sources']) if 'parents' in p)
            del receipt['sources'][parent]
        self.reseal('receipt.json', omit)
        with self.assertRaisesRegex(ContractError, 'proof inventory'):
            self.verify()

    def test_resealed_duplicate_source_proof_fails_inventory(self):
        self.reseal('receipt.json', lambda r:r['sources'].append(dict(r['sources'][0])))
        with self.assertRaisesRegex(ContractError, 'proof inventory'):
            self.verify()

    def test_resealed_call_accounting_fails_semantics(self):
        self.reseal('run.json', lambda r:r.update(calls=r['calls']+1))
        with self.assertRaisesRegex(ContractError, 'account|usage|call'):
            self.verify()

    def test_resealed_admission_fingerprint_fails(self):
        def corrupt(receipt):
            key=next(iter(receipt['admitted_fingerprints']))
            receipt['admitted_fingerprints'][key]='0'*64
        self.reseal('receipt.json',corrupt)
        with self.assertRaisesRegex(ContractError,'admitted fingerprints'):
            self.verify()

    def test_missing_code_inventory_must_not_report_verified(self):
        self.relocate()
        self.reseal('receipt.json',lambda r:r.update(code={}))
        with self.assertRaisesRegex(ContractError,'code|Code'):
            self.verify()


if __name__ == '__main__':
    unittest.main()
