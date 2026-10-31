"""NEW fixture framing/identity checks only; no target codec or producer."""
import ast
import base64
import hashlib
import io
import json
import struct
import unittest
import zlib
from pathlib import Path

HERE=Path(__file__).resolve().parent


def read(name):return (HERE/name).read_bytes()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(name):
    b=read(name);return dict(path=str((HERE/name).resolve()),bytes=len(b),sha256=sha(b))
def blob(b):
    r=zlib.decompress(base64.b64decode(b['data'],validate=True))
    assert len(r)==b['bytes'] and sha(r)==b['sha256'];return r
def plain(v):
    if type(v) is dict:
        if set(v)=={'$bytes_hex'}:return bytes.fromhex(v['$bytes_hex'])
        if set(v)=={'$tuple'}:return tuple(plain(x) for x in v['$tuple'])
        return {k:plain(x) for k,x in v.items()}
    if type(v) is list:return [plain(x) for x in v]
    return v


def main():
    corpus=json.loads(read('ROLE-AWARE-FORMAT-LITERAL-CORPUS-v2.json'))
    schema=json.loads(read('ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json'))
    bases={b['id']:b for b in corpus['bases']}
    counts=dict(bases=0,byte_negatives=0,anchors=0,actual_frames=0,known_empty_files=0)
    class Checks(unittest.TestCase):
        def test01_fixed_counts_and_sources(self):
            self.assertEqual(len(bases),40);self.assertEqual(len(corpus['byte_negatives']),225)
            self.assertEqual(len({m['id'] for m in corpus['byte_negatives']}),225)
            self.assertEqual(sha(read('ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json')),'b71cd8f49ccc8d4dc56b31915a3ed20465f58b08bb35b54df63a73a49e655b7a')
            ast.parse(read('role_ledger_independent_tests_v2.py'))

        def test02_exact_section_layout_and_hashes(self):
            for b in corpus['bases']:
                r=blob(b['raw']);self.assertEqual(r[:8],b'RAPLEDG1')
                self.assertEqual(struct.unpack_from('<HH',r,8),(1,2))
                self.assertEqual(struct.unpack_from('<Q',r,40)[0],len(r))
                off=4096
                for i,l in enumerate(b['layout']):
                    p=256+64*i
                    ident,width,n,start,size=struct.unpack_from('<HHIQQ',r,p)
                    self.assertEqual((ident,width,n,start,size),(i+1,l['record_size'],l['count'],off,l['bytes']))
                    self.assertEqual(n*width,size)
                    self.assertEqual(hashlib.sha256(r[start:start+size]).digest(),r[p+24:p+56])
                    off+=size;counts['actual_frames']+=1
                self.assertEqual(off,len(r));counts['bases']+=1

        def test03_all_mutation_bytes_and_pins(self):
            cache={}
            for m in corpus['byte_negatives']:
                if m['base'] not in cache:cache[m['base']]=blob(bases[m['base']]['raw'])
                base=cache[m['base']]
                if 'truncate' in m:r=base[:m['truncate']]
                elif 'append_hex' in m:r=base+bytes.fromhex(m['append_hex'])
                else:
                    p=m['patch'];r=bytearray(base);x=bytes.fromhex(p['hex']);r[p['offset']:p['offset']+len(x)]=x
                    if p['rehash_sections']:
                        for i in range(8):
                            q=256+64*i;o,n=struct.unpack_from('<QQ',r,q+8)
                            r[q+24:q+56]=hashlib.sha256(r[o:o+n]).digest()
                    r=bytes(r)
                self.assertEqual((len(r),sha(r)),(m['bytes'],m['sha256']));self.assertNotEqual(r,base)
                counts['byte_negatives']+=1

        def test04_manual_anchors(self):
            for b in corpus['bases']:
                r=blob(b['raw'])
                for a in b['anchors']:
                    x=bytes.fromhex(a['hex']);self.assertEqual(r[a['offset']:a['offset']+len(x)],x)
                    counts['anchors']+=1
            self.assertEqual(counts['anchors'],134)

        def test05_canonical_value_domains_and_named_keys(self):
            for b in corpus['bases']:
                v=plain(json.loads(blob(b['semantic_value'])))
                self.assertEqual(set(v),set(schema['api']['value_shape']['exact_keys']))
                self.assertEqual(set(v['header']),set(schema['api']['value_shape']['header_keys']))
                self.assertIs(type(v['module_edges']),tuple)
                for key in ('queries','paths','module_names'):self.assertIs(type(v[key]),bytes)
                for c in v['calls']:
                    self.assertEqual(set(c),set(schema['value_api_details']['call_exact_keys']))
                    self.assertEqual(set(c['flags']),set(schema['enums']['call_flags_bits']))
                    self.assertTrue(all(type(x) is bool for x in c['flags'].values()))
                    self.assertEqual(c['flags']['ERROR_DEFINITION_OBSERVED'],c['error_definition_atom']['tag']!='UNOBSERVED')
                    self.assertEqual(c['flags']['ERROR_DEFINED'],c['error_definition_atom']['value'] is True)
                self.assertLessEqual(len(blob(b['raw'])),14800384)

        def test06_complete_known_empty_has_empty_digest(self):
            empty=hashlib.sha256(b'').digest()
            wrong=[]
            for b in corpus['bases']:
                if not b['expected']['accepted']:continue
                v=plain(json.loads(blob(b['semantic_value'])))
                for f in v['files']:
                    if f['expected_size']==0 and f['flags']['HASH_COMPLETE']:
                        counts['known_empty_files']+=1
                        if f['expected_sha256']!=empty or f['actual_sha256']!=empty:wrong.append((b['id'],f['ordinal']))
            self.assertEqual(wrong,[],'Complete empty-file digests must be SHA256(empty); corrected named v2 keeps preserved v1 evidence')
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    report=dict(schema_version=1,status='PASS' if r.wasSuccessful() else 'FAIL',methods=r.testsRun,
                failures=[dict(test=str(t),traceback=x) for t,x in r.failures],errors=[dict(test=str(t),traceback=x) for t,x in r.errors],
                counts=counts,transcript=stream.getvalue(),pins=[pin('ROLE-AWARE-FORMAT-LITERAL-CORPUS-v2.json'),
                pin('ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT-v2.json'),pin('ROLE-AWARE-FORMAT-LITERAL-PROVENANCE-v2.json'),
                pin('author_role_ledger_literals_v2.py'),pin('role_ledger_independent_tests_v2.py'),pin(Path(__file__).name)],
                scope='Fixture byte/transport framing checks and known-empty self-review only, NOT a reference codec or subject test.',
                activity=dict(codec_imports=0,codec_runs=0,producer_imports=0,producer_runs=0,original_payload_operations=0,native_physical_operations=0))
    out=HERE/'ROLE-AWARE-FORMAT-LITERAL-STRUCTURE-PROOF-v2.json'
    raw=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode()
    with out.open('xb') as f:f.write(raw)
    print(json.dumps(dict(status=report['status'],methods=r.testsRun,failures=len(r.failures),errors=len(r.errors),counts=counts,proof=pin(out.name))))


if __name__=='__main__':main()
