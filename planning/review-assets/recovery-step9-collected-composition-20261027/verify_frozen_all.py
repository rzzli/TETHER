"""Invoke each historical verifier with its own preserved installed package."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
old=HERE.parent/'recovery-step9-four-arm-20261026'
prior=json.loads((old/'FROZEN-VERIFIER-CHECKS.json').read_bytes())
records=[]
for row in prior['records']:
    version=row['version']
    args=list(row['args'])
    args[-1]=str(HERE/f'FROZEN-{version}-AFTER.json')
    if version in ('032','033'):
        args[2]=str(ROOT/f'data/cache/r09-collected-frozen-{version}-after-20261027')
    records.append(dict(version=version,python=row['python'],helper=row['helper'],args=args))
qualification=json.loads((old/'QUALIFICATION.json').read_bytes())
records.append(dict(version='036',python=str(ROOT/'data/cache/recovery-step9-four-arm-wheel-20261026/environment/Scripts/python.exe'),
    helper=str(old/'verify_relocation.py'),args=[str(ROOT),str(ROOT/'data/reference/recovery-r09-four-arm-restored-20261027'),
        str(ROOT/'data/cache/r09-collected-frozen-036-after-20261027'),qualification['result']['receipt_sha256'],str(HERE/'FROZEN-036-AFTER.json')]))
for row in records:
    report=Path(row['args'][-1])
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
    assert payload['status'].startswith('passed'),payload['status']
    row.update(status=payload['status'],report=str(report),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest())
    print(json.dumps(dict(version=row['version'],status=row['status'])),flush=True)
with (HERE/'FROZEN-VERIFIER-CHECKS.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(schema_version=1,status='passed_all_six_matching_installed_verifiers',
        current_source_version_under_test='0.3.7',verification_only=True,records=records),stream,indent=2)
