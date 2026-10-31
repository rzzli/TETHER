"""PREPARED ONLY: assemble a new offline tool environment after owner approval.

Standard-library venv creation has no pip/ensurepip/network and no child dispatch.
Only the six RECORD-qualified package file lists are copied; nothing is imported.
Existing cache roots, project .venv and accepted wheel environments are read-only.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import sys
import venv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
QUALIFICATION = HERE / "CACHED-REFERENCE-QUALIFICATION.json"
QUALIFICATION_SHA256 = "401047cbf5b240867192a0d8acc1324b98ecb68837b6f4fca8f6b87dcb513ea4"
OUTPUT = ROOT / "data/cache/r09-jsonschema-reference-environment-20261028"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(contents):
    return hashlib.sha256(contents).hexdigest()


def plain(path):
    info = path.lstat()
    require(not path.is_symlink() and not (getattr(info, "st_file_attributes", 0) & 0x400), f"Reparse path: {path}")


def main():
    require(len(sys.argv) == 1 and sys.flags.isolated and sys.version_info[:2] == (3, 11)
            and struct.calcsize("P") == 8, "Requires Python -I, CPython3.11x64, no arguments")
    require(not OUTPUT.exists(), "Environment attempt already exists; preserve it and do not restart")
    raw = QUALIFICATION.read_bytes()
    require(sha(raw) == QUALIFICATION_SHA256, "Qualification report changed")
    qualified = json.loads(raw)
    require(qualified["status"] == "record_verified_cached_closure_source_inspection_only"
            and qualified["selected_files"] == 139 and qualified["selected_bytes"] == 1640116, "Wrong qualified closure")
    OUTPUT.mkdir(parents=True, exist_ok=False)
    manifest = dict(schema_version=1, status="failed_or_incomplete", source_qualification_sha256=QUALIFICATION_SHA256,
                    helper_sha256=sha(Path(__file__).read_bytes()), selected=[], copied_files=0, copied_bytes=0,
                    environment=str(OUTPUT / "environment"), package_imports=0, network_calls=0, child_dispatches=0,
                    native_target_calls=0, model_calls=0, restart_allowed=False)
    try:
        environment = OUTPUT / "environment"
        venv.EnvBuilder(with_pip=False, symlinks=False, system_site_packages=False, clear=False).create(environment)
        site = environment / "Lib/site-packages"
        require(site.is_dir(), "Expected Windows venv site-packages")
        for package in qualified["selected"]:
            source = Path(package["root"])
            plain(source)
            copied = {}
            for relative, expected in sorted(package["files"].items()):
                posix = PurePosixPath(relative)
                require(not posix.is_absolute() and "\\" not in relative and ":" not in relative
                        and all(part not in ("", ".", "..") for part in relative.split("/")), "Unsafe package path")
                require(posix.suffix.lower() not in (".pth", ".pyc"), "Executable path/cache bytecode prohibited")
                original = source.joinpath(*posix.parts)
                current = original
                while current != source:
                    plain(current)
                    current = current.parent
                contents = original.read_bytes()
                require(len(contents) == expected["bytes"] and sha(contents) == expected["sha256"], f"Changed source: {relative}")
                destination = site.joinpath(*posix.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as stream:
                    stream.write(contents)
                require(sha(destination.read_bytes()) == expected["sha256"], f"Copy failed: {relative}")
                copied[relative] = expected
                manifest["copied_files"] += 1
                manifest["copied_bytes"] += len(contents)
            manifest["selected"].append(dict(name=package["name"], version=package["version"], files=copied,
                                            source_root=package["root"], record_sha256=package["record_sha256"]))
        require(manifest["copied_files"] == 139 and manifest["copied_bytes"] == 1640116, "Incomplete copy")
        configuration = (environment / "pyvenv.cfg").read_bytes()
        require(b"include-system-site-packages = false" in configuration, "Venv site isolation disabled")
        require(not list(site.rglob("*.pth")) and not list(site.rglob("*.pyc")), "Unexpected executable startup/bytecode files")
        manifest.update(status="offline_reference_environment_materialized_not_import_qualified",
                        python=str(environment / "Scripts/python.exe"),
                        python_sha256=sha((environment / "Scripts/python.exe").read_bytes()),
                        pyvenv_configuration_sha256=sha(configuration), pip_installed=False,
                        runtime_import_abi_qualification="not_attempted", schema_validation_cases=0)
    except BaseException as error:
        manifest["failure"] = dict(error_class=type(error).__name__, message=str(error))
    with (OUTPUT / "ENVIRONMENT-RECEIPT.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: manifest[key] for key in ("status", "copied_files", "copied_bytes")}))
    return 0 if manifest["status"].startswith("offline_reference_environment_materialized_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
