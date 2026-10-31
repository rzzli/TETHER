"""Declare the isolated0.3.10 study fix after targeted source edits/tests finish."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
before=json.loads((HERE/'BEFORE-VERSION.json').read_bytes())
profile_path=ROOT/'src/asof/archive/semantic_dependencies.json'
old=profile_path.read_bytes()
assert hashlib.sha256(old).hexdigest()==before['previous_profile_sha256']
profile=json.loads(old)
assert profile['executing_build_profile']=='recovery-r09-native-0.3.9-20261027'
for name,digest in profile['modules'].items():
    assert hashlib.sha256((ROOT/'src/asof'/name).read_bytes()).hexdigest()==digest,name
for relative in ('src/asof/__init__.py','pyproject.toml','uv.lock'):
    path=ROOT/relative;text=path.read_text(encoding='utf-8')
    assert text.count('"0.3.9"')==1,relative
    path.write_text(text.replace('"0.3.9"','"0.3.10"'),encoding='utf-8')
profile['executing_build_profile']='recovery-r09-native-duration-0.3.10-20261028'
profile['previous_resource_sha256']=hashlib.sha256(old).hexdigest()
profile['scope']='Version-only legacy helper delta from0.3.9; native study duration budget/report correction, no legacy admission/scoring changes.'
profile['compatibility_review']='planning/review-assets/recovery-step9-native-duration-20261028/compatibility-profile-review.md'
profile['modules']['__init__.py']=hashlib.sha256((ROOT/'src/asof/__init__.py').read_bytes()).hexdigest()
profile_path.write_text(json.dumps(profile,indent=2)+'\n',encoding='utf-8')
report=dict(schema_version=1,status='working_0310_version_declared_not_accepted',
    previous_profile_sha256=hashlib.sha256(old).hexdigest(),profile_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest(),
    initializer_sha256=profile['modules']['__init__.py'],legacy_delta=['__init__.py'],
    model_calls=0,source_fixtures_rewritten=False)
with (HERE/'VERSION-BOUNDARY.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
