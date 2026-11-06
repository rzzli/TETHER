"""Fictional independent accounting checks, without production imports."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH=Path(__file__).with_name('audit.py')
spec=importlib.util.spec_from_file_location('independent_operational_audit',PATH)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def chain(rows):
    previous=None;result=[]
    for event,details in rows:
        row={'sequence':len(result),'event':event,'details':details,'previous_sha256':previous}
        previous=audit.sha(audit.canonical(row));row['sha256']=previous;result.append(row)
    return b''.join(audit.canonical(row)+b'\n' for row in result)


class IndependentAuditTests(unittest.TestCase):
    def test_command_recipe_resolves_hash_pinned_policy_without_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'policy.json';raw=audit.canonical({'fixed':True});path.write_bytes(raw)
            recipe={'command':['python','-I','-B','collect.py','--policy',str(path),'--policy-sha256',audit.sha(raw),'--stage-seconds','7200']}
            policy,seconds=audit.recipe_policy(recipe)
            self.assertEqual(policy,{'fixed':True});self.assertEqual(seconds,7200)
            path.write_bytes(b'{}')
            with self.assertRaises(ValueError):audit.recipe_policy(recipe)

    def test_chain_checks_content_and_allows_only_incomplete_tail(self):
        raw=chain([('reserved',{}),('done',{'bytes':10})])
        self.assertEqual(len(audit.verify_chain(raw)),2)
        self.assertEqual(len(audit.verify_chain(raw+b'{"partial":',allow_tail=True)),2)
        with self.assertRaises(ValueError):audit.verify_chain(raw.replace(b'"bytes":10',b'"bytes":11'))
        with self.assertRaises(ValueError):audit.verify_chain(raw+b'{"partial":')

    def test_model_measured_and_unresolved_reservations_are_distinct(self):
        reserved={'input_tokens':100,'output_tokens':20,'cost_usd':0.0}
        measured={'input_tokens':25,'output_tokens':4,'cost_usd':0.0}
        rows=[{'event':'study_dispatch','details':{'reserved':reserved}},
              {'event':'study_accounted','details':{'basis':'adapter_reported','usage':measured}}]
        value=audit.study_accounting(rows,True)
        self.assertEqual(value['measured_usage'],measured)
        self.assertEqual(value['estimated_usage']['input_tokens'],0)
        value=audit.study_accounting(rows[:1],True)
        self.assertEqual(value['estimated_usage'],reserved)
        self.assertTrue(value['unresolved_generation'])
        self.assertEqual(value['generation_attempts'],1)

    def test_double_dispatch_and_measured_excess_or_nonzero_cost_rejected(self):
        dispatched={'event':'study_dispatch','details':{'reserved':{'input_tokens':10,'output_tokens':2,'cost_usd':0.0}}}
        with self.assertRaises(ValueError):audit.study_accounting([dispatched,dispatched],True)
        for usage in [{'input_tokens':11,'output_tokens':1,'cost_usd':0.0},
                      {'input_tokens':1,'output_tokens':1,'cost_usd':1.0},
                      {'input_tokens':True,'output_tokens':1,'cost_usd':0.0}]:
            with self.assertRaises(ValueError):audit.study_accounting([dispatched,{'event':'study_accounted','details':{'basis':'adapter_reported','usage':usage}}],True)

    def test_request_known_bytes_and_failed_upper_bound_do_not_collapse(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'requests').mkdir()
            body=b'fictional body';(root/'requests/000.body').write_bytes(body)
            receipt={'status':'completed','dataset_id':'labbench_retrieved_literature','release_id':audit.sha(body),
                     'relative_path':'requests/000.body','sha256':audit.sha(body),'bytes':len(body),'url':'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=x',
                     'source_url':'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=x','http_status':200,'completed_at_utc':'2020-01-01T00:00:00Z'}
            receipt_raw=audit.canonical(receipt);(root/'requests/000.receipt.json').write_bytes(receipt_raw)
            first={'request_id':'000','url':receipt['url'],'kind':'search','status':'completed','byte_reservation':100,
                'accounted_bytes':len(body),'byte_accounting_basis':'retained_response_body','body_path':'requests/000.body',
                'body_sha256':audit.sha(body),'bytes':len(body),'http_status':200,'receipt_path':'requests/000.receipt.json','receipt_sha256':audit.sha(receipt_raw)}
            second={'request_id':'001','url':receipt['url'].replace('query=x','query=y'),'kind':'search','status':'failed','byte_reservation':100,
                'accounted_bytes':100,'byte_accounting_basis':'conservative_unmeasured_reservation','error_type':'TimeoutError','failure_cause':'TimeoutError'}
            rows=[first,second];events=[]
            for row in rows:
                events.append({'event':'retrieval_request_started','details':{key:row[key] for key in ('request_id','url','kind','byte_reservation')}|{'status':'started'}})
                events.append({'event':'retrieval_request_completed' if row['status']=='completed' else 'retrieval_request_failed','details':row})
            policy={'metadata_bytes':100,'article_bytes':200,'total_bytes':500,'max_queries':2,'max_articles':3}
            value=audit.request_accounting(root,rows,events,policy)
            self.assertEqual(value['known_response_body_bytes'],len(body))
            self.assertEqual(value['unknown_transfer_upper_bytes'],100)
            self.assertEqual(value['safety_accounted_bytes'],len(body)+100)
            bad=copy.deepcopy(rows);bad[1]['accounted_bytes']=0
            with self.assertRaises(ValueError):audit.request_accounting(root,bad,events,policy)
            (root/'requests/000.body').write_bytes(b'changed')
            with self.assertRaises(ValueError):audit.request_accounting(root,rows,events,policy)


if __name__=='__main__':unittest.main(verbosity=2)
