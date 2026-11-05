"""Retain source-bracketed focused replay regression results, never overwrite."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('tag')
    args = parser.parse_args()
    folder = Path(__file__).parent
    paths = [ROOT / name for name in ('src/asof/agents.py', 'src/asof/artifacts.py',
        'src/asof/replay_validation.py', 'tests/test_replay_archive_verification.py')
        if (ROOT / name).exists()]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    for path in paths:
        with (folder / (args.tag + '-' + path.name + '.txt')).open('xb') as stream:
            stream.write(path.read_bytes())
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_replay_archive_verification.py')
    captured = io.StringIO()
    result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
    log = folder / (args.tag + '.log')
    with log.open('x', encoding='utf-8') as stream:
        stream.write(captured.getvalue())
    after = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    record = dict(schema_version=1, status='PASS' if result.wasSuccessful() else 'FAIL',
        created_at_utc=datetime.now(timezone.utc).isoformat(), tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        source_sha256=before, source_unchanged=before == after,
        log_path=log.relative_to(ROOT).as_posix(), log_sha256=sha(log),
        python=sys.executable, isolated=bool(sys.flags.isolated),
        checker_sha256=sha(Path(__file__)), scope='Fictional source-tree replay archive regression tests')
    with (folder / (args.tag + '.json')).open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(captured.getvalue())
    print(json.dumps(record))
    return 0 if result.wasSuccessful() and before == after else 1


if __name__ == '__main__':
    raise SystemExit(main())
