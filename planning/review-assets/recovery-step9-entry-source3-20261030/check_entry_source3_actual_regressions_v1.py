"""Independent retained-data review only; no subject import or replay."""
import ast
import hashlib
import json
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'recovery-step9-entry-source2-20261030'
APIS=('CreateFileW','GetFileType','GetFileInformationByHandleEx',
      'GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle')
AXES=('scalar','count','error_value','error_definition')
KINDS={1:'HANDLE64',2:'BOOL32_BITS',3:'DWORD32',4:'COUNT32',5:'DEFINEDNESS'}


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def read_exact(p):
    assert pin(p['path'])==p
    return json.loads(Path(p['path']).read_bytes().decode('utf-8'))


def methods(path):
    return {n.name:ast.dump(n,include_attributes=False)
            for n in ast.parse(Path(path).read_bytes().decode('utf-8')).body
            if isinstance(n,ast.FunctionDef)}


def main():
    path=HERE/'ENTRY-SOURCE3-REGRESSION-PROOF-v1.json'
    p=pin(path)
    assert p['bytes']==336850 and p['sha256']=='ca6baf6761b6342cf0578e1f74167f3379e9efb3b1306ac5c1d1e5c38a110e28'
    proof=json.loads(path.read_bytes().decode('utf-8'))
    binding=read_exact(proof['binding']);read_exact(binding['execution_scope'])
    read_exact(proof['source_pause'])
    prep=read_exact(proof['preparation']);inputs=read_exact(proof['inputs'])
    for row in proof['source_map'].values():assert pin(row['path'])==row
    for row in prep['harness'].values():assert pin(row['path'])==row
    assert methods(prep['harness']['regressions']['path'])==methods(OLD/'entry_initial_regressions_v3.py')
    assert len(methods(prep['harness']['regressions']['path']))==5
    assert proof['status']=='PASS' and proof['passed_methods']==5
    assert proof['declared_methods']==proof['executed_methods']==5
    assert proof['actual_worlds_constructed']==proof['actual_entry_attempts']==5
    assert proof['setup_error'] is None and proof['audit_denials']==[] and proof['changed_pins']==[]
    assert proof['cooperative_deadline_late'] is False
    assert [m['outcome'] for m in proof['methods']]==['PASS']*5
    before_path=OLD/'ENTRY-SOURCE2-DIAGNOSTIC-PROOF-v2.json'
    assert pin(before_path)['sha256']=='a1ff84a198834c4fb5660f79693a65539c9e365d97209b03dfc972764268c459'
    before=json.loads(before_path.read_bytes().decode('utf-8'))
    summaries=[];row_count=0
    for index,method in enumerate(proof['methods']):
        assert method['error'] is method['cleanup_error'] is method['evidence_error'] is None
        ev=method['evidence'];obs=ev['observations'];rows=ev['native_rows']
        assert method['source_import_completed'] is True and ev['actual_entry_attempts']==1
        assert ev['first_clock_observed'] is ev['source_identities_same'] is ev['snapshot_genuine'] is True
        assert ev['partial_snapshot'] is False and ev['captured_native_bytes']==256*len(rows)
        assert obs['original_dispatches']==len(rows)
        old_rows=before['methods'][index]['evidence']['native_rows']
        assert len(rows)==len(old_rows)
        read_bytes=read_calls=close_calls=0
        for ordinal,row in enumerate(rows):
            raw=bytes.fromhex(row['raw_row256_hex'])
            assert len(raw)==256 and row['ordinal']==ordinal
            assert row['raw_row256_hex']==old_rows[ordinal]['raw_row256_hex']
            schema,size,number,generation,api_id=struct.unpack_from('<HHIIH',raw)
            assert (schema,size,number,generation)==(1,256,ordinal,1)
            api=APIS[api_id-1];assert row['facts']['api']==api
            for i,name in enumerate(AXES):
                bits,epoch,kind,width,reserved,stage,commit,padding=struct.unpack_from('<QIHBBIIQ',raw,128+32*i)
                assert epoch==1 and reserved==padding==0 and stage in (0,1) and commit in (0,1)
                assert not commit or stage
                label=KINDS[kind]
                assert width==(8 if label=='HANDLE64' else 1 if label=='DEFINEDNESS' else 4)
                known=(bool(bits) if label=='DEFINEDNESS' else bits-(1<<32) if label=='BOOL32_BITS' and bits&(1<<31) else bits) if commit else None
                assert row['axes'][name]==dict(native_state='COMMITTED' if commit else 'STAGED_UNCOMMITTED' if stage else 'UNOBSERVED',
                    kind=label,width=width,epoch=epoch,stage_hint=stage,commit=commit,raw_payload_bits=bits,known_value=known)
            if api=='ReadFile':
                read_calls+=1
                assert row['axes']['scalar']['known_value']==1 and row['axes']['count']['native_state']=='COMMITTED'
                read_bytes+=row['axes']['count']['known_value']
            if api=='CloseHandle':
                close_calls+=1
                assert row['axes']['scalar']['native_state']=='COMMITTED' and row['axes']['scalar']['known_value']==1
            row_count+=1
        assert obs['actual_read_dispatches']==read_calls
        assert obs['helper_completed_delivery_bytes']==read_bytes
        assert obs['scripted_close_attempts']==close_calls
        assert sum(r['attempts'] for r in ev['close_dispatch_attempts'])==close_calls
        assert all(r['attempts'] in (0,1) for r in ev['close_dispatch_attempts'])
        summaries.append(dict(method=method['method'],outcome=method['outcome'],original_calls=len(rows),
                              read_calls=read_calls,known_read_bytes=read_bytes,once_close_attempts=close_calls,
                              actual_helper_compiler_callbacks=obs['helper_compiler_callbacks']))
    fifth=proof['methods'][4]['evidence'];probe=fifth['stopped_close_probe']
    assert probe['cache_scalar_unobserved'] is True and probe['cache_scalar'] is None
    for name in ('call_stopped','wrapper_return_observed','wrapper_result_is_none',
                 'original_error_is_primary','original_error_rethrown'):
        assert probe[name] is True
    assert probe['wrapper_state']=='returned' and probe['callback_caught_original']==1
    assert probe['native_state']=='COMMITTED'
    assert probe['known_value']==probe['raw_payload_bits']==probe['chosen_path_close_attempts']==1
    row=fifth['native_rows'][probe['ordinal']]
    assert row['facts']['wrapper_state']=='returned' and row['facts']['wrapper_return'] is True and row['facts']['stopped'] is True
    assert row['axes']['scalar']['known_value']==1
    assert fifth['observations']['original_first_error']['type'].endswith('MemoryError')
    assert summaries[1]['original_calls']==inputs['baseline_geometry']['terminal_calls']==37
    assert summaries[1]['known_read_bytes']==inputs['baseline_geometry']['known_bytes']==2196237
    assert summaries[2]['once_close_attempts']==0 and summaries[3]['once_close_attempts']==1
    staged=proof['methods'][2]['evidence']['native_rows'][0]['axes']['scalar']
    assert staged['native_state']=='STAGED_UNCOMMITTED' and staged['raw_payload_bits']==1000 and staged['known_value'] is None
    result=dict(schema_version=1,status='CLEAR_SOURCE_PURE_FIVE_ENTRY_REGRESSIONS_ONLY',material_blockers=[],
                proof=p,checker=pin(__file__),binding=proof['binding'],execution_scope=binding['execution_scope'],
                source_pause=proof['source_pause'],source_map=proof['source_map'],preparation=proof['preparation'],
                before_source2_proof=pin(before_path),five_assertion_ASTs_unchanged=True,
                methods=summaries,total_raw_rows_byte_verified=row_count,native_axis_cells_byte_verified=4*row_count,
                all_61_native_rows_identical_to_retained_source2=True,
                actual_worlds=5,actual_entries=5,passed_methods=5,failed_methods=0,
                actual_original_dispatches=sum(x['original_calls'] for x in summaries),
                actual_read_dispatches=sum(x['read_calls'] for x in summaries),
                once_close_attempts=sum(x['once_close_attempts'] for x in summaries),
                fifth_stopped_close_evidence=probe,
                setup_cleanup_evidence_errors=0,audit_denials=0,changed_pins=0,
                elapsed_seconds=proof['elapsed_seconds'],subject_execution_by_reviewer=0,
                interpretation='The same fifth assertion now passes: committed close BOOL1, stopped flag, normal wrapper return and original MemoryError remain known, while the same-call scalar cache stays UNOBSERVED. Original raw rows and the other four assertions are retained unchanged. The fresh cleanup-under-earlier-error converse still passes.',
                limitations=['Only five synthetic entry worlds, not entry32/53 or native25 completion.',
                             'The measured0.203s belongs to this injected cooperative diagnostic, not production performance/resource fit.',
                             'No native/physical/real-first-entry/full-roster/new84/scientific or human qualification.'])
    out=HERE/'ENTRY-SOURCE3-REGRESSION-INDEPENDENT-ACTUAL-REVIEW-v1.json'
    with out.open('xb') as f:f.write((json.dumps(result,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    print(json.dumps(dict(review=pin(out),methods=summaries,raw_rows=row_count)))


if __name__=='__main__':
    main()
