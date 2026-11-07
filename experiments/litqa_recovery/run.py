"""One-shot supervised recovery; original collection and model assets stay frozen.

Frames and transition certificates are externally anchored inputs. This module
does not issue its own scientific or qualification approval. Replay only reads
retained records: it neither acquires execution claims nor launches a process.
"""
import argparse
from datetime import datetime, timezone
from functools import partial
import os
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):
    # The explicitly selected interpreter supplies the frozen installed runtime.
    sys.path.insert(0, str(ROOT))

import tether
from tether._process import ProcessLimits, supervise_command, validate_success_report
from tether_engine.serde import encode
from experiments.labbench import model
from experiments.labbench.runtime import (contain_process_tree, empty_import_cache,
    DeadlineWatchdog, InputAudit, ProcessSamples, process_sample)
from experiments.litqa_analysis import source_archive
from experiments.litqa_analysis.native_records import canonical, decode, digest, need, safe_path
from experiments.litqa_comparison import codecs, pipeline as primary, schedule
from experiments.litqa_recovery import admission, collection as c, pipeline, plan

PHASES = ("collect", "answer")
MAX_STREAM_BYTES = 4 * 1024 ** 2
FRAME_KEYS = {"schema_version", "kind", "purpose", "created_at_utc", "output", "common_root",
    "planning_frame", "planning_authority", "transition_certificate", "collection_frame", "model",
    "generation_configuration", "code_pins", "environment", "phase_seconds", "replay_seconds",
    "call_seconds", "maximum_answer_calls", "ordinary_retrieval", "automatic_retry", "provider_cost_usd"}


def source_pins():
    """Freeze the complete maintained producer/verifier closure, excluding tests."""
    folders = ("src/tether_engine", "packages/tether/src/tether", "experiments/labbench",
               "experiments/litqa_comparison", "experiments/litqa_supplied",
               "experiments/litqa_analysis", "experiments/litqa_recovery")
    pins = {p.relative_to(ROOT).as_posix(): c.capture(p)[0]["sha256"]
            for folder in folders for p in (ROOT / folder).rglob("*.py")
            if not p.name.startswith("test_")}
    for name in tuple(pins):
        for parent in (ROOT / name).parents:
            if parent == ROOT:
                break
            initializer = parent / "__init__.py"
            if initializer.is_file():
                pins[initializer.relative_to(ROOT).as_posix()] = c.capture(initializer)[0]["sha256"]
    c.source_pins()  # Also compares installed engine files with repository bytes.
    installed = Path(tether.__file__).parent
    for name, sha in pins.items():
        if name.startswith("packages/tether/src/tether/"):
            need(c.capture(installed / name.removeprefix("packages/tether/src/tether/"))[0]["sha256"] == sha,
                 "Loaded facade differs from controller source closure")
    return dict(sorted(pins.items()))


def environment():
    return dict(**c.environment(), facade_initializer=c.capture(tether.__file__)[0])


def _json(proof):
    return decode(c.bound(proof))


def _model(value):
    need(set(value) == {"model_receipt", "model_license", "port", "alias", "model_spec", "model_provenance"},
         "Exact original model metadata required")
    c.bound(value["model_receipt"])
    c.bound(value["model_license"])
    spec, bindings, provenance = model.make_server_spec(value["model_receipt"]["path"],
        value["model_receipt"]["sha256"], port=value["port"], alias=value["alias"], startup_seconds=180)
    need(encode(spec) == value["model_spec"] and encode(provenance) == value["model_provenance"],
         "Original model receipt/specification/provenance differs")
    return spec, bindings, provenance


def _qualified(proof, pins):
    value = _json(proof)
    need(value.get("schema_version") == 2 and value.get("kind") == "sc04_recovery_controller_qualification_v2"
         and value.get("status") == "PASS" and type(value.get("tests")) is int and value["tests"] > 0
         and all(type(value.get(k)) is int and value[k] == 0 for k in ("failures", "errors", "skipped"))
         and value.get("code_pins") == pins, "Current controller qualification required")


def _transition(proof, original, original_proof, pins, purpose):
    certificate = _json(proof)
    need(set(certificate) == {"schema_version", "kind", "status", "purpose", "original_supplied_frame",
        "primary", "primary_acceptance", "source_archive", "original_repository_root", "current_code_pins",
        "parity_proof", "qualification"} and certificate["schema_version"] == 2 and
        certificate["kind"] == "sc04_recovery_transition_certificate_v2" and certificate["status"] == "PASS"
        and certificate["purpose"] == purpose and certificate["original_supplied_frame"] == original_proof
        and certificate["current_code_pins"] == pins, "Explicit qualified namespace/recovery transition required")
    _qualified(certificate["qualification"], pins)
    c.bound(certificate["parity_proof"])
    archive = certificate["source_archive"]
    need(set(archive) == {"path", "sha256"}, "Explicit historical source archive descriptor required")
    source_archive.load_archive(archive["path"], archive["sha256"], original["code_pins"],
                                certificate["original_repository_root"])
    parent = certificate["primary"]
    need(set(parent) == {"root", "root_receipt_sha256"}, "Finalized primary external anchor required")
    root = plan._absolute(parent["root"])
    receipt, raw = c.capture(root / "ROOT-RECEIPT.json")
    need(receipt["sha256"] == plan._sha(parent["root_receipt_sha256"]), "Primary execution receipt changed")
    value = decode(raw)
    need(value["status"] == "primary_execution_complete" and "COMPLETE.json" in value["files"],
         "Primary execution must have finalized")
    need(set(value["files"]) == {p.name for p in root.iterdir() if p.is_file() and p.name != "ROOT-RECEIPT.json"},
         "Primary root file inventory differs")
    for name, item in value["files"].items():
        need(plan._relative(name) == name and "/" not in name and item["path"] == str(root / name),
             "Primary proof location differs")
        c.bound(item)
    complete = _json(value["files"]["COMPLETE.json"])
    need(complete["status"] == "primary_execution_complete" and
         complete["purpose"] in (("production",) if purpose == "production" else ("production", "fictional_qualification")),
         "Primary completion/purpose differs")
    acceptance = _json(certificate["primary_acceptance"])
    need(acceptance.get("status") == "passed" and
         acceptance.get("primary_execution_anchor") == parent["root_receipt_sha256"] and
         acceptance.get("scientific_correctness_scored") is False,
         "Independent primary acceptance differs")
    c.bound(acceptance["primary_replay"])
    if purpose == "production":
        need(acceptance.get("questions") == 199 and acceptance.get("answers") == 796,
             "Full primary cohort acceptance required")
        need(original["primary_execution"]["root"] == str(root) and
             original["primary_execution"]["receipt"]["sha256"] == parent["root_receipt_sha256"],
             "Primary parent substituted from original supplied frame")
    return certificate


