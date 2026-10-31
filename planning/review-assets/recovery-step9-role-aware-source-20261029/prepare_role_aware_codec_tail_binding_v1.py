"""Publish the exclusive scoped tail binding; never load or test subjects."""
import ast
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
P=H.parent/'recovery-step9-role-aware-producer-20261029'


def pin(p):
    b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def js(p):return json.loads(p.read_bytes())
def pub(n,v):
    b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
    with (H/n).open('xb') as f:f.write(b)
    return pin(H/n)


def main():
    scope=pin(H/'ROLE-AWARE-V2-NEGATIVE-TAIL-SCOPE-v1.json')
    assert scope['sha256']=='ad679f4a4555e3456f808d1b8b47a4570eedab4bd8d2dea10efd93a9df117e25'
    previous=js(H/'ROLE-AWARE-INDEPENDENT-CODEC_FIRST-SOURCE-BINDING-v5.json')
    names=['role_ledger_codec_v2','role_owner_v2','role_file_ports_v2','continue_role_verification_v2']
    assert previous['source_module_load_order']==names and set(previous['source_pins'])==set(names)
    proof=pin(H/'ROLE-AWARE-INDEPENDENT-CODEC_FIRST-PROOF-v5.json')
    outcome=js(Path(proof['path']))
    assert proof['sha256'].startswith('8184541d')
    assert outcome['codec_forwarding']['actual_decode_calls']==176
    corpus_pin=previous['dependencies']['literal_corpus']
    assert corpus_pin['sha256']=='8ae5b333a8955b2359b4c267d0ce586000959355a7c3a11bc5523ccd00f168a7'
    corpus=js(Path(corpus_pin['path']));tail=corpus['byte_negatives'][100:225]
    assert len(tail)==125 and len({m['id'] for m in tail})==125
    helper=pin(H/'probe_role_aware_codec_disjoint_tail_v1.py')
    tree=ast.parse(Path(helper['path']).read_bytes())
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='T' and n.func.attr=='run' for n in ast.walk(tree))
    hps=dict(common_runner=pin(H/'run_role_aware_independent_v5.py'),
        legacy_adapter=previous['harness_pins']['legacy_adapter'],codec_tests=previous['harness_pins']['codec_tests'])
    assert hps['common_runner']['sha256']=='ba767e126b1a07f215095f9c6e13d573b486b7df909537f4d85981df66b41d9a'
    assert hps['codec_tests']['sha256']=='a3051f08375fd412d49a9a69ce180b65de69214500c787f9562a23cc3859beea'
    deps=dict(literal_corpus=corpus_pin,format_schema=previous['dependencies']['format_schema'],
        prior_v2_codec_result=proof,prior_v2_codec_binding=pin(H/'ROLE-AWARE-INDEPENDENT-CODEC_FIRST-SOURCE-BINDING-v5.json'),
        failure_localization=pin(H/'ROLE-AWARE-CODEC-V2-FAILURE-LOCALIZATION-v1.json'),
        runner_static_peer=pin(H/'ROLE-AWARE-V2-RUNNERS-INDEPENDENT-STATIC-REVIEW-v1.json'))
    binding=pub('ROLE-AWARE-CODEC-DISJOINT-TAIL-BINDING-v1.json',dict(schema_version=1,status='BOUND_SINGLE_DISJOINT_TAIL_DIAGNOSTIC_FOR_ROOT_EXECUTION',
        mode='DISJOINT_BYTE_NEGATIVE_TAIL_100_224_V2',start_index=100,stop_index_exclusive=225,max_decode_calls=125,deadline_seconds=30,
        source_module_load_order=names,source_pins=previous['source_pins'],source_pause=previous['source_pause'],source_scope=previous['source_scope'],
        execution_scope=scope,harness_pins=hps,dependencies=deps,actual_helper=helper,
        no_replay='Indices0..99, positive base decode, four-methodsuite, V1, legacy and producer extensions are excluded. Each selected malformed raw byte string is forwarded at most once.',
        retention='Fixed exclusive attempt/proof filenames; all prior V5 first results retained.',
        source_input='Only raw bytes plus a case-independent callback reach the actual decode function. Labels/expected codes remain in diagnostic metadata.'))
    outline=pub('ROLE-AWARE-CODEC-DISJOINT-TAIL-BINDING-OUTLINE-v1.json',dict(schema_version=1,binding=binding,helper=helper,
        allowed_index_range=[100,224],planned_source_decode_calls=125,execution_owner='Root only after its final static review',
        attempt_basename='ROLE-AWARE-CODEC-DISJOINT-TAIL-ATTEMPT-v1.json',proof_basename='ROLE-AWARE-CODEC-DISJOINT-TAIL-PROOF-v1.json',
        activity=dict(subject_imports=0,subject_calls=0,V1_replays=0,full_suite_replays=0)))
    prep=pub('ROLE-AWARE-CODEC-DISJOINT-TAIL-PREPARATION-v1.json',dict(schema_version=1,status='EXECUTABLE_SCOPED_PROBE_PREPARED_UNEXECUTED',
        helper=helper,binding=binding,outline=outline,author=pin(Path(__file__).resolve()),source_pause=previous['source_pause'],
        source_pins_metadata=previous['source_pins'],harness_pins=hps,dependencies=deps,execution_scope=scope,
        selected_indices=list(range(100,225)),selected_ids=[m['id'] for m in tail],selected_raw_sha256=[m['sha256'] for m in tail],
        planned_calls=125,actual_calls_now=0,prior_decode_accounting=dict(base_decodes=40,earlier_negatives=100,type_refusals=2,callback_decodes=34,total=176),
        guards=['All four exact V2 sources load once through unchanged closed loader/audit.',
            'One original30s cooperative deadline starts before binding/hash/import; existing facade checks actual calls/original callbacks.',
            'Common after-loop and final before-publication late veto; no hard callback-free hang guarantee.',
            'Every row starts unknown; actual rejection/code/surface/correctness and live forwarding delta retained independently.',
            'Wrong rejection codes are retained and do not stop the finite tail; deadline/user interruption/audit denial stops new dispatch and leaves explicit unknown suffix.',
            'No T.run call, no earlier negative replay, no accepted positive base decode, no source/oracle edit or scientific qualification.'],
        activity=dict(subject_sources_read_or_hashed=0,subject_imports=0,subject_calls=0,original_payload_native_physical_operations=0),
        pending=['Native narrow helper/binding static review','Root invokes the single probe and retains first actual result'],
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(preparation=prep,binding=binding,outline=outline,helper=helper)))


if __name__=='__main__':main()
