"""Pure census-wire validation. Reported module paths are never filesystem inputs."""
import json
import re

STATUS = "module_census_observations_retained_not_ABI_qualification"
TOTAL_BYTES = 2097152
RESERVE_BYTES = 65536
ROW_BYTES = 65536
MAX_MODULES = 64
APIS = {
    "CreateToolhelp32Snapshot": 1,
    "Module32FirstW": 1,
    "Module32NextW": 64,
    "GetModuleFileNameW": 64,
    "CloseHandle": 1,  # Census snapshot only, not loader/output/parent handles.
    "GetSystemDirectoryW": 1,
}
SYSTEM_NAMES = (
    "ntdll.dll", "kernel32.dll", "kernelbase.dll", "ucrtbase.dll", "msvcp140.dll",
    "vcruntime140.dll", "vcruntime140_1.dll", "advapi32.dll", "psapi.dll", "sechost.dll",
    "rpcrt4.dll", "msvcrt.dll", "bcrypt.dll", "bcryptprimitives.dll", "cryptbase.dll", "cryptsp.dll",
)
CORE_NAMES = ("libomp.dll", "ggml-base.dll", "ggml.dll", "llama.dll")


class CensusValidationError(ValueError):
    pass


def need(value, message):
    if not value:
        raise CensusValidationError(message)


def integer(value, low=0, high=0xffffffff):
    return type(value) is int and low <= value <= high


