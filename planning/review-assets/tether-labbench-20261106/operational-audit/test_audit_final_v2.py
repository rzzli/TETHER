"""Fictional final-audit contradictions; no production code or answers imported."""
import copy
import base64
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('independent_final',Path(__file__).with_name('audit_final_v2.py'))
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
A=audit.A


def write(root,name,value):
    raw=A.canonical(value)+b'\n';path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {'path':name,'bytes':len(raw),'sha256':A.sha(raw)}


def source_manifest():
    case={'id':'q1','ordinal':0,'status':'completed','sealed_at_utc':'2026-11-06T00:00:01+00:00',
        'coverage':{'retained_articles':1},'byte_accounting':{'known_response_body_bytes':20,
        'unknown_transfer_upper_bytes':0,'safety_accounted_bytes':20,'selected_text_bytes':10,
        'basis':'verified_retrieval_and_passage_outputs'}}
    return {'status':'completed','schedule':['q1'],'cases':[case],'fatal':None,'cutoff':'2026-11-06T00:00:02+00:00',
        'totals':{'scheduled':1,'counts':{'completed':1,'failed':0,'interrupted':0,'unexecuted':0},
        'known_response_body_bytes':20,'unknown_transfer_upper_bytes':0,'safety_accounted_bytes':20,
        'selected_text_bytes':10,'cases_with_sources':1,'completed_without_sources':0}}


def produced(root):
    candidate={'answer_index':0,'evidence_ids':['p1']}
    query={'id':'q1','question':'Which?','choices':['(A) Yes','(B) Insufficient information to answer the question']}
    sources=[{'source_id':'p1','text':'Fact','sha256':A.sha(b'Fact')}]
    payload={'prompt':'fictional'}
    request={'query':query,'sources':sources,'payload_sha256':A.sha(A.canonical(payload))}
    context={'task_id':'q1','request_sha256':A.sha(A.canonical(request)),
        'query_sha256':A.sha(A.canonical(query)),'sources_sha256':A.sha(A.canonical(sources))}
    decision={'accepted':True,'reason':None,'prediction':candidate,'request_sha256':A.sha(A.canonical(request)),
        'context_sha256':A.sha(A.canonical(context)),'semantic_support':'unevaluated'}
    values={'candidate':candidate,'session_response':candidate,'request':request,'payload':payload,
        'context':context,'sources':sources,'decision':decision}
    artifacts={key:write(root,key+'.json',value) for key,value in values.items()}
    row={'id':'q1','producer_status':'produced','check_status':'accepted','prediction':candidate,'reason':None}
    return {'id':'q1','ordinal':0,'disposition':row,'artifacts':artifacts},query


