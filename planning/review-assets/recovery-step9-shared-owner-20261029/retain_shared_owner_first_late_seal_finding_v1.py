"""Read-only localization from retained actual48 evidence and NEW source."""
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
proof_path=HERE/'SHARED-OWNER-INTEGRATION-ACTUAL-FIRST-PROOF-v1.json'
assert pin(proof_path)['sha256']=='5a104017dfd925f46b11aa15b4a53355a407a8fa0afce6b83c01ec5ae9ccd577'
proof=json.loads(proof_path.read_bytes());run=next(r for r in proof['runs'] if r['id']=='seal_ack_late')
final=run['snapshots'][-1]['data'];seal=final['outputs']['publications']['seal']
assert proof['histories_executed']==48 and proof['histories_matched']==47
assert all(proof['source_unchanged'].values()) and not proof['audit_denials']
assert seal['attempted'] and seal['return_observed'] and seal['acknowledged']
assert final['terminal']['seal_acknowledged'] is False
assert final['origin']['now']==final['origin']['hard_end']==400
assert final['terminal']['pure_owner_ack'] is False and final['terminal']['final_clock_passed'] is False
value=dict(schema_version=1,status='CONFIRMED_THIRD_SOURCE_BOUNDARY_KNOWN_CALLBACK_ACK_LOST_IN_TERMINAL_SUMMARY',first_proof=pin(proof_path),source=pin(HERE/'shared_owner_v1.py'),driver=pin(HERE/'shared_owner_fixture_driver_v1.py'),checker=pin(HERE/'check_shared_owner_integration_actual_v1.py'),fixture=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURES-v3.json'),public_schema=pin(HERE/'SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json'),case='seal_ack_late',actual_callback_record=seal,actual_terminal=final['terminal'],actual_origin=final['origin'],actual_error=final['errors']['primary'],actual_last_sink_observations=[{k:v for k,v in rec.items() if k!='payload_hex'} for rec in run['sink_records'][-3:]],cause='The owner _callback retains actual returned ACK before its post-call original-clock check. _finish assigns terminal.seal_acknowledged from try_action(_publish), whose exception outcomeFalse replaces the known callback fact. Same source pattern exists for candidate/cleanup/receipt; only late-seal was directly exercised in the frozen48.',classification='Source bookkeeping boundary, not a frozen literal/oracle or harness correction. Preserve known callback ACK while retaining deadline/primary/incomplete veto; no successful seal gate/final acknowledgment afterhard.',additional_actual_replay=False,source_modified=False,oracle_modified=False,actual_target_API_calls=0,qualification=final['qualification'])
path=HERE/'SHARED-OWNER-LATE-SEAL-FIRST-FINDING-v1.json'
with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(finding=pin(path))))
