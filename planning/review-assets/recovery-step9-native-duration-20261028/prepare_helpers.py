"""Reuse qualified operator helpers for the separately versioned duration correction."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE.parent/'recovery-step9-native-integration-20261027'
TESTS=int(sys.argv[1]);PINS=int(sys.argv[2])
assert TESTS>1724 and PINS>=324
assert not (HERE/'run_validation.py').exists()
for name in ('run_validation.py','build_installed.py','prepare_simulation_protocol.py',
        'qualify_simulated.py','verify_native_installed.py','verify_default_installed.py'):
    text=(OLD/name).read_text(encoding='utf-8')
    text=text.replace('0.3.9','0.3.10').replace('1724',str(TESTS)).replace('324',str(PINS))
    text=text.replace('recovery-step9-native-validation-20261028','recovery-step9-duration-validation-20261028')
    text=text.replace('recovery-step9-native-wheel-20261028','recovery-step9-duration-wheel-20261028')
    if name=='qualify_simulated.py':text=text.replace('r09-native-simulation-','r09-native-duration-simulation-')
    if name=='verify_default_installed.py':
        addition='''
from asof.study.native_interpretation import verify_native_duration
from asof.workflow import Budget
duration_configuration=dict(budget=encode(Budget()))
duration_cases=[]
for name,elapsed,configuration,report,expected in [
    ('zero',0.0,duration_configuration,dict(elapsed_seconds=0.0),True),
    ('enclosed',0.01,duration_configuration,dict(elapsed_seconds=0.02),True),
    ('report_equal',0.01,duration_configuration,dict(elapsed_seconds=0.01),True),
    ('over_budget',9999.0,duration_configuration,dict(elapsed_seconds=0.02),False),
    ('at_budget',300.0,duration_configuration,dict(elapsed_seconds=300.0),False),
    ('above_report',0.01,duration_configuration,dict(elapsed_seconds=0.0),False),
    ('missing_budget',0.0,{},dict(elapsed_seconds=0.02),False),
    ('missing_report',0.0,duration_configuration,None,False),
]:
    try:
        verify_native_duration(dict(elapsed_seconds=elapsed),configuration,report=report)
        accepted=True
    except ContractError:accepted=False
    assert accepted==expected,name
    duration_cases.append(dict(id=name,accepted=accepted,expected=expected))
native_wrapper_exercise['duration_cases']=duration_cases

'''
        assert text.count('records = []')==1
        text=text.replace('records = []',addition+'records = []')
    with (HERE/name).open('x',encoding='utf-8') as stream:stream.write(text)
# This is a retained copy of the existing asset mirror proof, not a new mirror.
with (HERE/'NATIVE-MODEL-MIRROR.json').open('xb') as stream:stream.write((OLD/'NATIVE-MODEL-MIRROR.json').read_bytes())
report=dict(schema_version=1,status='operator_helpers_prepared_not_executed',version='0.3.10',
    expected_tests=TESTS,expected_source_pins=PINS,template_phase=OLD.relative_to(ROOT).as_posix(),
    helpers=[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in HERE.glob('*.py')],
    model_assets_reacquired=False,model_calls=0)
with (HERE/'HELPER-PREPARATION.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(dict(status=report['status'],tests=TESTS,pins=PINS)))