def make_frame(planning_frame, planning_authority, transition_certificate, collection_qualification,
               output, common_root, *, collect_seconds=7200, answer_seconds=3600, replay_seconds=1800):
    """Return a frame for external approval/sealing; performs no dispatch or writes."""
    _, parent, _ = c._planning(planning_frame, planning_authority)
    original = _json(parent["original_frame"])
    output = plan._absolute(output)
    return dict(schema_version=2, kind="sc04_supervised_recovery_execution_v2", purpose=original["purpose"],
        created_at_utc=c.utc(), output=str(output), common_root=str(plan._absolute(common_root)),
        planning_frame=planning_frame, planning_authority=planning_authority,
        transition_certificate=transition_certificate,
        collection_frame=c.make_frame(planning_frame, planning_authority, collection_qualification,
            output / "collect/worker/phase", collect_seconds - 60), model=original["model"],
        generation_configuration=original["generation_configuration"], code_pins=source_pins(), environment=environment(),
        phase_seconds=dict(collect=collect_seconds, answer=answer_seconds), replay_seconds=replay_seconds,
        call_seconds=120, maximum_answer_calls=len(parent["answer_queries"]), ordinary_retrieval=False,
        automatic_retry=False, provider_cost_usd=0)


def _locations(frame, parent, authority, planning_frame):
    output, common = plan._absolute(frame["output"]), plan._absolute(frame["common_root"])
    original = plan._absolute(parent["original_root"])
    need(common == original.parent and output != common and output.is_relative_to(common),
         "Original and recovered outputs require explicit common study root")
    protected_roots = [original, authority.parent, plan._absolute(planning_frame["output"])]
    source = _json(parent["original_frame"])
    if source.get("primary_execution") is not None:
        protected_roots.append(plan._absolute(source["primary_execution"]["root"]))
    for protected in protected_roots:
        need(not output.is_relative_to(protected) and not protected.is_relative_to(output), "Recovery output overlaps protected root")
    safe_path(output.parent)
    return output


def verify_frame(path, sha, output=None):
    proof, raw = c.capture(path)
    need(proof["sha256"] == plan._sha(sha), "External controller frame anchor differs")
    frame = decode(raw)
    need(set(frame) == FRAME_KEYS and type(frame["schema_version"]) is int and frame["schema_version"] == 2
         and frame["kind"] == "sc04_supervised_recovery_execution_v2" and frame["purpose"] in
         ("production", "fictional_qualification") and frame["automatic_retry"] is False
         and frame["ordinary_retrieval"] is False and frame["provider_cost_usd"] == 0, "Recovery controller schema/policy")
    if output is not None:
        need(frame["output"] == str(plan._absolute(output)), "Frozen controller output differs")
    stamp = datetime.fromisoformat(frame["created_at_utc"])
    need(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0, "UTC controller freeze required")
    need(frame["code_pins"] == source_pins() and frame["environment"] == environment(), "Controller source/environment changed")
    pf, parent, authority = c._planning(frame["planning_frame"], frame["planning_authority"])
    _locations(frame, parent, authority, pf)
    original = _json(parent["original_frame"])
    need(frame["purpose"] == original["purpose"] and frame["model"] == original["model"] and
         frame["generation_configuration"] == original["generation_configuration"] == encode(codecs.CONFIG),
         "Original model/scientific configuration changed")
    _model(frame["model"])
    _transition(frame["transition_certificate"], original, parent["original_frame"], frame["code_pins"], frame["purpose"])
    seconds = frame["phase_seconds"]
    need(set(seconds) == set(PHASES) and type(seconds["collect"]) is int and 180 <= seconds["collect"] <= 21600
         and type(seconds["answer"]) is int and 240 <= seconds["answer"] <= 43200 and
         type(frame["replay_seconds"]) is int and 60 <= frame["replay_seconds"] <= 3600 and
         type(frame["call_seconds"]) is int and frame["call_seconds"] == 120 and
         type(frame["maximum_answer_calls"]) is int and frame["maximum_answer_calls"] == len(parent["answer_queries"]),
         "Recovery phase/call ceilings differ")
    if frame["purpose"] == "production":
        need((len(parent["doi_schedule"]), len(parent["answer_queries"]), sum(len(h["dois"]) for h in parent["hints"])) ==
             (190, 199, 205), "Full original production denominator required")
    cf = frame["collection_frame"]
    expected = c.make_frame(frame["planning_frame"], frame["planning_authority"], cf["qualification"],
                           Path(frame["output"]) / "collect/worker/phase", seconds["collect"] - 60)
    expected["created_at_utc"] = cf["created_at_utc"]
    need(cf == expected, "Embedded collection frame differs from authorized parent/limits")
    q = _json(cf["qualification"])
    need(q.get("kind") == "sc04_recovery_collection_qualification_v2" and q.get("schema_version") == 2
         and q.get("status") == "PASS" and type(q.get("tests")) is int and q["tests"] > 0
         and all(type(q.get(k)) is int and q[k] == 0 for k in ("failures", "errors", "skipped"))
         and q.get("code_pins") == cf["code_pins"], "Collection qualification differs")
    return proof, raw, frame, parent, authority


