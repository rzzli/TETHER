"""Explicit all-v2 map and honest abort accounting; no subject import/run."""
import hashlib
from pathlib import Path

H=Path(__file__).resolve().parent


def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)


PARTIAL='''def partial_codec_counts(error,test_filename):
    """Read only exact frozen T.run local counters; never replay a test.

    Declared totals are not executed-case counts. If no exact frame/domain is
    available, return None with a reason instead of inventing zero accounting.
    """
    expected={'unique_bases','unique_byte_negatives','encode_calls','decode_calls','check_calls','getter_calls',
              'callback_exception_cases','value_refusal_cases','caller_mutation_cases','subject_methods'}
    try:
        tb=error.__traceback__
        for _ in range(128):
            if tb is None:break
            frame=tb.tb_frame
            if frame.f_code.co_filename==test_filename and frame.f_code.co_name=='run':
                value=frame.f_locals.get('counts')
                if type(value) is not dict or len(value)!=len(expected) or set(value)!=expected:
                    return dict(counts=None,complete=False,reason='pinned test frame counts shape unavailable')
                if any(type(x) is not int or not 0<=x<=(1<<63)-1 for x in value.values()):
                    return dict(counts=None,complete=False,reason='pinned test frame counters outside exact builtin integer domain')
                return dict(counts=dict(value),complete=False,reason='partial exact frozen T.run traceback-local counters at abort',
                    declared_not_executed_fields=['unique_bases','unique_byte_negatives','subject_methods'],
                    completed_method_outcomes=None,completed_method_outcomes_reason='T.run result did not return; remainder UNKNOWN')
            tb=tb.tb_next
    except BaseException:
        return dict(counts=None,complete=False,reason='counter observation failed; original conformance error preserved')
    return dict(counts=None,complete=False,reason='exact frozen T.run traceback frame absent; counts UNKNOWN')


'''


def map_v2(t):
    for old,new in [('role_ledger_codec_v1','role_ledger_codec_v2'),('role_owner_v1','role_owner_v2'),
                    ('role_file_ports_v1','role_file_ports_v2'),('continue_role_verification_v1','continue_role_verification_v2')]:
        t=t.replace(old,new)
    return t


