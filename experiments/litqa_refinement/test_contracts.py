import unittest

from tether_engine.serde import canonical, encode
from experiments.litqa_refinement import contracts as c


def query():
    return dict(id='00000000-0000-0000-0000-000000000001',question='What color is fictional Lumarin?',
                choices=['(A) Cobalt','(B) Amber','(C) Insufficient information to answer the question'])


def sources():
    text='Fictional Lumarin is cobalt.'
    return [dict(source_id='PMC1:body:p0000:c0-27',text=text,sha256=c.codecs.digest(text.encode()))]


def prior(*,index=0,status='accepted'):
    return c.candidate(query(),dict(answer_index=index,evidence_ids=[sources()[0]['source_id']]),
        producer_status='produced',original_admission_status=status,native_call_sha256='1'*64,
        generated_at_utc='2026-11-06T01:00:00+00:00',offered_ids=[s['source_id'] for s in sources()])


def critic():
    return dict(support='supported',evidence_ids=[sources()[0]['source_id']],criticism='The raw source states cobalt.',
                queries=[['Lumarin'],['color']])


def context():
    return c.critique(query(),prior(),sources(),critic(),native_status='completed',native_call_sha256='2'*64)


class ContractTests(unittest.TestCase):
    def test_control_is_frozen_and_never_evidence(self):
        p=prior();r=context()
        self.assertFalse(p['is_scientific_evidence']);self.assertFalse(r['is_scientific_evidence'])
        with self.assertRaises(TypeError):p['prediction']['answer_index']=1
        with self.assertRaises(TypeError):r['decoded']['queries'][0][0]='different'
        self.assertEqual(c.parse_critic(canonical(critic()),query(),p,sources())['support'],'supported')

    def test_candidate_binding_preserves_policy_rejection_and_failed_null(self):
        self.assertEqual(prior(status='rejected')['original_admission_status'],'rejected')
        missing=c.candidate(query(),None,producer_status='input_unavailable',original_admission_status='not_run',
                            native_call_sha256=None,generated_at_utc=None,offered_ids=())
        self.assertIsNone(missing['prediction'])
        wrong=encode(prior());wrong['query_sha256']='0'*64
        with self.assertRaises(ValueError):c.validate_candidate(query(),wrong)
        changed=query();changed['choices'][0]='(A) Green'
        with self.assertRaises(ValueError):c.validate_candidate(changed,prior())

    def test_strict_fields_duplicate_keys_and_offered_citations(self):
        values=[]
        x=critic();x['confidence']=0.8;values.append(canonical(x))
        values.append(canonical(critic()).replace(b'"supported"',b'"supported","support":"supported"'))
        x=critic();x['evidence_ids']=['unknown'];values.append(canonical(x))
        x=critic();x['evidence_ids']*=2;values.append(canonical(x))
        x=critic();x['evidence_ids']=[];values.append(canonical(x))
        for raw in values:
            with self.subTest(raw=raw),self.assertRaises(ValueError):c.parse_critic(raw,query(),prior(),sources())

    def test_utf8_bounds_and_term_safety(self):
        for text in ['é'*81,'x\nline']:
            x=critic();x['criticism']=text
            with self.assertRaises(ValueError):c.parse_critic(canonical(x),query(),prior(),sources())
        for terms in [[['a','b','c'],['d']],[['a'*49],['b']],[['PMC123'],['color']],
                      [['PMID 123'],['color']],[['PMID123'],['color']],[['PMCID123'],['color']],
                      [['NOT Lumarin'],['color']],[['https://x'],['color']],
                      [['Lumarin'],['lumarin']],[['10.1234/x'],['color']]]:
            x=critic();x['queries']=terms
            with self.subTest(terms=terms),self.assertRaises(ValueError):c.parse_critic(canonical(x),query(),prior(),sources())
        x=critic();x['criticism']='é'*80
        self.assertEqual(c.parse_critic(canonical(x),query(),prior(),sources())['criticism'],'é'*80)

    def test_null_prior_requires_not_assessable(self):
        missing=c.candidate(query(),None,producer_status='parse_failure',original_admission_status='not_run',
                            native_call_sha256='a'*64,generated_at_utc='2026-11-06T00:00:00Z',offered_ids=())
        with self.assertRaises(ValueError):c.parse_critic(canonical(critic()),query(),missing,sources())
        x=critic();x['support']='not_assessable';x['evidence_ids']=[]
        self.assertEqual(c.parse_critic(canonical(x),query(),missing,sources())['support'],'not_assessable')

    def test_unavailable_critic_cannot_invent_decoding(self):
        with self.assertRaises(ValueError):c.critique(query(),prior(),sources(),critic(),native_status='capacity',native_call_sha256=None)
        absent=c.critique(query(),prior(),sources(),None,native_status='capacity',native_call_sha256=None)
        self.assertEqual(c.validate_critique(query(),prior(),absent,sources()),absent)


if __name__=='__main__':unittest.main()
