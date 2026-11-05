"""Retained full-controller rehearsal; entirely generated fictional source data."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"experiments/scifact/tests"))
from test_scifact_run import fictional_preparation
from experiments.scifact.run import run_stage,write

parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
arguments=parser.parse_args();root=arguments.output.resolve();root.mkdir(parents=True,exist_ok=False)
preparation,anchor=fictional_preparation(root)
write(root/"FIXTURE.json",{"scope":"fictional generated claims and sources only; no benchmark performance inference",
                          "preparation_manifest_sha256":anchor})
result=run_stage(preparation,anchor,root/"stage",sys.executable,
                 ROOT/"data/reference/scifact-evaluator-66feffc5/evaluator/eval.py",
                 ROOT/"planning/review-assets/tether-scifact-20261105/ENVIRONMENT-QUALIFICATION-02.json")
write(root/"REHEARSAL-COMPLETED.json",{"status":"PASS","scope":"fictional full pipeline with actual worker, policy, scorer, supervision and environment",
                                     "scheduled":result["scheduled"],"provider_spend_usd":result["provider_spend_usd"]})
print("Fictional controller rehearsal complete; actual benchmark fitting remains unexecuted.")
