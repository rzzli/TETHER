"""Exercise the independent reader on retained real-model fictional responses."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from experiments.litqa_analysis import native_records as n

RUNS=(
    ('data/cache/sc04-controller-qualification-attempt01','8de520bfdef4dbe7b6363aeb962b8c4bb453adc475297aca2fa08d88e7c10cf0'),
    ('data/cache/sc04-supplied-controller-qualification-attempt01','f9dd1f8b8d0a560730d0450cec03647ec8adcba5d23e0836c16e6af03c1cf19c'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);results=[]
    try:
        for relative,anchor in RUNS:
            root=ROOT/relative;raw=n.read(root/'ROOT-RECEIPT.json');n.need(n.digest(raw)==anchor,'Historical qualification root anchor')
            receipt=n.decode(raw)
            for item in receipt['files'].values():n.verify_proof(item)
            frame=n.load(root/'FRAME.json');n.need(frame['purpose']=='fictional_qualification','Fictional responses only')
            info=n.load(root/'answer/worker/MODEL.json');complete=n.load(root/'answer/worker/COMPLETE.json')
            stage=n.load(root/'answer/worker/phase/REPORT.json');path=ROOT/'experiments/litqa_comparison/codecs.py'
            code=dict(path=str(path),sha256=frame['code_pins']['experiments/litqa_comparison/codecs.py'],bytes=path.stat().st_size)
            for row in stage['rows']:
                cell=root/'answer/worker/phase/products'/f'{row["ordinal"]:04d}';query=n.load(cell/'INPUT.json')['query']
                actual=n.reconstruct(cell,query,model_provenance=info['provenance'],alias=info['alias'],
                    owner_pid=complete['server_terminal']['pid'],configuration=frame['generation_configuration'],code_proof=code)
                results.append(dict(run=relative,id=row['id'],branch=row['branch'],status=actual['summary']['status'],
                    usage=actual['summary']['usage'],answer_index=actual['prediction']['answer_index'],
                    wrong_fictional_abstention=actual['prediction']['answer_index']==1))
        n.need(len(results)==10 and all(r['status']=='completed' for r in results),'All retained fictional answer cells reconstructed')
        report=dict(status='PASS',native_answer_records=10,results=results,
            reader_sha256=n.digest(n.read(ROOT/'experiments/litqa_analysis/native_records.py')),
            helper_sha256=n.digest(n.read(Path(__file__))),model_dispatches=0,production_predictions_scored=0,
            scope='Independent frozen prompt, native output, measured usage and call-record reconstruction; known semantic failures unchanged.')
        (args.output/'QUALIFICATION.json').write_bytes(n.canonical(report)+b'\n')
        print(json.dumps({k:report[k] for k in ('status','native_answer_records','model_dispatches','production_predictions_scored')}))
    except BaseException as error:
        (args.output/'FAILURE.json').write_bytes(n.canonical(dict(error_type=type(error).__name__,message=str(error),completed=len(results)))+b'\n');raise


if __name__=='__main__':main()
