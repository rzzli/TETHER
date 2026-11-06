import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.scifact_comparison.audit import verify_outputs, file_sha
from experiments.scifact_comparison.inputs import encoded
from experiments.scifact_comparison.worker import Writer, process_requests


class FakeSolver:
    def predict(self,claims,corpus,*,event,**unused):
        cid,did = claims[0]['id'],corpus[0]['doc_id']
        event(event='pair_started',claim_id=cid,abstract_id=did)
        pair = dict(claim_id=cid,abstract_id=did,predicted_label='SUPPORT',predicted_rationale=[0],
                    label_probs=[0.,0.,1.],rationale_probs=[.75])
        observation = dict(claim_id=cid,abstract_id=did,token_count=10,memory=dict(peak_working_set_bytes=10))
        event(event='pair_completed',status='completed',prediction=pair,**observation)
        return dict(status='completed',pair_predictions=[pair],observations=[observation])


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.requests = [dict(id=1,claim='Fictional',documents=[dict(doc_id=2,title='Fictional',abstract=['Fictional sentence.'])])]
        request_sha = hashlib.sha256(b''.join(encoded(r)+b'\n' for r in self.requests)).hexdigest()
        writer = Writer(self.root,1024**2)
        writer.publish('recipe.json',dict(condition='primary',schedule=[1],requests=dict(sha256=request_sha)))
        writer.publish('MODEL.json',dict(metadata=dict(hparams=dict(label_threshold=None,rationale_threshold=.5))))
        writer.event('inputs_admitted',requests_sha256=request_sha,condition='primary',references_read=False)
        counts = process_requests(self.requests,FakeSolver(),writer,'primary',expected_k=1)
        writer.publish('REPORT.json',dict(status='schedule_accounted',counts=counts))
        writer.event('condition_completed',counts=counts)
        writer.publish('RECEIPT.json',dict(status='complete',files=dict(writer.files),
            journal_last_sha256=writer.previous,journal_records=writer.sequence,
            recipe_sha256=file_sha(self.root/'recipe.json'),requests_sha256=request_sha))
        writer.close()

    def audit(self):
        return verify_outputs(self.root,file_sha(self.root/'RECEIPT.json'),self.requests,
                              expected_condition='primary',expected_k=1)

    def tamper_and_reseal(self,name,edit):
        path = self.root/name
        value = json.loads(path.read_bytes())
        edit(value)
        path.write_bytes(encoded(value)+b'\n')
        receipt = json.loads((self.root/'RECEIPT.json').read_bytes())
        receipt['files'][name] = dict(bytes=path.stat().st_size,sha256=file_sha(path))
        (self.root/'RECEIPT.json').write_bytes(encoded(receipt)+b'\n')

    def test_complete_fixture(self):
        self.assertEqual(self.audit()['counts']['completed_pairs'],1)

    def test_corrupt_output_without_resealing(self):
        (self.root/'pairs/1-2.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'Sealed output'):
            self.audit()

    def test_resealed_pair_contradicts_journal(self):
        self.tamper_and_reseal('pairs/1-2.json',lambda p:p['prediction'].update(predicted_label='CONTRADICT'))
        with self.assertRaisesRegex(ValueError,'Pair commit'):
            self.audit()

    def test_accounting_cannot_be_rewritten(self):
        self.tamper_and_reseal('REPORT.json',lambda p:p['counts'].update(completed_pairs=17))
        with self.assertRaisesRegex(ValueError,'accounting'):
            self.audit()

    def test_extra_file_rejected(self):
        (self.root/'extra.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'inventory'):
            self.audit()

    def test_missing_file_rejected(self):
        (self.root/'claims/1.json').unlink()
        with self.assertRaisesRegex(ValueError,'Sealed output'):
            self.audit()

    def test_changed_requests_rejected(self):
        self.requests[0]['claim'] = 'Substituted'
        with self.assertRaisesRegex(ValueError,'request bytes'):
            self.audit()

    def test_journal_corruption_rejected(self):
        path = self.root/'journal.jsonl'
        path.write_bytes(path.read_bytes().replace(b'claim_started',b'claim_altered',1))
        with self.assertRaisesRegex(ValueError,'hash chain'):
            self.audit()


if __name__ == '__main__':
    unittest.main()
