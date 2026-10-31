"""Structural/source-binding checks, not a native/token/prefix implementation."""
import ast
import collections
import copy
import hashlib
import json
from pathlib import Path
import time
import unittest

HERE=Path(__file__).resolve().parent
CORPUS=HERE/'UNICODE-CONTROL-CORPUS-v1.json'
STAGES=HERE/'UNICODE-CONTROL-STAGES-v1.json'
PROVENANCE=HERE/'UNICODE-CONTROL-PROVENANCE-v1.json'
GENERATION=HERE/'UNICODE-CONTROL-GENERATION-CHECKS-v1.json'
CONTRACT=HERE/'UNICODE-CONTROL-CONTRACT-v2.json'
REPORT=HERE/'UNICODE-CONTROL-STRUCTURAL-CHECKS-v1.json'
data=json.loads(CORPUS.read_text(encoding='utf-8'));stage_data=json.loads(STAGES.read_text(encoding='utf-8'));contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def fingerprint(value):return hashlib.sha256(canonical(value)).hexdigest()
def pin(path):
    path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def require(value,message):
    if not value:raise ValueError(message)
def validate_framing(corpus):
    cases=corpus['cases'];require(type(cases) is list and len(cases)==84,'Exact84fixture count')
    ids=set();stages={s['id']:s for s in stage_data['stages']}
    for ordinal,case in enumerate(cases):
        require(type(case['id']) is str and case['id'] not in ids and case['ordinal']==ordinal,'Stable unique ID/order');ids.add(case['id'])
        require(case['stage_id'] in stages and case['grammar_sha256']==stages[case['stage_id']]['grammar_sha256'],'Exact stage grammar binding')
        raw=bytes.fromhex(case['raw_hex']);require(raw.hex()==case['raw_hex'] and len(raw)==case['bytes']<=1024 and hashlib.sha256(raw).hexdigest()==case['sha256'],'Exact raw framing')
        expected=case['expected']
        require(type(expected['native_byte_eligible']) is bool and type(expected['generation_grammar_membership']) is bool
            and type(expected['complete_v3_semantic_validation']) is bool,'Typed authored outcomes')
        if expected['native_byte_eligible']:
            require(expected['native_membership'] is expected['generation_grammar_membership'] and expected['native_membership_null_reason'] is None,'Eligible native expectation')
        else:
            require(expected['native_membership'] is None and expected['native_membership_null_reason'] in ('harness_raw_nul_rejection','harness_utf8_rejection'),'Harness native-null distinction')
        require(case['coverage_population'] is (expected['native_byte_eligible'] and expected['generation_grammar_membership'] and expected['complete_v3_semantic_validation']),'Fixed coverage population')
        require(case['measured_piece_ledger'] is None and type(case['measured_piece_ledger_null_reason']) is str,'Source-only unknown measured ledger')
        cap=min(65536,4*len(raw)+32)
        require(case['prospective_token_cap']==cap and case['prospective_case_row_bound']==12*cap+3*len(raw)+8192+64<=65536,'Conditional row/token arithmetic')
        if expected['JSON_value'] is not None:
            require(fingerprint(expected['JSON_value'])==expected['JSON_value_sha256'],'Decoded scalar JSON fingerprint')
        else:require(type(expected['JSON_value_null_reason']) is str and expected['JSON_value_sha256'] is None,'Null decoded domain reason')
    return cases

