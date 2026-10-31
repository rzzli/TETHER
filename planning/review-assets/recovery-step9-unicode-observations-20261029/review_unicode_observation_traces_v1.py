"""Finite pinned-fixture inspection; no observation-validator API or native calls."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/'UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v1.json'
NOTE=HERE/'UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v1.md'

def digest(raw):return hashlib.sha256(raw).hexdigest()
def canon(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=digest(raw))
def typed_equal(a,b):
    assert type(a) is type(b)
    if type(a) is dict:
        assert a.keys()==b.keys()
        for k in a:typed_equal(a[k],b[k])
    elif type(a) is list:
        assert len(a)==len(b)
        for x,y in zip(a,b):typed_equal(x,y)
    else:assert a==b

def main():
    assert not OUT.exists() and not NOTE.exists()
    paths={
        'fixtures':HERE/'UNICODE-OBSERVATIONS-TRACE-FIXTURES-v1.json',
        'freeze':HERE/'UNICODE-OBSERVATIONS-TRACE-FREEZE-v1.json',
        'design':HERE/'UNICODE-OBSERVATIONS-DESIGN-CONTRACT-v2.json',
        'context':HERE/'UNICODE-OBSERVATIONS-SYNTHETIC-CONTEXT-v1.json',
        'author':HERE/'author_unicode_observation_traces_v1.py',
        'encoding_proof':HERE/'UNICODE-OBSERVATIONS-TRACE-ENCODING-PROOF-v1.json',
        'corpus':ROOT/'recovery-step9-unicode-control-20261029/UNICODE-CONTROL-CORPUS-v1.json',
        'base_design':ROOT/'recovery-step9-unicode-wire-20261029/UNICODE-WIRE-DESIGN-CONTRACT-v2.json',
        'framing':ROOT/'recovery-step9-unicode-wire-20261029/UNICODE-WIRE-FRAMING-CONTRACT-v1.json',
    }
    pins={k:pin(p) for k,p in paths.items()}
    assert pins['fixtures']['sha256']=='113bdf35742cf0be7eeae760dba966220ed0941d61de6254c89d3c7371b86ef1'
    assert pins['freeze']['sha256']=='64e07cf33268334b13d742fac9860211fdb2faf7a7e996e5d176b1cbf7708a41'
    data={k:json.loads(p.read_text(encoding='utf-8')) for k,p in paths.items() if k!='author'}
    source=data['corpus']['cases'];semantic=data['base_design']['semantic_contract'];context=data['context'];fixture=data['fixtures']
    names=semantic['API_accounting']['names'];classes=semantic['coverage']['classes']
    assert len(source)==84 and len(names)==25 and len(classes)==4
    table={p['id']:bytes.fromhex(p['piece_hex']) for p in context['ordinary_piece_table']}
    assert len(table)==117 and table[0]==b'' and not set(table)&{1022,1023}
    assert list(table.values())==sorted(set(table.values()))
    raw_source=[bytes.fromhex(c['raw_hex']) for c in source]
    for c,raw in zip(source,raw_source):assert len(raw)==c['bytes'] and digest(raw)==c['sha256']
    summaries=[];all_rows={};base_bytes={};mixed=0
    for base in fixture['base_traces']:
        raw=bytes.fromhex(base['raw_hex']);assert len(raw)==base['bytes'] and digest(raw)==base['sha256'] and raw.endswith(b'\n')
        lines=raw[:-1].split(b'\n');rows=[json.loads(line) for line in lines]
        assert len(rows)==base['row_count'] and len(rows) in (185,191)
        all_rows[base['id']]=rows;base_bytes[base['id']]=[line+b'\n' for line in lines]
        assert [r['row_sequence'] for r in rows]==list(range(len(rows)))
        for r,line in zip(rows,lines):
            assert canon(r)==line and set(r)==set(semantic['framing']['common_row_keys'])
            assert r['wire_semantics_sha256']=='75605c03fb5b9bac659538035d8205b34df2ae1781b997a3181a1564676aa6c4'
            assert set(r['native_state'])==set(semantic['framing']['native_state_fields'])
            assert r['native_state']['total_attempted']==sum(c['attempted'] for c in r['native_call_counters'].values())
            assert r['native_state']['total_returned']==sum(c['returned'] for c in r['native_call_counters'].values())
            assert all(c['attempted']==c['returned'] for c in r['native_call_counters'].values())
        for index,entry in enumerate(semantic['event_order']['setup_events']):
            r=rows[index];assert r['event']==entry['event']
            expected={n:1024 if type(v) is str else v for n,v in entry['cumulative_attempted_equals_returned'].items()}
            assert {n:c['returned'] for n,c in r['native_call_counters'].items()}==expected
            fields=semantic['event_order']['setup_body_schemas'][r['event']]['fields'];assert set(r['body'])==set(fields)
            for key,rule in fields.items():
                if type(rule) is dict and 'const' in rule:typed_equal(r['body'][key],rule['const'])
                if type(rule) is dict and 'exact_typed_value' in rule:typed_equal(r['body'][key],rule['exact_typed_value'])
            if 'modules' in r['body']:
                body=r['body'];phase='pre_cpu' if index==1 else 'post_cpu'
                assert body['module_policy_phase']==phase
                expected_modules=[{'name':'recognizer.exe','path':context['expected_self']}]
                expected_modules += [{'name':n,'path':context['expected_runtime']+'\\'+n} for n in ('libomp.dll','ggml-base.dll','ggml.dll','llama.dll')]
                if phase=='post_cpu':expected_modules.append({'name':'ggml-cpu-x64.dll','path':context['expected_runtime']+'\\ggml-cpu-x64.dll'})
                typed_equal(body['modules'],expected_modules)
        current={n:r['returned'] for n,r in rows[14]['native_call_counters'].items()}
        token_work=0;geometries=[];known=geometry_count=harness=0;allmatch=True
        strata=list(dict.fromkeys(c['stratum'] for c in source));assert len(strata)==6
        progress=[0]*6
        for i,c in enumerate(source):
            before,result=rows[15+2*i:17+2*i];assert before['event']=='unicode_before_case' and result['event']=='unicode_case_result'
            assert before['body']['case_ordinal']==i and result['body']['case_ordinal']==i
            for r in (before,result):
                b=r['body'];assert (b['case_id'],b['stage_instance_id'],b['grammar_sha256'],b['raw_sha256'],b['raw_bytes'])==(c['id'],c['stage_id'],c['grammar_sha256'],c['sha256'],c['bytes'])
            assert before['native_state']['cases_computed']==before['native_state']['case_results_written']==i
            typed_equal(before['native_state']['stratum_computed'],progress);typed_equal(before['native_state']['stratum_results_written'],progress)
            assert {n:x['returned'] for n,x in before['native_call_counters'].items()}==current
            b=result['body'];q=b['QC'];o=b['observation'];ledger=b['ledger'];delta={n:0 for n in names}
            expected=c['expected'];typed_equal(b['authored_expected'],dict(native_member=expected['native_membership'],generation_member=expected['generation_grammar_membership'],semantic_eligible=expected['complete_v3_semantic_validation'],coverage_population=c['coverage_population']))
            if not expected['native_byte_eligible']:
                harness+=1;assert ledger is None and q['status']=='harness_ineligible' and o['status']==q['reason']
                assert all(v is None for k,v in o.items() if k!='status') and len(o)==7
                assert b['matches_authored_native_expectation'] is None;geometries.append(None)
            elif q['status']=='unknown':
                assert base['id']=='complete_population_QC_unknown' and i==4 and ledger is None
                delta['llama_tokenize']=1;geometries.append(None);allmatch=None
                assert o['status']=='not_attempted_QC_unknown' and all(v is None for k,v in o.items() if k!='status')
            else:
                geometry_count+=1;assert q=={'status':'ok','reason':None}
                pieces=[bytes.fromhex(h) for h in ledger['piece_hex']];lengths=list(map(len,pieces));N=len(pieces)
                assert ledger['piece_byte_lengths']==lengths and b''.join(pieces)==raw_source[i]
                assert [table[token] for token in ledger['token_ids']]==pieces and N<=c['prospective_token_cap']
                delta['llama_tokenize']=1 if N==1 else 2;delta['llama_token_to_piece']=N+sum(n>1 for n in lengths)
                delta['llama_sampler_init_grammar']=delta['llama_sampler_free']=1;token_work+=N
                if o['status']=='native_token_rejection':
                    cut=o['first_rejected_token_index'];assert type(cut) is int and 0<=cut<N
                    assert o['first_rejected_byte_start']==sum(lengths[:cut]) and o['first_rejected_byte_end']==sum(lengths[:cut+1])
                    assert o['all_input_tokens_admitted'] is False and o['native_member'] is False and o['completion_EOG'] is None
                    delta['llama_sampler_apply']=cut+1;delta['llama_sampler_accept']=cut
                else:
                    assert o['all_input_tokens_admitted'] is True and [e['id'] for e in o['completion_EOG']]==[1022,1023]
                    flags=[e['admitted'] for e in o['completion_EOG']];assert all(type(x) is bool for x in flags)
                    if flags[0]!=flags[1]:mixed+=1;assert o['status']=='native_EOG_disagreement' and o['native_member'] is None
                    else:assert o['native_member'] is flags[0] and o['status']==('native_member' if flags[0] else 'native_eog_rejection')
                    delta['llama_sampler_apply']=N+2;delta['llama_sampler_accept']=N
                if o['native_member'] is not None:known+=1
                match=None if o['native_member'] is None else o['native_member']==expected['native_membership']
                assert b['matches_authored_native_expectation'] is match
                if allmatch is not None:allmatch=allmatch and match if match is not None else None
                # Independent byte-lead interval construction, not the author's scalar loop or analyzer.
                raw_source[i].decode('utf-8','strict');intervals=[];at=0
                while at<len(raw_source[i]):
                    lead=raw_source[i][at];width=1 if lead<128 else 2 if lead<224 else 3 if lead<240 else 4
                    intervals.append((at,at+width,width));at+=width
                counts={k:0 for k in classes};matrix=[[0]*3 for _ in range(4)];boundaries=[];start=0
                for ti,n in enumerate(lengths):
                    end=start+n;pending=next((s for s in intervals if s[0]<end<s[1]),None) if n else None
                    labels=[];widths=[];witnesses=[]
                    if pending:
                        labels=[classes[pending[2]-2]];counts[labels[0]]+=1
                        for width in range(1,5):
                            found=next((s for s in intervals if s[2]==width and start<=s[0] and s[1]<=pending[0]),None)
                            if found:widths.append(width);witnesses.append([width,found[0],found[1]]);matrix[width-1][pending[2]-2]+=1
                        if widths:labels.append(classes[3]);counts[classes[3]]+=1
                    boundaries.append(dict(token_ordinal=ti,start=start,end=end,pending_start=pending[0] if pending else None,pending_end=pending[1] if pending else None,complete_widths=widths,witnesses=witnesses,classes=labels));start=end
                geo=dict(counts=counts,matrix=matrix,zero_piece_count=lengths.count(0),boundaries=boundaries);geometries.append(geo)
                typed_equal(b['compact_analysis'],{k:geo[k] for k in ('counts','matrix','zero_piece_count')})
            current={n:current[n]+delta[n] for n in names}
            assert {n:x['returned'] for n,x in result['native_call_counters'].items()}==current
            progress[strata.index(c['stratum'])]+=1
            assert result['native_state']['cases_computed']==i+1 and result['native_state']['case_results_written']==i
            typed_equal(result['native_state']['stratum_computed'],progress)
            assert result['native_state']['token_work_reserved']==token_work
        coverage=rows[183];assert coverage['event']=='unicode_coverage_summary'
        counts={k:0 for k in classes};matrix=[[0]*3 for _ in range(4)];unknown=[]
        for c,g in zip(source,geometries):
            if not c['coverage_population']:continue
            if g is None:unknown.append(c['ordinal']);continue
            for k in classes:counts[k]+=g['counts'][k]
            for a in range(4):
                for b in range(3):matrix[a][b]+=g['matrix'][a][b]
        selectors=None if unknown else {};selected=None if unknown else [];indexed={}
        if not unknown:
            for cl in classes:
                found=next(((c,b) for c,g in zip(source,geometries) if c['coverage_population'] for b in g['boundaries'] if cl in b['classes']),None)
                if found is None:selectors[cl]=None;continue
                c,b=found;pair=(c['ordinal'],b['token_ordinal'])
                if pair not in indexed:indexed[pair]=len(selected);selected.append(dict(case_ordinal=pair[0],token_ordinal=pair[1],take_tokens=pair[1]+1,byte_cut=b['end'],classes=b['classes']))
                selectors[cl]=indexed[pair]
        summary=dict(coverage_complete=not unknown,all_case_QC_complete=geometry_count+harness==84,counts=None if unknown else counts,matrix=None if unknown else matrix,known_counts_lower_bound=counts,known_matrix_lower_bound=matrix,unknown_population_ordinals=unknown,selectors=selectors,selected_prefixes=selected,required_available=None if unknown else all(counts[k]>0 for k in classes))
        typed_equal({k:coverage['body'][k] for k in summary},summary);typed_equal(base['authored_geometry_summary'],summary)
        assert {n:x['returned'] for n,x in coverage['native_call_counters'].items()}==current
        if base['id']=='complete_positive':
            assert len(rows)==191 and len(selected)==3 and rows[184]['event']=='unicode_selection_plan'
            for j,choice in enumerate(selected):
                r=rows[185+j];b=r['body'];geo=geometries[choice['case_ordinal']]['boundaries'][choice['token_ordinal']];n=choice['take_tokens']
                assert r['event']=='unicode_selected_prefix_result'
                assert b['pending_interval']==[geo['pending_start'],geo['pending_end']] and b['piece_interval']==[geo['start'],geo['end']]
                assert b['prefix_sha256']==digest(raw_source[choice['case_ordinal']][:choice['byte_cut']])
                assert b['complete_widths']==geo['complete_widths'] and b['witnesses']==geo['witnesses']
                current['llama_sampler_init_grammar']+=1;current['llama_sampler_free']+=1;current['llama_sampler_apply']+=n+2;current['llama_sampler_accept']+=n;token_work+=n
                assert {n:x['returned'] for n,x in r['native_call_counters'].items()}==current
                assert r['native_state']['selected_prefixes_computed']==j+1 and r['native_state']['selected_prefix_results_written']==j
                assert all(e['admitted'] is False for e in b['observation']['completion_EOG'])
            assert [r['event'] for r in rows[188:]]==['unicode_cleanup_returned','unicode_batch_returned','child_normal_completion']
        else:assert rows[-1]['event']=='failure' and len(rows)==185
        current['llama_model_free']+=1;current['llama_backend_free']+=1
        assert {n:x['returned'] for n,x in rows[-1]['native_call_counters'].items()}==current
        assert current['llama_sampler_init_grammar']==current['llama_sampler_free']==geometry_count+(3 if base['id']=='complete_positive' else 0)
        state=rows[-1]['native_state'];assert state['samplers_owned']==state['sampler_release_unknown']==0
        assert state['model_free_return_observed'] is state['backend_free_return_observed'] is True
        assert state['model_owned'] is state['backend_owned'] is state['model_release_unknown'] is state['backend_release_unknown'] is False
        if base['failure_marker_hex'] is not None:
            marker=json.loads(bytes.fromhex(base['failure_marker_hex']));r=rows[-1]
            identity=dict(pid=4242,error_class=r['body']['error_class'],reason_code=r['body']['reason_code'],elapsed_ms=r['elapsed_ms'],row_sequence_reserved=r['row_sequence'])
            assert digest(canon(identity))==r['body']['primary_failure_id']==marker['primary_failure_id']
            assert marker['elapsed_ms']==r['elapsed_ms'] and marker['row_sequence_reserved']==r['row_sequence']
            assert marker['failure_row_publication']['sha256']==digest(lines[-1]+b'\n')
        p=base['expected_projection'];assert (p['validated_native_geometry_rows'],p['known_membership_outcomes'])==(geometry_count,known)
        assert p['all_expected_membership_outcomes_match'] is allmatch
        summaries.append(dict(id=base['id'],rows=len(rows),bytes=len(raw),cases=84,geometry=geometry_count,known_membership=known,harness=harness,total_returned=sum(current.values()),token_work=token_work,selectors=selectors,expected_classification=p['classification']))
    assert len(fixture['scenarios'])==36 and len(fixture['callback_cases'])==11
    for sc in fixture['scenarios']:
        lines=base_bytes[sc['base_trace']];raw=b''.join(lines if sc['prefix_rows'] is None else lines[:sc['prefix_rows']]);parts=raw[:-1].split(b'\n') if raw else []
        parts=[p+b'\n' for p in parts]
        for change in sc['replace_rows']:parts[change['index']]=bytes.fromhex(change['raw_hex'])
        raw=b''.join(parts)+b''.join(bytes.fromhex(x) for x in sc['append_rows_hex'])+bytes.fromhex(sc['tail_hex'])
        assert len(raw)==sc['materialized_bytes'] and digest(raw)==sc['materialized_sha256']
    assert mixed==0
    assert all(pin(p)==pins[k] for k,p in paths.items())
    note='''# Unicode observation literal-trace peer v1

One finite coverage gap remains before validator implementation: none of the four complete bases or 36 overlays supplies a coherent mixed-EOG result. The membership-conflict base has two known-false EOG admissions, not a disagreement. Add a whole-case negative or literal overlay whose exact closed union reports mixed EOG booleans, native_member/matches null, valid geometry retained for all78 native-byte cases, known membership77, and clean terminal failure. Keep population and the original failed experiment unchanged.

Independent pinned-data inspection otherwise agrees on all four full histories: 84 source-linked cases, global117 byte-piece identities, 15 setup bodies/vectors, per-case and selected-prefix API arithmetic, publication lag, independent UTF8 interval geometry, population summaries/selectors, final cleanup and failure identity references. The positive has191 rows/U3; negatives retain all84 cases with unavailable, known conflict or QC-unknown axes distinct. Every overlay materializes to its declared bytes/digest. Malformed overlay expectations were inspected as authored test inputs, not evaluated by a new validator.

This is a fixture/source-format peer check only. No observe/require-complete API exists in this review; no untrusted-input parser, source/owner authentication, runtime file, native vocabulary, model or SDK call was evaluated. All qualification and runtime flags remain false. Preserve v1 and correct the missing fixture in a separate successor after root's finite-batch decision.
'''
    with NOTE.open('x',encoding='utf-8',newline='\n') as out:out.write(note)
    value=dict(schema_version=1,status='HOLD_ONE_MISSING_COHERENT_MIXED_EOG_FIXTURE',recorded_at_utc=datetime.now(timezone.utc).isoformat(),reviewer='/root/native_039_acceptance_audit',inputs=pins,review_script=pin(Path(__file__)),note=pin(NOTE),base_checks=summaries,
        overlay_materializations=36,callback_families=11,coherent_mixed_EOG_cases=0,
        finding=dict(id='mixed_EOG_membership_unknown_whole_history_missing',expected_native_geometry_rows=78,expected_known_membership_outcomes=77,expected_membership_match=None,geometry_and_population_unchanged=True),
        batch_complete=True,no_other_confirmed_material_finding_in_bounded_batch=True,
        observation_validator_implemented=False,SDK_native_payload_operations=0,old_run_operations=0,profile_qualified=False,originals_authenticated=False,runtime_authorized=False)
    with OUT.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(peer=pin(OUT),note=pin(NOTE),base_traces=len(summaries),overlays=36)))

if __name__=='__main__':main()
