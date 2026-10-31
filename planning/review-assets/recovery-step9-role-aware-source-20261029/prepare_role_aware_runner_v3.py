"""The selected common post-suite veto, with no subject import/run."""
import hashlib
from pathlib import Path

H=Path(__file__).resolve().parent
raw=(H/'run_role_aware_independent_v2.py').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='0cad8bf8ed080a17842945086d9b3ff9c8ea93352ad6e62655417cfe1d87d79e'
t=raw.decode()
old='        record=dict(schema_version=1,status=status,phase=phase,methods=methods,method_outcomes=method_outcomes,failures=failures,errors=errors,'
assert t.count(old)==1
t=t.replace(old,"        common_post_suite_late_veto=time.monotonic()>=started+60\n        if common_post_suite_late_veto:status='FIRST_FAILURES_RETAINED'\n        record=dict(schema_version=1,status=status,phase=phase,common_post_suite_late_veto=common_post_suite_late_veto,methods=methods,method_outcomes=method_outcomes,failures=failures,errors=errors,")
t=t.replace('ROLE-AWARE-INDEPENDENT-SOURCE-BINDING-v2.json','ROLE-AWARE-INDEPENDENT-SOURCE-BINDING-v3.json')
t=t.replace("+'-PROOF-v2.json'","+'-PROOF-v3.json'")
t=t.replace("+'-ATTEMPT-v2.json'","+'-ATTEMPT-v3.json'")
t=t.replace('ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v2.json','ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v3.json')
with (H/'run_role_aware_independent_v3.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
print('Prepared named runnerV3 common deadline veto; subject imports/runs0')