class FinalAuditTests(unittest.TestCase):
    def test_actual_amendment_hash_only_source_proofs_are_both_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);old=root/'old.py';new=root/'new.py';old.write_bytes(b'old code');new.write_bytes(b'new code')
            before=A.sha(old.read_bytes());after=A.sha(new.read_bytes());code='experiments/labbench/run.py'
            frozen={key:key for key in ('queries','configuration','generation_limits','alias','model_receipt','generation_output')}
            frozen['code_pins']={code:before}
            amended={**frozen,'schema_version':1,'kind':'labbench_generation_freeze','original_freeze':{'sha256':'c'*64},
                'mode':'benchmark','scheduled_count':199,'code_pins':{code:after},'change_control':{'changed_files':[code],
                'previous_sha256':before,'new_sha256':after,'reason':'cache path correction',
                'old_source':{'path':str(old),'sha256':before},'new_source':{'path':str(new),'sha256':after}}}
            audit.generation_amendment(frozen,'c'*64,amended)
            old.write_bytes(b'changed old code')
            with self.assertRaises(ValueError):audit.generation_amendment(frozen,'c'*64,amended)
            old.write_bytes(b'old code');new.write_bytes(b'changed new code')
            with self.assertRaises(ValueError):audit.generation_amendment(frozen,'c'*64,amended)

    def test_collection_totals_and_cutoff_are_reconstructed(self):
        manifest=source_manifest();self.assertEqual(audit.collection_totals(manifest,['q1'],100),manifest['totals'])
        for field,value in [('known_response_body_bytes',21),('scheduled',0)]:
            bad=copy.deepcopy(manifest);bad['totals'][field]=value
            with self.assertRaises(ValueError):audit.collection_totals(bad,['q1'],100)
        manifest['cutoff']='2026-11-06T00:00:00+00:00'
        with self.assertRaises(ValueError):audit.collection_totals(manifest,['q1'],100)

    def test_failed_collection_cannot_undercharge_or_grant_sources(self):
        manifest=source_manifest();case=manifest['cases'][0];case.update(status='failed',coverage=None,selected=None,task_sources=None)
        case['byte_accounting'].update(known_response_body_bytes=0,unknown_transfer_upper_bytes=100,safety_accounted_bytes=100,
            selected_text_bytes=0,basis='conservative_whole_case_reservation_until_source_seal')
        manifest.update(status='partial',fatal={'reason':'fictional'})
        manifest['totals'].update(counts={'completed':0,'failed':1,'interrupted':0,'unexecuted':0},
            known_response_body_bytes=0,unknown_transfer_upper_bytes=100,safety_accounted_bytes=100,selected_text_bytes=0,cases_with_sources=0)
        audit.collection_totals(manifest,['q1'],100)
        case['byte_accounting']['unknown_transfer_upper_bytes']=0
        with self.assertRaises(ValueError):audit.collection_totals(manifest,['q1'],100)
        case['byte_accounting']['unknown_transfer_upper_bytes']=100;case['task_sources']={'path':'unexpected'}
        with self.assertRaises(ValueError):audit.collection_totals(manifest,['q1'],100)

    def test_exact_inventory_rejects_undeclared_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);proof=write(root,'one.json',{'ok':True});declared={'one.json':{k:proof[k] for k in ('sha256','bytes')}}
            self.assertEqual(audit.inventory(root,declared,set()),proof['bytes'])
            write(root,'extra.json',{})
            with self.assertRaises(ValueError):audit.inventory(root,declared,set())
            (root/'extra.json').unlink();(root/'one.json').write_bytes(b'changed')
            with self.assertRaises(ValueError):audit.inventory(root,declared,set())

    def test_same_candidate_and_request_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);case,query=produced(root);audit.candidate_join(root,case,query)
            request=A.parse(A.read_proof(root,case['artifacts']['request']));payload=A.parse(A.read_proof(root,case['artifacts']['payload']))
            body=A.canonical({'prompt':payload['prompt'],'content':A.canonical(case['disposition']['prediction']).decode(),'tokens_evaluated':2,'tokens_predicted':3})
            wrapper={'body_base64':base64.b64encode(body).decode(),'body_sha256':A.sha(body),'http_status':200,'complete':True,
                'request_sha256':A.sha(A.canonical(request)),'payload_sha256':A.sha(A.canonical(payload))}
            report={'calls':1,'measured_usage':{'input_tokens':2,'output_tokens':3,'cost_usd':0.0},'estimated_usage':dict(A.ZERO)}
            case['accounting']={'generation_attempts':1,'measured_usage':report['measured_usage'],'estimated_usage':dict(A.ZERO)}
            token_body=A.canonical({'tokens':[1,2]})+b'\n'
            case['artifacts']['tokenization_body']=write(root,'tokenization/body.bin',{'tokens':[1,2]})
            case['artifacts']['tokenization']=write(root,'tokenization/result.json',{'body_base64':base64.b64encode(token_body).decode(),
                'body_sha256':A.sha(token_body),'complete':True,'http_status':200,'payload_sha256':wrapper['payload_sha256'],'token_count':2})
            values={'request.json':request,'payload.json':payload,'configuration.json':{},'raw-response.bin':wrapper,
                'response.json':case['disposition']['prediction'],'report.json':report,'journal.jsonl':{'fixture_only':True}}
            proofs={key:write(root,'session/'+key,value) for key,value in values.items()}
            receipt={'outputs':{key:{'sha256':p['sha256'],'bytes':p['bytes'],'logical_id':key} for key,p in proofs.items()}}
            case['artifacts']['session_receipt']=write(root,'session/receipt.json',receipt)
            events=[{'event':'study_response_captured','details':{'content_sha256':proofs['raw-response.bin']['sha256']}},
                {'event':'study_response_accepted','details':{'response_sha256':A.sha(A.canonical(case['disposition']['prediction']))}},
                {'event':'study_completed','details':{'report_sha256':A.sha(A.canonical(report))}}]
            audit.verify_session_bytes(root,case,events)
            case['disposition']['prediction']={'answer_index':1,'evidence_ids':[]}
            with self.assertRaises(ValueError):audit.candidate_join(root,case,query)
            case,query=produced(root)
            case['artifacts']['request']=write(root,'request.json',{'query':query,'sources':[],'payload_sha256':'0'*64})
            with self.assertRaises(ValueError):audit.candidate_join(root,case,query)

    def test_repeated_dispatch_and_undercharged_unresolved_are_rejected(self):
        reserved={'input_tokens':100,'output_tokens':20,'cost_usd':0.0}
        events=[{'event':'study_dispatch','details':{'reserved':reserved}}]
        expected=A.study_accounting(events,True)
        self.assertTrue(audit.accounting_join(events,True,expected)['unresolved_generation'])
        with self.assertRaises(ValueError):audit.accounting_join(events+events,True,expected)
        bad=copy.deepcopy(expected);bad['estimated_usage']['input_tokens']=0
        with self.assertRaises(ValueError):audit.accounting_join(events,True,bad)

    def test_generation_totals_include_failures_and_missing_cases_fail(self):
        zero=A.study_accounting([],False)
        index=[{'id':'a','ordinal':0,'accounting':zero,'disposition':{'producer_status':'unexecuted','check_status':'not_run'}}]
        totals={'scheduled':1,'generation_attempts':0,'tokenizer_attempts':0,'unresolved_generation':0,
            'measured_usage':dict(A.ZERO),'estimated_usage':dict(A.ZERO),'producer_statuses':{'unexecuted':1},'check_statuses':{'not_run':1}}
        self.assertEqual(audit.generation_totals(index,['a'],totals),totals)
        with self.assertRaises(ValueError):audit.generation_totals(index,['a','b'],totals)
        totals['check_statuses']={}
        with self.assertRaises(ValueError):audit.generation_totals(index,['a'],totals)

    def test_completed_generation_requires_terminal_cleanup(self):
        manifest={'status':'completed','cleanup':'normal_verified','failure_reason':None}
        terminal={'status':'completed','cleanup':'normal_verified','server_terminal':{'server_stopped':True}}
        index=[{'terminal_basis':'worker_terminal'}]
        audit.cleanup_join(manifest,terminal,index)
        terminal['server_terminal']['server_stopped']=False
        with self.assertRaises(ValueError):audit.cleanup_join(manifest,terminal,index)
        terminal['server_terminal']['server_stopped']=True;index[0]['terminal_basis']='parent_recovered_no_replay'
        with self.assertRaises(ValueError):audit.cleanup_join(manifest,terminal,index)

    def test_external_anchor_is_not_internal_self_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);proof=write(root,'record.json',{'self':'not authority'})
            self.assertEqual(audit.anchored(root/'record.json',proof['sha256']),{'self':'not authority'})
            with self.assertRaises(ValueError):audit.anchored(root/'record.json','0'*64)
        frozen={key:key for key in ('queries','configuration','generation_limits','alias','model_receipt','generation_output')}
        frozen['code_pins']={'experiments/labbench/run.py':'a'*64,'experiments/labbench/model.py':'b'*64}
        amended={**frozen,'schema_version':1,'kind':'labbench_generation_freeze','original_freeze':{'sha256':'c'*64},
            'mode':'benchmark','scheduled_count':199,'code_pins':{**frozen['code_pins'],'experiments/labbench/run.py':'d'*64},
            'change_control':{'changed_files':['experiments/labbench/run.py'],'previous_sha256':'a'*64,'new_sha256':'d'*64,'reason':'cache root correction'}}
        audit.generation_amendment(frozen,'c'*64,amended)
        amended['configuration']='changed prompt'
        with self.assertRaises(ValueError):audit.generation_amendment(frozen,'c'*64,amended)


if __name__=='__main__':unittest.main(verbosity=2)
