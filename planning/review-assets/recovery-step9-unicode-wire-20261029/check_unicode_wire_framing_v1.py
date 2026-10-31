"""STRUCTURAL tests only for frozen design fragments, never a runtime parser."""
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import time
import unittest

HERE=Path(__file__).resolve().parent
CONTROL=HERE.parent/'recovery-step9-unicode-control-20261029'
PROOF=HERE/'UNICODE-WIRE-FRAMING-STRUCTURAL-PROOF-v1.json'
INPUTS=['UNICODE-WIRE-DESIGN-CONTRACT-v2.json','UNICODE-WIRE-DESIGN-FREEZE-v2.json','UNICODE-WIRE-FRAMING-CONTRACT-v1.json',
    'UNICODE-WIRE-FRAMING-CONTRACT-FREEZE-v1.json','UNICODE-WIRE-FRAMING-FIXTURES-v1.json','UNICODE-WIRE-FRAMING-FREEZE-v1.json',
    'author_unicode_wire_framing_v1.py','author_unicode_wire_framing_v2.py']
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=sha(raw))
def strict(raw):
    if type(raw) is not bytes or not raw or not raw.endswith(b'\n') or raw.endswith(b'\r\n') or raw.startswith(b'\xef\xbb\xbf'):raise ValueError('framing')
    if b'\n' in raw[:-1] or len(raw)>65536:raise ValueError('row')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('duplicate')
            out[k]=v
        return out
    value=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite')))
    if canonical(value)+b'\n'!=raw:raise ValueError('canonical')
    return value

