"""Fixed phase-specific immutable binding paths; no subject operation."""
import hashlib
from pathlib import Path

H=Path(__file__).resolve().parent
raw=(H/'run_role_aware_independent_v3.py').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='dd909a12e68c1073e1814519316940000ea39930dfb83e01827cc2a8932bfe89'
t=raw.decode()
old="    parser=argparse.ArgumentParser();parser.add_argument('--binding-sha256',required=True);args=parser.parse_args()"
new="    parser=argparse.ArgumentParser();parser.add_argument('--binding-sha256',required=True);parser.add_argument('--phase',required=True,choices=('CODEC_FIRST','LEGACY48_FIRST'));args=parser.parse_args()"
assert t.count(old)==1;t=t.replace(old,new)
old="    started=time.monotonic();binding_path=HERE/'ROLE-AWARE-INDEPENDENT-SOURCE-BINDING-v3.json'"
new="    started=time.monotonic();binding_path=HERE/('ROLE-AWARE-INDEPENDENT-'+args.phase+'-SOURCE-BINDING-v4.json')"
assert t.count(old)==1;t=t.replace(old,new)
old="        if binding['schema_version']!=1 or binding['phase'] not in ('CODEC_FIRST','LEGACY48_FIRST'):raise RuntimeError('explicit phase binding')"
new="        if binding['schema_version']!=1 or binding['phase'] not in ('CODEC_FIRST','LEGACY48_FIRST') or binding['phase']!=args.phase:raise RuntimeError('explicit argument/binding phase mismatch')"
assert t.count(old)==1;t=t.replace(old,new)
t=t.replace("+'-PROOF-v3.json'","+'-PROOF-v4.json'")
t=t.replace("+'-ATTEMPT-v3.json'","+'-ATTEMPT-v4.json'")
t=t.replace('ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v3.json','ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v4.json')
with (H/'run_role_aware_independent_v4.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
print('Prepared named runnerV4 immutable per-phase bindings; subject imports/runs0')
