"""Corrected BG02 isolated worker; immutable common measurement helpers reused."""
from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
from pathlib import Path
import sys
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from equal_policy.worker import forbid_network, bundle_inventory, process_memory

IMPLEMENTATION_MODULES = {
    'tether': ('equal_policy_v2.reference', 'validate_bundle'),
    'independent': ('equal_policy_v2.independent', 'validate_bundle'),
    'hash_schema': ('equal_policy.controls', 'hash_schema'),
    'reject_all': ('equal_policy.controls', 'reject_all'),
}


def _implementation(name):
    module_name, function_name = IMPLEMENTATION_MODULES[name]
    module = importlib.import_module(module_name)
    return module, getattr(module, function_name)


def _run_worker(implementation, root, descriptor, scratch):
    # Only the experiment tree is added. Product imports resolve to the installed
    # interpreter environment, never repository src or packages/tether/src.
    experiments = Path(__file__).resolve().parents[1]
    forbidden_sources = (experiments.parent / 'src', experiments.parent / 'packages/tether/src')
    removed = [path for path in sys.path if path and Path(path).resolve() in forbidden_sources]
    sys.path[:] = [path for path in sys.path if not path or Path(path).resolve() not in forbidden_sources]
    sys.path.insert(0, str(experiments))
    inventory = bundle_inventory(root)
    tracemalloc.start()
    import_wall, import_cpu = time.perf_counter(), time.process_time()
    stdout, stderr = io.StringIO(), io.StringIO()
    module = None
    operation_wall = operation_cpu = None
    stage = 'import'
    result = None
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            module, validator = _implementation(implementation)
            import_wall = time.perf_counter() - import_wall
            import_cpu = time.process_time() - import_cpu
            import_current, import_peak = tracemalloc.get_traced_memory()
            tracemalloc.reset_peak()
            stage = 'operation'
            started_wall, started_cpu = time.perf_counter(), time.process_time()
            try:
                result = validator(root, descriptor, scratch_dir=scratch)
                required = {'schema_version', 'control_id', 'decision', 'stage', 'violated_obligations', 'checked_scope', 'observables'}
                if (type(result) is not dict or not required <= result.keys()
                        or result['decision'] not in ('accept', 'reject', 'inspect_only', 'unsupported', 'error')
                        or type(result['observables']) is not dict):
                    raise TypeError('Validator returned an invalid result contract')
            finally:
                operation_wall = time.perf_counter() - started_wall
                operation_cpu = time.process_time() - started_cpu
    except BaseException as error:
        if stage == 'import':
            import_wall = time.perf_counter() - import_wall
            import_cpu = time.process_time() - import_cpu
            import_current, import_peak = tracemalloc.get_traced_memory()
        result = dict(schema_version=1, control_id=descriptor.get('control_id'), decision='error', stage=stage,
            violated_obligations=[], checked_scope=[], observables={}, error_class=type(error).__name__, reason=str(error))
    operation_current, operation_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    memory = process_memory()
    return dict(schema_version=1, implementation=implementation, result=result,
        metrics=dict(import_wall_seconds=import_wall, import_cpu_seconds=import_cpu,
            operation_wall_seconds=operation_wall, operation_cpu_seconds=operation_cpu,
            import_traced_current_bytes=import_current, import_traced_peak_bytes=import_peak,
            operation_traced_current_bytes=operation_current, operation_traced_peak_bytes=operation_peak,
            operation_traced_peak_above_start_bytes=max(0, operation_peak - import_current),
            tracemalloc_scope='Python allocations only; operation peak includes retained import allocations; instrumentation overhead included',
            import_boundary='Selected module import; lazily imported dependencies are charged to operation',
            os_process_memory=memory, bundle_inventory=inventory),
        runtime=dict(python=sys.executable, python_version=sys.version, isolated=bool(sys.flags.isolated),
            experiments_path=str(experiments), implementation_file=str(module.__file__) if module else None,
            removed_repository_source_paths=removed,
            loaded_product_modules={name: str(getattr(sys.modules[name], '__file__', None))
                                    for name in ('tether_engine', 'tether') if name in sys.modules},
            repository_product_source_on_path=any(Path(path).resolve() in
                (experiments.parent / 'src', experiments.parent / 'packages/tether/src') for path in sys.path if path)),
        diagnostics=dict(captured_stdout=stdout.getvalue(), captured_stderr=stderr.getvalue(),
                         network='socket connect/bind/DNS forbidden by audit hook in CLI worker',
                         timeout='parent runner owns hard timeout and terminal timeout record'))


def run_worker(implementation, root, descriptor, scratch):
    previous_path = list(sys.path)
    try:
        return _run_worker(implementation, root, descriptor, scratch)
    finally:
        sys.path[:] = previous_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--implementation', required=True, choices=('tether', 'independent', 'hash_schema', 'reject_all'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--descriptor', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    descriptor_path = args.descriptor.resolve() if args.descriptor.is_absolute() else (root / args.descriptor).resolve()
    if not root.is_dir() or not descriptor_path.is_relative_to(root):
        parser.error('Descriptor must be inside the existing frozen bundle root')
    scratch = args.scratch.resolve()
    if scratch.is_relative_to(root) or root.is_relative_to(scratch):
        parser.error('Scratch must be separate from frozen bundle')
    scratch.mkdir(parents=True, exist_ok=False)
    sys.addaudithook(forbid_network)
    # Frozen descriptor bytes are producer-controlled metadata. Validators still
    # validate their declared fields; oracle files are never loaded by this worker.
    with descriptor_path.open('r', encoding='utf-8-sig') as stream:
        descriptor = json.load(stream)
    output = run_worker(args.implementation, root, descriptor, scratch)
    print(json.dumps(output, ensure_ascii=False, allow_nan=False, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
