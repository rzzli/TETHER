"""Freeze every SC03 condition and scientific analysis before development inference."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT),str(ROOT/'src')]
from experiments.scifact_comparison.inputs import CONDITIONS,need
from experiments.scifact_comparison.prepare import pin,read,write

ASSETS = ROOT/'planning/review-assets/tether-semantic-20261106'
SC03 = ASSETS/'sc03'
OUTPUT = SC03/'production-freeze-attempt01'
PREPARED = ROOT/'data/benchmark/scifact_comparison/preparation-20261106-attempt01/MANIFEST.json'
PREPARED_SHA = '90833e941e216d702873fb91786f0175778c72029fb8964453c3159e61bce8c5'


def main():
    OUTPUT.mkdir(parents=True,exist_ok=False)
    try:
        tests = SC03/'production-components-attempt02/QUALIFICATION.json'
        need(read(tests)['status'] == 'PASS' and read(tests)['tests'] == 62,'Production tests not passed')
        for proof in read(tests)['source_pins']:
            need(pin(proof['path']) == proof,'Tested scientific source changed')
        need(pin(PREPARED)['sha256'] == PREPARED_SHA,'Prepared authority differs')
        prepared = read(PREPARED)
        pins = {}
        def retain(path):
            proof = pin(path)
            pins[proof['path']] = proof
            return proof
        for proof in prepared['source_parents']+prepared['source_pins']+[prepared['protocol'],prepared['retrieval']]:
            need(pin(proof['path']) == proof,'Prepared parent/source changed')
            retain(proof['path'])
        for condition in CONDITIONS:
            for field in ('requests','lineage'):
                proof = prepared['conditions'][condition][field]
                need(pin(proof['path']) == proof,'Prepared condition product changed')
                retain(proof['path'])
        input_review = SC03/'input-review-attempt01/INPUT-REVIEW.json'
        need(read(input_review)['status'] == 'PASS' and read(input_review)['manifest_sha256'] == PREPARED_SHA,'Input review differs')
        auditor = SC03/'production-auditor-rehearsal01/VERIFIED.json'
        need(read(auditor)['status'] == 'PASS' and pin(read(auditor)['auditor']['path']) == read(auditor)['auditor'],
             'Production auditor qualification differs')
        context = read(SC03/'external-model-context-attempt01/PREFLIGHT.json')
        need(context['status'] == 'PASS' and pin(context['model']['path']) == context['model'] and
             pin(context['policy_code']['path']) == context['policy_code'],'External-model policy qualification differs')
        for path in (tests,PREPARED,input_review,auditor,SC03/'external-model-context-attempt01/PREFLIGHT.json',
                     Path(context['model']['path']),Path(__file__),SC03/'run_production.py'):
            retain(path)
        conditions = {}
        rehearsal = SC03/'worker-rehearsal-acceptance01/ACCEPTANCE.json'
        for condition in CONDITIONS:
            condition_output = OUTPUT/condition
            child = ROOT/f'data/benchmark/scifact_comparison/production-20261106-attempt01/{condition}'
            command = [sys.executable,'-I','-B',str(ASSETS/'freeze_sc03_worker.py'),
                '--mode','production','--output',str(condition_output),'--worker-output',str(child),
                '--tests',str(tests),'--tests-sha256',pin(tests)['sha256'],
                '--prepared',str(PREPARED),'--prepared-sha256',PREPARED_SHA,
                '--condition',condition,'--rehearsal-acceptance',str(rehearsal),
                '--rehearsal-sha256','189b54dd1083a80c255b60025655d40f9c0e4267e2ac4695974c23edcb98b8fc']
            completed = subprocess.run(command,cwd=ROOT,capture_output=True,timeout=120)
            with (OUTPUT/(condition+'-freeze.stdout.txt')).open('xb') as stream:
                stream.write(completed.stdout)
            with (OUTPUT/(condition+'-freeze.stderr.txt')).open('xb') as stream:
                stream.write(completed.stderr)
            need(completed.returncode == 0,'Condition freeze failed: '+condition)
            conditions[condition] = retain(condition_output/'MANIFEST.json')
        old = ROOT/'data/benchmark/scifact/native-20261105T234805Z-attempt01'
        old_receipt = read(old/'RECEIPT.json')
        need(pin(old/'RECEIPT.json')['sha256'] == '3a997165aac2f0a85a93890f5e10a66d8117563e380e98f892dd3cb8a93f8968','Baseline anchor differs')
        for relative in ('dispositions.json','evaluation.json'):
            need(pin(old/relative)['sha256'] == old_receipt['outputs'][relative],'Baseline result changed')
        prep = ROOT/'data/benchmark/scifact/preparation-20261105-attempt03'
        for tree in (ROOT/'experiments/scifact_comparison',ROOT/'experiments/scifact',ROOT/'src/asof'):
            for path in sorted(tree.rglob('*.py')):
                retain(path)
        frame = dict(schema_version=1,kind='sc03_production_frame',condition_order=list(CONDITIONS),
            prepared=retain(PREPARED),preparation_root=str(prep),model=context['model'],cutoff=context['cutoff'],
            references=retain(prep/'restricted/references_dev.jsonl'),
            evaluator=retain(ROOT/'data/reference/scifact-evaluator-66feffc5/evaluator/eval.py'),
            split=retain(prep/'restricted/split.json'),baseline_dispositions=retain(old/'dispositions.json'),
            baseline_evaluation=retain(old/'evaluation.json'),conditions=conditions,
            run_output=str(OUTPUT/'execution'),analysis_output=str(ROOT/'data/benchmark/scifact_comparison/analysis-20261106-attempt01'),
            protocol=retain(ROOT/'planning/TETHER SciFact Full Context Protocol 2026-11-06.md'),
            python=retain(sys.executable),bootstrap=dict(seed=20261106,replicates=10000),provider_spend_usd=0,
            scope='All 300 exposed public dev claims; fixed retrieved five; four separately labelled evidence interventions.')
        frame['pins'] = list(pins.values())
        write(OUTPUT/'EXPERIMENT.json',frame)
        write(OUTPUT/'RECEIPT.json',dict(status='FROZEN',experiment=pin(OUTPUT/'EXPERIMENT.json'),benchmark_calls=0))
        print(json.dumps(dict(status='FROZEN',frame=pin(OUTPUT/'EXPERIMENT.json'),conditions=5,claims_per_condition=300)))
    except BaseException as error:
        write(OUTPUT/'FAILED.json',dict(status='FAIL',error_type=type(error).__name__,error=str(error)))
        raise


if __name__ == '__main__':
    main()
