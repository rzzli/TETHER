"""First-result-only runner for a future exact four-module source pause.

Preparation file only until Root supplies an exact execution binding/scope.
No module discovery, cached subject source fallback, old owner or native ports.
"""
import argparse
import ast
import base64
import builtins
import copy
import dataclasses
import encodings.utf_16_le
import hashlib
import io
import json
import math
from pathlib import Path
import re
import struct
import sys
import time
import traceback
import types
import unittest
import zlib

HERE=Path(__file__).resolve().parent
PRODUCER=HERE.parent/'recovery-step9-role-aware-producer-20261029'
SHARED=HERE.parent/'recovery-step9-shared-owner-20261029'
SUBJECT_NAMES=('role_ledger_codec_v1','role_owner_v1','role_file_ports_v1','continue_role_verification_v1')


def pin(path):
    raw=path.read_bytes();return dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def checked(expected):
    if type(expected) is not dict or set(expected)!={'path','bytes','sha256'}:raise RuntimeError('exact pin shape')
    raw=Path(expected['path']).read_bytes()
    if type(expected['bytes']) is not int or len(raw)!=expected['bytes'] or hashlib.sha256(raw).hexdigest()!=expected['sha256']:raise RuntimeError('pinned NEW source/data changed')
    return raw


def load_harness(name,expected):
    raw=checked(expected)
    if name in sys.modules:raise RuntimeError('fresh harness name already cached')
    module=types.ModuleType(name);module.__file__=expected['path'];module.__package__=''
    sys.modules[name]=module
    exec(compile(raw,module.__file__,'exec'),module.__dict__)
    return module


class DeadlineCodecFacade:
    """Forward actual source functions/data under one cooperative deadline.

    No source callback site is added. Only the supplied callback is wrapped;
    actual FormatError and actual DecodedLedger objects are exposed unchanged.
    A callback-free hang has no hard bound without a separately owned watchdog.
    """
    def __init__(self,actual,deadline):
        self.actual=actual;self.deadline=deadline;self.FormatError=actual.FormatError
        self.stats=dict(facade_attempts=0,preforward_deadline_refusals=0,actual_encode_calls=0,actual_decode_calls=0,
            actual_source_check_sites=0,original_callback_calls=0,original_callback_returns=0,original_callback_exceptions=0,
            actual_source_returns=0,actual_source_exceptions=0,postcall_late_vetoes=0,late_seen=False)
    def _late(self):
        late=time.monotonic()>=self.deadline
        if late:self.stats['late_seen']=True
        return late
    def _guard(self,where):
        if self._late():raise TimeoutError('original cooperative suite deadline: '+where)
    def _call(self,which,value,check):
        self.stats['facade_attempts']+=1
        try:self._guard('before actual codec call')
        except BaseException:
            self.stats['preforward_deadline_refusals']+=1
            raise
        def wrapped():
            self.stats['actual_source_check_sites']+=1
            self._guard('before original check callback')
            self.stats['original_callback_calls']+=1
            try:result=check()
            except BaseException:
                # Record lateness without replacing the ORIGINAL exception.
                self.stats['original_callback_exceptions']+=1
                self._late()
                raise
            self.stats['original_callback_returns']+=1
            self._guard('after original check callback')
            return result
        function=self.actual.encode_ledger if which=='encode' else self.actual.decode_ledger
        self.stats['actual_'+which+'_calls']+=1
        try:result=function(value,check=wrapped)
        except BaseException:
            self.stats['actual_source_exceptions']+=1
            self._late() # Never mask an original callback or source exception.
            raise
        self.stats['actual_source_returns']+=1
        if self._late():
            self.stats['postcall_late_vetoes']+=1
            raise TimeoutError('original cooperative suite deadline after actual codec return')
        return result
    def encode_ledger(self,value,*,check):return self._call('encode',value,check)
    def decode_ledger(self,value,*,check):return self._call('decode',value,check)


