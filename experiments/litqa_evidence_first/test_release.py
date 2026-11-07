"""Offline exact-commit CI admission and changed-tree rejection."""
from copy import deepcopy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import subprocess

from . import contracts as c, release


def ci():
    run = dict(head_sha='a' * 40, status='completed', conclusion='success', id=42,
               url='https://api.github.com/repos/rzzli/TETHER/actions/runs/42',
               path='.github/workflows/validate.yml', head_branch='main', event='push', run_attempt=1)
    jobs = [dict(name=name, head_sha=run['head_sha'], run_id=42, status='completed', conclusion='success')
            for name in sorted(release.REQUIRED_JOBS)]
    for job in jobs: job['run_attempt'] = run['run_attempt']
    return dict(run=run, jobs=dict(total_count=4, jobs=jobs))


class ReleaseTests(unittest.TestCase):
    def test_actual_bounded_git_archive_transport_with_invented_ci_metadata(self):
        # The fake run is a codec fixture, never evidence of a real green CI run.
        revision = subprocess.check_output(['git', '-C', str(c.ROOT), 'rev-parse', 'HEAD'],
                                           timeout=10).decode().strip()
        value = ci(); value['run']['head_sha'] = revision
        for job in value['jobs']['jobs']: job['head_sha'] = revision
        with tempfile.TemporaryDirectory() as name:
            anchor = c.write(Path(name).resolve() / 'invented-ci.json', value)
            source = c.capture(c.ROOT / 'src/tether_engine/serde.py')[0]
            result = release.verify(anchor, [source])
        self.assertEqual(result['commit'], revision)
        self.assertEqual(result['matched_runtime_files'], 1)
        self.assertEqual(result['source_http_requests'], 0)

    def test_all_four_jobs_same_exact_commit(self):
        self.assertEqual(release.validate_ci(ci()), 'a' * 40)

    def test_stale_failed_missing_duplicate_or_running_job_is_rejected(self):
        for field, replacement in [('head_sha', 'b' * 40), ('status', 'in_progress'),
                                   ('conclusion', 'failure'), ('run_id', 41)]:
            value = ci(); value['jobs']['jobs'][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError): release.validate_ci(value)
        value = ci(); value['jobs']['jobs'].pop()
        with self.assertRaises(ValueError): release.validate_ci(value)
        value = ci(); value['jobs']['jobs'][0] = deepcopy(value['jobs']['jobs'][1])
        with self.assertRaises(ValueError): release.validate_ci(value)

    def test_wrong_repository_and_short_commit_do_not_qualify(self):
        for key, changed in [('head_sha', 'a' * 7), ('url', 'https://example.org/run/42'), ('id', True)]:
            value = ci(); value['run'][key] = changed
            with self.subTest(key=key), self.assertRaises(ValueError): release.validate_ci(value)

    def test_workflow_branch_event_and_attempt_identity_are_required(self):
        for key, changed in (('path', '.github/workflows/unrelated.yml'), ('head_branch', 'other'),
                             ('event', 'pull_request'), ('run_attempt', True), ('run_attempt', 0)):
            value = ci(); value['run'][key] = changed
            with self.subTest(key=key, changed=changed), self.assertRaises(ValueError): release.validate_ci(value)
        for key in ('path', 'head_branch', 'event', 'run_attempt'):
            value = ci(); del value['run'][key]
            with self.subTest(missing=key), self.assertRaises(ValueError): release.validate_ci(value)

    def test_every_job_must_come_from_the_same_exact_attempt(self):
        for changed in (2, True, None):
            value = ci(); value['jobs']['jobs'][0]['run_attempt'] = changed
            with self.subTest(attempt=changed), self.assertRaises(ValueError): release.validate_ci(value)
        value = ci(); del value['jobs']['jobs'][0]['run_attempt']
        with self.assertRaises(ValueError): release.validate_ci(value)

    def test_uncommitted_source_bytes_are_rejected_despite_green_ci(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); source = root / 'module.py'; source.write_bytes(b'x = 1\n')
            proof = c.capture(source)[0]
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as archive: archive.writestr('module.py', b'x = 1\n')
            with patch.object(c, 'ROOT', root):
                self.assertEqual(release.archive_matches(stream.getvalue(), [proof]), 1)
                source.write_bytes(b'x = 2\n')
                with self.assertRaises(ValueError): release.archive_matches(stream.getvalue(), [proof])
                changed = c.capture(source)[0]
                with self.assertRaises(ValueError): release.archive_matches(stream.getvalue(), [changed])

    def test_duplicate_or_outside_closure_cannot_hide_a_changed_dependency(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); source = root / 'module.py'; source.write_bytes(b'pass\n')
            proof = c.capture(source)[0]; stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as archive: archive.writestr('module.py', b'pass\n')
            with patch.object(c, 'ROOT', root):
                with self.assertRaises(ValueError): release.archive_matches(stream.getvalue(), [proof, proof])
                with self.assertRaises(ValueError): release.archive_matches(stream.getvalue(), [])
            with patch.object(c, 'ROOT', root / 'different'):
                with self.assertRaises(ValueError): release.archive_matches(stream.getvalue(), [proof])


if __name__ == '__main__': unittest.main()
