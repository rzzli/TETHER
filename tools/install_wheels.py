"""Build both TETHER wheels from fresh staging trees and install the inspected bytes."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    # Bootstrap from the checkout before either distribution is installed.
    sys.path.insert(0, str(ROOT / "src"))

from tether_engine.serde import ContractError


def _version(source):
    with (source / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]["version"]


def _wheel_members(wheel, namespace, distribution, version):
    """Check exact member names before either package's content policy."""
    metadata_root = distribution + '-' + version + '.dist-info'
    with zipfile.ZipFile(wheel) as archive:
        names = [info.orig_filename for info in archive.infolist()]
        if len(names) != len(set(names)):
            raise ContractError('Duplicate wheel member')
        for name in names:
            parts = name.rstrip('/').split('/')
            if (not parts or any(part in ('', '.', '..') or ':' in part for part in parts)
                    or '\\' in name or '\x00' in name or parts[0] not in (namespace, metadata_root)
                    or len(parts) < 2):
                raise ContractError('Unexpected wheel namespace/member: '+name)
    required = {metadata_root+'/'+name for name in ('METADATA', 'WHEEL', 'RECORD')}
    if not required.issubset(names):
        raise ContractError('Packaged runtime metadata missing')
    return names, metadata_root


def validate_engine_wheel(wheel):
    """Reject research drivers, stale builds and incomplete compatibility imports."""
    __version__ = _version(ROOT)
    names, metadata_root = _wheel_members(wheel, 'tether_engine', 'tether_target_engine', __version__)
    compatibility = {'tether_engine/study/'+name for name in ('__init__.py', 'proofs.py', 'stable_read.py')}
    if any(name.startswith('tether_engine/study/') and name not in compatibility for name in names):
        raise ContractError('Historical study payload is outside the slim engine wheel')
    required = {'tether_engine/demo/v2/case.json', 'tether_engine/demo/case.json',
                'tether_engine/schemas/native-receipt-v2.json',
                'tether_engine/schemas/journal-envelope-v1.json',
                'tether_engine/schemas/generated-claim-response-v1.json',
                'tether_engine/schemas/generated-span-selection-v2.json',
                'tether_engine/schemas/portable-bundle-v1.json'} | compatibility
    if not required.issubset(names):
        raise ContractError('Packaged runtime/demo/compatibility imports missing')
    return {'members':len(names), 'namespace':'tether_engine', 'metadata_root':metadata_root}


def validate_wrapper_wheel(wheel):
    __version__ = _version(ROOT / "packages/tether")
    names, metadata_root = _wheel_members(wheel, 'tether', 'tether_target_agents', __version__)
    if any(name.startswith('tether/study/') for name in names):
        raise ContractError('Historical study launcher is outside the slim wrapper wheel')
    required = {'tether/'+name+'.py' for name in ('__init__', '__main__', '_cli', '_aliases',
                                                   '_presentation', '_catalog_binding', 'api')}
    required.add('tether/py.typed')
    if not required.issubset(names):
        raise ContractError('Packaged wrapper entry points missing')
    return {'members':len(names), 'namespace':'tether', 'metadata_root':metadata_root}


def _stage_distribution(source, staged):
    """Copy only declared build inputs, never a caller's reused build tree."""
    staged.mkdir()
    for name in ('pyproject.toml', 'LICENSE'):
        if (source/name).is_file():
            shutil.copyfile(source/name, staged/name)
    shutil.copytree(source/'src', staged/'src',
                    ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))


