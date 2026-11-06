"""Invented admission-capacity probe: no external HTTP or model execution."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[5]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]
tempfile.tempdir=str(ROOT/'data/cache')
from experiments.litqa_comparison.tests.test_admission import AdmissionTests
from experiments.litqa_comparison import codecs


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    f=AdmissionTests('runTest');f.setUp()
    try:
        f.query['choices'][0]='(A) '+('α'*2400)
        try:
            f.capture()
        except codecs.PayloadCapacityError as error:
            disposition=dict(status='reproduced',error_type=type(error).__name__,message=str(error))
        else:
            raise AssertionError('Expected frozen admission to reject the overcapacity prompt before model_call')
        result=dict(kind='invented_sc04_admission_capacity_probe',created_at_utc=datetime.now(timezone.utc).isoformat(),
            qualification_only=True,production_cases_read=False,real_http_requests=0,model_dispatches=0,
            query_id=f.query['id'],changed_choice_utf8_bytes=len(f.query['choices'][0].encode()),
            changed_choice_ascii_json_bytes=len(json.dumps(f.query['choices'][0],ensure_ascii=True).encode()),
            disposition=disposition,source_manifest_sha256=sha(f.f.root/'MANIFEST.json'),
            scope='The existing invented HTTP fixture supplies sources. capture() raises before its context returns; '
                  'pipeline.execute calls model_call only after capture returns. No provider is invoked.',
            finding='Answer capacity does not reach the per-cell graceful capacity handler in the frozen primary/supplied admission path.',
            frozen_sources={name:sha(ROOT/name) for name in (
                'experiments/litqa_comparison/admission.py','experiments/litqa_comparison/pipeline.py',
                'experiments/litqa_comparison/transport.py','experiments/litqa_comparison/codecs.py',
                'experiments/litqa_supplied/admission.py','experiments/litqa_comparison/tests/test_admission.py',
                'experiments/litqa_comparison/tests/test_acquisition.py')})
        destination=Path(__file__).with_name('CAPACITY-PROBE.json')
        with destination.open('xb') as stream:
            stream.write(json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2).encode()+b'\n')
        print(json.dumps(dict(status='reproduced',report=str(destination),sha256=sha(destination))))
    finally:f.doCleanups()

if __name__=='__main__':main()
