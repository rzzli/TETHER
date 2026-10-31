"""Independent generated-prefix reference. CODE ONLY until Root authorizes it.

Reads three pinned NEW review assets. Of the historical vector it uses only
the213 positive byte-size VALUES in original list order, never embedded paths,
roles or digests. No subject, original file, model, native or SDK operation.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import time
import traceback

H=Path(__file__).resolve().parent
P=H.parent/'recovery-step9-role-aware-producer-20261029'
S=H.parent/'recovery-step9-shared-owner-20261029'
EXPECTED={
    'size_vector':(P/'RETAINED-HISTORICAL-RESOURCE-VECTOR-v1.json','3a7e00e9cc812f7fcf0676c70704c65ab35565cac4b6a652fe06fad42c890c75'),
    'tiny_cohort':(S/'SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json','eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8'),
    'implementation_slice':(P/'ROLE-AWARE-PRODUCER-IMPLEMENTATION-SLICE-v1.json','35484f8a35d29bc108712dc7279e1cbbcb4b76470d28a6c1241895bbc4fd3f9c')}
CHUNK=1048576
SEED=bytes(range(256))


def pin(path):
    b=path.read_bytes();return dict(path=str(path.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(p):
    if type(p) is not dict or set(p)!={'path','bytes','sha256'}:raise ValueError('exact pin shape')
    b=Path(p['path']).read_bytes()
    if type(p['bytes']) is not int or len(b)!=p['bytes'] or hashlib.sha256(b).hexdigest()!=p['sha256']:raise ValueError('pin mismatch')
    return b
def integer(v):return type(v) is int and 0<v<(1<<63)


def main():
    started=time.monotonic() # Reference preparation has its OWN recorded timer.
    parser=argparse.ArgumentParser();parser.add_argument('--binding-sha256',required=True);args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}',args.binding_sha256):raise ValueError('binding digest required')
    binding_path=H/'ROLE-AWARE-LARGE-REFERENCE-BINDING-v1.json'
    attempt=H/'ROLE-AWARE-LARGE-REFERENCE-ATTEMPT-v1.json'
    output=H/'ROLE-AWARE-LARGE-REFERENCE-PROOF-v1.json'
    binding=None;position=0;hashes={};sizes=None;descriptors=None;record=None;deadline=None;copy_count=0
    try:
        raw=binding_path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=args.binding_sha256:raise ValueError('binding changed')
        binding=json.loads(raw)
        if binding['mode']!='INDEPENDENT_LARGE_PERIODIC_PREFIX_REFERENCE_V1':raise ValueError('reference role')
        if type(binding['deadline_seconds']) is not int or not 1<=binding['deadline_seconds']<=300:raise ValueError('explicit independent reference budget1..300s')
        deadline=started+binding['deadline_seconds']
        checked(binding['execution_scope'])
        if attempt.exists() or output.exists():raise RuntimeError('first reference attempt/result retained; no replay')
        if set(binding['inputs'])!=set(EXPECTED):raise ValueError('exact three metadata inputs')
        loaded={}
        for key,(path,digest) in EXPECTED.items():
            p=binding['inputs'][key]
            if Path(p['path']).resolve()!=path or p['sha256']!=digest:raise ValueError('metadata input role/path')
            loaded[key]=json.loads(checked(p))
        with attempt.open('xb') as out:out.write((json.dumps(dict(binding_sha256=args.binding_sha256,started_monotonic=started,subject_imports=0),sort_keys=True)+'\n').encode())
        # The only values extracted from historical rows are .bytes.
        rows=loaded['size_vector']['files']
        if type(rows) is not list or len(rows)!=213:raise ValueError('exact213 size rows')
        sizes=[r['bytes'] for r in rows]
        if not all(integer(n) for n in sizes) or sum(sizes)!=9017363392 or max(sizes)!=3991999872:raise ValueError('retained size geometry')
        if sum(n//CHUNK+(n%CHUNK!=0) for n in sizes)!=8796:raise ValueError('retained1MiB chunk geometry')
        checkpoints=sorted(set(sizes));hasher=hashlib.sha256()
        block=SEED*(CHUNK//len(SEED));view=memoryview(block)
        # Correct continuation across checkpoints whose sizes are NOT multiples
        # of256: select the offset into the shared periodic block explicitly.
        for stop in checkpoints:
            while position<stop:
                if time.monotonic()>=deadline:raise TimeoutError('independent reference preparation deadline')
                offset=position%len(block);n=min(stop-position,len(block)-offset)
                hasher.update(view[offset:offset+n]);position+=n
            if time.monotonic()>=deadline:raise TimeoutError('reference checkpoint deadline')
            hashes[str(stop)]=hasher.copy().hexdigest();copy_count+=1
        blobs=loaded['tiny_cohort']['blobs']
        if len(blobs)!=3 or [b['bytes'] for b in blobs]!=[58,83,68]:raise ValueError('exact209 tiny bytes')
        descriptors=[]
        for i,b in enumerate(blobs):
            body=bytes.fromhex(b['utf8_hex'])
            if len(body)!=b['bytes'] or hashlib.sha256(body).hexdigest()!=b['sha256']:raise ValueError('frozen tiny bytes')
            # Deliberately replace every historical/cohort path with a NEW
            # fictional path; no inherited role or source authority.
            filename=('cohort_leaf.py','cohort_entry.py','metadata.json')[i]
            descriptors.append(dict(file_id=i,path='D:\\FictionalRoleAwareLarge\\'+filename,
                role='captured_software' if i<2 else 'captured_metadata',capture=True,size=len(body),sha256=b['sha256'],utf8_hex=b['utf8_hex']))
        for i,size in enumerate(sizes):
            descriptors.append(dict(file_id=i+3,path='D:\\FictionalRoleAwareLarge\\bulk\\file_'+str(i).zfill(3)+'.bin',
                role='hash_only_bulk',capture=False,size=size,sha256=hashes[str(size)],periodic_size_index=i))
        if len(descriptors)!=216:raise ValueError('exact216 descriptors')
        Q=sum(d['size']//CHUNK+(d['size']%CHUNK!=0) for d in descriptors)
        N=len(descriptors);R=Q+16*N;C=6*N+R;E=6*N+2*2+2*2+192
        if (Q,R,C,E)!=(8799,12255,13551,1496):raise ValueError('large reservation geometry')
        if time.monotonic()>=deadline:raise TimeoutError('reference final deadline')
        record=dict(schema_version=1,status='REFERENCE_COMPLETE',binding=pin(binding_path),helper=pin(Path(__file__).resolve()),
            input_pins=binding['inputs'],reference_started_monotonic=started,reference_elapsed_seconds=time.monotonic()-started,
            reference_bytes_hashed=position,reference_hash_copy_calls=copy_count,unique_checkpoint_count=len(checkpoints),checkpoint_sha256=hashes,
            size_values=sizes,descriptors=descriptors,chunk=CHUNK,N=N,B=2,M=2,Q=Q,R=R,C=C,E=E,
            total_future_producer_bytes=9017363601,captured_future_producer_bytes=209,actual_reference_owner_or_subject_calls=0,
            expected_actual_reads=8799,expected_candidate_calls=9879,expected_terminal_calls=10095,expected_closures=216,
            recipe='Each virtual bulk is a prefix of periodic bytes00..ff reset at offset0 perfile. Prefix hashes share one independent SHA stream with copy at unique sizes.',
            memory='One1MiB shared independent reference block plus small hash/checkpoint metadata. No wholebulk/model/original body exists. CPython/RSS unknown.',
            authority='Invented fixture expected digests only; no historical path/digest/consumer/source authority inherited.',
            qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_real_roster','new84_runtime','resource_fit','scientific']})
    except BaseException as error:
        record=dict(schema_version=1,status='REFERENCE_PARTIAL_OR_ERROR_FIRST_RESULT_RETAINED',error_class=type(error).__name__,
            message=str(error)[:2048],traceback=traceback.format_exc(),reference_started_monotonic=started,
            reference_elapsed_seconds=time.monotonic()-started,reference_bytes_hashed=position,reference_hash_copy_calls=copy_count,
            completed_checkpoint_sha256=hashes,size_values=sizes,descriptors=None,
            missing_expected_digests='UNKNOWN; producer execution must not consume partial reference data.',subject_imports=0,subject_calls=0)
    finally:
        if record is not None:
            final_late=deadline is not None and time.monotonic()>=deadline
            record['final_deadline_veto']=final_late
            if final_late and record['status']=='REFERENCE_COMPLETE':record['status']='REFERENCE_PARTIAL_OR_ERROR_FIRST_RESULT_RETAINED';record['descriptors']=None
            with output.open('xb') as out:out.write((json.dumps(record,sort_keys=True,indent=2)+'\n').encode())
            print(json.dumps(dict(proof=pin(output),status=record['status'],reference_bytes_hashed=position,checkpoint_copies=copy_count)))
    return 0 if record and record['status']=='REFERENCE_COMPLETE' else 1


if __name__=='__main__':raise SystemExit(main())
