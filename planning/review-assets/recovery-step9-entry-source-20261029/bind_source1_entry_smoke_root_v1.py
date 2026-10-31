"""Authorize one diagnostic entry against unchanged, known-failing Source1."""
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
def pin(name,digest):
    path=H/name;raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==digest,name
    return dict(path=str(path.resolve()),bytes=len(raw),sha256=digest)
peer=pin('ENTRY-SOURCE1-SMOKE-STATIC-REVIEW-v1.json','e0658f511582d617fb07580c30c662f5102248774dd7ec6146f5a5cc2782942a')
freeze=pin('ENTRY-INITIAL-REGRESSION-FREEZE-v1.json','4fc87eec8904b341d3abdfc538d682cdfb149cf8ec3bc161d9b836c2ca0f639f')
preparation=pin('ENTRY-INITIAL-REGRESSION-PREPARATION-v1.json','88ee40834682483046ad053a0cedbaac63a0e5ca7e04f672f0f705ea941f567c')
binding=json.loads((H/'ENTRY-SOURCE1-SMOKE-BINDING-OUTLINE-v1.json').read_bytes())
for p in [binding['inputs'],binding['source_pause'],*binding['source_map'].values(),*binding['harness'].values()]:
    raw=Path(p['path']).read_bytes()
    assert len(raw)==p['bytes'] and hashlib.sha256(raw).hexdigest()==p['sha256']
assert binding['preparation']==preparation
scope=dict(schema_version=1,status='ROOT_AUTHORIZED_ONE_SOURCE1_DIAGNOSTIC_ENTRY_EXPECTED_FAILURE',
    static_smoke_peer=peer,prefixed_regressions_freeze=freeze,preparation=preparation,
    source_pause_sha256='5594746b7d9687a7a386f4188564726f8ab000f1ec4ba38e557b7696373687fb',
    execution='Run frozen6e454c6b once. Load only the exact new kernel as pre-entry TCB, attempt test01 ordinary entry exactly once, and stop on the constructor invoke/invoke_reserved failure. This scope intentionally observes a known source HOLD and is not source acceptance.',
    deeper_checks='test02 journal finalization and test03 staged scalar/cache assertions were authored before correction; they must remain NOT_REACHED here. No alias, repaired class, partial Core fabrication, retry or old owner construction.',
    boundaries='Original real60s cooperative smoke timer. Controlled original entry clock and exclusive attempt/proof. Retain original error/trace frames/clock/registered state and zero/nonzero actual calls honestly, including any earlier setup error. No hard callback-free watchdog guarantee.',
    not_authorized=['full32/53 or native25 run','source correction before retained failure','native/compiler/SDK/FFI/model actions','original/protected targets','paid calls or downloads','app/default changes'],
    qualification=False,provider_spend_usd=0)
path=H/'ENTRY-SOURCE1-SMOKE-EXECUTION-SCOPE-v1.json'
for name in ('ENTRY-SOURCE1-SMOKE-ATTEMPT-v1.json','ENTRY-SOURCE1-SMOKE-PROOF-v1.json'):
    assert not(H/name).exists(),name
with path.open('x',encoding='utf-8',newline='\n')as out:
    json.dump(scope,out,sort_keys=True,indent=2);out.write('\n')
binding['status']='AUTHORIZED_SOURCE1_ENTRY_SMOKE_ONLY'
binding['execution_scope']=pin(path.name,hashlib.sha256(path.read_bytes()).hexdigest())
bpath=H/'ENTRY-SOURCE1-SMOKE-BINDING-v1.json'
with bpath.open('x',encoding='utf-8',newline='\n')as out:
    json.dump(binding,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(dict(scope_sha256=binding['execution_scope']['sha256'],binding_sha256=hashlib.sha256(bpath.read_bytes()).hexdigest())))
