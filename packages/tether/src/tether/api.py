"""Typed offline entry points over the existing supervised artifact-policy path.

No function grants source access from serialized paths. Callers supply roots and
retain returned hashes independently. Failed runs keep their existing journals;
this interface never retries a dispatch or overwrites a result.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import cast

from . import _presentation
from ._catalog_binding import PolicyRequest
from ._process import ProcessLimits
from tether_engine import bundle as _bundle
from tether_engine.serde import ContractError


@dataclass(frozen=True)
class PolicyInputs:
    case: Path
    snapshot: Path
    catalog: Path
    policy: Path
    roots: Path
    use_id: str
    frame_sha256: str


@dataclass(frozen=True)
class RunArtifacts:
    directory: Path
    receipt_sha256: str
    engine_receipt_sha256: str

    @property
    def dossier(self) -> Path:
        return self.directory / "dossier.md"

    @property
    def native(self) -> Path:
        return self.directory / "engine"


@dataclass(frozen=True)
class BundleArtifact:
    directory: Path
    manifest_sha256: str


def _path(value: Path) -> Path:
    if not isinstance(value, Path):
        raise TypeError("API paths must be pathlib.Path instances")
    # Do not resolve source descendants or turn serialized metadata into grants.
    return value.absolute()


def _roots(values: tuple[Path, ...]) -> tuple[Path, ...]:
    if type(values) is not tuple:
        raise TypeError("source_roots must be an explicit tuple of Paths")
    return tuple(_path(value) for value in values)


def _report(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ContractError("Unexpected API implementation report")
    return dict(cast(dict[str, object], value))


def _digest(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ContractError("Expected a retained lowercase SHA-256")
    return value


def run_offline(
    inputs: PolicyInputs,
    output: Path,
    *,
    source_roots: tuple[Path, ...],
    process_timeout_seconds: float = 3600.0,
) -> RunArtifacts:
    """Execute one policy-bound run with unchanged workflow budgets and $0 cost.

    The output's parent must exist; output itself must be new. Only the offline
    extractive backend is exposed. Exceptions and interruption propagate after
    the supervisor retains available evidence; callers must inspect before retry.
    """
    if not isinstance(inputs, PolicyInputs):
        raise TypeError("inputs must be PolicyInputs")
    destination, roots = _path(output), _roots(source_roots)
    case, snapshot, catalog, policy, root_map = (
        _path(p)
        for p in (inputs.case, inputs.snapshot, inputs.catalog, inputs.policy, inputs.roots)
    )
    request = PolicyRequest(
        policy, root_map, case, snapshot, catalog, inputs.use_id, inputs.frame_sha256
    )
    request.validate()
    limits = ProcessLimits(timeout_seconds=process_timeout_seconds)
    limits.validate()
    argv = [
        "run",
        "--case",
        str(case),
        "--snapshot",
        str(snapshot),
        "--catalog",
        str(catalog),
        "--output",
        str(destination),
    ]
    report = _report(
        _presentation.create_outer(
            destination, argv, limits=limits, policy_request=request, source_roots=roots
        )
    )
    if report.get("status") != "completed":
        raise ContractError("Offline API did not produce a completed run")
    return RunArtifacts(
        destination,
        _digest(report.get("receipt_sha256")),
        _digest(report.get("engine_receipt_sha256")),
    )


def verify_run(run: RunArtifacts, *, source_roots: tuple[Path, ...]) -> dict[str, object]:
    """Verify the outer policy, current producer, exact bytes and source semantics."""
    return _report(
        _presentation.verify_outer(
            _path(run.directory), _digest(run.receipt_sha256), source_roots=_roots(source_roots)
        )
    )


def export_run(
    run: RunArtifacts, output: Path, *, source_roots: tuple[Path, ...]
) -> BundleArtifact:
    """Verify the outer grant, then export its native source-inclusive bundle.

    Bundle replay does not re-establish the outer artifact-use grant or replay the
    producer code. Keep the outer run for those separately verified guarantees.
    """
    roots = _roots(source_roots)
    report = verify_run(run, source_roots=roots)
    engine = _report(report.get("engine"))
    if engine.get("receipt_sha256") != _digest(run.engine_receipt_sha256):
        raise ContractError("API native receipt differs from the verified outer receipt")
    destination = _path(output)
    result = _report(
        _bundle.export_bundle(
            run.native,
            destination,
            source_roots=(run.directory, *roots),
            receipt_sha256=run.engine_receipt_sha256,
            include_originals=True,
        )
    )
    return BundleArtifact(destination, _digest(result.get("manifest_sha256")))


def verify_bundle(bundle: BundleArtifact) -> dict[str, object]:
    """Verify included sources and supported semantic replay after relocation."""
    return _report(_bundle.verify_bundle(_path(bundle.directory), _digest(bundle.manifest_sha256)))
