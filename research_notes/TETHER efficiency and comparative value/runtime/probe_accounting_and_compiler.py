"""No-network fake adapter and original-only fictional compiler measurements."""
from __future__ import annotations
import collections
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "packages/tether/src")]
from asof.chrono import load_snapshot
from asof.contracts import Availability, Case, Profile, Snapshot, SourceNode, TemporalClass
from asof.serde import canonical, decode, encode, fingerprint, read_json
from asof.local_model import LocalSelectionBackend, verify_backend_execution
from asof.workflow import Budget, run_workflow
from asof.study import source_fact_sources as compiler


def write(path, value):
    path.write_bytes(canonical(value) + b"\n")


def accounting(root):
    root.mkdir()
    config = dict(schema_version=1, endpoint="http://127.0.0.1:55580", model_id="fake-transport-only",
        model_provenance=dict(weights_sha256={"fictional":"a"*64}, runtime_sha256="b"*64),
        retrieval=dict(max_records=12, max_request_bytes=12000), max_output_tokens=256, timeout_seconds=2, seed=1)
    write(root / "config.json", config)
    backend = LocalSelectionBackend(root / "config.json")
    class FakeOpener:
        def open(self, request, timeout):
            payload = json.loads(request.data)
            ids = payload["json_schema"]["properties"]["observation_ids"]["items"]["enum"][:1]
            return io.BytesIO(canonical(dict(content=json.dumps(dict(observation_ids=ids)),
                truncated=False, tokens_evaluated=1000000, tokens_predicted=1)))
    backend.opener = FakeOpener()
    base = ROOT / "src/asof/demo/v2"
    case = decode(Case, read_json(base / "case.json"))
    store = load_snapshot(base / "snapshot.json", case)
    run = run_workflow(case, store, backend, budget=Budget(max_input_tokens=100000, max_output_tokens=10000))
    document = dict(schema_version=1, attempts=encode(backend.records))
    verify_backend_execution(document, encode(run.trace), encode(run.configuration))
    write(root / "backend-execution.json", document)
    write(root / "trace.json", run.trace)
    result = dict(status=run.status, calls=run.calls, budget=encode(run.budget), accounted=encode(run.usage),
        measured=encode(run.measured_usage), estimated=encode(run.estimated_usage),
        reported_input_tokens=sum(r["response"]["tokens_evaluated"] for r in backend.records),
        usage_contract_violation_events=sum(e["event"]=="backend_usage_contract_violated" for e in run.trace),
        backend_archive_verification="accepted", fake_transport=True, network_calls=0)
    write(root / "result.json", result)
    return result


def compiler_case(root, count):
    root.mkdir()
    rows = [dict(id=str(i), targetId="T", diseaseId="D", beta=0.5, standardError=0.1,
        pValueMantissa=1.0, pValueExponent=-4) for i in range(count)]
    payload = canonical(dict(unselected_padding="p"*(1024*1024), rows=rows))
    (root / "original.json").write_bytes(payload)
    stamp = datetime(2026,10,31, tzinfo=timezone.utc)
    day = date(2020,1,1)
    availability = Availability(day,day,day,day,day,"fictional",None)
    node = SourceNode("s", "fictional", "v1", "original.json", hashlib.sha256(payload).hexdigest(),
        "agent_evidence", availability, TemporalClass.CONTEMPORARY, "https://example.invalid/fictional")
    snapshot = Snapshot(2,"fictional",Profile.DEMO,stamp.date(),False,(),(node,),str(root),origin_at=stamp)
    task = dict(schema_version=1,task_id="fictional",scope=dict(target_id="T",indication_id="D",
        target_namespace_version="fictional",indication_namespace_version="fictional",action=None,modality=None,tissue=None),
        cutoff=stamp.isoformat(),profile="synthetic_demo",primary_families=["reported_measurement"],
        records=[dict(record_key="r"+str(i),source_id="s",locator=dict(format="json",pointer="/rows/"+str(i)),
                      identity=dict(id=str(i),targetId="T",diseaseId="D")) for i in range(count)],
        fields=[dict(record_key="r"+str(i),field=name,family="reported_measurement",group="g"+str(i),
                     unit_field=None,empty_policy="unknown") for i in range(count)
                for name in ("beta","standardError","pValueMantissa","pValueExponent")],
        joins=[],collection=dict(status="selected_records",reason="fictional scaling fixture"))
    real_read, real_fingerprint = compiler.read_file, compiler.fingerprint
    counts = collections.Counter()
    def read(path,deadline,maximum):
        result=real_read(path,deadline,maximum)
        counts["json_reads"]+=1; counts["json_logical_bytes"]+=len(result)
        return result
    def hashed(value):
        if isinstance(value,dict) or hasattr(value,"keys"):
            if "task_id" in value and "fields" in value:
                counts["task_hashes"]+=1; counts["task_logical_bytes"]+=len(canonical(value))
        return real_fingerprint(value)
    with patch.object(compiler,"read_file",read),patch.object(compiler,"fingerprint",hashed):
        start=time.perf_counter()
        result=compiler.compile_reference(task,snapshot,root,{"fictional":{"roles":["agent_evidence"]}},deadline=time.monotonic()+60)
        elapsed=time.perf_counter()-start
    write(root / "reference.json",result.document)
    answer=dict(records=count,fields=len(task["fields"]),source_bytes=len(payload),elapsed_instrumented_seconds=elapsed,
                counts=dict(counts),reference_sha256=result.fingerprint)
    write(root / "result.json",answer)
    return answer


if __name__ == "__main__":
    parent=Path(sys.argv[1]).absolute();parent.mkdir(parents=True,exist_ok=False)
    result=dict(accounting=accounting(parent/"accounting"),
        compiler=[compiler_case(parent/("compiler-"+str(n)),n) for n in (1,8,32)])
    write(parent/"results.json",result)
    print(json.dumps(result,indent=2))
