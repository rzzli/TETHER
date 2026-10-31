"""Read-only copied-Arrow/cache diagnosis; compile/decode only, never execute.

No Arrow import, environment repair, receipt rewrite or acceptance aggregation.
Writes only a new diagnosis JSON beside this operator helper.
"""

import base64
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import marshal
from pathlib import Path
import struct
import sys
import types


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "data/cache/recovery-step9-token-aware-wheel-20261026/environment-v2/Lib/site-packages"
TARGET = ROOT / "data/cache/recovery-step9-generation-wheel-20261028/ingestion-environment/Lib/site-packages"
REPORT = HERE / "OPTIONAL-ARROW-DIAGNOSIS.json"
EXPECTED_MODULES = {"ipc", "types", "util", "_generated_version", "__init__"}
FIELDS = (
    "co_argcount", "co_posonlyargcount", "co_kwonlyargcount", "co_nlocals",
    "co_stacksize", "co_flags", "co_code", "co_consts", "co_names",
    "co_varnames", "co_name", "co_qualname", "co_firstlineno", "co_linetable",
    "co_exceptiontable", "co_freevars", "co_cellvars", "co_lnotab",
)


def proof(path):
    path = Path(path)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(sha256=digest, bytes=path.stat().st_size)


def utc(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def stamp(path):
    stat = Path(path).stat()
    return dict(mtime_ns=stat.st_mtime_ns, mtime_utc=utc(stat.st_mtime),
                creation_time_utc_on_windows=utc(stat.st_ctime))


def constant(value):
    if isinstance(value, types.CodeType):
        return dict(type="code", fields={name: constant(getattr(value, name)) for name in FIELDS})
    if value is None or value is Ellipsis:
        return dict(type=type(value).__name__)
    if isinstance(value, bytes):
        return dict(type="bytes", hex=value.hex())
    if isinstance(value, str):
        return dict(type="str", value=value)
    if isinstance(value, bool):
        return dict(type="bool", value=value)
    if isinstance(value, int):
        return dict(type="int", value=str(value))
    if isinstance(value, float):
        return dict(type="float", value=value.hex())
    if isinstance(value, complex):
        return dict(type="complex", real=value.real.hex(), imag=value.imag.hex())
    if isinstance(value, (tuple, frozenset)):
        values = [constant(item) for item in value]
        if isinstance(value, frozenset):
            values.sort(key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=True))
        return dict(type=type(value).__name__, values=values)
    raise AssertionError("Unexpected code constant type: " + type(value).__name__)


def filenames(code):
    result = {code.co_filename}
    for item in code.co_consts:
        if isinstance(item, types.CodeType):
            result.update(filenames(item))
    return result


def field_hash(code):
    value = json.dumps(constant(code), sort_keys=True, ensure_ascii=True,
                       separators=(",", ":")).encode("ascii")
    return hashlib.sha256(value).hexdigest()


def header(contents, source):
    assert len(contents) > 16 and contents[:4] == importlib.util.MAGIC_NUMBER
    flags, seconds, size = struct.unpack("<III", contents[4:16])
    assert flags == 0  # All five observed files use timestamp-based CPython caches.
    stat = source.stat()
    return dict(magic_hex=contents[:4].hex(), flags=flags, source_timestamp_seconds=seconds,
                source_timestamp_utc=utc(seconds), source_bytes=size,
                timestamp_matches_corresponding_source=seconds == int(stat.st_mtime) & 0xFFFFFFFF,
                size_matches_corresponding_source=size == stat.st_size & 0xFFFFFFFF)


