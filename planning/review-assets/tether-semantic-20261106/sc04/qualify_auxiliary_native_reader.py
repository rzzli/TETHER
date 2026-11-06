"""Reconstruct retained actual-model fictional expansion/ranking responses."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from experiments.litqa_analysis import auxiliary_native as a,native_records as n


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);rows=[]
    try:
        root=ROOT/'data/cache/sc04-controller-qualification-attempt01'
        raw=n.read(root/'ROOT-RECEIPT.json');n.need(n.digest(raw)=='8de520bfdef4dbe7b6363aeb962b8c4bb453adc475297aca2fa08d88e7c10cf0','Original fictional root anchor')
        receipt=n.decode(raw)
        for item in receipt['files'].values():n.verify_proof(item)
        frame=n.load(root/'FRAME.json');n.need(frame['purpose']=='fictional_qualification','Fictional records only')
        path=ROOT/'experiments/litqa_comparison/codecs.py'
        code=dict(path=str(path),sha256=frame['code_pins']['experiments/litqa_comparison/codecs.py'],bytes=path.stat().st_size)
        for task in ('expand','rank'):
            info=n.load(root/task/'worker/MODEL.json');complete=n.load(root/task/'worker/COMPLETE.json')
            report=n.load(root/task/'worker/phase/REPORT.json')
            for row in report['rows']:
                cell=root/task/'worker/phase/products'/f'{row["ordinal"]:04d}';query=n.load(cell/'INPUT.json')['query']
                result=a.reconstruct(cell,query,task=task,model_provenance=info['provenance'],alias=info['alias'],
                    owner_pid=complete['server_terminal']['pid'],configuration=frame['generation_configuration'],code_proof=code,
                    expected_endpoint=f'http://{info["spec"]["host"]}:{info["spec"]["port"]}')
                rows.append(dict(task=task,id=row['id'],branch=row['branch'],status=result['summary']['status'],
                                 usage=result['summary']['usage'],decoded=result['prediction']))
        n.need(len(rows)==6 and all(row['status']=='completed' for row in rows),'All six original auxiliary calls reconstructed')
        report=dict(status='PASS',native_auxiliary_records=6,results=rows,model_dispatches=0,network_calls=0,production_predictions_scored=0,
            sources_sha256={str(path.relative_to(ROOT)):n.digest(n.read(path)) for path in
                            (ROOT/'experiments/litqa_analysis/native_records.py',ROOT/'experiments/litqa_analysis/auxiliary_native.py',Path(__file__))},
            scope='Independent question-only expansion/ranking prompt, grammar, output, usage and exact native-event reconstruction; full phase/source-parent joins remain separate.')
        (args.output/'QUALIFICATION.json').write_bytes(n.canonical(report)+b'\n')
        print(json.dumps({key:report[key] for key in ('status','native_auxiliary_records','model_dispatches','network_calls')}))
    except BaseException as error:
        (args.output/'FAILURE.json').write_bytes(n.canonical(dict(error_type=type(error).__name__,message=str(error),completed=len(rows)))+b'\n');raise


if __name__=='__main__':main()
