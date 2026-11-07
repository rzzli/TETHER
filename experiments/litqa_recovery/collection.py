"""Bounded v2 source collection and model-free replay after an explicit stop.

Completed v1 resolutions stay in their original acquisition roots. Interrupted
metadata remains unresolved, with its original reservation and no synthetic
receipt. Only untouched ordinals can enter the current supplied-source resolver.
This library never runs a model or resumes an execution. A separately supervised
caller must provide the externally anchored execution frame and qualifications.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import stat
import sys
import time

import tether_engine

from experiments.litqa_analysis import supplied_collection
from experiments.litqa_analysis.native_records import canonical, decode, digest, need, read, safe_path
from experiments.litqa_supplied import resolver
from experiments.litqa_recovery import plan as planning


ROOT = Path(__file__).resolve().parents[2]
MAX_FILES = 20000
MAX_TOTAL_BYTES = 512 * 1024 ** 2
RUNTIME_FILES = (
    "experiments/litqa_recovery/collection.py", "experiments/litqa_recovery/plan.py",
    "experiments/litqa_supplied/resolver.py", "experiments/labbench/retrieval.py",
    "experiments/litqa_comparison/__init__.py", "experiments/litqa_comparison/codecs.py",
    "experiments/litqa_analysis/supplied_collection.py", "experiments/litqa_analysis/collection.py",
    "experiments/litqa_analysis/sources.py", "experiments/litqa_analysis/native_records.py",
)


def utc():
    return datetime.now(timezone.utc).isoformat()


def capture(path):
    path = planning._absolute(path)
    raw = read(path, planning.MAX_FILE_BYTES)
    return dict(path=str(path), bytes=len(raw), sha256=digest(raw)), raw


def bound(proof):
    need(isinstance(proof, dict) and set(proof) == {"path", "bytes", "sha256"} and
         type(proof["bytes"]) is int and 0 <= proof["bytes"] <= planning.MAX_FILE_BYTES,
         "Exact collection input proof required")
    planning._sha(proof["sha256"])
    actual, raw = capture(proof["path"])
    need(actual == proof, "Collection input bytes changed")
    return raw


def source_pins():
    names = set(RUNTIME_FILES)
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "src/tether_engine").rglob("*.py"))
    for name in tuple(names):
        for parent in (ROOT / name).parents:
            if parent == ROOT:
                break
            initializer = parent / "__init__.py"
            if initializer.is_file():
                names.add(initializer.relative_to(ROOT).as_posix())
    pins = {name: capture(ROOT / name)[0]["sha256"] for name in sorted(names)}
    installed = Path(tether_engine.__file__).parent
    for name, fingerprint in pins.items():
        if name.startswith("src/tether_engine/"):
            loaded = installed / name.removeprefix("src/tether_engine/")
            need(capture(loaded)[0]["sha256"] == fingerprint, "Loaded engine differs from frozen current source closure")
    return pins


def environment():
    return dict(version=sys.version, executable=capture(sys.executable)[0],
                engine_version=tether_engine.__version__, engine_initializer=capture(tether_engine.__file__)[0])


def _write(path, raw):
    path = planning._absolute(path)
    need(safe_path(path.parent).is_dir(), "Safe existing collection output parent required")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return capture(path)[0]


def publish(path, value):
    return _write(path, canonical(value) + b"\n")


def inventory(root, omit=()):
    root = planning._absolute(root)
    need(safe_path(root).is_dir(), "Collection output root required")
    files, directories, total = {}, set(), 0
    for path in root.rglob("*"):
        planning._absolute(path)
        name = planning._relative(path.relative_to(root).as_posix())
        info = path.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "Linked collection artifact")
        need(len(files) + len(directories) < MAX_FILES, "Collection inventory file bound")
        if stat.S_ISDIR(info.st_mode):
            directories.add(name)
        else:
            need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "Nonregular or linked collection file")
            if name in omit:
                continue
            total += info.st_size
            need(total <= MAX_TOTAL_BYTES, "Collection inventory byte bound")
            files[name] = capture(path)[0]
    return files, directories


def _chain(raw):
    need(raw and raw.endswith(b"\n"), "Incomplete collection journal")
    events, previous = [], None
    for index, line in enumerate(raw.splitlines()):
        event = decode(line)
        need(isinstance(event, dict) and set(event) == {"sequence", "event", "details", "previous_sha256", "sha256"} and
             type(event["sequence"]) is int and event["sequence"] == index and
             event["previous_sha256"] == previous and isinstance(event["details"], dict), "Collection journal sequence")
        need(event["sha256"] == digest(canonical({k: v for k, v in event.items() if k != "sha256"})), "Collection journal hash")
        previous = event["sha256"]
        events.append(event)
    return events


def _planning(frame_proof, authority_proof):
    frame = decode(bound(frame_proof))
    authority = decode(bound(authority_proof))
    need(frame["kind"] == "sc04_recovery_planning_authority_v2" and frame["schema_version"] == 2 and
         frame["automatic_retry"] is False and frame["production_dispatch_qualified"] is False,
         "Planning authority version/policy")
    original = frame["plan"]
    observed = planning.inspect_parent(original["interrupted_snapshot"]["path"], original["interrupted_snapshot"]["sha256"],
        original["original_frame"]["path"], original["original_frame"]["sha256"])
    need(observed == original, "Planning authority differs from independently reconstructed parent")
    need(authority == dict(kind="sc04_parent_continuation_authority_v2", parent_identity=original["parent_identity"],
         frame=frame_proof, allowed_dispatch_ordinals=original["allowed_dispatch_ordinals"],
         interrupted_snapshot=original["interrupted_snapshot"], registry_policy=frame["registry_policy"],
         automatic_retry=False, production_dispatch_qualified=False), "Planning authority contents differ")
    policy = decode(bound(frame["registry_policy"]))
    need(set(policy) == {"schema_version", "kind", "parent_identity", "registry", "contract"} and
         policy["schema_version"] == 1 and policy["kind"] == "sc04_recovery_registry_binding_v1" and
         policy["parent_identity"] == original["parent_identity"] and policy["registry"] == frame["registry"] and
         policy["contract"] == frame["prospective_contract"], "Registry policy/parent binding")
    bound(frame["prospective_contract"])
    need(frame["planner_source"] == capture(Path(planning.__file__))[0], "Planning implementation changed since authority")
    registry = planning._absolute(policy["registry"])
    authority_root = registry / original["parent_identity"]
    need(safe_path(authority_root).is_dir() and str(authority_root) == frame["authority"] and
         authority_proof["path"] == str(authority_root / "AUTHORITY.json"), "Canonical parent authority location")
    planning_root = planning._absolute(frame["output"])
    need(frame_proof["path"] == str(planning_root / "FRAME.json"), "Planning output frame location")
    files, dirs = inventory(planning_root)
    need(not dirs and set(files) == {"FRAME.json", "COMPLETE.json", "journal.jsonl"}, "Incomplete or failed planning output")
    complete = decode(bound(files["COMPLETE.json"]))
    need(complete == dict(status="planning_authority_reserved", frame=frame_proof, authority=authority_proof,
                         model_or_http_execution_performed=False, production_dispatch_qualified=False), "Planning completion binding")
    events = _chain(bound(files["journal.jsonl"]))
    need([e["event"] for e in events] == ["recovery_planning_output_reserved", "parent_authority_reserved", "planning_authority_sealed"] and
         events[1]["details"] == dict(authority=str(authority_root), frame_sha256=frame_proof["sha256"]) and
         events[-1]["details"] == dict(complete_sha256=files["COMPLETE.json"]["sha256"]), "Planning journal/frame/authority binding")
    return frame, original, authority_root


def make_frame(planning_frame, planning_authority, qualification, output, phase_seconds):
    """Return an unpersisted execution frame for a caller to freeze externally."""
    parent_frame, parent, authority_root = _planning(planning_frame, planning_authority)
    original = decode(bound(parent["original_frame"]))
    count = len(parent["allowed_dispatch_ordinals"])
    policy = original["policy"]
    return dict(schema_version=2, kind="sc04_recovered_collection_execution_v2", purpose=original["purpose"],
                created_at_utc=utc(), planning_frame=planning_frame, planning_authority=planning_authority,
                qualification=qualification, output=str(planning._absolute(output)), code_pins=source_pins(), python=environment(),
                policy=policy, limits=dict(phase_seconds=phase_seconds, doi_seconds=60,
                    request_seconds=policy["request_seconds"], new_slots=count, new_http_attempts=2*count,
                    new_response_reservation_bytes=count*(policy["metadata_bytes"]+policy["article_bytes"])),
                automatic_retry=False, provider_cost_usd=0, model_execution_permitted=False)


def verify_frame(path, sha, output):
    proof, raw = capture(path)
    need(proof["sha256"] == planning._sha(sha), "External recovery execution frame mismatch")
    frame = decode(raw)
    need(set(frame) == {"schema_version", "kind", "purpose", "created_at_utc", "planning_frame", "planning_authority", "qualification",
                       "output", "code_pins", "python", "policy", "limits", "automatic_retry", "provider_cost_usd", "model_execution_permitted"} and
         type(frame["schema_version"]) is int and frame["schema_version"] == 2 and
         frame["kind"] == "sc04_recovered_collection_execution_v2" and frame["automatic_retry"] is False and
         frame["provider_cost_usd"] == 0 and frame["model_execution_permitted"] is False, "Recovery execution frame schema/policy")
    need(frame["output"] == str(planning._absolute(output)), "Recovery output differs from frozen frame")
    stamp = datetime.fromisoformat(frame["created_at_utc"])
    need(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0, "UTC recovery freeze required")
    need(frame["code_pins"] == source_pins() and frame["python"] == environment(), "Recovery source/environment changed")
    qualification = decode(bound(frame["qualification"]))
    need(qualification["schema_version"] == 2 and qualification["kind"] == "sc04_recovery_collection_qualification_v2" and
         qualification["status"] == "PASS" and type(qualification["tests"]) is int and qualification["tests"] > 0 and
         all(type(qualification[k]) is int and qualification[k] == 0 for k in ("failures", "errors", "skipped")) and
         qualification["code_pins"] == frame["code_pins"], "Exact current collection qualification required")
    parent_frame, parent, authority_root = _planning(frame["planning_frame"], frame["planning_authority"])
    original = decode(bound(parent["original_frame"]))
    need(frame["purpose"] == original["purpose"] and frame["policy"] == original["policy"], "Original collection purpose/policy changed")
    count = len(parent["allowed_dispatch_ordinals"])
    limits = frame["limits"]
    need(type(limits["phase_seconds"]) is int and 1 <= limits["phase_seconds"] <= 21600 and limits ==
         dict(phase_seconds=limits["phase_seconds"], doi_seconds=60, request_seconds=frame["policy"]["request_seconds"],
              new_slots=count, new_http_attempts=2*count,
              new_response_reservation_bytes=count*(frame["policy"]["metadata_bytes"]+frame["policy"]["article_bytes"])),
         "Explicit recovery resource limits")
    for protected in (Path(parent["original_root"]), authority_root.parent, Path(parent_frame["output"])):
        out = planning._absolute(output)
        need(not out.is_relative_to(protected) and not protected.is_relative_to(out), "Recovery output overlaps an immutable/control root")
    return proof, raw, frame, parent, authority_root


class Journal:
    def __init__(self, root):
        self.path = root / "journal.jsonl"
        self.stream = self.path.open("xb")
        self.previous = None
        self.sequence = 0
    def append(self, event, **details):
        value = dict(sequence=self.sequence, previous_sha256=self.previous, event=event, details=details)
        value["sha256"] = digest(canonical(value))
        self.stream.write(canonical(value) + b"\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.previous, self.sequence = value["sha256"], self.sequence + 1
    def close(self):
        self.stream.close()


def _account(result):
    original = result["accounting"]
    return dict(http_attempts=len(result["manifest"]["requests"]), measured_response_bytes=original["measured_response_bytes"],
                safety_accounted_bytes=original["safety_accounted_bytes"], unknown_transfer_upper_bytes=original["unknown_transfer_upper_bytes"],
                wire_bytes=None, provider_cost_usd=0)


def _resolved(slot, disposition, resolution, parents):
    result = supplied_collection.reconstruct(resolution["root"], resolution["receipt_sha256"], resolution["plan"])
    return dict(ordinal=slot["ordinal"], id=slot["id"], branch="shared", disposition=disposition, resolution=resolution,
                parent_proofs=parents, coverage=result["coverage"], accounting=_account(result)), result


def _inherited(slot):
    need(slot["disposition"] == "inherited_uncertain_metadata", "Expected inherited uncertainty")
    return dict(ordinal=slot["ordinal"], id=slot["id"], branch="shared", disposition="inherited_uncertain_metadata", resolution=None,
                parent_proofs={k: slot[k] for k in ("plan", "journal", "reservation", "response_proof", "terminal_proof")},
                coverage=dict(exact_doi_resolved=None, article_retained=None, source_availability="unknown",
                    missingness="interrupted_metadata_transfer_without_retained_response", ordinary_retrieval=False),
                accounting=dict(http_attempts=1, measured_response_bytes=None,
                    safety_accounted_bytes=slot["accounting"]["safety_accounted_bytes"],
                    unknown_transfer_upper_bytes=slot["accounting"]["unknown_transfer_upper_bytes"], wire_bytes=None, provider_cost_usd=0))


def _total(records):
    return dict(http_attempts=sum(r["accounting"]["http_attempts"] for r in records),
                measured_response_bytes=sum(r["accounting"]["measured_response_bytes"] or 0 for r in records),
                safety_accounted_bytes=sum(r["accounting"]["safety_accounted_bytes"] for r in records),
                unknown_transfer_upper_bytes=sum(r["accounting"]["unknown_transfer_upper_bytes"] for r in records),
                wire_bytes=None, provider_cost_usd=0)


def _accounting(records, parent):
    historical = _total([r for r in records if r["disposition"] in ("adopt_completed", "inherited_uncertain_metadata")])
    need(historical == parent["historical_accounting"], "Inherited physical accounting differs")
    incremental = _total([r for r in records if r["disposition"] == "newly_completed"])
    return dict(historical=historical, incremental=incremental, total=_total(records))


def _latest_availability(resolution, result):
    times = []
    for request in result["manifest"]["requests"]:
        if request["transport_status"] == "captured":
            receipt_raw = read(Path(resolution["root"]) / request["receipt_path"])
            need(digest(receipt_raw) == request["receipt_sha256"], "Source availability receipt differs from verified source")
            receipt = decode(receipt_raw)
            stamp = datetime.fromisoformat(receipt["completed_at_utc"])
            need(stamp.tzinfo is not None, "Aware source receipt timestamp")
            times.append(stamp.astimezone(timezone.utc))
    return times


def _incomplete_usage(root, request_plan):
    """Conservative failure evidence; an invalid/torn prefix never becomes zero."""
    policy = request_plan["policy"]
    cap = policy["metadata_bytes"] + policy["article_bytes"]
    result = dict(status="unverified_attempt_prefix", observed_http_attempts=None, measured_response_bytes=None,
                  safety_accounted_bytes=cap, unknown_transfer_upper_bytes=cap, wire_bytes=None, automatic_retry=False)
    try:
        receipt_proof, _ = capture(root / "RECEIPT.json")
        reconstructed = supplied_collection.reconstruct(root, receipt_proof["sha256"], request_plan)
        return dict(status="completed_source_not_accepted_by_controller", receipt=receipt_proof,
                    accounting=_account(reconstructed), automatic_retry=False)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        proof, raw = capture(root / "journal.jsonl")
        events = _chain(raw)
        starts = [e["details"] for e in events if e["event"] == "http_attempt"]
        need(len(starts) <= 2, "Attempt prefix request bound")
        terminal = [e["details"] for e in events if e["event"] == "http_terminal"]
        need(len(terminal) <= len(starts), "Attempt prefix terminal bound")
        # This report conservatively reserves both possible requests until a
        # completed resolution is independently reconstructible. It never uses
        # producer-reported byte counts as measurements without their originals.
        result.update(status="retained_attempt_prefix", journal=proof, observed_http_attempts=len(starts),
                      request_reservations=starts, observed_terminal_records=len(terminal))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return result


def execute(frame_path, frame_sha, *, output, clock=time.monotonic):
    """Execute each allowed DOI once; failures retain output/authority forever."""
    output = planning._absolute(output)
    need(safe_path(output.parent).is_dir(), "Existing recovery output parent required")
    # Authenticate the locator/control roots before creating any output. Full
    # expensive validation runs inside the durable attempt, but a wrong output
    # must never add even a failure record to an immutable original directory.
    initial_proof, initial_raw = capture(frame_path)
    need(initial_proof["sha256"] == planning._sha(frame_sha), "External recovery execution frame mismatch")
    initial_frame = decode(initial_raw)
    initial_parent, initial_plan, initial_authority = _planning(
        initial_frame["planning_frame"], initial_frame["planning_authority"])
    need(initial_frame["output"] == str(output), "Recovery output differs from frozen frame")
    for root in (initial_plan["original_root"], initial_authority.parent, initial_parent["output"]):
        protected = planning._absolute(root)
        need(not output.is_relative_to(protected) and not protected.is_relative_to(output),
             "Recovery output overlaps an immutable/control root")
    output.mkdir(exist_ok=False)
    journal = Journal(output)
    started = clock()
    rows, frame, parent, current, claim = [], None, None, None, None
    try:
        journal.append("collection_output_reserved", created_at_utc=utc(), owner_pid=os.getpid())
        proof, raw, frame, parent, authority = verify_frame(frame_path, frame_sha, output)
        rows = [dict(ordinal=s["ordinal"], id=s["id"], branch="shared", disposition="unexecuted", resolution=None)
                for s in parent["slots"]]
        need(clock is time.monotonic or frame["purpose"] == "fictional_qualification", "Production requires the native monotonic clock")
        deadline = started + frame["limits"]["phase_seconds"]
        def budget():
            need(clock() < deadline, "Recovered collection phase deadline exceeded")
        budget()
        _write(output / "FRAME.json", raw)
        journal.append("collection_frame_verified", frame_sha256=frame_sha, parent_identity=parent["parent_identity"])
        claim = authority / "collection-execution"
        claim.mkdir(exist_ok=False)
        claim_proof = publish(claim / "CLAIM.json", dict(kind="sc04_collection_execution_claim_v2", frame=proof,
            output=str(output), parent_identity=parent["parent_identity"], allowed_dispatch_ordinals=parent["allowed_dispatch_ordinals"],
            created_at_utc=utc(), automatic_retry=False))
        journal.append("collection_execution_claimed", claim=claim_proof)
        (output / "products").mkdir()
        (output / "records").mkdir()
        availability = []
        for slot in parent["slots"]:
            budget()
            index = slot["ordinal"]
            current = index
            if slot["disposition"] == "adopt_completed":
                product = slot["product"]
                resolution = dict(root=product["root"], receipt_sha256=product["receipt"]["sha256"], plan=product["plan"])
                row, result = _resolved(slot, "adopt_completed", resolution,
                    dict(original_slot=slot["original_slot"], receipt=product["receipt"], manifest=product["manifest"]))
                availability.extend(_latest_availability(resolution, result))
                event = "slot_adopted"
            elif slot["disposition"] == "inherited_uncertain_metadata":
                row = _inherited(slot)
                event = "slot_uncertainty_retained"
            else:
                need(slot["disposition"] == "untouched" and slot["dispatch_allowed"] and
                     index in parent["allowed_dispatch_ordinals"], "Only untouched slots may dispatch")
                request_plan = planning._doi_plan(slot["id"], frame["policy"])
                product_root = output / "products" / f"{index:04d}"
                journal.append("slot_reserved", ordinal=index, id=slot["id"],
                    maximum_response_reservation_bytes=frame["policy"]["metadata_bytes"]+frame["policy"]["article_bytes"],
                    doi_seconds=60)
                rows[index] = dict(rows[index], disposition="new_attempt_incomplete", attempt_root=str(product_root))
                resolver.acquire(request_plan, product_root, deadline=min(deadline, clock()+60))
                budget()
                receipt_proof, _ = capture(product_root / "RECEIPT.json")
                resolution = dict(root=str(product_root), receipt_sha256=receipt_proof["sha256"], plan=request_plan)
                row, result = _resolved(slot, "newly_completed", resolution,
                    dict(receipt=receipt_proof, manifest=capture(product_root / "MANIFEST.json")[0]))
                availability.extend(_latest_availability(resolution, result))
                event = "slot_completed"
            rows[index] = row
            row_proof = publish(output / "records" / f"{index:04d}.json", row)
            journal.append(event, ordinal=index, id=slot["id"], record=row_proof)
            current = None
        budget()
        verified = verify_frame(frame_path, frame_sha, output)
        need(verified[3] == parent, "Immutable parent changed during collection")
        budget()
        cutoff = datetime.now(timezone.utc)
        need(not availability or max(availability) <= cutoff, "Source receipt is future-dated at collection seal")
        accounting = _accounting(rows, parent)
        need(accounting["incremental"]["http_attempts"] <= frame["limits"]["new_http_attempts"] and
             accounting["incremental"]["safety_accounted_bytes"] <= frame["limits"]["new_response_reservation_bytes"],
             "Recovery acquisition budget exceeded")
        manifest = dict(schema_version=2, kind="sc04_recovered_collection_v2", status="complete", execution_frame=proof,
            planning_frame=frame["planning_frame"], parent_identity=parent["parent_identity"], original_root=parent["original_root"],
            doi_schedule=parent["doi_schedule"], answer_queries=parent["answer_queries"], hints=parent["hints"], records=rows,
            accounting=accounting, publication_cutoff=frame["policy"]["cutoff_date"], availability_cutoff=cutoff.isoformat(),
            ordinary_retrieval=False, automatic_retry=False, provider_cost_usd=0, scientific_support_verified=False)
        manifest_proof = publish(output / "MANIFEST.json", manifest)
        resources = publish(output / "RESOURCES.json", dict(wall_seconds=clock()-started,
            phase_seconds=frame["limits"]["phase_seconds"], accounting=accounting, interruption_gap_seconds=None,
            original_stage_deadline_compliance_claimed=False, model_calls=0, provider_cost_usd=0))
        budget()
        complete = publish(output / "COMPLETE.json", dict(status="complete", kind="sc04_recovered_collection_v2",
            manifest=manifest_proof, resources=resources, execution_claim=claim_proof, scientific_scoring_performed=False))
        journal.append("collection_completed", complete=complete)
        journal.close()
        files, _ = inventory(output)
        receipt = publish(output / "RECEIPT.json", dict(schema_version=2, kind="sc04_recovered_collection_receipt_v2",
            status="complete", execution_frame=proof, files=files))
        budget()
        return dict(output=str(output), receipt=receipt, manifest=manifest_proof)
    except BaseException as error:
        failure = dict(error_type=type(error).__name__, automatic_retry=False, original_attempt_modified=False,
                       execution_claim_may_exist=claim is not None and claim.exists(), current_ordinal=current)
        if frame is not None and parent is not None:
            failure["historical_accounting"] = parent["historical_accounting"]
            failure["scheduled_dois"] = parent["scheduled_dois"]
            failure["scheduled_answers"] = parent["scheduled_answers"]
            if current is not None and rows and rows[current]["disposition"] == "new_attempt_incomplete":
                rows[current]["attempt_usage"] = _incomplete_usage(Path(rows[current]["attempt_root"]),
                    planning._doi_plan(rows[current]["id"], frame["policy"]))
            failure["rows"] = rows
        try:
            journal.append("collection_failed", error_type=type(error).__name__, current_ordinal=current, automatic_retry=False)
        except BaseException:
            pass
        try:
            publish(output / "FAILURE.json", failure)
        except BaseException:
            pass
        raise
    finally:
        journal.close()


def replay(output, receipt_sha):
    """Independently reconstruct source rows, scheduling and physical accounting."""
    output = planning._absolute(output)
    receipt_proof, raw = capture(output / "RECEIPT.json")
    need(receipt_proof["sha256"] == planning._sha(receipt_sha), "External recovered-collection receipt mismatch")
    receipt = decode(raw)
    need(set(receipt) == {"schema_version", "kind", "status", "execution_frame", "files"} and receipt["schema_version"] == 2 and
         receipt["kind"] == "sc04_recovered_collection_receipt_v2" and receipt["status"] == "complete", "Recovered receipt schema")
    files, directories = inventory(output, omit=("RECEIPT.json",))
    need(files == receipt["files"] and "FAILURE.json" not in files, "Recovered collection exact file inventory")
    proof = receipt["execution_frame"]
    _, frame_raw, frame, parent, authority = verify_frame(proof["path"], proof["sha256"], output)
    need(bound(proof) == frame_raw == bound(files["FRAME.json"]), "Original execution frame copy differs")
    claim_path = authority / "collection-execution/CLAIM.json"
    claim_proof, claim_raw = capture(claim_path)
    claim = decode(claim_raw)
    need(set(claim) == {"kind", "frame", "output", "parent_identity", "allowed_dispatch_ordinals", "created_at_utc", "automatic_retry"} and
         claim["kind"] == "sc04_collection_execution_claim_v2" and claim["frame"] == proof and claim["output"] == str(output) and
         claim["parent_identity"] == parent["parent_identity"] and claim["allowed_dispatch_ordinals"] == parent["allowed_dispatch_ordinals"] and
         claim["automatic_retry"] is False, "Exclusive execution claim binding")
    events = _chain(bound(files["journal.jsonl"]))
    need(len(events) >= 4 and events[0]["event"] == "collection_output_reserved" and
         events[1]["event"] == "collection_frame_verified" and events[1]["details"] == dict(frame_sha256=proof["sha256"], parent_identity=parent["parent_identity"]) and
         events[2]["event"] == "collection_execution_claimed" and events[2]["details"] == dict(claim=claim_proof), "Recovered setup/claim journal")
    cursor, rows, reconstructions, availability = 3, [], {}, []
    expected_files = {"FRAME.json", "journal.jsonl", "MANIFEST.json", "RESOURCES.json", "COMPLETE.json"}
    expected_dirs = {"records", "products"}
    for slot in parent["slots"]:
        index = slot["ordinal"]
        name = f"records/{index:04d}.json"
        expected_files.add(name)
        row = decode(bound(files[name]))
        if slot["disposition"] == "adopt_completed":
            product = slot["product"]
            resolution = dict(root=product["root"], receipt_sha256=product["receipt"]["sha256"], plan=product["plan"])
            expected, result = _resolved(slot, "adopt_completed", resolution,
                dict(original_slot=slot["original_slot"], receipt=product["receipt"], manifest=product["manifest"]))
            kind = "slot_adopted"
        elif slot["disposition"] == "inherited_uncertain_metadata":
            expected, result, resolution = _inherited(slot), None, None
            kind = "slot_uncertainty_retained"
        else:
            need(events[cursor]["event"] == "slot_reserved" and events[cursor]["details"] == dict(ordinal=index, id=slot["id"],
                 maximum_response_reservation_bytes=frame["policy"]["metadata_bytes"]+frame["policy"]["article_bytes"], doi_seconds=60),
                 "Recovered original-order one-shot reservation")
            cursor += 1
            prefix = f"products/{index:04d}"
            product_root = output / prefix
            resolution = dict(root=str(product_root), receipt_sha256=files[prefix + "/RECEIPT.json"]["sha256"],
                              plan=planning._doi_plan(slot["id"], frame["policy"]))
            expected, result = _resolved(slot, "newly_completed", resolution,
                dict(receipt=files[prefix + "/RECEIPT.json"], manifest=files[prefix + "/MANIFEST.json"]))
            product_receipt = decode(bound(files[prefix + "/RECEIPT.json"]))
            expected_files.update(prefix + "/" + n for n in product_receipt["files"])
            expected_files.add(prefix + "/RECEIPT.json")
            expected_dirs.update((prefix, prefix + "/responses"))
            kind = "slot_completed"
        need(row == expected, "Recovered row differs from original source reconstruction")
        need(events[cursor]["event"] == kind and events[cursor]["details"] == dict(ordinal=index, id=slot["id"], record=files[name]),
             "Recovered row/journal bijection")
        cursor += 1
        rows.append(row)
        reconstructions[slot["id"]] = result
        if result is not None:
            availability.extend(_latest_availability(resolution, result))
    manifest = decode(bound(files["MANIFEST.json"]))
    cutoff = datetime.fromisoformat(manifest["availability_cutoff"])
    need(cutoff.tzinfo is not None and cutoff.utcoffset().total_seconds() == 0 and
         (not availability or max(availability) <= cutoff), "Recovered source availability cutoff")
    accounting = _accounting(rows, parent)
    need(manifest == dict(schema_version=2, kind="sc04_recovered_collection_v2", status="complete", execution_frame=proof,
         planning_frame=frame["planning_frame"], parent_identity=parent["parent_identity"], original_root=parent["original_root"],
         doi_schedule=parent["doi_schedule"], answer_queries=parent["answer_queries"], hints=parent["hints"], records=rows,
         accounting=accounting, publication_cutoff=frame["policy"]["cutoff_date"], availability_cutoff=cutoff.isoformat(),
         ordinary_retrieval=False, automatic_retry=False, provider_cost_usd=0, scientific_support_verified=False), "Recovered manifest full cohort/accounting differs")
    resources = decode(bound(files["RESOURCES.json"]))
    need(set(resources) == {"wall_seconds", "phase_seconds", "accounting", "interruption_gap_seconds", "original_stage_deadline_compliance_claimed", "model_calls", "provider_cost_usd"} and
         type(resources["wall_seconds"]) in (float, int) and 0 <= resources["wall_seconds"] < frame["limits"]["phase_seconds"] and
         resources["phase_seconds"] == frame["limits"]["phase_seconds"] and resources["accounting"] == accounting and
         resources["interruption_gap_seconds"] is None and resources["original_stage_deadline_compliance_claimed"] is False and
         resources["model_calls"] == resources["provider_cost_usd"] == 0, "Recovered physical resources differ")
    complete = decode(bound(files["COMPLETE.json"]))
    need(complete == dict(status="complete", kind="sc04_recovered_collection_v2", manifest=files["MANIFEST.json"],
         resources=files["RESOURCES.json"], execution_claim=claim_proof, scientific_scoring_performed=False), "Recovered completion binding")
    need(len(events) == cursor+1 and events[cursor]["event"] == "collection_completed" and
         events[cursor]["details"] == dict(complete=files["COMPLETE.json"]), "Recovered journal completion")
    need(set(files) == expected_files and directories <= expected_dirs, "Unexpected recovered collection artifacts")
    need(inventory(output, omit=("RECEIPT.json",)) == (files, directories), "Recovered output changed during replay")
    return dict(status="independently_reconstructed", manifest=manifest,
                by_doi={r["id"]: r for r in rows}, reconstructions=reconstructions,
                receipt=receipt_proof, scientific_support_verified=False, model_or_http_execution_performed=False)
