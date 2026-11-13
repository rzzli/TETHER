"""One fresh, sequential native SciFact stage with no implicit worker retries.

The supervisor alone sees preparation/evaluation references. Workers receive
purpose-specific recipes containing only approved input paths and byte proofs.
"""
from __future__ import annotations

import argparse
import base64
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import os
import math
from pathlib import Path
import platform
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError, canonical, fingerprint, freeze, parse_json, safe_child
from tether_engine.study.proofs import capture_file
from tether._process import ProcessLimits, supervise_command, validate_success_report
from experiments.scifact.data_views import verify_preparation, load_product
from experiments.scifact.native_contract import validate_prediction
from experiments.scifact.tether_adapter import authorize_products, build_context, verify_session

GRID = tuple({"k": k, "rationale_threshold": threshold} for k in (5, 10, 20) for threshold in (.25, .5, .75))
SELECTION_CRITERION = "abstract_rationalized_f1_then_sentence_label_f1_then_smaller_k_then_higher_threshold"
DEFAULT_LIMITS = {"stage_seconds": 14400, "fit_seconds": 1800, "prediction_seconds": 3600,
                  "query_seconds": 60, "memory_bytes": 8 * 1024**3, "storage_bytes": 10 * 1024**3,
                  "process_output_bytes": 16 * 1024**2}


def need(condition, message):
    if not condition:
        raise ContractError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def file_proof(path):
    path = Path(path).absolute()
    proof = capture_file(path, "native-stage-artifact")
    return {"path": str(path), "sha256": proof["sha256"], "bytes": proof["bytes"]}


def read(path, maximum=64 * 1024**2):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "Missing or symlinked stage artifact")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    need(len(raw) <= maximum, "Stage artifact exceeds read bound")
    return parse_json(raw)


def write(path, value):
    publish_bytes(Path(path), canonical(value) + b"\n")


def capture_runtime(environment_qualification):
    """Check qualified RECORD payloads and capture actual native/core code identities.

    Scope is installed distribution payloads, project task code and executables;
    this is not attestation of every OS/stdlib component or transient host changes.
    """
    qualification = read(environment_qualification)
    need(qualification.get("status") == "PASS", "Missing qualified CPU environment")
    need(Path(qualification["python"]["executable"]).resolve() == Path(sys.executable).resolve(), "Controller must use the qualified interpreter")
    need(platform.python_version() == qualification["python"]["version"], "Python version differs")
    executables = {}
    for field in ("executable", "base_executable"):
        # uv's authorized base-interpreter alias can be a junction. Record the
        # alias and its explicit target; ordinary data/artifact proofs stay strict.
        qualified_path=Path(qualification["python"][field])
        proof = file_proof(qualified_path.resolve(strict=True))
        need(proof["sha256"] == qualification["python"][field + "_sha256"], "Python executable changed")
        executables[field] = {**proof,"qualified_path":str(qualified_path.absolute())}
    packages = {}
    for name, expected in sorted(qualification["installed"].items()):
        dist = metadata.distribution(name)
        need(dist.version == expected["version"], "Dependency version changed: " + name)
        meta_sha = hashlib.sha256(dist.read_text("METADATA").encode()).hexdigest()
        need(meta_sha == expected["metadata_sha256"], "Dependency metadata changed: " + name)
        files = {}
        for entry in dist.files or ():
            if entry.hash is None:
                continue
            need(entry.hash.mode == "sha256", "Unsupported dependency RECORD digest")
            proof = file_proof(dist.locate_file(entry))
            encoded = base64.urlsafe_b64encode(bytes.fromhex(proof["sha256"])).rstrip(b"=").decode()
            need(encoded == entry.hash.value and proof["bytes"] == entry.size, "Dependency payload differs from RECORD")
            files[str(entry)] = {"sha256": proof["sha256"], "bytes": proof["bytes"]}
        need(len(files) == expected["record_payloads_verified"], "Dependency payload inventory changed")
        packages[name] = {"version": dist.version, "metadata_sha256": meta_sha, "files": files}
    code = {str(path.resolve()): file_proof(path) for path in sorted(Path(__file__).parent.glob("*.py"))}
    return freeze({"schema_version": 1, "qualification": file_proof(environment_qualification),
                   "executables": executables, "packages": packages, "task_code": code,
                   "scope": "qualified_RECORD_payloads_project_task_code_and_Python_executables_not_full_host_attestation"})


