"""Plan an interrupted DOI collection without making HTTP or model calls.

``inspect_parent(audit_path, audit_sha, frame_path, frame_sha)`` consumes the
externally anchored ``sc04_read_only_interrupted_attempt_audit`` inventory and
the separately anchored original frame. Audit summaries and claimed counts are
never used as authority. Every file, ordered reservation, completed product and
the single unresolved metadata-request prefix is reconstructed from originals.
Other interruption shapes fail closed and require a separately qualified design.

``reserve_parent(..., registry_policy_path=..., registry_policy_sha=...,
registry=..., output=...)`` requires an externally anchored registry policy with
exact fields ``schema_version: 1``, ``kind: sc04_recovery_registry_binding_v1``,
``parent_identity``, ``registry`` and a ``contract`` byte proof. It creates a fresh
planning output and an exclusive parent authority in that existing registry.
The anchored policy must be shared by all continuations of that parent. Authorities
are permanent reservations, not expiring leases. A failed reservation/output is
never removed or reused. The result is planning evidence, not a qualified HTTP,
model, collection-completion, or scientific-result artifact.
"""
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import urlencode
from uuid import UUID

from experiments.litqa_analysis import supplied_collection
from experiments.litqa_analysis.native_records import canonical, decode, digest, need, read, safe_path


MAX_FILES = 20000
MAX_FILE_BYTES = 32 * 1024 ** 2
MAX_TOTAL_BYTES = 256 * 1024 ** 2
PHASE = "collect/worker/phase"
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _absolute(value):
    text = os.fspath(value)
    need(isinstance(text, str) and text and "\x00" not in text and
         not text.startswith(("\\\\", "//")), "Unsafe absolute recovery path")
    parts = re.split(r"[/\\]", text)
    need(all(p not in (".", "..") and not p.endswith((".", " ")) for p in parts),
         "Aliased or traversing recovery path")
    path = Path(text)
    need(path.is_absolute() and not any(":" in p for p in path.parts[1:]), "Local absolute recovery path required")
    return path


def _relative(name):
    need(isinstance(name, str) and name and "\\" not in name and ":" not in name and
         "\x00" not in name and all(p and p not in (".", "..") and
         not p.endswith((".", " ")) for p in name.split("/")), "Unsafe inventory path")
    return name


def _sha(value):
    need(isinstance(value, str) and _HEX.fullmatch(value), "Invalid external SHA-256")
    return value


def _capture(path):
    path = _absolute(path)
    raw = read(path, MAX_FILE_BYTES)
    return raw, dict(path=str(path), bytes=len(raw), sha256=digest(raw))


def _proof(path):
    return _capture(path)[1]


def _bound_bytes(proof):
    need(isinstance(proof, dict) and set(proof) == {"path", "bytes", "sha256"} and
         type(proof["bytes"]) is int and 0 <= proof["bytes"] <= MAX_FILE_BYTES,
         "Invalid frozen input proof")
    _sha(proof["sha256"])
    raw, actual = _capture(proof["path"])
    need(actual == proof, "Frozen input bytes changed")
    return raw


def _bound(proof):
    return decode(_bound_bytes(proof))


def _inventory(root):
    root = _absolute(root)
    need(safe_path(root).is_dir(), "Original attempt directory required")
    files, directories = {}, set()
    total = 0
    for path in root.rglob("*"):
        need(len(files) + len(directories) < MAX_FILES, "Interrupted inventory count bound")
        _absolute(path)
        info = path.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "Linked interrupted artifact")
        name = _relative(path.relative_to(root).as_posix())
        if stat.S_ISDIR(info.st_mode):
            directories.add(name)
        else:
            need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "Nonregular or hard-linked interrupted artifact")
            total += info.st_size
            need(total <= MAX_TOTAL_BYTES, "Interrupted inventory total byte bound")
            files[name] = _proof(path)
    return files, directories