def main():
    raw=(H/'run_role_aware_independent_v4.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='b75a2872293941398738492fa252f01dea7c19b364ca21f099d0d968f9961353'
    t=map_v2(raw.decode())
    t=once(t,'class Results(unittest.TextTestResult):',PARTIAL+'class Results(unittest.TextTestResult):')
    t=t.replace('-SOURCE-BINDING-v4.json','-SOURCE-BINDING-v5.json').replace("+'-PROOF-v4.json'","+'-PROOF-v5.json'").replace("+'-ATTEMPT-v4.json'","+'-ATTEMPT-v5.json'")
    t=t.replace('ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v4.json','ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v5.json')
    t=once(t,"    phase='UNBOUND';report_path=None",
        "    phase='UNBOUND';report_path=None;execution_stage='BOOTSTRAP';codec_started=False;codec_returned=False;legacy_started=False;codec_test_filename=None\n    codec_count_observation=dict(counts=None,complete=False,reason='codec conformance not started')")
    t=once(t,'        modules=D.load_exact_modules(source_pins)',"        execution_stage='SOURCE_DEFINITION'\n        modules=D.load_exact_modules(source_pins)")
    t=once(t,'            codec_result=T.run(facade,corpus)',
        "            execution_stage='CODEC_CONFORMANCE';codec_started=True;codec_test_filename=T.__file__\n            codec_result=T.run(facade,corpus)\n            codec_returned=True\n            codec_count_observation=dict(counts=dict(codec_result['counts']),complete=True,reason='exact frozen T.run returned measured counters')")
    t=once(t,'            result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)',
        "            execution_stage='LEGACY_CONFORMANCE';legacy_started=True\n            result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)")
    t=once(t,'        record=dict(schema_version=1,status=status,phase=phase,common_post_suite_late_veto=common_post_suite_late_veto,',
        '        record=dict(schema_version=1,status=status,phase=phase,execution_stage=execution_stage,codec_conformance_started=codec_started,codec_result_returned=codec_returned,codec_count_observation=codec_count_observation,common_post_suite_late_veto=common_post_suite_late_veto,')
    t=once(t,"    except BaseException as err:\n        record=dict(schema_version=1,status='SETUP_OR_HARNESS_ERROR_FIRST_RESULT_PRESERVED',phase=phase,error_class=type(err).__name__,",
        "    except BaseException as err:\n        if codec_started and not codec_returned:codec_count_observation=partial_codec_counts(err,codec_test_filename)\n        failure_status='CODEC_CONFORMANCE_ABORTED_FIRST_RESULT_PRESERVED' if codec_started else ('LEGACY_CONFORMANCE_ABORTED_FIRST_RESULT_PRESERVED' if legacy_started else 'SETUP_OR_IMPORT_ERROR_FIRST_RESULT_PRESERVED')\n        record=dict(schema_version=1,status=failure_status,phase=phase,execution_stage=execution_stage,codec_conformance_started=codec_started,codec_result_returned=codec_returned,codec_count_observation=codec_count_observation,methods=None,method_outcomes=None,method_outcomes_reason='conformance result did not return; not zero completed-method accounting' if codec_started or legacy_started else 'conformance not started',error_class=type(err).__name__,")
    with (H/'run_role_aware_independent_v5.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
    raw=(H/'run_role_aware_extensions_v1.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='832600c037d9518d7645531d33437547a2b96a9245985db5f2d1d41cee9ee625'
    t=map_v2(raw.decode())
    t=once(t,"        roles['role_ledger_codec_v2']=modules['role_ledger_codec_v2']",
        "        roles['role_ledger_codec_v1']=modules['role_ledger_codec_v2'] # HARNESS-ONLY logical role for unchanged test module.")
    t=t.replace('ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v1.json','ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v2.json')
    t=t.replace("+'-PROOF-v1.json'","+'-PROOF-v2.json'").replace("+'-ATTEMPT-v1.json'","+'-ATTEMPT-v2.json'")
    t=t.replace('ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v1.json','ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v2.json')
    t=once(t,"phase='UNBOUND';report_path=None;indexed_observations=[];extension_observations=[]",
        "phase='UNBOUND';report_path=None;indexed_observations=[];extension_observations=[];execution_stage='BOOTSTRAP';extensions_started=False;extensions_returned=False")
    t=once(t,'        modules=D.load_exact_modules(source_pins)',"        execution_stage='SOURCE_DEFINITION'\n        modules=D.load_exact_modules(source_pins)")
    t=once(t,'        result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)',
        "        execution_stage='EXTENSIONS_CONFORMANCE';extensions_started=True\n        result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)\n        extensions_returned=True")
    t=once(t,'        record=dict(schema_version=1,status=status,phase=phase,common_post_suite_late_veto=common_post_suite_late_veto,',
        '        record=dict(schema_version=1,status=status,phase=phase,execution_stage=execution_stage,extensions_conformance_started=extensions_started,extensions_result_returned=extensions_returned,common_post_suite_late_veto=common_post_suite_late_veto,')
    t=once(t,"    except BaseException as err:\n        record=dict(schema_version=1,status='SETUP_OR_HARNESS_ERROR_FIRST_RESULT_PRESERVED',phase=phase,error_class=type(err).__name__,",
        "    except BaseException as err:\n        failure_status='EXTENSIONS_CONFORMANCE_ABORTED_FIRST_RESULT_PRESERVED' if extensions_started else 'SETUP_OR_IMPORT_ERROR_FIRST_RESULT_PRESERVED'\n        record=dict(schema_version=1,status=failure_status,phase=phase,execution_stage=execution_stage,extensions_conformance_started=extensions_started,extensions_result_returned=extensions_returned,methods=None,method_outcomes=None,method_outcomes_reason='suite result did not return; observations are only known retained partial observations' if extensions_started else 'conformance not started',error_class=type(err).__name__,")
    t=once(t,"            clocks='One original real60s cooperative suite deadline is checked around actual codec calls/original callbacks and after the suite. Original callback exceptions/False returns remain unchanged. Every genuine owner retains original synthetic100/395/400 clock; readonly negative projection does not resample it.',",
        "            clocks='One original real60s cooperative extension suite deadline uses entry/loop/projector checks and the common post-suite veto; codec facade forwarding is NOT executed in this phase. Original synthetic100/395/400 owner monitors remain unchanged.',")
    with (H/'run_role_aware_extensions_v2.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
    print('Prepared explicit all-v2 independent runnerV5/extensionsV2; no subject import/run')


if __name__=='__main__':main()
