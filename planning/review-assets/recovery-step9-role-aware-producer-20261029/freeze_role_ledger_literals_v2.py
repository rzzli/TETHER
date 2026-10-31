"""Exact authorized fixture delta/freeze; reads NEW review assets only."""
import ast
import base64
import hashlib
import json
import zlib
from pathlib import Path

H=Path(__file__).resolve().parent


def rb(n):return (H/n).read_bytes()
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(n):
    b=rb(n);return dict(path=str((H/n).resolve()),bytes=len(b),sha256=sha(b))
def js(n):return json.loads(rb(n))
def blob(b):
    r=zlib.decompress(base64.b64decode(b['data'],validate=True));assert sha(r)==b['sha256'] and len(r)==b['bytes'];return r
def pval(v):
    if type(v) is dict:
        if set(v)=={'$bytes_hex'}:return bytes.fromhex(v['$bytes_hex'])
        if set(v)=={'$tuple'}:return tuple(pval(x) for x in v['$tuple'])
        return {k:pval(x) for k,x in v.items()}
    if type(v) is list:return [pval(x) for x in v]
    return v
def render(x):return x.hex() if type(x) is bytes else x
def diffs(a,b,p=()):
    assert type(a) is type(b),(p,type(a),type(b))
    if type(a) is dict:
        assert set(a)==set(b),p
        return [d for k in a for d in diffs(a[k],b[k],p+(k,))]
    if type(a) in (list,tuple):
        assert len(a)==len(b),p
        return [d for i in range(len(a)) for d in diffs(a[i],b[i],p+(i,))]
    return [] if a==b else [dict(path=list(p),before=render(a),after=render(b))]
