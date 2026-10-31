"""All nine earlier study versions retain their own matching installed verifiers."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE.parent/'recovery-step9-native-integration-20261027'
prior=json.loads((OLD/'FROZEN-VERIFIER-CHECKS.json').read_bytes())
assert len(prior['records'])==8
records=[]
for original in prior['records']:
    version=original['version'];args=list(original['args'])
    if version=='037':
        args[0]=str(HERE/f'FROZEN-{version}-AFTER.json')
        args[1]=str(ROOT/f'data/cache/r09-duration-frozen-{version}-20261028')
    elif version=='038':
        args[-1]=str(ROOT/f'data/cache/r09-duration-frozen-{version}-20261028/guarded-installed-verification.json')
    else:
        args[-1]=str(HERE/f'FROZEN-{version}-AFTER.json')
        if version in ('032','033','036'):args[2]=str(ROOT/f'data/cache/r09-duration-frozen-{version}-20261028')
    records.append(dict(version=version,python=original['python'],helper=original['helper'],args=args))
records.append(dict(version='039',python=str(ROOT/'data/cache/recovery-step9-native-wheel-20261028/ingestion-environment/Scripts/python.exe'),
    helper=str(OLD/'verify_native_installed.py'),args=[str(HERE/'FROZEN-039-AFTER.json'),
        str(ROOT/'data/cache/r09-duration-frozen-039-20261028')]))
for row in records:
    report=Path(row['args'][0] if row['version'] in ('037','039') else row['args'][-1])
    assert not report.exists()
    expected='0.3.'+str(int(row['version'][-1]))
    checked=subprocess.run([row['python'],'-I','-c',"from importlib.metadata import version; assert version('asof-target-agents') == "+repr(expected)],capture_output=True,text=True)
    row['version_check_exit_code']=checked.returncode
    assert checked.returncode==0,checked.stderr
    argv=[row['python'],'-I',row['helper'],*row['args']]
    with (HERE/f"FROZEN-{row['version']}-AFTER.log").open('x',encoding='utf-8') as stream:
        result=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT)
    row.update(argv=argv,exit_code=result.returncode)
    assert result.returncode==0,row
    payload=json.loads(report.read_bytes())
    assert payload['status'].startswith(('passed','installed_collected_source_relocation_verified','installed_native_simulation_relocation_verified'))
    for key,value in payload.items():
        if key=='guards' or (key.endswith('attempts') and isinstance(value,dict)):
            assert all(v==[] for v in value.values()),(report,key,value)
        elif key.endswith('attempts'):assert value==[],(report,key,value)
    row.update(status=payload['status'],report=str(report),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest())
    print(json.dumps(dict(version=row['version'],status=row['status'])),flush=True)
with (HERE/'FROZEN-VERIFIER-CHECKS.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(schema_version=1,status='passed_all_nine_matching_installed_verifiers',current_source_version_under_test='0.3.10',verification_only=True,records=records),stream,indent=2)