def _install_checked(output, scratch, python, *, offline):
    constraints = ROOT / "tools/build-constraints.txt"
    deliverables = {}
    requirements = []
    for name, source, validator in (
        ("engine", ROOT, validate_engine_wheel),
        ("wrapper", ROOT / "packages/tether", validate_wrapper_wheel),
    ):
        staged = scratch / name
        _stage_distribution(source, staged)
        subprocess.run(
            ["uv", "build", *(["--offline"] if offline else []),
             "--build-constraints", str(constraints), "--python", str(python),
             "--wheel", "--out-dir", str(output)], cwd=staged, check=True,
        )
        prefix = "tether_target_engine" if name == "engine" else "tether_target_agents"
        built = list(output.glob(prefix + "-*.whl"))
        if len(built) != 1:
            raise ContractError(f"Expected exactly one {name} wheel")
        wheel = built[0]
        inventory = validator(wheel)
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        deliverables[name] = {"wheel": wheel.name, "wheel_sha256": digest, "wheel_inventory": inventory}
        requirements.append(f"{wheel.as_uri()} --hash=sha256:{digest}")

    # Reinstall even when the environment already has an editable or older build
    # with the same distribution version. uv checks both exact local hashes.
    pins = scratch / "wheels.txt"
    pins.write_text("\n".join(requirements) + "\n", encoding="utf-8")
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python), "--offline", "--no-index",
         "--no-deps", "--reinstall", "--require-hashes", "-r", str(pins)], check=True,
    )
    for module in ("tether_engine", "tether"):
        run = scratch / (module + "-demo")
        command = [str(python), "-I", "-B", "-m", module]
        demo = json.loads(subprocess.check_output([*command, "demo", "--output", str(run)], cwd=scratch))
        subprocess.run([*command, "verify", "--run-dir", str(run)],
                       cwd=scratch, check=True, stdout=subprocess.DEVNULL)
        if module == "tether":
            subprocess.run(
                [str(python), "-I", "-B", "-c",
                 "import sys; from pathlib import Path; from tether.api import RunArtifacts, verify_run; "
                 "verify_run(RunArtifacts(Path(sys.argv[1]), *sys.argv[2:]), source_roots=())",
                 str(run), demo["receipt_sha256"], demo["engine_receipt_sha256"]],
                cwd=scratch, check=True,
            )
    diagnostic = subprocess.check_output(
        [str(python), "-I", "-B", "-c",
         'import json, tether, tether_engine; from importlib.metadata import version; '
         'from tether.api import run_offline, verify_run; '
         'print(json.dumps({name: {"version": version(dist), "import_path": module.__file__} '
         'for name, dist, module in (("engine", "tether-target-engine", tether_engine), '
         '("wrapper", "tether-target-agents", tether))}))'], cwd=scratch, text=True,
    )
    report = {
        **deliverables["engine"], "deliverables": deliverables,
        "installed_diagnostic": json.loads(diagnostic),
        "build_constraints_sha256": hashlib.sha256(constraints.read_bytes()).hexdigest(),
        "package_network_policy": "offline" if offline else "build_dependencies_only",
        "dependency_free_demo": "passed",
    }
    (output / "checked-wheels.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def installed_wheel_report(output):
    """Reconcile retained wheel hashes and namespace files with this test interpreter."""
    report = json.loads((output / "checked-wheels.json").read_text(encoding="utf-8"))
    for name, dist_name, namespace, validate in (
        ("engine", "tether-target-engine", "tether_engine", validate_engine_wheel),
        ("wrapper", "tether-target-agents", "tether", validate_wrapper_wheel),
    ):
        dist = importlib.metadata.distribution(dist_name)
        wheel = output / f"{dist_name.replace('-', '_')}-{dist.version}-py3-none-any.whl"
        item = report["deliverables"][name]
        if item["wheel"] != wheel.name or item["wheel_sha256"] != hashlib.sha256(wheel.read_bytes()).hexdigest():
            raise ContractError(f"Retained {name} wheel differs from install report")
        if validate(wheel) != item["wheel_inventory"]:
            raise ContractError(f"Retained {name} wheel inventory differs from install report")
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.namelist():
                if member.startswith(namespace + "/") and not member.endswith("/"):
                    if dist.locate_file(member).read_bytes() != archive.read(member):
                        raise ContractError(f"Installed file differs from checked wheel: {member}")
    return report


def package_check(directory):
    """Run the standalone validator's offline packaging gate in a fresh environment."""
    environment = directory / "wheel-environment"
    subprocess.run(["uv", "venv", "--offline", "--python", sys.executable, str(environment)], check=True)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    output = directory / "wheels"
    output.mkdir()
    return _install_checked(output.resolve(), directory.resolve(), python.absolute(), offline=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory for the installed wheels and their report")
    parser.add_argument("--offline", action="store_true", help="Use only cached build dependencies")
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix:
        parser.error("Run with the Python interpreter of the intended virtual environment")
    with tempfile.TemporaryDirectory(prefix="tether-wheels-") as temporary:
        scratch = Path(temporary).resolve()
        output = args.output.absolute() if args.output else scratch / "wheels"
        output.mkdir(parents=True, exist_ok=False)
        report = _install_checked(output, scratch, Path(sys.executable), offline=args.offline)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