def select_configuration(rows):
    need(len(rows) == len(GRID), "Exactly the declared nine tuning configurations are required")
    need({fingerprint(row["configuration"]) for row in rows} == {fingerprint(row) for row in GRID}, "Tuning configuration inventory differs")
    for row in rows:
        need(row["status"] == "completed", "A failed tuning configuration cannot be silently excluded")
        for metric in ("abstract_rationalized_f1", "sentence_label_f1"):
            value = row["metrics"][metric]
            need(type(value) in (int, float) and 0 <= value <= 1, "Invalid tuning metric")
    return min(rows, key=lambda row: (-row["metrics"]["abstract_rationalized_f1"], -row["metrics"]["sentence_label_f1"],
                                      row["configuration"]["k"], -row["configuration"]["rationale_threshold"]))


def session_cells(job, expected_schedule, *, require_complete=True):
    """Read every observed worker outcome; absence remains unexecuted, never NEI."""
    job = Path(job)
    expected = [str(key) for key in expected_schedule]
    records = {}
    journal_path = job / "session/journal.jsonl"
    if journal_path.exists():
        events = read_chain(journal_path, allow_incomplete_tail=not require_complete)
        for event in events:
            if event["event"] not in ("native_terminal", "native_unexecuted"):
                continue
            details = event["details"]
            path = safe_child(job / "session", details["path"])
            proof = file_proof(path)
            need(proof["sha256"] == details["record_sha256"], "Worker terminal record changed")
            value = read(path, 4 * 1024**2)
            need(fingerprint(value) == details["record_fingerprint"] and value["cell_id"] == details["cell_id"], "Worker journal/cell disagreement")
            need(value["cell_id"] not in records, "Duplicate worker outcome")
            records[value["cell_id"]] = value
    if require_complete:
        complete = read(job / "COMPLETE.json")
        need(complete["status"] == "completed", "Worker did not complete")
        verify_session(job / "session", expected_receipt_sha256=complete["session_receipt_sha256"])
        need(set(records) == set(expected) and all(row["status"] == "completed" for row in records.values()), "Worker schedule incomplete or failed")
    return records


def reconcile_worker(job, recipe, records):
    """Join internally valid journal events to the exact supervisor authorization."""
    need(fingerprint(read(Path(job)/"recipe.json")) == fingerprint(recipe), "Worker recipe differs from submitted recipe")
    events = read_chain(Path(job)/"session/journal.jsonl")
    configured = events[1]["details"]
    requests = {event["details"]["cell_id"]:event["details"]["request"] for event in events if event["event"] == "native_dispatch"}
    need(fingerprint(configured["configuration"]) == fingerprint(recipe["configuration"]), "Worker configuration differs from submitted recipe")
    setup = "fit" if recipe["mode"] == "fit" else "setup"
    need(fingerprint(requests[setup]) == fingerprint({"mode":recipe["mode"],"inputs":recipe["inputs"]}), "Worker setup inputs differ from submitted recipe")
    if recipe["mode"] == "predict":
        proof = recipe["inputs"]["queries"]
        need(file_proof(proof["path"]) == proof, "Worker query product changed")
        queries = [parse_json(line) for line in Path(proof["path"]).read_bytes().splitlines()]
        need([row["id"] for row in queries] == recipe["schedule"], "Worker query schedule differs")
        for query in queries:
            need(fingerprint(requests[str(query["id"])]) == fingerprint({"query":query,"configuration":recipe["configuration"]}),
                 "Worker request differs from authorized query/configuration")


