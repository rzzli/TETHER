"""Literal fixture authoring only: no UTF8 codec, decoder or vendor adapter.

Expected scalar/byte pairs and malformed-byte positions below are authored from
UTF8-ORACLE-SPEC-v1.md. Helpers frame those expectations; they do not classify or
decode input. Structural validation is a separate, nonsemantic operation.
"""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SPEC=HERE/'UTF8-ORACLE-SPEC-v1.md'
CORPUS=HERE/'UTF8-ORACLE-CORPUS-v1.json'
PROVENANCE=HERE/'UTF8-ORACLE-GENERATION-PROVENANCE-v1.json'
CASES=[]

def digest(raw):return hashlib.sha256(raw).hexdigest()
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=digest(raw))
def error(code,offset,start,offending):
    return dict(code=code,byte_offset=offset,sequence_start_offset=start,offending_byte=offending)
def step(raw,final,status,*,emitted=(),pending='',width=None,consumed=None,examined=None,total=None,total_examined=None,
         failure=None,unconsumed=''):
    raw=bytes.fromhex(raw);pending=bytes.fromhex(pending);unconsumed=bytes.fromhex(unconsumed)
    # Length defaults only frame fully consumed known fixtures. Exceptional
    # consumed/examined values are explicitly authored at each negative case.
    count=len(raw) if consumed is None else consumed
    observed=count if examined is None else examined
    return dict(chunk_hex=raw.hex(),final=final,expected=dict(status=status,emitted_scalars=list(emitted),decoded_scalars=None,
        pending_hex=pending.hex(),pending_width=width,consumed_in_chunk=count,examined_in_chunk=observed,
        consumed_total=count if total is None else total,examined_total=observed if total_examined is None else total_examined,
        unconsumed_hex=unconsumed.hex(),error=failure,finalization=('failed' if status=='error' else 'succeeded') if final else 'not_requested'))
def case(identity,stratum,purpose,rule,steps):
    raw=b'';cuts=[];decoded=[]
    for item in steps:
        raw+=bytes.fromhex(item['chunk_hex']);cuts.append(len(raw))
        decoded+=item['expected']['emitted_scalars'];item['expected']['decoded_scalars']=list(decoded)
    CASES.append(dict(id=identity,stratum=stratum,purpose=purpose,expectation_rule=rule,
        raw_hex=raw.hex(),sha256=digest(raw),chunk_cuts=cuts,steps=steps))

# Scalar expectations are literal integer/hex pairs, not implementation output.
SCALARS=[
    ('cent',0x00A2,'c2a2'),('two_byte_max',0x07FF,'dfbf'),
    ('three_byte_min',0x0800,'e0a080'),('euro',0x20AC,'e282ac'),
    ('before_surrogates',0xD7FF,'ed9fbf'),('after_surrogates',0xE000,'ee8080'),
    ('noncharacter_fdd0',0xFDD0,'efb790'),('bom',0xFEFF,'efbbbf'),('bmp_max',0xFFFF,'efbfbf'),
    ('four_byte_min',0x10000,'f0908080'),('grinning_face',0x1F600,'f09f9880'),('scalar_max',0x10FFFF,'f48fbfbf'),
]