def main():
    started=time.monotonic();assert not PROOF.exists(),'Preserve first structural result'
    before={name:pin(HERE/name) for name in INPUTS}
    fixtures=json.loads((HERE/INPUTS[4]).read_text(encoding='utf-8'))
    base=json.loads((HERE/INPUTS[0]).read_text(encoding='utf-8'));closure=json.loads((HERE/INPUTS[2]).read_text(encoding='utf-8'))
    s=base['semantic_contract'];f=closure['framing_semantics'];fp=closure['effective_wire_semantics_sha256']
    c=json.loads((CONTROL/'UNICODE-CONTROL-CORPUS-v1.json').read_text(encoding='utf-8'))['cases']
    stages=json.loads((CONTROL/'UNICODE-CONTROL-STAGES-v1.json').read_text(encoding='utf-8'))['stages']
    byid={x['id']:x for x in fixtures['JSONL_rows']};frags={x['id']:x for x in fixtures['pack_fragments']}
    counts=dict(pack_fragments=0,JSONL_rows=0,partial_history_scenarios=0)

    class Checks(unittest.TestCase):
        def root_shape(self,row):
            self.assertEqual(set(row),set(s['framing']['common_row_keys']));self.assertIs(type(row['schema_version']),int);self.assertEqual(row['schema_version'],1)
            for key,cap in [('row_sequence',275),('elapsed_ms',120000)]:self.assertIs(type(row[key]),int);self.assertTrue(0<=row[key]<=cap)
            self.assertEqual(row['wire_semantics_sha256'],fp)
            self.assertEqual(set(row['native_call_counters']),set(s['API_accounting']['names']))
            for key,item in row['native_call_counters'].items():
                self.assertEqual(set(item),{'attempted','returned'})
                for value in item.values():self.assertIs(type(value),int);self.assertTrue(0<=value<=s['API_accounting']['hard_caps'][key])
                self.assertLessEqual(item['returned'],item['attempted'])
            self.assertEqual(set(row['native_state']),set(s['framing']['native_state_fields']))
            for key,kind in s['framing']['native_state_fields'].items():
                value=row['native_state'][key]
                if kind=='strict bool':self.assertIs(type(value),bool)
                elif type(kind) is dict:
                    self.assertIs(type(value),int);self.assertTrue(kind['strict_int_range'][0]<=value<=kind['strict_int_range'][1])
                elif type(kind) is list:self.assertIn(value,kind)
                else:self.assertIs(type(value),list);self.assertEqual(len(value),6);self.assertTrue(all(type(v) is int and 0<=v<=84 for v in value))
            state=row['native_state']
            self.assertEqual(state['total_attempted'],sum(v['attempted'] for v in row['native_call_counters'].values()))
            self.assertEqual(state['total_returned'],sum(v['returned'] for v in row['native_call_counters'].values()))
            self.assertEqual(sum(state['stratum_computed']),state['cases_computed']);self.assertEqual(sum(state['stratum_results_written']),state['case_results_written'])
            self.assertLessEqual(state['case_results_written'],state['cases_computed'])

        def case_union(self,row):
            body=row['body'];self.assertEqual(set(body),set(s['case_row']['body_keys']))
            self.assertIs(type(body['case_ordinal']),int);self.assertTrue(0<=body['case_ordinal']<84);source=c[body['case_ordinal']]
            self.assertEqual(body['case_id'],source['id']);self.assertEqual(body['stage_instance_id'],source['stage_id'])
            self.assertEqual(body['grammar_sha256'],source['grammar_sha256']);self.assertEqual(body['raw_sha256'],source['sha256']);self.assertEqual(body['raw_bytes'],source['bytes'])
            obs=body['observation'];self.assertIs(type(obs),dict);self.assertEqual(set(obs),set(f['observation']['exact_keys']));self.assertIn(obs['status'],f['observation']['status_enum'])
            status=obs['status'];ledger=body['ledger'];qc=body['QC'];self.assertEqual(set(qc),{'status','reason'})
            self.assertIn(qc['status'],f['QC']['status_enum'])
            if status in f['QC']['harness_reason_enum'] or status=='not_attempted_QC_unknown':
                self.assertTrue(all(obs[k] is None for k in obs if k!='status'));self.assertIsNone(ledger)
                self.assertEqual(body['compact_analysis'],dict(counts=None,matrix=None,zero_piece_count=None));self.assertIsNone(body['matches_authored_native_expectation'])
                if status=='not_attempted_QC_unknown':self.assertEqual(qc['status'],'unknown');self.assertIn(qc['reason'],f['QC']['unknown_reason_enum'])
                else:self.assertEqual(qc,dict(status='harness_ineligible',reason=status))
                return
            self.assertEqual(qc,dict(status='ok',reason=None));self.assertIs(type(ledger),dict)
            self.assertEqual(set(ledger),{'token_ids','piece_byte_lengths','piece_hex'})
            N=len(ledger['token_ids']);self.assertEqual(N,len(ledger['piece_byte_lengths']));self.assertEqual(N,len(ledger['piece_hex']));self.assertTrue(1<=N<=source['prospective_token_cap'])
            self.assertTrue(all(type(v) is int and 0<=v<262144 for v in ledger['token_ids']))
            self.assertTrue(all(type(v) is int and 0<=v<=source['bytes'] for v in ledger['piece_byte_lengths']))
            expected=f['observation']['ordinary_membership_union'][status]
            self.assertIs(obs['native_member'],expected['native_member']);self.assertIs(obs['all_input_tokens_admitted'],expected['all_input_tokens_admitted'])
            if expected['rejection_fields'] is None:self.assertTrue(all(obs[k] is None for k in ('first_rejected_token_index','first_rejected_byte_start','first_rejected_byte_end')))
            else:
                r=obs['first_rejected_token_index'];self.assertIs(type(r),int);self.assertTrue(0<=r<N)
                self.assertEqual(obs['first_rejected_byte_start'],sum(ledger['piece_byte_lengths'][:r]));self.assertEqual(obs['first_rejected_byte_end'],sum(ledger['piece_byte_lengths'][:r+1]))
            if obs['completion_EOG'] is not None:
                self.assertTrue(1<=len(obs['completion_EOG'])<=64)
                for e in obs['completion_EOG']:self.assertEqual(set(e),{'id','admitted'});self.assertIs(type(e['id']),int);self.assertTrue(0<=e['id']<262144);self.assertIs(type(e['admitted']),bool)
                self.assertEqual([e['id'] for e in obs['completion_EOG']],sorted(set(e['id'] for e in obs['completion_EOG'])))
            if status=='native_EOG_disagreement':self.assertEqual({e['admitted'] for e in obs['completion_EOG']},{True,False});self.assertIsNone(body['matches_authored_native_expectation'])
            elif status=='native_member':self.assertTrue(all(e['admitted'] is True for e in obs['completion_EOG']))
            elif status=='native_eog_rejection':self.assertTrue(all(e['admitted'] is False for e in obs['completion_EOG']))
            else:self.assertIsNone(obs['completion_EOG'])

        def failure_union(self,row):
            self.assertLessEqual(len(canonical(row))+1,8192);b=row['body'];self.assertEqual(set(b),set(f['failure']['JSONL_exact_body_keys']))
            self.assertIn(b['error_class'],f['failure']['child_error_class_enum']);self.assertIn(b['reason_code'],f['failure']['reason_code_enum'])
            self.assertIn(b['diagnostic_file'],f['failure']['diagnostic_file_enum']);self.assertEqual(b['profile_qualification'],'not_established')

        def test_contract_fingerprint_enums_and_population(self):
            self.assertEqual(sha(canonical(dict(base_design_semantic_sha256=base['semantic_sha256'],framing_semantics=f))),fp)
            self.assertEqual(len(set(f['observation']['status_enum'])),7);self.assertEqual(len(set(f['failure']['reason_code_enum'])),30)
            for token in f['observation']['status_enum']+f['failure']['reason_code_enum']+f['failure']['child_error_class_enum']:
                self.assertRegex(token,r'^[A-Za-z_][A-Za-z0-9_]*$')
            self.assertEqual(len(c),84);self.assertEqual(sum(x['coverage_population'] for x in c),68);self.assertEqual(sum(x['expected']['native_byte_eligible'] for x in c),78)
            self.assertEqual(len(f['harness']['exact_observation']),7);self.assertEqual(sum(v is None for v in f['harness']['exact_observation'].values()),6)

        def test_literal_fragment_hashes_headers_and_ID_fields(self):
            for fragment in fixtures['pack_fragments']:
                raw=bytes.fromhex(fragment['raw_hex']);self.assertEqual(len(raw),fragment['bytes']);self.assertEqual(sha(raw),fragment['sha256']);self.assertIs(fragment['complete_profile_pack'],False);counts['pack_fragments']+=1
            header=bytes.fromhex(frags['header/exact']['raw_hex']);self.assertEqual(len(header),188);self.assertEqual(header[:8],b'R09NU01\0');self.assertEqual(header[8:12],b'\x01\0\0\0')
            self.assertEqual(header[12:44],bytes.fromhex(fp));self.assertEqual([int.from_bytes(header[i:i+4],'little') for i in range(172,188,4)],[4,2,84,4])
            self.assertNotEqual(bytes.fromhex(frags['header/old_magic']['raw_hex'])[:8],header[:8]);self.assertNotEqual(bytes.fromhex(frags['header/big_endian_version']['raw_hex'])[8:12],header[8:12])
            self.assertEqual(int.from_bytes(bytes.fromhex(frags['header/wrong_case_count']['raw_hex'])[180:184],'little'),85)
            self.assertEqual(len(bytes.fromhex(frags['header/trailing_header_byte']['raw_hex'])),189)
            self.assertLess(len(bytes.fromhex(frags['header/truncated_digest']['raw_hex'])),188)
            for name in ('empty','nonASCII','overlong','truncated','unsafe_backslash'):self.assertIs(frags['ID/'+name]['component_framing_expected'],False)

        def test_source_bound_grammar_stage_case_fragments_only(self):
            grams=list(dict.fromkeys(x['grammar_sha256'] for x in stages));strata=[x['name'] for x in s['corpus']['strata']]
            for i,h in enumerate(grams):
                fragment=frags['grammar/'+str(i)];raw=bytes.fromhex(fragment['raw_hex']);n=int.from_bytes(raw[:4],'little');at=4+n
                self.assertEqual(raw[4:at],('grammar/'+str(i)).encode());self.assertEqual(raw[at:at+32],bytes.fromhex(h));at+=32
                size=int.from_bytes(raw[at:at+4],'little');text=raw[at+4:];self.assertEqual(len(text),size);self.assertEqual(sha(text),h)
                self.assertEqual(text,next(x['prepared']['generation_grammar']['grammar'].encode() for x in stages if x['grammar_sha256']==h))
            for i,stage in enumerate(stages):
                raw=bytes.fromhex(frags['stage/'+str(i)]['raw_hex']);n=int.from_bytes(raw[:4],'little');at=4+n
                self.assertEqual(raw[4:at].decode(),stage['id']);self.assertEqual(raw[at:at+32],bytes.fromhex(stage['request_sha256']));self.assertEqual(raw[at+32:at+64],bytes.fromhex(stage['payload_sha256']));self.assertEqual(int.from_bytes(raw[at+64:],'little'),grams.index(stage['grammar_sha256']))
            for ordinal in (0,76,78,83):
                case=c[ordinal];raw=bytes.fromhex(frags['case/'+str(ordinal)]['raw_hex']);n=int.from_bytes(raw[:4],'little');at=4+n
                self.assertEqual(raw[4:at].decode(),case['id']);self.assertEqual(int.from_bytes(raw[at:at+4],'little'),ordinal);at+=12
                self.assertEqual(raw[at:at+32],bytes.fromhex(case['sha256']));at+=32;B=int.from_bytes(raw[at:at+4],'little');at+=4
                self.assertEqual(raw[at:at+B],bytes.fromhex(case['raw_hex']));at+=B;self.assertEqual(len(raw)-at,36)
                dims=[int.from_bytes(raw[at+i:at+i+4],'little') for i in range(0,36,4)]
                # JSON serialization sorts expected dimension keys; compare the normative order.
                order=['project_JSON_parse','Unicode_scalar_JSON','complete_v3_semantic_validation','generation_grammar_membership','native_membership','JSON_syntax']
                self.assertEqual(dims[:6],[2 if case['expected'][k] is None else int(case['expected'][k]) for k in order])
                self.assertEqual(dims[-1],case['prospective_token_cap']);self.assertEqual(bytes.fromhex(frags['case/'+str(ordinal)+'/truncated']['raw_hex']),raw[:-1])

        def test_literal_rows_framing_closed_union_and_explicit_scopes(self):
            for fixture in fixtures['JSONL_rows']:
                with self.subTest(row=fixture['id']):
                    raw=bytes.fromhex(fixture['raw_hex']);self.assertEqual(len(raw),fixture['bytes']);self.assertEqual(sha(raw),fixture['sha256']);self.assertIs(fixture['full_profile_valid'],False);self.assertIs(fixture['source_schedule_expected'],False)
                    valid=True
                    try:
                        row=strict(raw)
                        if fixture['scope'].startswith('mathematical_size_only'):
                            self.assertLessEqual(len(raw),60864) # NOT a valid source/observation history.
                        else:
                            self.root_shape(row)
                            if row['event']=='failure':self.failure_union(row)
                            else:self.case_union(row)
                    except (AssertionError,ValueError,UnicodeError,KeyError,TypeError):valid=False
                    self.assertEqual(valid,fixture['framing_expected']);counts['JSONL_rows']+=1

        def test_known_geometry_nulls_and_write_lag_are_distinct(self):
            for identity,zeros in [('case/one_whole_piece',0),('case/empty_piece_preserved',1),('case/mixed_EOG_geometry_preserved',0),('case/token_rejection_geometry_preserved',0)]:
                row=strict(bytes.fromhex(byid[identity]['raw_hex']));b=row['body'];case=c[b['case_ordinal']];ledger=b['ledger']
                self.assertEqual(b''.join(bytes.fromhex(x) for x in ledger['piece_hex']),bytes.fromhex(case['raw_hex']))
                self.assertEqual([len(bytes.fromhex(x)) for x in ledger['piece_hex']],ledger['piece_byte_lengths']);self.assertEqual(ledger['piece_byte_lengths'].count(0),zeros)
                self.assertEqual(b['QC']['status'],'ok');self.assertEqual(b['compact_analysis']['zero_piece_count'],zeros)
                self.assertTrue(all(value==0 for value in b['compact_analysis']['counts'].values()))
                self.assertEqual(row['native_state']['cases_computed'],1);self.assertEqual(row['native_state']['case_results_written'],0)
            for identity in ('case/harness_null_ledger','case/QC_unknown_null_measurements'):
                row=strict(bytes.fromhex(byid[identity]['raw_hex']));self.assertIsNone(row['body']['ledger']);self.assertTrue(all(v is None for v in row['body']['compact_analysis'].values()))

        def test_size_API_counter_and_footer_arithmetic(self):
            template=s['wire_size']['fixed_case_sizing_envelope'];self.assertEqual(len(canonical(template))+1-6,6408)
            self.assertLess(6408+64,8192);self.assertEqual(12*4128+3*1024+8192+64,60864)
            self.assertEqual(sum(s['API_accounting']['hard_caps'].values()),4276181);self.assertEqual(sum(s['API_accounting']['positive_fixed_profile_upper_bounds'].values()),530477)
            self.assertEqual(s['wire_size']['JSONL_buckets']['footer']['bytes_each'],8192);self.assertEqual(s['wire_size']['maximum_JSONL_rows'],276)
            self.assertEqual(96*65536+96*8192+64*8192+4*65536+16*8192,7995392);self.assertEqual(7995392+4096+65536,8065024)
            self.assertLess(8065024,8388608);self.assertLessEqual(fixtures['sizing']['footer_failure_example_bytes'],8192)
            # The mathematical envelope is intentionally not a semantic case pass.
            envelope=strict(bytes.fromhex(byid['sizing/maximum_arrays_preserving_zeros']['raw_hex']))
            with self.assertRaises(AssertionError):self.case_union(envelope)

        def test_partial_and_negative_histories_never_qualify(self):
            histories=fixtures['negative_partial_histories'];self.assertEqual(histories,f['partial_history']['history_expectations']);self.assertEqual(len(histories),14)
            for history in histories:self.assertIs(history['profile_qualified'],False);counts['partial_history_scenarios']+=1
            ids={x['id']:x for x in histories};self.assertIsNone(ids['mixed_EOG_known_geometry']['native_member']);self.assertEqual(ids['mixed_EOG_known_geometry']['geometry'],'retained')
            self.assertEqual(ids['pending_sampler_creation']['dependent_model_backend_release'],'blocked');self.assertIsNone(ids['population_geometry_unknown']['selectors'])
            self.assertEqual(ids['wrong_case_body_after_good_snapshot']['validated_native_rows'],0);self.assertIs(ids['complete_rows_then_marker']['failure_marker'],True)

    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    stable=before=={name:pin(HERE/name) for name in INPUTS};elapsed=time.monotonic()-started
    proof=dict(schema_version=1,status='passed' if result.wasSuccessful() and stable else 'failed',recorded_at_utc=datetime.now(timezone.utc).isoformat(),inputs=before,
        checker=pin(Path(__file__)),methods=result.testsRun,counts=counts,failures=[dict(test=str(t),traceback=s) for t,s in result.failures],errors=[dict(test=str(t),traceback=s) for t,s in result.errors],
        elapsed_seconds=elapsed,inputs_unchanged=stable,complete_profile_packs=0,bridge_decoder_parent_runtime_implementations=0,CPU_GGUF_oldpack_operations=0,
        target_native_SDK_tokenizer_compiler_calls=0,profile_qualified=False,source_qualification=False,
        scope='Only frozen literal fragment/row and finite counter/size/schema structural checks. No fullpack parser, real native observation, owner/source or complete profile history validation.')
    with PROOF.open('x',encoding='utf-8') as out:json.dump(proof,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),status=proof['status'],methods=result.testsRun,counts=counts)))
    return 0 if proof['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
