"""Read only the explicitly permitted synthetic eight-control source."""
import hashlib
from pathlib import Path

H=Path(__file__).resolve().parent
p=H.parent/'recovery-step9-shared-owner-20261029'/'shared_owner_five_regressions_v2.py'
raw=p.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='8fc70bcfa3a12ffd4bcae0c5fd3ba6c856960f4044bef3856d5f19537fc4367d'
t=raw.decode()
old='  calls=w.clock.calls;issued=D.invoke(w.owner.snapshot);raw=D.invoke(issued.to_dict)'
assert t.count(old)==1
t=t.replace(old,'  calls=w.clock.calls;issued=D.invoke(w.owner.snapshot);legacy=D.projected_snapshot(w,issued);raw=D.invoke(legacy.to_dict)')
with (H/'role_aware_same8_adapter_v1.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
print('Prepared actual-projector same8 adapter; subject imports/runs0')