def _journal(path, expected=None):
    if expected is None:
        raw = read(path, MAX_FILE_BYTES)
    else:
        need(expected['path'] == str(_absolute(path)), 'Journal proof locator differs')
        raw = _bound_bytes(expected)
    need(raw and raw.endswith(b"\n"), "Truncated or empty journal prefix")
    events, previous = [], None
    for index, line in enumerate(raw.splitlines()):
        event = decode(line)
        need(isinstance(event, dict) and set(event) ==
             {"details", "event", "sequence", "previous_sha256", "sha256"} and
             type(event["sequence"]) is int and event["sequence"] == index and
             event["previous_sha256"] == previous and isinstance(event["details"], dict) and
             isinstance(event["event"], str), "Invalid journal prefix schema")
        fingerprint = event["sha256"]
        _sha(fingerprint)
        need(digest(canonical({k: v for k, v in event.items() if k != "sha256"})) == fingerprint,
             "Invalid journal prefix hash")
        previous = fingerprint
        events.append(event)
    return events


def _reservation(event):
    need(event["event"] == "build_reserved", "Missing original reservation")
    details = event["details"]
    need(set(details) == {"created_at_utc", "owner_pid", "run_id"} and
         type(details["owner_pid"]) is int and details["owner_pid"] > 0 and
         str(UUID(details["run_id"])) == details["run_id"], "Original reservation identity")
    stamp = datetime.fromisoformat(details["created_at_utc"])
    need(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0, "Aware UTC reservation required")


def _doi_plan(doi, policy):
    plan = dict(kind="sc04_supplied_doi_plan_v1", doi=doi, policy=policy,
                metadata_url=supplied_collection.BASE + "search?" + urlencode(
                    dict(query='DOI:"' + doi + '"', format="json", pageSize=10, resultType="core")),
                role="supplied_source_diagnostic", ordinary_retrieval=False)
    supplied_collection.query_plan(plan)
    return plan


def _inputs(frame):
    need(frame["kind"] == "sc04_supplied_execution_v1" and
         frame["purpose"] in ("production", "fictional_qualification") and
         frame["automatic_retry"] is False and frame["ordinary_retrieval"] is False and
         type(frame["provider_cost_usd"]) is int and frame["provider_cost_usd"] == 0,
         "Original supplied-frame role/policy")
    products = frame["products"]
    need(set(products) == {"doi_schedule", "answer_queries", "hints"}, "Exact original input projections")
    dois, queries, hints = (_bound(products[k]) for k in ("doi_schedule", "answer_queries", "hints"))
    need(all(type(frame[k]) is int and frame[k] > 0 for k in ("unique_dois", "questions", "question_doi_pairs")),
         "Original integer cohort sizes")
    need(isinstance(dois, list) and len(dois) == frame["unique_dois"] <= 190 and
         all(isinstance(d, str) for d in dois) and len(set(dois)) == len(dois), "Complete unique DOI schedule")
    need(isinstance(queries, list) and isinstance(hints, list) and
         len(queries) == len(hints) == frame["questions"] <= 199, "Complete query/hint schedule")
    if frame["purpose"] == "production":
        need((len(dois), len(queries), frame["question_doi_pairs"]) == (190, 199, 205), "Complete production cohort")
    ids, flattened = [], []
    for query, hint in zip(queries, hints):
        need(isinstance(query, dict) and set(query) == {"id", "question", "choices"} and
             str(UUID(query["id"])) == query["id"] and isinstance(query["question"], str) and query["question"].strip(),
             "Original visible query fields")
        choices = query["choices"]
        need(isinstance(choices, list) and 2 <= len(choices) <= 26 and
             all(isinstance(c, str) and c.startswith(f"({chr(65+i)}) ") and c[4:].strip()
                 for i, c in enumerate(choices)), "Original option order")
        need(isinstance(hint, dict) and set(hint) == {"id", "question", "dois"} and
             (hint["id"], hint["question"]) == (query["id"], query["question"]) and
             isinstance(hint["dois"], list) and 1 <= len(hint["dois"]) <= 2 and
             all(isinstance(d, str) for d in hint["dois"]) and len(set(hint["dois"])) == len(hint["dois"]),
             "Question/hint identity or order differs")
        ids.append(query["id"])
        flattened.extend(hint["dois"])
    need(len(set(ids)) == len(ids) and len(flattened) == frame["question_doi_pairs"] and
         list(dict.fromkeys(flattened)) == dois, "Complete ordered question-to-DOI join")
    for doi in dois:
        _doi_plan(doi, frame["policy"])
    return dois, queries, hints