def main():
    assert not REPORT.exists()
    wheel_report_path = HERE / "WHEEL-ENVIRONMENTS.json"
    wheel_report = json.loads(wheel_report_path.read_text(encoding="utf-8"))
    before = {row["relative_path"]: row for row in wheel_report["copied_existing_arrow_files"]}
    assert len(before) == 760
    file_rows, mismatches = [], []
    for relative, expected in before.items():
        source, target = SOURCE / relative, TARGET / relative
        assert source.exists() and target.exists()
        original, current = proof(source), proof(target)
        assert original == {key: expected[key] for key in ("sha256", "bytes")}
        changed = current != original
        row = dict(relative_path=relative, copy_time=original, current=current,
                   source_still_matches_copy_pin=True, changed=changed)
        file_rows.append(row)
        if changed:
            mismatches.append(row)
    assert len(mismatches) == 5
    assert {Path(row["relative_path"]).name.split(".cpython-")[0] for row in mismatches} == EXPECTED_MODULES
    assert all(row["relative_path"].startswith("pyarrow/__pycache__/")
               and row["relative_path"].endswith(".cpython-311.pyc") for row in mismatches)
    expected_files = set(before)
    actual_files = set()
    for folder in ("pyarrow", "pyarrow.libs", "pyarrow-21.0.0.dist-info"):
        actual_files.update(path.relative_to(TARGET).as_posix()
                            for path in (TARGET / folder).rglob("*") if path.is_file())
    assert actual_files == expected_files
    bytecode = []
    for row in mismatches:
        relative = row["relative_path"]
        module = Path(relative).name.split(".cpython-")[0]
        source_relative = f"pyarrow/{module}.py"
        old_source, new_source = SOURCE / source_relative, TARGET / source_relative
        assert proof(old_source) == proof(new_source)
        original = (SOURCE / relative).read_bytes()
        current = (TARGET / relative).read_bytes()
        old_code, new_code = marshal.loads(original[16:]), marshal.loads(current[16:])
        assert isinstance(old_code, types.CodeType) and isinstance(new_code, types.CodeType)
        assert filenames(old_code) == {str(old_source)} and filenames(new_code) == {str(new_source)}
        source_bytes = new_source.read_bytes()
        # This creates code objects without executing any source or importing Arrow.
        old_compiled = compile(source_bytes, old_code.co_filename, "exec", dont_inherit=True, optimize=0)
        new_compiled = compile(source_bytes, new_code.co_filename, "exec", dont_inherit=True, optimize=0)
        assert marshal.dumps(old_compiled) == original[16:]
        assert marshal.dumps(new_compiled) == current[16:]
        assert field_hash(old_code) == field_hash(new_code) == field_hash(old_compiled) == field_hash(new_compiled)
        old_header, new_header = header(original, old_source), header(current, new_source)
        assert old_header["timestamp_matches_corresponding_source"] and old_header["size_matches_corresponding_source"]
        assert new_header["timestamp_matches_corresponding_source"] and new_header["size_matches_corresponding_source"]
        copied_header_valid_for_new_source = old_header["source_timestamp_seconds"] == int(new_source.stat().st_mtime) & 0xFFFFFFFF
        assert copied_header_valid_for_new_source is False
        bytecode.append(dict(
            module=module, cache_relative_path=relative, original_cache=row["copy_time"], current_cache=row["current"],
            source_relative_path=source_relative, source=proof(new_source), source_unchanged=True,
            original_compiler_filename=old_code.co_filename, current_compiler_filename=new_code.co_filename,
            compiler_filename_length_delta=len(new_code.co_filename)-len(old_code.co_filename),
            serialized_file_size_delta=len(current)-len(original), original_header=old_header, current_header=new_header,
            copied_timestamp_cache_invalid_for_new_source=copied_header_valid_for_new_source is False,
            current_marshaled_payload_exactly_matches_source_compile=True,
            original_marshaled_payload_exactly_matches_source_compile=True,
            all_recursive_code_fields_except_filename_match=True, code_fields_compared=FIELDS,
            recursive_code_fields_sha256=field_hash(new_code), current_cache_times=stamp(TARGET / relative),
            original_source_times=stamp(old_source), current_source_times=stamp(new_source),
        ))
    record_relative = "pyarrow-21.0.0.dist-info/RECORD"
    assert proof(SOURCE / record_relative) == proof(TARGET / record_relative)
    distribution_rows = list(csv.reader((TARGET / record_relative).read_text(encoding="utf-8").splitlines()))
    hashed_rows, unhashed_rows, outside_scope = 0, [], []
    record_by_path = {}
    for relative, digest, size in distribution_rows:
        record_by_path[relative] = dict(digest=digest or None, size=size or None)
        path = (TARGET / relative).resolve()
        if not path.is_relative_to(TARGET.resolve()) or relative not in expected_files:
            outside_scope.append(relative)
            continue
        if not digest:
            unhashed_rows.append(relative)
            continue
        algorithm, encoded = digest.split("=", 1)
        assert algorithm == "sha256"
        actual = proof(path)
        assert base64.urlsafe_b64encode(bytes.fromhex(actual["sha256"])).rstrip(b"=").decode("ascii") == encoded
        assert not size or actual["bytes"] == int(size)
        hashed_rows += 1
    assert not outside_scope
    for row in bytecode:
        row["cache_record_entry"] = record_by_path.get(row["cache_relative_path"])
        row["source_record_entry"] = record_by_path.get(row["source_relative_path"])
        assert row["source_record_entry"] and row["source_record_entry"]["digest"]
        assert row["cache_record_entry"] is None or row["cache_record_entry"]["digest"] is None
    build_helper = HERE / "build_installed.py"
    build_text = build_helper.read_text(encoding="utf-8")
    assert "shutil.copyfileobj(src,dst)" in build_text
    assert "copied.append" in build_text and "import pyarrow" in build_text
    assert build_text.index("copied.append") < build_text.index("import pyarrow") < build_text.index("report=dict")
    last_command = wheel_report["commands"][-1]
    assert last_command["exit_code"] == 0 and last_command["argv"][1:3] == ["-I", "-c"]
    assert "import pyarrow" in last_command["argv"][-1] and "-B" not in last_command["argv"]
    # Recheck all 760 after inspection/compilation; nothing in this diagnosis writes them.
    for row in file_rows:
        assert proof(TARGET / row["relative_path"]) == row["current"]
        assert proof(SOURCE / row["relative_path"]) == row["copy_time"]
    report = dict(
        schema_version=1, status="verified_five_source_equivalent_recompiled_caches_not_760_byte_identity",
        verified_at_utc=datetime.now(timezone.utc).isoformat(), helper_sha256=proof(__file__)["sha256"],
        source_site=str(SOURCE), target_site=str(TARGET), copy_manifest=proof(wheel_report_path),
        copied_files_checked=760, byte_identical_to_copy_pins=755, changed_files=5,
        missing_files=[], unlisted_files=[], original_source_files_still_match_copy_pins=760,
        all_files=file_rows, bytecode_derivations=bytecode,
        distribution_record=dict(file=record_relative, identity=proof(TARGET / record_relative),
            rows=len(distribution_rows), cryptographic_rows_verified=hashed_rows,
            unhashed_rows=unhashed_rows, outside_copied_scope=outside_scope),
        build_sequence=dict(helper=str(build_helper), identity=proof(build_helper),
            copy_method="exclusive byte copy; no source mtime preservation",
            digest_capture="original bytes recorded before verification import",
            subsequent_command=last_command, bytecode_writing_not_disabled_by_command=True,
            import_command_log=proof(Path(wheel_report["wheel"]).parents[1]/"command-06.log"),
            manifest_times=stamp(wheel_report_path),
            interpretation="Timestamp cache invalidation and filename rebasing exactly explain all five changes; timeline and explicit import are consistent with that build sequence.",
            process_write_attribution="Not independently OS-attested; no claim that file timestamps alone identify the writer."),
        compiler=dict(version=sys.version, cache_tag=sys.implementation.cache_tag,
            magic_hex=importlib.util.MAGIC_NUMBER.hex(), optimize=0, dont_inherit=True,
            source_compile_operations=10, resulting_code_objects_executed=0),
        policy_decision="none; acceptance remains pending explicit prospective root amendment",
        runtime_or_optional_environment_files_modified=False, receipts_modified=False,
        package_imports=0, native_target_calls=0, model_calls=0, network_calls=0,
        limitations=["Code-object/source equality is not a native-extension scientific or general ABI qualification",
                     "The five copy-time cache hashes differ; never claim all760 byte-identical or blanket-ignore pyc files"],
    )
    with REPORT.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    print(json.dumps(dict(status=report["status"], files=760, unchanged=755, changed=5,
                          exact_compiled_payload_matches=5, report=str(REPORT))))


if __name__ == "__main__":
    main()
