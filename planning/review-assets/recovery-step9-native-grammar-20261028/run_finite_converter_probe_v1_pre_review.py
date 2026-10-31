"""Operator-only finite native converter diagnostic. Default/dry-run never dispatches.

Root approval of the exact protocol hash and a subsequent explicit --execute are
required. Archived copies of this helper are provenance, not replay authorities.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import ctypes
import hashlib
from importlib import metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread
import time
from zipfile import ZipFile

from asof.journal import RunJournal, read_chain
from asof.serde import canonical, encode, parse_json
from asof.study.stable_read import checked_path, deadline_check, hash_file, stable_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROTOCOL = HERE / 'FINITE-CONVERTER-EXECUTION-PROTOCOL.json'
ACCEPTANCE_SHA = '27f33a36fd01d48b79e1492ad6b4b185a60e4bd662bb1ee0d955e5a284079cdc'
BRIDGE_SHA = 'ea5064b8e2b68aa193efb0e129ef1da6087809d1a6fb21facccefaad70c362ca'
CAPTURE = 1048576


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pin(path):
    path = Path(path).absolute()
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def normal(path):
    return os.path.normcase(os.path.abspath(os.fsdecode(path)))


def under(path, root):
    try:
        return os.path.commonpath([normal(path), normal(root)]) == normal(root)
    except ValueError:
        return False


def typed(value):
    if value is None: return ('null',)
    if type(value) is bool: return ('bool', value)
    if type(value) is int: return ('int', str(value))
    if type(value) is float: return ('float', repr(value))
    if type(value) is str: return ('string', value)
    if type(value) is list: return ('array', tuple(typed(v) for v in value))
    if type(value) is dict: return ('object', tuple(sorted((k, typed(v)) for k, v in value.items())))
    raise ValueError('Unsupported JSON type')


def write_new(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value) + b'\n')
        stream.flush(); os.fsync(stream.fileno())


def copy_new(source, target):
    with Path(source).open('rb') as src, Path(target).open('xb') as dst:
        while block := src.read(1048576): dst.write(block)
        dst.flush(); os.fsync(dst.fileno())
    assert sha(source) == sha(target)


def load_protocol(expected):
    assert sys.flags.isolated and metadata.version('asof-target-agents') == '0.3.10'
    assert importlib.util.find_spec('pyarrow') is None
    assert PROTOCOL.is_file() and sha(PROTOCOL) == expected
    p = parse_json(PROTOCOL.read_bytes())
    assert p['schema_version'] == 1 and p['kind'] == 'finite_actual_converter_probe_v1'
    assert p['helper']['sha256'] == sha(__file__) and normal(p['helper']['path']) == normal(__file__)
    assert p['accepted_software']['acceptance']['sha256'] == ACCEPTANCE_SHA
    assert p['bridge']['sha256'] == BRIDGE_SHA
    assert p['limits'] == dict(max_children=2, per_child_seconds=30, global_seconds=120,
        max_input_bytes=65536, max_stdout_bytes=CAPTURE, max_stderr_bytes=CAPTURE, max_native_output_bytes=4194304)
    assert [s['mode'] for s in p['stages']] == ['roundtrip', 'convert'] and p['force_gbnf'] is False
    out = Path(p['output'])
    assert out.is_absolute() and under(out, ROOT/'data/cache') and not out.exists()
    assert len(p['runtime_files']) == 32 and len([r for r in p['runtime_files'] if r['path'].lower().endswith('.dll')]) == 30
    assert all(not r['path'].lower().endswith('.gguf') and under(r['path'], p['native_root']) for r in p['runtime_files'])
    assert normal(p['accepted_software']['installed_python']) == normal(sys.executable)
    installed_root = Path(sys.prefix)/'Lib/site-packages'
    assert all(under(r['path'], installed_root/'asof') for r in p['accepted_software']['installed_files'])
    assert len(p['accepted_software']['installed_files']) == 83
    pins = [p['helper'], p['bridge'], *p['runtime_files'], *p['provenance_files'],
            *p['accepted_software']['installed_files'], p['accepted_software']['wheel'],
            p['accepted_software']['acceptance'], p['accepted_software']['python'], *[s['input'] for s in p['stages']]]
    for r in pins:
        path = Path(r['path'])
        assert path.is_absolute() and path.drive.lower() != 'e:' and '\\data\\benchmark\\' not in normal(path)
        assert not path.name.lower().endswith('.gguf')
        checked_path(path.parent, path.name)
    for index, stage in enumerate(p['stages']):
        directory = out/'stages'/f'{index:02d}-{stage["mode"]}'
        assert normal(stage['cwd']) == normal(directory)
        assert stage['argv'] == [p['bridge']['path'], stage['mode'], p['native_root'],
            str(out/'inputs'/f'{stage["mode"]}.json'), str(directory/'result.json')]
        assert stage['input']['bytes'] <= p['limits']['max_input_bytes']
    assert sha(p['accepted_software']['acceptance']['path']) == ACCEPTANCE_SHA
    return p, pins


def verify_pins(pins, deadline):
    for r in pins:
        proof = hash_file(Path(r['path']), deadline)
        assert proof['sha256'] == r['sha256'] and proof['bytes'] == r['bytes'], r['path']


def install_guards(p, mode, output):
    state = dict(dispatches=0, spawned_children=0, denied=[], active_argv=None, active_cwd=None)
    writable = [Path(output)] if mode == 'execute' else [Path(output)]
    claim = normal(p['execution_claim'])
    system32 = Path(os.environ['SystemRoot'])/'System32'
    def audit(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'socket.__new__', 'os.system'):
            state['denied'].append(event); raise RuntimeError('No network/system execution')
        if event == 'ctypes.dlopen':
            name = normal(args[0]) if args and isinstance(args[0], (str, bytes, os.PathLike)) else ''
            allowed = str(args[0]).lower() in ('kernel32', 'kernel32.dll') or name in (normal(system32/'version.dll'), normal(system32/'psapi.dll'))
            if not allowed:
                state['denied'].append(event); raise RuntimeError('No llama DLL loading in parent')
        if event == 'subprocess.Popen':
            expected = subprocess.list2cmdline(state['active_argv']) if state['active_argv'] else None
            if mode != 'execute' or state['dispatches'] >= 2 or args[1] != expected or args[0] not in (None, p['bridge']['path']) or normal(args[2]) != normal(state['active_cwd']):
                state['denied'].append(event); raise RuntimeError('Only two exact approved bridge children')
            state['dispatches'] += 1
        if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
            path = normal(args[0])
            if path.startswith('e:') or '\\data\\benchmark\\' in path or path.endswith('.gguf'):
                state['denied'].append(dict(event=event,path=path)); raise RuntimeError('No external/evaluation/GGUF reads')
            file_mode = args[1] if len(args)>1 else None
            flags = args[2] if len(args)>2 and isinstance(args[2],int) else 0
            writing = bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)) or (isinstance(file_mode,str) and any(c in file_mode for c in 'wax+'))
            if writing and not any(under(path, root) for root in writable) and not (mode=='execute' and path==claim):
                state['denied'].append(dict(event=event,path=path)); raise RuntimeError('Writes limited to reserved diagnostic output')
    sys.addaudithook(audit)
    return state


def run_child(stage, journal, state, deadline):
    directory = Path(stage['cwd'])
    child_start = time.monotonic()
    child_end = min(child_start+30, deadline-5)
    deadline_check(child_end)
    record = dict(mode=stage['mode'], argv=stage['argv'], cwd=stage['cwd'], pid=None,
        spawn_succeeded=False, timed_out=False, capture_overflow=False, reaped=False, cleanup_errors=[])
    process = None; threads = []; stop = Event(); streams = {}; captures=ExitStack()
    journal.append('native_converter_attempt_reserved', mode=stage['mode'], argv=stage['argv'],
        input_sha256=stage['input']['sha256'], timeout_seconds=child_end-child_start)
    def drain(name, pipe, sink):
        item = streams[name]
        try:
            while True:
                block = pipe.read(65536)
                if not block: break
                item['observed_bytes_at_least'] += len(block)
                remaining = CAPTURE-item['retained_bytes']
                if remaining: sink.write(block[:remaining]); item['retained_bytes'] += min(len(block),remaining)
                if len(block)>remaining:
                    item['truncated']=True; stop.set(); break
        except BaseException as error:
            item['error_class']=type(error).__name__; stop.set()
        finally:
            try: sink.flush(); os.fsync(sink.fileno())
            except BaseException as error: item['error_class']=type(error).__name__; stop.set()
    try:
        stdout=captures.enter_context((directory/'stdout.bin').open('xb',buffering=0))
        stderr=captures.enter_context((directory/'stderr.bin').open('xb',buffering=0))
        env = dict(persisted_system_environment(stage), TEMP=str(directory), TMP=str(directory))
        journal.append('native_converter_dispatch', mode=stage['mode'], input_sha256=stage['input']['sha256'])
        state['active_argv'], state['active_cwd'] = stage['argv'], stage['cwd']
        process = subprocess.Popen(stage['argv'], cwd=directory, env=env, shell=False,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0), close_fds=True)
        record.update(pid=process.pid, spawn_succeeded=True)
        state['spawned_children'] += 1
        journal.append('native_converter_started', mode=stage['mode'], pid=process.pid)
        for name, pipe, sink in (('stdout',process.stdout,stdout),('stderr',process.stderr,stderr)):
            streams[name]=dict(retained_bytes=0,observed_bytes_at_least=0,truncated=False,error_class=None)
            thread=Thread(target=drain,args=(name,pipe,sink),daemon=True); thread.start(); threads.append(thread)
        while process.poll() is None:
            if stop.is_set() or time.monotonic()>=child_end:
                record['timed_out']=time.monotonic()>=child_end
                record['capture_overflow']=any(s['truncated'] for s in streams.values())
                process.kill(); break
            time.sleep(min(.02,max(.001,child_end-time.monotonic())))
    except BaseException as error:
        record.update(parent_error_class=type(error).__name__, parent_error_message=str(error)[:2048])
        if isinstance(error,KeyboardInterrupt): record['interrupted']=True
        raise
    finally:
        state['active_argv']=state['active_cwd']=None
        if process is not None:
            try:
                if process.poll() is None: process.kill()
                process.wait(timeout=max(.1,min(5,deadline-time.monotonic())))
                record['reaped']=True
            except BaseException as error: record['cleanup_errors'].append(type(error).__name__)
            record['exit_code']=process.poll()
            for thread in threads: thread.join(timeout=max(.1,min(5,deadline-time.monotonic())))
            if any(t.is_alive() for t in threads): record['cleanup_errors'].append('CaptureThreadUnresolved')
            for pipe in (process.stdout,process.stderr):
                if pipe is not None and not any(t.is_alive() for t in threads): pipe.close()
        try: captures.close()
        except BaseException as error: record['cleanup_errors'].append(type(error).__name__)
        record.update(elapsed_seconds=time.monotonic()-child_start, streams=streams)
        for name in ('stdout','stderr'):
            if (directory/(name+'.bin')).is_file(): record[name]=pin(directory/(name+'.bin'))
        write_new(directory/'parent-attempt.json',record)
        journal.append('native_converter_attempt_terminal', **record)
    return record


def persisted_system_environment(stage):
    # Deliberately excludes credentials, PYTHONPATH, CL overrides and user PATH.
    system = Path(os.environ['SystemRoot'])
    return dict(SystemRoot=str(system),WINDIR=str(system),SystemDrive=system.drive,PATH=str(system/'System32'))


def validate_native_result(p, stage, record):
    directory = Path(stage['cwd'])
    if record.get('interrupted'): return 'interrupted',None
    if not record['spawn_succeeded']: return 'spawn_failure',None
    if record['timed_out']: return 'timeout',None
    if record['capture_overflow'] or any(v['truncated'] for v in record['streams'].values()): return 'capture_limit_exceeded',None
    if record['cleanup_errors'] or not record['reaped'] or any(v['error_class'] for v in record['streams'].values()): return 'capture_or_cleanup_failure',None
    stderr=(directory/'stderr.bin').read_bytes()
    stdout=(directory/'stdout.bin').read_bytes()
    try: result=parse_json(stdout)
    except Exception: return 'malformed_native_stdout',None
    if record['exit_code'] != 0 or result.get('status') != 'native_call_returned':
        if 'Unexpected grammar backend marker' in result.get('message',''): return 'unsupported_backend',result
        return ('abi_or_native_process_failure' if stage['mode']=='roundtrip' else 'conversion_exception_or_failure'),result
    if stderr:
        return ('conversion_incomplete_warning' if b'conversion was incomplete' in stderr else 'native_diagnostics'),result
    assert result['mode']==stage['mode'] and result['input_sha256']==stage['input']['sha256']
    assert result['input_bytes']==stage['input']['bytes'] and result['force_gbnf'] is False
    assert result['normal_cpp_lifetime_completed'] is True and result['common_module_process_lifetime_pinned'] is True
    output=directory/'result.output.bin'
    assert normal(result['output_path'])==normal(output) and output.stat().st_size<=4194304
    assert sha(output)==result['output_sha256'] and output.stat().st_size==result['output_bytes'] and result['output_bytes']>0
    assert parse_json((directory/'result.json').read_bytes())==result
    expected={Path(r['path']).name.lower():r for r in p['runtime_files'] if r['path'].lower().endswith('.dll')}
    snapshots=[]
    for key in ('native_modules_before','native_modules_after'):
        seen={}
        for module in result[key]:
            name=module['name'].lower(); assert name in expected and name not in seen
            r=expected[name]
            assert normal(module['path'])==normal(r['path']) and module['sha256']==r['sha256'] and module['bytes']==r['bytes']
            seen[name]=(normal(module['path']),module['sha256'],module['bytes'])
        assert 'llama-common.dll' in seen
        snapshots.append(seen)
    assert snapshots[0]==snapshots[1], 'Unexpected late native module change'
    returned=output.read_bytes()
    if stage['mode']=='roundtrip':
        if typed(parse_json(returned))!=typed(parse_json(Path(stage['input']['path']).read_bytes())):
            return 'abi_roundtrip_semantic_difference',result
        return 'abi_roundtrip_passed',result
    text=returned.decode('utf-8')
    if not text or text.startswith('%') or not (text.startswith('root ::=') or '\nroot ::=' in text): return 'unsupported_backend',result
    return 'converter_returned_without_diagnostics',result


def dry_run(p, pins, expected):
    out=ROOT/'data/cache'/('r09-converter-dry-run-'+str(time.time_ns()))
    state=install_guards(p,'dry-run',out)
    journal=RunJournal(out,kind='build'); started=time.monotonic(); end=started+120
    try:
        with stable_files([Path(r['path']) for r in pins]+[PROTOCOL],deadline=end):
            verify_pins(pins,end)
            assert all(sha(s['input']['path'])==s['input']['sha256'] for s in p['stages'])
            assert typed({'bool':True})!=typed({'bool':1}) and typed([1])!=typed([1.0])
            assert typed(parse_json(Path(p['stages'][0]['input']['path']).read_bytes()))==typed(p['roundtrip_fixture'])
            corpus=parse_json(Path(p['corpus']['path']).read_bytes())
            assert len(corpus)==109 and {hashlib.sha256(r['schema_json'].encode()).hexdigest() for r in corpus}=={p['schema_sha256']}
            assert sha(p['stages'][1]['input']['path'])==p['schema_sha256']
            assert not Path(p['output']).exists() and not Path(p['execution_claim']).exists()
            journal.append('dry_run_verified',protocol_sha256=expected,immutable_inputs=len(pins),native_dispatches=0)
        assert state['dispatches']==0 and not state['denied']
        report=dict(schema_version=1,status='preparation_validated_no_native_dispatch',protocol_sha256=expected,
            immutable_inputs=len(pins),stages=2,native_children=0,llama_dlls_loaded=0,model_calls=0,
            no_execution_output_or_claim_created=True,guards=state,elapsed_seconds=time.monotonic()-started)
        write_new(out/'dry-run-report.json',report)
        return report,out
    except BaseException as error:
        journal.fail(error,'dry-run'); raise
    finally: journal.close()


def execute(p, pins, expected):
    out=Path(p['output']); journal=RunJournal(out,kind='build'); started=time.monotonic(); end=started+120
    state=install_guards(p,'execute',out); records=[]; disposition='not_dispatched'
    try:
        write_new(p['execution_claim'],dict(schema_version=1,protocol_sha256=expected,output=str(out),owner_pid=os.getpid(),once_only=True))
        for folder in ('config','inputs','stages'): (out/folder).mkdir()
        archive=[(PROTOCOL,out/'config/protocol.json'),(Path(__file__),out/'config/operator-helper.py'),
                 (Path(p['accepted_software']['wheel']['path']),out/'config/accepted-software.whl')]
        archive += [(Path(r['path']),out/'config'/f'provenance-{i:02d}-{Path(r["path"]).name}') for i,r in enumerate(p['provenance_files'])]
        for source,target in archive: copy_new(source,target)
        write_new(out/'config/effective-software.json',p['accepted_software'])
        write_new(out/'config/effective-native-manifest.json',p['runtime_files'])
        for stage in p['stages']:
            Path(stage['cwd']).mkdir()
            copy_new(stage['input']['path'],out/'inputs'/f'{stage["mode"]}.json')
        immutable=[Path(r['path']) for r in pins]+[PROTOCOL]+[target for _,target in archive]+list((out/'inputs').glob('*.json'))
        with stable_files(immutable,deadline=end):
            verify_pins(pins,end)
            journal.append('native_converter_inputs_qualified',protocol_sha256=expected,immutable_files=len(immutable),source_schema_sha256=p['schema_sha256'])
            for stage in p['stages']:
                deadline_check(end)
                record=run_child(stage,journal,state,end)
                try:
                    classification,result=validate_native_result(p,stage,record)
                except (AssertionError,KeyError,ValueError,TypeError,OSError) as error:
                    classification='abi_native_contract_mismatch' if stage['mode']=='roundtrip' else 'conversion_native_contract_mismatch'
                    result=dict(validation_error_class=type(error).__name__,validation_error_message=str(error)[:2048])
                records.append(dict(mode=stage['mode'],classification=classification,attempt=record,program_result=result))
                journal.append('native_converter_stage_reviewed',mode=stage['mode'],classification=classification)
                if classification not in ('abi_roundtrip_passed','converter_returned_without_diagnostics'):
                    disposition='closed_negative_'+classification; break
                disposition='abi_and_converter_returned_cleanly_native_grammar_still_pending'
            verify_pins(pins,end)
            assert state['dispatches']==len(records)<=2 and not state['denied']
            deadline_check(end)
            summary=dict(schema_version=1,status=disposition,protocol_sha256=expected,records=records,
                native_children=state['spawned_children'],dispatch_attempts=state['dispatches'],maximum_native_children=2,model_calls=0,servers=0,vocabulary_loads=0,
                gguf_reads=0,provider_spend_usd=0,native_grammar_conformance='not_established',
                elapsed_seconds=time.monotonic()-started,guards={k:v for k,v in state.items() if not k.startswith('active_')})
            write_new(out/'terminal-report.json',summary)
            journal.append('native_converter_terminal',status=disposition,children=state['dispatches'],terminal_report_sha256=sha(out/'terminal-report.json'))
        journal.close()
        events=read_chain(out/'journal.jsonl')
        outputs={path.relative_to(out).as_posix():dict(sha256=sha(path),bytes=path.stat().st_size)
                 for path in out.rglob('*') if path.is_file()}
        receipt=dict(schema_version=1,kind='finite_converter_terminal_artifact_inventory_v1',protocol_sha256=expected,
            disposition=disposition,journal_tip_sha256=events[-1]['sha256'],outputs=outputs,
            semantic_scope='Fixed diagnostic harness evidence; not AsOf dossier/scientific validation')
        write_new(out/'receipt.json',receipt)
        return summary,out
    except BaseException as error:
        try: journal.fail(error,'native-converter')
        except BaseException as secondary: error.add_note('Failure journaling also failed: '+type(secondary).__name__)
        failure=dict(schema_version=1,status='failed',error_class=type(error).__name__,message=str(error)[:4096],
            protocol_sha256=expected,records=records,observed_dispatch_attempts=state['dispatches'],known_spawned_children=state['spawned_children'],
            recovery_action='Inspect only; never automatically repeat this protocol',guards=state)
        try: write_new(out/'failure.json',failure)
        except BaseException as secondary: error.add_note('Failure marker also failed: '+type(secondary).__name__)
        raise
    finally: journal.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--dry-run',action='store_true'); modes.add_argument('--execute',action='store_true')
    parser.add_argument('--protocol-sha256',required=True)
    args=parser.parse_args()
    p,pins=load_protocol(args.protocol_sha256)
    report,out=dry_run(p,pins,args.protocol_sha256) if args.dry_run else execute(p,pins,args.protocol_sha256)
    print(json.dumps(dict(status=report['status'],output=str(out),native_children=report.get('native_children',0),
        receipt_sha256=sha(out/'receipt.json') if (out/'receipt.json').is_file() else None)))


if __name__=='__main__': main()
