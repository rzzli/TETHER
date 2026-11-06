"""Explicit parent-only task projection; no model or source HTTP requests."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from experiments.litqa_comparison.preparation import prepare,load_product
from experiments.litqa_comparison.codecs import digest


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    m=prepare(ROOT/'data/benchmark/labbench/preparation-20261106-attempt02',a.output)
    q=load_product(m,'source_queries');answers=load_product(m,'answer_queries')
    assert len(q)==len(answers)==199
    assert all(x['id']==y['id'] and x['question']==y['question'] for x,y in zip(q,answers))
    print(json.dumps(dict(status='reconstructed',scheduled=199,
        manifest_sha256=digest((a.output/'MANIFEST.json').read_bytes()),
        reference_fields_in_predictor_products=False,model_dispatches=0,http_requests=0)))


if __name__=='__main__':main()
