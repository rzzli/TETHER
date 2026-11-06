"""Apply the qualified production output auditor to the retained real-model rehearsal."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT),str(ROOT/'src')]
from experiments.scifact_comparison.audit import verify_outputs
from experiments.scifact_comparison.prepare import pin,write

assets = ROOT/'planning/review-assets/tether-semantic-20261106/sc03'
output = assets/'production-auditor-rehearsal01'
output.mkdir(parents=True,exist_ok=False)
source = assets/'worker-rehearsal-freeze01/fictional-requests.jsonl'
requests = [json.loads(line) for line in source.read_bytes().splitlines()]
try:
    result = verify_outputs(ROOT/'data/benchmark/scifact_comparison/worker-rehearsal-20261106-attempt01',
        '1b65514097fb05108128510a2dc0485b8386ed8e250c5d6335f3f12062721f31',requests,expected_condition='primary')
    write(output/'VERIFIED.json',dict(status='PASS',counts=result['counts'],
        source=pin(source),auditor=pin(ROOT/'experiments/scifact_comparison/audit.py'),
        model_reexecuted=False,receipt_sha256=result['receipt_sha256']))
    print(json.dumps(dict(status='PASS',counts=result['counts'],report=pin(output/'VERIFIED.json'))))
except BaseException as error:
    write(output/'FAILED.json',dict(status='FAIL',error_type=type(error).__name__,error=str(error)))
    raise
