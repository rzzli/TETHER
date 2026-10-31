"""Pure, independent validator for the frozen public observation DATA v2.

Authority: PUBLIC-OBSERVATION-SCHEMA-v2 SHA256
50ee2d7a9285370e6a3f0d18801c43e441b327f7ceac9eb46ebdf0463eff28d6.
Lexical API/module and first-batch descriptor domains come from the pinned
proposal-v2 and synthetic-cohort-v1 metadata. No subject module is imported.
This checks actual observation format, not scenario expectations or readiness.
"""

from math import isfinite


class SnapshotValidationError(ValueError):
    """Malformed public observation; path identifies the first rejected field."""

    def __init__(self, path):
        self.path = path
        super().__init__(path)


APIS = ("CreateFileW", "GetFileType", "GetFileInformationByHandleEx",
        "GetFinalPathNameByHandleW", "GetFileSizeEx", "ReadFile", "CloseHandle")
MODULES = ("cohort_leaf", "cohort_entry")
KINDS = ("candidate", "cleanup", "failure", "receipt", "seal")
STAGES = ("authority_factory", "checker_factory", "admit_reconcile",
          "hash_remaining", "archive", "journal", "resources", "core", "consistency")
GATES = ("admission", "hashes", "archive", "journal", "resources", "core",
         "consistency", "leases_closed", "sealed", "final_clock")
PHASES = ("CREATED", "PLAN", "RESERVATION", "EARLY_CAPTURE", "HANDOFF",
          "LOADING", "CONTINUATION", "CHECKERS", "FINALIZING", "FINALIZED")
STATUSES = ("ACTIVE", "REFUSED", "INCOMPLETE", "PURE_SEAM_COMPLETE_CONSISTENT",
            "PURE_SEAM_COMPLETE_NEGATIVE")
REFUSALS = (None, "INVALID_INPUT", "PLAN_NOT_ADMITTED", "JOINT_CAP_EXCEEDED",
            "FOREIGN_IDENTITY", "PORT_ALREADY_BOUND", "OUTPUT_NOT_OWNED",
            "OUTPUT_ALREADY_RESERVED", "EARLY_DESCRIPTOR_MISMATCH",
            "EARLY_SOURCE_NOT_LIVE_COMPLETE", "HANDOFF_REPEATED",
            "CONTINUATION_REPEATED", "SOURCE_LOADER_UNBOUND", "SOURCE_IMPORT_REFUSED",
            "RAW_RETURN_UNKNOWN", "READ_COUNT_UNKNOWN", "READ_PROGRESS_INCOMPLETE",
            "IDENTITY_INCOMPLETE", "CHECKER_BINDING_REFUSED", "CHECKER_CONTEXT_REFUSED",
            "PUBLICATION_REFUSED", "JOURNAL_CLOSED", "POST_SEAL_DISPATCH",
            "WORK_DEADLINE", "HARD_DEADLINE", "CLOCK_INVALID", "FINALIZED_MISUSE")
DIAGNOSTIC_PHASES = (
    "binding_invoke", "pre_dispatch", "after_scalar_before_aux",
    "after_scalar_before_right_transfer", "error_copy", "RawReturn_allocation",
    "after_count_before_aux", "buffer_copy", "hash_update", "post_call_clock",
    "identity_query", "handoff", "close_wrapper", "cleanup_publication", "entry",
    "bind_ports", "bind_test_hooks", "bind_test_compiler", "admit_plan",
    "reserve_output", "capture_early", "issue_continuation", "claim_continuation",
    "load_source", "continue_once", "finalize", "journal_append", "journal_close",
    "publish_candidate", "publish_cleanup", "publish_failure", "publish_receipt",
    "publish_seal", "original_close", "diagnostic_format", "final_clock",
    "authority_factory", "checker_factory", "admit_reconcile", "hash_remaining",
    "archive", "journal", "resources", "core", "consistency", "copy_bytes",
    "before_final_ack")
