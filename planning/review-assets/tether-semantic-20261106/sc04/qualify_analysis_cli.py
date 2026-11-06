"""Read-only qualification of the final analysis CLI and retained failure controls."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
SUCCESS=ROOT/'data/cache/sc04-analysis-cli-qualification-attempt03'
SUCCESS_SHA='a3aafe838e864f28485863fc3eff8d118e5eaa8cbe0d18e9237bdc52fbd2463c'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def proof(path):return dict(path=str(Path(path).absolute()),bytes=Path(path).stat().st_size,sha256=sha(Path(path).read_bytes()))


def check_inventory(root,expected_sha):
    receipt=load(root/'RECEIPT.json');assert sha((root/'RECEIPT.json').read_bytes())==expected_sha
    actual={p.relative_to(root).as_posix():proof(p) for p in root.rglob('*') if p.is_file() and p!=root/'RECEIPT.json'}
    assert receipt['status']=='complete' and receipt['files']==actual
    return len(actual)


def chain(path):
    previous=None;events=[];raw=path.read_bytes();assert raw.endswith(b'\n')
    for number,line in enumerate(raw.splitlines()):
        event=json.loads(line);fingerprint=event.pop('sha256')
        assert event['sequence']==number and event['previous_sha256']==previous and sha(canonical(event))==fingerprint
        previous=fingerprint;events.append(event)
    return events


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--success',type=Path,default=SUCCESS)
    parser.add_argument('--success-sha256',default=SUCCESS_SHA)
    parser.add_argument('--controls',type=Path,default=ROOT/'planning/review-assets/tether-semantic-20261106/sc04/analysis-controls-attempt11/QUALIFICATION.json')
    args=parser.parse_args();success=args.success.absolute()
    args.output.mkdir(parents=True,exist_ok=False)
    count=check_inventory(success,args.success_sha256);complete=load(success/'COMPLETE.json');frame=load(success/'FRAME.json')
    assert complete['purpose']==frame['purpose']=='fictional_qualification' and frame['analysis_inputs'] is None
    assert complete['worker_receipt']==proof(success/'worker/RECEIPT.json')
    count+=check_inventory(success/'worker',complete['worker_receipt']['sha256'])
    for p in frame['code_proofs'].values():assert proof(p['path'])==p
    summary=load(success/'worker/RESULTS.json');native=load(success/'worker/NATIVE-AGREEMENT.json');percase=load(success/'worker/PER-CASE.json')
    assert summary['scheduled_count']==2 and set(summary['arms'])=={'L/O','E/O','L/R','E/R','supplied'}
    assert native['status']=='PASS' and native['arms_checked']==5
    for arm,row in summary['arms'].items():
        assert row['scheduled_count']==2 and row['counts']['raw_correct']==row['counts']['correct_and_admitted']==1
        assert row['counts']['native_unsure']==1 and row['raw_metrics']==row['checked_metrics']==dict(accuracy=.5,coverage=.5,precision=1.)
        assert len(percase[arm]['scored'])==len(percase[arm]['sources'])==2
        for case in row['case_results']:
            assert case['prediction']['answer_index']==(0 if case['id'].endswith('901') else 1)
    assert len(chain(success/'journal.jsonl'))==5
    worker_events=chain(success/'worker/journal.jsonl')
    assert worker_events[-1]['event']=='analysis_completed'
    supervision=load(success/'SUPERVISION.json');assert supervision['process_reaped'] and supervision['termination_reason']=='exited' and supervision['cleanup_errors']==[]
    timeout=ROOT/'data/cache/sc04-analysis-cli-timeout-attempt02'
    timeout_report=load(timeout/'SUPERVISION.json')
    assert timeout_report['process_reaped'] and timeout_report['termination_reason']=='deadline_exceeded' and timeout_report['cleanup_errors']==[]
    assert not (timeout/'RECEIPT.json').exists() and not (timeout/'worker/RECEIPT.json').exists()
    assert load(timeout/'FAILURE.json')['automatic_retry'] is False and chain(timeout/'journal.jsonl')[-1]['event']=='analysis_failed'
    assert chain(timeout/'worker/journal.jsonl')[-1]['event']=='primary_verification_started'
    missing=ROOT/'data/cache/sc04-analysis-cli-missing-attempt01'
    assert load(missing/'worker/FAILURE.json')['error_type']=='FileNotFoundError' and not (missing/'RECEIPT.json').exists()
    assert load(missing/'SUPERVISION.json')['process_reaped'] and chain(missing/'journal.jsonl')[-1]['event']=='analysis_failed'
    controls=load(args.controls)
    assert controls['status']=='PASS' and controls['failures']==controls['errors']==controls['skipped']==0
    for name,fingerprint in controls['source_sha256'].items():
        name=Path(name).as_posix()
        assert name in frame['code_proofs'] and frame['code_proofs'][name]['sha256']==fingerprint
    resources=load(success/'worker/RESOURCES.json')
    result=dict(status='PASS',successful_attempt=proof(success/'RECEIPT.json'),files_checked_in_nested_inventories=count,
        controls=proof(args.controls),qualification_helper=proof(Path(__file__)),
        source_pins_checked=len(frame['code_proofs']),full_controls=controls['tests'],answer_records=10,arms=5,correct_per_arm=1,questions_per_arm=2,
        worker_seconds=resources['analysis_wall_seconds'],worker_peak_memory_bytes=resources['analysis_process']['process_peak_working_set_bytes'],
        total_supervised_seconds=supervision['total_elapsed_seconds'],provider_spend_usd=0,
        failed_attempts=[dict(path=str(ROOT/'data/cache/sc04-analysis-cli-qualification-attempt01'),reason='Platform helper blocked; fixed native OS-version identity.'),
            dict(path=str(ROOT/'data/cache/sc04-analysis-cli-timeout-attempt01'),reason='Supervisor exception diagnostics attribute was not retained; fixed and regression added.')],
        timeout_control=proof(timeout/'SUPERVISION.json'),missing_input_control=proof(missing/'worker/FAILURE.json'),
        failure_control_scope='Retained earlier failure controls; no rerun for the trailing-newline-only runner change. Regression suite is current.',
        scope='End-to-end offline fictional analysis and failure handling. No new inference, public acquisition, production scoring or scientific validity established.')
    (args.output/'QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
