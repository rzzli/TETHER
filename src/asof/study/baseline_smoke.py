"""Finite synthetic artifact publication/replay; no model, server or study session."""

import argparse
import hashlib
import json
from pathlib import Path
import re

from asof.atomic import ensure_directory, publish_bytes
from asof.serde import canonical, encode, freeze, parse_json

from .baselines import REQUIRED_RESOURCES, reviewer_view, run_baseline, verify_baseline
from .diagnostic import load_synthetic_request
from .diagnostic_codec import need
from .proofs import _no_links, capture_file, capture_package_proof, verify_package_proof

MAX_FILE_BYTES = 2097152


def _cells():
    return [
        dict(
            cell_id=f"cell-{index:02d}",
            fixture=fixture,
            method=method,
            neutral_label="Candidate A" if method == "extractive" else "Candidate B",
        )
        for index, (fixture, method) in enumerate(
            (
                (f, m)
                for f in ("synthetic-context", "synthetic-orientation")
                for m in ("extractive", "lexical")
            ),
            1,
        )
    ]


def _policy(request, method):
    return dict(
        schema_version=1,
        method=method,
        query=request["question"]["text"] if method == "lexical" else None,
        max_excerpts=3,
        max_quote_bytes=8192,
        max_request_bytes=65536,
        max_result_bytes=65536,
    )


def _assignment():
    return dict(
        schema_version=1,
        role="evaluation_only",
        assignment="fixed_not_randomized_not_blinded",
        cells=_cells(),
    )


def _accounting():
    return dict(
        schema_version=1,
        role="evaluation_only",
        algorithm_invocations=4,
        model_calls=0,
        input_tokens=0,
        output_tokens=0,
        provider_cost_usd=0.0,
        cpu_time_and_energy="not_measured",
        scientific_validation="not_attempted",
    )


def _members():
    return {"package-proof.json", "assignment.json", "accounting.json"} | {
        f'{cell["cell_id"]}-{kind}.json'
        for cell in _cells()
        for kind in ("request", "policy", "result", "reviewer")
    }


def _write(root, name, value):
    _no_links(root)
    payload = canonical(value)
    need(len(payload) <= MAX_FILE_BYTES, "Smoke artifact exceeds capture bound")
    publish_bytes(root / name, payload)


def _read(root, name):
    path = root / name
    proof = capture_file(path, name)
    need(proof["bytes"] <= MAX_FILE_BYTES, "Smoke artifact exceeds read bound")
    with path.open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    need(
        len(raw) == proof["bytes"]
        and hashlib.sha256(raw).hexdigest() == proof["sha256"],
        "Smoke artifact changed during read",
    )
    need(capture_file(path, name) == proof, "Smoke artifact changed after read")
    return parse_json(raw), proof


def _inventory(root):
    _no_links(root)
    names = set()
    for path in root.iterdir():
        _no_links(path)
        need(path.is_file(), "Unexpected nonfile smoke member")
        names.add(path.name)
    return names


def _prepare_parent(parent):
    """Check existing ancestry before creating any missing descendant.

    Recheck each directory after initialization. Path-based APIs cannot prevent
    every hostile rename between checks; detectable link/identity races fail.
    """
    missing = []
    ancestor = parent
    while True:
        try:
            ancestor.lstat()
            break
        except FileNotFoundError:
            missing.append(ancestor)
            ancestor = ancestor.parent
    _no_links(ancestor)
    for directory in reversed(missing):
        _no_links(directory.parent)
        before = directory.parent.stat()
        ensure_directory(directory)
        _no_links(directory)
        after = directory.parent.stat()
        need(
            (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino),
            "Smoke parent changed during initialization",
        )
    _no_links(parent)


