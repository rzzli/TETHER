"""Framing/provenance checks only. This is not a UTF8 test adapter or decoder."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import time
import unittest

HERE=Path(__file__).resolve().parent
CORPUS=HERE/'UTF8-ORACLE-CORPUS-v2.json'
SPEC=HERE/'UTF8-ORACLE-SPEC-v2.md'
GENERATOR=HERE/'author_utf8_oracle_corpus_v2.py'
PROVENANCE=HERE/'UTF8-ORACLE-GENERATION-PROVENANCE-v2.json'
REPORT=HERE/'UTF8-ORACLE-STRUCTURAL-CHECKS-v2.json'
DATA=json.loads(CORPUS.read_text(encoding='utf-8'))
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def need(value,message):
    if not value:raise ValueError(message)
def rawhex(value):
    need(type(value) is str and len(value)%2==0 and all(c in '0123456789abcdef' for c in value),'Canonical lowercase byte hex')
    return bytes.fromhex(value)
def scalar(value):return type(value) is int and 0<=value<=0x10FFFF and not 0xD800<=value<=0xDFFF

def validate_framing(data):
    need(data['schema_version']==1 and data['profile']=='strict_UTF8_byte_chunk_oracle_v1','Exact fixture profile')
    cases=data['cases'];need(type(cases) is list and len(cases)<=128,'Fixture count cap')
    ids=set();steps=totalbytes=0
    fields={'status','emitted_scalars','decoded_scalars','pending_hex','pending_width','consumed_in_chunk','examined_in_chunk',
        'consumed_total','examined_total','unconsumed_hex','error','finalization'}
    for case in cases:
        identity=case['id'];need(type(identity) is str and identity and identity not in ids,'Stable unique fixture ID');ids.add(identity)
        raw=rawhex(case['raw_hex']);need(len(raw)<=128 and hashlib.sha256(raw).hexdigest()==case['sha256'],'Fixture raw hash/size')
        totalbytes+=len(raw);joined=b'';cuts=[];emitted=[];consumed=examined=0;firsterror=None;finished=False
        need(type(case['steps']) is list and case['steps'] and case['steps'][-1]['final'] is True,'Explicit final request')
        for step in case['steps']:
            steps+=1;need(not finished,'No feeds after successful finalization')
            need(set(step)=={'chunk_hex','final','expected'} and type(step['final']) is bool,'Exact step shape')
            chunk=rawhex(step['chunk_hex']);joined+=chunk;cuts.append(len(joined));state=step['expected']
            need(type(state) is dict and set(state)==fields,'Exact expected-state schema')
            need(state['status'] in ('boundary','pending','error','finished'),'Declared state enum')
            need(type(state['emitted_scalars']) is list and all(scalar(s) for s in state['emitted_scalars']),'Scalar output type/range')
            emitted+=state['emitted_scalars'];need(state['decoded_scalars']==emitted,'Cumulative authored output framing')
            pending=rawhex(state['pending_hex']);unconsumed=rawhex(state['unconsumed_hex'])
            need((not pending and state['pending_width'] is None) or
                type(state['pending_width']) is int and 2<=state['pending_width']<=4 and 0<len(pending)<state['pending_width'],
                'Pending framing width/count')
            ci,ei=state['consumed_in_chunk'],state['examined_in_chunk']
            need(type(ci) is int and type(ei) is int and 0<=ci<=ei<=len(chunk),'Per-step work bounds')
            consumed+=ci;examined+=ei
            need(state['consumed_total']==consumed and state['examined_total']==examined,'Cumulative work arithmetic')
            need(unconsumed==chunk[ci:],'Unconsumed supplied tail framing')
            failure=state['error']
            if state['status']=='error':
                need(type(failure) is dict and set(failure)=={'code','byte_offset','sequence_start_offset','offending_byte'},'Error-object shape')
                need(failure['code'] in ('invalid_lead','unexpected_continuation','invalid_continuation','overlong_sequence',
                    'surrogate_scalar','out_of_range_scalar','premature_eof'),'Error category enum')
                need(type(failure['byte_offset']) is int and type(failure['sequence_start_offset']) is int and
                    0<=failure['sequence_start_offset']<=failure['byte_offset']==consumed,'Error offset framing')
                need(failure['offending_byte'] is None or type(failure['offending_byte']) is int and 0<=failure['offending_byte']<=255,
                    'Offending byte type/range')
                if firsterror is not None:
                    need(failure==firsterror and ci==ei==0 and not state['emitted_scalars'],'Absorbing error metadata framing')
                else:firsterror=copy.deepcopy(failure)
                need(examined==consumed+(failure['offending_byte'] is not None),'Examined-but-not-consumed framing')
            else:
                need(failure is None and firsterror is None,'No recovery or stray error')
                need(ci==ei==len(chunk),'Nonerror whole chunk framing')
            need(state['finalization']==(('failed' if failure else 'succeeded') if step['final'] else 'not_requested'),
                'Per-step finalization label')
            need(not (state['status'] in ('boundary','finished') and pending),'Boundary cannot contain pending bytes')
            need(state['status']!='pending' or pending,'Pending state needs evidence')
            finished=state['status']=='finished';need(not finished or step['final'],'Finished requires final request')
        need(joined==raw and cuts==case['chunk_cuts'],'Full raw bytes and cumulative supplied cuts')
    need(steps<=1024 and totalbytes<=32768,'Aggregate finite corpus bounds')
    return dict(fixtures=len(cases),steps=steps,supplied_bytes=totalbytes)

class Checks(unittest.TestCase):
    def test_corpus_framing_schema_arithmetic(self):
        self.assertEqual(validate_framing(DATA),dict(fixtures=107,steps=167,supplied_bytes=354))
    def test_each_declared_scalar_has_complete_and_every_interior_cut(self):
        cases={c['id']:c for c in DATA['cases']}
        for pair in DATA['expected_scalar_encoding_pairs']:
            raw=rawhex(pair['hex']);self.assertTrue(scalar(pair['scalar']))
            self.assertIn('scalar/'+pair['id'],cases)
            for cut in range(1,len(raw)):
                case=cases['interior/'+pair['id']+'/'+str(cut)]
                self.assertEqual(case['raw_hex'],pair['hex']);self.assertEqual(case['chunk_cuts'],[cut,len(raw)])
                self.assertEqual(case['steps'][-1]['expected']['emitted_scalars'],[pair['scalar']])
        self.assertEqual(len(DATA['expected_scalar_encoding_pairs']),14)
    def test_all_required_fixed_strata_and_error_categories_present(self):
        ids={c['id'] for c in DATA['cases']}
        required={'ascii/raw_nul','ascii/control_edges','ascii/json_escape_bmp','ascii/json_escape_surrogate_pair',
            'ascii/json_escape_lone_surrogate','ascii/json_backslash_prefix','ascii/json_object_prefix','scalar/bom',
            'scalar/noncharacter_fdd0','scalar/bmp_max','scalar/scalar_max','mixed/three_widths_three_chunks',
            'mixed/complete_two_then_partial_four','mixed/middle_bom_is_not_removed','scalar/two_byte_min','scalar/four_middle_lead','split_restricted/overlong_three','split_restricted/overlong_four','split_restricted/surrogate','split_restricted/out_of_range','mixed/nul_does_not_terminate','multichunk/empty_while_pending',
            'absorbing/pending_error_later_valid_bytes_ignored','absorbing/boundary_error_empty_final','invalid/valid_prefix_committed'}
        self.assertTrue(required<=ids)
        codes={s['expected']['error']['code'] for c in DATA['cases'] for s in c['steps'] if s['expected']['error']}
        self.assertEqual(codes,{'invalid_lead','unexpected_continuation','invalid_continuation','overlong_sequence',
            'surrogate_scalar','out_of_range_scalar','premature_eof'})
        for name,width in [('cent',2),('euro',3),('grinning_face',4)]:
            for cut in range(1,width):
                self.assertIn('eof/same_chunk/'+name+'/'+str(cut),ids)
                self.assertIn('eof/empty_final/'+name+'/'+str(cut),ids)
    def test_generation_provenance_and_no_decoder_implementation(self):
        provenance=json.loads(PROVENANCE.read_text(encoding='utf-8'))
        self.assertEqual(provenance['specification'],pin(SPEC));self.assertEqual(provenance['corpus'],pin(CORPUS))
        self.assertEqual(provenance['generator'],pin(GENERATOR));self.assertEqual(DATA['specification'],pin(SPEC))
        self.assertEqual(provenance['decoder_or_codec_calls'],0);self.assertEqual(provenance['CPU_GGUF_oldpack_access'],0)
        tree=ast.parse(GENERATOR.read_text(encoding='utf-8'))
        imports=[n.names[0].name if isinstance(n,ast.Import) else n.module for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertEqual(imports,['hashlib','json','pathlib'])
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('decode','encode') for n in ast.walk(tree)))
        self.assertFalse(any(isinstance(n,ast.Name) and n.id in ('codecs','utf_8_decode','WinDLL','Popen') for n in ast.walk(tree)))
    def test_reject_structural_corruptions_without_interpreting_UTF8(self):
        for mode in ('duplicate','hash','cuts','hex','counter','scalar','error-offset','recovery'):
            value=copy.deepcopy(DATA)
            if mode=='duplicate':value['cases'][1]['id']=value['cases'][0]['id']
            elif mode=='hash':value['cases'][1]['sha256']='0'*64
            elif mode=='cuts':value['cases'][1]['chunk_cuts']=[999]
            elif mode=='hex':value['cases'][1]['raw_hex']='zz'
            elif mode=='counter':value['cases'][1]['steps'][0]['expected']['consumed_total']+=1
            elif mode=='scalar':value['cases'][1]['steps'][0]['expected']['emitted_scalars']=[0xD800]
            elif mode=='error-offset':
                item=next(c for c in value['cases'] if c['id']=='invalid/stray_80');item['steps'][0]['expected']['error']['byte_offset']=1
            else:
                item=next(c for c in value['cases'] if c['id']=='absorbing/boundary_error_empty_final');item['steps'][-1]['expected']['emitted_scalars']=[0x41]
            with self.subTest(mode=mode),self.assertRaises(ValueError):validate_framing(value)

if __name__=='__main__':
    assert not REPORT.exists(),'Preserve previous structural evidence'
    started=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    proof=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,
        failures=[dict(test=str(c),trace=t) for c,t in result.failures],errors=[dict(test=str(c),trace=t) for c,t in result.errors],
        corpus=pin(CORPUS),specification=pin(SPEC),generator=pin(GENERATOR),generation_provenance=pin(PROVENANCE),checker=pin(Path(__file__)),
        counts=validate_framing(DATA),elapsed_seconds=time.monotonic()-started,
        semantic_decoder_comparisons=0,test_adapters_implemented=0,CPU_GGUF_oldpack_operations=0,native_compiler_network_calls=0,
        scope='Structural/schema/hash/cut/counter-framing/provenance checks only; no UTF8 decoding or independent semantic oracle validation.')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(proof,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(report=pin(REPORT),counts=proof['counts'])))
    raise SystemExit(0 if result.wasSuccessful() else 1)
