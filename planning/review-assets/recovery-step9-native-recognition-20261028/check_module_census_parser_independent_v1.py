"""Independent census false-completeness vectors, memory-only parser component."""
import ast
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "module_census_validation_v1.py"
REPORT = HERE / "SELF-MODULE-CENSUS-PARSER-INDEPENDENT-PROOF-v1.json"
SENTINEL = r"C:\NeverOpen\unlisted_sentinel.dll"
EXE = r"D:\Synthetic\census_probe.exe"
RUNTIME = r"D:\Synthetic\runtime"
SYSTEM = r"C:\Windows\System32"
PID = 4242
STATUS = "module_census_observations_retained_not_ABI_qualification"
CORES = ("libomp.dll", "ggml-base.dll", "ggml.dll", "llama.dll")
API_NAMES = ("CreateToolhelp32Snapshot", "Module32FirstW", "Module32NextW",
             "GetModuleFileNameW", "CloseHandle", "GetSystemDirectoryW")
DENIED, VECTORS, FILESYSTEM_ATTEMPTS = [], [], []


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=digest(raw))


def audit(event, args):
    if event in ("ctypes.dlopen", "subprocess.Popen", "os.system") or event.startswith("socket."):
        DENIED.append(event)
        raise AssertionError("Independent parser permits no native dispatch")


