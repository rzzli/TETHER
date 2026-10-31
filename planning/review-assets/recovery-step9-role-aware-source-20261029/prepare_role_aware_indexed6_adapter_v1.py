"""Preserve all six pre-code assertions; adapt only genuine projection."""
import hashlib
from pathlib import Path

H=Path(__file__).resolve().parent
p=H.parent/'recovery-step9-production-preflight-20261029'/'indexed_accounting_controls_v2.py'
raw=p.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='d76e1a2d7c70a9a42fa70c5f4989f08f2e291e79f12fa53b454250998c74bf5b'
t=raw.decode()
old='  raw=D.invoke(w.owner.snapshot).to_dict()'
assert t.count(old)==1
t=t.replace(old,'  issued=D.invoke(w.owner.snapshot);raw=D.invoke(D.projected_snapshot(w,issued).to_dict)')
old="      final=w.owner.snapshot().to_dict();self.assertTrue(all(f['close_invocations']==1 for f in final['files']))"
assert t.count(old)==1
t=t.replace(old,"      final=D.invoke(D.projected_snapshot(w,D.invoke(w.owner.snapshot)).to_dict);self.assertTrue(all(f['close_invocations']==1 for f in final['files']))")
with (H/'role_aware_indexed6_adapter_v1.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
print('Prepared unchanged-assertion actual indexed6 adapter; subject imports/runs0')
