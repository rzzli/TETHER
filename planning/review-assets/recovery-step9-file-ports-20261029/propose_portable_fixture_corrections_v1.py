"""Propose literal edits only. Frozen fixtures/source are never overwritten."""
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TARGET=HERE/'PORTABLE-FILE-PORTS-CORRECTION-PROPOSAL-v1.json'
IDS=('success_baseline','owned_open_identity','namespace_owned_journal_reserve_failure','read_hash','read_copy','read_short_read','write_short','write_flush_false','write_flush_unknown','seal_close_return_late','output_registry_normal','BOOL_ReadFile_2','BOOL_ReadFile_-1')


def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def main():
    assert not TARGET.exists()
    fixture=HERE/'FILE-PORTS-FIXTURES-v3.json';original=json.loads(fixture.read_text(encoding='utf-8'));by={x['id']:x for x in original['cases']};candidates=copy.deepcopy(by)
    for identity in IDS:
        case=candidates[identity]
        if identity=='namespace_owned_journal_reserve_failure':continue
        new=[];now=0
        for index,step in enumerate(case['script']):
            if step['kind']=='clock':now=step['now_ns']
            if step['kind']=='hook' and step['name']=='hash_update':new.append(dict(kind='clock',now_ns=now,raises=None,before_projection={}))
            new.append(copy.deepcopy(step))
            if step['kind']=='hook' and step['raises'] is None and step['name'] in ('hash_update','copy_bytes'):
                new.append(dict(kind='clock',now_ns=now,raises=None,before_projection={}))
            if step['kind']=='clock' and index>=1:
                api=case['script'][index-1]
                next_step=case['script'][index+1] if index+1<len(case['script']) else None
                if api['kind']=='api' and api['name']=='CreateFileW' and api['arguments']['desired_access']==2147483648 and api['outcome']['raise'] is None:
                    raw=api['outcome']['raw_return']['value']
                    if type(raw) is int and raw not in (0,2**64-1) and now<295000000000 and not(next_step and next_step['kind']=='hook' and next_step['name']=='log_append'):
                        new.append(dict(kind='hook',name='log_append',raises=None,before_projection={'slots.o0.open_state':'observed_owned'}))
        case['script']=new
    # Full reserve action has one coherent prefix independent of a later failure.
    baseline=candidates['success_baseline'];target=candidates['namespace_owned_journal_reserve_failure'];prefix=[]
    failure=next(s for s in by[target['id']]['script'] if s['kind']=='api' and s['name']=='CreateFileW')
    for index,step in enumerate(baseline['script']):
        prefix.append(copy.deepcopy(step))
        if step['kind']=='api' and step['name']=='CreateFileW' and step['arguments']['path'].endswith('\\journal.jsonl'):
            prefix[-1]['outcome']=copy.deepcopy(failure['outcome'])
            after=copy.deepcopy(baseline['script'][index+1]);after['before_projection']={'slots.j0.open_state':'known_failure_no_handle'};prefix.append(after);break
    target['script']=prefix
    expected=target['expected'];expected['known_write_bytes']=expected['write_hash_bytes']=expected['flushed_known_bytes']=len(b'fixture-reservation\n')
    r0=copy.deepcopy(by['success_baseline']['expected']['slots'][0]);j0=copy.deepcopy(expected['slots'][0]);expected['slots']=[r0,j0]
    for counter in ('api_attempts','api_returns'):expected[counter]={name:0 for name in expected[counter]}
    for step in prefix:
        if step['kind']=='api':expected['api_attempts'][step['name']]+=1;expected['api_returns'][step['name']]+=step['outcome']['raise'] is None
    expected_changes={
      'write_false_and_close_failure':{'primary':'false'},
      'owned_open_log':{'disposition':'incomplete_unknown'},
      'read_hash':{'disposition':'incomplete_unknown'},'read_copy':{'disposition':'incomplete_unknown'},
      'seal_close_return_late':{'primary':'hard_deadline'},
    }
    for identity,case in candidates.items():
        if case['required_vector']==14 and case['subcase'] in ('relative','\\\\server\\share','\\\\?\\D:\\'):
            expected_changes[identity]={'primary':'path_root'}
    for identity,changes in expected_changes.items():candidates[identity]['expected'].update(changes)
    patches=[]
    for identity,case in candidates.items():
        old=by[identity]
        if case!=old:
            old_script,new_script=old['script'],case['script']
            patches.append(dict(id=identity,script_changed=old_script!=new_script,old_script_steps=len(old_script),new_script_steps=len(new_script),new_script=new_script if old_script!=new_script else None,
                expected_field_changes={k:dict(before=old['expected'][k],proposed=v) for k,v in case['expected'].items() if old['expected'][k]!=v}))
    assert {p['id'] for p in patches if p['script_changed']}==set(IDS)
    result=dict(schema_version=1,status='PROPOSAL_ONLY_NOT_APPLIED_PENDING_ROOT_AND_PEER',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        inputs={p.name:pin(p) for p in [fixture,HERE/'FILE-PORTS-FIXTURE-CALLABLE-FREEZE-v2.json',HERE/'portable_file_ports_v1.py',HERE/'PORTABLE-FILE-PORTS-FIRST-BEHAVIORAL-PROOF-v1.json',HERE/'FILE-PORTS-ROOT-PRIMARY-WITNESS-v1.json']},author=pin(Path(__file__)),
        thirteen_script_case_ids=list(IDS),patches=patches,
        rationale={'fresh_clock_samples':'Insert real scripted clock calls before/after each hash update and after successful copy, at the same nondecreasing fictional time as the preceding sample. Preserve existing time advances and deadline crossings. No source guard is removed or turned into a cached check.',
        'noop_log':'Explicit no-op log_append after timely known-owned original open when no failing log hook was already present. The source invokes the hook unconditionally; it is not silently skipped by a test adapter.',
        'namespace_prefix':'The same reserve_namespace_and_journal action follows the same parent/leaf attributes and complete reservation-file prefix as baseline until the journal CreateFileW fails. Keep known partial reservation bytes/close and zero original reads; no case-selected shortcut.',
        'primary':'Preserve false as the original WriteFile failure; later close_failed remains secondary. This one-field correction is already root-authorized.',
        'diagnostics':'Other proposed negative diagnostic/classification changes reflect existing v1 behavior: opaque hook failure is conservatively unknown, invalid root syntax is path_root, and earliest hard cutoff on seal close is hard_deadline. No rejection is relaxed and all qualification flags remain false. These choices need peer/root agreement, not silent application.'},
        source_corrections_required=['Unreturned WriteFile must set write_count_unknown before any possible cleanup or report; preserve primary exception object.',
        'Content reads/writes require a same-owner successful four-query identity witness. Primitive seed assumptions need an explicit HARNESS-ONLY identity capability, not an arbitrary identity_ok/ready dict or general owned handle. Add caught-identity-failure no-content probes.'],
        scope='Only a finite fictional interface/source correction proposal. Source-v1 and all frozen84 fixtures remain unchanged. Candidate scripts may be tested in memory; they are not an accepted fixture revision or real run.',
        profile_qualified=False,runtime_authorized=False,actual_API_calls=0,old_original_payload_operations=0)
    with TARGET.open('x',encoding='utf-8') as out:json.dump(result,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proposal=pin(TARGET),script_cases=len(IDS),all_changed_cases=len(patches))))


if __name__=='__main__':main()