def build():
    case('ascii/empty_final','ASCII and empty feeds','Empty stream finalizes without output','Empty boundary plus final request',
        [step('',True,'finished')])
    ASCII=[
        ('ordinary','41427a','Ordinary ASCII scalar identity'),
        ('raw_nul','00','Raw NUL emits U+0000; no JSON or harness inference'),
        ('control_edges','00011f207f','ASCII controls, space and DEL are scalar values'),
        ('json_escape_bmp','225c753030343122','ASCII JSON escape spelling is not decoded as U+0041'),
        ('json_escape_surrogate_pair','225c75443833445c754445303022','ASCII JSON surrogate-pair spelling stays ASCII'),
        ('json_escape_lone_surrogate','225c754438303022','ASCII lone-surrogate spelling stays validUTF8, regardless of JSON semantics'),
        ('json_backslash_prefix','225c','An unfinished JSON string escape is a finished validUTF8 stream'),
        ('json_object_prefix','7b2261223a','An unfinished JSON object prefix is validUTF8'),
    ]
    for name,raw,purpose in ASCII:
        case('ascii/'+name,'ASCII and JSON escape controls',purpose,'One-byte00..7F identity; no JSON parser',
            [step(raw,True,'finished',emitted=list(bytes.fromhex(raw)))])
    for name,scalar,raw in SCALARS:
        data=bytes.fromhex(raw);width=len(data)
        case('scalar/'+name,'Literal scalar boundaries','Complete literal scalar '+hex(scalar),'Literal scalar/hex pair from encoding table',
            [step(raw,True,'finished',emitted=[scalar])])
        for cut in range(1,width):
            case('interior/'+name+'/'+str(cut),'Every declared representative interior cut',
                'Retain exactly'+str(cut)+'bytes, then complete the scalar','Fixed literal scalar and every interior byte cut',
                [step(data[:cut].hex(),False,'pending',pending=data[:cut].hex(),width=width),
                 step(data[cut:].hex(),True,'finished',emitted=[scalar],total=width,total_examined=width)])
    for name,scalar,raw in (SCALARS[0],SCALARS[3],SCALARS[10]):
        data=bytes.fromhex(raw);width=len(data);steps=[]
        for i,value in enumerate(data):
            last=i==width-1
            steps.append(step(bytes([value]).hex(),last,'finished' if last else 'pending',emitted=[scalar] if last else [],
                pending='' if last else data[:i+1].hex(),width=None if last else width,total=i+1,total_examined=i+1))
        case('multichunk/'+name,'Byte-at-a-time completion','Complete one scalar across all its bytes','Literal scalar table; each byte a separate chunk',steps)
    case('multichunk/empty_while_pending','Empty feeds','Empty feeds preserve both boundary and pending state','Empty feed changes no byte/scalar state',[
        step('',False,'boundary'),step('e2',False,'pending',pending='e2',width=3,total=1,total_examined=1),
        step('',False,'pending',pending='e2',width=3,total=1,total_examined=1),
        step('82ac',False,'boundary',emitted=[0x20AC],total=3,total_examined=3),step('',True,'finished',total=3,total_examined=3)])
    case('mixed/ascii_then_partial_euro','Mixed complete and partial tails','Commit ASCII before a pending3byte scalar','A+E282 pending, then euro+B',[
        step('41e282',False,'pending',emitted=[0x41],pending='e282',width=3),
        step('ac42',True,'finished',emitted=[0x20AC,0x42],total=5,total_examined=5)])
    case('mixed/complete_two_then_partial_four','Mixed complete and partial tails','Keep a complete scalar before an astral pending tail','Cent+F09F pending, then complete astral scalar',[
        step('c2a2f09f',False,'pending',emitted=[0xA2],pending='f09f',width=4),
        step('9880',True,'finished',emitted=[0x1F600],total=6,total_examined=6)])
    case('mixed/three_widths_three_chunks','Mixed complete and partial tails','Multiple completions and new pending sequences across chunks','Literal A,cent,euro,astral,Z sequence',[
        step('41c2a2e2',False,'pending',emitted=[0x41,0xA2],pending='e2',width=3),
        step('82acf09f',False,'pending',emitted=[0x20AC],pending='f09f',width=4,total=8,total_examined=8),
        step('98805a',True,'finished',emitted=[0x1F600,0x5A],total=11,total_examined=11)])
    case('mixed/nul_does_not_terminate','NUL is a scalar','Continue after a raw NUL','No NUL sentinel in strictUTF8',[
        step('4100c2',False,'pending',emitted=[0x41,0],pending='c2',width=2),
        step('a242',True,'finished',emitted=[0xA2,0x42],total=5,total_examined=5)])
    case('mixed/bom_is_not_removed','BOM preservation','An initial BOM is emitted, followed by ASCII','UTF8 not UTF8-SIG',[
        step('efbb',False,'pending',pending='efbb',width=3),step('bf41',True,'finished',emitted=[0xFEFF,0x41],total=4,total_examined=4)])
    # Every unfinished prefix of a fixed representative of each width.
    for name,scalar,raw in (SCALARS[0],SCALARS[3],SCALARS[10]):
        data=bytes.fromhex(raw);width=len(data)
        for cut in range(1,width):
            prefix=data[:cut].hex();failure=error('premature_eof',cut,0,None)
            case('eof/same_chunk/'+name+'/'+str(cut),'Premature EOF','Reject unfinished scalar at requested same-chunk EOF','Pending prefix plus final request',[
                step(prefix,True,'error',pending=prefix,width=width,failure=failure)])
            case('eof/empty_final/'+name+'/'+str(cut),'Premature EOF','Reject pending bytes on a later empty final feed','Empty final consumes/examines no extra bytes',[
                step(prefix,False,'pending',pending=prefix,width=width),
                step('',True,'error',pending=prefix,width=width,total=cut,total_examined=cut,failure=failure)])
    NEGATIVES=[
        ('stray_80','80','unexpected_continuation',0,'',None),('stray_bf','bf','unexpected_continuation',0,'',None),
        ('overlong_lead_c0','c0af','invalid_lead',0,'',None),('overlong_lead_c1','c180','invalid_lead',0,'',None),
        ('lead_f5','f5808080','invalid_lead',0,'',None),('lead_f8','f888808080','invalid_lead',0,'',None),('lead_ff','ff','invalid_lead',0,'',None),
        ('two_ascii_continuation','c241','invalid_continuation',1,'c2',2),('two_new_lead','c2c2a2','invalid_continuation',1,'c2',2),
        ('three_ascii_second','e241','invalid_continuation',1,'e2',3),('three_ascii_third','e28241','invalid_continuation',2,'e282',3),
        ('four_ascii_second','f041','invalid_continuation',1,'f0',4),('four_ascii_third','f09f41','invalid_continuation',2,'f09f',4),
        ('four_ascii_fourth','f09f9841','invalid_continuation',3,'f09f98',4),
        ('three_overlong_low','e080af','overlong_sequence',1,'e0',3),('three_overlong_high','e09fbf','overlong_sequence',1,'e0',3),
        ('four_overlong_low','f08080af','overlong_sequence',1,'f0',4),('four_overlong_high','f08fbfbf','overlong_sequence',1,'f0',4),
        ('surrogate_low','eda080','surrogate_scalar',1,'ed',3),('surrogate_high','edbfbf','surrogate_scalar',1,'ed',3),
        ('out_of_range_low','f4908080','out_of_range_scalar',1,'f4',4),('out_of_range_high','f4bfbfbf','out_of_range_scalar',1,'f4',4),
        ('nul_is_not_continuation','c200','invalid_continuation',1,'c2',2),('del_is_not_continuation','e27f','invalid_continuation',1,'e2',3),
    ]
    for name,raw,code,offset,pending,width in NEGATIVES:
        data=bytes.fromhex(raw)
        case('invalid/'+name,'Malformed byte sequences','Reject the authored earliest offending byte','Literal negative position and rule category',[
            step(raw,True,'error',pending=pending,width=width,consumed=offset,examined=offset+1,
                failure=error(code,offset,0,data[offset]),unconsumed=data[offset:].hex())])
    case('invalid/valid_prefix_committed','Valid output before byte error','Retain valid output preceding a later same-chunk failure','A+cent emitted, E2 pending,28 rejected at offset4',[
        step('41c2a2e228a142',True,'error',emitted=[0x41,0xA2],pending='e2',width=3,consumed=4,examined=5,
            failure=error('invalid_continuation',4,3,0x28),unconsumed='28a142')])
    case('invalid/valid_scalar_then_stray','Valid output before byte error','Keep euro output before a stray continuation','Euro emitted,80 rejected at a new scalar boundary',[
        step('e282ac80',True,'error',emitted=[0x20AC],consumed=3,examined=4,
            failure=error('unexpected_continuation',3,3,0x80),unconsumed='80')])
    case('eof/valid_prefix_committed','Valid output before EOF error','Preserve ASCII while the following scalar remains incomplete','A emitted, E282 pending at requested EOF',[
        step('41e282',True,'error',emitted=[0x41],pending='e282',width=3,failure=error('premature_eof',3,1,None))])
    failure=error('invalid_continuation',1,0,0x41)
    case('absorbing/pending_error_later_valid_bytes_ignored','Absorbing error','Do not recover when a later chunk could complete the pending scalar','Offending byte examined/notconsumed; subsequent bytes ignored',[
        step('c2',False,'pending',pending='c2',width=2),
        step('41a2',False,'error',pending='c2',width=2,consumed=0,examined=1,total=1,total_examined=2,failure=failure,unconsumed='41a2'),
        step('a242',True,'error',pending='c2',width=2,consumed=0,examined=0,total=1,total_examined=2,failure=failure,unconsumed='a242')])
    failure=error('unexpected_continuation',0,0,0x80)
    case('absorbing/boundary_error_empty_final','Absorbing error','Empty final request preserves the first byte error','No extra byte/offset or replacement after rejection',[
        step('80',False,'error',consumed=0,examined=1,failure=failure,unconsumed='80'),
        step('',True,'error',consumed=0,examined=0,total=0,total_examined=1,failure=failure)])
    return dict(schema_version=1,profile='strict_UTF8_byte_chunk_oracle_v1',status='fixed_expected_fixtures_not_adapter_or_native_qualification',
        specification=pin(SPEC),limits=dict(maximum_fixtures=128,maximum_steps=1024,maximum_bytes_per_fixture=128,maximum_total_supplied_bytes=32768),
        error_recovery='none_absorbing',normalization='none',JSON_membership='out_of_scope',
        expected_scalar_encoding_pairs=[dict(id=name,scalar=scalar,hex=raw) for name,scalar,raw in SCALARS],cases=CASES)

