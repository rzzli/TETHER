"""Apply the narrow reviewed profile migration; preserve every previous byte."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
RESOURCE = ROOT / 'src/asof/archive/semantic_dependencies.json'
OLD_PACKAGE = ROOT / 'data/cache/tether-051-installed-qualification-attempt02/environment/Lib/site-packages/asof'
APPROVED = {
    'agents.py': 'd6517766232959f2fc0f9d5d84b3fc181c35774cb4dac32df2d88f99bcc4d2fc',
    'artifacts.py': 'bb8027adea7bc2719f24895db9afbe05b44281231ee0a7a3e29592047290cd98',
    'replay_validation.py': '9ac7442fe07d5d82c6516d2e2bc214d68354c8e2e1e216ed40dc872cb5c45905',
}


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def save(path, value):
    with path.open('xb') as stream:
        stream.write(json.dumps(value, indent=2).encode('utf-8') + b'\n')


def main():
    prior_bytes = RESOURCE.read_bytes()
    prior = json.loads(prior_bytes)
    assert prior_bytes == (OLD_PACKAGE / 'archive/semantic_dependencies.json').read_bytes()
    assert prior['executing_build_profile'] == 'tether-ce-corrections-0.3.12-atomic-retry-20261102'
    assert len(prior['modules']) == 22
    root = RESOURCE.parent.parent
    assert '__version__ = "0.3.13"' in (root / '__init__.py').read_text()
    actual = {name: digest((root / name).read_bytes()) for name in prior['modules']}
    changed = sorted(name for name in actual if actual[name] != prior['modules'][name])
    assert changed == ['__init__.py', 'agents.py', 'artifacts.py'], changed
    for name, expected in APPROVED.items():
        assert digest((root / name).read_bytes()) == expected, name
    archive_python = {p.name: digest(p.read_bytes()) for p in sorted(RESOURCE.parent.glob('*.py'))}
    assert archive_python == {p.name: digest(p.read_bytes()) for p in sorted((OLD_PACKAGE / 'archive').glob('*.py'))}
    preserved = HERE / 'semantic_dependencies-0.3.12-atomic-retry.json'
    with preserved.open('xb') as stream:
        stream.write(prior_bytes)
    new = dict(prior)
    new.update(executing_build_profile='tether-replay-correction-0.3.13-20261105',
        previous_resource_sha256=digest(prior_bytes),
        scope='Reviewed executing dependency migration for live archived-v2 replay validation. The archive Python and frozen v0.2 compatibility policy remain unchanged; historical archive verification does not gain the new live replay guarantee. Original source/data/receipt bytes are preserved.',
        compatibility_review='planning/review-assets/tether-replay-correction-20261105/archive-profile/REVIEW.md')
    new['modules'] = {**actual, 'replay_validation.py': APPROVED['replay_validation.py']}
    new_bytes = json.dumps(new, indent=2).encode('utf-8') + b'\n'
    proposed = HERE / 'semantic_dependencies-0.3.13-proposed.json'
    with proposed.open('xb') as stream:
        stream.write(new_bytes)
    record = dict(schema_version=1, status='PREPARED', created_at_utc=datetime.now(timezone.utc).isoformat(),
        active_resource=RESOURCE.relative_to(ROOT).as_posix(),
        old_copy=preserved.relative_to(ROOT).as_posix(), candidate=proposed.relative_to(ROOT).as_posix(),
        old_resource_sha256=digest(prior_bytes), new_resource_sha256=digest(new_bytes),
        changed_existing_module_pins=changed, added_module_pins=['replay_validation.py'],
        unchanged_existing_modules=19, previous_module_count=22, new_module_count=23,
        policy_unchanged=new['policy'] == prior['policy'], archive_python_sha256=archive_python,
        approved_current_module_sha256=new['modules'], script_sha256=digest(Path(__file__).read_bytes()))
    save(HERE / 'PREPARED.json', record)
    assert RESOURCE.read_bytes() == prior_bytes
    staged = RESOURCE.with_name('semantic_dependencies.json.replay-correction-stage')
    with staged.open('xb') as stream:
        stream.write(new_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staged, RESOURCE)
    assert RESOURCE.read_bytes() == new_bytes
    assert archive_python == {p.name: digest(p.read_bytes()) for p in sorted(RESOURCE.parent.glob('*.py'))}
    save(HERE / 'APPLIED.json', dict(record, status='APPLIED', applied_at_utc=datetime.now(timezone.utc).isoformat()))
    print(json.dumps(dict(status='APPLIED', old_resource_sha256=digest(prior_bytes),
        new_resource_sha256=digest(new_bytes), changed=changed, added=['replay_validation.py'])))


if __name__ == '__main__':
    main()