def _claim_value(frame_proof, frame, parent):
    return dict(schema_version=2, kind="sc04_answer_execution_claim_v2", frame=frame_proof,
        output=frame["output"], parent_identity=parent["parent_identity"],
        question_ids=[q["id"] for q in parent["answer_queries"]], maximum_calls=frame["maximum_answer_calls"],
        automatic_retry=False)


def reserve_answers(frame_proof, frame, parent, authority):
    """Permanent one-shot reservation; even an empty/failed claim is never reused."""
    root = authority / "answer-execution"
    safe_path(authority)
    root.mkdir(exist_ok=False)
    return c.publish(root / "CLAIM.json", _claim_value(frame_proof, frame, parent))


def _answer_claim(frame_proof, frame, parent, authority, proof):
    need(proof["path"] == str(authority / "answer-execution/CLAIM.json") and
         _json(proof) == _claim_value(frame_proof, frame, parent), "Exclusive answer execution claim differs")


def supervised(command, limits, output, label):
    """Retain bounded child streams and process cleanup even when dispatch fails."""
    result = None
    try:
        result = supervise_command(command, limits=limits)
    except BaseException as error:
        result = getattr(error, "tether_engine_result", getattr(error, "result", None))
        raise
    finally:
        if result is not None:
            c._write(output / (label + "-stdout.txt"), result.stdout)
            c._write(output / (label + "-stderr.txt"), result.stderr)
            c.publish(output / (label + "-SUPERVISION.json"), dict(returncode=result.returncode, supervision=result.supervision))
        else:
            c.publish(output / (label + "-DISPATCH-UNKNOWN.json"),
                      dict(status="no_supervisor_terminal", automatic_retry=False))
    need(result.returncode == 0, "Recovery worker failed; automatic replay of calls forbidden")
    validate_success_report(result.supervision, limits, len(result.stdout), len(result.stderr))
    return result


def _command(frame_proof, job_proof, output, cache, mode):
    return [sys.executable, "-I", "-B", "-X", "pycache_prefix=" + str(cache), str(Path(__file__).absolute()), mode,
            "--frame", frame_proof["path"], "--frame-sha256", frame_proof["sha256"], "--job", job_proof["path"],
            "--job-sha256", job_proof["sha256"], "--output", str(output)]


def _failure(root, journal, error, **details):
    try:
        journal.append("execution_failed", error_type=type(error).__name__, automatic_retry=False)
        c.publish(root / "FAILURE.json", encode(dict(error_type=type(error).__name__, automatic_retry=False, **details)))
    except BaseException as secondary:
        error.add_note("Failure retention: " + type(secondary).__name__)


def _completed_inventory(files):
    need(not any(Path(name).name in {"FAILURE.json", "DEADLINE.json", "FINALIZATION-FAILED.json"}
                 or Path(name).name.endswith("-DISPATCH-UNKNOWN.json") for name in files),
         "Completed recovery contains a failure, timeout or unknown dispatch")


def _review_terminal(root, frame_proof, job_proof, result, anchored=None):
    def proof_at(path):
        return c.capture(path)[0] if anchored is None else anchored[str(path)]
    report = proof_at(root / "REPORT.json")
    need(_json(report) == result, "Review report differs")
    events = c._chain(c.bound(proof_at(root / "journal.jsonl")))
    need([(e["event"], e["details"]) for e in events] == [
        ("review_reserved", dict(frame=frame_proof, job=job_proof)),
        ("review_completed", dict(report=report))], "Review terminal journal differs")
    need({p.name for p in root.iterdir()} == {"REPORT.json", "journal.jsonl", "io-audit.jsonl"},
         "Unexpected review artifacts")
    for line in c.bound(proof_at(root / "io-audit.jsonl")).splitlines():
        need(decode(line).get("allowed") is True, "Review recorded a denied access")


def _phase(frame_proof, frame, parent, authority, phase, prior, claim):
    root = Path(frame["output"]) / phase
    root.mkdir(exist_ok=False)
    journal = c.Journal(root)
    try:
        journal.append("phase_reserved", phase=phase, frame=frame_proof)
        cf = c.publish(root / "COLLECTION-FRAME.json", frame["collection_frame"]) if phase == "collect" else None
        cache = ROOT / "data/cache" / ("sc04-recovery-" + frame_proof["sha256"] + "-" + phase)
        job = dict(schema_version=2, phase=phase, frame=frame_proof, collection=prior,
            collection_frame=cf, answer_claim=claim, cutoff=c.utc() if phase == "answer" else None,
            import_cache=str(cache))
        job_proof = c.publish(root / "JOB.json", job)
        for mode, label in (("worker", "execution"), ("review-worker", "review")):
            output = root / ("worker" if mode == "worker" else "review")
            selected_cache = cache if mode == "worker" else Path(str(cache) + "-review")
            command = _command(frame_proof, job_proof, output, selected_cache, mode)
            seconds = frame["phase_seconds"][phase] if mode == "worker" else frame["replay_seconds"]
            limits = ProcessLimits(timeout_seconds=seconds, max_output_bytes=MAX_STREAM_BYTES)
            c.publish(root / (label + "-COMMAND.json"), dict(command=command, limits=limits.payload()))
            journal.append("child_dispatched", role=mode, command_sha256=digest(canonical(command)))
            supervised(command, limits, root, label)
            journal.append("child_reaped", role=mode)
        result = _json(c.capture(root / "review/REPORT.json")[0])
        need(result["status"] == "verified" and result["phase"] == phase and result["frame"] == frame_proof,
             "Recovered review result binding")
        _review_terminal(root / "review", frame_proof, job_proof, result)
        _completed_inventory(c.inventory(root)[0])
        c.publish(root / "REPLAY.json", result)
        journal.append("phase_verified", report=c.capture(root / "REPLAY.json")[0])
        journal.close()
        proof = c.publish(root / "PACKAGE-RECEIPT.json", dict(schema_version=2, phase=phase, frame=frame_proof,
                           files=c.inventory(root)[0]))
        return dict(root=str(root), receipt=proof, stage_receipt=result["stage_receipt"])
    except BaseException as error:
        _failure(root, journal, error, phase=phase)
        raise
    finally:
        journal.close()


