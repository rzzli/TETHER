"""Nine normative DATA classifications only; no encoder or subject calls."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import struct
import zlib

H=Path(__file__).resolve().parent
SRC=H.parent/'recovery-step9-role-aware-source-20261029'


def pin(p):
    b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def js(p):return json.loads(p.read_bytes())
def pub(n,v):
    b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
    with (H/n).open('xb') as f:f.write(b)
    return pin(H/n)
def blob(x):
    b=zlib.decompress(base64.b64decode(x['data'],validate=True));assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256'];return b
def untransport(v):
    if type(v) is dict:
        if set(v)=={'$bytes_hex'}:return bytes.fromhex(v['$bytes_hex'])
        if set(v)=={'$tuple'}:return tuple(untransport(x) for x in v['$tuple'])
        return {k:untransport(x) for k,x in v.items()}
    if type(v) is list:return [untransport(x) for x in v]
    return v


def main():
    choice=pin(H/'ROLE-AWARE-RESERVATION-ORACLE-CORRECTION-v3.json')
    assert choice['sha256']=='11949f60ddc08b4a02d6262dd42b7859a7e18f2afe994eb49107f04f8eee7e8a'
    prior=pin(H/'ROLE-AWARE-FORMAT-LITERAL-CORPUS-v2.json')
    assert prior['sha256']=='55e01082063f23128780cf47f6f8275f360a7e896e400fa4b1271cd081a5581c'
    test=pin(H/'role_ledger_independent_tests_v2.py')
    assert test['sha256']=='a3051f08375fd412d49a9a69ce180b65de69214500c787f9562a23cc3859beea'
    old=js(Path(prior['path']));new=copy.deepcopy(old)
    base=next(x for x in old['bases'] if x['id']=='n4_hash_failure_terminal')
    value=untransport(json.loads(blob(base['semantic_value'])));raw=blob(base['raw'])
    N=len(value['files']);B=value['header']['early_count'];M=len(value['modules']);chunk=value['header']['read_chunk']
    R=sum((f['expected_size']//chunk+(f['expected_size']%chunk!=0)+16) for f in value['files'] if f['expected_size']>0)
    formulas={'reserved_R':R,'reserved_C':6*N+R,'reserved_E':6*N+2*B+2*M+192}
    assert (N,B,M,chunk,R,formulas['reserved_C'],formulas['reserved_E'])==(1,0,0,65536,17,23,198)
    offsets={'reserved_R':168,'reserved_C':172,'reserved_E':176}
    for k,offset in offsets.items():assert struct.unpack_from('<I',raw,offset)[0]==formulas[k]==value['header'][k]
    wanted={f'reserved_{r:02}_{p}':field for r,field in ((1,'reserved_R'),(2,'reserved_C'),(3,'reserved_E')) for p in range(3)}
    evidence=[]
    for before,after in zip(old['byte_negatives'],new['byte_negatives']):
        if before['id'] not in wanted:assert before==after;continue
        field=wanted[before['id']];p=before['patch'];assert before['base']==base['id'] and not p['rehash_sections']
        assert p['offset'] in (offsets[field],offsets[field]+2,offsets[field]+3) and p['hex']=='01'
        b=bytearray(raw);x=bytes.fromhex(p['hex']);b[p['offset']:p['offset']+len(x)]=x
        assert len(b)==before['bytes'] and hashlib.sha256(b).hexdigest()==before['sha256']
        actual=struct.unpack_from('<I',b,offsets[field])[0];assert actual!=formulas[field]
        assert before['expected']==dict(accepted=False,required_code='RESERVED_NONZERO')
        after['expected']['required_code']='STATE_CONTRADICTION'
        evidence.append(dict(id=before['id'],field=field,field_offset=offsets[field],patch_offset=p['offset'],
            original_u32=formulas[field],mutated_u32=actual,mutation_raw_sha256=before['sha256'],still_rejects=True,
            prior_code='RESERVED_NONZERO',required_code='STATE_CONTRADICTION'))
    assert {e['id'] for e in evidence}==set(wanted) and len(evidence)==9
    assert new['bases']==old['bases'] and len(new['bases'])==40 and len(new['byte_negatives'])==225
    for before,after in zip(old['byte_negatives'],new['byte_negatives']):
        a=copy.deepcopy(before);b=copy.deepcopy(after);a['expected'].pop('required_code');b['expected'].pop('required_code');assert a==b
    assert sum(len(b['anchors']) for b in new['bases'])==134
    c=js(H/'ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT-v2.json')
    c['basis'].append(choice);c['basis'].append(pin(H/'ROLE-AWARE-FORMAT-LITERAL-CORPUS-v2.json'))
    c['actual_counts'].update(reservation_data_regions=3,true_zero_padding_regions=29,
        true_zero_padding_region_mutations=87,reservation_data_formula_mutations=9)
    c['reserved_region_accounting']='The historical32 region entries are29 true zero-padding regions and3 reservation DATA regions. reserved_R/C/E are u32 values, not zero bytes. No mutation/case/anchor is removed.'
    c['normative_reservation_code']='Exactly nine existing reserved_01/02/03 variants must reject STATE_CONTRADICTION for mismatch with the recomputed R/C/E formula. All other codes unchanged.'
    c['frozen_test']=test
    cp=pub('ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT-v3.json',c)
    new['contract']=cp
    fp=pub('ROLE-AWARE-FORMAT-LITERAL-CORPUS-v3.json',new)
    first=pin(SRC/'ROLE-AWARE-INDEPENDENT-CODEC_FIRST-PROOF-v4.json')
    assert first['sha256']=='7e01d1288d29c229f473524a5b9ece22a0578513fc2fc43911dc2c5a78bcd0aa'
    actual=js(Path(first['path']))
    assert actual['codec_forwarding']['facade_attempts']==83 and actual['codec_forwarding']['actual_source_check_sites']==1288
    dp=pub('ROLE-AWARE-FORMAT-LITERAL-DELTA-v3.json',dict(schema_version=1,status='EXACT_NINE_ERROR_CODES_ONLY_NO_BYTE_CHANGES',root_choice=choice,
        old_corpus=prior,new_corpus=fp,unchanged_base_objects=40,unchanged_base_raw_and_semantic_bytes=True,
        unchanged_mutation_recipes_raw_bytes_hashes_and_IDs=225,unchanged_anchors=134,changed_required_codes=evidence,
        normative_reason='Frozen b71 layout types R/C/E as u32 reservation data; startswith(reserved) was an author selector mistake. This correction follows that prior schema, not a source workaround.',
        independent_formula=dict(N=N,B=B,M=M,chunk=chunk,positive_sizes=[f['expected_size'] for f in value['files'] if f['expected_size']>0],**formulas),
        region_classes=dict(total_historical_region_records=32,actual_zero_padding=29,reservation_data=3),frozen_test_unchanged=test,
        subject_imports=0,subject_calls=0))
    pp=pub('ROLE-AWARE-FORMAT-LITERAL-PROVENANCE-v3.json',dict(schema_version=1,status='POST_SOURCE_FAILURE_NORMATIVE_CLASSIFICATION_CORRECTION',author=pin(Path(__file__).resolve()),
        contract=cp,corpus=fp,delta=dp,previous_provenance=pin(H/'ROLE-AWARE-FORMAT-LITERAL-PROVENANCE-v2.json'),
        chronology='The40 raw/value goldens predate source. This explicit nine-code correction follows the first actual83-call abort and corrects the fixture author mistake using the unchanged pre-code schema. No pre-fix chronology or actual run is reconstructed.',
        first_actual_proof=first,retained_known_forwarding=actual['codec_forwarding'],completed_test_result=None,
        completed_test_result_reason='T.run aborted while unittest formatted a failure; method outcomes/remainder were not returned and remain UNKNOWN.',
        data_checks=dict(groups_passed=3,whole_base_and_mutation_identity=True,all_nine_formula_mismatches=True,frozen_test_and_region_count=True),
        source_changes='NONE; sourceV2 reservation classification remains unchanged. Exception lifecycle/refreeze changes are separate.',
        activity=dict(subject_imports=0,subject_calls=0,producer_calls=0,original_payload_native_physical_operations=0)))
    freeze=pub('ROLE-AWARE-FORMAT-LITERAL-FREEZE-v3.json',dict(schema_version=1,status='NORMATIVE_NINE_CODE_CORRECTION_FROZEN_PENDING_PEER',
        pins=[cp,fp,dp,pp,choice,test,pin(Path(__file__).resolve()),prior,pin(H/'ROLE-AWARE-FORMAT-LITERAL-FREEZE-v2.json'),
              pin(H/'ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json'),pin(H/'ROLE-AWARE-FORMAT-LITERAL-INDEPENDENT-REVIEW-v2.json'),first],
        base_histories=40,byte_negative_expansions=225,anchors=134,changed_error_codes=9,true_zero_padding_regions=29,reservation_data_regions=3,
        data_checks_passed=3,actual_source_calls_in_this_preparation=0,
        pending=['Native exact nine-code/data-metadata peer','root acceptance','explicitV2 source execution scope+binding'],
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(contract=cp,corpus=fp,delta=dp,provenance=pp,freeze=freeze,changed_codes=9,data_check_groups=3)))


if __name__=='__main__':main()
