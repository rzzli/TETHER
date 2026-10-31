"""Read-only independent review of retained five-check data, never source run."""
import hashlib
import json
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
APIS=('CreateFileW','GetFileType','GetFileInformationByHandleEx',
      'GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle')
AXES=('scalar','count','error_value','error_definition')
KINDS={1:'HANDLE64',2:'BOOL32_BITS',3:'DWORD32',4:'COUNT32',5:'DEFINEDNESS'}


def pin(path):
    path=Path(path).resolve()
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def read_exact(p):
    assert pin(p['path'])==p
    return json.loads(Path(p['path']).read_bytes().decode('utf-8'))


def main():
    proof_path=HERE/'ENTRY-SOURCE2-DIAGNOSTIC-PROOF-v2.json'
    p=pin(proof_path)
    assert p['bytes']==337633 and p['sha256']=='a1ff84a198834c4fb5660f79693a65539c9e365d97209b03dfc972764268c459'
    proof=json.loads(proof_path.read_bytes().decode('utf-8'))
    binding=read_exact(proof['binding'])
    read_exact(binding['execution_scope'])
    read_exact(proof['source_pause'])
    prep=read_exact(proof['preparation'])
    inputs=read_exact(proof['inputs'])
    for row in proof['source_map'].values():assert pin(row['path'])==row
    for row in prep['harness'].values():assert pin(row['path'])==row
    assert proof['status']=='INCOMPLETE_OR_FAILED' and proof['passed_methods']==4
    assert proof['declared_methods']==proof['executed_methods']==5
    assert proof['actual_worlds_constructed']==proof['actual_entry_attempts']==5
    assert proof['setup_error'] is None and proof['audit_denials']==[] and proof['changed_pins']==[]
    assert proof['cooperative_deadline_late'] is False
    assert [x['outcome'] for x in proof['methods']]==['PASS']*4+['FAIL']
    summaries=[]
    row_count=0
    for method in proof['methods']:
        assert method['cleanup_error'] is method['evidence_error'] is None
        ev=method['evidence'];obs=ev['observations']
        assert method['source_import_completed'] is True and ev['actual_entry_attempts']==1
        assert ev['first_clock_observed'] is ev['source_identities_same'] is ev['snapshot_genuine'] is True
        assert ev['partial_snapshot'] is False
        rows=ev['native_rows']
        assert ev['captured_native_bytes']==256*len(rows)
        assert obs['original_dispatches']==len(rows)
        read_bytes=0;read_calls=0;close_calls=0
        for ordinal,row in enumerate(rows):
            raw=bytes.fromhex(row['raw_row256_hex'])
            assert len(raw)==256 and row['ordinal']==ordinal
            schema,size,index,generation,api_id=struct.unpack_from('<HHIIH',raw)
            assert (schema,size,index,generation)==(1,256,ordinal,1)
            api=APIS[api_id-1]
            assert row['facts']['api']==api
            for i,name in enumerate(AXES):
                bits,epoch,kind,width,reserved,stage,commit,padding=struct.unpack_from('<QIHBBIIQ',raw,128+32*i)
                assert epoch==1 and reserved==padding==0 and stage in (0,1) and commit in (0,1)
                assert not commit or stage
                label=KINDS[kind]
                assert width==(8 if label=='HANDLE64' else 1 if label=='DEFINEDNESS' else 4)
                known=(bool(bits) if label=='DEFINEDNESS' else bits-(1<<32) if label=='BOOL32_BITS' and bits&(1<<31) else bits) if commit else None
                expected=dict(native_state='COMMITTED' if commit else 'STAGED_UNCOMMITTED' if stage else 'UNOBSERVED',
                              kind=label,width=width,epoch=epoch,stage_hint=stage,commit=commit,
                              raw_payload_bits=bits,known_value=known)
                assert row['axes'][name]==expected
            if api=='ReadFile':
                read_calls+=1
                assert row['axes']['scalar']['known_value']==1
                assert row['axes']['count']['native_state']=='COMMITTED'
                read_bytes+=row['axes']['count']['known_value']
            if api=='CloseHandle':
                close_calls+=1
                assert row['axes']['scalar']['native_state']=='COMMITTED'
                assert row['axes']['scalar']['known_value']==1
            row_count+=1
        assert obs['actual_read_dispatches']==read_calls
        assert obs['helper_completed_delivery_bytes']==read_bytes
        assert obs['scripted_close_attempts']==close_calls
        assert sum(r['attempts'] for r in ev['close_dispatch_attempts'])==close_calls
        assert all(r['attempts'] in (0,1) for r in ev['close_dispatch_attempts'])
        summaries.append(dict(method=method['method'],outcome=method['outcome'],
                              actual_original_calls=len(rows),actual_read_calls=read_calls,
                              known_read_bytes=read_bytes,once_close_attempts=close_calls,
                              helper_compiler_callbacks=obs['helper_compiler_callbacks']))
    fifth=proof['methods'][4]
    assert fifth['error']['args']==['stopped CloseHandle normal-return path must not heal its interrupted scalar cache']
    ev=fifth['evidence'];probe=ev['stopped_close_probe']
    assert probe['cache_scalar_unobserved'] is False and probe['cache_scalar']==1
    for key in ('call_stopped','wrapper_return_observed','wrapper_result_is_none',
                'original_error_is_primary','original_error_rethrown'):
        assert probe[key] is True
    assert probe['wrapper_state']=='returned' and probe['callback_caught_original']==1
    assert probe['known_value']==probe['raw_payload_bits']==probe['chosen_path_close_attempts']==1
    assert probe['native_state']=='COMMITTED'
    close=ev['native_rows'][probe['ordinal']]
    assert close['facts']['stopped'] is True and close['facts']['wrapper_return'] is True
    assert close['facts']['wrapper_state']=='returned' and close['axes']['scalar']['known_value']==1
    assert ev['observations']['original_first_error']['type'].endswith('MemoryError')
    assert summaries[0]['actual_original_calls']==0
    assert summaries[1]['actual_original_calls']==inputs['baseline_geometry']['terminal_calls']==37
    assert summaries[1]['known_read_bytes']==inputs['baseline_geometry']['known_bytes']==2196237
    assert summaries[2]['once_close_attempts']==0 and summaries[3]['once_close_attempts']==1
    staged=proof['methods'][2]['evidence']['native_rows'][0]['axes']['scalar']
    assert staged['native_state']=='STAGED_UNCOMMITTED' and staged['raw_payload_bits']==1000 and staged['known_value'] is None
    result=dict(schema_version=1,status='HOLD_CONFIRMED_SOURCE2_STOPPED_CLOSE_CACHE_HEALING',
                proof=p,checker=pin(__file__),binding=proof['binding'],
                execution_scope=binding['execution_scope'],source_pause=proof['source_pause'],
                source_map=proof['source_map'],preparation=proof['preparation'],
                methods=summaries,total_raw_rows_verified=row_count,
                native_axis_cells_byte_compared=4*row_count,
                actual_entry_worlds=5,passed_assertions=4,failed_assertions=1,
                precise_failure=probe,
                original_error_and_wrapper_facts_preserved=True,
                setup_cleanup_evidence_errors=0,audit_denials=0,changed_pins=0,
                source_execution_by_reviewer=0,
                measured_source2_diagnostic_seconds=proof['elapsed_seconds'],
                interpretation='The fifth actual assertion failed because the stopped same CloseHandle cache became1 after actual native commit and caught callback fault/normal wrapper return. This is source failure evidence, not expected-failure PASS. The prior four assertions passed. Source3 must guard stopped same-call healthy cache/reconcile work while preserving fresh cleanup under an earlier owner error.',
                limits=['One five-world synthetic diagnostic, not full32/53 or native25 qualification.',
                        'No native/physical/real-entry/new84/full-roster/resource/scientific qualification.'])
    out=HERE/'ENTRY-SOURCE2-DIAGNOSTIC-INDEPENDENT-ACTUAL-REVIEW-v2.json'
    with out.open('xb') as f:f.write((json.dumps(result,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    print(json.dumps(dict(review=pin(out),summaries=summaries,total_rows=row_count)))


if __name__=='__main__':
    main()
