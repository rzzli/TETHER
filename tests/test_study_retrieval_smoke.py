"""Recorded retrieval integration regressions; no real source or inference."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, encode
from tether_engine.study import retrieval_smoke as module
from tether_engine.study.proofs import capture_file
from tether_engine.study.retrieval_smoke import smoke, verify, RetrievalRecordedVerifier


TEMP = Path(__file__).resolve().parents[1] / 'data/cache'


class RetrievalSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(dir=TEMP)
        cls.root = Path(cls.tmp.name)/'recorded'
        cls.result = smoke(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_two_policy_cells_share_default_budget_and_verify(self):
        result = verify(self.root,self.result['receipt_sha256'])
        self.assertEqual(result['recorded_adapter_cells'],2)
        self.assertEqual(result['actual_model_calls'],0)
        self.assertEqual(result['fixture_declared_usage']['input_tokens'],128)
        self.assertEqual(result['scientific_validation'],'not_attempted')

    def test_external_anchor_and_no_output_reuse(self):
        with self.assertRaises(ContractError):
            verify(self.root,'0'*64)
        with self.assertRaises(FileExistsError):
            smoke(self.root)

    def test_public_stage_cannot_substitute_request_or_policy(self):
        verifier = RetrievalRecordedVerifier(self.root,self.result['run_id'])
        stage = verifier.prepare_stage('id_order_v1')
        bad = encode(stage)
        bad['original_request']['source_request']['evidence'][0]['statement']='fabricated'
        with self.assertRaises(ContractError):
            verifier.validate_payload(bad,verifier.prepare_payload(stage))
        with self.assertRaises(ContractError):
            verifier.prepare_stage('../foreign')

    def test_shared_expiry_precedes_parent_replay(self):
        verifier = RetrievalRecordedVerifier(self.root,self.result['run_id'],deadline=time.monotonic()-1)
        with patch.object(module,'verify_retrieval_preparation',side_effect=AssertionError('late parent read')):
            with self.assertRaises(ContractError):
                verifier.prepare_stage('id_order_v1')

    def test_replay_has_no_generation_process_or_network_dispatch(self):
        with patch.object(module.DeadlineRecordedBackend,'generate',side_effect=AssertionError('replay dispatched')):
            result = verify(self.root,self.result['receipt_sha256'])
        self.assertEqual(result['observed_model_usage']['input_tokens'],0)
        self.assertEqual(result['four_arm_manifests'],'preparation_only_no_four_arm_outputs')

    def test_resealed_summary_accounting_and_resource_alias_rejected(self):
        for kind in ('summary','resource'):
            target = Path(self.tmp.name)/('tampered-'+kind)
            shutil.copytree(self.root,target)
            if kind == 'summary':
                summary = json.loads((target/'summary.json').read_bytes())
                summary['fixture_declared_usage']['input_tokens'] = 999
                (target/'summary.json').write_bytes(canonical(summary))
            else:
                package = json.loads((target/'package-proof.json').read_bytes())
                name = next(iter(package['resources']))
                package['resources'][name]['relative_path'] = 'study/'+module.STIMULI
                (target/'package-proof.json').write_bytes(canonical(package))
            receipt = json.loads((target/'receipt.json').read_bytes())
            receipt['artifacts'] = {name:encode(capture_file(target/name,name)) for name in receipt['artifacts']}
            raw = canonical(receipt)
            (target/'receipt.json').write_bytes(raw)
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                verify(target,hashlib.sha256(raw).hexdigest())

    def test_extra_file_rejected(self):
        target = Path(self.tmp.name)/'extra'
        shutil.copytree(self.root,target)
        (target/'unlisted.txt').write_text('not an approved member')
        with self.assertRaises(ContractError):
            verify(target,self.result['receipt_sha256'])


class RetrievalFailureTests(unittest.TestCase):
    def test_recorded_timeout_retains_one_attempt_no_success_and_no_retry(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            target = Path(tmp)/'timeout'
            real_document=module._document
            def timeout_document(stage,payload):
                doc=encode(real_document(stage,payload))
                doc['outcome']='timeout'
                return doc
            with patch.object(module,'_document',side_effect=timeout_document):
                with self.assertRaises(TimeoutError):
                    smoke(target)
            self.assertFalse((target/'receipt.json').exists())
            self.assertTrue((target/'failure.json').is_file())
            self.assertTrue((target/'cells/id_order_v1/failure.json').is_file())
            self.assertFalse((target/'cells/literal_case_overlap_then_id_v1').exists())
            failure=json.loads((target/'failure.json').read_bytes())
            self.assertEqual(failure['attempted_cells'],['id_order_v1'])
            self.assertEqual(failure['accepted_cells'],[])

    def test_interruption_during_retrieval_preserves_terminal_failure(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            target=Path(tmp)/'interrupted'
            with patch.object(module,'prepare_retrieval',side_effect=KeyboardInterrupt) as call:
                with self.assertRaises(KeyboardInterrupt):
                    smoke(target)
            self.assertEqual(call.call_count,1)
            self.assertTrue((target/'failure.json').is_file())
            self.assertFalse((target/'receipt.json').exists())

    def test_write_failure_preserves_primary_and_never_dispatches(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            target=Path(tmp)/'write-failure'
            with patch.object(module,'_write',side_effect=OSError('invented device failure')):
                with patch.object(module.DeadlineRecordedBackend,'generate',side_effect=AssertionError('must not dispatch')):
                    with self.assertRaisesRegex(OSError,'invented device failure'):
                        smoke(target)
            self.assertTrue((target/'journal.jsonl').is_file())
            self.assertFalse((target/'receipt.json').exists())

    def test_concurrent_reservation_has_one_owner_and_no_dispatch(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            target=Path(tmp)/'concurrent'
            def attempt():
                try:
                    smoke(target)
                except BaseException as error:
                    return type(error)
                return None
            with patch.object(module,'prepare_retrieval',side_effect=KeyboardInterrupt) as call:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results=list(pool.map(lambda _:attempt(),range(2)))
            self.assertEqual(call.call_count,1)
            self.assertCountEqual(results,[KeyboardInterrupt,FileExistsError])
            self.assertFalse((target/'receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