def execute(frame_path, frame_sha, *, output):
    """Reserve fresh output, then dispatch collect/review/answer/review once each."""
    # Authenticate locations before any write, then retain deeper-validation failures.
    proof, raw = c.capture(frame_path)
    need(proof["sha256"] == plan._sha(frame_sha), "External controller frame mismatch")
    locator = decode(raw)
    need(locator["output"] == str(plan._absolute(output)), "Controller output substitution")
    pf, parent, authority = c._planning(locator["planning_frame"], locator["planning_authority"])
    root = _locations(locator, parent, authority, pf)
    root.mkdir(exist_ok=False)
    journal = c.Journal(root)
    phases, claim, started = {}, None, time.monotonic()
    handle = watchdog = None
    try:
        journal.append("controller_reserved", frame=proof)
        _, checked, frame, parent, authority = verify_frame(frame_path, frame_sha, output)
        need(checked == raw, "Controller frame changed during reservation")
        c._write(root / "FRAME.json", raw)
        journal.append("controller_verified", frame=proof, parent_identity=parent["parent_identity"])
        handle = contain_process_tree()
        watchdog = DeadlineWatchdog(time.monotonic()+sum(frame["phase_seconds"].values())+2*frame["replay_seconds"]+900,
                                    root / "DEADLINE.json")
        watchdog.__enter__()
        phases["collect"] = _phase(proof, frame, parent, authority, "collect", None, None)
        journal.append("phase_accepted", phase="collect", descriptor=phases["collect"])
        # The completed source phase is replayed independently in the answer worker.
        claim = reserve_answers(proof, frame, parent, authority)
        journal.append("answers_claimed", claim=claim)
        phases["answer"] = _phase(proof, frame, parent, authority, "answer", phases["collect"], claim)
        journal.append("phase_accepted", phase="answer", descriptor=phases["answer"])
        verify_frame(frame_path, frame_sha, output)
        complete = c.publish(root / "COMPLETE.json", dict(status="recovered_diagnostic_complete", purpose=frame["purpose"],
            frame=proof, phases=phases, answer_claim=claim, wall_seconds=time.monotonic()-started,
            provider_cost_usd=0, ordinary_retrieval=False, scientific_scoring_performed=False, sc04_complete=False))
        journal.append("controller_completed", complete=complete)
        journal.close()
        receipt = c.publish(root / "ROOT-RECEIPT.json", dict(schema_version=2, kind="sc04_recovered_root_receipt_v2",
                            frame=proof, files=c.inventory(root)[0]))
        return dict(output=str(root), receipt=receipt, phases=phases)
    except BaseException as error:
        _failure(root, journal, error, completed_phases=list(phases), answer_claim=claim,
                 wall_seconds=time.monotonic()-started)
        raise
    finally:
        journal.close()
        if watchdog is not None: watchdog.__exit__(None, None, None)
        _ = handle


def _job(frame_proof, frame, path, sha, output, mode):
    proof, raw = c.capture(path)
    need(proof["sha256"] == plan._sha(sha), "Externally anchored worker job differs")
    job = decode(raw)
    need(set(job) == {"schema_version", "phase", "frame", "collection", "collection_frame", "answer_claim", "cutoff", "import_cache"}
         and job["schema_version"] == 2 and job["phase"] in PHASES and job["frame"] == frame_proof,
         "Recovery worker job schema/binding")
    phase_root = Path(frame["output"]) / job["phase"]
    need(proof["path"] == str(phase_root / "JOB.json") and plan._absolute(output) ==
         phase_root / ("worker" if mode == "worker" else "review"), "Worker role/output location differs")
    cache = ROOT / "data/cache" / ("sc04-recovery-" + frame_proof["sha256"] + "-" + job["phase"])
    need(job["import_cache"] == str(cache), "Worker cache identity differs")
    if job["phase"] == "collect":
        need(job["collection"] is None and job["cutoff"] is None and job["answer_claim"] is None and
             job["collection_frame"]["path"] == str(phase_root / "COLLECTION-FRAME.json") and
             _json(job["collection_frame"]) == frame["collection_frame"], "Collection worker inputs differ")
    else:
        need(job["collection_frame"] is None and job["collection"]["root"] == str(Path(frame["output"]) / "collect"),
             "Answer collection predecessor differs")
        cutoff = datetime.fromisoformat(job["cutoff"])
        need(cutoff.tzinfo is not None and cutoff.utcoffset().total_seconds() == 0, "Aware answer cutoff required")
    return proof, job


def _package(descriptor, frame_proof, phase):
    root = plan._absolute(descriptor["root"])
    proof = descriptor["receipt"]
    need(proof["path"] == str(root / "PACKAGE-RECEIPT.json"), "Phase receipt location differs")
    value = _json(proof)
    need(value == dict(schema_version=2, phase=phase, frame=frame_proof,
                      files=c.inventory(root, omit=("PACKAGE-RECEIPT.json",))[0]), "Phase inventory/frame differs")
    _completed_inventory(value["files"])
    return root


