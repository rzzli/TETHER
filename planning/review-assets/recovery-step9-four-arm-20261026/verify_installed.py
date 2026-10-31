"""Installed-wheel restoration test with denied original reads and archived execution."""
import ctypes
import hashlib
import importlib.abc
import json
import os
import sys
import time
from pathlib import Path

# The verifier is installed separately. Run with -I; no repository sys.path edits.
BASE = Path(sys.argv[1]).resolve()
REPORT = Path(sys.argv[2]).resolve()
REPORT.parent.mkdir(exist_ok=True, parents=True)
materialization = json.loads((BASE/'materialization.json').read_text(encoding='utf-8'))
envelope = json.loads((BASE/'envelope.json').read_text(encoding='utf-8'))
environment = Path(sys.prefix).resolve()
qualification=json.loads((Path(__file__).parent/'QUALIFICATION.json').read_bytes())
current_bundle=Path(qualification['output']).resolve()
assert qualification['status']=='passed'
script = Path(__file__).resolve()
old_roots = [r['logical_root'] for r in envelope['roots']]
forbidden_reads, forbidden_execution, forbidden_imports, forbidden_network = [], [], [], []


def under(path, root):
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def normalized(path):
    return os.path.normcase(os.path.abspath(os.fspath(path)))


approved = [normalized(current_bundle), normalized(BASE), normalized(environment), normalized(script), normalized(REPORT.parent)]
old = [normalized(p) for p in old_roots]
restored_code = [normalized(Path(roots['project'])) for roots in materialization['approved_root_candidates'].values()]


def audit(event, args):
    if event in ('open', 'os.listdir', 'os.scandir') and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = normalized(os.fsdecode(args[0]))
        if path.startswith('e:') or '\\data\\benchmark\\' in path:
            forbidden_reads.append(dict(event=event,path=path))
            raise PermissionError('Original assets and benchmark payloads unavailable')
        if any(under(path, root) for root in old) and not any(under(path, root) for root in approved):
            forbidden_reads.append(dict(event=event, path=path))
            raise PermissionError('Original-root access denied by restoration guard')
    if event == 'exec' and args:
        filename = args[0].co_filename
        if filename and not filename.startswith('<') and any(under(normalized(filename), root) for root in restored_code):
            forbidden_execution.append(filename)
            raise PermissionError('Archived source execution denied')
    if event in ('socket.connect', 'subprocess.Popen'):
        forbidden_network.append(event)
        raise PermissionError('Network/child dispatch denied during verification')


class NoTools(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'tools' or fullname.startswith('tools.'):
            forbidden_imports.append(fullname)
            raise ImportError('Repository-only tools package forbidden in installed verification')


sys.meta_path.insert(0, NoTools())
sys.addaudithook(audit)
from asof.archive.restore import verify
import asof.archive.core as core

assert Path(core.__file__).resolve().is_relative_to(environment)
from asof.study.__main__ import smoke
study_result = smoke(REPORT.parent / 'study-smoke-installed')
from asof.study.baseline_smoke import smoke as baseline_smoke
from asof.serde import encode
baseline_result = encode(baseline_smoke(REPORT.parent / 'baseline-smoke-installed'))
from asof.study.fixed_evidence_smoke import smoke as comparison_smoke
comparison_result = encode(comparison_smoke(REPORT.parent / 'comparison-installed'))
from asof.study.retrieval_smoke import smoke as retrieval_smoke
retrieval_result = encode(retrieval_smoke(REPORT.parent / 'retrieval-installed'))
assert study_result['status'] == 'recorded_smoke_passed'
from asof.study.authority_four_arm import verify as four_arm_verify
four_arm_result=encode(four_arm_verify(current_bundle,qualification['result']['receipt_sha256']))
assert four_arm_result == qualification['result']
records = []
started = time.monotonic()
for run in envelope['runs']:
    run_started = time.monotonic()
    try:
        result = verify(materialization['envelope'], materialization['envelope_sha256'], run['run_id'],
                        materialization['approved_root_candidates'][run['run_id']],
                        receipt_sha256=run.get('receipt_sha256'), journal_sha256=run.get('journal_sha256'))
        records.append(dict(run_id=run['run_id'], status='passed', result=result,
                            elapsed_seconds=time.monotonic()-run_started))
    except Exception as error:
        records.append(dict(run_id=run['run_id'], status='failed', error_class=type(error).__name__, message=str(error)))
    REPORT.write_text(json.dumps(dict(status='verification_in_progress', results=records), indent=2)+'\n', encoding='utf-8')

class Memory(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
        (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
        'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]

memory = Memory()
memory.cb = ctypes.sizeof(memory)
ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Memory), ctypes.c_ulong]
ctypes.windll.psapi.GetProcessMemoryInfo.restype = ctypes.c_int
ok = ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(memory), memory.cb)
result = dict(installed_authority_four_arm=four_arm_result, installed_retrieval_smoke=retrieval_result, installed_comparison_smoke=comparison_result, installed_baseline_smoke=baseline_result, installed_study_smoke=study_result, status='passed' if all(r['status']=='passed' for r in records) else 'failed',
              installed_module=str(core.__file__), isolated_mode=bool(sys.flags.isolated),
              verifier_environment=str(environment), results=records, elapsed_seconds=time.monotonic()-started,
              peak_working_set_bytes=memory.PeakWorkingSetSize if ok else None,
              original_root_access_attempts=forbidden_reads, archived_execution_attempts=forbidden_execution,
              repository_tools_import_attempts=forbidden_imports, network_or_child_attempts=forbidden_network,
              receipt_bytes_rewritten=False, historical_program_execution='not_performed',
              scientific_validation='not_established')
REPORT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['status']=='passed' else 1)