def inspect_parent(audit_path, audit_sha, frame_path, frame_sha):
    """Reconstruct a bounded interruption plan; write nothing and dispatch nothing."""
    audit_path, frame_path = _absolute(audit_path), _absolute(frame_path)
    _sha(audit_sha)
    _sha(frame_sha)
    audit_raw, audit_proof = _capture(audit_path)
    frame_raw, frame_proof = _capture(frame_path)
    need(audit_proof["sha256"] == audit_sha and frame_proof["sha256"] == frame_sha,
         "External interruption/frame anchor mismatch")
    audit, frame = decode(audit_raw), decode(frame_raw)
    need(type(audit["schema_version"]) is int and audit["schema_version"] == 1 and
         audit["kind"] == "sc04_read_only_interrupted_attempt_audit" and
         audit["frame_proof"] == frame_proof and
         audit["externally_retained_anchors"]["supplied_frame_sha256"] == frame_sha,
         "Interrupted audit/frame identity differs")
    root = _absolute(audit["original_root"])
    files, directories = _inventory(root)
    expected = audit["original_inventory"]
    need(isinstance(expected, dict) and 0 < len(expected) <= MAX_FILES, "Bounded original snapshot inventory")
    for name, proof in expected.items():
        _relative(name)
        need(isinstance(proof, dict) and set(proof) == {"path", "bytes", "sha256"} and
             type(proof["bytes"]) is int and 0 <= proof["bytes"] <= MAX_FILE_BYTES and
             proof.get("path") == str(root / name), "Original inventory locator differs")
        _sha(proof["sha256"])
    need(files == expected, "Interrupted parent bytes/file membership changed")
    need(files["FRAME.json"]["sha256"] == frame_sha and _bound(files["FRAME.json"]) == frame,
         "Original output frame differs")
    dois, queries, hints = _inputs(frame)
    base = {"FRAME.json", "journal.jsonl", "collect/COMMAND.json", "collect/JOB.json", "collect/journal.jsonl",
            "collect/worker/CONFIG.json", "collect/worker/io-audit.jsonl", "collect/worker/journal.jsonl",
            PHASE + "/CONFIG.json", PHASE + "/journal.jsonl"}
    allowed_files = set(base)
    allowed_dirs = {"collect", "collect/worker", PHASE, PHASE + "/products", PHASE + "/slots"}
    root_events, collect_events, worker_events, stage_events = (
        _journal(root / p, files[p]) for p in ("journal.jsonl", "collect/journal.jsonl", "collect/worker/journal.jsonl", PHASE + "/journal.jsonl"))
    for events in (root_events, collect_events, worker_events, stage_events):
        _reservation(events[0])
    need(len(root_events) == len(collect_events) == 2 and len(worker_events) == 1 and
         root_events[1]["event"] == "diagnostic_phase_started" and root_events[1]["details"] == {"phase": "collect"} and
         collect_events[1]["event"] == "diagnostic_worker_dispatch" and collect_events[1]["details"] == {"phase": "collect"},
         "Unsupported controller/worker interruption prefix")
    job = _bound(files["collect/JOB.json"])
    need(set(job) == {"phase", "frame_sha256", "common_root", "collection", "cutoff", "import_cache"} and
         job["phase"] == "collect" and job["frame_sha256"] == frame_sha and job["common_root"] == str(root) and
         job["collection"] is None and job["cutoff"] is None, "Original collection job identity")
    command = _bound(files["collect/COMMAND.json"])
    argv = command["command"]
    need(isinstance(argv, list) and len(argv) == 17, "Original command shape")
    driver = _absolute(argv[5])
    need(driver.parts[-3:] == ("experiments", "litqa_supplied", "run.py"), "Original collection driver")
    original_repo = driver.parents[2]
    cache = original_repo / "data/cache" / ("sc04-diagnostic-" + root.name + "-collect-imports")
    need(job["import_cache"] == str(cache) and argv == [frame["python"]["path"], "-I", "-B", "-X", "pycache_prefix=" + str(cache),
         str(driver), "worker", "--frame", str(frame_path), "--frame-sha256", frame_sha, "--job", str(root / "collect/JOB.json"),
         "--job-sha256", files["collect/JOB.json"]["sha256"], "--output", str(root / "collect/worker")],
         "Original command/frame/job binding")
    need(set(command) == {"command", "limits"} and command["limits"] ==
         dict(max_output_bytes=4*1024**2, timeout_seconds=frame["phase_seconds"]["collect"]), "Original collection limits")
    config = _bound(files["collect/worker/CONFIG.json"])
    need(config == dict(frame_sha256=frame_sha, job=job, purpose=frame["purpose"]), "Original worker configuration")
    io_raw = _bound_bytes(files["collect/worker/io-audit.jsonl"])
    need(io_raw and io_raw.endswith(b"\n"), "Truncated original I/O prefix")
    for line in io_raw.splitlines():
        need(isinstance(decode(line), dict), "Malformed original I/O prefix")
    schedule = [dict(ordinal=i, id=d, branch="shared") for i, d in enumerate(dois)]
    stage_config = _bound(files[PHASE + "/CONFIG.json"])
    need(set(stage_config) == {"kind", "stage", "ids", "schedule", "seconds"} and
         stage_config["kind"] == "sc04_stage_v1" and stage_config["stage"] == "supplied" and
         stage_config["ids"] == dois and stage_config["schedule"] == schedule and
         type(stage_config["seconds"]) in (int, float) and math.isfinite(stage_config["seconds"]) and
         0 < stage_config["seconds"] <= frame["phase_seconds"]["collect"], "Original collection schedule/configuration")
    need(len(stage_events) >= 2 and stage_events[1]["event"] == "stage_configured" and
         stage_events[1]["details"] == dict(config_sha256=files[PHASE + "/CONFIG.json"]["sha256"]),
         "Stage journal/config binding")
    states, cursor, active = [], 0, None
    measured = conservative = historical_attempts = 0
    for event in stage_events[2:]:
        details = event["details"]
        if event["event"] == "slot_reserved":
            need(active is None and cursor < len(schedule) and details == schedule[cursor], "Nonsequential or repeated slot reservation")
            active = cursor
            cursor += 1
        elif event["event"] == "slot_terminal":
            need(active is not None, "Terminal slot without reservation")
            name = PHASE + f"/slots/{active:04d}.json"
            row = _bound(files[name])
            need(details == dict(ordinal=active, slot_sha256=files[name]["sha256"], path=f"slots/{active:04d}.json", status="completed") and
                 set(row) == {"ordinal", "id", "branch", "status", "reason", "product"} and
                 all(row[k] == v for k, v in schedule[active].items()) and row["status"] == "completed" and row["reason"] is None,
                 "Completed slot identity/hash differs")
            prefix = PHASE + f"/products/{active:04d}"
            product_root, product = root / prefix, row["product"]
            need(isinstance(product, dict) and set(product) == {"root", "receipt", "plan", "manifest"} and
                 product["root"] == str(product_root) and product["receipt"] == files[prefix + "/RECEIPT.json"] and
                 product["manifest"] == files[prefix + "/MANIFEST.json"] and product["plan"] == _doi_plan(row["id"], frame["policy"]),
                 "Completed product locator/plan differs")
            result = supplied_collection.reconstruct(product_root, product["receipt"]["sha256"], product["plan"])
            receipt = _bound(files[prefix + "/RECEIPT.json"])
            allowed_files.update(prefix + "/" + n for n in receipt["files"])
            allowed_files.update((name, prefix + "/RECEIPT.json"))
            allowed_dirs.update((prefix, prefix + "/responses"))
            measured += result["accounting"]["measured_response_bytes"]
            conservative += result["accounting"]["safety_accounted_bytes"]
            historical_attempts += len(result["manifest"]["requests"])
            states.append(dict(**schedule[active], disposition="adopt_completed", dispatch_allowed=False,
                               original_slot=files[name], product=product, coverage=result["coverage"], accounting=result["accounting"]))
            active = None
        else:
            raise ValueError("Unsupported collection journal event; no continuation authorized")
    if active is not None:
        prefix = PHASE + f"/products/{active:04d}"
        plan_path, journal_path = root / (prefix + "/PLAN.json"), root / (prefix + "/journal.jsonl")
        plan = _bound(files[prefix + "/PLAN.json"])
        need(plan == _doi_plan(dois[active], frame["policy"]), "Uncertain original DOI plan differs")
        uncertain = _journal(journal_path, files[prefix + "/journal.jsonl"])
        _reservation(uncertain[0])
        request = dict(request_id="000", kind="metadata", url=plan["metadata_url"],
                       byte_reservation=plan["policy"]["metadata_bytes"], transport_status="started")
        need(len(uncertain) == 3 and uncertain[1]["event"] == "plan_bound" and
             uncertain[1]["details"] == dict(plan_sha256=files[prefix + "/PLAN.json"]["sha256"]) and
             uncertain[2]["event"] == "http_attempt" and uncertain[2]["details"] == request,
             "Unsupported uncertain request prefix")
        allowed_files.update((prefix + "/PLAN.json", prefix + "/journal.jsonl"))
        allowed_dirs.update((prefix, prefix + "/responses"))
        conservative += request["byte_reservation"]
        historical_attempts += 1
        states.append(dict(**schedule[active], disposition="inherited_uncertain_metadata", dispatch_allowed=False,
                           plan=files[prefix + "/PLAN.json"], journal=files[prefix + "/journal.jsonl"],
                           reservation=request, response_proof=None, terminal_proof=None,
                           accounting=dict(measured_response_bytes=None, safety_accounted_bytes=request["byte_reservation"],
                                           unknown_transfer_upper_bytes=request["byte_reservation"])))
    states.extend(dict(**slot, disposition="untouched", dispatch_allowed=True) for slot in schedule[cursor:])
    need(len(states) == len(schedule) and set(files) == allowed_files and directories <= allowed_dirs,
         "Unexplained original artifacts; untouched dispatch cannot be established")
    # Recheck after independent product reconstruction: no moving parent can be
    # silently reduced to whichever files were observed first.
    need(_inventory(root) == (files, directories), "Parent changed during recovery inspection")
    for proof in frame["products"].values():
        _bound(proof)
    need(_proof(audit_path) == audit_proof and _proof(frame_path) == frame_proof, "Anchors changed during inspection")
    key = digest(canonical(dict(original_frame_sha256=frame_sha, original_root_reservation_sha256=root_events[0]["sha256"])))
    return dict(schema_version=2, kind="sc04_interrupted_collection_plan_v2", parent_identity=key,
                original_root=str(root), interrupted_snapshot=audit_proof, original_frame=frame_proof,
                original_root_reservation_sha256=root_events[0]["sha256"],
                parent_inventory_sha256=digest(canonical(files)), original_journal_proofs={
                    name: proof for name, proof in files.items() if name.endswith("/journal.jsonl") or name == "journal.jsonl"},
                input_proofs=frame["products"], doi_schedule=dois, answer_queries=queries, hints=hints, slots=states,
                scheduled_dois=len(dois), scheduled_answers=len(queries), question_doi_pairs=sum(len(h["dois"]) for h in hints),
                prior_answers=0, allowed_dispatch_ordinals=[s["ordinal"] for s in states if s["dispatch_allowed"]],
                historical_accounting=dict(http_attempts=historical_attempts, measured_response_bytes=measured,
                    safety_accounted_bytes=conservative, unknown_transfer_upper_bytes=conservative-measured,
                    wire_bytes=None, provider_cost_usd=0),
                model_or_http_execution_performed=False, production_dispatch_qualified=False,
                scope="Read-only interrupted-source reconstruction; process absence, producer equivalence, recovery execution and scientific acceptance remain separate gates.")