def _prepared(frame, frame_proof, job):
    root = _package(job["collection"], frame_proof, "collect")
    stage = job["collection"]["stage_receipt"]
    need(stage["path"] == str(root / "worker/phase/RECEIPT.json"), "Collection receipt locator differs")
    c.bound(stage)
    return admission.prepare(root / "worker/phase", stage["sha256"], frame["common_root"])


def _input_files(frame_proof, frame, parent, authority, job_proof, job):
    """Exact control/provenance reads; never grants evaluator gold or data roots."""
    inputs = {frame_proof["path"], job_proof["path"]}
    def add(proof):
        c.bound(proof)
        inputs.add(proof["path"])
    for proof in (frame["planning_frame"], frame["planning_authority"], frame["transition_certificate"],
                  parent["interrupted_snapshot"], parent["original_frame"], frame["collection_frame"]["qualification"]):
        add(proof)
    pf = _json(frame["planning_frame"])
    for proof in (pf["registry_policy"], pf["prospective_contract"]): add(proof)
    inputs.update(str(p) for p in Path(pf["output"]).iterdir() if p.is_file())
    audit = _json(parent["interrupted_snapshot"])
    for proof in audit["original_inventory"].values(): add(proof)
    original = _json(parent["original_frame"])
    for key in ("doi_schedule", "answer_queries", "hints"): add(original["products"][key])
    cert = _json(frame["transition_certificate"])
    for key in ("primary_acceptance", "parity_proof", "qualification"): add(cert[key])
    add(_json(cert["primary_acceptance"])["primary_replay"])
    primary_root = Path(cert["primary"]["root"])
    primary_receipt, raw = c.capture(primary_root / "ROOT-RECEIPT.json")
    add(primary_receipt)
    for proof in decode(raw)["files"].values(): add(proof)
    archive_proof, archive_raw = c.capture(cert["source_archive"]["path"])
    add(archive_proof)
    for proof in decode(archive_raw)["files"].values(): add(proof)
    for key in ("collection_frame", "answer_claim"):
        if job[key] is not None: add(job[key])
    if job["collection"] is not None:
        inputs.update(str(p) for p in Path(job["collection"]["root"]).rglob("*") if p.is_file())
    for name in ("collection-execution/CLAIM.json", "answer-execution/CLAIM.json"):
        path = authority / name
        if path.is_file(): inputs.add(str(path))
    inputs.update(str(ROOT / name) for name in frame["code_pins"])
    inputs.add(sys.executable)
    inputs.add(frame["model"]["model_receipt"]["path"])
    inputs.add(frame["model"]["model_license"]["path"])
    return inputs


class WorkerAudit(InputAudit):
    """Narrow extra claim write permission; offline review forbids dispatch APIs."""
    def __init__(self, *, claim_root=None, offline=False, **kwargs):
        super().__init__(**kwargs)
        self.claim_root, self.offline = claim_root, offline

    def mutation_path(self, value):
        # Do not normalize away traversal first: reject ambiguous spelling and
        # then check every existing ancestor for links/reparse points.
        try:
            path = plan._absolute(os.fsdecode(value))
            existing = path
            while not existing.exists(): existing = existing.parent
            safe_path(existing)
            return path
        except (ValueError, OSError, TypeError) as error:
            self.denials += 1
            raise PermissionError("Unsafe worker mutation path") from error

    def hook(self, event, args):
        if self.offline and (event.startswith("socket.") or event in ("subprocess.Popen", "os.system", "os.spawn")):
            self.denials += 1
            raise PermissionError("Offline recovery replay cannot dispatch")
        if event in ("os.link", "os.symlink"):
            self.denials += 1
            raise PermissionError("Worker cannot create filesystem links")
        if event in ("os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.chmod", "os.chown", "os.truncate", "os.utime"):
            paths = args[:2] if event in ("os.rename", "os.link", "os.symlink") else args[:1]
            paths = [self.mutation_path(p) for p in paths]
            allowed = all(p.is_relative_to(self.output) for p in paths)
            if event == "os.mkdir" and self.claim_root is not None and paths[0] == self.claim_root:
                allowed = True
            if not allowed:
                self.denials += 1
                raise PermissionError("Worker filesystem mutation outside owned output")
        if event == "open" and not getattr(self.local, "busy", False) and self.claim_root is not None:
            name, mode, flags = args
            if not isinstance(name, int) and Path(os.fsdecode(name)).absolute() == self.claim_root / "CLAIM.json":
                writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
                if writing and not (flags & os.O_EXCL and flags & os.O_CREAT and not flags & (os.O_TRUNC | os.O_APPEND)):
                    self.denials += 1
                    raise PermissionError("Collection claim may only be exclusively created")
                # Only collection.execute writes its own exclusive claim outside output.
                self.local.busy = True
                try:
                    self.stream.write(canonical(dict(path=str(self.claim_root / "CLAIM.json"), mode=mode,
                        flags=flags, allowed=True, basis="exclusive_collection_claim")) + b"\n")
                    self.opens += 1
                finally:
                    self.local.busy = False
                return
        super().hook(event, args)


def _answer_accounting(report, maximum):
    rows = report["rows"]
    measured = dict(input_tokens=0, output_tokens=0, cost_usd=0.0)
    reserved = dict(input_tokens=0, output_tokens=0)
    generations = 0
    for row in rows:
        need(row["status"] == "completed" and row["product"] is not None, "Completed native answer rows required")
        summary = row["product"]["call"]["summary"]
        generations += int(summary["generation_entered"])
        if summary["usage"] is not None:
            for key in measured: measured[key] += summary["usage"][key]
        reserved["input_tokens"] += summary["reservation_input_tokens"]
        reserved["output_tokens"] += summary["reservation_output_tokens"]
    need(report["scheduled"] == report["entered"] == len(rows) == maximum and report["unexecuted"] == 0
         and generations <= maximum and reserved["output_tokens"] <= maximum * 256 and measured["cost_usd"] == 0,
         "Native answer schedule/call/token/provider ceiling exceeded")
    return dict(scheduled=report["scheduled"], entered=report["entered"], unexecuted=report["unexecuted"],
                generation_calls=generations, measured_usage=measured, conservative_reservations=reserved, maximum_calls=maximum)


