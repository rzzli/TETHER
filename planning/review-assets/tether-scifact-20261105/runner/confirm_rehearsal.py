"""Byte/inventory confirmation of the retained fictional controller rehearsal."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
EVIDENCE=Path(__file__).resolve().parent
RUN=ROOT/"data/cache/scifact-runner-fictional-attempt02/stage"


def read(path):return json.loads(Path(path).read_bytes())
def proof(path):
    raw=Path(path).read_bytes()
    return {"path":str(Path(path).resolve()),"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}


report=read(RUN/"REPORT.json");receipt=read(RUN/"RECEIPT.json");frozen=read(RUN/"FROZEN.json")
assert report["status"]=="completed" and report["scheduled"]==1
actual={p.relative_to(RUN).as_posix() for p in RUN.rglob("*") if p.is_file() and p.name!="RECEIPT.json"}
assert actual==set(receipt["outputs"])
for name,digest in receipt["outputs"].items():assert proof(RUN/name)["sha256"]==digest
for path,item in frozen["runtime"]["task_code"].items():assert proof(path)==item
assert [job["name"] for job in report["jobs"]]==["fit",*[f"tune-{i:02d}" for i in range(1,10)],"dev"]
assert [job["name"] for job in report["auxiliary_jobs"]]==[*[f"score-tune-{i:02d}" for i in range(1,10)],"check","score-dev"]
transports={p.stem:read(p) for p in (RUN/"transport").glob("*.json")}
assert len(transports)==22 and all(row["returncode"]==0 for row in transports.values())
peaks=[read(Path(job["path"])/"COMPLETE.json").get("peak_sampled_working_set_bytes")
       for job in [*report["jobs"],*report["auxiliary_jobs"]]]
qualified={
    "schema_version":1,"status":"PASS_fictional_runner_only","verified_at_utc":datetime.now(timezone.utc).isoformat(),
    "scope":"Generated fictional dataset and transport fixture; actual trained worker, native purpose/source policy, official scorer, subprocess supervision and runtime verification. No production SciFact fitting or results.",
    "unit_tests":{"runner":{"methods":11,"failures":0,"errors":0,"log":proof(EVIDENCE/"runner-tests-attempt06.log")},
                  "scorer_worker":{"methods":4,"failures":0,"errors":0,"log":proof(EVIDENCE/"scorer-worker-tests-attempt01.log")}},
    "retained_failures":{"regression_red":proof(EVIDENCE/"runner-tests-attempt01.log"),
                         "runtime_alias_rehearsal":proof(ROOT/"data/cache/scifact-runner-fictional-attempt01/stage/FAILED.json")},
    "rehearsal":{"output":str(RUN),"receipt":proof(RUN/"RECEIPT.json"),"report":proof(RUN/"REPORT.json"),
                 "freeze":proof(RUN/"FROZEN.json"),"dev_freeze":proof(RUN/"DEV-FROZEN.json"),
                 "check_verification":proof(RUN/"check-verification.json"),"outputs_verified":len(actual),
                 "producer_attempts":11,"auxiliary_attempts":11,"elapsed_seconds":report["elapsed_seconds"],
                 "controller_runtime_reverification_wall_seconds":sum(row["wall_seconds"] for row in report["controller_costs"] if row["operation"]=="runtime_reverification"),
                 "parent_supervised_execution_seconds":sum(row["supervision"]["execution_elapsed_seconds"] for row in transports.values()),
                 "maximum_sampled_child_working_set_bytes":max((value for value in peaks if value is not None),default=None),
                 "unobserved_child_memory_samples":sum(value is None for value in peaks),
                 "retained_stage_bytes":sum(p.stat().st_size for p in RUN.rglob("*") if p.is_file()),"provider_spend_usd":0},
    "source_code":frozen["runtime"]["task_code"],
    "limitations":["Fictional flow qualification supplies no benchmark performance estimate.",
                   "Managed input auditing and polling limits are not a hostile-code/OS sandbox.",
                   "Source/environment checks bracket processes; they do not continuously attest the host.",
                   "Fast children may finish before a memory sampling tick; process-lifetime peaks remain in their cell resources.",
                   "Scientific annotation validity is outside the provenance check."]}
destination=EVIDENCE/"RUNNER-QUALIFICATION-20261105.json"
with destination.open("x",encoding="utf-8",newline="\n") as stream:json.dump(qualified,stream,indent=2);stream.write("\n")
print(json.dumps({"status":qualified["status"],"receipt_sha256":qualified["rehearsal"]["receipt"]["sha256"],
                  "elapsed_seconds":report["elapsed_seconds"],"outputs_verified":len(actual),"qualification":proof(destination)}))
