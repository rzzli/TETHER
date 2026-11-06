"""Fictional independent-reconstruction controls; no production case access."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import reconstruct as r


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def pin(value):
    return {'sha256': hashlib.sha256(value).hexdigest(), 'bytes': len(value)}


def write_record(root, ident='fiction-A', status='completed', decision='accept'):
    root.mkdir()
    request = {'control_id': ident, 'bundle_root': 'invented', 'descriptor': {'path': 'descriptor.json', 'sha256': 'a'*64, 'bytes': 1}}
    result = {'schema_version': 1, 'control_id': ident, 'status': status, 'decision': {
        'schema_version': 1, 'control_id': ident, 'decision': decision,
        'stage': 'prepare_run', 'violated_obligations': [], 'checked_scope': [], 'observables': {}},
        'resources': {'operation_wall_seconds': 2.0, 'operation_cpu_seconds': 1.0}}
    request_raw, result_raw = raw(request)+b'\n', raw(result)+b'\n'
    (root/'request.json').write_bytes(request_raw); (root/'result.json').write_bytes(result_raw)
    events=[]; previous='0'*64
    for seq,(name,detail) in enumerate((('reserved',{'request_sha256':hashlib.sha256(raw(request)).hexdigest()}),('terminal',{'result':pin(result_raw)}))):
        event={'sequence':seq,'previous_sha256':previous,'event':name,'details':detail,'at_utc':'2026-01-01T00:00:00+00:00'}
        event['sha256']=hashlib.sha256(raw(event)).hexdigest(); previous=event['sha256']; events.append(event)
    journal=b''.join(raw(x)+b'\n' for x in events);(root/'journal.jsonl').write_bytes(journal)
    receipt={'schema_version':1,'kind':'inspect_policy_case','request':pin(request_raw),'result':pin(result_raw),'journal':pin(journal),'terminal_chain_sha256':previous}
    receipt_raw=raw(receipt)+b'\n';(root/'receipt.json').write_bytes(receipt_raw)
    return request,result,pin(receipt_raw)


def sample(request,result):
    content=raw(result).decode()
    return {'id':request['control_id'],'epoch':1,'input':raw(request).decode(),'target':'',
        'output':{'completion':content,'choices':[{'message':{'role':'assistant','content':content}}]},
        'scores':{'archive_scorer':{'value':'C','answer':result['decision']['decision']}},
        'metadata':{},'model_usage':{},'events':[
            {'event':'sample_init','sample':{'id':request['control_id'],'input':raw(request).decode(),'target':''}},
            {'event':'span_begin','type':'solver','name':'archive_solver'},
            {'event':'score','target':'','scorer':'archive_scorer','score':{'value':'C'}}],
        'error_retries':[]}


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[4]/'data/cache/inspect-independent-reconstruction-tests'
        base.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(dir=base);self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)

    def test_duplicate_and_nonfinite_core_json_rejected(self):
        for value in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":Infinity}',b'\xff'):
            with self.assertRaises((ValueError,UnicodeError)):r.parse(value)

    def test_pinned_record_and_changed_request_fail(self):
        request,result,receipt=write_record(self.root/'case')
        checked=r.case_record(self.root/'case',receipt['sha256'],request)
        self.assertEqual(checked['result'],result)
        (self.root/'case/request.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):r.case_record(self.root/'case',receipt['sha256'],request)

    def test_valid_byte_seal_cannot_relabel_case_identity(self):
        request,_,receipt=write_record(self.root/'case')
        expected={**request,'control_id':'fiction-B'}
        with self.assertRaises(ValueError):r.case_record(self.root/'case',receipt['sha256'],expected)

    def test_native_candidate_request_target_and_identity_joins(self):
        request,result,_=write_record(self.root/'case')
        native=sample(request,result)
        expected={'control_id':'fiction-A','decision':'accept','observables':{}}
        self.assertTrue(r.native_archive_join(native,request,result,expected)['native_correct'])
        for field,value in (('id','fiction-B'),('target','accept'),('input','another request')):
            bad={**native,field:value}
            with self.assertRaises(ValueError):r.native_archive_join(bad,request,result,expected)
        bad={**native,'output':{**native['output'],'completion':'{}'}}
        with self.assertRaises(ValueError):r.native_archive_join(bad,request,result,expected)

    def test_missing_errors_and_unsupported_stay_on_schedule(self):
        request,result,_=write_record(self.root/'case')
        expected=[{'control_id':'A','decision':'accept','observables':{}},{'control_id':'B','decision':'reject','observables':{}},{'control_id':'C','decision':'inspect_only','observables':{}}]
        rows=[{'control_id':'A','status':'completed','native_decision':'accept','decision_match':True,'full_match':True},
              {'control_id':'B','status':'error','native_decision':'error','decision_match':False,'full_match':False}]
        totals=r.aggregate(expected,rows)
        self.assertEqual(totals['scheduled'],3);self.assertEqual(totals['full_match'],1)
        self.assertEqual(totals['missing'],1);self.assertEqual(totals['errors'],1)
        self.assertEqual(totals['full_match_rate'],1/3);self.assertEqual(totals['false_admissions'],0)
        with self.assertRaises(ValueError):r.aggregate(expected,rows+[rows[0]])

    def test_observable_numbers_null_and_expected_subset(self):
        expected={'control_id':'A','decision':'accept','observables':{'feature_values':{'a':None},'dispatches':1}}
        actual={'control_id':'A','decision':'accept','observables':{'features':{'values':{'a':{'value':None},'extra':{'value':0.4}}},'calls':1}}
        self.assertTrue(r.compare(actual,expected)['full_match'])
        actual['observables']['calls']=True
        self.assertFalse(r.compare(actual,expected)['full_match'])
        actual['observables']['calls']=1;del actual['observables']['features']['values']['a']
        self.assertFalse(r.compare(actual,expected)['full_match'])

    def test_zip_native_log_and_duplicate_sample_rejected(self):
        request,result,_=write_record(self.root/'case');native=sample(request,result)
        path=self.root/'native.eval'
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('header.json',raw({'status':'success','eval':{'task':'fiction'},'stats':{},'results':{}}))
            z.writestr('samples/fiction-A_epoch_1.json',raw(native))
        self.assertEqual(r.native_log(path)['samples'][0]['id'],'fiction-A')
        bad=self.root/'duplicate.json';bad.write_bytes(raw({'status':'success','samples':[native,native]}))
        with self.assertRaises(ValueError):r.native_log(bad)

    def test_native_nan_unscored_is_not_core_nan_or_correct(self):
        native=r.parse_native(b'{"scores":{"archive_scorer":{"value":NaN,"reason":"unsupported"}}}')
        self.assertTrue(r.is_unscored(native['scores']['archive_scorer']))
        with self.assertRaises(ValueError):r.parse_native(b'{"model_usage":{"x":{"input_tokens":NaN}}}')

    def test_native_condensed_attachments_resolve_before_semantic_joins(self):
        request,result,_=write_record(self.root/'case');native=sample(request,result)
        native['attachments']={'input-key':native['input'],'result-key':native['output']['completion']}
        native['events'][0]['sample']['input']='attachment://input-key'
        native['output']['choices'][0]['message']['content']='attachment://result-key'
        path=self.root/'condensed.json';path.write_bytes(raw({'status':'success','samples':[native]}))
        decoded=r.native_log(path)['samples'][0]
        self.assertTrue(r.native_archive_join(decoded,request,result,{'control_id':'fiction-A','decision':'accept','observables':{}})['native_correct'])
        del native['attachments']['input-key'];path.write_bytes(raw({'status':'success','samples':[native]}))
        with self.assertRaises(ValueError):r.native_log(path)

    def test_statistics_are_descriptive_and_drop_no_positive_value(self):
        got=r.statistics([3.0,1.0,2.0])
        self.assertEqual(got,{'count':3,'sum':6.0,'median':2.0,'minimum':1.0,'maximum':3.0})
        self.assertEqual(r.statistics([])['count'],0)
        with self.assertRaises(ValueError):r.statistics([1.0,-1.0])

    def test_primary_count_projection_hand_computed_includes_failure(self):
        oracle=[{'control_id':'A','decision':'accept','observables':{}},
                {'control_id':'B','decision':'reject','observables':{}},
                {'control_id':'C','decision':'reject','observables':{}}]
        rows=[{'control_id':'A','status':'completed','decision':{'control_id':'A','decision':'accept','observables':{}}},
              {'control_id':'B','status':'completed','decision':{'control_id':'B','decision':'accept','observables':{}}},
              {'control_id':'C','status':'error','decision':None}]
        score=r.primary_counts(oracle,rows)
        self.assertEqual({k:score[k] for k in ('scheduled','completed','full_conformance','decision_match','false_admission','unscored')},
                         {'scheduled':3,'completed':2,'full_conformance':1,'decision_match':1,'false_admission':1,'unscored':1})
        self.assertEqual(score['full_conformance_per_scheduled'],1/3)
        self.assertEqual(score['cases'][0]['reason'],None)

    def test_global_audit_failure_cannot_be_completed_cell_conformance(self):
        frozen={'input_pins':{'fiction':{'sha256':'a'*64,'bytes':2}},'batch_input_pins':{'fiction':{'sha256':'a'*64,'bytes':2}},'audit_scope':'fictional'}
        audit={'files':1,'logical_bytes':2,'wall_seconds':0.1,'environment_inventory_files':1}
        result={'status':'partial','source_integrity':{'status':'failed','global_preflight':audit,'global_postflight':None,'error':'fictional source change','scope':'fictional'}}
        events=[{'event':'global_source_preflight','details':audit},{'event':'global_source_postflight_failed','details':{'error':'fictional source change'}}]
        checked=r.check_audit_record(frozen,result,events)
        self.assertFalse(checked['retained_integrity_passed'])
        result['status']='completed'
        with self.assertRaises(ValueError):r.check_audit_record(frozen,result,events)

    def test_batch_audit_partition_must_match_full_pin_values(self):
        frozen={'input_pins':{'fiction':{'sha256':'a'*64,'bytes':2}},'batch_input_pins':{'fiction':{'sha256':'b'*64,'bytes':2}},'audit_scope':'fictional'}
        with self.assertRaises(ValueError):r.check_audit_record(frozen,{},[])

    def test_exact_corpus_inventory_rejects_extra_file_and_empty_directory(self):
        corpus=self.root/'corpus';bundle=corpus/'bundles';bundle.mkdir(parents=True)
        (bundle/'one').mkdir();(bundle/'one/input.json').write_bytes(b'{}')
        original={'bundles':{'one/input.json':pin(b'{}')},'bundle_directories':['one']}
        content=raw(original);(corpus/'FROZEN.json').write_bytes(content)
        frozen={'corpus_root':str(corpus),'corpus':pin(content)}
        self.assertEqual(r.verify_corpus_inventory(frozen)['files'],1)
        (bundle/'unexpected').mkdir()
        with self.assertRaises(ValueError):r.verify_corpus_inventory(frozen)
        (bundle/'unexpected').rmdir();(bundle/'one/extra').write_bytes(b'new')
        with self.assertRaises(ValueError):r.verify_corpus_inventory(frozen)


if __name__=='__main__':unittest.main()