class Checks(unittest.TestCase):
    def test_exact_case_order_strata_and_framing(self):
        cases=validate_framing(data)
        self.assertEqual(dict(collections.Counter(c['stratum'] for c in cases)),contract['corpus']['strata'])
        self.assertEqual(sum(c['coverage_population'] for c in cases),68)
        self.assertEqual(sum(c['expected']['native_byte_eligible'] for c in cases),78)
    def test_actual_full_stage_payload_and_grammar_bindings(self):
        self.assertEqual(stage_data['stage_instances'],4);self.assertEqual(len(stage_data['unique_grammar_hashes']),2)
        for declared,stage in zip(contract['language']['stage_instances'],stage_data['stages']):
            for key,value in declared.items():self.assertEqual(stage[key],value)
            p=stage['prepared'];self.assertEqual(p['interface'],'source-quote-interpretation-v3-gbnf')
            self.assertEqual(p['semantic_data']['original_request'],stage['request'])
            self.assertEqual(p['request_sha256'],fingerprint(stage['request']))
            self.assertEqual(p['payload_sha256'],fingerprint(p['payload']))
            grammar=p['generation_grammar'];raw=grammar['grammar'].encode('utf-8')
            self.assertTrue(grammar['grammar'].startswith('root ::='));self.assertEqual(grammar['generator'],'strict-interpretation-gbnf-v1')
            self.assertEqual(hashlib.sha256(raw).hexdigest(),stage['grammar_sha256']);self.assertEqual(len(raw),stage['grammar_bytes'])
            self.assertEqual(p['payload']['grammar'],grammar['grammar']);self.assertLessEqual(len(raw),65536)
            self.assertLessEqual(len(canonical(p['payload'])),65536);self.assertLessEqual(len(p['payload']['prompt'].encode('utf-8')),32768)
            self.assertFalse(p['execution_authorized']);self.assertEqual(p['native_conformance'],'unverified')
    def test_scalar_grid_contexts_and_ASCII_counterparts(self):
        by_id={c['id']:c for c in data['cases']}
        for index,pair in enumerate(data['scalar_pairs']):
            char=chr(pair['scalar']);self.assertEqual(char.encode('utf-8').hex(),pair['hex'])
            texts=['A'+char+'B','X'+char*8+'Y','e\u0301A'+char+'\U0001f600Z']
            for field,text in enumerate(texts):
                c=by_id['scalar/'+pair['id']+'/field'+str(field)];value=c['expected']['JSON_value']
                actual=value['claims'][0]['text'] if field==0 else value['abstention_reason'] if field==1 else value['unresolved'][0]
                self.assertEqual(actual,text);self.assertEqual(c['stage_id'],stage_data['stages'][(3*index+field)%4]['id'])
                self.assertGreater(c['wire_statistics']['raw_nonASCII_bytes'],0)
            raw=by_id['scalar/'+pair['id']+'/field0'];escaped=by_id['ASCII_escape/'+pair['id']]
            self.assertEqual(raw['expected']['JSON_value'],escaped['expected']['JSON_value'])
            self.assertEqual(escaped['ASCII_counterpart_of'],raw['id']);self.assertEqual(raw['stage_id'],escaped['stage_id'])
            self.assertEqual(escaped['wire_statistics']['raw_nonASCII_bytes'],0);self.assertTrue(escaped['wire_statistics']['ASCII_only'])
            self.assertGreater(escaped['wire_statistics']['Unicode_escape_spellings'],0)
    def test_semantic_and_generation_controls_stay_distinct(self):
        by_id={c['id']:c for c in data['cases']}
        for identity in ('negative/raw_less_than','negative/key_order','negative/outside_whitespace'):
            e=by_id[identity]['expected'];self.assertTrue(e['complete_v3_semantic_validation']);self.assertFalse(e['generation_grammar_membership'])
        e=by_id['negative/duplicate_claim_text']['expected'];self.assertFalse(e['complete_v3_semantic_validation']);self.assertTrue(e['generation_grammar_membership'])
        e=by_id['negative/lone_surrogate_escape']['expected'];self.assertTrue(e['project_JSON_parse']);self.assertFalse(e['Unicode_scalar_JSON']);self.assertIsNone(e['JSON_value'])
        e=by_id['negative/duplicate_JSON_name']['expected'];self.assertTrue(e['JSON_syntax']);self.assertFalse(e['project_JSON_parse'])
        for c in data['cases']:
            if c['stratum']=='byte_harness_guards':self.assertIsNone(c['expected']['native_membership']);self.assertFalse(c['coverage_population'])
        self.assertTrue(by_id['guard/raw_NUL']['wire_statistics']['UTF8_valid'])
        self.assertEqual(sum(not c['wire_statistics']['UTF8_valid'] for c in data['cases']),5)
    def test_bounds_and_selector_are_prospective_without_implementation(self):
        limits=contract['preserved_limits'];self.assertEqual((limits['cooperative_work_ms'],limits['whole_child_seconds'],limits['owner_seconds']),(117000,120,300))
        self.assertEqual(limits['prospective_profile_token_upper_bound'],100*4128)
        rows=contract['JSONL_reservation'];reserved=sum(v['count']*v['bytes_each'] for v in rows.values() if type(v) is dict)
        self.assertEqual(reserved,rows['maximum_reserved_bytes']);self.assertEqual(reserved,7995392);self.assertLess(reserved,8388608)
        self.assertEqual(sum(v['count'] for v in rows.values() if type(v) is dict),276)
        self.assertEqual(contract['coverage']['required_classes'],['pending_width2','pending_width3','pending_width4','same_piece_complete_scalar_then_pending'])
        self.assertIsNone(contract['coverage']['expected_measured_counts']);self.assertFalse(contract['execution_authorized'])
        self.assertEqual(contract['coverage']['selector']['maximum_unique_selected_boundaries'],4)
    def test_provenance_and_raw_semantic_generation_checks(self):
        provenance=json.loads(PROVENANCE.read_text(encoding='utf-8'));proof=json.loads(GENERATION.read_text(encoding='utf-8'))
        self.assertEqual(provenance['corpus'],pin(CORPUS));self.assertEqual(provenance['stages'],pin(STAGES));self.assertEqual(provenance['pure_checks'],pin(GENERATION))
        self.assertEqual(proof['status'],'passed');self.assertEqual(proof['errors'],[]);self.assertEqual(proof['cases'],84)
        self.assertEqual([r['id'] for r in proof['exact_rawbyte_semantic_checks']],[c['id'] for c in data['cases']])
        for row in proof['exact_rawbyte_semantic_checks']:
            self.assertTrue(row['exact_rawbytes_v3_validator_called']);self.assertTrue(row['project_JSON_matches']);self.assertTrue(row['scalar_domain_matches']);self.assertTrue(row['v3_semantic_matches'])
        for row in provenance['source_modules']:
            self.assertTrue(row['universal_newline_source_text_equal']);self.assertEqual(row['installed'],pin(row['installed']['path']));self.assertEqual(row['workspace'],pin(row['workspace']['path']))
        self.assertEqual(len(provenance['source_modules']),9)
        self.assertEqual(provenance['CPU_GGUF_oldpack_operations'],0);self.assertEqual(provenance['tokenizer_native_compiler_network_calls'],0)
        self.assertEqual(proof['denied_operations'],[])
    def test_reject_structural_tampering_without_native_or_selector(self):
        for kind in ('casecount','duplicate','rawhash','ordinal','stage','native-null','population','rowbound'):
            value=copy.deepcopy(data)
            if kind=='casecount':value['cases'].pop()
            elif kind=='duplicate':value['cases'][1]['id']=value['cases'][0]['id']
            elif kind=='rawhash':value['cases'][0]['sha256']='0'*64
            elif kind=='ordinal':value['cases'][0]['ordinal']=1
            elif kind=='stage':value['cases'][0]['stage_id']='foreign'
            elif kind=='native-null':value['cases'][-1]['expected']['native_membership']=False
            elif kind=='population':value['cases'][-1]['coverage_population']=True
            else:value['cases'][0]['prospective_case_row_bound']=65537
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate_framing(value)

if __name__=='__main__':
    assert not REPORT.exists(),'Preserve earlier structural evidence'
    started=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    report=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',methods=result.testsRun,
        failures=[dict(test=str(t),traceback=x) for t,x in result.failures],errors=[dict(test=str(t),traceback=x) for t,x in result.errors],
        checker=pin(Path(__file__)),corpus=pin(CORPUS),stages=pin(STAGES),contract=pin(CONTRACT),provenance=pin(PROVENANCE),generation_checks=pin(GENERATION),
        elapsed_seconds=time.monotonic()-started,cases=84,stage_instances=4,unique_grammars=2,coverage_population=68,
        source_only=True,native_tokenizer_compiler_SDK_calls=0,CPU_GGUF_oldpack_operations=0,selector_or_bridge_implementation=False,
        scope='Structural/frame/identity/source/predeclared-outcome checks only. Generation-membership and natural token-boundary availability remain unqualified.')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(report,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(report=pin(REPORT),methods=result.testsRun,passed=result.wasSuccessful())))
    raise SystemExit(0 if result.wasSuccessful() else 1)
