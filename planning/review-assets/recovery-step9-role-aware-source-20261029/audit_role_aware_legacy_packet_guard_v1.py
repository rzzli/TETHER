"""Retained-payload/source-text audit only; no subject or adapter execution."""
import ast
import collections
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
P=H.parent/'recovery-step9-role-aware-producer-20261029'


def pin(p):
    b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def js(p):return json.loads(p.read_bytes())


def main():
    proof=pin(H/'ROLE-AWARE-INDEPENDENT-LEGACY48_FIRST-PROOF-v6.json')
    assert proof['sha256']=='dc02853ad550319d50c8361aa073aa0d4ba4ee8577d3b2bc99dc6bf318565a84'
    data=js(Path(proof['path']));schema=js(P/'ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json')
    assert pin(P/'ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json')['sha256']=='b71cd8f49ccc8d4dc56b31915a3ed20465f58b08bb35b54df63a73a49e655b7a'
    const=schema['publication']['constants'];aliases=const['packet_kind'];mapping=const['packet_kind_to_artifact']
    assert aliases==['candidate','cleanup','failure','receipt','seal']
    assert all(mapping[x]==x+'.json' for x in aliases)
    text=(H/'role_aware_legacy_fixture_adapter_v1.py').read_text(encoding='utf-8')
    bad="if decoded['kind']!=kind+'.json' or decoded['status'] not in ('OBSERVED_COMPLETE','OBSERVED_NEGATIVE','INCOMPLETE'):r.violate('wrong new packet kind/status')"
    assert text.count(bad)==1
    assert text.index(bad)<text.index('  action_result=r.callback_actions(target)')
    calls=collections.Counter();packets=[];runs=[]
    for run in data['legacy_runs']:
        for rec in run['sink_records']:
            if not rec['target'].startswith('publish_'):continue
            raw=bytes.fromhex(rec['payload_hex']);packet=json.loads(raw)
            checks=dict(kind_alias=type(packet['kind']) is str and packet['kind'] in aliases and packet['kind']==rec['kind'],
                status=packet['status'] in const['status'],schema_version=type(packet['schema_version']) is int and packet['schema_version']==2,
                scope=packet['scope']==const['packet_scope'],keys=set(packet)==set(schema['publication']['packet_exact_keys']),
                canonical=(json.dumps(packet,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()==raw,
                qualification=set(packet['qualification'])==set(schema['publication']['nested']['qualification']) and all(x is False for x in packet['qualification'].values()))
            assert all(checks.values())
            assert packet['kind']!=rec['kind']+'.json'
            assert rec['returned'] is False and rec['acknowledged'] is False
            calls[(rec['target'],packet['kind'],packet['status'])]+=1
            packets.append(dict(history=run['id'],target=rec['target'],callback_kind=rec['kind'],wire_kind=packet['kind'],wire_status=packet['status'],
                raw_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),checks=checks,callback_clock=rec['clock'],
                return_observed=rec['returned'],acknowledged=rec['acknowledged'],scripted_callback_not_reached=True))
        runs.append(dict(id=run['id'],matched=run['matched'],fixture_difference_count=len(run['differences']),protocol_errors=run['protocol_errors'],
            violations=run['violations'],publication_attempts=sum(x['target'].startswith('publish_') for x in run['sink_records'])))
    assert len(runs)==48 and sum(x['matched'] for x in runs)==7
    unmatched=[r for r in runs if not r['matched']]
    assert len(unmatched)==41 and all(r['violations'] and set(r['violations'])=={'wrong new packet kind/status'} for r in unmatched)
    assert all(not r['protocol_errors'] for r in runs)
    assert len(packets)==89 and sum(r['fixture_difference_count']==0 for r in unmatched)==36
    focus=[]
    for row in data['same8_observations']:
        if not row['name'].startswith('known_late_') or not row['name'].endswith('_ACK'):continue
        kind=row['name'][len('known_late_'):-len('_ACK')]
        assert kind in ('candidate','cleanup','receipt','seal')
        assert row['origin']['now']==100 and row['primary_class']=='HarnessError'
        rec=row['publications'][kind]
        assert rec['return_observed'] is False and rec['acknowledged'] is False
        focus.append(dict(target=kind,actual_clock=row['origin']['now'],actual_primary=row['primary_class'],
            target_attempted=rec['attempted'],target_return_observed=rec['return_observed'],target_acknowledged=rec['acknowledged'],
            conclusion='Intended clock_set400/returned-ACK branch was blocked by the adapter; source late-ACK retention is not tested by this failed run.'))
    assert len(focus)==4
    report=dict(schema_version=1,status='FINITE_ACTUAL_HARNESS_DEFECT_CONFIRMED_SOURCE_ACK_ATTRIBUTION_HELD',
        proof=proof,schema=pin(P/'ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json'),adapter=pin(H/'role_aware_legacy_fixture_adapter_v1.py'),author=pin(Path(__file__).resolve()),
        finding=dict(id='PACKET_KIND_ALIAS_VERSUS_ARTIFACT_FILENAME',classification='HARNESS_DEFECT',
            normative_field='publication.constants.packet_kind',normative_aliases=aliases,separate_artifact_mapping=mapping,
            actual_guard=bad,causal_order='The guard executes before callback_actions, so it throws before the actual scripted clock/ACK or callback exception rule.',
            proposed_finite_correction='Compare packet.kind to the exact callback kind short alias, preserve status/schema/keys/qualification/size/canonical/DAG/clock/once-only guards and every frozen48 assertion. Root must choose any named correction.'),
        counts=dict(methods=9,histories_complete=48,histories_matched=7,histories_unmatched=41,unmatched_with_zero_fixture_differences=36,
            histories_protocol_errors=0,actual_retained_publication_packets=89,valid_alias_and_status_packets=89,blocked_before_callback_actions=89,
            focused_late_ACK_controls_unexercised=4),
        packet_groups=[dict(target=k[0],kind=k[1],status=k[2],count=v) for k,v in calls.items()],packets=packets,runs=runs,late_ACK_focus=focus,
        limits=['This audit checks retained literal packet framing/alias/status fields, not every nested semantic or future physical publication gate.',
            'The48 assertions and same8 remain unchanged; no failed run is relabeled a pass.',
            'No source ACK defect is demonstrated by a callback which never returned. Other source defects beyond this blocking boundary remain unknown until an authorized corrected execution.',
            'No new runner, adapter, source, corpus or fixture expectation was changed.'],
        source_unchanged=data['source_unchanged'],activity=dict(retained_data_and_static_harness_text_only=True,subject_imports=0,subject_calls=0,adapter_runs=0,
            four_method_suite_replays=0,legacy_replays=0,original_payload_native_physical_operations=0),
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']})
    out=H/'ROLE-AWARE-LEGACY-PACKET-GUARD-INDEPENDENT-REVIEW-v1.json'
    with out.open('xb') as f:f.write((json.dumps(report,sort_keys=True,indent=2)+'\n').encode())
    print(json.dumps(dict(report=pin(out),counts=report['counts'],finding=report['finding']['id'])))


if __name__=='__main__':main()
