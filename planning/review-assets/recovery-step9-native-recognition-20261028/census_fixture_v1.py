"""Own-authored data fixtures only: no filesystem, SDK, executable or module reads."""
import copy
import json
import ntpath

APIS = ("CreateToolhelp32Snapshot", "Module32FirstW", "Module32NextW", "GetModuleFileNameW", "CloseHandle", "GetSystemDirectoryW")
CORE = ("libomp.dll", "ggml-base.dll", "ggml.dll", "llama.dll")
SYSTEM = ("ntdll.dll", "kernel32.dll", "kernelbase.dll", "ucrtbase.dll", "msvcp140.dll", "vcruntime140.dll",
          "vcruntime140_1.dll", "advapi32.dll", "psapi.dll", "sechost.dll", "rpcrt4.dll", "msvcrt.dll",
          "bcrypt.dll", "bcryptprimitives.dll", "cryptbase.dll", "cryptsp.dll")


def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()+b"\n"


def wide(text, cap=2048, *, conversion_failed=False):
    raw = text.encode("utf-16-le", errors="surrogatepass")
    units = [int.from_bytes(raw[i:i+2], "little") for i in range(0, len(raw), 2)]
    count = min(len(units), cap)
    adjusted = bool(count and count < len(units) and 0xd800 <= units[count-1] <= 0xdbff and 0xdc00 <= units[count] <= 0xdfff)
    if adjusted:
        count -= 1
    prefix = b"".join(unit.to_bytes(2, "little") for unit in units[:count])
    try:
        rendered = prefix.decode("utf-16-le", errors="strict")
        if conversion_failed:
            rendered = None
    except UnicodeError:
        rendered = None
    return dict(utf16_units=len(units), prefix_utf16_units=count, truncated=count < len(units), pair_cut_adjusted=adjusted,
                utf8_conversion="failed" if rendered is None else "returned", utf8=rendered,
                utf16_code_units_hex="".join(f"{unit:04x}" for unit in units[:count]))


def reframe(fixture, *, repair_prefix_bytes=True):
    rows = fixture["rows"]
    prefix = fixture["attempt_bytes"] + sum(len(encoded(row)) for row in rows[:-1])
    if repair_prefix_bytes and rows[-1].get("event") == "module_census_complete":
        rows[-1]["structured_bytes_reserved_before_complete"] = prefix
        rows[-1]["structured_bytes_written_known_before_complete"] = prefix
    fixture["raw_lines"] = [encoded(row) for row in rows]
    return fixture


def make_census_fixture(*, pid=20, executable=r"D:\SyntheticCensus\own.exe", runtime=r"D:\SyntheticRuntime",
                        unknown_paths=(r"C:\NeverOpen\unlisted_sentinel.dll",), count=None):
    paths = [executable, *(runtime+"\\"+name for name in CORE), *unknown_paths]
    if count is not None:
        while len(paths) < count:
            paths.append(r"C:\NeverOpen\extra_" + str(len(paths)) + ".dll")
        paths = paths[:count]
    attempt = dict(schema_version=1, mode="--module-census", status="claimed_before_native_load", draft=True)
    rows = [dict(event="before_explicit_required_OpenMP_dependency_load", dependency_native_initialization_possible=True),
            dict(event="module_census_started", schema_version=1, mode="--module-census",
                 scope="post_core4_current_process_metadata_only", pid=pid, known_core4_load_stage_returned=True,
                 Api_constructed=False, target_C_queries=0, ABI_eligibility_established=False,
                 max_modules=64, max_structured_bytes=2097152, reserved_terminal_bytes=65536)]
    counters = {api: dict(reserved=0, returned=0) for api in APIS}
    call_id = 0
    def pair(api, ordinal=None, *, ok=True, error=None, returned_count=None, more_entries=None, buffer_clipped=False):
        nonlocal call_id
        call_id += 1; counters[api]["reserved"] += 1; counters[api]["returned"] += 1
        rows.append(dict(event="census_call_reserved", call_id=call_id, api=api, ordinal=ordinal, started_ms=call_id))
        rows.append(dict(event="census_call_returned", call_id=call_id, api=api, ordinal=ordinal, ended_ms=call_id,
                         ok=ok, error=error, returned_count=returned_count, more_entries=more_entries, buffer_clipped=buffer_clipped))
        return call_id
    pair("CreateToolhelp32Snapshot")
    pair("Module32FirstW", more_entries=True)
    for i, path in enumerate(paths, 1):
        path_wide = wide(path)
        query_id = pair("GetModuleFileNameW", i, returned_count=path_wide["utf16_units"])
        rows.append(dict(event="module_metadata", ordinal=i, snapshot_name=wide(ntpath.basename(path), 256),
                         snapshot_name_terminated=True, path=path_wide, path_query_call_id=query_id,
                         path_full_utf16_units_known=path_wide["utf16_units"], path_buffer_terminated=True, path_contains_NUL=False))
        pair("Module32NextW", i, ok=i < len(paths), error=None if i < len(paths) else 18, more_entries=i < len(paths))
    rows.append(dict(event="module_census_enumeration_end", entries_recorded=len(paths),
                     entries_returned_at_least=len(paths), natural_end=True, termination_reason="natural_end"))
    pair("CloseHandle")
    system_directory = r"C:\Windows\System32"
    pair("GetSystemDirectoryW", returned_count=wide(system_directory)["utf16_units"])
    descriptions = []
    counts = {name: 0 for name in ("self_executable", *CORE)}
    def folded(text):
        return text.replace("/", "\\").translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))
    for i, path in enumerate(paths, 1):
        name = ntpath.basename(path)
        directory = path[:max(path.rfind("\\"), path.rfind("/"))]
        in_system = folded(directory) == folded(system_directory)
        listed = folded(name) in SYSTEM
        if folded(path) == folded(executable):
            category = "self_executable"; counts["self_executable"] += 1
        elif folded(directory) == folded(runtime) and folded(name) in CORE:
            category = "pinned_runtime_report"; counts[folded(name)] += 1
        else:
            category = "listed_system_report" if in_system and listed else "unlisted_report"
        descriptions.append(dict(ordinal=i, category=category, snapshot_basename_matches_path=True,
                                 system_directory_matches=in_system, system_basename_listed=listed))
    rows.append(dict(event="module_census_classification", system_directory=wide(system_directory), rows=descriptions,
                     required_report_counts=counts, all_required_once=all(n == 1 for n in counts.values()), classification_is_eligibility=False))
    rows.append(dict(event="module_census_complete", pid=pid, entries_recorded=len(paths), natural_end=True,
        metadata_complete=True, all_prior_rows_durable=True, required_known_reports_complete=True, classification_complete=True,
        snapshot_close_returned=True, Api_constructed=False, target_C_queries=0, ABI_eligibility_established=False,
        counters=copy.deepcopy(counters), structured_bytes_reserved_before_complete=0,
        structured_bytes_written_known_before_complete=0))
    raw_attempt = encoded(attempt)
    result = dict(rows=rows, raw_lines=[], attempt=attempt, attempt_raw=raw_attempt, attempt_bytes=len(raw_attempt),
                  expected_pid=pid, expected_executable=executable, expected_runtime=runtime)
    return reframe(result)