EVENTS = ("output_reserved", "source_open_reserved", "source_open_returned",
          "source_identity_reserved", "source_identity_returned", "source_hash_reserved",
          "source_hash_returned", "handoff_reserved", "handoff_claimed",
          "source_compile_reserved", "source_compile_returned", "file_open_reserved",
          "file_open_returned", "file_hash_reserved", "file_hash_returned",
          "stage_reserved", "stage_returned", "finalization_reserved",
          "publication_reserved", "publication_returned", "original_close_reserved",
          "original_close_returned_or_unknown", "journal_close_reserved")
OPERATION = ("not_attempted", "reserved", "entered_return_unknown", "return_observed", "refused")
QUALIFICATIONS = ("FFI_registration_proven", "originals_authenticated",
                  "production_owner_bound", "profile_qualified", "real_checkers_bound",
                  "runtime_authorized", "verification_complete")


def _bad(path):
    raise SnapshotValidationError(path)


def _record(value, keys, path):
    if type(value) is not dict or any(type(k) is not str for k in value):
        _bad(path)
    if len(value) != len(keys) or set(value) != set(keys):
        _bad(path)


def _list(value, cap, path):
    if type(value) is not list or (cap is not None and len(value) > cap):
        _bad(path)


def _int(value, cap, path, minimum=0):
    if type(value) is not int or not minimum <= value <= cap:
        _bad(path)


def _bool(value, path):
    if type(value) is not bool:
        _bad(path)


def _str(value, cap, path):
    if type(value) is not str or (cap is not None and len(value) > cap):
        _bad(path)


def _enum(value, choices, path):
    if type(value) is not str or value not in choices:
        _bad(path)


def _nullable_enum(value, choices, path):
    if value is not None:
        _enum(value, choices, path)


def _time(value, path, minimum=None):
    if type(value) not in (int, float) or (type(value) is float and not isfinite(value)):
        _bad(path)
    if minimum is not None and value < minimum:
        _bad(path)


def _hex(value, path, nullable=True):
    if value is None and nullable:
        return
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        _bad(path)


def _flags(record, names, path):
    for name in names:
        _bool(record[name], path + "." + name)


def _atom(value, tags, path):
    _record(value, ("tag", "value"), path)
    _enum(value["tag"], tags, path + ".tag")
    tag, scalar = value["tag"], value["value"]
    if tag in ("UNOBSERVED", "NULL"):
        if scalar is not None:
            _bad(path + ".value")
    elif tag == "BOOL32":
        _int(scalar, (1 << 31) - 1, path + ".value", -(1 << 31))
    else:
        _int(scalar, (1 << (64 if tag == "HANDLE" else 32)) - 1, path + ".value")


def _path(value, path):
    _str(value, 4096, path)
    # DOS path labels only; no filesystem normalization or lookup is performed.
    if (len(value) < 3 or value[0] not in "CcDd" or value[1] != ":"
            or value[2] not in "/\\" or "\x00" in value):
        _bad(path)
    units = sum(2 if ord(c) > 0xffff else 1 for c in value)
    if units > 4096 or any(0xd800 <= ord(c) <= 0xdfff for c in value):
        _bad(path)


def _link(value, path):
    if value is None:
        return
    _record(value, ("bytes", "sha256"), path)
    _int(value["bytes"], 524288, path + ".bytes")
    _hex(value["sha256"], path + ".sha256", False)


def _callback(value, cap, path, no_payload=False):
    _record(value, ("attempted", "return_observed", "acknowledged", "prepared_bytes",
                    "prepared_sha256", "semantics"), path)
    _flags(value, ("attempted", "return_observed", "acknowledged"), path)
    _int(value["prepared_bytes"], cap, path + ".prepared_bytes")
    _hex(value["prepared_sha256"], path + ".prepared_sha256")
    if type(value["semantics"]) is not str or value["semantics"] != "fictional_callback_not_physical_IO":
        _bad(path + ".semantics")
    if value["return_observed"] and not value["attempted"]:
        _bad(path + ".return_observed")
    if value["acknowledged"] and not value["return_observed"]:
        _bad(path + ".acknowledged")
    if value["prepared_sha256"] is None and value["prepared_bytes"] != 0:
        _bad(path + ".prepared_sha256")
    if no_payload and (value["prepared_bytes"] != 0 or value["prepared_sha256"] is not None):
        _bad(path + ".prepared_bytes")


