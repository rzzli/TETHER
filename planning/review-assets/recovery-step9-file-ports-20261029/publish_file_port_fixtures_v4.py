"""Apply only the root/peer-approved fictional fixture proposal; no port calls."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
DATA=HERE/'FILE-PORTS-FIXTURES-v4.json'
FREEZE=HERE/'FILE-PORTS-FIXTURE-FREEZE-v4.json'
ROOT=HERE/'PORTABLE-FILE-PORTS-ROOT-FIXTURE-PUBLICATION-v4.json'
PROPOSAL=HERE/'PORTABLE-FILE-PORTS-CORRECTION-PROPOSAL-v1.json'
OLD=HERE/'FILE-PORTS-FIXTURES-v3.json'
def pin(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    assert not DATA.exists() and not FREEZE.exists()
    assert pin(ROOT)['sha256']=='c35f98026775de8e4faa9b5230b3ee8adf8e24707efe13e455b6553b26f0fb6f'
    assert pin(PROPOSAL)['sha256']=='c30fbddf1019dee9a457705ec2553d0662b6555ae5a753a6bab7aeecd51dfc22'
    old=json.loads(OLD.read_text(encoding='utf-8'));new=copy.deepcopy(old);proposal=json.loads(PROPOSAL.read_text(encoding='utf-8'));by={c['id']:c for c in new['cases']}
    for patch in proposal['patches']:
        c=by[patch['id']]
        if patch['script_changed']:c['script']=patch['new_script']
        for key,change in patch['expected_field_changes'].items():
            assert c['expected'][key]==change['before'];c['expected'][key]=change['proposed']
    changed=[a['id'] for a,b in zip(old['cases'],new['cases']) if a!=b]
    scripts=[a['id'] for a,b in zip(old['cases'],new['cases']) if a['script']!=b['script']]
    unchanged=[a['id'] for a,b in zip(old['cases'],new['cases']) if a==b]
    assert len(new['cases'])==84 and len(changed)==18 and len(unchanged)==66 and len(scripts)==13
    assert scripts==proposal['thirteen_script_case_ids']
    assert {k:v for k,v in old.items() if k!='cases'}=={k:v for k,v in new.items() if k!='cases'}
    with DATA.open('x',encoding='utf-8') as f:json.dump(new,f,sort_keys=True,separators=(',',':'));f.write('\n')
    record=dict(schema_version=1,status='FICTIONAL_V4_EXACT_REVIEWED_CORRECTIONS_PUBLISHED_NOT_PORT_ACCEPTANCE',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        data=pin(DATA),author=pin(Path(__file__)),inputs={p.name:pin(p) for p in (ROOT,PROPOSAL,OLD,HERE/'FILE-PORTS-FIXTURE-SCHEMA-v3.json',HERE/'file_port_fixture_script_v2.py')},
        changed_case_ids=changed,changed_script_ids=scripts,unchanged_case_ids=unchanged,all_noncase_metadata_unchanged=True,
        scope='Exact approved13 scripts/18 changed cases/66 unchanged. Shared schema and callable fictional interface bytes unchanged. Actual portable behavioral proof is a separate subsequent stage; this author never invokes port or API.',
        profile_qualified=False,runtime_authorized=False,actual_API_calls=0,old_original_payload_operations=0)
    with FREEZE.open('x',encoding='utf-8') as f:json.dump(record,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(data=pin(DATA),freeze=pin(FREEZE),changed=len(changed),scripts=len(scripts))))
if __name__=='__main__':main()