class Results(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.outcomes=[]
    def addSuccess(self,t):self.outcomes.append(dict(test=str(t),status='PASS'));super().addSuccess(t)
    def addFailure(self,t,e):self.outcomes.append(dict(test=str(t),status='FAIL'));super().addFailure(t,e)
    def addError(self,t,e):self.outcomes.append(dict(test=str(t),status='ERROR'));super().addError(t,e)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binding-sha256',required=True);args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}',args.binding_sha256):raise ValueError('exact binding SHA256 required')
    started=time.monotonic();binding_path=HERE/'ROLE-AWARE-INDEPENDENT-SOURCE-BINDING-v2.json'
    D=None;binding=None;source_pins={};modules={};record=None;codec_result=None;codec_forwarding=None;runs=[];focused=[]
    phase='UNBOUND';report_path=None
    try:
        b= binding_path.read_bytes()
        if hashlib.sha256(b).hexdigest()!=args.binding_sha256:raise RuntimeError('binding hash mismatch')
        binding=json.loads(b)
        if binding['schema_version']!=1 or binding['phase'] not in ('CODEC_FIRST','LEGACY48_FIRST'):raise RuntimeError('explicit phase binding')
        phase=binding['phase'];report_path=HERE/('ROLE-AWARE-INDEPENDENT-'+phase+'-PROOF-v2.json')
        attempt_path=HERE/('ROLE-AWARE-INDEPENDENT-'+phase+'-ATTEMPT-v2.json')
        if report_path.exists() or attempt_path.exists():raise RuntimeError('first result/attempt already retained; no replay')
        if binding['deadline_seconds']!=60 or type(binding['deadline_seconds']) is not int:raise RuntimeError('fixed suite safety cap')
        if set(binding['source_pins'])!=set(SUBJECT_NAMES) or binding['source_module_load_order']!=list(SUBJECT_NAMES):raise RuntimeError('exact coherent new source order')
        source_pins={name:binding['source_pins'][name] for name in SUBJECT_NAMES}
        for name,p in source_pins.items():
            if Path(p['path']).resolve()!=HERE/(name+'.py'):raise RuntimeError('subject source path outside fixed map')
            checked(p)
        for key in ('source_scope','execution_scope','source_pause'):checked(binding[key])
        for p in binding['dependencies'].values():checked(p)
        for p in binding['harness_pins'].values():checked(p)
        # Only NEW pinned metadata/source pins are touched in bootstrap. The
        # fixed synthetic originals remain bytes in the frozen JSON cohort.
        with attempt_path.open('xb') as out:
            out.write((json.dumps(dict(schema_version=1,phase=phase,binding_sha256=args.binding_sha256,
                                      started_monotonic=started,source_imports_before_attempt=0),sort_keys=True)+'\n').encode())
        D=load_harness('role_aware_independent_legacy_adapter_v1',binding['harness_pins']['legacy_adapter'])
        D.TEST_DEADLINE=started+60
        # Trusted harmless codec warmup BEFORE any ACTIVE subject definition.
        assert 'A'.encode('utf-16-le')==b'A\0'
        modules=D.load_exact_modules(source_pins)
        # Trusted validator is a separate harness dependency. It is not in the
        # producer's closed own-import map and cannot become an imported gate.
        validator=load_harness('role_aware_exact_legacy_snapshot_validator_v1',binding['harness_pins']['snapshot_validator'])
        D.SUBJECT_FILENAMES.add(binding['harness_pins']['snapshot_validator']['path'])
        roles=dict(zip(('shared_owner_v1','shared_file_ports_v1','continue_verification_v1'),
                       (modules['role_owner_v1'],modules['role_file_ports_v1'],modules['continue_role_verification_v1'])))
        roles['shared_owner_snapshot_validator_v1']=validator
        if phase=='CODEC_FIRST':
            T=load_harness('role_aware_independent_frozen_codec_tests_v2',binding['harness_pins']['codec_tests'])
            corpus=json.loads(checked(binding['dependencies']['literal_corpus']))
            # The adapter audit additionally recognizes source frames, so
            # source getters/error properties remain guarded without keeping
            # unittest traceback formatting inside ACTIVE source operations.
            facade=DeadlineCodecFacade(modules['role_ledger_codec_v1'],started+60)
            codec_forwarding=facade.stats
            codec_result=T.run(facade,corpus)
            late_suite_veto=facade._late()
            codec_forwarding=dict(facade.stats)
            codec_forwarding['post_suite_late_veto']=late_suite_veto
            status='PASS' if codec_result['status']=='PASS' and not late_suite_veto else 'FIRST_FAILURES_RETAINED'
            methods=codec_result['methods'];method_outcomes=[];failures=codec_result['failures'];errors=codec_result['errors']
        else:
            fixture,schema,public,cohort=D.literals()
            R=load_harness('role_aware_independent_same8_adapter_v1',binding['harness_pins']['same8_adapter'])
            class Actual48(unittest.TestCase):
                def test_all48_genuine_producer_histories(self):
                    for case in fixture['cases']:
                        with self.subTest(history=case['id']):
                            if time.monotonic()>=D.TEST_DEADLINE:raise TimeoutError('original independent suite60s deadline')
                            result=D.FrozenRun(roles,validator,fixture,schema,public,cohort,case).run();runs.append(result)
                            self.assertTrue(result['matched'],json.dumps(dict(differences=result['differences'],
                                protocol_errors=result['protocol_errors'],violations=result['violations']),sort_keys=True))
                    self.assertEqual(len(runs),48)
            suite=unittest.TestSuite();suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Actual48))
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(R.make_tests(D,roles,fixture,public,cohort,validator,focused)))
            result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)
            status='PASS' if result.wasSuccessful() else 'FIRST_FAILURES_RETAINED';methods=result.testsRun;method_outcomes=result.outcomes
            failures=[dict(test=str(t),traceback=x) for t,x in result.failures];errors=[dict(test=str(t),traceback=x) for t,x in result.errors]
        record=dict(schema_version=1,status=status,phase=phase,methods=methods,method_outcomes=method_outcomes,failures=failures,errors=errors,
            codec=codec_result,codec_forwarding=codec_forwarding,legacy_runs=runs,same8_observations=focused,histories_executed=len(runs),histories_matched=sum(x['matched'] for x in runs),
            legacy_snapshot_count=sum(len(x['snapshots']) for x in runs),actual_legacy_fake_dispatches=sum(len(x['binding_records']) for x in runs),
            actual_marker_module_execs=sum(len(x['marker_module_execs']) for x in runs),genuine_projector_calls=len(D.PROJECTOR_OBSERVATIONS),
            projector_observations=D.PROJECTOR_OBSERVATIONS,audit_denials=D.AUDIT_DENIALS,source_pins=source_pins,
            source_unchanged={name:pin(Path(p['path']))==p for name,p in source_pins.items()},
            harness_unchanged={name:pin(Path(p['path']))==p for name,p in binding['harness_pins'].items()},
            source_binding=pin(binding_path),runner=pin(Path(__file__).resolve()),dependencies=binding['dependencies'],
            elapsed_seconds=time.monotonic()-started,scope='Actual NEW four-module SOURCE/PURE only, if explicitly authorized. No real source/entry/FFI/physical/native/profile/scientific qualification.',
            module_policy='Fresh fixed four-module map only. Old shared_owner_v1 dictionary keys are HARNESS-ONLY roles referencing actual new module objects; no old owner code/import/cache alias.',
            audit_policy='Source ACTIVE boundaries plus exact subject filename frames cover getters/callbacks; no unexpected filesystem/network/native/import events. Trusted test reporting is outside subject activity.',
            clocks='One original real60s cooperative suite deadline is checked around actual codec calls/original callbacks and after the suite. Original callback exceptions/False returns remain unchanged. Every genuine owner retains original synthetic100/395/400 clock; readonly negative projection does not resample it.',
            hard_wall_time_guard=False,callback_free_hang_bound='UNKNOWN_NO_OWNED_OUTER_WATCHDOG',
            actual_target_API_calls=0,original_or_payload_operations=0,qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']})
    except BaseException as err:
        record=dict(schema_version=1,status='SETUP_OR_HARNESS_ERROR_FIRST_RESULT_PRESERVED',phase=phase,error_class=type(err).__name__,
            message=str(err)[:2048],traceback=traceback.format_exc(),codec=codec_result,codec_forwarding=codec_forwarding,legacy_runs=runs,same8_observations=focused,
            source_pins=source_pins,source_unchanged={n:pin(Path(p['path']))==p for n,p in source_pins.items()},
            audit_denials=[] if D is None else D.AUDIT_DENIALS,elapsed_seconds=time.monotonic()-started,
            subject_runtime_qualification=False,actual_target_API_calls=0,original_or_payload_operations=0)
    finally:
        if record is not None:
            if report_path is None:report_path=HERE/'ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v2.json'
            with report_path.open('xb') as out:out.write((json.dumps(record,sort_keys=True,indent=2)+'\n').encode())
            print(json.dumps(dict(proof=pin(report_path),status=record['status'],phase=phase,methods=record.get('methods'),
                                  histories=len(runs),matched=sum(x.get('matched',False) for x in runs))))
    return 0 if record and record['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