def worker(frame_path, frame_sha, job_path, job_sha, *, output):
    proof, _, frame, parent, authority = verify_frame(frame_path, frame_sha)
    job_proof, job = _job(proof, frame, job_path, job_sha, output, "worker")
    phase = job["phase"]
    if phase == "answer": _answer_claim(proof, frame, parent, authority, job["answer_claim"])
    root = plan._absolute(output)
    root.mkdir(exist_ok=False)
    journal = c.Journal(root)
    owner = audit = watchdog = handle = None
    started = time.monotonic()
    try:
        journal.append("worker_reserved", frame=proof, job=job_proof)
        handle = contain_process_tree()
        end = started + frame["phase_seconds"][phase] - 10
        watchdog = DeadlineWatchdog(end, root / "DEADLINE.json")
        watchdog.__enter__()
        empty_import_cache(expected=job["import_cache"], cache_root=ROOT / "data/cache")
        inputs = _input_files(proof, frame, parent, authority, job_proof, job)
        spec = bindings = provenance = None
        if phase == "answer":
            spec, bindings, provenance = _model(frame["model"])
            inputs.update(str(p) for p in bindings.values())
            (root / "server").mkdir()
            c.publish(root / "MODEL.json", dict(spec=encode(spec), bindings={k: str(v) for k,v in bindings.items()},
                                               provenance=encode(provenance), alias=frame["model"]["alias"]))
        c.publish(root / "CONFIG.json", dict(frame=proof, job=job, purpose=frame["purpose"]))
        audit = WorkerAudit(inputs=inputs, output=root, code_roots=(ROOT / "src", ROOT / "packages/tether/src",
            ROOT / "experiments", Path(sys.prefix), Path(sys.base_prefix), Path(job["import_cache"])),
            claim_root=authority / "collection-execution" if phase == "collect" else None)
        audit.activate()
        if phase == "collect":
            cf = job["collection_frame"]
            result = c.execute(cf["path"], cf["sha256"], output=root / "phase")
            stage_receipt = result["receipt"]
            usage = _json(result["manifest"])["accounting"]
        else:
            prepared = _prepared(frame, proof, job)
            # No server is started until the durable parent's answer claim is checked.
            _answer_claim(proof, frame, parent, authority, job["answer_claim"])
            with model.owned_server(spec, bindings, output=root / "server", journal=journal, parent_deadline=end-30) as owner:
                with ProcessSamples(owner.terminal_record["pid"]) as samples:
                    result = pipeline.answer(parent["answer_queries"], parent["hints"], prepared, root / "phase",
                        seconds=max(.001, end-time.monotonic()-40), cutoff=job["cutoff"], model_provenance=provenance,
                        call_model=partial(primary.model_call, owner=owner, model_provenance=provenance, alias=frame["model"]["alias"]))
                c.publish(root / "SERVER-RESOURCE-SAMPLES.json", samples.values)
            need(owner.terminal_record["server_stopped"] is True and result["status"] == "complete", "Incomplete answer/server cleanup")
            stage_receipt = c.capture(root / "phase/STAGE-RECEIPT.json")[0]
            usage = _answer_accounting(result, frame["maximum_answer_calls"])
        need(time.monotonic() < end and source_pins() == frame["code_pins"], "Worker deadline or code freeze changed")
        audit.flush()
        need(audit.denials == 0, "Worker undeclared file access")
        # OwnedServer exposes a deeply immutable terminal snapshot. Convert at
        # the artifact boundary without changing the accepted in-memory state.
        complete = c.publish(root / "COMPLETE.json", encode(dict(status="complete", phase=phase, frame=proof, job=job_proof,
            stage_receipt=stage_receipt, accounting=usage, wall_seconds=time.monotonic()-started,
            worker_memory=process_sample(os.getpid()), server_terminal=owner.terminal_record if owner else None,
            audit_denials=0, provider_cost_usd=0)))
        journal.append("worker_completed", complete=complete)
    except BaseException as error:
        _failure(root, journal, error, phase=phase, wall_seconds=time.monotonic()-started,
                 server_terminal=owner.terminal_record if owner else None)
        raise
    finally:
        if audit is not None: audit.flush()
        journal.close()
        if watchdog is not None: watchdog.__exit__(None, None, None)
        _ = handle


