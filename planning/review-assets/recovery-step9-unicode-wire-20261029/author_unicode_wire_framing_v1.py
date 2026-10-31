"""Literal DESIGN framing examples, not a complete profile pack or parser.

Synthetic token labels below are never observed tokenizer/native results.
Only new frozen corpus/stage metadata and the prospective design are read.
"""
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
CONTROL=HERE.parent/'recovery-step9-unicode-control-20261029'
CONTRACT=HERE/'UNICODE-WIRE-DESIGN-CONTRACT-v2.json'
OUT=HERE/'UNICODE-WIRE-FRAMING-FIXTURES-v1.json'
FREEZE=HERE/'UNICODE-WIRE-FRAMING-FREEZE-v1.json'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=sha(raw))
def write(path,v):
    with path.open('x',encoding='utf-8') as out:json.dump(v,out,sort_keys=True,indent=2,ensure_ascii=True);out.write('\n')
def u32(v):return struct.pack('<I',v)
def span(raw):return u32(len(raw))+raw
def identity(v):return span(v.encode('ascii'))
def tri(v):return 2 if v is None else (1 if v else 0)
def main():
    assert not OUT.exists() and not FREEZE.exists(),'Preserve versioned framing fixtures'
    d=json.loads(CONTRACT.read_text(encoding='utf-8'));assert pin(CONTRACT)['sha256']=='ddf9fd360d72def0b91bd99b047422bf8ee623c0f8d6e0ba73535e04a7af1abc'
    s=d['semantic_contract'];fp=d['semantic_sha256']
    corpus=json.loads((CONTROL/'UNICODE-CONTROL-CORPUS-v1.json').read_text(encoding='utf-8'))['cases']
    stages=json.loads((CONTROL/'UNICODE-CONTROL-STAGES-v1.json').read_text(encoding='utf-8'))['stages']
    assert [corpus[i]['id'] for i in (0,76,78,83)]==['baseline/mechanism_asof0','negative/lone_surrogate_escape','guard/raw_NUL','guard/premature_EOF']
    grammars=list(dict.fromkeys(x['grammar_sha256'] for x in stages));strata=[x['name'] for x in s['corpus']['strata']]
    pack=[];rows=[]
    def fragment(name,kind,raw,valid,expected):
        pack.append(dict(id=name,component=kind,raw_hex=raw.hex(),bytes=len(raw),sha256=sha(raw),component_framing_expected=valid,
            expected=expected,complete_profile_pack=False,native_qualification=False))
    header=(b'R09NU01\0'+u32(1)+b''.join(bytes.fromhex(v) for v in [fp,s['corpus']['corpus_sha256'],s['corpus']['stages_sha256'],
        '65a34539dd1bdecb20ed85724c58f80e362113cb4db969f5edf60b48af9a111d','05c214f42e9214691b5675cca58e67a6265dd069d2e7829f604df23c7ccca3e6'])+
        b''.join(u32(v) for v in [4,2,84,4]))
    assert len(header)==188
    fragment('header/exact','fixed_header',header,True,dict(version=1,stages=4,grammars=2,cases=84,classes=4,consumed=188,full_pack_error='missing_records'))
    for name,raw,why in [('old_magic',b'R09NC02\0'+header[8:],'magic'),('big_endian_version',header[:8]+b'\0\0\0\1'+header[12:],'version'),
        ('wrong_case_count',header[:180]+u32(85)+header[184:],'exact_counts'),('truncated_digest',header[:130],'truncated'),
        ('trailing_header_byte',header+b'x','fixed_header_trailing')]:fragment('header/'+name,'fixed_header',raw,False,dict(error=why))
    for i,h in enumerate(grammars):
        stage=next(x for x in stages if x['grammar_sha256']==h);raw=stage['prepared']['generation_grammar']['grammar'].encode('utf-8')
        assert len(raw)==stage['grammar_bytes'] and sha(raw)==h
        fragment('grammar/'+str(i),'grammar_record',identity('grammar/'+str(i))+bytes.fromhex(h)+span(raw),True,
            dict(id='grammar/'+str(i),grammar_bytes=len(raw),grammar_sha256=h,full_pack_error='fragment_only'))
    for i,x in enumerate(stages):
        raw=identity(x['id'])+bytes.fromhex(x['request_sha256'])+bytes.fromhex(x['payload_sha256'])+u32(grammars.index(x['grammar_sha256']))
        fragment('stage/'+str(i),'stage_record',raw,True,dict(id=x['id'],ordinal=i,grammar_index=grammars.index(x['grammar_sha256']),full_pack_error='fragment_only'))
    dimensions=['project_JSON_parse','Unicode_scalar_JSON','complete_v3_semantic_validation','generation_grammar_membership','native_membership','JSON_syntax']
    for ordinal in (0,76,78,83):
        x=corpus[ordinal];expected=x['expected'];raw=bytes.fromhex(x['raw_hex'])
        kind=0 if expected['native_byte_eligible'] else (2 if expected['harness_disposition']=='harness_raw_nul_rejection' else 1)
        record=(identity(x['id'])+u32(ordinal)+u32(next(i for i,z in enumerate(stages) if z['id']==x['stage_id']))+u32(strata.index(x['stratum']))+
            bytes.fromhex(x['sha256'])+span(raw)+b''.join(u32(tri(expected[k])) for k in dimensions)+u32(int(expected['native_byte_eligible']))+u32(kind)+u32(x['prospective_token_cap']))
        fragment('case/'+str(ordinal),'case_record',record,True,dict(id=x['id'],ordinal=ordinal,raw_sha256=x['sha256'],raw_bytes=len(raw),
            dimensions={k:expected[k] for k in dimensions},native_byte_eligible=expected['native_byte_eligible'],harness_kind=kind,token_cap=x['prospective_token_cap'],full_pack_error='fragment_only'))
        fragment('case/'+str(ordinal)+'/truncated','case_record',record[:-1],False,dict(error='truncated_u32'))
    for name,raw,why in [('empty',u32(0),'empty_ID'),('nonASCII',span(b'\xff'),'ID_ASCII_grammar'),('overlong',span(b'x'*129),'ID_cap'),
        ('truncated',u32(10)+b'abc','truncated'),('unsafe_backslash',span(b'bad\\ID'),'ID_grammar')]:
        fragment('ID/'+name,'ID',raw,False,dict(error=why))

    def make_row(ordinal,kind):
        x=corpus[ordinal];b=bytes.fromhex(x['raw_hex']);r=copy.deepcopy(s['wire_size']['fixed_case_sizing_envelope'])
        r.update(row_sequence=16+2*ordinal,elapsed_ms=1000,wire_semantics_sha256=fp)
        state=r['native_state']
        for k,v in s['framing']['native_state_fields'].items():
            if v=='strict bool':state[k]=False
            elif isinstance(v,dict):state[k]=0 if v['strict_int_range'][0]>=0 else -1
        state.update(coverage_state='not_computed',last_attempt=None,last_return=None,stratum_computed=[0]*6,stratum_results_written=[0]*6,
            cases_computed=ordinal+1,case_results_written=ordinal,current_case_index=ordinal,current_selected_prefix_index=-1,last_EOG_id=-1)
        state['stratum_computed'][strata.index(x['stratum'])]=1
        # This isolated row is framing/geometry evidence, not a fabricated setup trace.
        r['native_call_counters']={name:dict(attempted=0,returned=0) for name in s['API_accounting']['names']}
        e=x['expected'];eligible=e['native_byte_eligible'];qc='ok' if eligible else 'harness_ineligible'
        observed=dict(status='native_member' if eligible else e['harness_disposition'],native_member=True if eligible else None,
            all_input_tokens_admitted=True if eligible else None,first_rejected_token_index=None,first_rejected_byte_start=None,first_rejected_byte_end=None,
            completion_EOG=[dict(id=99,admitted=True)] if eligible else None)
        ledger=dict(token_ids=[7],piece_byte_lengths=[len(b)],piece_hex=[b.hex()]) if eligible else None
        if kind=='empty_piece':ledger=dict(token_ids=[7,8],piece_byte_lengths=[0,len(b)],piece_hex=['',b.hex()])
        if kind=='mixed_EOG':observed.update(status='native_EOG_disagreement',native_member=None,completion_EOG=[dict(id=98,admitted=True),dict(id=99,admitted=False)])
        if kind=='token_rejection':observed.update(status='native_token_rejection',native_member=False,all_input_tokens_admitted=False,
            first_rejected_token_index=0,first_rejected_byte_start=0,first_rejected_byte_end=len(b),completion_EOG=None)
        r['body']=dict(case_ordinal=ordinal,case_id=x['id'],stage_instance_id=x['stage_id'],grammar_sha256=x['grammar_sha256'],raw_sha256=x['sha256'],raw_bytes=len(b),
            authored_expected=dict(native_member=e['native_membership'],generation_member=e['generation_grammar_membership'],semantic_eligible=e['complete_v3_semantic_validation'],coverage_population=x['coverage_population']),
            QC=dict(status=qc,reason=None if eligible else e['harness_disposition']),observation=observed,ledger=ledger,
            compact_analysis=dict(counts={k:0 for k in s['coverage']['classes']} if eligible else None,matrix=[[0]*3 for _ in range(4)] if eligible else None,
                zero_piece_count=(1 if kind=='empty_piece' else 0) if eligible else None),
            matches_authored_native_expectation=None if observed['native_member'] is None else observed['native_member']==e['native_membership'])
        return r
    def row(name,value,valid,scope='row_framing_only',raw=None):
        raw=canonical(value)+b'\n' if raw is None else raw
        rows.append(dict(id=name,raw_hex=raw.hex(),bytes=len(raw),sha256=sha(raw),framing_expected=valid,scope=scope,
            full_profile_valid=False,source_schedule_checked=False,actual_native_tokenizer_observation=False))
    base=make_row(0,'whole_piece')
    for name,o,k in [('case/one_whole_piece',0,'whole_piece'),('case/empty_piece_preserved',0,'empty_piece'),
        ('case/mixed_EOG_geometry_preserved',0,'mixed_EOG'),('case/token_rejection_geometry_preserved',0,'token_rejection'),('case/harness_null_ledger',78,'harness')]:
        row(name,make_row(o,k),True,'row_framing_and_authored_geometry_only')
    raw=canonical(base)+b'\n'
    for name,bad in [('missing_LF',raw[:-1]),('CRLF',raw[:-1]+b'\r\n'),('BOM',b'\xef\xbb\xbf'+raw),
        ('duplicate_name',raw[:-2]+b',"row_sequence":16}\n'),('nonfinite',raw.replace(b'"elapsed_ms":1000',b'"elapsed_ms":NaN',1)),
        ('invalid_UTF8',raw.replace(b'unicode_case_result',b'unicode_\xffcase_result',1))]:row('invalid/'+name,None,False,raw=bad)
    bad=copy.deepcopy(base);bad['row_sequence']=True;row('invalid/bool_sequence',bad,False,'closed_root_schema')
    bad=copy.deepcopy(base);bad['verified']=True;row('invalid/ready_flag',bad,False,'closed_root_schema')
    bad=copy.deepcopy(base);bad['native_state']['last_attempt']='null';row('invalid/string_null_API_tag',bad,False,'closed_native_state_schema')
    failure=copy.deepcopy(base);failure.update(event='failure',row_sequence=191)
    failure['body']=dict(primary_failure_id='f'*64,error_class='BridgeError',reason_code='synthetic_failure',diagnostic_file='failure.json',profile_qualification='not_established')
    assert len(canonical(failure))+1<=8192;row('footer/failure_small',failure,True,'footer_framing_only')
    large=copy.deepcopy(s['wire_size']['fixed_case_sizing_envelope']);large['wire_semantics_sha256']=fp
    N=4128;B=1024;large['body']['ledger']=dict(token_ids=[262143]*N,piece_byte_lengths=[0]*(N-1)+[B],piece_hex=['']*(N-1)+['61'*B])
    largest=canonical(large)+b'\n';assert len(largest)<=60864
    row('sizing/maximum_arrays_preserving_zeros',None,True,'mathematical_size_only_NOT_source_bound_case',raw=largest)
    value=dict(schema_version=1,status='LITERAL_FRAMING_DESIGN_FIXTURES_BEFORE_ANY_PARSER_OR_PACK_IMPLEMENTATION',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        contract=pin(CONTRACT),semantic_sha256=fp,author=pin(Path(__file__)),pack_fragments=pack,JSONL_rows=rows,
        grammar_stage_corpus_basis='Only exact NEW frozen source assets; four selected case fragments are predeclared by ordinal0,76,78,83 to exercise ternary/harness framing, not token outcomes.',
        component_scope='Fragment/component framing expectations only. There is intentionally NO complete84casepack, executableasset, parser/adapter or fullstage/native proof. Every full_profile_valid/complete_profile_pack flag isfalse.',
        synthetic_token_context=dict(vocabulary_size=100,EOG_ids=[99],ordinary_token_labels=[7,8],observed=False,
            note='Mixed-EOG example uses synthetic IDs98/99; no actual vocab/tool is accessed. Isolated row native snapshots are datatype examples, not a fabricated successful setup history.'),
        sizing=dict(fixed_case_overhead=6408,maximum_array_example_bytes=len(largest),footer_failure_example_bytes=len(canonical(failure))+1,
            all_examples_within_respective_declared_caps=True),
        activity=dict(target_native_SDK_tokenizer_compiler_calls=0,CPU_GGUF_oldpack_reads=0,complete_profile_packs_written=0,
            bridge_pack_parser_parent_runtime_implementations=0),execution_authorized=False)
    write(OUT,value)
    write(FREEZE,dict(schema_version=1,status='FRAMING_FIXTURES_FROZEN_FOR_INDEPENDENT_REVIEW_BEFORE_IMPLEMENTATION',fixtures=pin(OUT),contract=pin(CONTRACT),author=pin(Path(__file__)),
        pack_fragments=len(pack),JSONL_rows=len(rows),complete_profile_packs=0,implementation_authorized=False,execution_authorized=False))
    print(json.dumps(dict(fixtures=pin(OUT),freeze=pin(FREEZE),fragments=len(pack),rows=len(rows),largest=len(largest))))
if __name__=='__main__':main()
