"""Freeze SC04 inputs and execution policy; no model or HTTP dispatch."""
import argparse
from datetime import datetime,timezone
from importlib import metadata
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]
from asof.serde import canonical,encode
from experiments.litqa_comparison import run,qualification_fixtures,preparation

MODEL=Path(r'E:\projects_data\drug_target_agents_data\models\qwen25-14b-q4km-20261018T032528Z')
PREPARATION=ROOT/'data/benchmark/litqa_comparison/preparation-20261106-attempt02/MANIFEST.json'
PREPARATION_SHA='29a18fb45f4f8fe76b52eb833ddf351b4fa9a47c82a2fa9d9a971ff38f814dc4'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--purpose',choices=('fictional_qualification','production'),required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    parent=None
    if args.purpose=='fictional_qualification':
        answers=qualification_fixtures.queries();source=[dict(id=q['id'],question=q['question']) for q in answers]
        products={}
        for name,rows in (('source_queries',source),('answer_queries',answers)):
            run.write(args.output/(name+'.json'),rows);products[name]=run.pipeline.proof(args.output/(name+'.json'))
        seconds=dict(expand=600,collect=300,rank=600,answer=900);replay_seconds=180
    else:
        parent=run.pipeline.proof(PREPARATION)
        run.codecs.need(parent['sha256']==PREPARATION_SHA,'Original199 preparation anchor')
        manifest=run.pipeline.read(parent)
        source=preparation.load_product(manifest,'source_queries');answers=preparation.load_product(manifest,'answer_queries')
        products={name:run.pipeline.proof(manifest['products'][name]['path']) for name in ('source_queries','answer_queries')}
        seconds=dict(expand=3600,collect=7200,rank=7200,answer=10800);replay_seconds=1800
    receipt=run.pipeline.proof(MODEL/'acquisition.json')
    run.codecs.need(receipt['sha256']==run.RECEIPT_SHA,'Qualified model receipt differs')
    # make_server_spec reconstructs exact required native asset proofs from the
    # retained acquisition receipt. owned_server rehashes assets before launch.
    spec,bindings,provenance=run.model.make_server_spec(receipt['path'],receipt['sha256'],port=55628,
                                                    alias='tether-sc04-primary-qwen14b-v1',startup_seconds=180)
    environment=dict(python_version=sys.version,packages=sorted((d.metadata.get('Name','unknown'),d.version) for d in metadata.distributions()),
                     execution_dependencies='Standard library plus pinned native llama.cpp; installed packages are inventory, not an activation claim.')
    run.write(args.output/'ENVIRONMENT.json',environment)
    frame=dict(kind='sc04_primary_execution_v1',purpose=args.purpose,created_at_utc=datetime.now(timezone.utc).isoformat(),
        count=len(answers),schedule=[q['id'] for q in answers],phases=list(run.PHASES),
        conditions=['L/O','E/O','L/R','E/R','supplied_source_pending_separate_execution'],
        provider_spend_usd=0,automatic_retry=False,code_pins=run.code_pins(),python=run.pipeline.proof(sys.executable),
        python_version=sys.version,generation_configuration=encode(run.codecs.CONFIG),phase_seconds=seconds,replay_seconds=replay_seconds,
        port=55628,alias='tether-sc04-primary-qwen14b-v1',model_receipt=receipt,model_license=run.pipeline.proof(MODEL/'LICENSE-QWEN'),
        model_spec=encode(spec),model_provenance=provenance,query_products=products,parent_preparation=parent,
        policy=encode(run.acquisition.legacy.DEFAULT_POLICY),environment=run.pipeline.proof(args.output/'ENVIRONMENT.json'),
        protocol=run.pipeline.proof(ROOT/'planning/TETHER LitQA2 Retrieval Comparison Protocol 2026-11-06.md'),
        scope='Full primary factorial execution. No scientific scoring and no supplied-source diagnostic in this controller.')
    run.write(args.output/'FRAME.json',frame)
    proof=run.pipeline.proof(args.output/'FRAME.json')
    run.load_frame(proof['path'],proof['sha256']);run.validate_products(frame)
    run.write(args.output/'ANCHOR.json',proof)
    print(canonical(proof).decode())


if __name__=='__main__':main()
