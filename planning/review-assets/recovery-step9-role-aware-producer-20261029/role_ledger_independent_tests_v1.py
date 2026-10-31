"""Pre-code tests of exact captured literal data; no source loading or I/O.

The future runner supplies a freshly pinned codec module and the NEW corpus.
No fixture ID, expected value or fault label is passed to codec entry points.
Producer APIs and owner identity are deliberately outside this module.
"""
import base64
import copy
import hashlib
import io
import json
import struct
import unittest
import zlib


def untransport(v):
    if type(v) is dict:
        if set(v)=={'$bytes_hex'}:
            return bytes.fromhex(v['$bytes_hex'])
        if set(v)=={'$tuple'}:
            return tuple(untransport(x) for x in v['$tuple'])
        return {k:untransport(x) for k,x in v.items()}
    if type(v) is list:
        return [untransport(x) for x in v]
    return v


def unpack_blob(b):
    assert b['encoding']=='zlib-base64'
    raw=zlib.decompress(base64.b64decode(b['data'],validate=True))
    assert type(raw) is bytes and len(raw)==b['bytes']
    assert hashlib.sha256(raw).hexdigest()==b['sha256']
    return raw


def same(actual,expected,path=()):
    assert type(actual) is type(expected),(path,type(actual).__name__,type(expected).__name__)
    if type(expected) is dict:
        assert set(actual)==set(expected),(path,'keys')
        for k in expected:same(actual[k],expected[k],path+(k,))
    elif type(expected) in (list,tuple):
        assert len(actual)==len(expected),(path,'length')
        for i,x in enumerate(expected):same(actual[i],x,path+(i,))
    elif type(expected) is float:
        assert struct.pack('<d',actual)==struct.pack('<d',expected),(path,'float-bits')
    else:
        assert actual==expected,(path,'value')


def raw_mutation(base,mutation):
    if 'truncate' in mutation:return base[:mutation['truncate']]
    if 'append_hex' in mutation:return base+bytes.fromhex(mutation['append_hex'])
    p=mutation['patch'];b=bytearray(base);replacement=bytes.fromhex(p['hex'])
    b[p['offset']:p['offset']+len(replacement)]=replacement
    if p['rehash_sections']:
        for i in range(8):
            d=256+64*i;off,n=struct.unpack_from('<QQ',b,d+8)
            b[d+24:d+56]=hashlib.sha256(b[off:off+n]).digest()
    return bytes(b)