def _write(path, value):
    path = _absolute(path)
    need(safe_path(path.parent).is_dir(), "Safe existing output parent required")
    raw = canonical(value) + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return _proof(path)


def reserve_parent(audit_path, audit_sha, frame_path, frame_sha, *, registry_policy_path,
                   registry_policy_sha, registry, output):
    """Permanently reserve one planning authority; never dispatch or release it."""
    plan = inspect_parent(audit_path, audit_sha, frame_path, frame_sha)
    registry, output, parent = _absolute(registry), _absolute(output), Path(plan["original_root"])
    policy_raw, policy_proof = _capture(registry_policy_path)
    need(policy_proof["sha256"] == _sha(registry_policy_sha), "External registry-policy anchor differs")
    policy = decode(policy_raw)
    need(isinstance(policy, dict) and set(policy) == {"schema_version", "kind", "parent_identity", "registry", "contract"} and
         type(policy["schema_version"]) is int and policy["schema_version"] == 1 and
         policy["kind"] == "sc04_recovery_registry_binding_v1" and policy["parent_identity"] == plan["parent_identity"] and
         policy["registry"] == str(registry), "Registry differs from externally pinned parent policy")
    contract = policy["contract"]
    need(isinstance(contract, dict) and set(contract) == {"path", "bytes", "sha256"} and
         type(contract["bytes"]) is int and 0 <= contract["bytes"] <= MAX_FILE_BYTES and
         _proof(contract["path"]) == contract, "Prospective recovery contract changed")
    need(safe_path(registry).is_dir() and safe_path(output.parent).is_dir(), "Existing explicit registry/output parent required")
    need(not registry.is_relative_to(parent) and not output.is_relative_to(parent) and
         not output.is_relative_to(registry) and not registry.is_relative_to(output), "Recovery roots must remain separate")
    authority = registry / plan["parent_identity"]
    output.mkdir(exist_ok=False)
    events, previous = [], None
    def event(name, **details):
        nonlocal previous
        value = dict(event=name, details=details, sequence=len(events), previous_sha256=previous)
        value["sha256"] = digest(canonical(value))
        with (output / "journal.jsonl").open("ab") as stream:
            stream.write(canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        previous = value["sha256"]
        events.append(value)
    try:
        event("recovery_planning_output_reserved", created_at_utc=datetime.now(timezone.utc).isoformat(), owner_pid=os.getpid())
        frame = dict(kind="sc04_recovery_planning_authority_v2", schema_version=2, plan=plan,
                     registry=str(registry), authority=str(authority), output=str(output),
                     registry_policy=policy_proof, prospective_contract=contract,
                     created_at_utc=datetime.now(timezone.utc).isoformat(), planner_source=_proof(__file__),
                     python=dict(version=sys.version, executable=_proof(sys.executable)),
                     automatic_retry=False, production_dispatch_qualified=False)
        frame_proof = _write(output / "FRAME.json", frame)
        # mkdir is the exclusive cross-output lock. Even an empty authority
        # directory after a write failure prevents a competing reservation.
        authority.mkdir(exist_ok=False)
        event("parent_authority_reserved", authority=str(authority), frame_sha256=frame_proof["sha256"])
        authority_proof = _write(authority / "AUTHORITY.json", dict(kind="sc04_parent_continuation_authority_v2",
            parent_identity=plan["parent_identity"], frame=frame_proof, allowed_dispatch_ordinals=plan["allowed_dispatch_ordinals"],
            interrupted_snapshot=plan["interrupted_snapshot"], registry_policy=policy_proof,
            automatic_retry=False, production_dispatch_qualified=False))
        need(inspect_parent(audit_path, audit_sha, frame_path, frame_sha) == plan, "Parent changed before authority finalization")
        need(_proof(policy_proof["path"]) == policy_proof and _proof(contract["path"]) == contract,
             "Recovery authority policy changed during reservation")
        complete = _write(output / "COMPLETE.json", dict(status="planning_authority_reserved", frame=frame_proof,
                          authority=authority_proof, model_or_http_execution_performed=False, production_dispatch_qualified=False))
        event("planning_authority_sealed", complete_sha256=complete["sha256"])
        return dict(output=str(output), frame=frame_proof, authority=authority_proof, complete=complete)
    except BaseException as error:
        try:
            event("planning_failed", error_type=type(error).__name__, automatic_retry=False)
            _write(output / "FAILURE.json", dict(error_type=type(error).__name__, automatic_retry=False,
                   authority_may_be_reserved=authority.exists(), original_attempt_modified=False))
        except BaseException:
            pass
        raise
