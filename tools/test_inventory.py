"""Collect repository unittest modules in separate processes, without Git history.

This is a census, not a test pass. Import failures, timeouts and uncollected
methods remain explicit. Optional environments can be assigned by path prefix.
Only trusted repository tests should be imported by this developer utility.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOTS = ('tests', 'experiments', 'packages/tether/tests')


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
        stream.write('\n')


def declared_methods(path):
    """Count direct class declarations separately from inherited/generated cases."""
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    return [{'owner': node.name, 'method': child.name, 'line': child.lineno}
            for node in tree.body if isinstance(node, ast.ClassDef)
            for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            and child.name.startswith('test_')]


def source_inventory(root):
    root = Path(root)
    result = []
    for folder in TEST_ROOTS:
        for path in sorted((root / folder).rglob('test_*.py')):
            relative = path.relative_to(root).as_posix()
            if '__pycache__' in path.parts:
                continue
            result.append({'path': relative, 'module': relative[:-3].replace('/', '.'),
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'declared': declared_methods(path)})
    if not result:
        raise ValueError('No test sources found')
    return sorted(result, key=lambda item: item['path'])


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def collect_worker(root, module):
    root = Path(root).resolve()
    sys.path[:0] = [str(root), str(root / 'src'), str(root / 'packages/tether/src')]
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(module)
    cases = []
    for test in flatten(suite):
        row = {'id': test.id(), 'path': None, 'owner': None, 'method': None}
        try:
            method = getattr(test, test._testMethodName)
            row.update(path=Path(inspect.getsourcefile(method)).resolve().relative_to(root).as_posix(),
                       owner=method.__qualname__.rsplit('.', 1)[0], method=test._testMethodName)
        except (AttributeError, TypeError, ValueError):
            pass
        cases.append(row)
    return {'module': module, 'cases': cases, 'errors': loader.errors,
            'status': 'collection_failed' if loader.errors else 'collected_not_executed'}


def interpreter_for(path, environments):
    candidates = [(prefix, value) for prefix, value in environments.items()
                  if path == prefix or path.startswith(prefix.rstrip('/') + '/')]
    return str(Path(max(candidates, key=lambda item: len(item[0]))[1]).resolve()) if candidates else sys.executable


def reconcile(sources, modules):
    cases = [case for module in modules for case in module.get('cases', [])]
    covered = {(case['path'], case['owner'], case['method']) for case in cases}
    missing = [dict(path=source['path'], **method) for source in sources for method in source['declared']
               if (source['path'], method['owner'], method['method']) not in covered]
    failures = [module['module'] for module in modules if module['status'] != 'collected_not_executed']
    counts = {'source_files': len(sources), 'declared_methods': sum(len(s['declared']) for s in sources),
              'collected_entries': len(cases), 'unique_test_ids': len({c['id'] for c in cases}),
              'uncollected_declarations': len(missing), 'failed_modules': len(failures)}
    return {'status': 'collection_complete_not_execution' if cases and not missing and not failures else 'collection_incomplete',
            'tests_executed': 0, 'counts': counts, 'uncollected_declarations': missing,
            'failed_modules': failures, 'sources': sources, 'modules': modules}


def run_worker(command, *, cwd, env, stdout, stderr, timeout):
    """Contain the native Windows interpreter launcher and its descendants."""
    # Developer commands run after installing the dependency-free engine.
    from tether_engine.process_tree import process_tree_for
    tree = process_tree_for(subprocess.Popen)
    if tree is None:
        return subprocess.run(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                              timeout=timeout, check=False)
    process, primary = None, None
    try:
        deadline = time.monotonic() + timeout
        process = tree.launch(command, deadline=deadline, cwd=cwd, env=env,
                              stdout=stdout, stderr=stderr)
        code = process.wait(timeout=max(0, deadline - time.monotonic()))
        return subprocess.CompletedProcess(command, code)
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            tree.finish(time.monotonic() + 5)
            if process is not None:
                process.wait(timeout=5)
        except BaseException as error:
            if primary is None:
                raise
            primary.add_note('Inventory process cleanup: ' + type(error).__name__)


def collect(root, output, *, environments=None, timeout=120):
    root, output = Path(root).resolve(), Path(output).absolute()
    if timeout <= 0:
        raise ValueError('Collection timeout must be positive')
    # Refuse stale results even if collection would otherwise fail early.
    output.mkdir(parents=True, exist_ok=False)
    sources = source_inventory(root)
    write_new(output / 'sources.json', sources)
    modules = []
    for index, source in enumerate(sources):
        work = output / f'{index:04d}'
        work.mkdir()
        scratch = work / 'scratch'
        scratch.mkdir()
        env = dict(os.environ, TEMP=str(scratch), TMP=str(scratch), TMPDIR=str(scratch),
                   PYTHONDONTWRITEBYTECODE='1')
        env.pop('PYTHONPATH', None)
        interpreter = interpreter_for(source['path'], environments or {})
        command = [interpreter, '-I', '-B', str(Path(__file__).resolve()), '--worker', source['module'],
                   '--root', str(root), '--output', str(work / 'collection.json')]
        start = time.monotonic()
        state = {'module': source['module'], 'path': source['path'], 'interpreter': interpreter,
                 'status': 'collection_failed', 'cases': [], 'errors': []}
        with (work / 'stdout.txt').open('xb') as stdout, (work / 'stderr.txt').open('xb') as stderr:
            try:
                process = run_worker(command, cwd=scratch, env=env, stdout=stdout, stderr=stderr,
                                     timeout=timeout)
                state['returncode'] = process.returncode
                if (work / 'collection.json').is_file():
                    report = json.loads((work / 'collection.json').read_text(encoding='utf-8'))
                    if report['module'] != source['module']:
                        raise ValueError('Worker module identity mismatch')
                    state.update(report)
                if process.returncode:
                    state['status'] = 'collection_failed'
            except subprocess.TimeoutExpired:
                state['status'] = 'collection_timeout'
            except (OSError, ValueError, KeyError) as error:
                state['errors'].append(f'{type(error).__name__}: {error}')
        state['elapsed_seconds'] = round(time.monotonic() - start, 6)
        if hashlib.sha256((root / source['path']).read_bytes()).hexdigest() != source['sha256']:
            state['status'] = 'source_changed_during_collection'
        modules.append(state)
        write_new(work / 'result.json', state)
    # No imported test module has executed in this coordinator process.
    result = reconcile(sources, modules)
    write_new(output / 'inventory.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--environments', type=Path, help='JSON mapping test path prefixes to local Python interpreters')
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        try:
            result = collect_worker(args.root, args.worker)
        except Exception as error:
            import traceback
            result = {'module': args.worker, 'cases': [], 'status': 'collection_failed',
                      'errors': [type(error).__name__ + ': ' + str(error), traceback.format_exc()]}
        write_new(args.output, result)
        return int(result['status'] != 'collected_not_executed')
    environments = json.loads(args.environments.read_text(encoding='utf-8')) if args.environments else {}
    result = collect(args.root, args.output, environments=environments, timeout=args.timeout)
    print(json.dumps({'status': result['status'], **result['counts']}))
    return int(result['status'] != 'collection_complete_not_execution')


if __name__ == '__main__':
    raise SystemExit(main())
