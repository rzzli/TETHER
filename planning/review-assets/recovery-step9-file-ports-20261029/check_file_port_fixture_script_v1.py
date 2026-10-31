"""Check fictional fixture interchange only; no port implementation under test."""
import ast
import copy
from dataclasses import FrozenInstanceError
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'file_port_fixture_script_v1.py'
FIXTURES=HERE/'FILE-PORTS-FIXTURES-v2.json'
PROOF=HERE/'FILE-PORTS-FIXTURE-CALLABLE-PROOF-v1.json'


def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def main():
    assert not PROOF.exists()
    paths=[SOURCE,Path(__file__),FIXTURES,HERE/'FILE-PORTS-FIXTURE-FREEZE-v2.json',HERE/'FILE-PORTS-FIXTURE-SCHEMA-v2.json',HERE/'FILE-PORTS-FIXTURE-SCHEMA-FREEZE-v2.json',HERE/'FILE-PORTS-ROOT-FIXTURE-SCOPE-v1.json',HERE/'FILE-PORTS-ROOT-BOOL-DOMAIN-REVIEW-v1.json']
    before={str(p):pin(p) for p in paths}
    spec=importlib.util.spec_from_file_location('fictional_file_script',SOURCE)
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    data=json.loads(FIXTURES.read_text(encoding='utf-8'));cases=data['cases'];by={x['id']:x for x in cases}
    counts=dict(cases=0,api_script_returns=0,api_script_exceptions=0,clock_samples=0,hook_calls=0,required_families=16,additional_BOOL_controls=15)
    def echo(case):
        oracle=None
        def observer():return copy.deepcopy(case['script'][oracle.index]['before_projection'])
        oracle=m.FakeScript(case,observe=observer)
        for step in case['script']:
            index=oracle.index;expected=oracle._exceptions[index];actual=None
            try:
                if step['kind']=='api':
                    returned=oracle.api(step['name'],copy.deepcopy(step['arguments']))
                    if expected is None:
                        assert type(returned) is m.RawReturn
                        assert type(returned.value) is type(step['outcome']['raw_return']['value'])
                        assert returned.value==step['outcome']['raw_return']['value'];counts['api_script_returns']+=1
                elif step['kind']=='clock':
                    returned=oracle.clock()
                    if expected is None:assert returned==step['now_ns']/1000000000;counts['clock_samples']+=1
                else:oracle.hook(step['name']);counts['hook_calls']+=1
            except BaseException as error:actual=error
            if expected is not None:
                assert actual is expected
                if step['kind']=='api':counts['api_script_exceptions']+=1
            else:assert actual is None,repr(actual)
        oracle.assert_exhausted();return oracle

    class Checks(unittest.TestCase):
        def test_all84_callable_interchange_exact_dispatch_only(self):
            self.assertEqual(len(cases),84)
            with mock.patch('builtins.open',side_effect=AssertionError('No live file operation')):
                for case in cases:echo(case);counts['cases']+=1

        def test_required16_families_and_supplemental_signed_BOOL_domain(self):
            self.assertEqual({c['required_vector'] for c in cases if c['required_vector'] is not None},set(range(17)))
            self.assertEqual(sum(c['required_vector']==0 for c in cases),1)
            self.assertEqual(sum(c['required_vector'] is None for c in cases),15)
            for name in ('ReadFile','CloseHandle','CreateDirectoryW'):
                for value in (2,-1):
                    c=by['BOOL_'+name+'_'+str(value)]
                    step=next(x for x in c['script'] if x['kind']=='api' and x['name']==name)
                    raw=step['outcome']['raw_return'];self.assertIs(type(raw['value']),int);self.assertEqual(raw['value'],value)
                    self.assertEqual(c['expected']['disposition'],'primitive_complete')
                rejects=[c for c in cases if c['id'].startswith('BOOL_reject_'+name+'_')]
                self.assertEqual(len(rejects),3)
                for c in rejects:self.assertFalse(any(x['kind']=='api' for x in c['script']));self.assertEqual(c['expected']['disposition'],'control_rejected')

        def test_literal_ownership_count_and_late_write_expectations(self):
            for identity in ('open_NULL','open_unreturned'):
                c=by[identity];self.assertEqual(c['expected']['slots'][0]['close_attempts'],0);self.assertIsNone(c['expected']['slots'][0]['handle'])
                self.assertEqual(c['expected']['api_attempts']['CloseHandle'],0)
            f=by['namespace_owned_journal_reserve_failure']['expected'];self.assertTrue(f['namespace_owned']);self.assertFalse(f['reservation_ready']);self.assertEqual(f['api_attempts']['ReadFile'],0)
            self.assertEqual((by['read_hash']['expected']['known_read_bytes'],by['read_hash']['expected']['hashed_bytes'],by['read_hash']['expected']['captured_bytes']),(3,0,0))
            self.assertEqual((by['read_copy']['expected']['known_read_bytes'],by['read_copy']['expected']['hashed_bytes'],by['read_copy']['expected']['captured_bytes']),(3,3,0))
            failed=by['read_failed_count'];step=next(x for x in failed['script'] if x['kind']=='api' and x['name']=='ReadFile')
            self.assertEqual(step['outcome']['raw_return']['raw_count'],0);self.assertIs(step['outcome']['raw_return']['raw_count_defined'],False);self.assertTrue(failed['expected']['read_count_unknown'])
            late=by['output_registry_late_known_write']['expected'];self.assertEqual((late['known_write_bytes'],late['write_hash_bytes'],late['flushed_known_bytes']),(4,0,0));self.assertFalse(late['terminal_ack']);self.assertEqual(late['slots'][0]['close_state'],'not_dispatched_deadline')
            self.assertEqual(by['uncertain_close_not_retried']['expected']['slots'][0]['close_attempts'],1)
            retry=by['write_false_and_close_failure']['expected'];self.assertEqual(retry['primary'],'false_and_close_failure');self.assertEqual(retry['secondary'],['close_failed'])

        def test_namespace_readiness_and_no_API_after_hard_cutoff(self):
            baseline=by['success_baseline'];steps=baseline['script'];first_original=next(i for i,x in enumerate(steps) if x['kind']=='api' and x['name']=='CreateFileW' and x['arguments']['desired_access']==2147483648)
            self.assertTrue(any(x['kind']=='api' and x['name']=='CloseHandle' and x['arguments']['handle']==201 for x in steps[:first_original]))
            self.assertTrue(any(x['kind']=='api' and x['name']=='FlushFileBuffers' and x['arguments']['handle']==202 for x in steps[:first_original]))
            self.assertEqual(steps[first_original]['before_projection']['reservation_ready'],True)
            for c in cases:
                now=0
                for step in c['script']:
                    if step['kind']=='clock':now=step['now_ns']
                    elif step['kind']=='api':self.assertLess(now,300000000000,c['id'])
                self.assertIs(c['expected']['terminal_ack'],False)
                self.assertEqual(c['expected']['journal_recursive_events'],0)

        def test_search_end_roots_UTF16_units_and_early_B_counts(self):
            self.assertEqual(by['scan_empty']['expected']['api_attempts']['FindClose'],0)
            self.assertNotEqual(by['scan_initial18']['expected']['disposition'],'primitive_complete')
            c=by['scan_natural_end'];end=next(x for x in c['script'] if x['kind']=='api' and x['name']=='FindNextFileW')
            self.assertEqual(end['outcome']['raw_return']['last_error'],18);self.assertIs(end['outcome']['raw_return']['buffer_defined'],False);self.assertEqual(c['expected']['api_attempts']['FindClose'],1)
            self.assertEqual(by['scan_overflow']['facts'] if 'facts' in by['scan_overflow'] else by['scan_overflow']['request']['facts']['non_dot_successes_before_stop'],65)
            roots=by['roots_C_D_counted_once'];self.assertEqual(roots['plan']['U'],2);self.assertEqual(roots['expected']['api_attempts']['GetFileAttributesExW'],2)
            for size in (4096,4097):
                record=by['path_UTF16_'+str(size)]['path_records'][0]
                self.assertEqual(len(record['path'].encode('utf-16-le'))//2,size);self.assertLess(len(record['path']),size)
            for c in cases:
                if c['required_vector']==10:
                    self.assertEqual(c['initial']['known_read_bytes'],3);self.assertEqual(c['expected']['known_read_bytes'],3)
                    self.assertEqual(c['expected']['api_attempts']['CreateFileW'],0);self.assertEqual(c['expected']['api_attempts']['CloseHandle'],1)

        def test_strict_numeric_and_raw_return_domain_admission(self):
            base=by['success_baseline']
            for value in (True,-1,10**1000):
                c=copy.deepcopy(base);c['script'][0]['now_ns']=value
                with self.assertRaises(m.ScriptMismatch):m.validate_case(c)
            raw=dict(value=1,last_error=0,error_defined=False,raw_count=3,raw_count_defined=True,buffer_hex='616263',buffer_defined=True)
            for name in ('ReadFile','CloseHandle','CreateDirectoryW'):
                for value in (True,False,2**31,-2**31-1):
                    with self.assertRaises(m.ScriptMismatch):m.raw_return(name,dict(raw,value=value))
                for value in (2,-1):self.assertEqual(m.raw_return(name,dict(raw,value=value)).value,value)
            c=copy.deepcopy(base);c['script'][0]['now_ns']=600000000001
            with self.assertRaises(m.ScriptMismatch):m.validate_case(c)

        def test_exact_sequence_projection_and_deep_input_copy(self):
            c=copy.deepcopy(by['open_NULL']);oracle=m.FakeScript(c,observe=lambda:{})
            c['expected']['primary']='mutated';self.assertNotEqual(oracle.expected['primary'],'mutated')
            with self.assertRaises(m.ScriptMismatch):oracle.api('CreateFileW',{})
            c=copy.deepcopy(by['success_baseline']);oracle=m.FakeScript(c,observe=lambda:{})
            with self.assertRaises(m.ScriptMismatch):oracle.assert_exhausted()
            while oracle.index<len(c['script']):
                step=c['script'][oracle.index]
                try:
                    if step['kind']=='clock':oracle.clock()
                    elif step['kind']=='api':oracle.api(step['name'],step['arguments'])
                    else:oracle.hook(step['name'])
                except m.ScriptMismatch as error:self.assertEqual(str(error),'checkpoint_before_dispatch_mismatch');break
            else:self.fail('Missing registry projection was ignored')
            raw=m.raw_return('ReadFile',dict(value=2,last_error=0,error_defined=False,raw_count=3,raw_count_defined=True,buffer_hex='616263',buffer_defined=True))
            with self.assertRaises(FrozenInstanceError):raw.value=1

        def test_clock_hook_and_API_exception_identity_is_preconstructed(self):
            for kind in ('clock','hook','api'):
                c=copy.deepcopy(by['open_NULL'])
                if kind=='clock':c['script']=[dict(kind='clock',now_ns=0,raises={'class':'UnicodeError','message':'synthetic'},before_projection={})]
                elif kind=='hook':c['script']=[dict(kind='clock',now_ns=0,raises=None,before_projection={}),dict(kind='hook',name='hash_update',raises={'class':'KeyboardInterrupt','message':'synthetic'},before_projection={})]
                else:c=copy.deepcopy(by['open_unreturned'])
                # Recalculate dispatch counters only to author this synthetic interchange control.
                c['expected']['api_attempts']={n:0 for n in m.API_KEYS};c['expected']['api_returns']={n:0 for n in m.API_KEYS}
                for s in c['script']:
                    if s['kind']=='api':c['expected']['api_attempts'][s['name']]+=1;c['expected']['api_returns'][s['name']]+=s['outcome']['raise'] is None
                echo(c)

        def test_source_scope_no_filesystem_or_port_algorithms(self):
            imports=[]
            for node in ast.walk(ast.parse(SOURCE.read_text(encoding='utf-8'))):
                if isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
                elif isinstance(node,ast.ImportFrom):imports.append(node.module)
                elif isinstance(node,ast.Call) and isinstance(node.func,ast.Name):self.assertNotIn(node.func.id,('open','exec','eval','compile','__import__'))
            self.assertEqual(set(imports),{'dataclasses','re','types'})

    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    stable=before=={str(p):pin(p) for p in paths}
    record=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),status='passed' if result.wasSuccessful() and stable else 'failed',source=pin(SOURCE),checker=pin(Path(__file__)),inputs=before,inputs_unchanged=stable,methods=result.testsRun,counts=counts,
                failures=[dict(test=str(t),traceback=s) for t,s in result.failures],errors=[dict(test=str(t),traceback=s) for t,s in result.errors],
                scope='Fixture interchange/closed source-domain and authored-data checks only. Fake echo calls return planned data; they do not validate any file port or compute expected ownership results.',
                expected_port_states_are_authored_not_observed=True,port_implementation_under_test=False,actual_API_calls=0,old_original_payload_operations=0,profile_qualified=False,runtime_authorized=False)
    with PROOF.open('x',encoding='utf-8') as out:json.dump(record,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),status=record['status'],methods=result.testsRun,counts=counts)))
    return 0 if record['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
