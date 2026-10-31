"""Finite planning probe. All writes stay in a newly reserved workspace directory."""
import ast
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = ROOT / 'data/cache/r09-windows-lock-probe-v1'
OUT.mkdir(exist_ok=False)
report = {'schema_version': 1, 'role': 'planning_only', 'generation_calls': 0,
          'provider_spend_usd': 0, 'runtime_changes': False, 'asset_checks': []}
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                              wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
kernel.CreateFileW.restype = wintypes.HANDLE
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.CloseHandle.restype = wintypes.BOOL
INVALID = ctypes.c_void_p(-1).value
held = []


def lock(path, directory=False):
    handle = kernel.CreateFileW(str(path), 0x80000000, 3 if directory else 1,
                                None, 3, 0x02000000 if directory else 0x80, None)
    if handle == INVALID:
        raise ctypes.WinError(ctypes.get_last_error())
    held.append(handle)


def release():
    while held:
        if not kernel.CloseHandle(held.pop()):
            raise ctypes.WinError(ctypes.get_last_error())


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def publish():
    target = HERE / ('LOCK-PROBE-RESULT.json' if report.get('status') == 'passed'
                     else 'LOCK-PROBE-FAILURE.json')
    with target.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)


try:
    start = time.monotonic()
    assert os.name == 'nt'
    fixture = OUT / 'invented.txt'
    fixture.write_bytes(b'invented stable-read fixture')
    lock(fixture)
    attempts = {}
    for name in ('write', 'delete', 'rename'):
        try:
            if name == 'write':
                fixture.write_bytes(b'must not succeed')
            elif name == 'delete':
                fixture.unlink()
            else:
                fixture.rename(OUT / 'renamed.txt')
        except OSError as error:
            attempts[name] = {'denied': True, 'winerror': error.winerror}
        else:
            raise AssertionError('Invented fixture mutation was not denied: ' + name)
    release()
    fixture.write_bytes(b'after release')
    renamed = fixture.rename(OUT / 'renamed.txt')
    renamed.unlink()
    report['invented_mutations'] = attempts
    report['invented_mutations_after_release_succeeded'] = True

    inventory = json.loads((ROOT / 'planning/review-assets/recovery-step5-20261026/inventory.json').read_bytes())
    assets = [a for a in inventory['assets'] if a['path'].lower().endswith(('.dll', '.gguf', 'llama-tokenize.exe'))]
    assert len(assets) == 34
    exe = next(Path(a['path']) for a in assets if a['path'].endswith('llama-tokenize.exe'))
    model = next(Path(a['path']) for a in assets if '00001-of-00003.gguf' in a['path'])
    model_root = model.parent
    directories = {model_root, exe.parent}
    for directory in sorted(directories):
        lock(directory, True)
    for asset in assets:
        path = Path(asset['path'])
        assert path.is_relative_to(model_root) and not path.is_symlink()
        lock(path)
    assert {p.resolve() for p in exe.parent.glob('*.dll')} == {
        Path(a['path']).resolve() for a in assets if a['path'].lower().endswith('.dll')}
    for asset in assets:
        path = Path(asset['path'])
        actual = sha(path)
        assert actual == asset['sha256'] and path.stat().st_size == asset['bytes']
        report['asset_checks'].append({'path': str(path), 'sha256': actual, 'bytes': asset['bytes']})
    report['pre_hash_seconds'] = time.monotonic() - start
    measurements = ROOT / 'planning/review-assets/recovery-step9-comparison-20261026/tokenizer-measurement-v1'
    prior = json.loads((measurements / 'RESULT.json').read_bytes())['measurements'][0]
    prompt = (ROOT / 'data/cache/r09-tokenizer-measurement-v1/00.prompt.bin').read_bytes()
    assert hashlib.sha256(prompt).hexdigest() == prior['prompt_sha256']
    argv = [str(exe), '--offline', '--model', str(model), '--no-escape', '--no-bos',
            '--stdin', '--ids', '--show-count']
    env = {k: v for k, v in os.environ.items() if not k.startswith(('LLAMA_', 'HF_', 'HUGGING_FACE'))}
    env['LLAMA_ARG_OFFLINE'] = '1'
    child_start = time.monotonic()
    result = subprocess.run(argv, input=prompt, capture_output=True, timeout=30,
                            env=env, cwd=exe.parent, creationflags=subprocess.CREATE_NO_WINDOW)
    (OUT / 'stdout.bin').write_bytes(result.stdout)
    (OUT / 'stderr.bin').write_bytes(result.stderr)
    report.update(argv=argv, exit_code=result.returncode, child_seconds=time.monotonic()-child_start)
    assert result.returncode == 0
    text = result.stdout.decode('utf-8')
    matches = re.findall(r'\[[\d, \r\n-]+\]', text)
    assert len(matches) == 1
    ids = ast.literal_eval(matches[0])
    counts = re.findall(r'Total number of tokens:\s*(\d+)', text.replace(matches[0], ''))
    assert len(counts) == 1 and int(counts[0]) == len(ids) == prior['cli_tokens']
    report.update(prompt_sha256=prior['prompt_sha256'], count=len(ids), expected_count=prior['cli_tokens'])
    for asset in assets:
        assert sha(Path(asset['path'])) == asset['sha256']
    assert {p.resolve() for p in exe.parent.glob('*.dll')} == {
        Path(a['path']).resolve() for a in assets if a['path'].lower().endswith('.dll')}
    report.update(status='passed', elapsed_seconds=time.monotonic()-start,
                  locked_files=len(assets), locked_directories=len(directories),
                  post_hashes_match=True, tokenizer_calls=1)
except BaseException as error:
    report.update(status='failed', error_class=type(error).__name__, error=str(error))
    publish()
    raise
else:
    publish()
finally:
    release()
