"""Bounded reference-only scorer process; no fitting inputs or model access."""
from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from asof.atomic import publish_bytes
from asof.serde import ContractError, canonical, parse_json
from experiments.scifact.evaluate import official_metrics, evaluate_schedule
from experiments.scifact.native_contract import validate_prediction, validate_references, validate_schedule
from experiments.scifact.runtime import IOAudit, Watchdog, load_input, measured
from experiments.scifact.tether_adapter import NativeSession


def write(path, value):
    publish_bytes(path, canonical(value)+b"\n")


def execute(recipe_path, output):
    recipe=parse_json(Path(recipe_path).read_bytes())
    required={"schema_version","mode","inputs","schedule","evaluator","limits"}
    if set(recipe)!=required or recipe["schema_version"]!=1 or recipe["mode"] not in {"tune","evaluate"}:
        raise ContractError("Invalid scorer recipe")
    if set(recipe["inputs"])!={"corpus","references","candidates"}:
        raise ContractError("Scorer inputs must be corpus, references and candidates only")
    limits=recipe["limits"]
    if (set(limits)!={"phase_seconds","memory_bytes"} or
        not all(type(value) in (int,float) and math.isfinite(value) and value>0 for value in limits.values()) or
        type(limits["memory_bytes"]) is not int):
        raise ContractError("Invalid scorer limits")
    schedule=validate_schedule(recipe["schedule"])
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    write(output/"recipe.json",recipe)
    proofs={**recipe["inputs"],"evaluator":recipe["evaluator"]}
    roots=[sys.prefix,sys.base_prefix,Path(__file__).resolve().parent]
    if os.name=="nt":roots.append(Path(os.environ.get("SystemRoot","C:/Windows"))/"System32")
    audit=IOAudit([proof["path"] for proof in proofs.values()],output,roots);audit.activate()
    with Watchdog(output,memory_limit=limits["memory_bytes"],call_seconds=limits["phase_seconds"]) as watchdog:
        with NativeSession(output/"session",["score"],{"mode":recipe["mode"]},max_wall_seconds=limits["phase_seconds"]) as session:
            start,cpu=time.perf_counter(),time.process_time()
            try:
                session.begin("score",{key:recipe[key] for key in ("mode","inputs","schedule","evaluator")})
                watchdog.active_started=start
                raw={key:load_input(proof) for key,proof in proofs.items()}
                corpus_rows=[parse_json(line) for line in raw["corpus"].splitlines()]
                corpus={row["doc_id"]:row for row in corpus_rows}
                if len(corpus)!=len(corpus_rows):raise ContractError("Duplicate scorer corpus identity")
                references=validate_references([parse_json(line) for line in raw["references"].splitlines()],corpus,schedule)
                candidates=parse_json(raw["candidates"])
                if recipe["mode"]=="tune":
                    if len(candidates)!=len(schedule):raise ContractError("Scorer candidate count differs")
                    predictions=[validate_prediction(value,corpus,expected_claim_id=key) for value,key in zip(candidates,schedule)]
                    result=official_metrics(references,predictions,evaluator_path=recipe["evaluator"]["path"])
                else:
                    result=evaluate_schedule(schedule,corpus,references,candidates,evaluator_path=recipe["evaluator"]["path"])
                payload=canonical(result)+b"\n";publish_bytes(output/"RESULT.json",payload)
                session.finish("score",result,measured(start,cpu,input_bytes=sum(map(len,raw.values())),output_bytes=len(payload),examples=len(schedule)))
                receipt=session.finalize();watchdog.active_started=None;audit.flush()
                write(output/"COMPLETE.json",{"status":"completed","session_receipt_sha256":receipt["sha256"],
                      "result_sha256":hashlib.sha256(payload).hexdigest(),"memory_sampling_seconds":watchdog.sample_seconds,
                      "peak_sampled_working_set_bytes":watchdog.peak_sample,"memory_observations":watchdog.memory_observations,
                      "io_audit_scope":"managed_python_opens_trusted_reference_only_scorer_not_os_sandbox"})
            except BaseException as error:
                watchdog.active_started=None
                if session.active is not None:
                    try:session.fail("score",error,measured(start,cpu,input_bytes=None,output_bytes=None,examples=None))
                    except BaseException:pass
                write(output/"FAILED.json",{"error_type":type(error).__name__,"message":str(error),"recovery":"inspect only; no repeat"})
                audit.flush();raise


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--recipe",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    arguments=parser.parse_args();execute(arguments.recipe,arguments.output)