def _review(frame_proof, frame, parent, authority, job_proof, job, anchored=None):
    phase = job["phase"]
    root = Path(job_proof["path"]).parent / "worker"
    def proof_at(path):
        return c.capture(path)[0] if anchored is None else anchored[str(path)]
    complete_proof = proof_at(root / "COMPLETE.json")
    complete = _json(complete_proof)
    need(set(complete) == {"status", "phase", "frame", "job", "stage_receipt", "accounting", "wall_seconds",
         "worker_memory", "server_terminal", "audit_denials", "provider_cost_usd"} and
         complete["status"] == "complete" and complete["phase"] == phase and complete["frame"] == frame_proof
         and complete["job"] == job_proof and complete["audit_denials"] == 0 and complete["provider_cost_usd"] == 0
         and type(complete["wall_seconds"]) in (float, int) and math.isfinite(complete["wall_seconds"]) and
         0 <= complete["wall_seconds"] < frame["phase_seconds"][phase],
         "Worker completion/accounting identity differs")
    need(_json(proof_at(root / "CONFIG.json")) == dict(frame=frame_proof, job=job, purpose=frame["purpose"]),
         "Worker effective configuration differs")
    events = c._chain(c.bound(proof_at(root / "journal.jsonl")))
    need(events[0]["event"] == "worker_reserved" and events[0]["details"] == dict(frame=frame_proof, job=job_proof)
         and events[-1]["event"] == "worker_completed" and events[-1]["details"] == dict(complete=complete_proof),
         "Worker journal/terminal binding differs")
    if phase == "collect":
        need(len(events) == 2, "Collection worker has unexpected dispatch events")
    else:
        need([e["event"] for e in events[1:-1]] == ["server_started", "server_ready", "server_terminal"] and
             events[1]["details"] == events[2]["details"] == dict(pid=complete["server_terminal"]["pid"]) and
             events[-2]["details"] == complete["server_terminal"], "Owned server lifecycle differs")
    for line in c.bound(proof_at(root / "io-audit.jsonl")).splitlines():
        need(decode(line).get("allowed") is True, "Worker recorded a denied access")
    stage = complete["stage_receipt"]
    filename = "RECEIPT.json" if phase == "collect" else "STAGE-RECEIPT.json"
    need(stage["path"] == str(root / "phase" / filename), "Worker stage proof location differs")
    c.bound(stage)
    if phase == "collect":
        result = c.replay(root / "phase", stage["sha256"])
        need(complete["accounting"] == result["manifest"]["accounting"] and complete["server_terminal"] is None,
             "Recovered collection worker accounting differs")
        summary = dict(unique_dois=len(result["manifest"]["doi_schedule"]), accounting=result["manifest"]["accounting"])
    else:
        _answer_claim(frame_proof, frame, parent, authority, job["answer_claim"])
        prepared = _prepared(frame, frame_proof, job)
        info = _json(proof_at(root / "MODEL.json"))
        spec, bindings, provenance = _model(frame["model"])
        need(info == dict(spec=encode(spec), bindings={k:str(v) for k,v in bindings.items()},
                         provenance=encode(provenance), alias=frame["model"]["alias"]) and
             complete["server_terminal"]["server_stopped"] is True, "Original owned model/terminal differs")
        info["owner_pid"] = complete["server_terminal"]["pid"]
        result = pipeline.replay_answers(root / "phase", stage["sha256"], parent["answer_queries"], parent["hints"],
                                         prepared, cutoff=job["cutoff"], model_info=info)
        observed = schedule.inspect(root / "phase")
        report = _json(proof_at(root / "phase/REPORT.json"))
        need(observed["finalized"] and observed["entered"] == len(parent["answer_queries"]) and
             all(row["status"] == "completed" for row in observed["rows"]) and
             complete["accounting"] == _answer_accounting(report, frame["maximum_answer_calls"]),
             "Answer schedule/worker accounting differs")
        summary = encode(result)
    return dict(status="verified", phase=phase, frame=frame_proof, stage_receipt=stage,
                summary=summary, model_or_http_execution_performed=False, scientific_support_verified=False)


def review_worker(frame_path, frame_sha, job_path, job_sha, *, output):
    proof, _, frame, parent, authority = verify_frame(frame_path, frame_sha)
    job_proof, job = _job(proof, frame, job_path, job_sha, output, "review-worker")
    root = plan._absolute(output)
    root.mkdir(exist_ok=False)
    journal = c.Journal(root)
    handle = audit = None
    try:
        journal.append("review_reserved", frame=proof, job=job_proof)
        handle = contain_process_tree()
        with DeadlineWatchdog(time.monotonic()+frame["replay_seconds"]-10, root / "DEADLINE.json"):
            cache = job["import_cache"] + "-review"
            empty_import_cache(expected=cache, cache_root=ROOT / "data/cache")
            inputs = _input_files(proof, frame, parent, authority, job_proof, job)
            inputs.update(str(p) for p in (Path(job_path).parent / "worker").rglob("*") if p.is_file())
            audit = WorkerAudit(inputs=inputs, output=root, code_roots=(ROOT / "src", ROOT / "packages/tether/src",
                ROOT / "experiments", Path(sys.prefix), Path(sys.base_prefix), Path(cache)), offline=True)
            audit.activate()
            result = _review(proof, frame, parent, authority, job_proof, job)
            need(source_pins() == frame["code_pins"] and audit.denials == 0, "Replay code/access invariant")
            report = c.publish(root / "REPORT.json", result)
            journal.append("review_completed", report=report)
    except BaseException as error:
        _failure(root, journal, error)
        raise
    finally:
        if audit is not None: audit.flush()
        journal.close()
        _ = handle


