"""Two root-approved literal closures; source does not yet exist."""
import copy
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(name,value):
 with (HERE/name).open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'))
old_schema=HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json'
old_fixture=HERE/'SHARED-OWNER-INTEGRATION-FIXTURES-v2.json'
assert pin(old_schema)['sha256']=='7ea6cb057c749e54a4fa557345ce00076fbd9b6b911eb7d767d9666fd7ddb0c8'
assert pin(old_fixture)['sha256']=='45b17a6c737d6dbd914557f698a74ed92bf18077a0d2b86864cec63b72d037c5'
schema=json.loads(old_schema.read_bytes());old_s=copy.deepcopy(schema)
schema['check_relations'].append('one_of')
schema['check_paths']+=' The ONLY extra harness path is $binding.ReadFile.<file_id>.<occurrence>.arguments.requested: read the actual argument dictionary captured by the generic binding Spy. file_id is strict canonical ordinal0..3, occurrence1..68. This is not a new Snapshot/CallRef/source field. one_of is bounded literal membership with strict type comparison (never bool/int coercion).'
schema['binding_override_rule']+=' HARNESS-ONLY transport normalization: baseline file_id is a cohort blob-id string and buffer_write uses frame_id; map the id via the FROZEN cohort order to canonical integer file_id and frame_id to frame before generic dispatch. Override rules already use integer file_id and frame. No aliases/labels enter source arguments/hooks. Expected argument dictionaries come from frozen descriptors and authored literal counts, NEVER the subject CallRef: all fixed API fields stay exact; ReadFile.requested=min(65536,literal file size minus SUM of earlier scripted defined-success literal counts for that file). For the17 shortleaf calls this is exactly58..42; the18th must not dispatch even though41bytes remain and globalR51 is not exhausted. Also compare source CallRef.requested to the independently expected argument, never use it to derive expected.'
schema['expected_comparison']+=' BEFORE any expected comparison, validate the ACTUAL Snapshot/FinalResult against all exact publicDATA nested keys, enums, caps and strict primitive domains: bool never equals int, numeric counters/IDs are exact int, time finite nonbool int/float, atoms retain raw API domains, immutable diagnostics have no exception leaves. A finalized noncomplete result MUST have status REFUSED or INCOMPLETE, excludingACTIVE andbothcomplete statuses. This test-harness one_of predicate grants no source authority.'
schema['step_error_policy']+=' Failed-prefix and hard-cutoff monitors stay strict: do not execute unexpected regular work after a fault; every attempted unexpected binding/sink callback is recorded as a test violation BEFORE raising, not hidden/normalized to0. No callback admitted at/after original hard_end. Snapshot/read-only diagnostics may be inspected without clock/I/O. These monitors do not create new cleanup or budget resets.'
write('SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json',schema)
fixture=json.loads(old_fixture.read_bytes());old_f=copy.deepcopy(fixture)
incomplete=0
for case in fixture['cases']:
 complete=any(c['at']=='final' and c['path']=='status' and c['relation']=='eq' and c['value'] in ('PURE_SEAM_COMPLETE_CONSISTENT','PURE_SEAM_COMPLETE_NEGATIVE') for c in case['checks'])
 if not complete:
  case['checks'].append(dict(at='final',path='status',relation='one_of',value=['REFUSED','INCOMPLETE']))
  incomplete+=1
 if case['id']=='short_read_attempt_exhaustion':
  for occurrence in range(1,18):
   case['checks'].append(dict(at='final',path='$binding.ReadFile.0.'+str(occurrence)+'.arguments.requested',relation='eq',value=59-occurrence))
assert incomplete==45
fixture['schema']=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json')
fixture['author']=pin(Path(__file__).resolve())
fixture['comparison_policy']=schema['expected_comparison']
write('SHARED-OWNER-INTEGRATION-FIXTURES-v3.json',fixture)
# Independent exact-delta removal recovers the original case values.
reverse=copy.deepcopy(fixture)
added=[]
for before,after in zip(old_f['cases'],reverse['cases']):
 assert after['checks'][:len(before['checks'])]==before['checks']
 appended=after['checks'][len(before['checks']):]
 added.append(dict(id=after['id'],checks=copy.deepcopy(appended)))
 after['checks']=copy.deepcopy(before['checks'])
assert reverse['cases']==old_f['cases']
for key in ('schema','author','comparison_policy'):reverse[key]=old_f[key]
assert reverse==old_f
changed_schema=[k for k in old_s if old_s[k]!=schema[k]]
assert set(changed_schema)=={'check_relations','check_paths','binding_override_rule','expected_comparison','step_error_policy'}
proof=dict(schema_version=1,status='passed',scope='Two closed literal/harness clarifications only. No source API/field, history, step, action, raw fact, input byte or frame changes.',preserved_schema=pin(old_schema),preserved_fixture=pin(old_fixture),preserved_freeze=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-FREEZE-v2.json'),schema=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json'),fixture=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURES-v3.json'),author=pin(Path(__file__).resolve()),changed_schema_fields=changed_schema,added_checks=added,status_checks_added=45,independent_requested_checks_added=17,requested_values=list(range(58,41,-1)),all_prior_checks_retained=True,reverse_cases_exact=True,all48_schedules_actions_frames_unchanged=True,actual_API_calls=0,fake_dispatches=0,source_implementation=False)
write('SHARED-OWNER-INTEGRATION-TWO-CLOSURE-DELTA-v3.json',proof)
print(json.dumps(dict(schema=proof['schema'],fixture=proof['fixture'],delta=pin(HERE/'SHARED-OWNER-INTEGRATION-TWO-CLOSURE-DELTA-v3.json'))))