def _diagnostic(value, path, identity_check):
    _record(value, ("identity", "phase", "class_name", "message", "args_repr", "format_failed"), path)
    token = value["identity"]
    # Only this field may be an opaque object. Its provenance is checked by the
    # independent driver's actual owner.exception_for_token identity resolver.
    if (issubclass(type(token), BaseException) or type(token) in
            (type(None), bool, int, float, str, bytes, list, dict, tuple, set, frozenset, bytearray)):
        _bad(path + ".identity")
    if identity_check is None or identity_check(token) is not True:
        _bad(path + ".identity")
    _enum(value["phase"], DIAGNOSTIC_PHASES, path + ".phase")
    _str(value["class_name"], 128, path + ".class_name")
    _str(value["message"], 256, path + ".message")
    _list(value["args_repr"], 8, path + ".args_repr")
    for i, item in enumerate(value["args_repr"]):
        # DATA supplies a count bound but no numeric per-repr string cap.
        # Do not invent one from the independently specified message cap.
        _str(item, None, path + ".args_repr[" + str(i) + "]")
    _bool(value["format_failed"], path + ".format_failed")


def _context(value, files, path):
    if value is None:
        return
    _record(value, ("file_ids", "captured_bytes", "digests", "complete"), path)
    _list(value["file_ids"], len(files), path + ".file_ids")
    previous = -1
    for i, fid in enumerate(value["file_ids"]):
        _int(fid, len(files) - 1, path + ".file_ids[" + str(i) + "]")
        if fid <= previous:
            _bad(path + ".file_ids[" + str(i) + "]")
        previous = fid
    _int(value["captured_bytes"], 16384, path + ".captured_bytes")
    _bool(value["complete"], path + ".complete")
    digests = value["digests"]
    if type(digests) is not dict or len(digests) > len(files):
        _bad(path + ".digests")
    known = [f["spec"]["path"] for f in files]
    for key, digest in digests.items():
        _path(key, path + ".digests.<path>")
        if key not in known:
            _bad(path + ".digests.<path>")
        _hex(digest, path + ".digests.<path>", False)


