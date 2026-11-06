import copy
import hashlib
from types import SimpleNamespace
import unittest

from asof.serde import fingerprint
from experiments.scifact_comparison.inputs import digest
from experiments.scifact_comparison.policy import CONFIGURATION, check_primary, validate_pair_decode


def fixture():
    docs = [dict(doc_id=i, title='Fictional title', abstract=['Fictional sentence.']) for i in range(5)]
    corpus = {d['doc_id']:d for d in docs}
    context = SimpleNamespace(queries={9:dict(id=9,claim='Fictional claim.')}, corpus=corpus,
        model=dict(configuration=copy.deepcopy(CONFIGURATION),producer_code=dict(sha256='a'*64)),
        document_hashes={k:digest(d) for k,d in corpus.items()},
        sentence_hashes={(i,0):hashlib.sha256(docs[i]['abstract'][0].encode()).hexdigest() for i in range(5)},
        model_manifest_sha256='b'*64, policy_sha256='c'*64,
        manifest=dict(archive=dict(sha256='d'*64),products=dict(corpus=dict(sha256='e'*64))))
    request = dict(id=9, claim='Fictional claim.', documents=docs)
    pairs = [dict(claim_id=9, abstract_id=i, input_document_sha256=digest(d), status='completed', model_dispatch=True,
                  prediction=dict(claim_id=9,abstract_id=i,predicted_label='SUPPORT' if i == 0 else 'NEI',
                                  predicted_rationale=[0], label_probs=[0.,0.,1.] if i == 0 else [0.,1.,0.], rationale_probs=[.9]),
                  observations=dict(token_count=10,memory=dict(peak_working_set_bytes=100))) for i,d in enumerate(docs)]
    claim = dict(condition='primary', id=9,status='produced',input_sha256=digest(request),
                 prediction=dict(id=9,evidence={'0':dict(label='SUPPORT',sentences=[0])}),wall_seconds=1.,cpu_seconds=.5)
    retrieved = [dict(doc_id=i,rank=i+1,score=.5,document_sha256=digest(d)) for i,d in enumerate(docs)]
    return context,request,claim,pairs,retrieved


class PolicyTests(unittest.TestCase):
    def test_valid_retains_tokens_and_frozen_result(self):
        args = fixture()
        accepted = check_primary(*args)
        self.assertEqual(accepted['measured_transformer_resources']['input_tokens'],50)
        self.assertEqual(accepted['candidate']['scientific_validation'],'not_performed')
        args[3][0]['observations']['token_count'] = 1
        self.assertEqual(accepted['measured_transformer_resources']['pair_observations'][0]['token_count'],10)

    def test_changed_source_rejected(self):
        args = fixture()
        args[1]['documents'][0]['abstract'][0] = 'Changed.'
        args[2]['input_sha256'] = digest(args[1])
        with self.assertRaisesRegex(ValueError,'document differs'):
            check_primary(*args)

    def test_changed_claim_rejected(self):
        args = fixture()
        args[1]['claim'] = 'Changed'
        args[2]['input_sha256'] = digest(args[1])
        with self.assertRaisesRegex(ValueError,'Claim text'):
            check_primary(*args)

    def test_request_hash_rejected(self):
        args = fixture()
        args[2]['input_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError,'input binding'):
            check_primary(*args)

    def test_incomplete_pair_rejected(self):
        args = fixture()
        args[3][0]['status'] = 'overlength'
        with self.assertRaisesRegex(ValueError,'not completed'):
            check_primary(*args)

    def test_changed_pair_order_rejected(self):
        args = fixture()
        args[3].reverse()
        with self.assertRaisesRegex(ValueError,'coverage/order'):
            check_primary(*args)

    def test_claim_cannot_change_pair_prediction(self):
        args = fixture()
        args[2]['prediction']['evidence']['0']['label'] = 'CONTRADICT'
        with self.assertRaisesRegex(ValueError,'assemble'):
            check_primary(*args)

    def test_changed_retrieval_rank_rejected_by_frozen_checker(self):
        args = fixture()
        args[4][0]['rank'] = 2
        with self.assertRaises(ValueError):
            check_primary(*args)

    def test_changed_retrieval_hash_rejected_by_frozen_checker(self):
        args = fixture()
        args[4][0]['document_sha256'] = 'f'*64
        with self.assertRaises(ValueError):
            check_primary(*args)

    def test_out_of_bounds_token_count(self):
        for count in (True,0,4097):
            args = fixture()
            args[3][0]['observations']['token_count'] = count
            with self.assertRaisesRegex(ValueError,'tokens'):
                check_primary(*args)

    def test_decode_threshold_tie(self):
        pair = dict(predicted_label='CONTRADICT',label_probs=[.5,.5,0.],
                    predicted_rationale=[0],rationale_probs=[.5,.4999])
        validate_pair_decode(pair,2)

    def test_inconsistent_label_rationale_or_probabilities_rejected(self):
        pair = fixture()[3][0]['prediction']
        for key,value in [('predicted_label','CONTRADICT'),('predicted_rationale',[]),
                          ('label_probs',[float('nan'),0.,1.]),('rationale_probs',[2.]),
                          ('label_probs',[.5,.5,.5]),('rationale_probs',[])]:
            bad = dict(pair,**{key:value})
            with self.assertRaises(ValueError):
                validate_pair_decode(bad,1)


if __name__ == '__main__':
    unittest.main()