if __name__=='__main__':
    assert not CORPUS.exists() and not PROVENANCE.exists(),'Preserve prior authored fixture bytes'
    corpus=build()
    with CORPUS.open('x',encoding='utf-8') as out:json.dump(corpus,out,sort_keys=True,indent=2);out.write('\n')
    provenance=dict(schema_version=1,status='literal_fixture_generation_before_any_adapter',generator=pin(Path(__file__)),
        specification=pin(SPEC),corpus=pin(CORPUS),fixture_count=len(CASES),steps=sum(len(c['steps']) for c in CASES),
        supplied_bytes=sum(len(bytes.fromhex(c['raw_hex'])) for c in CASES),
        basis='Authored literal scalar/hex pairs, every declared representative interior cut, authored negative-byte positions and explicit step expectations. Helpers only frame lengths, byte slices, cumulative emitted lists and hashes.',
        decoder_or_codec_calls=0,vendor_calls=0,model_token_ID_selection=False,CPU_GGUF_oldpack_access=0,compiler_or_native_calls=0,
        semantic_validation='pending_independent_review_and_postfreeze_reference_check')
    with PROVENANCE.open('x',encoding='utf-8') as out:json.dump(provenance,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(corpus=pin(CORPUS),provenance=pin(PROVENANCE),fixtures=len(CASES),steps=provenance['steps'],bytes=provenance['supplied_bytes'])))
