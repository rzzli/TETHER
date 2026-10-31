"""Explicit matching installed 0.3.5 replay; never load live or archived code."""
import hashlib
from importlib import metadata
import importlib.abc
import json
import os
from pathlib import Path
import sys
import time

ROOT, REPORT = (Path(x).resolve() for x in sys.argv[1:])
ENV = Path(sys.prefix).resolve()
BUNDLE = ROOT / 'data/reference/recovery-r09-retrieval-restored-20261026'
ANCHOR = '11dcbbed608beea93abb4303ff2d77b988994205b133b2d07aaa465143c01b50'
assert sys.flags.isolated and metadata.version('asof-target-agents') == '0.3.5'
attempts = dict(reads=[], imports=[], dispatch=[])


def under(path, root):
    try:
        return os.path.commonpath([path, os.path.normcase(str(root))]) == os.path.normcase(str(root))
    except ValueError:
        return False


def audit(event, args):
    if event in ('open', 'os.listdir', 'os.scandir') and args and isinstance(args[0], (str, bytes, os.PathLike)):
        name = os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if under(name, ROOT) and not any(under(name, p) for p in (ENV, BUNDLE, Path(__file__), REPORT.parent)):
            attempts['reads'].append(name)
            raise PermissionError('Only installed verifier and restored bundle are allowed')
        if name.startswith('e:'):
            attempts['reads'].append(name)
            raise PermissionError('No original E data needed for invented replay')
    if event in ('subprocess.Popen', 'os.system', 'socket.connect', 'socket.getaddrinfo'):
        attempts['dispatch'].append(event)
        raise PermissionError('Replay cannot dispatch')


class NoTools(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tools', 'planning'):
            attempts['imports'].append(fullname)
            raise ImportError('Repository runtime import denied')


sys.meta_path.insert(0, NoTools())
sys.addaudithook(audit)
from asof.serde import encode
from asof.study.retrieval_smoke import verify

started = time.monotonic()
assert hashlib.sha256((BUNDLE / 'receipt.json').read_bytes()).hexdigest() == ANCHOR
result = encode(verify(BUNDLE, ANCHOR))
assert all(not x for x in attempts.values())
REPORT.write_text(json.dumps(dict(status='passed', version='0.3.5', isolated=True,
    bundle=str(BUNDLE), receipt_sha256=ANCHOR, result=result, attempts=attempts,
    elapsed_seconds=time.monotonic()-started), indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(status='passed', version='0.3.5', attempts=attempts)))
