"""Inspect only the pinned two-branch fixture delta; no observation validator."""
from datetime import datetime,timezone
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v2.json'
NOTE=HERE/'UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v2.md'

def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(name):
    p=HERE/name;raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=sha(raw))
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def equal(a,b):assert canon(a)==canon(b)
def rows(base):
    raw=bytes.fromhex(base['raw_hex']);assert len(raw)==base['bytes'] and sha(raw)==base['sha256'] and raw.endswith(b'\n')
    return [json.loads(line) for line in raw[:-1].split(b'\n')]
def counters(row):return {name:r['returned'] for name,r in row['native_call_counters'].items()}

def main():
    assert not OUT.exists() and not NOTE.exists()
    expected={
        'UNICODE-OBSERVATIONS-TRACE-FIXTURES-v1.json':'113bdf35742cf0be7eeae760dba966220ed0941d61de6254c89d3c7371b86ef1',
        'UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v1.json':'a22e3d7010978f25d16a9c549134a6866336617b5d99c83721cca19bac164804',
        'UNICODE-OBSERVATIONS-TRACE-FIXTURES-v2.json':'cecd6aad28b91a526541ffc1694e5fa9e7c91749f8b920453316314319bf065b',
        'UNICODE-OBSERVATIONS-TRACE-FREEZE-v2.json':'d2c9ade61f3c619bb6d66bc92ba560ea3a5d8e297fcf06350dff4df62976c145',
        'UNICODE-OBSERVATIONS-ROOT-SUPPLEMENTAL-TRACE-SCOPE-v1.json':'013fb851f2da521e04659d32688fd46b88a8649d4c156efdcf4f6f2fa7796a51',
        'author_unicode_observation_trace_supplement_v2.py':'0913182a0344ad40ad5d0c90d9050b80406506a64906d87622a2c4f69a1c6eca',
        'UNICODE-OBSERVATIONS-TRACE-ENCODING-PROOF-v2.json':'8625e590c41e39c3ff5f2192bb35b0ac8fb4f436ee3625f87ba45ea247314d8f',
    }
    pins={name:pin(name) for name in expected}
    assert all(pins[name]['sha256']==value for name,value in expected.items())
    old=read('UNICODE-OBSERVATIONS-TRACE-FIXTURES-v1.json');new=read('UNICODE-OBSERVATIONS-TRACE-FIXTURES-v2.json')
    equal(new['base_traces'][:4],old['base_traces']);equal(new['scenarios'],old['scenarios']);equal(new['callback_cases'],old['callback_cases'])
    equal(new['sources'],old['sources']);equal(new['in_memory_pack'],old['in_memory_pack'])
    assert len(new['base_traces'])==6 and len(new['scenarios'])==36 and len(new['callback_cases'])==11
    positive,conflict=rows(old['base_traces'][0]),rows(old['base_traces'][2])
    mixed_base,nonpop_base=new['base_traces'][4:];mixed,nonpop=rows(mixed_base),rows(nonpop_base)
    assert len(mixed)==len(nonpop)==185
    for i,(actual,prior) in enumerate(zip(mixed,conflict)):
        if i!=24:equal(actual,prior)
    mb=mixed[24]['body'];old_body=conflict[24]['body'];expected_body=copy.deepcopy(old_body)
    expected_body['observation'].update(status='native_EOG_disagreement',native_member=None,completion_EOG=[{'id':1022,'admitted':True},{'id':1023,'admitted':False}])
    expected_body['matches_authored_native_expectation']=None;equal(mb,expected_body)
    equal({k:v for k,v in mixed[24].items() if k!='body'},{k:v for k,v in conflict[24].items() if k!='body'})
    assert mixed[24]['native_state']['last_apply_logit_kind']==1
    equal(mixed_base['authored_geometry_summary'],old['base_traces'][2]['authored_geometry_summary'])
    equal(mixed_base['authored_final_counters'],old['base_traces'][2]['authored_final_counters'])
    assert mixed_base['failure_marker_hex']==old['base_traces'][2]['failure_marker_hex']
    mp=mixed_base['expected_projection'];assert mp['known_membership_outcomes']==77 and mp['validated_native_geometry_rows']==78 and mp['all_expected_membership_outcomes_match'] is None
    assert mp['classification']=='complete_negative_consistent' and mp['case_collection_complete'] is True
    # The existing literal rejection reference supplies the independent fixed N/r/span formula.
    reference=new['supplemental_branch_references'];assert len(reference)==1
    ref=reference[0];assert (ref['case_ordinal'],ref['before_row'],ref['result_row'])==(68,151,152)
    original=positive[152]['body'];o=original['observation'];assert o['status']=='native_token_rejection'
    n=len(original['ledger']['token_ids']);r=o['first_rejected_token_index'];lengths=original['ledger']['piece_byte_lengths']
    assert (n,r,sum(lengths[:r]),sum(lengths[:r+1]))==(227,226,225,226)
    names=list(positive[151]['native_call_counters']);original_delta={name:counters(positive[152])[name]-counters(positive[151])[name] for name in names}
    expected_delta=dict.fromkeys(names,0);expected_delta.update(llama_tokenize=2,llama_token_to_piece=227,llama_sampler_apply=227,llama_sampler_accept=226,llama_sampler_init_grammar=1,llama_sampler_free=1)
    equal(original_delta,expected_delta);equal(ref['expected']['native_call_delta_each_attempted_returned'],expected_delta)
    difference={name:(1 if name=='llama_tokenize' else 0)-value for name,value in expected_delta.items()}
    assert sum(difference.values())==-683
    for i,row in enumerate(nonpop[:184]):
        prior=positive[i]
        assert row['event']==prior['event'] and row['row_sequence']==i and row['elapsed_ms']==prior['elapsed_ms']
        expected_counts={name:value+(difference[name] if i>=152 else 0) for name,value in counters(prior).items()}
        equal(counters(row),expected_counts)
        for counts_for_name in row['native_call_counters'].values():assert counts_for_name['attempted']==counts_for_name['returned']
        assert row['native_state']['total_attempted']==row['native_state']['total_returned']==sum(expected_counts.values())
        assert row['native_state']['token_work_reserved']==prior['native_state']['token_work_reserved']-(227 if i>=152 else 0)
        for field in ('sampler_nonnull_returns','sampler_free_returned_nonnull'):
            assert row['native_state'][field]==prior['native_state'][field]-(1 if i>=152 else 0)
        if i!=152 and i!=183:equal(row['body'],prior['body'])
    bad=nonpop[152]['body'];assert bad['case_ordinal']==68 and bad['case_id']=='negative/unknown_quote'
    assert bad['authored_expected']['coverage_population'] is False and bad['authored_expected']['native_member'] is False
    assert bad['QC']=={'status':'unknown','reason':'tokenize_size_invalid'} and bad['ledger'] is None
    assert bad['observation']['status']=='not_attempted_QC_unknown' and all(v is None for k,v in bad['observation'].items() if k!='status')
    assert bad['matches_authored_native_expectation'] is None
    assert nonpop[152]['native_state']['last_tokenize_return']==0 and nonpop[152]['native_state']['last_return']=='llama_tokenize'
    assert nonpop[152]['native_state']['last_apply_logit_kind']==positive[150]['native_state']['last_apply_logit_kind']
    summary=copy.deepcopy(old['base_traces'][0]['authored_geometry_summary']);summary['all_case_QC_complete']=False
    equal(nonpop_base['authored_geometry_summary'],summary)
    assert summary['coverage_complete'] is True and summary['required_available'] is True and summary['unknown_population_ordinals']==[]
    coverage=copy.deepcopy(positive[183]['body']);coverage['all_case_QC_complete']=False
    equal(nonpop[183]['body'],coverage)
    np=nonpop_base['expected_projection'];assert (np['validated_native_geometry_rows'],np['known_membership_outcomes'])==(77,77)
    assert np['all_expected_membership_outcomes_match'] is None and np['case_collection_complete'] is True and np['normal_schedule_complete'] is False
    last=nonpop[-1];assert last['event']=='failure' and last['body']['reason_code']=='document_QC_unknown'
    expected_counts=counters(nonpop[183]);expected_counts['llama_model_free']+=1;expected_counts['llama_backend_free']+=1
    equal(counters(last),expected_counts)
    s=last['native_state'];assert s['model_free_return_observed'] is s['backend_free_return_observed'] is True
    assert s['model_owned'] is s['backend_owned'] is s['model_release_unknown'] is s['backend_release_unknown'] is False
    assert s['sampler_release_unknown']==s['samplers_owned']==0 and s['sampler_free_returned_nonnull']==77
    for base,rs in ((mixed_base,mixed),(nonpop_base,nonpop)):
        raw=bytes.fromhex(base['raw_hex']);assert raw==b''.join(canon(row)+b'\n' for row in rs)
        marker=json.loads(bytes.fromhex(base['failure_marker_hex']));last=rs[-1]
        identity=dict(pid=4242,error_class=last['body']['error_class'],reason_code=last['body']['reason_code'],elapsed_ms=last['elapsed_ms'],row_sequence_reserved=last['row_sequence'])
        assert sha(canon(identity))==last['body']['primary_failure_id']==marker['primary_failure_id']
        assert marker['elapsed_ms']==last['elapsed_ms'] and marker['row_sequence_reserved']==last['row_sequence']
        assert marker['failure_row_publication']['sha256']==sha(canon(last)+b'\n')
        assert all(base['expected_projection'][k] is False for k in ('profile_qualified','originals_authenticated','runtime_authorized'))
    encoding=read('UNICODE-OBSERVATIONS-TRACE-ENCODING-PROOF-v2.json');assert encoding['status']=='passed'
    assert all(pin(name)==value for name,value in pins.items())
    note='''# Observation trace successor peer

The narrow v2 literal preparation is clear. Its first four bases, 36 overlays and 11 callback vectors are exact v1 values, so the prior whole-history peer inspection remains applicable. One added mixed-EOG history changes only case4's observation/match fields: true/false EOG, membership null, valid geometry78 and known-membership77. Counters, later source state, population summary and failure marker remain unchanged from the prior conflict history.

The added nonpopulation-QC-unknown history changes case68 to one known tokenize0 return, no piece/sampler work, and null measurements. Independent arithmetic confirms its -683 aggregate call delta, unchanged other case bodies, source write lag, retained known population summary/selectors and all_case_QC_complete false. Its model/backend cleanup returns and document_QC_unknown failure/marker links are consistent. The existing rejection case68 is referenced with N227/r226/span[225,226), not duplicated.

This is finite pinned fixture/source inspection only, not an observation validator, actual token/vocabulary result, original authentication, runtime authorization or profile qualification. No SDK/native/old-run/payload or runtime pack file operation occurred. A separate root source-only implementation decision remains required.
'''
    with NOTE.open('x',encoding='utf-8',newline='\n') as f:f.write(note)
    result=dict(schema_version=1,status='CLEAR_NARROW_LITERAL_TRACE_PREPARATION_ONLY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),reviewer='/root/native_039_acceptance_audit',inputs=pins,review_script=pin(Path(__file__).name),note=pin(NOTE.name),
        unchanged_prior=dict(base_traces=4,scenarios=36,callback_families=11),added_coherent_branches=2,
        mixed_EOG=dict(native_geometry=78,known_membership=77,matches=None,counter_changes=0,population_unchanged=True),
        nonpopulation_QC_unknown=dict(ordinal=68,native_geometry=77,known_membership=77,known_population_summary=True,all_case_QC_complete=False,aggregate_call_delta=-683,cleanup_known=True),
        existing_rejection_reference=dict(ordinal=68,N=227,r=226,span=[225,226],apply=227,accept=226),
        prior_gap_resolved=True,no_remaining_material_finding_in_bounded_delta=True,
        observation_validator_implemented=False,SDK_native_payload_operations=0,old_run_operations=0,profile_qualified=False,originals_authenticated=False,runtime_authorized=False)
    with OUT.open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(peer=pin(OUT.name),note=pin(NOTE.name),base_traces=6)))

if __name__=='__main__':main()
