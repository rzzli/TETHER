"""Author a fixed corpus from accepted pure v3 renderers; no runtime adapter.

Expected outcomes are declared below, independently of tokenization/native
observation. This writes JSON fixture/grammar/provenance artifacts, never a
native pack, bridge, model request or execution protocol.
"""
import copy
import ctypes  # stdlib declarations before the native-call denial hook.
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ORACLE=HERE.parent/'recovery-step9-utf8-oracle-20261029/UTF8-ORACLE-CORPUS-v2.json'
ORACLE_SHA='65428d32cc06c58836d1d541bde0e893db13cef9e5ae756e26d6e353908b302d'
CONTRACT=HERE/'UNICODE-CONTROL-CONTRACT-v2.json'
PROFILE=HERE/'UNICODE-CONTROL-PROFILE-v2.md'
CORPUS=HERE/'UNICODE-CONTROL-CORPUS-v1.json'
GRAMMARS=HERE/'UNICODE-CONTROL-STAGES-v1.json'
PROVENANCE=HERE/'UNICODE-CONTROL-PROVENANCE-v1.json'
PURE=HERE/'UNICODE-CONTROL-GENERATION-CHECKS-v1.json'
START=time.monotonic();DEADLINE=START+60
DENIED=[]
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        DENIED.append(event);raise AssertionError('No runtime/native/process/network in source-only fixture generation')
    if event=='open' and args and isinstance(args[0],(str,bytes)):
        value=str(args[0]).replace('/','\\').lower()
        if value.endswith(('.gguf','.dll','.pyd','.pack')) or 'recognition-verifier-captured-pack' in value:
            DENIED.append('protected_payload_open');raise AssertionError('No CPU/model/oldpack input')
sys.addaudithook(guard)
from asof.serde import ContractError,canonical,encode,fingerprint,parse_json
from asof import serde
from asof.study import interpretation_generation as generation,interpretation_grammar as grammar
from asof.study import interpretation_interface,diagnostic,diagnostic_codec,fixed_evidence,diagnostic_resources,native_interpretation

def tick():
    if time.monotonic()>=DEADLINE:raise TimeoutError('Source-only fixture authoring60s deadline')
def pin(path):
    tick();path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def dump(path,value):
    tick()
    with path.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,ensure_ascii=True,indent=2,allow_nan=False);out.write('\n')
def wire(doc,ascii_only=False):
    return json.dumps(doc,sort_keys=True,ensure_ascii=ascii_only,separators=(',',':'),allow_nan=False).replace('<','\\u003c').encode('utf-8')
def caution(text):
    return dict(abstention_reason=None,answer_status='answered',claims=[dict(kind='caution',limitations=['Synthetic encoding control; not scientific interpretation.'],quote_refs=['Q0'],text=text)],unresolved=[])
def abstain(reason,unresolved=None):
    return dict(abstention_reason=reason,answer_status='abstained',claims=[],unresolved=[] if unresolved is None else unresolved)
def scalars_only(value):
    if isinstance(value,str):return all(not 0xD800<=ord(c)<=0xDFFF for c in value)
    if isinstance(value,dict):return all(scalars_only(k) and scalars_only(v) for k,v in value.items())
    if isinstance(value,list):return all(scalars_only(v) for v in value)
    return True
def byte_stats(raw):
    result=dict(raw_nonASCII_bytes=sum(b>=128 for b in raw),ASCII_only=all(b<128 for b in raw),
        Unicode_escape_spellings=raw.count(b'\\u'),short_JSON_escape_spellings=sum(raw.count(v) for v in (b'\\n',b'\\r',b'\\t',b'\\b',b'\\f')))
    try:
        text=raw.decode('utf-8','strict');counts={str(w):0 for w in range(1,5)}
        for char in text:counts[str(len(char.encode('utf-8')))]+=1
        result.update(UTF8_valid=True,raw_scalar_width_counts=counts,raw_scalar_width_counts_null_reason=None)
    except UnicodeError:
        result.update(UTF8_valid=False,raw_scalar_width_counts=None,raw_scalar_width_counts_null_reason='Invalid UTF8 has no complete strict-scalar segmentation.')
    return result

