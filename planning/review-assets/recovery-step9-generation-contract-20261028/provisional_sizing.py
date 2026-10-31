"""Formal-structure sizing only; not a native grammar parser or production renderer."""
from collections import Counter
from functools import lru_cache
import hashlib
from itertools import product
import json
from pathlib import Path
import random
import string

HERE=Path(__file__).resolve().parent


def wire_literal(value):
    wire=json.dumps(value,ensure_ascii=False).replace('<','\\u003c')
    return json.dumps(wire,ensure_ascii=False)


class Lengths:
    def __init__(self):self.rules={'eps':'""'}
    def exact(self,kind,n):
        if n==1:return {'a':'char-a','w':'char-w','n':'char-n'}[kind]
        key=f'{kind}e{n}'
        if key in self.rules:return key
        assert n>1 and n&(n-1)==0
        half=n//2
        a,w,b=(self.exact(k,half) for k in ('a','w','n'))
        self.rules[key]=f'{a} {a}' if kind=='a' else f'{w} {w}' if kind=='w' else f'{b} {a} | {w} {b}'
        return key
    def bounded(self,kind,n):
        if n==0:return None if kind=='n' else 'eps'
        key=f'{kind}r{n}'
        if key in self.rules:return key
        m=1<<(n.bit_length()-1);r=n-m
        small=self.bounded(kind,m-1)
        alternatives=[small] if small else []
        alternatives.append(f'{self.exact(kind,m)} {self.bounded("a",r)}')
        if kind=='n':
            tail=self.bounded('n',r)
            if tail:alternatives.append(f'{self.exact("w",m)} {tail}')
        self.rules[key]=' | '.join(alternatives)
        return key
    def source(self):return ''.join(f'{name} ::= {body}\n' for name,body in self.rules.items())


def pairs(k):
    rules=[];counter=0
    def node(lo,hi):
        nonlocal counter
        if hi-lo==1:return wire_literal('Q'+str(lo)),None
        index=counter;counter+=1;mid=(lo+hi)//2
        left,lp=node(lo,mid);right,rp=node(mid,hi)
        a,p=f'i{index}',f'p{index}'
        rules.append(f'{a} ::= {left} | {right}\n')
        alternatives=[v for v in (lp,rp,f'{left} "," {right}',f'{right} "," {left}') if v]
        rules.append(f'{p} ::= '+ ' | '.join(alternatives)+'\n')
        return a,p
    all_ids,distinct=node(0,k)
    rules.append(f'refs ::= "[" ({all_ids}'+(' | '+distinct if distinct else '')+') "]"\n')
    return ''.join(rules),len(rules)


def concatenate(left,right):
    result=Counter()
    for x,xc in left.items():
        for y,yc in right.items():result[x+y]+=xc*yc
    return result


@lru_cache(None)
def exact_language(kind,n):
    if n==1:return Counter({'W':1,'N':1}) if kind=='a' else Counter({'W' if kind=='w' else 'N':1})
    half=n//2
    if kind in ('a','w'):return concatenate(exact_language(kind,half),exact_language(kind,half))
    return concatenate(exact_language('n',half),exact_language('a',half))+concatenate(exact_language('w',half),exact_language('n',half))


@lru_cache(None)
def bounded_language(kind,n):
    if n==0:return Counter() if kind=='n' else Counter({'':1})
    m=1<<(n.bit_length()-1);r=n-m
    result=bounded_language(kind,m-1)+concatenate(exact_language(kind,m),bounded_language('a',r))
    if kind=='n':result+=concatenate(exact_language('w',m),bounded_language('n',r))
    return result


def size(source):return dict(raw_gbnf_bytes=len(source.encode()),json_string_bytes=len(json.dumps(source,ensure_ascii=False).encode()))


checks=[]
for n in range(9):
    for kind in ('a','n'):
        got=bounded_language(kind,n)
        expected={''.join(s) for length in range(n+1) for s in product('WN',repeat=length)
            if kind=='a' or 'N' in s}
        assert set(got)==expected and all(v==1 for v in got.values())
        checks.append(dict(kind=kind,n=n,words=len(got),maximum_derivations=max(got.values(),default=0)))
lengths=Lengths()
for n in (1800,512):lengths.bounded('n',n)
length_source=lengths.source()
pair_sizes=[]
for k in (1,2,16,64,256):
    source,count=pairs(k);pair_sizes.append(dict(catalog=k,rules=count,**size(source)))
rng=random.Random(20261028)
scenarios=[]
for label,texts in [('256_short_unique',[f'T{i}' for i in range(256)]),
    ('256_independent_1800_ascii',[''.join(rng.choices(string.ascii_letters,k=1800)) for _ in range(256)])]:
    assert all(len(t)<=1800 for t in texts)
    literals=''.join(f'l{i} ::= {wire_literal(t)}\n' for i,t in enumerate(dict.fromkeys(texts)))
    scenarios.append(dict(label=label,literal_rules=len(set(texts)),decoded_characters=sum(map(len,texts)),
        original_text_list_json_bytes=len(json.dumps(texts,separators=(',',':')).encode()),**size(literals)))
report=dict(schema_version=1,role='provisional_formal_structure_only',
    helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    bounded_nonblank=dict(bounds=[1800,512],rules=len(lengths.rules),**size(length_source)),
    reference_pair_structure=pair_sizes,literal_scenarios=scenarios,
    finite_binary_alphabet_consistency=checks,
    excluded_from_sizes=['Unicode/escape character atoms','response/object/list productions','source-report ID/literal binding productions',
        'complete original prompt','complete serialized HTTP payload'],
    native_grammar_parsed=False,production_module_implemented=False,model_calls=0,servers=0)
with (HERE/'PROVISIONAL-SIZING.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(dict(bounded_nonblank=report['bounded_nonblank'],pairs_256=pair_sizes[-1],
    literal_scenarios=scenarios,finite_consistency_checks=len(checks))))
