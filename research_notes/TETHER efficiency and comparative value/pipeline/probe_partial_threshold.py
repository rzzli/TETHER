"""Fictional omission versus false-assertion threshold discrimination."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"data/cache/comparative-audit-20261102/pipeline-attempt-03"
sys.path.insert(0,str(ROOT))
from tests.test_study_source_fact_evaluation import SourceFactEvaluationTests
from asof.serde import canonical, encode
from asof.study.source_fact_sources import compile_reference
from asof.study.source_fact_evaluation import score_cell

class RetainedTemporaryDirectory(tempfile.TemporaryDirectory):
    def cleanup(self):
        self._finalizer.detach()

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    tempfile.tempdir=str(OUT)
    fixture=SourceFactEvaluationTests()
    with patch.object(tempfile,"TemporaryDirectory",RetainedTemporaryDirectory):
        fixture.setUp()
    task=copy.deepcopy(fixture.task)
    task["primary_families"]=["reported_measurement"]
    task["records"]=task["records"][:1]
    task["fields"]=[field for field in task["fields"] if field["record_key"]=="r0"]
    reference=compile_reference(task,fixture.snapshot,fixture.root,{"control":{"roles":["agent_evidence"]}},deadline=time.monotonic()+20)
    fixture.reference=reference
    omitted=[fact["fact_id"] for fact in reference.document["facts"] if fact["field"]=="standardError"]
    outputs={"complete":fixture.output(),"omitted_one":fixture.output(omit=omitted,status="partial",reason="Fictional omission"),"wrong_value":fixture.output()}
    index=next(i for i,f in enumerate(reference.document["facts"]) if f["field"]=="standardError")
    outputs["wrong_value"]["facts"][index]["value"]=2.0
    results={}
    for key,output in outputs.items():
        raw=canonical(output)
        (OUT/(key+".json")).write_bytes(raw)
        scored=encode(score_cell(reference,raw,cell_id="fictional-"+key))
        results[key]={field:scored[field] for field in ("terminal","critical_errors","completion","primary","answer_status")}
    assert results["omitted_one"]["primary"]["passes"]=={"60":True,"80":False,"100":False}
    assert results["omitted_one"]["critical_errors"]==[]
    assert results["wrong_value"]["primary"]["passes"]=={"60":False,"80":False,"100":False}
    (OUT/"result.json").write_text(json.dumps(dict(status="PASS",scope="Invented JSON source, one group, four measurement fields",results=results),indent=2)+"\n",encoding="utf-8")
    print(json.dumps(results,indent=2))

if __name__=="__main__":
    main()
