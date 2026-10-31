"""Explicit installed source/token replay with live repository code unavailable."""
import hashlib
import importlib.abc
from importlib import metadata
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(sys.argv[1]).resolve()
REPORT = Path(sys.argv[2]).resolve()
ENV = Path(sys.prefix).resolve()
HERE = Path(__file__).resolve().parent
record = json.loads((HERE/'REAL-PREPARATION.json').read_bytes())
authority = json.loads((HERE/'SOURCE-AUTHORITY-v1.json').read_bytes())
raw = Path(r'E:\projects_data\drug_target_agents_data')
run = Path(record['output'])
assert sys.flags.isolated and metadata.version('asof-target-agents') == '0.3.4'
assert metadata.version('pyarrow') == '21.0.0'
with (run/'receipt.json').open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == record['receipt_sha256']
roots = {'project': ROOT, 'raw': raw}
allowed_source = {os.path.normcase(str(roots[p['root_id']].joinpath(*p['relative_path'].split('/'))))
                  for p in authority['files'].values()}
attempts = dict(live_code=[], unapproved_source=[], imports=[], dispatch=[])


def normalized(path):
    return os.path.normcase(os.path.abspath(os.fsdecode(path)))


def under(path, root):
    try:
        return os.path.commonpath([path, normalized(root)]) == normalized(root)
    except ValueError:
        return False


def audit(event, args):
    if event in ('open', 'os.listdir', 'os.scandir') and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = normalized(args[0])
        if under(path, ROOT/'src') or under(path, ROOT/'.venv'):
            attempts['live_code'].append(path)
            raise PermissionError('Live source/development environment unavailable')
        if event == 'open' and (under(path, ROOT) or under(path, raw)):
            if path not in allowed_source and not any(under(path, approved) for approved in (ENV, run, REPORT.parent, Path(__file__))):
                attempts['unapproved_source'].append(path)
                raise PermissionError('Source outside explicit preparation authority')
    if event in ('subprocess.Popen', 'socket.connect'):
        attempts['dispatch'].append(event)
        raise PermissionError('Read-only replay cannot dispatch')


class NoRepositoryModules(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tools', 'planning'):
            attempts['imports'].append(fullname)
            raise ImportError('Repository-only runtime imports unavailable')


sys.meta_path.insert(0, NoRepositoryModules())
sys.addaudithook(audit)
from asof.serde import encode, fingerprint
from asof.study.source_preparation import verify_source_preparation
from asof.study.tokenization import verify_tokenization
from asof.study.preparation_payloads import prepare_payloads
from asof.serde import read_json

started = time.monotonic()
source = verify_source_preparation(run/'source', record['source_receipt_sha256'],
    record['source_authority_sha256'], roots, deadline=time.monotonic()+300)
payloads = prepare_payloads(read_json(run/'source/request.json'))
spec = read_json(run/'tokenizer-spec.json')
assert len(payloads) == len(record['records']) == 6
for cell, item in zip(payloads, record['records']):
    assert cell['payload_sha256'] == item['payload_sha256']
    verify_tokenization(run/f"token-{item['index']:02d}", item['receipt_sha256'],
        item['prompt_sha256'], fingerprint(spec), expected_payload_sha256=item['payload_sha256'])
assert not any(attempts.values())
result = dict(schema_version=1, status='passed_installed_source_and_token_replay',
              installed_environment=str(ENV), optional_dependency='pyarrow==21.0.0',
              source=encode(source), quote_count=6, input_reservation=record['input_reservation'],
              original_data_access='27 explicitly approved files only',
              original_request_sha256=source['request_sha256'], guards=attempts,
              elapsed_seconds=time.monotonic()-started, generation_calls=0,
              scientific_validation='not_performed', whole_R09_complete=False)
with REPORT.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
