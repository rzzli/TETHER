"""Four bounded independent pure probes; no old run, payload or native calls."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import types

HERE=Path(__file__).resolve().parent
OUT=HERE/'UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-AFTER-v2.json'
EXPECTED={
    'unicode_observations_v1.py':'58d6a62fe6a9416c94e5637b615886cecd90bc78ef1559f05f7d1d1ebd6e32c0',
    'unicode_observations_v2.py':'47c7cc1fc3889e32c5a3ff3efff50425ef208a041a308f5a447872bd788414b6',
    'unicode_observation_tables_v1.py':'009e46ee19e945575472afb5105e88fe708a38b30c2f1014bbf8f6549d76786d',
    'unicode_observation_test_support_v2.py':'4d072b5e49dedc51a8b275b6bd39000075864828855a8bee7fc54e11db1c7de1',
    'UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v3.json':'66a57c7b3316e6791dbdcb645ca968338aa61f19f68962964bf96126c9d6ca70',
    'UNICODE-OBSERVATIONS-IMPLEMENTATION-FREEZE-v2.json':'f8afdc057976ac871bb8d27b75771a0c3332c66a17869e48be68006ded02c1e6',
    'UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-PEER-v1.json':'5ebd57eff292ecf5c49abf7ae7d41c60598721f87c2673460cc53c59da1a96be',
    'UNICODE-OBSERVATIONS-ROOT-BOUNDARY-AFTER-v2.json':'628834ca137cedfb11dfdd9ca29e3ec2cd3c05a892706971d62912bac4d08a2e',
}

def pin(name):
    p=HERE/name;raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def load(name,modulename,expected):
    raw=(HERE/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
    module=types.ModuleType(modulename);module.__file__=str(HERE/name);sys.modules[modulename]=module
    exec(compile(raw,str(HERE/name),'exec'),module.__dict__);return module

def main():
    started=time.monotonic();assert not OUT.exists()
    before={name:pin(name) for name in EXPECTED}
    assert all(before[name]['sha256']==value for name,value in EXPECTED.items())
    S=load('unicode_observation_test_support_v2.py','unicode_observation_peer_support_v2',EXPECTED['unicode_observation_test_support_v2.py'])
    U=load('unicode_observations_v2.py','unicode_observations_peer_under_test_v2',EXPECTED['unicode_observations_v2.py'])
    def check():
        if time.monotonic()-started>30:raise TimeoutError('Bounded independent pure probe30s')
    outcomes=[]
    # Same data-error family as the independently identified v1 boundary.
    raw=b'{"schema_version":'+b'9'*5000+b'}\n'
    try:S.invoke(U.observe,raw,S.PROFILE,S.bindings(U),check=check)
    except U.ObservationError as error:
        assert error.reason=='JSON_data';outcomes.append(dict(id='integer_conversion_is_bounded_data_error',passed=True,reason=error.reason,validated_rows=error.validated_prefix['validated_rows']))
    else:raise AssertionError('Giant integer did not produce bounded data error')
    # Preserve a valid marker-only negative before making the new-work mutation.
    scenario=next(row for row in S.F['scenarios'] if row['id']=='marker_only_after_complete_rows')
    raw,marker=S.materialize(scenario)
    value=S.invoke(U.observe,raw,S.PROFILE,S.bindings(U),failure_marker=marker,check=check).to_dict()
    assert value['classification']=='complete_negative_consistent' and value['validated_case_rows']==84
    outcomes.append(dict(id='valid_marker_only_negative_is_retained',passed=True,classification=value['classification']))
    m=json.loads(marker);m['native_call_counters']['llama_tokenize']['attempted']+=1;m['native_call_counters']['llama_tokenize']['returned']+=1
    state=m['native_state'];state['total_attempted']+=1;state['total_returned']+=1
    state.update(last_attempt='llama_tokenize',last_return='llama_tokenize',last_return_kind=2,last_scalar=1,last_tokenize_return=1)
    try:S.invoke(U.observe,raw,S.PROFILE,S.bindings(U),failure_marker=S.canonical(m)+b'\n',check=check)
    except U.ObservationError as error:
        assert error.reason=='failure_after_completed_phase_new_work'
        assert error.validated_prefix['validated_case_rows']==84 and error.validated_prefix['terminal_negative_seen'] is True
        outcomes.append(dict(id='marker_only_post_normal_tokenize_rejected',passed=True,reason=error.reason,validated_cases=84))
    else:raise AssertionError('Extra marker-only work laundered into complete source-negative')
    # A next-declared-prefix creation with no return remains unknown/partial.
    vector_path=HERE/'UNICODE-OBSERVATIONS-PREFIX-PHASE-VECTOR-v1.json';v=json.loads(vector_path.read_text(encoding='utf-8'))
    partial=S.invoke(U.observe,bytes.fromhex(v['raw_hex']),S.PROFILE,S.bindings(U),failure_marker=None if v['failure_marker_hex'] is None else bytes.fromhex(v['failure_marker_hex']),check=check).to_dict()
    assert partial['classification']=='partial_observation' and partial['validated_case_rows']==84
    assert partial['source_cleanup_consistent'] is False and partial['terminal_source_phase']=='declared_next_prefix'
    counts=partial['final_native_call_counters'];state=partial['final_native_state']
    assert counts['llama_sampler_init_grammar']['attempted']-counts['llama_sampler_init_grammar']['returned']==1
    assert counts['llama_model_free']['attempted']==counts['llama_backend_free']['attempted']==0
    assert state['model_owned'] is state['backend_owned'] is True
    outcomes.append(dict(id='declared_prefix_nonreturn_retained_partial',passed=True,classification=partial['classification'],validated_cases=84,pending_sampler_init=1,dependent_frees=0))
    assert S.DENIALS==[]
    old=ast.parse((HERE/'unicode_observations_v1.py').read_text(encoding='utf-8'))
    new=ast.parse((HERE/'unicode_observations_v2.py').read_text(encoding='utf-8'))
    named=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
    left,right=named(old),named(new);assert left.keys()==right.keys()
    changed=[name for name in left if left[name]!=right[name]];assert changed==['_Reader','observe']
    oldr=next(n for n in old.body if isinstance(n,ast.ClassDef) and n.name=='_Reader')
    newr=next(n for n in new.body if isinstance(n,ast.ClassDef) and n.name=='_Reader')
    methods=lambda node:{n.name:ast.dump(n,include_attributes=False) for n in node.body if isinstance(n,ast.FunctionDef)}
    lm,rm=methods(oldr),methods(newr)
    changed_methods=[name for name in lm if lm[name]!=rm[name]]
    assert changed_methods==['parse','failure_row','process','marker_record','finish'] and set(rm)-set(lm)=={'failure_tail'}
    assert all(pin(name)==value for name,value in before.items())
    record=dict(schema_version=1,status='passed',recorded_at_utc=datetime.now(timezone.utc).isoformat(),inputs=before,
        checker=pin(Path(__file__).name),prefix_vector=pin(vector_path.name),outcomes=outcomes,
        changed_named_top_level_ASTs=changed,changed_reader_methods=changed_methods,added_reader_methods=['failure_tail'],
        unchanged_reader_methods=[n for n in lm if n not in changed_methods],
        author_full_suite_rerun=False,probe_count=4,audit_denials=S.DENIALS,elapsed_seconds=time.monotonic()-started,
        scope='Exact new source/pure boundary probes and AST review only. Existing pinned pure matcher reused without original-source closure qualification.',
        SDK_native_payload_operations=0,old_run_operations=0,pack_file_created=False,profile_qualified=False,originals_authenticated=False,runtime_authorized=False)
    with OUT.open('x',encoding='utf-8',newline='\n') as out:json.dump(record,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(OUT.name),status='passed',probes=4)))

if __name__=='__main__':main()
