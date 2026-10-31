"""Root-authorized prose-only hook-count correction; no source behavior."""
import copy
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(name,value):
 with (HERE/name).open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'))
old_schema=HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v1.json'
old_fixture=HERE/'SHARED-OWNER-INTEGRATION-FIXTURES-v1.json'
assert pin(old_schema)['sha256']=='166eedbab91179a75d381de92ad8ef1f9c97076036b5dbb7c5008e91fa3fe300'
assert pin(old_fixture)['sha256']=='aba712bc59f5b8411bf356b24469d86f5a71ab624049ca5057e8fb40ec683d15'
schema=json.loads(old_schema.read_bytes());before=copy.deepcopy(schema)
phrase='seven exact proposal hook methods'
assert schema['binding_override_rule'].count(phrase)==1
schema['binding_override_rule']=schema['binding_override_rule'].replace(phrase,'six exact proposal hook methods across seven active APIs')
reverse=copy.deepcopy(schema);reverse['binding_override_rule']=before['binding_override_rule'];assert reverse==before
write('SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json',schema)
fixture=json.loads(old_fixture.read_bytes());prior=copy.deepcopy(fixture)
fixture['schema']=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json')
fixture['author']=pin(Path(__file__).resolve())
reverse=copy.deepcopy(fixture);reverse['schema']=prior['schema'];reverse['author']=prior['author'];assert reverse==prior
write('SHARED-OWNER-INTEGRATION-FIXTURES-v2.json',fixture)
proof=dict(schema_version=1,status='passed',scope='Exactly one schema prose hook-count correction and two fixture provenance pins. No field/behavior/schedule/check/input changes.',preserved_schema=pin(old_schema),preserved_fixture=pin(old_fixture),schema=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json'),fixture=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURES-v2.json'),author=pin(Path(__file__).resolve()),all48_cases_identical=fixture['cases']==prior['cases'],frames_identical=fixture['frames_hex']==prior['frames_hex'],baseline_rows_identical=fixture['expected_baseline_serialized_rows']==prior['expected_baseline_serialized_rows'],source_implementation=False,actual_API_calls=0)
write('SHARED-OWNER-INTEGRATION-WORDING-DELTA-PROOF-v2.json',proof)
print(json.dumps(dict(schema=proof['schema'],fixture=proof['fixture'],proof=pin(HERE/'SHARED-OWNER-INTEGRATION-WORDING-DELTA-PROOF-v2.json'))))
