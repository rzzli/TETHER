"""Read-only RECORD/source qualification; imports only Python's standard library.

Does not import cached packages, create an environment, copy packages, validate
corpus data or run any native target/model. Writes one new qualification report.
"""
import base64
import csv
from email.parser import Parser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import sys

HERE = Path(__file__).resolve().parent
CACHE = Path("C:/Users/zzric/AppData/Local/uv/cache/archive-v0")
REPORT = HERE / "CACHED-REFERENCE-QUALIFICATION.json"
SELECTED = {
    "jsonschema": ("4.26.0", "k5zMh1I94cktfILjawn79", "KEEj4yBqmFUdAmqM2Kw3a"),
    "referencing": ("0.37.0", "_otTDk1tF35GuPrzecDsg", "EIAouAl3HnAKkclR8TYWC"),
    "jsonschema-specifications": ("2025.9.1", "0v5dYOFfXmuCH_TybYlnX", "yPekydzNH2PkvwOYdh7ju"),
    "attrs": ("26.1.0", "_Skmrp7wYgOObbfQ3NkWK", "YLb4Sz4MkXLfWQo6t17IG"),
    "rpds-py": ("2026.6.3", "UmRZ5clbAUczk8DJ9HlAJ", None),
    "typing-extensions": ("4.15.0", "GG_sEg51npeKXwQxbYrep", None),
}
MAX_FILES_PER_ROOT = 2000
MAX_BYTES_PER_ROOT = 32 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(contents):
    return hashlib.sha256(contents).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def plain(path):
    info = path.lstat()
    require(not path.is_symlink() and not (getattr(info, "st_file_attributes", 0) & 0x400), f"Reparse point: {path}")
    require(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode), f"Nonregular path: {path}")


def inventory(root):
    plain(CACHE)
    plain(root)
    files, ignored, count, size = {}, [], 0, 0
    for current, directories, names in os.walk(root, followlinks=False):
        for name in directories:
            plain(Path(current) / name)
        for name in names:
            path = Path(current) / name
            plain(path)
            relative = path.relative_to(root).as_posix()
            require(path.suffix.lower() != ".pth", f"Executable .pth prohibited: {path}")
            if path.suffix.lower() == ".pyc":
                ignored.append(relative)
                continue
            count += 1
            size += path.stat().st_size
            require(count <= MAX_FILES_PER_ROOT and size <= MAX_BYTES_PER_ROOT, "Distribution inspection cap exceeded")
            contents = path.read_bytes()
            files[relative] = dict(sha256=digest(contents), bytes=len(contents))
    return files, ignored


def qualify(name, version, archive):
    root = CACHE / archive
    files, ignored = inventory(root)
    metadata_paths = [key for key in files if key.endswith(".dist-info/METADATA")]
    require(len(metadata_paths) == 1, f"Ambiguous distribution: {archive}")
    metadata_path = metadata_paths[0]
    dist = metadata_path.rsplit("/", 1)[0]
    metadata = Parser().parsestr((root / metadata_path).read_text(encoding="utf-8"))
    normalize = lambda value: value.lower().replace("_", "-")
    require(normalize(metadata["Name"]) == name and metadata["Version"] == version, f"Wrong metadata: {archive}")
    wheel = Parser().parsestr((root / dist / "WHEEL").read_text(encoding="utf-8"))
    tags = wheel.get_all("Tag", [])
    require(tags == (["cp311-cp311-win_amd64"] if name == "rpds-py" else ["py3-none-any"]), f"Incompatible WHEEL tag: {archive}")
    record_path = dist + "/RECORD"
    record = (root / record_path).read_bytes()
    require(len(record) <= 1024 * 1024, "RECORD byte cap exceeded")
    seen, wheel_hashed, total = set(), 0, 0
    for row in csv.reader(io.StringIO(record.decode("utf-8"), newline="")):
        require(len(row) == 3, f"Invalid RECORD row: {archive}")
        relative, signature, declared_size = row
        posix = PurePosixPath(relative)
        require(relative and not posix.is_absolute() and "\\" not in relative and ":" not in relative
                and all(part not in ("", ".", "..") for part in relative.split("/")), f"Unsafe RECORD path: {relative}")
        require(relative not in seen, f"Duplicate RECORD path: {relative}")
        seen.add(relative)
        if relative.endswith(".pyc"):
            continue
        require(relative in files, f"Missing RECORD file: {relative}")
        if relative == record_path:
            require(signature == declared_size == "", "RECORD self-entry must be unhashed")
            continue
        require(signature.startswith("sha256=") and declared_size.isdigit(), f"Unhashed selected file: {relative}")
        encoded = signature.split("=", 1)[1]
        expected = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).hex()
        require(len(expected) == 64 and files[relative]["sha256"] == expected, f"RECORD digest mismatch: {relative}")
        require(files[relative]["bytes"] == int(declared_size), f"RECORD size mismatch: {relative}")
        wheel_hashed += 1
        total += files[relative]["bytes"]
    require(set(files) == {value for value in seen if not value.endswith(".pyc")}, f"Unrecorded non-PYC files: {archive}")
    return dict(name=name, version=version, root=str(root), archive=archive, requires_python=metadata.get("Requires-Python"),
                requires_dist=metadata.get_all("Requires-Dist", []), wheel_tags=tags, metadata_path=metadata_path,
                metadata_sha256=files[metadata_path]["sha256"], wheel_sha256=files[dist + "/WHEEL"]["sha256"],
                record_path=record_path, record_sha256=digest(record), wheel_hashed_files=wheel_hashed,
                selected_files=len(files), selected_bytes=sum(item["bytes"] for item in files.values()),
                ignored_pyc=ignored, files=files, file_manifest_sha256=digest(canonical(files)),
                pth_files=0, reparse_points=0, unrecorded_non_pyc_files=0)


def main():
    require(sys.flags.isolated and sys.version_info[:2] == (3, 11) and struct.calcsize("P") == 8,
            "Qualification host must be isolated CPython 3.11 x64")
    require(not REPORT.exists(), "Qualification report exists; no replacement")
    result = dict(schema_version=1, status="failed", execution_authorized=False,
                  cache_read_only=True, package_imports=0, package_copies=0, environments_created=0,
                  schema_validation_cases=0, native_target_calls=0, model_calls=0,
                  host=dict(executable=sys.executable, version=sys.version, pointer_bytes=struct.calcsize("P")),
                  selected=[], twin_comparisons=[])
    try:
        for name, (version, selected, twin) in SELECTED.items():
            row = qualify(name, version, selected)
            result["selected"].append(row)
            if twin:
                other = qualify(name, version, twin)
                require(row["files"] == other["files"], f"Cached twins differ outside PYC: {name}")
                result["twin_comparisons"].append(dict(name=name, selected_root=row["root"], other_root=other["root"],
                    identical_excluding_pyc=True, file_manifest_sha256=row["file_manifest_sha256"]))
        result.update(status="record_verified_cached_closure_source_inspection_only",
                      selected_files=sum(row["selected_files"] for row in result["selected"]),
                      selected_bytes=sum(row["selected_bytes"] for row in result["selected"]),
                      runtime_import_abi_qualification="not_attempted",
                      incompatible_rpds_excluded=dict(archive="mDvB1JoDsxQY1Dnf9f9tP", version="2026.5.1", tag="cp314-cp314-win_amd64"))
    except BaseException as error:
        result["failure"] = dict(error_class=type(error).__name__, message=str(error))
    with REPORT.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: value for key, value in result.items() if key in ("status", "selected_files", "selected_bytes", "failure")}))
    return 0 if result["status"].startswith("record_verified_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