def replay(output, receipt_sha):
    """Read-only full replay; no claims, subprocesses, HTTP or model calls."""
    root = plan._absolute(output)
    receipt_proof, raw = c.capture(root / "ROOT-RECEIPT.json")
    need(receipt_proof["sha256"] == plan._sha(receipt_sha), "External recovery root anchor differs")
    receipt = decode(raw)
    need(set(receipt) == {"schema_version", "kind", "frame", "files"} and receipt["schema_version"] == 2 and
         receipt["kind"] == "sc04_recovered_root_receipt_v2" and
         receipt["files"] == c.inventory(root, omit=("ROOT-RECEIPT.json",))[0], "Recovery root inventory differs")
    _completed_inventory(receipt["files"])
    need({name for name in receipt["files"] if "/" not in name} == {"FRAME.json", "COMPLETE.json", "journal.jsonl"},
         "Unexpected controller artifacts")
    proof = receipt["frame"]
    _, frame_raw, frame, parent, authority = verify_frame(proof["path"], proof["sha256"], root)
    need(c.bound(proof) == frame_raw == c.bound(receipt["files"]["FRAME.json"]), "Recovery frame copy differs")
    complete = _json(receipt["files"]["COMPLETE.json"])
    anchored = {proof["path"]: proof for proof in receipt["files"].values()}
    need(set(complete) == {"status", "purpose", "frame", "phases", "answer_claim", "wall_seconds", "provider_cost_usd",
                          "ordinary_retrieval", "scientific_scoring_performed", "sc04_complete"} and
         complete["status"] == "recovered_diagnostic_complete" and complete["frame"] == proof and
         complete["purpose"] == frame["purpose"] and set(complete["phases"]) == set(PHASES) and
         complete["provider_cost_usd"] == 0 and complete["ordinary_retrieval"] is False and
         complete["scientific_scoring_performed"] is False and complete["sc04_complete"] is False,
         "Recovered completion claim differs")
    wall = complete["wall_seconds"]
    need(type(wall) in (float, int) and math.isfinite(wall) and 0 <= wall <=
         sum(frame["phase_seconds"].values()) + 2 * frame["replay_seconds"] + 1800, "Controller wall time differs")
    _answer_claim(proof, frame, parent, authority, complete["answer_claim"])
    results, child_seconds = {}, 0
    for phase in PHASES:
        descriptor = complete["phases"][phase]
        phase_root = _package(descriptor, proof, phase)
        need(phase_root == root / phase, "Recovery phase output differs")
        job_proof = anchored[str(phase_root / "JOB.json")]
        _, job = _job(proof, frame, job_proof["path"], job_proof["sha256"], phase_root / "review", "review-worker")
        need(job["collection"] == (complete["phases"]["collect"] if phase == "answer" else None) and
             job["answer_claim"] == (complete["answer_claim"] if phase == "answer" else None), "Recovery stage predecessor differs")
        for mode, label in (("worker", "execution"), ("review-worker", "review")):
            command = _json(anchored[str(phase_root / (label + "-COMMAND.json"))])
            cache = job["import_cache"] + ("-review" if mode == "review-worker" else "")
            limits = ProcessLimits(timeout_seconds=frame["phase_seconds"][phase] if mode == "worker" else frame["replay_seconds"],
                                   max_output_bytes=MAX_STREAM_BYTES)
            need(command == dict(command=_command(proof, job_proof, phase_root / ("worker" if mode == "worker" else "review"),
                                                  cache, mode), limits=limits.payload()), "Supervised command/limits changed")
            terminal = _json(anchored[str(phase_root / (label + "-SUPERVISION.json"))])
            need(terminal["returncode"] == 0, "Child did not exit successfully")
            stdout = c.bound(anchored[str(phase_root / (label + "-stdout.txt"))])
            stderr = c.bound(anchored[str(phase_root / (label + "-stderr.txt"))])
            validate_success_report(terminal["supervision"], limits, len(stdout), len(stderr))
            child_seconds += terminal["supervision"]["execution_elapsed_seconds"]
        result = _review(proof, frame, parent, authority, job_proof, job, anchored)
        need(result == _json(anchored[str(phase_root / "REPLAY.json")]) ==
             _json(anchored[str(phase_root / "review/REPORT.json")]) and descriptor["stage_receipt"] == result["stage_receipt"],
             "Retained independent replay differs")
        _review_terminal(phase_root / "review", proof, job_proof, result, anchored)
        events = c._chain(c.bound(anchored[str(phase_root / "journal.jsonl")]))
        need([e["event"] for e in events] == ["phase_reserved", "child_dispatched", "child_reaped", "child_dispatched",
             "child_reaped", "phase_verified"], "Phase dispatch/reap journal differs")
        need(events[0]["details"] == dict(phase=phase, frame=proof) and
             events[-1]["details"] == dict(report=anchored[str(phase_root / "REPLAY.json")]), "Phase journal proof binding")
        for index, mode in ((1, "worker"), (3, "review-worker")):
            label = "execution" if mode == "worker" else "review"
            command = _json(anchored[str(phase_root / (label + "-COMMAND.json"))])["command"]
            need(events[index]["details"] == dict(role=mode, command_sha256=digest(canonical(command))) and
                 events[index+1]["details"] == dict(role=mode), "Dispatch journal command binding")
        results[phase] = result
    need(wall >= child_seconds, "Controller time is shorter than sequential child executions")
    events = c._chain(c.bound(receipt["files"]["journal.jsonl"]))
    expected = [("controller_reserved", dict(frame=proof)),
        ("controller_verified", dict(frame=proof, parent_identity=parent["parent_identity"])),
        ("phase_accepted", dict(phase="collect", descriptor=complete["phases"]["collect"])),
        ("answers_claimed", dict(claim=complete["answer_claim"])),
        ("phase_accepted", dict(phase="answer", descriptor=complete["phases"]["answer"])),
        ("controller_completed", dict(complete=receipt["files"]["COMPLETE.json"]))]
    need([(e["event"], e["details"]) for e in events] == expected, "Controller journal order/claims differ")
    return dict(status="verified", receipt=receipt_proof, phases=results,
                model_or_http_execution_performed=False, scientific_support_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("execute", "worker", "review-worker", "replay"))
    parser.add_argument("--frame", type=Path)
    parser.add_argument("--frame-sha256")
    parser.add_argument("--job", type=Path)
    parser.add_argument("--job-sha256")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt-sha256")
    args = parser.parse_args()
    if args.mode == "replay":
        result = replay(args.output, args.receipt_sha256)
    elif args.mode == "execute":
        result = execute(args.frame, args.frame_sha256, output=args.output)
    else:
        operation = worker if args.mode == "worker" else review_worker
        result = operation(args.frame, args.frame_sha256, args.job, args.job_sha256, output=args.output)
    print(canonical(result).decode("utf-8"), flush=True)


if __name__ == "__main__":
    main()
