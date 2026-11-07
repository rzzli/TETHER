"""One isolated comparison worker; parent owns timeout and atomic publication."""
from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import time
import tracemalloc


def forbid_network(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.bind', 'socket.getaddrinfo'):
        raise PermissionError('BG02 validator worker forbids network operations')
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        name = Path(os.fsdecode(args[0])).name.casefold()
        if name == 'oracle.json' or name.endswith('_oracle.json') or (name.startswith('oracle') and name.endswith('.json')):
            raise PermissionError('BG02 validator worker cannot read oracle files')


def bundle_inventory(root):
    """Metadata-only logical file sizes; not bytes read or physical disk I/O."""
    count, logical, unique, skipped = 0, 0, {}, []
    for directory, children, names in os.walk(root, followlinks=False):
        retained = []
        for name in children:
            path = Path(directory, name)
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                skipped.append(path.relative_to(root).as_posix())
            else:
                retained.append(name)
        children[:] = retained
        for name in names:
            path = Path(directory, name)
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                skipped.append(path.relative_to(root).as_posix())
                continue
            count += 1
            logical += info.st_size
            key = (info.st_dev, info.st_ino) if info.st_ino else ('path', str(path.resolve()))
            unique[key] = info.st_size
    return dict(file_count=count, logical_file_bytes=logical, unique_logical_bytes=sum(unique.values()),
        uniqueness_basis='device/inode where available; resolved path otherwise',
        skipped_nonregular_or_link_paths=sorted(skipped),
        physical_disk_bytes=None, open_read_bytes=None,
        limitation='Metadata-only inventory; actual read volume, page-cache hits and physical disk traffic are not instrumented')


def process_memory():
    """OS process-lifetime peak, including imports; never claim child or system RSS."""
    if os.name == 'nt':
        try:
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            psapi = ctypes.WinDLL('psapi', use_last_error=True)
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                raise ctypes.WinError(ctypes.get_last_error())
            return dict(peak_bytes=counters.PeakWorkingSetSize, current_bytes=counters.WorkingSetSize,
                method='GetProcessMemoryInfo.PeakWorkingSetSize', scope='whole worker lifetime; includes imports', error=None)
        except (OSError, AttributeError) as error:
            return dict(peak_bytes=None, current_bytes=None, method=None, scope='unavailable', error=str(error))
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return dict(peak_bytes=int(value if sys.platform == 'darwin' else value * 1024), current_bytes=None,
            method='getrusage(RUSAGE_SELF).ru_maxrss', scope='whole worker lifetime; includes imports', error=None)
    except (ImportError, OSError) as error:
        return dict(peak_bytes=None, current_bytes=None, method=None, scope='unavailable', error=str(error))


def _implementation(name):
    module = importlib.import_module('equal_policy.' + ('controls' if name in ('hash_schema', 'reject_all') else
        'reference' if name == 'tether' else 'independent'))
    return module, getattr(module, name if name in ('hash_schema', 'reject_all') else 'validate_bundle')


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
