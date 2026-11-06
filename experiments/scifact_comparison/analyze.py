"""Post-production source-inclusive paired checking, native scoring and diagnostics."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/'src')]
from asof.serde import encode
from experiments.scifact_comparison.audit import verify_outputs, read
from experiments.scifact_comparison.prepare import pin, write
from experiments.scifact_comparison.inputs import CONDITIONS, need
from experiments.scifact_comparison.policy import build_external_context, check_primary
from experiments.scifact_comparison.statistics import case_counts, metrics, total, paired_bootstrap
from experiments.scifact_comparison.diagnostics import compare_condition
from experiments.scifact.evaluate import evaluate_schedule


def rows(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frame',required=True,type=Path)
    parser.add_argument('--frame-sha256',required=True)
    parser.add_argument('--results',required=True,type=Path)
    parser.add_argument('--results-sha256',required=True)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    started = time.perf_counter()
    try:
        need(pin(args.frame)['sha256'] == args.frame_sha256,'Experiment frame external anchor differs')
        need(pin(args.results)['sha256'] == args.results_sha256,'Results external anchor differs')
        frame,result_anchors = read(args.frame),read(args.results)
        for proof in frame['pins']:
            need(pin(proof['path']) == proof,'Frozen scientific input/code changed: '+proof['path'])
        prepared = read(frame['prepared']['path'])
        runs,requests = {},{}
        need(set(result_anchors['conditions']) == set(CONDITIONS) and result_anchors['condition_order'] == list(CONDITIONS),
             'All five ordered condition anchors required')
        for condition in CONDITIONS:
            binding = result_anchors['conditions'][condition]
            launch = read(frame['conditions'][condition]['path'])
            outcome_path = Path(launch['launch_output'])/'OUTCOME.json'
            need(pin(outcome_path) == binding['supervisor_outcome'],'Supervisor outcome changed')
            outcome = read(outcome_path)
            need(outcome['status'] == 'completed' and outcome['all_frozen_pins_unchanged'],'Condition did not complete with preserved sources')
            requests[condition] = rows(prepared['conditions'][condition]['requests']['path'])
            runs[condition] = verify_outputs(launch['qualification_output'],binding['worker_receipt']['sha256'],
                requests[condition],expected_condition=condition)
        context = build_external_context(frame['preparation_root'],frame['model']['path'],frame['model']['sha256'],
            args.output/'proofs',cutoff=frame['cutoff'],workspace_root=ROOT)
        retrieval = {r['id']:r['retrieved'] for r in rows(prepared['retrieval']['path'])}
        primary = runs['primary']
        dispositions,checks = [],[]
        for request,claim in zip(requests['primary'],primary['claims']):
            cid = request['id']
            if claim['status'] != 'produced':
                dispositions.append(dict(id=cid,producer_status='input_unavailable',check_status='not_run',prediction=None,
                                         reason='One or more scheduled primary pairs had unavailable/overlength inputs.'))
                continue
            try:
                checked = check_primary(context,request,claim,primary['pairs'][cid],retrieval[cid])
                checks.append(encode(checked))
                status,reason = 'accepted',None
            except ValueError as error:
                status,reason = 'rejected',str(error)
                checks.append(dict(id=cid,status='rejected',reason=reason))
            dispositions.append(dict(id=cid,producer_status='produced',check_status=status,prediction=claim['prediction'],reason=reason))
        references = rows(frame['references']['path'])
        schedule = prepared['schedule']
        evaluation = encode(evaluate_schedule(schedule,context.corpus,references,dispositions,evaluator_path=frame['evaluator']['path']))
        write(args.output/'CHECKS.json',checks)
        write(args.output/'DISPOSITIONS.json',dispositions)
        write(args.output/'EVALUATION.json',evaluation)
        vectors = {}
        for gold,record in zip(references,dispositions):
            pred = record['prediction'] if record['check_status'] == 'accepted' else dict(id=gold['id'],evidence={})
            vectors[gold['id']] = case_counts(gold,pred,produced=record['producer_status']=='produced',admitted=record['check_status']=='accepted')
        reconstruction = metrics(total(list(vectors.values())))
        need(all(abs(reconstruction[k]-v)<1e-12 for k,v in evaluation['checked_metrics'].items()),'Native sufficient statistics disagree')
        need(abs(reconstruction['strict_correct_per_scheduled']-evaluation['rates']['correct_and_admitted_per_scheduled'])<1e-12,
             'Strict reconstructed yield differs')
        baseline = read(frame['baseline_dispositions']['path'])
        if isinstance(baseline,dict):
            baseline = baseline['records']
        need([r['id'] for r in baseline] == schedule,'Baseline disposition schedule differs')
        baseline_vectors = {}
        for gold,record in zip(references,baseline):
            pred = record['prediction'] if record['check_status']=='accepted' else dict(id=gold['id'],evidence={})
            baseline_vectors[gold['id']] = case_counts(gold,pred,produced=record['producer_status']=='produced',admitted=record['check_status']=='accepted')
        old_metrics = metrics(total(list(baseline_vectors.values())))
        original_evaluation = read(frame['baseline_evaluation']['path'])
        need(all(abs(old_metrics[k]-v)<1e-12 for k,v in original_evaluation['checked_metrics'].items()),'Baseline native reconstruction differs')
        split = read(frame['split']['path'])
        components = {cid:split['group_by_claim'][str(cid)] for cid in schedule}
        need(len(set(components.values())) == 247,'Expected source-component count differs')
        bootstrap = paired_bootstrap(baseline_vectors,vectors,components,seed=20261106,replicates=10000)
        write(args.output/'PAIRED-BOOTSTRAP.json',bootstrap)
        summaries = {}
        for condition in CONDITIONS[1:]:
            report = compare_condition(primary['pairs'],runs[condition]['pairs'],rows(prepared['conditions'][condition]['lineage']['path']))
            write(args.output/(condition+'-diagnostics.json'),report)
            summaries[condition] = {k:v for k,v in report.items() if k != 'rows'}
        write(args.output/'COUNTS.json',dict(fields=list(__import__('experiments.scifact_comparison.statistics',fromlist=['FIELDS']).FIELDS),
            baseline=baseline_vectors,new=vectors,components=components))
        write(args.output/'REPORT.json',dict(status='analyzed',schedule_count=len(schedule),
            primary_counts=evaluation['counts'],primary_metrics=evaluation['checked_metrics'],
            baseline_metrics=original_evaluation['checked_metrics'],diagnostics=summaries,
            worker_resources={k:v['report'] for k,v in runs.items()},analysis_wall_seconds=time.perf_counter()-started,
            provider_cost_usd=0,scientific_scope='Exposed public SciFact development comparison; no clinical validity or isolated architecture effect.',
            independent_reconstruction='pending'))
        files = {p.relative_to(args.output).as_posix():pin(p) for p in args.output.rglob('*') if p.is_file()}
        write(args.output/'RECEIPT.json',dict(status='complete',frame_sha256=args.frame_sha256,result_anchors_sha256=args.results_sha256,files=files))
        print(json.dumps(dict(status='analyzed',counts=evaluation['counts'],receipt=pin(args.output/'RECEIPT.json'))))
    except BaseException as error:
        write(args.output/'FAILED.json',dict(status='FAIL',error_type=type(error).__name__,error=str(error)))
        raise


if __name__ == '__main__':
    main()
