"""Verify seven historical study versions using their matching installed code."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
old=HERE.parent/'recovery-step9-collected-composition-20261027'
prior=json.loads((old/'FROZEN-VERIFIER-CHECKS.json').read_bytes())
records=[]
for row in prior['records']:
    version=row['version']
    args=list(row['args'])
    args[-1]=str(HERE/f'FROZEN-{version}-AFTER.json')
    if version in ('032','033','036'):
        args[2]=str(ROOT/f'data/cache/r09-interface-frozen-{version}-after-20261027')
    records.append(dict(version=version,python=row['python'],helper=row['helper'],args=args))
records.append(dict(version='037',python=str(ROOT/'data/cache/recovery-step9-collected-wheel-20261027/ingestion-environment/Scripts/python.exe'),
    helper=str(old/'verify_collected_installed.py'),args=[str(HERE/'FROZEN-037-AFTER.json'),
        str(ROOT/'data/cache/r09-interface-frozen-037-after-20261027')]))
for row in records:
    report=Path(row['args'][0] if row['version']=='037' else row['args'][-1])
    assert not report.exists()
    package_version='0.3.'+str(int(row['version'][-1]))
    check=[row['python'],'-I','-c',"from importlib.metadata import version; assert version('asof-target-agents') == "+repr(package_version)]
    checked=subprocess.run(check,capture_output=True,text=True)
    row['version_check_exit_code']=checked.returncode
    assert checked.returncode==0,checked.stderr
    argv=[row['python'],'-I',row['helper'],*row['args']]
    with (HERE/f"FROZEN-{row['version']}-AFTER.log").open('x',encoding='utf-8') as stream:
        result=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT)
    row.update(argv=argv,exit_code=result.returncode)
    assert result.returncode==0,row
    payload=json.loads(report.read_bytes())
    assert payload['status'].startswith(('passed','installed_collected_source_relocation_verified')),payload['status']
    for key,value in payload.items():
        if key=='guards' or (key.endswith('attempts') and isinstance(value,dict)):
            assert all(v==[] for v in value.values()),(report,key,value)
        elif key.endswith('attempts'):
            assert value==[],(report,key,value)
    row.update(status=payload['status'],report=str(report),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest())
    print(json.dumps(dict(version=row['version'],status=row['status'])),flush=True)
with (HERE/'FROZEN-VERIFIER-CHECKS.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(schema_version=1,status='passed_all_seven_matching_installed_verifiers',
        current_source_version_under_test='0.3.8',verification_only=True,records=records),stream,indent=2)
