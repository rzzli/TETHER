"""Offline release admission against captured CI metadata and exact Git bytes.

The caller captures the official CI response before freezing the frame. This
module performs no HTTP requests. A green result from an earlier revision does
not qualify the running source tree, even if its method descriptor is unchanged.
"""
import hashlib
import io
import re
import shutil
import zipfile

from tether._process import ProcessLimits, supervise_command, validate_success_report
from tether_engine.serde import freeze
from . import contracts as c

REQUIRED_JOBS = frozenset({
    'tether-interface', 'validate (windows-latest, core)',
    'validate (ubuntu-latest, core)', 'validate (windows-latest, full)',
})


def validate_ci(value):
    c.need(set(value) == {'run', 'jobs'}, 'Exact captured CI run and jobs required')
    run = value['run']; jobs = value['jobs']['jobs']; commit = run['head_sha']
    c.need(type(commit) is str and re.fullmatch('[0-9a-f]{40}', commit), 'Full CI commit identity required')
    c.need(run['status'] == 'completed' and run['conclusion'] == 'success', 'Whole CI run must pass')
    c.need(type(run['id']) is int and run['id'] > 0 and
           run['url'] == f'https://api.github.com/repos/rzzli/TETHER/actions/runs/{run["id"]}',
           'Captured CI repository/run identity differs')
    c.need(run.get('path') == '.github/workflows/validate.yml' and run.get('head_branch') == 'main' and
           run.get('event') == 'push' and type(run.get('run_attempt')) is int and run['run_attempt'] > 0,
           'Required main/push workflow and exact run attempt differ')
    c.need(len(jobs) == 4 and {job['name'] for job in jobs} == REQUIRED_JOBS and
           value['jobs']['total_count'] == 4, 'All four distinct required jobs must be present')
    for job in jobs:
        c.need(job['head_sha'] == commit and job['run_id'] == run['id'] and
               type(job.get('run_attempt')) is int and job['run_attempt'] == run['run_attempt'] and
               job['status'] == 'completed' and job['conclusion'] == 'success',
               'A required exact-commit CI job did not pass')
    return commit


def archive_matches(raw, code_files):
    """Compare every running dependency with the corresponding committed file."""
    c.need(isinstance(raw, bytes) and 0 < len(raw) <= 64 * 1024 ** 2, 'Bounded Git source archive required')
    c.need(code_files, 'A complete declared runtime source closure is required')
    seen = set()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        c.need(len(names) == len(set(names)), 'Duplicate committed archive names')
        for proof in code_files:
            path = c.path(proof['path'])
            c.need(path.is_relative_to(c.ROOT) and path not in seen, 'Unique project source closure paths required')
            seen.add(path); name = path.relative_to(c.ROOT).as_posix()
            info = archive.getinfo(name)
            c.need(info.file_size == proof['bytes'] <= 64 * 1024 ** 2, 'Committed source size differs')
            data = archive.read(info)
            c.need(hashlib.sha256(data).hexdigest() == proof['sha256'], 'Committed source bytes differ: ' + name)
            c.capture(path, proof)
    return len(seen)


def verify(anchor, code_files):
    captured = c.read(anchor); commit = validate_ci(captured)
    executable = shutil.which('git'); c.need(executable is not None, 'Git is required to verify committed source bytes')
    limits = ProcessLimits(60, 64 * 1024 ** 2)
    result = supervise_command([executable, '-C', str(c.ROOT), 'archive', '--format=zip', commit], limits=limits)
    c.need(result.returncode == 0, 'Unable to read the exact CI commit')
    validate_success_report(result.supervision, limits, len(result.stdout), len(result.stderr))
    matched = archive_matches(result.stdout, code_files)
    c.capture(anchor['path'], anchor)
    return freeze(dict(kind='evidence_first_release_verified_v1', commit=commit,
        ci=anchor, matched_runtime_files=matched, required_jobs=sorted(REQUIRED_JOBS),
        verification_seconds=result.supervision['total_elapsed_seconds'], source_http_requests=0))