def wire(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def wide(text):
    raw = text.encode("utf-16-le", "surrogatepass")
    units = [int.from_bytes(raw[i:i+2], "little") for i in range(0, len(raw), 2)]
    return dict(utf16_units=len(units), prefix_utf16_units=len(units), truncated=False,
                pair_cut_adjusted=False, utf8_conversion="returned", utf8=text,
                utf16_code_units_hex="".join(format(unit, "04x") for unit in units))


def refresh(f):
    # Repair only raw-byte claims. Semantic rows/counts remain the test's input.
    footer = f["rows"][-1]
    before = f["attempt_bytes"] + sum(len(wire(row)) for row in f["rows"][:-1])
    footer["structured_bytes_reserved_before_complete"] = before
    footer["structured_bytes_written_known_before_complete"] = before
    f["raw_lines"] = [wire(row) for row in f["rows"]]
    return f


def fixture(count=6, *, remove=None, astral=False):
    paths = [EXE] + [RUNTIME + "\\" + name for name in CORES] + [SENTINEL]
    if astral:
        paths[-1] = r"C:\NeverOpen\tile_" + "😀" + ".dll"
    if remove == "self_executable":
        paths.remove(EXE)
    elif remove:
        paths.remove(RUNTIME + "\\" + remove)
    while len(paths) < count:
        paths.append(r"C:\NeverOpen\extra_" + str(len(paths)) + ".dll")
    # A missing required row is a repaired smaller corpus, not a simple bad count.
    if remove:
        paths = paths[:count-1]
    rows = [dict(event="before_explicit_required_OpenMP_dependency_load",
                 dependency_native_initialization_possible=True),
            dict(event="module_census_started", schema_version=1, mode="--module-census",
                 scope="post_core4_current_process_metadata_only", pid=PID,
                 known_core4_load_stage_returned=True, Api_constructed=False,
                 target_C_queries=0, ABI_eligibility_established=False, max_modules=64,
                 max_structured_bytes=2097152, reserved_terminal_bytes=65536)]
    counters = {name: dict(reserved=0, returned=0) for name in API_NAMES}
    clock = 0
    call_id = 0

    def pair(api, ordinal=None, *, ok=True, error=None, count=None, more=None):
        nonlocal clock, call_id
        call_id += 1
        counters[api]["reserved"] += 1
        clock += 1
        rows.append(dict(event="census_call_reserved", call_id=call_id, api=api,
                         ordinal=ordinal, started_ms=clock))
        counters[api]["returned"] += 1
        clock += 1
        rows.append(dict(event="census_call_returned", call_id=call_id, api=api,
                         ordinal=ordinal, ended_ms=clock, ok=ok, error=error,
                         returned_count=count, more_entries=more, buffer_clipped=False))
        return call_id

    pair("CreateToolhelp32Snapshot")
    pair("Module32FirstW", more=True)
    classifications = []
    for ordinal, path in enumerate(paths, 1):
        name = path.rsplit("\\", 1)[-1]
        query = pair("GetModuleFileNameW", ordinal, count=wide(path)["utf16_units"])
        rows.append(dict(event="module_metadata", ordinal=ordinal, snapshot_name=wide(name),
                         snapshot_name_terminated=True, path=wide(path), path_query_call_id=query,
                         path_full_utf16_units_known=wide(path)["utf16_units"],
                         path_buffer_terminated=True, path_contains_NUL=False))
        last = ordinal == len(paths)
        pair("Module32NextW", ordinal, ok=not last, error=18 if last else None, more=not last)
        category = "self_executable" if path == EXE else "pinned_runtime_report" if path.startswith(RUNTIME + "\\") else "unlisted_report"
        classifications.append(dict(ordinal=ordinal, category=category,
                                    snapshot_basename_matches_path=True,
                                    system_directory_matches=False, system_basename_listed=False))
    rows.append(dict(event="module_census_enumeration_end", entries_recorded=len(paths),
                     entries_returned_at_least=len(paths), natural_end=True, termination_reason="natural_end"))
    pair("CloseHandle")
    pair("GetSystemDirectoryW", count=wide(SYSTEM)["utf16_units"])
    # Deliberately claim all required reports even for repaired missing-row cases.
    rows.append(dict(event="module_census_classification", system_directory=wide(SYSTEM),
                     rows=classifications, required_report_counts={name: 1 for name in ("self_executable", *CORES)},
                     all_required_once=True, classification_is_eligibility=False))
    rows.append(dict(event="module_census_complete", pid=PID, entries_recorded=len(paths),
                     natural_end=True, metadata_complete=True, all_prior_rows_durable=True,
                     required_known_reports_complete=True, classification_complete=True,
                     snapshot_close_returned=True, Api_constructed=False, target_C_queries=0,
                     ABI_eligibility_established=False, counters=counters,
                     structured_bytes_reserved_before_complete=0,
                     structured_bytes_written_known_before_complete=0))
    attempt = wire(dict(schema_version=1, mode="--module-census", status="claimed_before_native_load", draft=True))
    return refresh(dict(rows=rows, attempt_bytes=len(attempt), expected_pid=PID,
                        expected_executable=EXE, expected_runtime=RUNTIME))


def parse(f):
    return NS["validate_census_rows"](f["rows"], expected_pid=f["expected_pid"],
        expected_executable=f["expected_executable"], expected_runtime=f["expected_runtime"],
        raw_lines=f["raw_lines"], attempt_bytes=f["attempt_bytes"])


class IndependentParser(unittest.TestCase):
    def rejected(self, label, f, message=None):
        refresh(f)
        with self.assertRaises(NS["CensusValidationError"]) as found:
            parse(f)
        if message:
            self.assertIn(message, str(found.exception))
        VECTORS.append(dict(case=label, outcome="rejected", reason=str(found.exception)))

    def test_complete_six_and_exact64_are_format_consistent(self):
        for count in (6, 64):
            value = parse(fixture(count))
            self.assertEqual(value["status"], STATUS)
            self.assertEqual(value["entries_recorded"], count)
            self.assertIs(value["ABI_eligibility_established"], False)
            VECTORS.append(dict(case="positive-" + str(count), outcome="census_only"))

    def test_fabricated_complete_after65th_query_clip_or_error(self):
        f = fixture(64)
        last = [row for row in f["rows"] if row.get("api") == "Module32NextW" and row["event"] == "census_call_returned"][-1]
        last.update(ok=True, error=None, more_entries=True)
        self.rejected("65th-return-with-complete-footer", f, "65th module")
        for clipped in (False, True):
            f = fixture()
            query = next(row for row in f["rows"] if row.get("api") == "GetModuleFileNameW" and row["event"] == "census_call_returned")
            query.update(ok=False, error=122 if clipped else 5, returned_count=32768 if clipped else 0, buffer_clipped=clipped)
            self.rejected("complete-after-query-" + ("clip" if clipped else "error"), f)
        f = fixture()
        last = [row for row in f["rows"] if row.get("api") == "Module32NextW" and row["event"] == "census_call_returned"][-1]
        last["error"] = 5
        self.rejected("complete-after-nonnatural-end", f, "naturally")

    def test_missing_required_rows_with_repaired_counts_and_bytes(self):
        for missing in ("self_executable", "ggml.dll"):
            f = fixture(remove=missing)
            self.rejected("repaired-missing-" + missing, f, "required known report")

    def test_utf16_cross_field_types_scalars_and_text(self):
        f = fixture(astral=True)
        self.assertEqual(parse(f)["status"], STATUS)
        VECTORS.append(dict(case="positive-astral-two-code-units", outcome="census_only"))
        for field, value in (("utf16_units", True), ("prefix_utf16_units", True),
                             ("utf8", "different_😀.dll"), ("utf8_conversion", "failed")):
            f = fixture(astral=True)
            row = [row for row in f["rows"] if row["event"] == "module_metadata"][-1]
            row["snapshot_name"][field] = value
            self.rejected("wide-mismatch-" + field, f)
        f = fixture(astral=True)
        row = [row for row in f["rows"] if row["event"] == "module_metadata"][-1]
        row["snapshot_name"]["utf16_code_units_hex"] = row["snapshot_name"]["utf16_code_units_hex"].upper()
        self.rejected("uppercase-numeric-hex", f)

    def test_unlisted_sentinel_is_diagnostic_only_without_filesystem(self):
        f = fixture()
        self.assertTrue(any(row.get("path", {}).get("utf8") == SENTINEL for row in f["rows"] if row["event"] == "module_metadata"))
        def forbidden(*args, **kwargs):
            FILESYSTEM_ATTEMPTS.append(repr(args[:1]))
            raise AssertionError("Pure parser attempted filesystem work")
        with patch("builtins.open", side_effect=forbidden), patch("io.open", side_effect=forbidden), \
             patch("os.open", side_effect=forbidden), patch("os.stat", side_effect=forbidden), \
             patch("os.lstat", side_effect=forbidden), patch.object(Path, "resolve", side_effect=forbidden):
            value = parse(f)
        self.assertEqual(FILESYSTEM_ATTEMPTS, [])
        self.assertEqual(value["status"], STATUS)
        self.assertEqual(value["category_counts"]["unlisted_report"], 1)
        self.assertIs(value["ABI_eligibility_established"], False)
        self.assertEqual(value["explicit_target_C_calls"], 0)
        VECTORS.append(dict(case="unlisted-sentinel-no-filesystem", outcome="census_only_no_eligibility"))

    def test_forged_eligibility_or_ABI_status_is_rejected(self):
        for field, value in (("ABI_eligibility_established", True), ("target_C_queries", 1),
                             ("status", "ABI_observations_retained_independent_qualification_pending")):
            f = fixture()
            f["rows"][-1][field] = value
            self.rejected("forged-" + field, f)
        f = fixture()
        f["rows"][1]["Api_constructed"] = True
        self.rejected("forged-Api-construction", f)


if __name__ == "__main__":
    if REPORT.exists():
        raise RuntimeError("Preserve first independent proof; no automatic repeat")
    sys.addaudithook(audit)
    RAW = SOURCE.read_bytes()
    TREE = ast.parse(RAW.decode("utf-8"))
    for node in TREE.body:
        if isinstance(node, ast.Import):
            assert {alias.name for alias in node.names} <= {"json", "re"}, "Unexpected parser import"
        assert not isinstance(node, ast.ImportFrom), "No external parser imports"
    NS = dict(__name__="independent_memory_only_census_validation")
    exec(compile(TREE, str(SOURCE) + "::<pure component only>", "exec"), NS)
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentParser))
    assert digest(SOURCE.read_bytes()) == digest(RAW), "Parser changed during independent check"
    proof = dict(schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                 status="passed" if result.wasSuccessful() else "failed", tests=result.testsRun,
                 failures=len(result.failures), errors=len(result.errors),
                 elapsed_seconds=time.monotonic()-started, source=pin(SOURCE), checker=pin(Path(__file__).resolve()),
                 vectors=VECTORS, forbidden_filesystem_attempts=FILESYSTEM_ATTEMPTS,
                 denied_real_operations=DENIED,
                 scope="Independent repaired-wire format/source consistency only; not adversarial-child, image authenticity or lifetime/global inventory proof",
                 activity=dict(actual_SDK_or_API_calls=0, children_or_compiler_or_DLL_loads=0,
                               unknown_image_or_GGUF_payload_reads=0))
    with REPORT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(proof, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(dict(proof=str(REPORT), sha256=pin(REPORT)["sha256"], vectors=len(VECTORS))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