def smoke(output):
    """Reserve a NEW directory and publish exactly four fixed synthetic cells."""
    root = Path(output).absolute()
    _prepare_parent(root.parent)
    parent_identity = root.parent.stat()
    root.mkdir()  # Atomic reservation: existing/concurrent output fails before work.
    try:
        _no_links(root)
        current_parent = root.parent.stat()
        need(
            (parent_identity.st_dev, parent_identity.st_ino)
            == (current_parent.st_dev, current_parent.st_ino),
            "Smoke parent changed during reservation",
        )
        resources = {name: "study/" + name for name in REQUIRED_RESOURCES}
        proof = capture_package_proof(resources, REQUIRED_RESOURCES)
        _write(root, "package-proof.json", proof)
        _write(root, "assignment.json", _assignment())
        for cell in _cells():
            req = load_synthetic_request(cell["fixture"])
            policy = _policy(req, cell["method"])
            prefix = cell["cell_id"]
            _write(root, prefix + "-request.json", req)
            _write(root, prefix + "-policy.json", policy)
            result = run_baseline(req, policy)
            _write(root, prefix + "-result.json", result)
            _write(
                root,
                prefix + "-reviewer.json",
                reviewer_view(result, cell["neutral_label"]),
            )
        _write(root, "accounting.json", _accounting())
        verify_package_proof(proof, required_resources=REQUIRED_RESOURCES)
        need(_inventory(root) == _members(), "Smoke inventory changed before sealing")
        artifacts = {
            name: encode(capture_file(root / name, name)) for name in sorted(_members())
        }
        receipt = dict(
            schema_version=1,
            kind="synthetic_baseline_smoke",
            role="evaluation_only",
            artifacts=artifacts,
        )
        _write(root, "receipt.json", receipt)
        anchor = hashlib.sha256(canonical(receipt)).hexdigest()
        return verify(root, anchor)
    except BaseException as exc:
        try:
            _write(
                root,
                "failure.json",
                dict(
                    schema_version=1,
                    kind="synthetic_smoke_failure",
                    error_class=type(exc).__name__,
                    message=str(exc),
                    model_calls=0,
                    retry_or_resume="not_supported",
                ),
            )
        except BaseException:
            pass  # Preserve the original exception, including interruption.
        raise


def verify(path, sha256):
    """Require external receipt anchor; recompute using current trusted package."""
    need(
        isinstance(sha256, str) and re.fullmatch(r"[0-9a-f]{64}", sha256),
        "Explicit external receipt SHA256 required",
    )
    root = Path(path).absolute()
    need(
        _inventory(root) == _members() | {"receipt.json"},
        "Smoke member inventory differs",
    )
    receipt, receipt_proof = _read(root, "receipt.json")
    need(receipt_proof["sha256"] == sha256, "External receipt anchor differs")
    need(
        isinstance(receipt, dict)
        and set(receipt) == {"schema_version", "kind", "role", "artifacts"}
        and type(receipt["schema_version"]) is int
        and receipt["schema_version"] == 1
        and receipt["kind"] == "synthetic_baseline_smoke"
        and receipt["role"] == "evaluation_only"
        and isinstance(receipt["artifacts"], dict)
        and set(receipt["artifacts"]) == _members(),
        "Invalid smoke receipt",
    )
    documents = {}
    for name in sorted(_members()):
        doc, proof = _read(root, name)
        need(
            canonical(proof) == canonical(receipt["artifacts"][name]),
            "Smoke artifact proof differs",
        )
        documents[name] = doc
    package = documents["package-proof.json"]
    need(
        isinstance(package, dict)
        and isinstance(package.get("resources"), dict)
        and set(package["resources"]) == set(REQUIRED_RESOURCES)
        and all(
            isinstance(package["resources"][name], dict)
            and package["resources"][name].get("relative_path") == "study/" + name
            for name in REQUIRED_RESOURCES
        ),
        "Smoke required resource paths differ",
    )
    verify_package_proof(package, required_resources=REQUIRED_RESOURCES)
    need(
        canonical(documents["assignment.json"]) == canonical(_assignment()),
        "Smoke assignment differs",
    )
    need(
        canonical(documents["accounting.json"]) == canonical(_accounting()),
        "Smoke accounting differs",
    )
    for cell in _cells():
        prefix = cell["cell_id"]
        req = load_synthetic_request(cell["fixture"])
        policy = _policy(req, cell["method"])
        need(
            canonical(documents[prefix + "-request.json"]) == canonical(req),
            "Smoke fixture differs",
        )
        need(
            canonical(documents[prefix + "-policy.json"]) == canonical(policy),
            "Smoke policy differs",
        )
        result = documents[prefix + "-result.json"]
        verify_baseline(req, policy, result)
        need(
            canonical(documents[prefix + "-reviewer.json"])
            == canonical(reviewer_view(result, cell["neutral_label"])),
            "Smoke reviewer projection differs",
        )
    need(
        _inventory(root) == _members() | {"receipt.json"},
        "Smoke inventory changed during verification",
    )
    for name, proof in receipt["artifacts"].items():
        need(
            canonical(capture_file(root / name, name)) == canonical(proof),
            "Smoke member changed during verification",
        )
    need(
        capture_file(root / "receipt.json", "receipt.json")["sha256"] == sha256,
        "Receipt changed during verification",
    )
    return freeze(
        dict(
            status="verified",
            receipt_sha256=sha256,
            synthetic_cells=4,
            artifact_files=len(_members()),
            model_calls=0,
            scientific_validation="not_attempted",
            real_case_admission=False,
        )
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("smoke")
    create.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("verify")
    check.add_argument("--path", type=Path, required=True)
    check.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    result = (
        smoke(args.output)
        if args.command == "smoke"
        else verify(args.path, args.sha256)
    )
    print(json.dumps(encode(result), sort_keys=True))


if __name__ == "__main__":
    main()
