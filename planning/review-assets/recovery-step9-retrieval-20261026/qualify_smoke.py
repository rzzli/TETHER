"""Finite invented retrieval qualification; deny original data and all dispatch."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

from asof.serde import encode
from asof.study.retrieval_smoke import smoke, verify

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = ROOT/'data/cache'/('r09-retrieval-qualified-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
attempts = dict(original_data=[], dispatch=[])


def audit(event, args):
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if path.startswith(os.path.normcase('E:\\')) or any(
                part.lower() in ('benchmark','gold_evidence','adjudication','completed-responses')
                for part in Path(path).parts):
            attempts['original_data'].append(path)
            raise PermissionError('Original/evaluation data unavailable to invented smoke')
    if event in ('subprocess.Popen','socket.connect'):
        attempts['dispatch'].append(event)
        raise PermissionError('Invented qualification cannot dispatch')


sys.addaudithook(audit)
started = time.monotonic()
result = smoke(OUT)
outer_elapsed = time.monotonic()-started
replay_start = time.monotonic()
replayed = verify(OUT, result['receipt_sha256'])
assert not any(attempts.values())
report = dict(schema_version=1, status='invented_retrieval_qualification_passed',
              output=str(OUT), result=encode(result), replay=encode(replayed),
              outer_preparation_and_sealing_seconds=outer_elapsed,
              read_only_replay_seconds=time.monotonic()-replay_start,
              guards=attempts, actual_model_calls=0, tokenizer_calls=0,
              provider_spending_usd=0, real_universe_expansion=False,
              scientific_validation='not_performed', entire_R09_complete=False)
with (HERE/'QUALIFICATION.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(report))
