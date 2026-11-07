"""Fictional retrieval parity: the trained pair classifier is never called."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hashlib

from tether_engine.serde import canonical, encode, ContractError
from experiments.scifact_calibration.test_inputs import fixture, proof, write
from experiments.scifact_calibration.inputs import verify_preparation_transition


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        try:
            import numpy, scipy, sklearn
        except ImportError:
            self.skipTest('isolated SciFact numerical environment required')
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        path,frame,prepared=fixture(self.root)
        self.authority=verify_preparation_transition(path,proof(path)['sha256'])
        from experiments.scifact.baseline import fit_model,save_model
        import json
        corpus={row['doc_id']:encode(row) for row in self.authority.corpus}
        queries=[json.loads(x) for x in (prepared/'views/queries_fit.jsonl').read_bytes().splitlines()]
        pairs=[json.loads(x) for x in (prepared/'restricted/fit_pairs.jsonl').read_bytes().splitlines()]
        # Add the fictional NEI class missing from this source fixture's training pairs.
        pairs.append(dict(claim_id=queries[0]['id'],doc_id=42,label='NEI',rationale_sentences=[],rationale_sets=[],negative_basis='invented'))
        self.model=fit_model(corpus,queries,pairs)
        folder=self.root/'model';save_model(self.model,folder)
        self.descriptor=dict(model=proof(folder/'model.json'),arrays=proof(folder/'arrays.npz'))

    def test_exact_top_five_parity_without_classifier(self):
        from experiments.scifact_calibration.retrieval import rank_queries
        expected=[self.model.predict(encode(q),k=5,rationale_threshold=.5)['retrieved'] for q in self.authority.queries]
        with patch('experiments.scifact.baseline.probabilities',side_effect=AssertionError('classifier called')):
            result=rank_queries(self.authority,self.descriptor)
        self.assertEqual(encode(result['retrieval']),[dict(id=q['id'],retrieved=r) for q,r in zip(self.authority.queries,expected)])
        self.assertEqual(len(result['requests'])*5,result['scheduled_pairs'])
        self.assertTrue(all(set(r)=={'id','claim','documents'} for r in result['requests']))

    def test_purpose_and_top_k_fail_before_model_read(self):
        from experiments.scifact_calibration.retrieval import rank_queries
        with patch.object(Path,'open',side_effect=AssertionError('model opened')):
            with self.assertRaises(ContractError): rank_queries(self.authority,self.descriptor,purpose='predict')
            with self.assertRaises(ContractError): rank_queries(self.authority,self.descriptor,k=3)

    def test_changed_model_and_mismatched_corpus_fail(self):
        from experiments.scifact_calibration.retrieval import rank_queries
        path=Path(self.descriptor['arrays']['path']);path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaises(ContractError): rank_queries(self.authority,self.descriptor)

    def test_replaced_preparation_after_authority_fails(self):
        from experiments.scifact_calibration.retrieval import rank_queries
        path=Path(self.authority.frame_proof['path']);path.write_bytes(b'{}')
        with self.assertRaises(ContractError): rank_queries(self.authority,self.descriptor)


if __name__=='__main__': unittest.main()