def validate_snapshot(value, *, diagnostic_identity_check=None):
    """Validate an ACTUAL detached Snapshot/FinalResult.to_dict(), or raise.

    diagnostic_identity_check(token) must return exact True for each opaque
    diagnostic token. Callback exceptions propagate unchanged. No callback is
    needed when errors contains no diagnostics. The function performs no I/O.
    """
    p = "$"
    _record(value, ("scope", "status", "phase", "refusal_code", "finalized", "pure_seam_complete",
                    "origin", "plan", "files", "calls", "api_counters", "byte_totals",
                    "early_context", "evidence_context", "loader", "journal", "outputs",
                    "stages", "gates", "errors", "terminal", "qualification"), p)
    if type(value["scope"]) is not str or value["scope"] != "pure_shared_owner_seam":
        _bad(p + ".scope")
    _enum(value["status"], STATUSES, p + ".status")
    _enum(value["phase"], PHASES, p + ".phase")
    _nullable_enum(value["refusal_code"], REFUSALS, p + ".refusal_code")
    _flags(value, ("finalized", "pure_seam_complete"), p)
    if value["finalized"] and not value["pure_seam_complete"] and value["status"] not in ("REFUSED", "INCOMPLETE"):
        _bad(p + ".status")
    q = value["qualification"]
    _record(q, QUALIFICATIONS, p + ".qualification")
    for key in QUALIFICATIONS:
        if q[key] is not False:
            _bad(p + ".qualification." + key)

    origin = value["origin"]
    _record(origin, ("start", "now", "work_end", "hard_end", "clock_state"), p + ".origin")
    for key in ("start", "now", "work_end", "hard_end"):
        _time(origin[key], p + ".origin." + key)
    if origin["now"] < origin["start"]:
        _bad(p + ".origin.now")
    for key, offset in (("work_end", 295), ("hard_end", 300)):
        if origin[key] != origin["start"] + offset:
            _bad(p + ".origin." + key)
    _enum(origin["clock_state"], ("ok", "work_expired", "hard_expired", "invalid"), p + ".origin.clock_state")

    files, calls, plan = value["files"], value["calls"], value["plan"]
    _list(files, 4, p + ".files")
    n, r, c, e, m = len(files), 68, 92, 224, 2
    if plan is not None:
        _record(plan, ("N", "B", "M", "R", "C", "E", "calls_used", "events_used", "capture_used",
                       "raw_storage_used", "raw_storage_peak", "read_buffer_capacity", "read_generation",
                       "output_reserved_bytes"), p + ".plan")
        limits = {"N": 4, "B": 2, "M": 2, "R": 68, "C": 92, "E": 224, "calls_used": 92,
                  "events_used": 224, "capture_used": 16384, "raw_storage_used": 131072,
                  "raw_storage_peak": 131072, "read_buffer_capacity": 65536,
                  "read_generation": 68, "output_reserved_bytes": 524288}
        for key, limit in limits.items():
            _int(plan[key], limit, p + ".plan." + key)
        n, r, c, e, m = plan["N"], plan["R"], plan["C"], plan["E"], plan["M"]
        if len(files) != n:
            _bad(p + ".files")
        if plan["B"] > n or c != 6 * n + r or e != 6 * n + 2 * plan["B"] + 2 * m + 192:
            _bad(p + ".plan")
        if plan["calls_used"] > c or plan["events_used"] > e or plan["read_generation"] > r:
            _bad(p + ".plan")
        if plan["raw_storage_used"] > plan["raw_storage_peak"]:
            _bad(p + ".plan.raw_storage_used")

    query_ids = []
    for i, file in enumerate(files):
        fp = p + ".files[" + str(i) + "]"
        _record(file, ("id", "spec", "early", "open_state", "handle_fact", "identity_state", "identity_queries",
                       "open_invocations", "read_invocations", "read_scalar_returns", "known_read_bytes", "hashed_bytes",
                       "captured_bytes", "read_count_unknown", "hash_complete", "capture_complete", "actual_sha256",
                       "close_reserved", "close_invocations", "close_return_observed", "close_success", "close_state"), fp)
        _int(file["id"], n - 1, fp + ".id")
        if file["id"] != i:
            _bad(fp + ".id")
        spec = file["spec"]
        _record(spec, ("path", "role", "size", "sha256", "capture"), fp + ".spec")
        _path(spec["path"], fp + ".spec.path")
        _enum(spec["role"], ("software", "owner_metadata", "artifact"), fp + ".spec.role")
        _int(spec["size"], 4096, fp + ".spec.size")
        _hex(spec["sha256"], fp + ".spec.sha256", False)
        if spec["capture"] is not True:
            _bad(fp + ".spec.capture")
        _flags(file, ("early", "read_count_unknown", "hash_complete", "capture_complete", "close_reserved", "close_return_observed"), fp)
        _enum(file["open_state"], ("unopened", "reserved", "entered_return_unknown", "owned", "known_failure_no_handle", "ownership_unknown"), fp + ".open_state")
        _atom(file["handle_fact"], ("UNOBSERVED", "NULL", "HANDLE"), fp + ".handle_fact")
        _enum(file["identity_state"], ("not_attempted", "in_progress", "verified", "refused", "unknown"), fp + ".identity_state")
        _enum(file["close_state"], ("not_attempted", "reserved", "not_dispatched_deadline", "entered_return_unknown", "returned_success", "returned_failure"), fp + ".close_state")
        for key in ("open_invocations", "close_invocations"):
            _int(file[key], 1, fp + "." + key)
        ri = (spec["size"] + 65535) // 65536 + 16 if spec["size"] else 0
        _int(file["read_invocations"], ri, fp + ".read_invocations")
        _int(file["read_scalar_returns"], file["read_invocations"], fp + ".read_scalar_returns")
        for key in ("known_read_bytes", "hashed_bytes", "captured_bytes"):
            _int(file[key], spec["size"], fp + "." + key)
        _hex(file["actual_sha256"], fp + ".actual_sha256")
        if file["close_success"] is not None:
            _bool(file["close_success"], fp + ".close_success")
        _list(file["identity_queries"], 4, fp + ".identity_queries")
        previous = -1
        for j, ordinal in enumerate(file["identity_queries"]):
            _int(ordinal, c - 1, fp + ".identity_queries[" + str(j) + "]")
            if ordinal <= previous:
                _bad(fp + ".identity_queries[" + str(j) + "]")
            previous = ordinal
            query_ids.append((i, ordinal, fp + ".identity_queries[" + str(j) + "]"))
    if plan is not None:
        derived_r = sum(((f["spec"]["size"] + 65535) // 65536 + 16) if f["spec"]["size"] else 0 for f in files)
        if r != derived_r or plan["B"] != sum(f["early"] for f in files):
            _bad(p + ".plan")

    _list(calls, c, p + ".calls")
    api_records = {api: 0 for api in APIS}
    for i, call in enumerate(calls):
        cp = p + ".calls[" + str(i) + "]"
        _record(call, ("ordinal", "api", "file_id", "reserved", "invocation_reserved", "raw_scalar", "raw_count", "raw_error",
                       "error_defined", "scalar_aux_ack", "count_aux_ack", "right_transfer_ack", "wrapper_return_observed",
                       "wrapper_state", "stopped", "count_defined", "buffer_state", "buffer_generation", "raw_buffer_bytes", "raw_buffer_sha256"), cp)
        _int(call["ordinal"], c - 1, cp + ".ordinal")
        if call["ordinal"] != i:
            _bad(cp + ".ordinal")
        _enum(call["api"], APIS, cp + ".api")
        api_records[call["api"]] += 1
        _int(call["file_id"], n - 1, cp + ".file_id")
        _flags(call, ("reserved", "invocation_reserved", "error_defined", "scalar_aux_ack", "count_aux_ack",
                      "right_transfer_ack", "wrapper_return_observed", "stopped", "count_defined"), cp)
        tags = (("UNOBSERVED", "NULL", "HANDLE") if call["api"] == "CreateFileW" else
                ("UNOBSERVED", "DWORD") if call["api"] in ("GetFileType", "GetFinalPathNameByHandleW") else
                ("UNOBSERVED", "BOOL32"))
        _atom(call["raw_scalar"], tags, cp + ".raw_scalar")
        _atom(call["raw_count"], ("UNOBSERVED", "COUNT32") if call["api"] == "ReadFile" else ("UNOBSERVED",), cp + ".raw_count")
        _atom(call["raw_error"], ("UNOBSERVED", "DWORD"), cp + ".raw_error")
        _enum(call["wrapper_state"], ("not_returned", "returned", "raised"), cp + ".wrapper_state")
        _enum(call["buffer_state"], ("not_applicable", "reserved", "raw_retained", "defined", "malformed", "unknown"), cp + ".buffer_state")
        if call["buffer_generation"] is not None:
            _int(call["buffer_generation"], r, cp + ".buffer_generation")
        if call["raw_buffer_bytes"] is not None:
            frame_caps = {"ReadFile": 65536, "GetFileInformationByHandleEx": 8,
                          "GetFinalPathNameByHandleW": 8202, "GetFileSizeEx": 8}
            if call["api"] not in frame_caps:
                _bad(cp + ".raw_buffer_bytes")
            _int(call["raw_buffer_bytes"], frame_caps[call["api"]], cp + ".raw_buffer_bytes")
        _hex(call["raw_buffer_sha256"], cp + ".raw_buffer_sha256")
        if (call["raw_buffer_bytes"] is None) != (call["raw_buffer_sha256"] is None):
            _bad(cp + ".raw_buffer_sha256")
    for fid, ordinal, path in query_ids:
        if ordinal >= len(calls) or calls[ordinal]["file_id"] != fid or calls[ordinal]["api"] not in (
                "GetFileType", "GetFileInformationByHandleEx", "GetFinalPathNameByHandleW", "GetFileSizeEx"):
            _bad(path)
    if plan is not None and plan["calls_used"] != len(calls):
        _bad(p + ".plan.calls_used")
    counters = value["api_counters"]
    _record(counters, APIS, p + ".api_counters")
    for api in APIS:
        ap = p + ".api_counters." + api
        counter = counters[api]
        _record(counter, ("reserved", "invocations", "scalar_returns", "count_values", "wrapper_returns"), ap)
        for key in counter:
            _int(counter[key], api_records[api] if key != "count_values" or api == "ReadFile" else 0, ap + "." + key)
        if counter["reserved"] != api_records[api]:
            _bad(ap + ".reserved")

    totals = value["byte_totals"]
    total_keys = ("known_read_bytes", "hashed_bytes", "captured_bytes", "early_known_read_bytes", "early_hashed_bytes",
                  "early_captured_bytes", "remaining_known_read_bytes", "remaining_hashed_bytes", "remaining_captured_bytes",
                  "read_count_unknown", "early_reopens_after_claim", "early_rehashes_after_claim")
    _record(totals, total_keys, p + ".byte_totals")
    for key in total_keys:
        if key == "read_count_unknown":
            _bool(totals[key], p + ".byte_totals." + key)
        else:
            _int(totals[key], 92 if key == "early_reopens_after_claim" else 68 if key == "early_rehashes_after_claim" else 16384, p + ".byte_totals." + key)
    _context(value["early_context"], files, p + ".early_context")
    _context(value["evidence_context"], files, p + ".evidence_context")

    loader = value["loader"]
    _record(loader, ("bound", "attempted", "returned", "cache_hits", "records"), p + ".loader")
    _bool(loader["bound"], p + ".loader.bound")
    for key in ("attempted", "returned", "cache_hits"):
        # Cache hits need not be unique; all names remain in the closed graph.
        _list(loader[key], None if key == "cache_hits" else m, p + ".loader." + key)
        for i, name in enumerate(loader[key]):
            _enum(name, MODULES, p + ".loader." + key + "[" + str(i) + "]")
        if key != "cache_hits" and len(set(loader[key])) != len(loader[key]):
            _bad(p + ".loader." + key)
    _list(loader["records"], m, p + ".loader.records")
    seen = set()
    for i, record in enumerate(loader["records"]):
        lp = p + ".loader.records[" + str(i) + "]"
        _record(record, ("module", "state", "return_observed", "accepted"), lp)
        _enum(record["module"], MODULES, lp + ".module")
        if record["module"] in seen:
            _bad(lp + ".module")
        seen.add(record["module"])
        _enum(record["state"], OPERATION, lp + ".state")
        _flags(record, ("return_observed", "accepted"), lp)

    journal = value["journal"]
    _record(journal, ("reservation", "next_sequence", "closed", "close_return_observed", "close_acknowledged", "tip", "events"), p + ".journal")
    _int(journal["reservation"], e, p + ".journal.reservation")
    if journal["reservation"] not in (0, e):
        _bad(p + ".journal.reservation")
    _int(journal["next_sequence"], e, p + ".journal.next_sequence")
    _flags(journal, ("closed", "close_return_observed", "close_acknowledged"), p + ".journal")
    _link(journal["tip"], p + ".journal.tip")
    _list(journal["events"], e, p + ".journal.events")
    if journal["next_sequence"] != len(journal["events"]):
        _bad(p + ".journal.next_sequence")
    for i, event in enumerate(journal["events"]):
        ep = p + ".journal.events[" + str(i) + "]"
        _record(event, ("sequence", "event", "stage", "kind", "file_id", "module", "elapsed", "state", "return_observed", "acknowledged"), ep)
        _int(event["sequence"], e - 1, ep + ".sequence")
        if event["sequence"] != i:
            _bad(ep + ".sequence")
        _enum(event["event"], EVENTS, ep + ".event")
        _nullable_enum(event["stage"], STAGES, ep + ".stage")
        _nullable_enum(event["kind"], KINDS[:3], ep + ".kind")
        _nullable_enum(event["module"], MODULES, ep + ".module")
        if event["file_id"] is not None:
            _int(event["file_id"], n - 1, ep + ".file_id")
        _time(event["elapsed"], ep + ".elapsed", 0)
        _enum(event["state"], OPERATION, ep + ".state")
        _flags(event, ("return_observed", "acknowledged"), ep)
        if event["acknowledged"] and not event["return_observed"]:
            _bad(ep + ".acknowledged")
    if plan is not None and plan["events_used"] != len(journal["events"]):
        _bad(p + ".plan.events_used")
    if journal["close_acknowledged"] and not journal["close_return_observed"]:
        _bad(p + ".journal.close_acknowledged")
    if journal["tip"] is not None and (not journal["close_acknowledged"] or any(not row["acknowledged"] for row in journal["events"])):
        _bad(p + ".journal.tip")

    outputs = value["outputs"]
    _record(outputs, ("reservation", "publications", "journal_close", "total_reserved_bytes"), p + ".outputs")
    _callback(outputs["reservation"], 0, p + ".outputs.reservation", True)
    _callback(outputs["journal_close"], 0, p + ".outputs.journal_close", True)
    _record(outputs["publications"], KINDS, p + ".outputs.publications")
    for kind in KINDS:
        _callback(outputs["publications"][kind], 8192, p + ".outputs.publications." + kind)
    _int(outputs["total_reserved_bytes"], 524288, p + ".outputs.total_reserved_bytes")

    _list(value["stages"], len(STAGES), p + ".stages")
    seen = set()
    for i, stage in enumerate(value["stages"]):
        sp = p + ".stages[" + str(i) + "]"
        _record(stage, ("name", "state", "return_observed", "accepted", "verdict"), sp)
        _enum(stage["name"], STAGES, sp + ".name")
        if stage["name"] in seen:
            _bad(sp + ".name")
        seen.add(stage["name"])
        _enum(stage["state"], ("reserved", "entered_return_unknown", "return_observed", "accepted", "refused"), sp + ".state")
        _flags(stage, ("return_observed", "accepted"), sp)
        _nullable_enum(stage["verdict"], ("consistent", "negative"), sp + ".verdict")
    _list(value["gates"], len(GATES), p + ".gates")
    for i, gate in enumerate(value["gates"]):
        _enum(gate, GATES, p + ".gates[" + str(i) + "]")
        if gate != GATES[i]:
            _bad(p + ".gates[" + str(i) + "]")

    errors = value["errors"]
    _record(errors, ("primary", "secondary"), p + ".errors")
    if errors["primary"] is not None:
        _diagnostic(errors["primary"], p + ".errors.primary", diagnostic_identity_check)
    _list(errors["secondary"], None, p + ".errors.secondary")
    for i, diagnostic in enumerate(errors["secondary"]):
        _diagnostic(diagnostic, p + ".errors.secondary[" + str(i) + "]", diagnostic_identity_check)
    terminal = value["terminal"]
    terminal_keys = ("started", "candidate_acknowledged", "original_closures_complete", "cleanup_acknowledged",
                     "journal_closed", "receipt_acknowledged", "seal_acknowledged", "final_clock_passed", "pure_owner_ack", "result_issued")
    _record(terminal, terminal_keys, p + ".terminal")
    _flags(terminal, terminal_keys, p + ".terminal")