def exact(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return set(a) == set(b) and all(exact(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(exact(x, y) for x, y in zip(a, b))
    return a == b


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "Duplicate census JSON key")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(CensusValidationError("Nonfinite census JSON")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CensusValidationError("Malformed census JSON") from error


def fields(row, event, keys):
    need(type(row) is dict and set(row) == {"event", *keys} and row["event"] == event,
         "Exact census event/field set required: " + event)


def units_of(text):
    need(type(text) is str and "\0" not in text, "Expected path must be a NUL-free string")
    raw = text.encode("utf-16-le", errors="surrogatepass")
    return tuple(int.from_bytes(raw[i:i+2], "little") for i in range(0, len(raw), 2))


def fold_units(units):
    # Deliberately no Unicode casefold, dot/short-name/prefix normalization, or filesystem API.
    return tuple(92 if u == 47 else u + 32 if 65 <= u <= 90 else u for u in units)


def split_units(units):
    folded = fold_units(units)
    last = max((i for i, u in enumerate(folded) if u == 92), default=-1)
    return folded[:last] if last >= 0 else (), folded[last+1:]


def validate_wide(record, *, prefix_cap, captured_cap):
    need(type(record) is dict and set(record) == {
        "utf16_units", "prefix_utf16_units", "truncated", "pair_cut_adjusted",
        "utf8_conversion", "utf8", "utf16_code_units_hex"}, "Exact Wide record required")
    total, count = record["utf16_units"], record["prefix_utf16_units"]
    need(integer(total, 0, captured_cap) and integer(count, 0, prefix_cap) and count <= total,
         "Wide captured/prefix length bounds")
    need(type(record["truncated"]) is type(record["pair_cut_adjusted"]) is bool,
         "Wide truncation flags must be booleans")
    need(record["truncated"] == (count < total), "Wide truncation/length mismatch")
    need(count == min(total, prefix_cap) - int(record["pair_cut_adjusted"]), "Wide prefix/pair-cut mismatch")
    need(not record["pair_cut_adjusted"] or total > prefix_cap, "Wide pair adjustment without clipping")
    encoded = record["utf16_code_units_hex"]
    need(type(encoded) is str and len(encoded) == 4*count and re.fullmatch("[0-9a-f]*", encoded) is not None,
         "Wide numeric UTF16 hex framing")
    units = tuple(int(encoded[i:i+4], 16) for i in range(0, len(encoded), 4))
    conversion = record["utf8_conversion"]
    need(conversion in ("returned", "failed") and type(conversion) is str, "Wide conversion outcome")
    if conversion == "returned":
        need(type(record["utf8"]) is str, "Wide successful conversion needs text")
        try:
            raw = b"".join(unit.to_bytes(2, "little") for unit in units)
            decoded = raw.decode("utf-16-le", errors="strict")
            record["utf8"].encode("utf-8", errors="strict")
        except UnicodeError as error:
            raise CensusValidationError("Wide returned text is not the same scalar sequence") from error
        need(decoded == record["utf8"], "Wide numeric UTF16/UTF8 mismatch")
    else:
        need(record["utf8"] is None, "Wide failed conversion must retain null text")
    return dict(units=units, complete=count == total and not record["truncated"] and not record["pair_cut_adjusted"],
                utf8_conversion=conversion, utf8=record["utf8"])


def validate_census_rows(rows, *, expected_pid, expected_executable, expected_runtime, raw_lines, attempt_bytes):
    """Validate a complete positive census, including unlisted metadata, without file I/O.

    A partial/error corpus is rejected as complete and must retain failed status.
    API counters cover census calls only; CloseHandle refers to the snapshot only.
    """
    need(integer(expected_pid, 1), "Expected owned PID must be a positive DWORD")
    expected_exe = fold_units(units_of(expected_executable))
    runtime = fold_units(units_of(expected_runtime))
    need(type(rows) is list and type(raw_lines) is list and 1 <= len(rows) == len(raw_lines) <= 333,
         "Census row count bound")
    need(integer(attempt_bytes, 1, 4096), "Attempt byte bound")
    need(all(type(raw) is bytes and raw.endswith(b"\n") and 0 < len(raw)-1 <= ROW_BYTES for raw in raw_lines),
         "Census row byte framing/cap")
    total_bytes = attempt_bytes + sum(map(len, raw_lines))
    need(total_bytes <= TOTAL_BYTES, "All-child structured artifact cap")
    need(attempt_bytes + len(raw_lines[-1]) <= RESERVE_BYTES, "Attempt/terminal reserve cap")
    before = attempt_bytes + sum(map(len, raw_lines[:-1]))
    need(before <= TOTAL_BYTES - RESERVE_BYTES, "Census data consumed terminal reserve")
    for row, raw in zip(rows, raw_lines):
        need(exact(row, strict_json(raw)), "Decoded census row is not bound to its wire bytes")

    position, call_id, last_ms = 0, 0, 0
    counters = {api: dict(reserved=0, returned=0) for api in APIS}
    metadata = []
    def take(event, keys):
        nonlocal position
        need(position < len(rows), "Missing census event: " + event)
        row = rows[position]; position += 1
        fields(row, event, keys)
        return row
    def pair(api, ordinal):
        nonlocal call_id, last_ms
        reserved = take("census_call_reserved", {"call_id", "api", "ordinal", "started_ms"})
        call_id += 1
        need(integer(reserved["call_id"], 1) and reserved["call_id"] == call_id and reserved["api"] == api,
             "Census call reservation sequence/API")
        need(exact(reserved["ordinal"], ordinal), "Census call reservation ordinal")
        need(integer(reserved["started_ms"], last_ms, 30000), "Census call start time")
        counters[api]["reserved"] += 1
        need(counters[api]["reserved"] <= APIS[api], "Census API reservation cap")
        result = take("census_call_returned", {
            "call_id", "api", "ordinal", "ended_ms", "ok", "error", "returned_count", "more_entries", "buffer_clipped"})
        need(integer(result["call_id"], 1) and result["call_id"] == call_id and result["api"] == api
             and exact(result["ordinal"], ordinal), "Census call return binding")
        need(integer(result["ended_ms"], reserved["started_ms"], 30000), "Census call return time")
        last_ms = result["ended_ms"]
        need(type(result["ok"]) is type(result["buffer_clipped"]) is bool, "Census call Boolean outcomes")
        need((result["ok"] and result["error"] is None)
             or (not result["ok"] and integer(result["error"])), "Census call error definition")
        if api in ("Module32FirstW", "Module32NextW"):
            need(type(result["more_entries"]) is bool and result["more_entries"] == result["ok"],
                 "Census enumeration Boolean result")
        else:
            need(result["more_entries"] is None, "Unexpected census enumeration field")
        if api in ("GetModuleFileNameW", "GetSystemDirectoryW"):
            need(integer(result["returned_count"]), "Census path raw return count")
        else:
            need(result["returned_count"] is None, "Unexpected census count field")
            need(result["buffer_clipped"] is False, "Non-buffer call clipping")
        counters[api]["returned"] += 1
        return result
    def successful(result):
        need(result["ok"] is True and result["error"] is None and result["buffer_clipped"] is False,
             "A failed/clipped census API cannot establish completeness")

    start = take("before_explicit_required_OpenMP_dependency_load", {"dependency_native_initialization_possible"})
    need(start["dependency_native_initialization_possible"] is True, "Missing initializer-effects disclosure")
    start = take("module_census_started", {
        "schema_version", "mode", "scope", "pid", "known_core4_load_stage_returned", "Api_constructed",
        "target_C_queries", "ABI_eligibility_established", "max_modules", "max_structured_bytes", "reserved_terminal_bytes"})
    need(exact(start, dict(event="module_census_started", schema_version=1, mode="--module-census",
         scope="post_core4_current_process_metadata_only", pid=expected_pid, known_core4_load_stage_returned=True,
         Api_constructed=False, target_C_queries=0, ABI_eligibility_established=False,
         max_modules=64, max_structured_bytes=TOTAL_BYTES, reserved_terminal_bytes=RESERVE_BYTES)),
         "Exact census-only start/PID/scope required")
    successful(pair("CreateToolhelp32Snapshot", None))
    first = pair("Module32FirstW", None); successful(first)
    need(first["more_entries"] is True, "No first module in a complete post-core census")
    ordinal = 1
    while True:
        need(ordinal <= MAX_MODULES, "65th module means partial corpus")
        query = pair("GetModuleFileNameW", ordinal); successful(query)
        n = query["returned_count"]
        need(1 <= n < 32768, "Census path query error/API clipping")
        row = take("module_metadata", {
            "ordinal", "snapshot_name", "snapshot_name_terminated", "path", "path_query_call_id",
            "path_full_utf16_units_known", "path_buffer_terminated", "path_contains_NUL"})
        need(integer(row["ordinal"], 1, 64) and row["ordinal"] == ordinal
             and integer(row["path_query_call_id"], 1) and row["path_query_call_id"] == call_id,
             "Census metadata ordinal/query binding")
        name = validate_wide(row["snapshot_name"], prefix_cap=256, captured_cap=256)
        path = validate_wide(row["path"], prefix_cap=2048, captured_cap=32768)
        need(name["complete"] and path["complete"] and len(name["units"]) < 256,
             "Clipped metadata cannot establish completeness")
        need(row["snapshot_name_terminated"] is True and row["path_buffer_terminated"] is True
             and row["path_contains_NUL"] is False and 0 not in name["units"] and 0 not in path["units"],
             "Census termination/NUL metadata")
        need(integer(row["path_full_utf16_units_known"], 1, 32767)
             and row["path_full_utf16_units_known"] == n == len(path["units"]), "Census full-path/count binding")
        parent, basename = split_units(path["units"])
        need(fold_units(name["units"]) == basename, "Snapshot/path basename disagreement is incomplete")
        metadata.append(dict(ordinal=ordinal, name=name, path=path, parent=parent, basename=basename, raw=row))
        more = pair("Module32NextW", ordinal)
        if more["ok"] is False:
            need(more["error"] == 18 and more["more_entries"] is False, "Enumeration did not end naturally")
            break
        successful(more)
        ordinal += 1
    count = len(metadata)
    end = take("module_census_enumeration_end", {"entries_recorded", "entries_returned_at_least", "natural_end", "termination_reason"})
    need(exact(end, dict(event="module_census_enumeration_end", entries_recorded=count,
                        entries_returned_at_least=count, natural_end=True, termination_reason="natural_end")),
         "Fabricated or partial enumeration completion")
    successful(pair("CloseHandle", None))  # Snapshot close only; no retry/fallback pair.
    system_query = pair("GetSystemDirectoryW", None); successful(system_query)
    need(1 <= system_query["returned_count"] < 32768, "System directory API clipping")
    classified = take("module_census_classification", {
        "system_directory", "rows", "required_report_counts", "all_required_once", "classification_is_eligibility"})
    system = validate_wide(classified["system_directory"], prefix_cap=2048, captured_cap=32768)
    need(system["complete"] and 0 not in system["units"]
         and len(system["units"]) == system_query["returned_count"], "System directory metadata incomplete")
    need(type(classified["rows"]) is list and len(classified["rows"]) == count,
         "Classification row count")
    runtime_names = {fold_units(units_of(name)): name for name in CORE_NAMES}
    system_names = {fold_units(units_of(name)) for name in SYSTEM_NAMES}
    required_counts = {name: 0 for name in ("self_executable", *CORE_NAMES)}
    categories = {}
    for observed, item in zip(classified["rows"], metadata):
        need(type(observed) is dict and set(observed) == {
            "ordinal", "category", "snapshot_basename_matches_path", "system_directory_matches", "system_basename_listed"},
            "Classification field set")
        need(integer(observed["ordinal"], 1, 64) and observed["ordinal"] == item["ordinal"],
             "Classification missing/duplicate/reordered ordinal")
        in_system = item["parent"] == fold_units(system["units"])
        listed = item["basename"] in system_names
        is_exe = fold_units(item["path"]["units"]) == expected_exe
        core = runtime_names.get(item["basename"]) if item["parent"] == runtime else None
        if is_exe:
            category = "self_executable"; required_counts["self_executable"] += 1
        elif core:
            category = "pinned_runtime_report"; required_counts[core] += 1
        elif in_system and listed:
            category = "listed_system_report"
        else:
            category = "unlisted_report"
        need(exact(observed, dict(ordinal=item["ordinal"], category=category,
             snapshot_basename_matches_path=True, system_directory_matches=in_system, system_basename_listed=listed)),
             "Classification must match raw metadata; it cannot grant eligibility")
        categories[category] = categories.get(category, 0) + 1
    need(all(value == 1 for value in required_counts.values()), "Complete census is missing/duplicating a required known report")
    need(exact(classified["required_report_counts"], required_counts)
         and classified["all_required_once"] is True and classified["classification_is_eligibility"] is False,
         "Required-report counts/observational scope mismatch")
    footer = take("module_census_complete", {
        "pid", "entries_recorded", "natural_end", "metadata_complete", "all_prior_rows_durable",
        "required_known_reports_complete", "classification_complete", "snapshot_close_returned", "Api_constructed",
        "target_C_queries", "ABI_eligibility_established", "counters", "structured_bytes_reserved_before_complete",
        "structured_bytes_written_known_before_complete"})
    expected_footer = dict(event="module_census_complete", pid=expected_pid, entries_recorded=count,
        natural_end=True, metadata_complete=True, all_prior_rows_durable=True, required_known_reports_complete=True,
        classification_complete=True, snapshot_close_returned=True, Api_constructed=False, target_C_queries=0,
        ABI_eligibility_established=False, counters=counters, structured_bytes_reserved_before_complete=before,
        structured_bytes_written_known_before_complete=before)
    need(exact(footer, expected_footer), "Census footer/counters/bytes/scope mismatch")
    need(position == len(rows), "Unexpected trailing census events")
    return dict(status=STATUS, entries_recorded=count, enumeration_complete=True, metadata_complete=True,
        publication_records_consistent=True, required_known_reports_complete=True, classification_complete=True,
        ABI_eligibility_established=False, explicit_target_C_calls=0, target_export_resolution=0,
        census_API_counters=counters, counter_scope="Census calls only; CloseHandle counts only the snapshot handle",
        child_structured_bytes=total_bytes, prefix_bytes_before_complete=before, category_counts=categories,
        raw_rows=rows, unknown_image_authenticity="not_verified", scientific_validation="not_established",
        module_inventory_scope="One declared current-child snapshot after core loads; reported metadata, not image authenticity, historical identity or future closure")