def main():
    tick();assert metadata.version('asof-target-agents')=='0.3.11'
    assert generation.INTERFACE=='source-quote-interpretation-v3-gbnf' and grammar.GENERATOR=='strict-interpretation-gbnf-v1'
    assert not any(p.exists() for p in (CORPUS,GRAMMARS,PROVENANCE,PURE))
    assert pin(ORACLE)['sha256']==ORACLE_SHA
    scalar_pairs=json.loads(ORACLE.read_text(encoding='utf-8'))['expected_scalar_encoding_pairs'];assert len(scalar_pairs)==14
    for pair in scalar_pairs:assert chr(pair['scalar']).encode('utf-8').hex()==pair['hex']
    contract=json.loads(CONTRACT.read_text(encoding='utf-8'));assert contract['corpus']['cases']==84
    stages=[];prepared=[];requests=[]
    for stage in contract['language']['stage_instances']:
        tick();request=diagnostic.load_synthetic_request(stage['fixture'])
        p=generation.prepare_payload(request,stage['arm'],stage['stage_index'],stage['feedback'])
        assert request['question']['question_id']==stage['question_id'] and p['semantic_data']['stage']==stage['stage_name']
        assert p['execution_authorized'] is False and p['native_conformance']=='unverified'
        stages.append(dict(stage,request=encode(request),prepared=encode(p),request_sha256=p['request_sha256'],payload_sha256=p['payload_sha256'],
            grammar_sha256=p['generation_grammar']['grammar_sha256'],grammar_bytes=p['generation_grammar']['grammar_bytes']))
        prepared.append(p);requests.append(request)
    cases=[];checks=[];errors=[]
    def add(identity,stratum,stage_index,construction,doc=None,raw=None,ascii_only=False,project_JSON=True,scalar_JSON=True,
            v3_semantic=True,generation_member=True,native_eligible=True,harness_reason=None,JSON_syntax=True,
            counterpart=None,non_scalar=None):
        tick();raw=wire(doc,ascii_only) if raw is None else raw
        assert type(raw) is bytes and 0<len(raw)<=1024 and identity not in {c['id'] for c in cases}
        stats=byte_stats(raw)
        try:parsed=parse_json(raw);actual_parse=True
        except (ContractError,UnicodeError,ValueError):parsed=None;actual_parse=False
        actual_scalar=scalars_only(parsed) if actual_parse else None
        try:
            validated=generation.validate_output(requests[stage_index],prepared[stage_index]['payload'],raw);actual_semantic=True
            assert validated['features']=={} and validated['clinical_probability'] is None
        except (ContractError,UnicodeError,ValueError):actual_semantic=False
        if actual_parse is not project_JSON or actual_scalar is not scalar_JSON or actual_semantic is not v3_semantic:
            errors.append(dict(id=identity,actual_project_JSON=actual_parse,actual_scalar_JSON=actual_scalar,actual_v3_semantic=actual_semantic,
                expected_project_JSON=project_JSON,expected_scalar_JSON=scalar_JSON,expected_v3_semantic=v3_semantic))
        value=encode(parsed) if actual_parse and actual_scalar else None
        value_reason=None if value is not None else ('No project-parsed JSON value.' if not actual_parse else 'Parsed string contains an unpaired UTF16 surrogate; scalar-domain JSON value withheld explicitly.')
        decoded_sha=fingerprint(value) if value is not None else None
        expected=dict(project_JSON_parse=project_JSON,JSON_syntax=JSON_syntax,JSON_syntax_null_reason=None if JSON_syntax is not None else 'Invalid UTF8 has no Unicode JSON syntax domain.',
            Unicode_scalar_JSON=scalar_JSON,Unicode_scalar_JSON_null_reason=None if scalar_JSON is not None else 'Project JSON parse fails before scalar-string validation.',
            JSON_value=value,JSON_value_null_reason=value_reason,JSON_value_sha256=decoded_sha,
            complete_v3_semantic_validation=v3_semantic,generation_grammar_membership=generation_member,
            native_byte_eligible=native_eligible,native_membership=generation_member if native_eligible else None,
            native_membership_null_reason=None if native_eligible else harness_reason,harness_disposition=harness_reason,
            non_scalar_string=non_scalar)
        population=native_eligible and generation_member and v3_semantic
        cases.append(dict(id=identity,ordinal=len(cases),stratum=stratum,stage_id=stages[stage_index]['id'],grammar_sha256=stages[stage_index]['grammar_sha256'],
            construction=construction,raw_hex=raw.hex(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),wire_statistics=stats,
            expected=expected,ASCII_counterpart_of=counterpart,coverage_population=population,
            coverage_exclusion_reason=None if population else ('Declared harness ineligibility.' if not native_eligible else 'Predeclared grammar/semantic control outside the positive coverage population.'),
            measured_piece_ledger=None,measured_piece_ledger_null_reason='Source-only fixture; no tokenizer or native call performed.',
            prospective_token_cap=min(65536,4*len(raw)+32),prospective_case_row_bound=12*min(65536,4*len(raw)+32)+3*len(raw)+8192+64))
        checks.append(dict(id=identity,exact_rawbytes_v3_validator_called=True,project_JSON_matches=actual_parse is project_JSON,
            scalar_domain_matches=actual_scalar is scalar_JSON,v3_semantic_matches=actual_semantic is v3_semantic,
            expected_generation_membership_source_review_only=True))
    for index,p in enumerate(prepared):
        q=p['semantic_data']['quote_catalog'][0];text=diagnostic_codec.pointer(p['semantic_data']['original_request'],q['request_pointer'])
        doc=dict(abstention_reason=None,answer_status='answered',claims=[dict(kind='source_report',limitations=[],quote_refs=[q['quote_id']],text=text)],unresolved=[])
        add('baseline/'+stages[index]['id'],'stage_source_report',index,'One exact originalQ0 source string under the actual stage grammar.',doc)
    for index,pair in enumerate(scalar_pairs):
        char=chr(pair['scalar']);name=pair['id']
        docs=[caution('A'+char+'B'),abstain('X'+char*8+'Y'),abstain('Synthetic encoding control; no scientific answer.',['e\u0301A'+char+'\U0001f600Z'])]
        for field,doc in enumerate(docs):
            add('scalar/'+name+'/field'+str(field),'scalar_field_grid',(3*index+field)%4,
                dict(scalar=pair,field_index=field,fixed_context=contract['corpus']['grid']['contexts'][field]),doc)
    for index,pair in enumerate(scalar_pairs):
        add('ASCII_escape/'+pair['id'],'ASCII_escape_counterparts',(3*index)%4,'ASCII JSONescape spelling of exactly the rawfield0 decoded full response.',
            caution('A'+chr(pair['scalar'])+'B'),ascii_only=True,counterpart='scalar/'+pair['id']+'/field0')
    ordered=sorted(p['scalar'] for p in scalar_pairs)
    mixed=[('all_scalars_ascending',caution('A'+''.join(chr(c) for c in ordered)+'Z')),
        ('all_scalars_descending',caution('A'+''.join(chr(c) for c in reversed(ordered))+'Z')),
        ('NFC',caution('\u00e9')),('NFD',caution('e\u0301')),
        ('quote_backslash',caution('A " quoted \\ ASCII Z')),('escaped_NUL',caution('A\0B')),
        ('escaped_less_than',caution('left<right')),('short_newline_escape',abstain('A\nB'))]
    for index,(name,doc) in enumerate(mixed):add('context/'+name,'mixed_normalization_escape',index%4,'Fixed independent mixed/representation context; no token observations.',doc)
    doc=caution('Synthetic control.');doc['claims'][0]['quote_refs']=['Q999']
    add('negative/unknown_quote','grammar_semantic_JSON_controls',0,'Unknown quoted reference.',doc,v3_semantic=False,generation_member=False)
    add('negative/blank_text','grammar_semantic_JSON_controls',1,'Blank generic string.',caution(''),v3_semantic=False,generation_member=False)
    doc=caution('Not the exact source literal.');doc['claims'][0]['kind']='source_report';doc['claims'][0]['limitations']=[]
    add('negative/source_report_literal','grammar_semantic_JSON_controls',2,'Source report text differs from its exact quote.',doc,v3_semantic=False,generation_member=False)
    doc=caution('Duplicate text.');doc['claims'].append(copy.deepcopy(doc['claims'][0]))
    add('negative/duplicate_claim_text','grammar_semantic_JSON_controls',3,'Global uniqueness is post-validation only.',doc,v3_semantic=False,generation_member=True)
    doc=caution('left<right');raw=wire(doc).replace(b'\\u003c',b'<')
    add('negative/raw_less_than','grammar_semantic_JSON_controls',0,'Same decodedvalue but rawless-than violates generation domain.',raw=raw,v3_semantic=True,generation_member=False)
    doc=caution('Order control.');raw=json.dumps(dict(reversed(list(doc.items()))),ensure_ascii=False,separators=(',',':')).encode('utf-8')
    add('negative/key_order','grammar_semantic_JSON_controls',1,'Valid JSON, wrong fullresponse generation key order.',raw=raw,v3_semantic=True,generation_member=False)
    raw=wire(caution('Whitespace control.')).replace(b',',b', ',1)
    add('negative/outside_whitespace','grammar_semantic_JSON_controls',2,'Valid JSON, extra outside-string whitespace.',raw=raw,v3_semantic=True,generation_member=False)
    raw=wire(caution('A\nB')).replace(b'A\\nB',b'A\nB')
    add('negative/raw_newline','grammar_semantic_JSON_controls',3,'Raw newline inside a JSON string.',raw=raw,project_JSON=False,scalar_JSON=None,v3_semantic=False,generation_member=False,JSON_syntax=False)
    raw=wire(caution('AXXB')).replace(b'AXXB',b'A\\ud800B')
    add('negative/lone_surrogate_escape','grammar_semantic_JSON_controls',0,'ASCII escape parses in Python but is outside Unicode scalar domain.',raw=raw,scalar_JSON=False,
        v3_semantic=False,generation_member=False,non_scalar=dict(pointer='/claims/0/text',codepoints=[65,55296,66]))
    raw=wire(caution('Duplicate key control.'));raw=raw[:-1]+b',"answer_status":"answered"}'
    add('negative/duplicate_JSON_name','grammar_semantic_JSON_controls',1,'JSONsyntax accepts repeatedname; exact project parser rejects it.',raw=raw,project_JSON=False,
        scalar_JSON=None,v3_semantic=False,generation_member=False,JSON_syntax=True)
    guards=[('raw_NUL',b'\0',True,'harness_raw_nul_rejection'),('bad_continuation',bytes.fromhex('c241'),False,'harness_utf8_rejection'),
        ('overlong',bytes.fromhex('c0af'),False,'harness_utf8_rejection'),('encoded_surrogate',bytes.fromhex('eda080'),False,'harness_utf8_rejection'),
        ('out_of_range',bytes.fromhex('f4908080'),False,'harness_utf8_rejection'),('premature_EOF',bytes.fromhex('e282'),False,'harness_utf8_rejection')]
    for index,(name,insert,utf8,reason) in enumerate(guards):
        raw=wire(caution('AXXB'))
        raw=raw[:raw.index(b'XX')]+insert if name=='premature_EOF' else raw.replace(b'XX',insert)
        add('guard/'+name,'byte_harness_guards',index%4,'Fixed byte-harness disposition, not native nonmembership.',raw=raw,project_JSON=False,scalar_JSON=None,
            v3_semantic=False,generation_member=False,native_eligible=False,harness_reason=reason,JSON_syntax=False if utf8 else None)
        assert cases[-1]['wire_statistics']['UTF8_valid'] is utf8
    assert len(cases)==84
    by_id={c['id']:c for c in cases}
    for c in cases:
        if c['ASCII_counterpart_of']:
            base=by_id[c['ASCII_counterpart_of']]
            assert c['expected']['JSON_value_sha256']==base['expected']['JSON_value_sha256'] and c['stage_id']==base['stage_id']
            assert c['wire_statistics']['ASCII_only'] and c['wire_statistics']['raw_nonASCII_bytes']==0 and base['wire_statistics']['raw_nonASCII_bytes']>0
        assert c['prospective_case_row_bound']<=65536
    source_modules=[generation,grammar,interpretation_interface,diagnostic,diagnostic_codec,fixed_evidence,diagnostic_resources,serde,native_interpretation]
    source_pins=[]
    for module in source_modules:
        installed=Path(module.__file__);relative=installed.parts[installed.parts.index('asof'):]
        workspace=ROOT/'src'/Path(*relative)
        assert installed.read_text(encoding='utf-8')==workspace.read_text(encoding='utf-8')
        source_pins.append(dict(module=module.__name__,installed=pin(installed),workspace=pin(workspace),universal_newline_source_text_equal=True))
    corpus=dict(schema_version=1,profile_id=contract['profile_id'],status='fixed_source_only_expected_documents_not_native_pack',
        contract=pin(CONTRACT),profile=pin(PROFILE),scalar_basis=pin(ORACLE),scalar_pairs=scalar_pairs,cases=cases,
        observed_token_IDs_used=False,tokenizer_calls=0,native_calls=0,execution_authorized=False,scientific_validation='not_established')
    stage_data=dict(schema_version=1,interface=generation.INTERFACE,generator=grammar.GENERATOR,stages=stages,
        stage_instances=len(stages),unique_grammar_hashes=sorted({s['grammar_sha256'] for s in stages}),
        actual_pure_renderer_used=True,native_conformance='unverified',execution_authorized=False)
    dump(CORPUS,corpus);dump(GRAMMARS,stage_data)
    proof=dict(schema_version=1,status='passed' if not errors else 'failed',helper=pin(Path(__file__)),corpus=pin(CORPUS),stages=pin(GRAMMARS),
        contract=pin(CONTRACT),profile=pin(PROFILE),cases=len(cases),stage_instances=4,unique_grammars=len(stage_data['unique_grammar_hashes']),
        exact_rawbyte_semantic_checks=checks,errors=errors,tokenizer_calls=0,native_compiler_network_calls=0,CPU_GGUF_oldpack_operations=0,
        expected_generation_membership='Authored source-rule expectation; not certified by a native recognizer or semantic validator.',denied_operations=DENIED,
        elapsed_seconds=time.monotonic()-START)
    dump(PURE,proof)
    provenance=dict(schema_version=1,status='source_only_fixture_generation_before_bridge_pack_runtime_code',generator=pin(Path(__file__)),corpus=pin(CORPUS),stages=pin(GRAMMARS),
        pure_checks=pin(PURE),contract=pin(CONTRACT),profile=pin(PROFILE),scalar_basis=pin(ORACLE),source_modules=source_pins,
        packaged_synthetic_assets=[pin(Path(diagnostic.__file__).parent/'resources'/name) for name in
            ('synthetic-context-v1.json','synthetic-orientation-v1.json','diagnostic-templates-v1.json','fixed-evidence-plan-v1.json')],
        runtime_distribution='asof-target-agents==0.3.11',case_order='Fourbaselines,42scalargrid,14ASCIIcounterparts,8contexts,10negativecontrols,6harnessguards.',
        limits_not_increased=True,CPU_GGUF_oldpack_operations=0,tokenizer_native_compiler_network_calls=0,execution_authorized=False)
    dump(PROVENANCE,provenance)
    print(json.dumps(dict(status=proof['status'],corpus=pin(CORPUS),stages=pin(GRAMMARS),checks=pin(PURE),provenance=pin(PROVENANCE),cases=84,
        unique_grammars=proof['unique_grammars'],errors=len(errors))))
    return 0 if not errors else 1

if __name__=='__main__':
    try:raise SystemExit(main())
    except SystemExit:raise
    except BaseException as error:
        failure=HERE/'UNICODE-CONTROL-AUTHORING-FAILURE-v1.json'
        if not failure.exists():dump(failure,dict(status='failed_source_only_authoring',error_class=type(error).__name__,error=str(error)[:2048],
            generator=pin(Path(__file__)),elapsed_seconds=time.monotonic()-START,automatic_retry=False,execution_authorized=False))
        raise