def run(codec,corpus):
    counts=dict(unique_bases=len(corpus['bases']),unique_byte_negatives=len(corpus['byte_negatives']),
                encode_calls=0,decode_calls=0,check_calls=0,getter_calls=0,callback_exception_cases=0,
                value_refusal_cases=0,caller_mutation_cases=0,subject_methods=4)
    byid={b['id']:b for b in corpus['bases']}
    measured={}
    errors=set(['TYPE_DOMAIN','SCHEMA_KEYS','INTEGER_DOMAIN','SIZE_CAP','OVERFLOW','MAGIC_VERSION',
                'RESERVED_NONZERO','SECTION_LAYOUT','SECTION_DIGEST','TRAILING_BYTES','ENUM_DOMAIN',
                'ATOM_DOMAIN','STATE_CONTRADICTION','QUERY_SPAN','PATH_DOMAIN','MODULE_GRAPH','ROLE_CAPTURE',
                'CLOCK_DOMAIN','DIAGNOSTIC_LAYOUT','REFERENCE_DOMAIN','UNENCODABLE_RAW','LEGACY_NOT_REPRESENTABLE','UNISSUED_ARTIFACT'])
    def invoke(which,value,check):
        counts[which+'_calls']+=1
        def checked():
            counts['check_calls']+=1
            return check()
        return getattr(codec,which+'_ledger')(value,check=checked)
    def value_of(b):return untransport(json.loads(unpack_blob(b['semantic_value'])))
    def error_surface(err,raw=None,required=None):
        assert type(err.code) is str and err.code in errors
        if required is not None:assert err.code==required,(err.code,required)
        assert err.offset is None or type(err.offset) is int and raw is not None and 0<=err.offset<=len(raw)
        assert type(err.path) is tuple
        assert all(type(x) is str or type(x) is int and x>=0 for x in err.path)
        # Diagnostics cannot be changed through their public fields.
        for key in ('code','offset','path'):
            previous=getattr(err,key)
            try:setattr(err,key,previous)
            except (AttributeError,TypeError):pass
            else:raise AssertionError('mutable FormatError.'+key)
    def refusal(which,v,raw=None,required=None):
        try:invoke(which,v,lambda:None)
        except codec.FormatError as err:error_surface(err,raw,required)
        else:raise AssertionError('invalid data accepted')

    class Tests(unittest.TestCase):
        def test01_literal_encode_decode_and_anchors(self):
            for b in corpus['bases']:
                raw=unpack_blob(b['raw'])
                if not b['expected']['accepted']:
                    refusal('decode',raw,raw,b['expected']['required_code'])
                    continue
                v=value_of(b);calln=[0]
                def check():calln[0]+=1
                actual=invoke('encode',v,check);measured.setdefault('encode',calln[0])
                assert type(actual) is bytes and actual==raw,b['id']
                for a in b['anchors']:
                    x=bytes.fromhex(a['hex']);assert actual[a['offset']:a['offset']+len(x)]==x
                calln[0]=0;obj=invoke('decode',raw,check);measured.setdefault('decode',calln[0])
                before=counts['check_calls'];d=obj.to_dict();counts['getter_calls']+=1;same(d,v)
                r1=obj.to_bytes();r2=obj.to_bytes();counts['getter_calls']+=2
                assert type(r1) is bytes and r1==raw and r1 is r2
                d['header']['origin_data_id']=0;d['calls'][0]['flags']['INVOKED']=False
                same(obj.to_dict(),v);counts['getter_calls']+=1
                assert counts['check_calls']==before
                if v['header']['profile']=='UNQUALIFIED_FRAGMENT':
                    assert d['files'][0]['expected_size'] is None

        def test02_byte_negative_expansions(self):
            cache={}
            for m in corpus['byte_negatives']:
                base=cache.setdefault(m['base'],unpack_blob(byid[m['base']]['raw']))
                raw=raw_mutation(base,m)
                assert len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256']
                refusal('decode',raw,raw,m['expected']['required_code'])

        def test03_strict_types_and_detached_mutation(self):
            baseline=value_of(byid['fragment_01_observed']);raw=unpack_blob(byid['fragment_01_observed']['raw'])
            bad=[]
            x=copy.deepcopy(baseline);x['extra']=None;bad.append((x,'SCHEMA_KEYS'))
            x=copy.deepcopy(baseline);x['header']['origin_data_id']=True;bad.append((x,None))
            x=copy.deepcopy(baseline);x['calls'][0]['input_handle_atom']={'tag':'NULL','value':None};bad.append((x,'ATOM_DOMAIN'))
            x=copy.deepcopy(baseline);x['calls'][0]['error_definition_atom']={'tag':'DEFINEDNESS','value':True}
            x['calls'][0]['flags'].update(ERROR_DEFINITION_OBSERVED=True,ERROR_DEFINED=True);bad.append((x,'STATE_CONTRADICTION'))
            x=copy.deepcopy(baseline);x['queries']=bytearray();bad.append((x,'TYPE_DOMAIN'))
            x=copy.deepcopy(baseline);x['module_edges']=[];bad.append((x,'TYPE_DOMAIN'))
            for clock in (float('nan'),float('inf'),float('-inf')):
                x=copy.deepcopy(baseline);x['header']['start_clock']={'tag':'F64','value':clock};bad.append((x,'CLOCK_DOMAIN'))
            x=copy.deepcopy(baseline);x['header']['origin_data_id']=1<<100;bad.append((x,None))
            hooks=[]
            class Meta(type):
                def __eq__(cls,other):hooks.append('metaclass-eq');return False
            class I(int,metaclass=Meta):
                def __int__(self):hooks.append('int');return 1
                def __index__(self):hooks.append('index');return 1
                def __repr__(self):hooks.append('repr');return '1'
            class D(dict):
                def items(self):hooks.append('items');return super().items()
                def __iter__(self):hooks.append('dict-iter');return super().__iter__()
            class L(list):
                def __iter__(self):hooks.append('list-iter');return super().__iter__()
            x=copy.deepcopy(baseline);x['header']['origin_data_id']=I(1);bad.append((x,None))
            bad.append((D(baseline),'TYPE_DOMAIN'))
            x=copy.deepcopy(baseline);x['files']=L(x['files']);bad.append((x,'TYPE_DOMAIN'))
            for x,code in bad:
                refusal('encode',x,None,code);counts['value_refusal_cases']+=1
                assert hooks==[],hooks
            for x in (bytearray(raw),memoryview(raw)):
                refusal('decode',x,None,'TYPE_DOMAIN');counts['value_refusal_cases']+=1
            # Mutation at check2 occurs AFTER structural capture, not before it.
            x=copy.deepcopy(baseline);n=[0]
            def mutate_after_capture():
                n[0]+=1
                if n[0]==2:x['header']['origin_data_id']=99;x['calls'][0]['flags']['STOPPED']=True
                return False
            out=invoke('encode',x,mutate_after_capture);counts['caller_mutation_cases']+=1
            assert n[0]>=3 and out==raw
            assert measured['encode']>=3 and measured['decode']>=3

        def test04_callback_identity_and_cached_getters(self):
            b=byid['fragment_01_observed'];raw=unpack_blob(b['raw']);v=value_of(b)
            factories=[lambda:Exception('stop'),lambda:RuntimeError('stop'),lambda:TimeoutError('stop'),
                       lambda:UnicodeError('stop'),lambda:UnicodeDecodeError('utf-8',b'\xff',0,1,'stop'),
                       lambda:MemoryError('stop'),lambda:RecursionError('stop'),lambda:KeyboardInterrupt('stop'),
                       lambda:SystemExit('stop'),lambda:GeneratorExit('stop'),lambda:StopIteration('stop')]
            for which,data in [('encode',v),('decode',raw)]:
                # Sites are actual callback counts from the same valid literal,
                # not fixed implementation details or a copied no-op guard.
                total=measured[which]
                for position in (1,(total+1)//2,total):
                    for make in factories:
                        stop=make();n=[0]
                        def check():
                            n[0]+=1
                            if n[0]==position:raise stop
                            return False
                        try:invoke(which,data,check)
                        except BaseException as seen:assert seen is stop
                        else:raise AssertionError('check stop swallowed')
                        counts['callback_exception_cases']+=1
                        assert n[0]==position
            # False return values supply no eligibility authority.
            obj=invoke('decode',raw,lambda:False)
            before=counts['check_calls'];same(obj.to_dict(),v);counts['getter_calls']+=1
            assert obj.to_bytes()==raw;counts['getter_calls']+=1
            assert counts['check_calls']==before
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    return dict(status='PASS' if result.wasSuccessful() else 'FAIL',methods=result.testsRun,
                failures=[{'test':str(t),'traceback':x} for t,x in result.failures],
                errors=[{'test':str(t),'traceback':x} for t,x in result.errors],counts=counts,
                observed_valid_check_sites=measured,transcript=stream.getvalue(),
                qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']})