def pub(name,value):
    raw=(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()
    with (H/name).open('xb') as f:f.write(raw)
    return pin(name)


def main():
    assert pin('ROLE-AWARE-FORMAT-LITERAL-CORPUS-v1.json')['sha256']=='16899fd5481e8bb63790dc9314acb8553af3eec65a81dc14ac6ce5cbeba56232'
    assert pin('role_ledger_independent_tests_v1.py')['sha256']=='8c4f5d138b01f4dd97bebd349b44ec92ac1658468f6ec502c6305da6b24453c8'
    assert pin('ROLE-AWARE-FORMAT-LITERAL-STRUCTURE-PROOF-v1.json')['sha256']=='5279908d8af849e994afbf9bf69bbf58db01bf7b8182023da16ead628b9651cc'
    old=js('ROLE-AWARE-FORMAT-LITERAL-CORPUS-v1.json');new=js('ROLE-AWARE-FORMAT-LITERAL-CORPUS-v2.json')
    assert [x['id'] for x in old['bases']]==[x['id'] for x in new['bases']]
    changes=[];unchanged=[];changed_mutations=[]
    empty=hashlib.sha256(b'').hexdigest()
    old_candidate=next(x['raw']['sha256'] for x in old['bases'] if x['id']=='n4_candidate_captured')
    new_candidate=next(x['raw']['sha256'] for x in new['bases'] if x['id']=='n4_candidate_captured')
    for a,b in zip(old['bases'],new['bases']):
        ident=a['id'];av=pval(json.loads(blob(a['semantic_value'])));bv=pval(json.loads(blob(b['semantic_value'])))
        ds=diffs(av,bv)
        assert a['anchors']==b['anchors'] and a['expected']==b['expected'] and a['layer']==b['layer']
        for d in ds:
            p=d['path'];allowed=False
            if ident in ('n4_candidate_captured','n4_terminal_captured') and p in (['files',0,'expected_sha256'],['files',0,'actual_sha256']):allowed=d['after']==empty
            if ident=='prospective_mixed_roles' and len(p)==3 and p[0]=='files' and p[1] in (0,1) and p[2] in ('expected_sha256','actual_sha256'):allowed=d['after']==empty
            if ident=='prospective_full_cap_shape_invalid_api' and len(p)==3 and p[0]=='files' and p[1] in range(128) and p[2]=='expected_sha256':allowed=d['after']==empty
            if ident=='n4_terminal_captured' and p==['header','previous_ledger_sha256']:allowed=d['before']==old_candidate and d['after']==new_candidate
            if ident=='fragment_13_observed' and p==['calls',0,'count_atom','value']:allowed=(d['before'],d['after'])==(7,0)
            if ident=='fragment_14_observed' and p==['calls',0,'input_handle_atom','value']:allowed=(d['before'],d['after'])==(0x0102030405060708,0)
            assert allowed,(ident,d)
        if ds:
            changes.append(dict(id=ident,semantic_changes=ds,old_raw_sha256=a['raw']['sha256'],new_raw_sha256=b['raw']['sha256']))
        else:
            assert a==b,ident
            unchanged.append(ident)
    assert len(changes)==6 and len(unchanged)==34
    for a,b in zip(old['byte_negatives'],new['byte_negatives']):
        da={k:v for k,v in a.items() if k!='sha256'};db={k:v for k,v in b.items() if k!='sha256'}
        assert da==db
        if a['sha256']!=b['sha256']:changed_mutations.append(a['id'])
    def methods(name):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(rb(name))) if isinstance(n,ast.FunctionDef) and n.name.startswith('test')}
    am=methods('role_ledger_independent_tests_v1.py');bm=methods('role_ledger_independent_tests_v2.py')
    assert set(am)==set(bm) and len(am)==4
    assert [k for k in am if am[k]!=bm[k]]==['test01_literal_encode_decode_and_anchors']
    proof=js('ROLE-AWARE-FORMAT-LITERAL-STRUCTURE-PROOF-v2.json')
    assert proof['status']=='PASS' and proof['methods']==6 and not proof['failures'] and not proof['errors']
    delta=pub('ROLE-AWARE-FORMAT-LITERAL-DELTA-v2.json',dict(schema_version=1,status='EXACT_FOUR_SELECTED_CORRECTIONS_ONLY',
        root=pin('ROLE-AWARE-FORMAT-LITERAL-ROOT-CORRECTION-v2.json'),before_peer=pin('ROLE-AWARE-FORMAT-LITERAL-INDEPENDENT-REVIEW-v1.json'),
        base_changes=changes,unchanged_base_ids=unchanged,semantic_field_changes=sum(len(x['semantic_changes']) for x in changes),
        byte_mutation_recipes_expected_outcomes_unchanged=225,dependent_mutation_hash_changes=changed_mutations,
        anchors_byte_identical=134,test_methods=4,only_changed_test_method='test01_literal_encode_decode_and_anchors',
        assertion_change='Pristine pre-encode deep copy; same(actual caller, pristine); both decoded comparisons use pristine. Other three test method ASTs identical.',
        source_schema_unchanged=True,subject_imports=0,subject_runs=0))
    names=[
        'ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json','ROLE-AWARE-PRODUCER-FORMAT-FREEZE-v2.json',
        'ROLE-AWARE-PRODUCER-FORMAT-INDEPENDENT-REVIEW-v2.json','ROLE-AWARE-PRODUCER-FORMAT-SCHEMA-ACCEPTANCE-v2.json',
        'ROLE-AWARE-FORMAT-LITERAL-ROOT-CORRECTION-v2.json','ROLE-AWARE-FORMAT-LITERAL-INDEPENDENT-REVIEW-v1.json',
        'ROLE-AWARE-FORMAT-LITERAL-SELF-REVIEW-v1.json','ROLE-AWARE-FORMAT-LITERAL-STRUCTURE-PROOF-v1.json',
        'ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT-DRAFT-v1.json','ROLE-AWARE-FORMAT-CORPUS-PRECHECK-v1.json',
        'author_role_ledger_literals_v1.py','ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT-v1.json','ROLE-AWARE-FORMAT-LITERAL-CORPUS-v1.json',
        'ROLE-AWARE-FORMAT-LITERAL-PROVENANCE-v1.json','role_ledger_independent_tests_v1.py','check_role_ledger_literal_structure_v1.py',
        'prepare_role_ledger_fixture_successor_v2.py','author_role_ledger_literals_v2.py','ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT-v2.json',
        'ROLE-AWARE-FORMAT-LITERAL-CORPUS-v2.json','ROLE-AWARE-FORMAT-LITERAL-PROVENANCE-v2.json','role_ledger_independent_tests_v2.py',
        'check_role_ledger_literal_structure_v2.py','ROLE-AWARE-FORMAT-LITERAL-STRUCTURE-PROOF-v2.json',Path(__file__).name]
    freeze=pub('ROLE-AWARE-FORMAT-LITERAL-FREEZE-v2.json',dict(schema_version=1,status='CORRECTED_PREIMPLEMENTATION_LITERALS_AND_TESTS_FROZEN',
        pins=[pin(n) for n in names]+[delta],counts=js('ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT-v2.json')['actual_counts'],
        structural_result=dict(methods=6,passed=6,failed=0,errors=0,bases=40,section_frames=320,byte_negatives=225,anchors=134),
        chronology='All v1 data and its first5PASS/1FAIL proof remain retained. V2 applies only Root-selected four preparation corrections. No target codec or producer source exists/was imported/tested.',
        distinction='Data-only decode never provides live ProducerSnapshot, context, raw fact, diagnostic token, or legacy48 identity. Full-cap API0 negative is a shape/hash control, not fabricated success.',
        pending=['Native exact delta peer','separate root acceptance/source scope','genuine producer first-slot/diagnostic/store/legacy integration controls','new84 roster/first entry/physical writer/native/resource/scientific gates'],
        activity=dict(fixture_author_v2_runs=1,fixture_structure_v2_runs=1,subject_imports=0,subject_runs=0,original_or_payload_operations=0,native_physical_operations=0),
        qualification={k:False for k in ['codec_implemented','producer_implemented','real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(delta=delta,freeze=freeze,test=pin('role_ledger_independent_tests_v2.py'),
                         corpus=pin('ROLE-AWARE-FORMAT-LITERAL-CORPUS-v2.json'),proof=pin('ROLE-AWARE-FORMAT-LITERAL-STRUCTURE-PROOF-v2.json'),
                         semantic_field_changes=sum(len(x['semantic_changes']) for x in changes),dependent_mutation_hash_changes=len(changed_mutations))))


if __name__=='__main__':main()
