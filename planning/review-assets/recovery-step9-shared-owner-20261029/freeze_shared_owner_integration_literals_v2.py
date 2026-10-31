"""Freeze exact preparation bytes; no component imports/execution."""
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
proof_path=HERE/'SHARED-OWNER-INTEGRATION-LITERAL-PROOF-v2.json'
proof=json.loads(proof_path.read_bytes())
assert proof['status']=='passed' and proof['methods']==6
for key in ('fixture','schema','public_schema','public_peer','root_scope','cohort','checker','wording_delta'):
 expected=proof[key];assert pin(Path(expected['path']))==expected
fixture=json.loads((HERE/'SHARED-OWNER-INTEGRATION-FIXTURES-v2.json').read_bytes())
assert len(fixture['cases'])==48 and len({c['group'] for c in fixture['cases']})==14
for name in ('shared_owner_v1.py','shared_file_ports_v1.py','continue_verification_v1.py'):assert not (HERE/name).exists()
names=['SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json','SHARED-OWNER-INTEGRATION-FIXTURES-v2.json','SHARED-OWNER-INTEGRATION-LITERAL-PROOF-v2.json','SHARED-OWNER-INTEGRATION-WORDING-DELTA-PROOF-v2.json','author_shared_owner_integration_fixtures_v1.py','correct_shared_owner_hook_wording_v2.py','check_shared_owner_integration_literals_v2.py','SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json','SHARED-OWNER-PUBLIC-DATA-INDEPENDENT-PEER-v2.json','SHARED-OWNER-ROOT-PREPARATION-SCOPE-v2.json','SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json','SHARED-OWNER-SYNTHETIC-INPUT-FREEZE-v1.json','SHARED-OWNER-COHORT-INDEPENDENT-PEER-v1.json']
value=dict(schema_version=2,status='CLOSED_LITERAL_48_HISTORY_PREPARATION_FROZEN_FOR_INDEPENDENT_PEER_SOURCE_NOT_AUTHORIZED',pins={name:pin(HERE/name) for name in names},freezer=pin(Path(__file__).resolve()),histories=48,groups=14,input_blob_bytes=209,authored_baseline=dict(expected_fake_original_calls=21,capacity_R=51,capacity_C=69,capacity_E=218,expected_journal_rows=53,start=100,work_end=395,hard_end=400),delta='Preserved v1 candidate; v2 changes only six-hook/seven-API prose and metadata repins, with exact48 schedules/checks/frames/serializedrow expectations unchanged.',scope='Closed synthetic literal metadata and expected causal observations only. No fixture behavior/under-test/helper/source-loader/fake API dispatch was run; peer/root source authorization remains separate.',publication_coverage='Actual-future-SinkSpy bytes/once-kind structural bound only; isolated8193/repeatedkind refusal not exercised, no new publication API.',current_fake_dispatches=0,actual_target_API_calls=0,reviewed_components_imported=False,toy_helpers_executed=False,source_implementation_authorized=False,fixture_behavior_qualified=False,qualification=fixture['qualification'])
path=HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-FREEZE-v2.json'
with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(freeze=pin(path),fixture=proof['fixture'],schema=proof['schema'],proof=pin(proof_path))))
