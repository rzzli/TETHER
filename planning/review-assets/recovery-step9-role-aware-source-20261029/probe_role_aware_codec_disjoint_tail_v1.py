"""One retained diagnostic: only byte-negative indices100..224, once each.

Prepared helper only until Root publishes its exact execution binding/scope.
No first-four-method replay, positive bases decode, legacy owner, or source edit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import traceback
import types

H=Path(__file__).resolve().parent
NAMES=('role_ledger_codec_v2','role_owner_v2','role_file_ports_v2','continue_role_verification_v2')
START=100
STOP=225


def pin(p):
    b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(p):
    if type(p) is not dict or set(p)!={'path','bytes','sha256'}:raise RuntimeError('exact pin shape')
    b=Path(p['path']).read_bytes()
    if type(p['bytes']) is not int or len(b)!=p['bytes'] or hashlib.sha256(b).hexdigest()!=p['sha256']:raise RuntimeError('pin changed')
    return b
def load_harness(name,p):
    raw=checked(p)
    if name in sys.modules:raise RuntimeError('fresh harness name cached')
    m=types.ModuleType(name);m.__file__=p['path'];m.__package__='';sys.modules[name]=m
    exec(compile(raw,m.__file__,'exec'),m.__dict__)
    return m


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binding-sha256',required=True);args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}',args.binding_sha256):raise ValueError('exact binding digest')
    started=time.monotonic();deadline=started+30
    binding_path=H/'ROLE-AWARE-CODEC-DISJOINT-TAIL-BINDING-v1.json'
    attempt_path=H/'ROLE-AWARE-CODEC-DISJOINT-TAIL-ATTEMPT-v1.json'
    proof_path=H/'ROLE-AWARE-CODEC-DISJOINT-TAIL-PROOF-v1.json'
    stage='BOOTSTRAP';D=None;facade=None;source_pins={};record=None;binding=None
    rows=[dict(index=i,id=None,expected_required_code=None,raw_sha256=None,attempted=False,rejected=None,
        actual_code=None,surface_valid=None,correct=None,unknown_reason='bootstrap not completed') for i in range(START,STOP)]
    counts=dict(planned_cases=125,reserved_rows=0,decode_observations=0,format_rejections=0,unexpected_accepts=0,
                code_mismatches=0,unexpected_exceptions=0,unknown_cases=125,unknown_rejection_cases=125,original_check_calls=0)
    try:
        raw=binding_path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=args.binding_sha256:raise RuntimeError('binding digest changed')
        binding=json.loads(raw)
        if binding['mode']!='DISJOINT_BYTE_NEGATIVE_TAIL_100_224_V2':raise RuntimeError('exact disjoint role')
        if any(type(binding[k]) is not int for k in ('start_index','stop_index_exclusive','max_decode_calls','deadline_seconds')):raise RuntimeError('strict disjoint integer fields')
        if (binding['start_index'],binding['stop_index_exclusive'],binding['max_decode_calls'],binding['deadline_seconds'])!=(START,STOP,125,30):raise RuntimeError('disjoint bounds changed')
        if attempt_path.exists() or proof_path.exists():raise RuntimeError('first attempt/result retained; no replay')
        if binding['source_module_load_order']!=list(NAMES) or set(binding['source_pins'])!=set(NAMES):raise RuntimeError('exact coherent V2 map')
        source_pins={n:binding['source_pins'][n] for n in NAMES}
        for n,p in source_pins.items():
            if Path(p['path']).resolve()!=H/(n+'.py'):raise RuntimeError('source outside fixed new map')
            checked(p)
        for k in ('source_pause','execution_scope','source_scope'):checked(binding[k])
        for p in binding['harness_pins'].values():checked(p)
        for p in binding['dependencies'].values():checked(p)
        with attempt_path.open('xb') as out:
            out.write((json.dumps(dict(binding_sha256=args.binding_sha256,started_monotonic=started,deadline_seconds=30,
                first_index=START,last_index=STOP-1,max_decode_calls=125,subject_imports_before_attempt=0),sort_keys=True)+'\n').encode())
        R=load_harness('role_aware_tail_trusted_runner_v5',binding['harness_pins']['common_runner'])
        D=load_harness('role_aware_tail_exact_legacy_audit_adapter_v1',binding['harness_pins']['legacy_adapter'])
        D.TEST_DEADLINE=deadline
        assert 'A'.encode('utf-16-le')==b'A\0'
        stage='SOURCE_DEFINITION';modules=D.load_exact_modules(source_pins)
        T=load_harness('role_aware_tail_exact_raw_mutation_helper_v2',binding['harness_pins']['codec_tests'])
        corpus=json.loads(checked(binding['dependencies']['literal_corpus']))
        if len(corpus['bases'])!=40 or len(corpus['byte_negatives'])!=STOP:raise RuntimeError('frozen corpus cardinality')
        schema=json.loads(checked(binding['dependencies']['format_schema']));codes=set(schema['validation']['error_codes'])
        bases={b['id']:b for b in corpus['bases']};cache={}
        # All labels/expected facts stay HERE. Actual source receives raw bytes
        # and one check function only; the check closure has no case variable.
        for i in range(START,STOP):
            m=corpus['byte_negatives'][i]
            rows[i-START].update(id=m['id'],expected_required_code=m['expected']['required_code'],raw_sha256=m['sha256'],unknown_reason='not dispatched')
        def original_check():
            counts['original_check_calls']+=1
            return False
        facade=R.DeadlineCodecFacade(modules['role_ledger_codec_v2'],deadline)
        stage='DISJOINT_TAIL_CONFORMANCE'
        for row in rows:
            if time.monotonic()>=deadline:break
            m=corpus['byte_negatives'][row['index']]
            if m['base'] not in cache:cache[m['base']]=T.unpack_blob(bases[m['base']]['raw'])
            bad=T.raw_mutation(cache[m['base']],m)
            if len(bad)!=m['bytes'] or hashlib.sha256(bad).hexdigest()!=m['sha256']:raise RuntimeError('frozen mutation changed')
            if facade.stats['actual_decode_calls']>=125:raise RuntimeError('decode dispatch cap')
            row['attempted']=True;row['unknown_reason']=None;counts['reserved_rows']+=1
            before=dict(facade.stats);stop=False
            try:
                value=facade.decode_ledger(bad,check=original_check)
            except modules['role_ledger_codec_v2'].FormatError as error:
                code=error.code;offset=error.offset;path=error.path
                surface=(type(code) is str and code in codes and
                    (offset is None or type(offset) is int and 0<=offset<=len(bad)) and type(path) is tuple and
                    all(type(x) is str or type(x) is int and x>=0 for x in path))
                row.update(rejected=True,actual_code=code if type(code) is str else None,surface_valid=surface,
                    correct=surface and (row['expected_required_code'] is None or code==row['expected_required_code']),
                    offset=offset if offset is None or type(offset) is int else None,
                    path=list(path) if surface else None,unknown_reason=None)
                counts['format_rejections']+=1
                if not row['correct']:counts['code_mismatches']+=1
            except BaseException as error:
                late=facade.stats['late_seen'] or time.monotonic()>=deadline
                row.update(error_class=type(error).__name__,rejected=None,correct=None if late else False,
                    unknown_reason='cooperative deadline interrupted observation' if late else 'unexpected non-FormatError exception')
                counts['unexpected_exceptions']+=1
                stop=late or isinstance(error,(KeyboardInterrupt,SystemExit,GeneratorExit)) or bool(D.AUDIT_DENIALS)
            else:
                row.update(rejected=False,correct=False,unknown_reason=None,returned_type=type(value).__name__)
                counts['unexpected_accepts']+=1
                del value
            finally:
                after=dict(facade.stats)
                row['forwarding_before']=before;row['forwarding_after']=after
                row['actual_decode_forward_delta']=after['actual_decode_calls']-before['actual_decode_calls']
                if row['actual_decode_forward_delta'] not in (0,1):raise RuntimeError('one-forward-per-case invariant')
                if row['correct'] is not None:counts['decode_observations']+=1
                counts['unknown_cases']=sum(x['correct'] is None for x in rows)
                counts['unknown_rejection_cases']=sum(x['rejected'] is None for x in rows)
            if stop:break
        late=time.monotonic()>=deadline
        complete=all(r['attempted'] and r['correct'] is not None and r.get('actual_decode_forward_delta')==1 for r in rows)
        record=dict(schema_version=1,status='COMPLETE_TAIL_DIAGNOSTIC_RETAINED' if complete and not late else 'PARTIAL_TAIL_DIAGNOSTIC_RETAINED',
            stage=stage,diagnostic_complete=complete and not late,all_tail_outcomes_match=complete and all(r['correct'] for r in rows) and not late,
            first_index=START,last_index=STOP-1,rows=rows,counters=counts,codec_forwarding=dict(facade.stats),
            common_post_suite_late_veto=late,elapsed_seconds=time.monotonic()-started,
            mismatched_indices=[r['index'] for r in rows if r['correct'] is False],unknown_indices=[r['index'] for r in rows if r['correct'] is None],
            source_pins=source_pins,source_unchanged={n:pin(Path(p['path']))==p for n,p in source_pins.items()},
            harness_unchanged={n:pin(Path(p['path']))==p for n,p in binding['harness_pins'].items()},
            binding=pin(binding_path),helper=pin(Path(__file__).resolve()),dependencies=binding['dependencies'],audit_denials=D.AUDIT_DENIALS,
            scope='One disjoint raw-byte diagnostic only; no full suite, earlier negative, V1, positive base decode or legacy replay. Matching this tail cannot repair earlier failed conformance.',
            bound='One original30s cooperative deadline including bootstrap; no hard callback-free hang bound without an owned outer watchdog.',
            actual_original_or_native_calls=0,qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']})
    except BaseException as error:
        record=dict(schema_version=1,status='TAIL_CONFORMANCE_ABORTED_RETAINED' if stage=='DISJOINT_TAIL_CONFORMANCE' else 'TAIL_SETUP_OR_IMPORT_ERROR_RETAINED',
            stage=stage,error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc(),rows=rows,counters=counts,
            codec_forwarding=None if facade is None else dict(facade.stats),counts_complete=False,
            unknown_reason='Remaining case outcomes unavailable; retained counters are partial facts, not zero complete accounting.',
            source_pins=source_pins,source_unchanged={n:pin(Path(p['path']))==p for n,p in source_pins.items()},
            audit_denials=[] if D is None else D.AUDIT_DENIALS,elapsed_seconds=time.monotonic()-started,
            actual_original_or_native_calls=0,runtime_qualified=False)
    finally:
        if record is not None:
            final_late=time.monotonic()>=deadline
            record['final_deadline_veto']=final_late
            if final_late:
                record['diagnostic_complete']=False;record['all_tail_outcomes_match']=False
                if record['status']=='COMPLETE_TAIL_DIAGNOSTIC_RETAINED':record['status']='PARTIAL_TAIL_DIAGNOSTIC_RETAINED'
            with proof_path.open('xb') as out:out.write((json.dumps(record,sort_keys=True,indent=2)+'\n').encode())
            print(json.dumps(dict(proof=pin(proof_path),status=record['status'],reserved_rows=counts['reserved_rows'],
                known_observations=counts['decode_observations'],unknown_cases=counts['unknown_cases'],
                actual_decode_calls=None if facade is None else facade.stats['actual_decode_calls'])))
    return 0 if record and record.get('diagnostic_complete') else 1


if __name__=='__main__':raise SystemExit(main())
