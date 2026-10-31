"""Version the new preparation slice after preserving the accepted 0.3.3 verifier."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OLD = ROOT / 'planning/review-assets/recovery-step9-comparison-20261026/code-validation.json'
PRESERVED = ROOT / 'data/reference/recovery-r09-comparison-verifier-033-20261026'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


prior = json.loads(OLD.read_bytes())
for name, expected in prior['source_pins'].items():
    raw = (ROOT / name).read_bytes()
    if name in ('src/asof/__init__.py', 'pyproject.toml', 'uv.lock'):
        raw = raw.replace(b'"0.3.4"', b'"0.3.3"')
    elif name == 'src/asof/archive/semantic_dependencies.json':
        raw = (PRESERVED / 'semantic_dependencies.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, name
assert json.loads((HERE / 'frozen-comparison-before.json').read_bytes())['status'] == 'passed_recorded_comparison_relocation'
profile_path = ROOT / 'src/asof/archive/semantic_dependencies.json'
old_raw = (PRESERVED / 'semantic_dependencies.json').read_bytes()
assert (ROOT / 'src/asof/__init__.py').read_bytes().replace(b'"0.3.4"', b'"0.3.3"') == (PRESERVED / '__init__.py').read_bytes()
for name in ('src/asof/__init__.py', 'pyproject.toml', 'uv.lock'):
    path = ROOT / name
    text = path.read_text(encoding='utf-8')
    assert text.count('"0.3.4"') == 1
profile = json.loads(old_raw)
for name, expected in profile['modules'].items():
    if name != '__init__.py':
        assert sha(ROOT / 'src/asof' / name) == expected
profile.update(executing_build_profile='recovery-r09-preparation-0.3.4-20261026',
               previous_resource_sha256=hashlib.sha256(old_raw).hexdigest(),
               scope='Version-only legacy helper delta from 0.3.3; new preparation modules do not alter legacy semantic helpers.',
               compatibility_review='planning/review-assets/recovery-step9-token-aware-20261026/compatibility-profile-review.md')
profile['modules']['__init__.py'] = sha(ROOT / 'src/asof/__init__.py')
assert json.loads(profile_path.read_bytes()) == profile
result = dict(schema_version=1, status='working_version_not_accepted', version='0.3.4',
              prior_pins_verified_with_reviewed_version_delta=len(prior['source_pins']),
              previous_profile_sha256=hashlib.sha256(old_raw).hexdigest(),
              new_profile_sha256=sha(profile_path),
              legacy_semantic_changes=['__init__.py version only'],
              prior_verifier='explicit reviewed frozen 0.3.3 installation',
              full_validation='pending', scientific_validation='not_established')
with (HERE / 'WORKING-VERSION.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
