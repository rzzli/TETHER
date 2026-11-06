"""Execute the five frozen SC03 conditions sequentially, without implicit retries."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT),str(ROOT/'src')]
from experiments.scifact_comparison.prepare import pin,read,write
from experiments.scifact_comparison.inputs import CONDITIONS,need,encoded
from experiments.scifact_multivers_supervision.supervise import supervise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frame',type=Path,required=True)
    parser.add_argument('--frame-sha256',required=True)
    args = parser.parse_args()
    need(pin(args.frame)['sha256'] == args.frame_sha256,'Production frame anchor differs')
    frame = read(args.frame)
    need(frame['condition_order'] == list(CONDITIONS),'Frozen condition order differs')
    output = Path(frame['run_output'])
    output.mkdir(parents=True,exist_ok=False)
    anchors = dict(condition_order=list(CONDITIONS),conditions={},frame_sha256=args.frame_sha256)
    events = (output/'events.jsonl').open('xb',buffering=0)
    def event(kind,**details):
        events.write(encoded(dict(event=kind,utc=datetime.now(timezone.utc).isoformat(),**details))+b'\n')
    try:
        event('started')
        for proof in frame['pins']:
            need(pin(proof['path']) == proof,'Scientific input/source changed before production')
        for condition in CONDITIONS:
            proof = frame['conditions'][condition]
            event('condition_started',condition=condition,manifest_sha256=proof['sha256'])
            result = supervise(proof['path'],proof['sha256'])
            manifest = read(proof['path'])
            outcome = pin(Path(manifest['launch_output'])/'OUTCOME.json')
            need(result['status'] == 'completed','Condition failed; inspect, do not repeat: '+condition)
            child = Path(manifest['qualification_output'])
            anchors['conditions'][condition] = dict(supervisor_outcome=outcome,worker_receipt=pin(child/'RECEIPT.json'))
            write(output/(condition+'-anchor.json'),anchors['conditions'][condition])
            event('condition_completed',condition=condition,receipt_sha256=anchors['conditions'][condition]['worker_receipt']['sha256'])
            print(json.dumps(dict(condition=condition,status='completed',report=read(child/'REPORT.json'))),flush=True)
        for proof in frame['pins']:
            need(pin(proof['path']) == proof,'Scientific source changed during production')
        write(output/'RESULT-ANCHORS.json',anchors)
        event('completed')
        print(json.dumps(dict(status='completed',anchors=pin(output/'RESULT-ANCHORS.json'))),flush=True)
    except BaseException as error:
        write(output/'FAILED.json',dict(status='FAIL',error_type=type(error).__name__,error=str(error),completed_conditions=list(anchors['conditions']),automatic_retry=False))
        event('failed',error_type=type(error).__name__)
        raise
    finally:
        events.close()


if __name__ == '__main__':
    main()
