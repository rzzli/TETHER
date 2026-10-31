"""Bind only exact reviewed metadata; imports no subject or harness module."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def pin(path):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT):raise RuntimeError('review asset outside repository')
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def save_new(path,value):
    with path.open('xb')as stream:
        stream.write((json.dumps(value,indent=2,sort_keys=True)+'\n').encode())


def main():
    peer=pin(sys.argv[1])
    if peer['sha256']!=sys.argv[2]:raise RuntimeError('reviewed combined peer changed')
    outline_path=HERE/'ENTRY-E08-SUITE-BINDING-OUTLINE-v2.json'
    outline_pin=pin(outline_path)
    if outline_pin['sha256']!='95fdb96dec4a515661b58f5d6a349b41935ae64fdf4f32ca52294be9cc93cfee':
        raise RuntimeError('frozen outline changed')
    binding=json.loads(outline_path.read_bytes())
    for value in [binding['source_pause'],binding['inputs'],binding['preparation'],
                  *binding['source_map'].values(),*binding['harness'].values()]:
        if pin(value['path'])!=value:raise RuntimeError('changed paused source/harness/metadata')
    if binding['source_pause']['sha256']!='c38df4b3133133805e7a13c30e2d65d21748e4c1ce1a320929c0871f05dfab67':
        raise RuntimeError('genuine Source4 pause anchor required')
    freeze=pin(HERE/'ENTRY-E08-SUITE-FREEZE-v2.json')
    if freeze['sha256']!='cf4d6aac69665e5829f00004225058028d6af67792e31429b859323e460fc36d':
        raise RuntimeError('frozen suite preparation changed')
    for path in binding['consumed_paths']:
        if Path(path).exists():raise RuntimeError('suite already consumed; no replay')
    scope=dict(schema_version=1,status='ROOT_AUTHORIZED_ONE_SOURCE4_E08_122_SUITE',
               source_pause=binding['source_pause'],preparation=binding['preparation'],
               inputs=binding['inputs'],freeze=freeze,outline=outline_pin,independent_combined_peer=peer,
               execution='Run the exact frozen Source4 runner once across CORRECTIONS5/LITERALS52/INTEGRATION15/CAUSAL50. Use only genuine entry-issued objects and unchanged frozen expected data. Retain every first action/cleanup/evidence outcome and existing raw/snapshot/policy facts.',
               deadline_seconds=60,
               deadline_boundary='One real cooperative timer from setup through per-world evidence persistence/final veto. Final proof writing/startup/exit are outside or unmeasured. No automatic retry, hard callback-free timeout or cap increase.',
               literal_boundary='A genuine metadata report is classified separately from a later FileSpec/captured-plan refusal. Policy-only contexts are not full helper-plan execution. No expected refusal counts as source PASS unless the exact original refusal and prescribed absence/identity observations are asserted.',
               generated_E32=dict(authorized=True,bulk_bytes=3991999872,
                                  recipe='procedural periodic bytes00..ff at offset0',
                                  sha256='5321e7c0efc028f133e7a6690e5c5bdf0344dded80904eb416fddb7ed0c2b1fb',
                                  read_buffer_bytes=1048576,bulk_capture_assembly=False,original_payload_reads=False),
               trusted_code_boundary='Kernel145042B is explicit pre-entry TCB; actual captured helper prefix99000B. Same original Core/Origin/nonce/registry/facades and budget must remain; data hashes/reports are not live authority.',
               preservation='Source3 five corrections and50/3 proof remain untouched; historical E16 constructor invocations stay excluded/deferred. This is a separately declared first Source4 execution, not repair/replay of prior experiments.',
               not_authorized=['frozen code/harness/golden edits','C++ compilation/SDK/FFI/target-native/model execution',
                               'native25 execution or positive native/physical capability',
                               'original/protected clinical or model payload reads','downloads or paid calls',
                               'application/default/profile/cap/downloader/monitor changes'],
               provider_spend_usd=0,qualification=False)
    scope_path=HERE/'ENTRY-E08-SUITE-EXECUTION-SCOPE-v1.json'
    save_new(scope_path,scope)
    binding['status']=binding['required_execution_status']
    binding['execution_scope']=pin(scope_path)
    binding['freeze']=freeze
    binding['allow_large_stream']=True
    binding_path=HERE/'ENTRY-E08-SUITE-BINDING-v1.json'
    save_new(binding_path,binding)
    print(json.dumps(dict(scope=pin(scope_path),binding=pin(binding_path))))


if __name__=='__main__':
    main()
