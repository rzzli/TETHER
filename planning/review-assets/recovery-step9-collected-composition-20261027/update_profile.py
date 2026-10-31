"""Declare only the initializer version change among legacy semantic helpers."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
path=ROOT/'src/asof/archive/semantic_dependencies.json'
before=json.loads((HERE/'BEFORE-VERSION.json').read_bytes())
raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()==before['prior_profile_sha256']
profile=json.loads(raw)
for name,expected in profile['modules'].items():
    if name!='__init__.py':
        assert hashlib.sha256((ROOT/'src/asof'/name).read_bytes()).hexdigest()==expected
profile.update(executing_build_profile='recovery-r09-collected-0.3.7-20261027',
    previous_resource_sha256=before['prior_profile_sha256'],
    scope='Version-only legacy helper delta from0.3.6; collected-source study composition extends explicit source admission without changing legacy helpers.',
    compatibility_review='planning/review-assets/recovery-step9-collected-composition-20261027/compatibility-profile-review.md')
profile['modules']['__init__.py']=hashlib.sha256((ROOT/'src/asof/__init__.py').read_bytes()).hexdigest()
path.write_text(json.dumps(profile,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='profile_updated',initializer_sha256=profile['modules']['__init__.py'],
    profile_sha256=hashlib.sha256(path.read_bytes()).hexdigest())))
