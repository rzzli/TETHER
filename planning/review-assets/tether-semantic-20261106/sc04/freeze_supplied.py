"""Freeze a separate supplied-paper diagnostic, with explicit privileged inputs."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]
from asof.serde import encode
from experiments.litqa_comparison import run as primary_controller,pipeline as proofs
from experiments.litqa_supplied import run,qualification_fixtures as fixture

PRIMARY_FRAME=ROOT/'planning/review-assets/tether-semantic-20261106/sc04/production-freeze01/FRAME.json'
PRIMARY_SHA='bf2898bed1a1c2f0a6040dd116ec37223f514764217441e4b8cf84345e4801d0'
INPUTS=ROOT/'data/benchmark/litqa_comparison/supplied-source-inputs-20261106-attempt03/MANIFEST.json'
INPUT_SHA='6635f6b0501b0b40abeda01b7ca723f5b3309838f6e6e4ba4810689f1378290d'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--purpose',choices=('fictional_qualification','production'),required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--primary-root',type=Path);parser.add_argument('--primary-root-sha256')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    primary=primary_controller.load_frame(PRIMARY_FRAME,PRIMARY_SHA)
    model={k:primary[k] for k in ('model_receipt','model_license','model_spec','model_provenance','port','alias')}
    model['port']=55630
    spec,_,provenance=run.model.make_server_spec(model['model_receipt']['path'],model['model_receipt']['sha256'],
        port=model['port'],alias=model['alias'],startup_seconds=180)
    model['model_spec']=encode(spec);model['model_provenance']=encode(provenance)
    source_projection=None;parent=None
    if args.purpose=='fictional_qualification':
        queries=fixture.queries();hints=[dict(id=q['id'],question=q['question'],dois=[fixture.DOI]) for q in queries]
        products={}
        for name,rows in (('answer_queries',queries),('hints',hints),('doi_schedule',[fixture.DOI])):
            run.write(args.output/(name+'.json'),rows);products[name]=proofs.proof(args.output/(name+'.json'))
        counts=(2,1,2);seconds=dict(collect=300,answer=600);replay_seconds=180
    else:
        run.codecs.need(args.primary_root is not None and args.primary_root_sha256,'Completed primary root and externally retained receipt hash required')
        receipt=proofs.proof(args.primary_root/'ROOT-RECEIPT.json')
        run.codecs.need(receipt['sha256']==args.primary_root_sha256,'Primary root external anchor')
        parent=dict(root=str(args.primary_root.resolve()),receipt=receipt)
        source_projection=proofs.proof(INPUTS);run.codecs.need(source_projection['sha256']==INPUT_SHA,'Diagnostic projection anchor')
        source=proofs.read(source_projection)
        run.codecs.need(source['role']=='diagnostic_selection_only' and not source['ordinary_retrieval_permitted'] and
                        not source['correct_answers_included'] and not source['key_passages_included'],'Privileged diagnostic input role')
        products=dict(answer_queries=primary['query_products']['answer_queries'],**source['products'])
        counts=(199,190,205);seconds=dict(collect=7200,answer=3600);replay_seconds=1800
    frame=dict(kind='sc04_supplied_execution_v1',purpose=args.purpose,created_at_utc=datetime.now(timezone.utc).isoformat(),
        questions=counts[0],unique_dois=counts[1],question_doi_pairs=counts[2],products=products,model=model,code_pins=run.code_pins(),
        python=proofs.proof(sys.executable),generation_configuration=primary['generation_configuration'],policy=primary['policy'],
        primary_execution=parent,source_projection=source_projection,primary_frame=proofs.proof(PRIMARY_FRAME),
        phase_seconds=seconds,replay_seconds=replay_seconds,ordinary_retrieval=False,provider_cost_usd=0,automatic_retry=False,
        qualification_scope='Frozen answer producer has known false abstentions; this experiment measures them without prompt retuning.',
        protocol=proofs.proof(ROOT/'planning/TETHER LitQA2 Retrieval Comparison Protocol 2026-11-06.md'),
        analysis=proofs.proof(ROOT/'planning/review-assets/tether-semantic-20261106/sc04/ANALYSIS-SPECIFICATION.md'),
        freeze_helper=proofs.proof(Path(__file__)))
    run.write(args.output/'FRAME.json',frame);proof=proofs.proof(args.output/'FRAME.json')
    run.load_frame(proof['path'],proof['sha256']);run.tasks(frame,'answer');run.primary_gate(frame)
    run.write(args.output/'ANCHOR.json',proof);print(run.canonical(proof).decode())


if __name__=='__main__':main()