def failure_dispositions(schedule, worker_records, reason):
    rows = []
    for claim_id in schedule:
        record = worker_records.get(str(claim_id))
        if record is None:
            rows.append({"id": claim_id, "producer_status": "unexecuted", "check_status": "not_run", "prediction": None, "reason": reason})
        elif record["status"] == "completed" and isinstance(record.get("result"), Mapping) and "prediction" in record["result"]:
            rows.append({"id": claim_id, "producer_status": "produced", "check_status": "not_run", "prediction": record["result"]["prediction"], "reason": "retained_unchecked_after_stage_failure"})
        else:
            status = "timeout" if record["status"] == "timeout" else "error"
            rows.append({"id": claim_id, "producer_status": status, "check_status": "not_run", "prediction": None, "reason": reason})
    return rows


class Stage:
    def __init__(self, preparation_root, preparation_manifest_sha256, output, python_executable,
                 evaluator_path, environment_qualification, *, limits=None, launcher=supervise_command):
        need(Path(python_executable).resolve() == Path(sys.executable).resolve(), "Controller and worker must use the same interpreter")
        self.preparation_root = Path(preparation_root).resolve()
        self.preparation_manifest_sha256 = preparation_manifest_sha256
        self.output = Path(output).resolve(); self.python = Path(python_executable).resolve()
        self.evaluator = Path(evaluator_path).resolve(); self.environment = Path(environment_qualification).resolve()
        self.limits = dict(DEFAULT_LIMITS if limits is None else limits)
        need(set(self.limits) == set(DEFAULT_LIMITS) and all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in self.limits.values()), "Invalid stage limits")
        need(all(type(self.limits[key]) is int for key in ("memory_bytes", "storage_bytes", "process_output_bytes")), "Stage byte limits must be integers")
        self.launcher = launcher; self.started = time.perf_counter(); self.phase = "initialize"
        self.journal = RunJournal(self.output, kind="build")
        self.manifest = None; self.schedule = []; self.jobs = []; self.dev_records = {}
        self.runtime = None; self.cutoff = now(); self.model_root = None; self.context = None
        self.controller_costs = []; self.auxiliary_jobs = []

    def boundary(self, *, source_check=True):
        remaining = self.limits["stage_seconds"] - (time.perf_counter() - self.started)
        need(remaining > 0, "Global native-stage time budget exhausted")
        size = sum(path.stat().st_size for path in self.output.rglob("*") if path.is_file())
        need(size <= self.limits["storage_bytes"], "Native-stage storage budget exhausted")
        if source_check and self.runtime is not None:
            started, cpu = time.perf_counter(), time.process_time()
            current = capture_runtime(self.environment)
            need(fingerprint(current) == fingerprint(self.runtime), "Code or qualified environment changed during stage")
            self.controller_costs.append({"operation": "runtime_reverification", "phase": self.phase,
                                          "wall_seconds": time.perf_counter()-started, "cpu_seconds": time.process_time()-cpu})
            if hasattr(self,"protocol_proof"):
                need(file_proof(self.protocol_proof["path"])==self.protocol_proof,"Frozen execution protocol changed")
        remaining = self.limits["stage_seconds"] - (time.perf_counter() - self.started)
        need(remaining > 0, "Global native-stage time budget exhausted after source verification")
        return remaining

    def product_input(self, product_id, purpose):
        authorize_products(self.manifest, [product_id], purpose)
        item = self.manifest["products"][product_id]
        path = safe_child(self.preparation_root, item["path"])
        proof = file_proof(path)
        need(proof["sha256"] == item["sha256"] and proof["bytes"] == item["bytes"], "Authorized worker input changed")
        return proof

    def initialize(self):
        started, cpu = time.perf_counter(), time.process_time()
        self.manifest = verify_preparation(self.preparation_root, self.preparation_manifest_sha256)
        need(not self.manifest["feasibility_issues"], "Preparation class feasibility gate is not satisfied")
        self.schedule = [row["id"] for row in load_product(self.preparation_root, self.manifest, "queries_dev", "predict")]
        self.runtime = capture_runtime(self.environment)
        self.evaluator_proof = file_proof(self.evaluator)
        self.protocol_proof=file_proof(Path(__file__).with_name("PROTOCOL-v1.txt"))
        self.freeze = {"schema_version": 1, "created_at_utc": now(), "preparation_root": str(self.preparation_root),
                       "preparation_manifest_sha256": self.preparation_manifest_sha256, "dev_schedule": self.schedule,
                       "grid": GRID, "selection_criterion":SELECTION_CRITERION,"protocol":self.protocol_proof,"limits": self.limits, "cutoff": self.cutoff,
                       "runtime": self.runtime, "evaluator": self.evaluator_proof,
                       "reference_access": "scoring_opens_after_corresponding_immutable_candidates_trusted_preparation_audit_may_inspect_labels", "provider_spend_usd": 0}
        write(self.output / "FROZEN.json", self.freeze)
        self.journal.append("build_stage", stage="initialized", freeze_sha256=file_proof(self.output / "FROZEN.json")["sha256"])
        self.controller_costs.append({"operation": "preparation_and_runtime_qualification", "phase": self.phase,
                                      "wall_seconds": time.perf_counter()-started, "cpu_seconds": time.process_time()-cpu})

    def dispatch(self, name, recipe):
        remaining = self.boundary()
        need(not (self.output / "jobs" / name).exists(), "Worker attempt already exists; never automatically repeat")
        timeout = min(float(recipe["limits"]["phase_seconds"]), remaining)
        limits = ProcessLimits(timeout_seconds=timeout, max_output_bytes=int(self.limits["process_output_bytes"]))
        recipe_path = self.output / "recipes" / (name + ".json")
        write(recipe_path, recipe)
        job = self.output / "jobs" / name
        command = [str(self.python), "-I", "-B", str(Path(__file__).with_name("worker.py").resolve()), "--recipe", str(recipe_path), "--output", str(job)]
        self.journal.append("build_worker_dispatch", name=name, recipe_sha256=file_proof(recipe_path)["sha256"], command=command,
                            environment={key: os.environ.get(key) for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")}, limits=limits.payload())
        self.jobs.append({"name": name, "path": str(job), "recipe": str(recipe_path), "schedule": recipe["schedule"], "mode": recipe["mode"]})
        result = None
        try:
            result = self.launcher(command, limits=limits)
        except BaseException as error:
            result = getattr(error, "tether_engine_result", None)
            raise
        finally:
            if result is not None:
                publish_bytes(self.output / "transport" / (name + ".stdout"), result.stdout)
                publish_bytes(self.output / "transport" / (name + ".stderr"), result.stderr)
                write(self.output / "transport" / (name + ".json"), {"returncode": result.returncode, "supervision": result.supervision,
                                                                       "recipe_sha256": file_proof(recipe_path)["sha256"]})
                self.journal.append("build_worker_returned", name=name, returncode=result.returncode, supervision=result.supervision)
        need(result is not None and result.returncode == 0, "Native worker failed: " + name)
        validate_success_report(result.supervision, limits, len(result.stdout), len(result.stderr))
        expected = ["fit"] if recipe["mode"] == "fit" else ["setup", *map(str, recipe["schedule"])]
        records = session_cells(job, expected)
        reconcile_worker(job, recipe, records)
        audit = job / "io-audit.jsonl"
        need(audit.is_file(), "Managed worker input-access audit is missing")
        audit_rows = [parse_json(line) for line in audit.read_bytes().splitlines()]
        need(audit_rows and all(row.get("allowed") is True for row in audit_rows), "Worker attempted an undeclared input/output")
        expected_inputs = {str(Path(item["path"]).resolve()).casefold() for item in recipe["inputs"].values()}
        observed = {str(Path(row["path"]).resolve()).casefold() for row in audit_rows if row.get("path")}
        need(expected_inputs <= observed, "Required worker inputs were not observed in access audit")
        self.boundary()
        return job, records

    def recipe(self, mode, inputs, configuration, schedule):
        return {"schema_version": 1, "mode": mode, "inputs": inputs, "configuration": configuration, "schedule": list(schedule),
                "limits": {"phase_seconds": self.limits["fit_seconds" if mode == "fit" else "prediction_seconds"],
                           "memory_bytes": self.limits["memory_bytes"], "query_seconds": self.limits["query_seconds"]}}

    def auxiliary(self, name, script, recipe, job):
        """One supervised scoring/checking attempt, never a producer retry."""
        remaining=self.boundary();job=Path(job)
        need(not job.exists(), "Auxiliary attempt already exists")
        limits=ProcessLimits(timeout_seconds=min(remaining,recipe["limits"]["phase_seconds"]),
                             max_output_bytes=self.limits["process_output_bytes"])
        recipe_path=self.output/"auxiliary-recipes"/(name+".json");write(recipe_path,recipe)
        command=[str(self.python),"-I","-B",str(Path(__file__).with_name(script).resolve()),"--recipe",str(recipe_path),"--output",str(job)]
        self.journal.append("build_auxiliary_dispatch",name=name,recipe_sha256=file_proof(recipe_path)["sha256"],command=command,limits=limits.payload())
        self.auxiliary_jobs.append({"name":name,"path":str(job),"recipe":str(recipe_path),"script":script})
        result=None
        try:result=self.launcher(command,limits=limits)
        except BaseException as error:
            result=getattr(error,"tether_engine_result",None);raise
        finally:
            if result is not None:
                publish_bytes(self.output/"transport"/(name+".stdout"),result.stdout)
                publish_bytes(self.output/"transport"/(name+".stderr"),result.stderr)
                write(self.output/"transport"/(name+".json"),{"returncode":result.returncode,"supervision":result.supervision,"recipe_sha256":file_proof(recipe_path)["sha256"]})
                self.journal.append("build_auxiliary_returned",name=name,returncode=result.returncode,supervision=result.supervision)
        need(result is not None and result.returncode==0,"Native auxiliary process failed: "+name)
        validate_success_report(result.supervision,limits,len(result.stdout),len(result.stderr))
        need(fingerprint(read(job/"recipe.json"))==fingerprint(recipe),"Auxiliary recipe changed")
        need(read(job/"COMPLETE.json")["status"]=="completed","Auxiliary process incomplete")
        self.boundary()
        return job

    def score(self, name, partition, candidates, schedule):
        purpose="tune" if partition=="tune" else "evaluate"
        candidate_path=self.output/"evaluation-inputs"/(name+".json");write(candidate_path,candidates)
        recipe={"schema_version":1,"mode":purpose,"schedule":list(schedule),"evaluator":self.evaluator_proof,
                "inputs":{"corpus":self.product_input("corpus",purpose),
                          "references":self.product_input("references_"+partition,purpose),"candidates":file_proof(candidate_path)},
                "limits":{"phase_seconds":min(600,self.boundary(source_check=False)),"memory_bytes":self.limits["memory_bytes"]}}
        need(file_proof(self.evaluator)==self.evaluator_proof,"Pinned evaluator changed")
        job=self.auxiliary("score-"+name,"score_worker.py",recipe,self.output/"evaluation-jobs"/name)
        records=session_cells(job,["score"])
        events=read_chain(job/"session/journal.jsonl")
        need(fingerprint(events[1]["details"]["configuration"])==fingerprint({"mode":purpose}),"Scorer configured purpose differs")
        request=next(event["details"]["request"] for event in events if event["event"]=="native_dispatch")
        need(fingerprint(request)==fingerprint({key:recipe[key] for key in ("mode","inputs","schedule","evaluator")}),"Scorer dispatch differs from authorized inputs")
        result=read(job/"RESULT.json")
        need(fingerprint(result)==fingerprint(records["score"]["result"]),"Scorer result differs from retained session")
        need(file_proof(job/"RESULT.json")["sha256"]==read(job/"COMPLETE.json")["result_sha256"],"Scorer result hash differs")
        audit=[parse_json(line) for line in (job/"io-audit.jsonl").read_bytes().splitlines()]
        need(audit and all(row.get("allowed") is True for row in audit),"Scorer attempted undeclared input")
        observed={str(Path(row["path"]).resolve()).casefold() for row in audit if row.get("path")}
        need({str(Path(proof["path"]).resolve()).casefold() for proof in [*recipe["inputs"].values(),recipe["evaluator"]]}<=observed,
             "Required scorer inputs were not observed in access audit")
        return result

    def fit(self):
        from experiments.scifact.baseline import LEARNER_SETTINGS, VECTORIZER_SETTINGS, SEED
        self.phase = "fit"; self.journal.append("build_stage", stage=self.phase)
        configuration = {"method_id": "scifact_sparse_linear_v1", "seed": SEED,
                         "learner_settings": LEARNER_SETTINGS, "vectorizer_settings": VECTORIZER_SETTINGS}
        inputs = {key: self.product_input(key, "fit") for key in ("corpus", "queries_fit", "fit_pairs")}
        self.fit_job, self.fit_records = self.dispatch("fit", self.recipe("fit", inputs, configuration, []))
        self.model_root = self.fit_job / "model"

    def predict_recipe(self, partition, configuration):
        purpose = "tune" if partition == "tune" else "predict"
        query_input = self.product_input("queries_" + partition, purpose)
        queries = load_product(self.preparation_root, self.manifest, "queries_" + partition, purpose)
        inputs = {"model_json": file_proof(self.model_root / "model.json"), "model_arrays": file_proof(self.model_root / "arrays.npz"), "queries": query_input}
        return self.recipe("predict", inputs, configuration, [row["id"] for row in queries])

    def tune(self):
        self.phase = "tune"; self.journal.append("build_stage", stage=self.phase)
        corpus = {row["doc_id"]: row for row in load_product(self.preparation_root, self.manifest, "corpus", "tune")}
        rows = []
        for number, configuration in enumerate(GRID, 1):
            recipe = self.predict_recipe("tune", configuration)
            job, records = self.dispatch(f"tune-{number:02d}", recipe)
            predictions = [validate_prediction(records[str(key)]["result"]["prediction"], corpus, expected_claim_id=key) for key in recipe["schedule"]]
            # Only the scoring process receives these reference bytes, after production.
            metrics = self.score(f"tune-{number:02d}","tune",predictions,recipe["schedule"])
            row = {"configuration": configuration, "status": "completed", "metrics": metrics,
                   "worker": str(job), "candidate_session_receipt_sha256": read(job / "COMPLETE.json")["session_receipt_sha256"]}
            write(self.output / "tuning" / f"config-{number:02d}.json", row); rows.append(row)
        selected = select_configuration(rows)
        self.selected = selected["configuration"]
        write(self.output / "tuning/selection.json", {"criterion": SELECTION_CRITERION,
                                                       "selected": selected, "configurations": rows})

    def freeze_model(self):
        self.phase = "freeze_model"; self.journal.append("build_stage", stage=self.phase)
        fit_inputs = ("corpus", "queries_fit", "fit_pairs")
        versions = {"python": platform.python_version(), **{name: item["version"] for name, item in self.runtime["packages"].items()}}
        fit_complete = read(self.fit_job / "COMPLETE.json")
        model = {"schema_version": 1, "kind": "scifact_model", "computed_at": now(), "fit_product_ids": fit_inputs,
                 "index_input_product_ids": ["corpus"], "fit_claim_ids": [row["id"] for row in load_product(self.preparation_root, self.manifest, "queries_fit", "fit")],
                 "configuration": self.selected, "files": self.fit_records["fit"]["result"]["files"],
                 "producer_code": file_proof(Path(__file__).with_name("baseline.py")), "dependency_versions": versions,
                 "input_product_proofs": {key: {field: self.manifest["products"][key][field] for field in ("sha256", "bytes")} for key in fit_inputs},
                 "preparation_manifest_sha256": self.preparation_manifest_sha256,
                 "fit_execution": {"path": str(self.fit_job / "session"), "receipt_sha256": fit_complete["session_receipt_sha256"], "cell_id": "fit"},
                 "training_metadata": self.fit_records["fit"]["result"].get("metadata", {})}
        write(self.model_root / "model-manifest.json", model)
        self.model_sha = file_proof(self.model_root / "model-manifest.json")["sha256"]
        self.boundary()
        started, cpu = time.perf_counter(), time.process_time()
        self.context = build_context(self.preparation_root, self.preparation_manifest_sha256, self.model_root, self.model_sha,
                                     self.cutoff, self.output / "proofs", workspace_root=Path.cwd())
        self.controller_costs.append({"operation": "native_source_and_model_context", "phase": self.phase,
                                      "wall_seconds": time.perf_counter()-started, "cpu_seconds": time.process_time()-cpu})
        write(self.output / "DEV-FROZEN.json", {"created_at_utc": now(), "model_manifest_sha256": self.model_sha,
              "configuration": self.selected, "dev_schedule": self.schedule, "policy_sha256": self.context.policy_sha256,
              "evaluator": self.evaluator_proof, "runtime_fingerprint": fingerprint(self.runtime), "reference_answers_opened_for_prediction": False})
        self.journal.append("build_dev_frozen", sha256=file_proof(self.output / "DEV-FROZEN.json")["sha256"])

    def predict_dev(self):
        self.phase = "predict_dev"; self.journal.append("build_stage", stage=self.phase)
        need((self.output / "DEV-FROZEN.json").is_file(), "Dev prediction requires frozen model/configuration")
        recipe = self.predict_recipe("dev", self.selected)
        need(recipe["schedule"] == self.schedule, "Development schedule changed")
        job, self.dev_records = self.dispatch("dev", recipe)
        self.dev_job = job

    def check(self):
        self.phase = "check"; self.journal.append("build_stage", stage=self.phase)
        candidate_path=self.output/"check-inputs/candidates.json"
        write(candidate_path,[self.dev_records[str(key)] for key in self.schedule])
        recipe={"schema_version":1,"preparation_root":str(self.preparation_root),"preparation_manifest_sha256":self.preparation_manifest_sha256,
                "model_root":str(self.model_root),"model_manifest_sha256":self.model_sha,"cutoff":self.cutoff,
                "workspace_root":str(Path.cwd()),"container_admission":self.context.container_admission,"policy_sha256":self.context.policy_sha256,
                "configuration":self.selected,"schedule":self.schedule,"candidates":file_proof(candidate_path),
                "producer_session":{"path":str(self.dev_job/"session"),"receipt_sha256":read(self.dev_job/"COMPLETE.json")["session_receipt_sha256"]},
                "limits":{"phase_seconds":self.boundary(),"query_seconds":self.limits["query_seconds"],"memory_bytes":self.limits["memory_bytes"]}}
        job=self.auxiliary("check","check_worker.py",recipe,self.output/"checks")
        complete=read(job/"COMPLETE.json")
        need(complete["candidate_input_sha256"]==recipe["candidates"]["sha256"] and complete["policy_sha256"]==self.context.policy_sha256,
             "Checker completion input/policy binding differs")
        self.check_verification=verify_session(job/"session",expected_receipt_sha256=complete["session_receipt_sha256"],context=self.context)
        self.dispositions=read(job/"dispositions.json")
        check_events=read_chain(job/"session/journal.jsonl")
        checked={event["details"]["cell_id"]:read(safe_child(job/"session",event["details"]["path"])) for event in check_events if event["event"]=="native_terminal"}
        need([row["id"] for row in self.dispositions]==self.schedule,"Checker disposition schedule differs")
        for row in self.dispositions:
            produced=self.dev_records[str(row["id"])];accepted=checked[str(row["id"])];body=accepted["result"]
            need(row["producer_status"]=="produced" and row["check_status"]==accepted["status"],"Checker disposition differs from retained session")
            need(fingerprint(row["prediction"])==fingerprint(produced["result"]["prediction"])==fingerprint(body["prediction"]),"Checker relabeled producer candidate")
            need(fingerprint(body["envelope"]["resources"])==fingerprint(produced["resources"]),"Checker altered producer resources")
            for field in ("retrieved","source_bindings"):
                need(fingerprint(body["envelope"][field])==fingerprint(produced["result"][field]),"Checker altered producer source bindings")
            need(row.get("reason")== (None if row["check_status"]=="accepted" else body["message"]),"Checker disposition reason differs")
        write(self.output / "check-verification.json", self.check_verification)
        write(self.output / "dispositions.json", self.dispositions)

    def evaluate(self):
        self.phase = "evaluate"; self.journal.append("build_stage", stage=self.phase)
        result = self.score("dev","dev",self.dispositions,self.schedule)
        write(self.output / "evaluation.json", result)
        self.boundary()
        self.journal.append("build_completed", scheduled=len(self.schedule), evaluation_sha256=file_proof(self.output / "evaluation.json")["sha256"],
                            elapsed_seconds=time.perf_counter()-self.started)
        report = {"schema_version": 1, "status": "completed", "scheduled": len(self.schedule), "model_manifest_sha256": self.model_sha,
                  "policy_sha256": self.context.policy_sha256, "counts": result["counts"], "raw_metrics": result["raw_metrics"],
                  "checked_metrics": result["checked_metrics"], "rates": result["rates"], "jobs": self.jobs,"auxiliary_jobs":self.auxiliary_jobs,
                  "elapsed_seconds": time.perf_counter()-self.started, "provider_spend_usd": 0, "controller_costs": self.controller_costs,
                  "scientific_scope": "public_SciFact_development_annotations_not_biological_truth_or_private_test"}
        write(self.output / "REPORT.json", report)
        receipt = {"schema_version": 1, "kind": "scifact_native_stage", "runtime_fingerprint": fingerprint(self.runtime),
                   "outputs": {path.relative_to(self.output).as_posix(): file_proof(path)["sha256"]
                               for path in sorted(self.output.rglob("*")) if path.is_file()}}
        write(self.output / "RECEIPT.json", receipt)
        return freeze(report)

    def execute(self):
        try:
            self.initialize(); self.fit(); self.tune(); self.freeze_model(); self.predict_dev(); self.check()
            return self.evaluate()
        except BaseException as error:
            self.journal.fail(error, self.phase)
            try:
                observed = session_cells(self.output / "jobs/dev", ["setup", *self.schedule], require_complete=False)
            except BaseException as inspection_error:
                observed = {}
                write(self.output / "FAILED-INSPECTION.json", {"error_type": type(inspection_error).__name__, "message": str(inspection_error)})
            write(self.output / "FAILED-DISPOSITIONS.json", failure_dispositions(self.schedule, observed, type(error).__name__))
            write(self.output / "FAILED.json", {"schema_version": 1, "phase": self.phase, "error_type": type(error).__name__,
                                               "message": str(error), "scheduled_dev": len(self.schedule), "jobs": self.jobs,
                                               "recovery": "inspect only; a separately justified new stage never reuses this output"})
            raise
        finally:
            self.journal.close()


def run_stage(preparation_root, preparation_manifest_sha256, output, python_executable, evaluator_path,
              environment_qualification, *, limits=None, launcher=supervise_command):
    return Stage(preparation_root, preparation_manifest_sha256, output, python_executable, evaluator_path,
                 environment_qualification, limits=limits, launcher=launcher).execute()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--preparation-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--environment-qualification", type=Path, required=True)
    args = parser.parse_args()
    print(canonical(run_stage(args.preparation, args.preparation_sha256, args.output, args.python,
                             args.evaluator, args.environment_qualification)).decode())


if __name__ == "__main__":
    main()
