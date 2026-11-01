"""Positive-allowlist P09 bundle preparation; emits DRAFT, never executes a study."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools/science"))
from asof.serde import canonical, parse_json
from asof.journal import RunJournal
from prepare_p05_public_bridge import safe_public

POLICY_SHA = "8d88c5dca9dfbebfd7851a6e50b5d668bdedd0a6f35bd0b77aebdff01fabf6c1"
COMPARISON_SHA = "1fc123d3c368d355c1f3d66a76eeaacea9ae954c6a6fad9aa3d05390d225cce0"
FIXTURES = ROOT / "data/cache/preprint-p05-fixtures-20261101T090035Z"
FIXTURE_SHA = "b6a43312e68cb26951124ab8a30507d47cb4c00e5b7f6f57be725f2fb1360040"
HGNC_SHA = "64fcdfcdf9bc0853ec502e0e4c7d6eb12647b2ca8b0e635ea04bdb584856baf7"
RAW_ROOT = Path(r"E:\projects_data\drug_target_agents_data")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_read(path, expected=None):
    raw = Path(path).read_bytes()
    need(expected is None or sha(raw) == expected, "Prepared anchor differs: " + Path(path).name)
    return raw


def payload_inventory(directory):
    return {p.relative_to(directory).as_posix(): sha(p.read_bytes()) for p in sorted(directory.rglob("*"))
            if p.is_file() and p.suffix in (".py", ".json")}


def wheel_payloads(path, prefix):
    with zipfile.ZipFile(path) as wheel:
        names = [n for n in wheel.namelist() if n.startswith(prefix + "/") and n.endswith((".py", ".json"))]
        need(len(names) == len(set(names)) and names, "Wheel package payload absent/duplicated")
        return {n[len(prefix) + 1:]: sha(wheel.read(n)) for n in sorted(names)}


def _prepare(bridge_root, output, core_wheel, replay_wheel, include_hgnc, presentation_root, presentation_metadata_root, journal):
    files, origins = {}, {}
    def write(logical, raw, role, origin):
        need(not Path(logical).is_absolute() and ".." not in Path(logical).parts, "Unsafe bundle member")
        path = output / logical
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
        files[logical] = dict(path=logical, sha256=sha(raw), bytes=len(raw), role=role)
        origins[logical] = origin
        if len(files) % 25 == 0:
            journal.append("build_progress", stage="allowlisted_bundle_copy", copied_files=len(files))
    def copy(logical, source, role):
        write(logical, Path(source).read_bytes(), role, "explicit_project_allowlist")
    policy_raw = checked_read(bridge_root / "source-policy.json", POLICY_SHA)
    comparison_raw = checked_read(bridge_root / "comparison.json", COMPARISON_SHA)
    policy = parse_json(policy_raw)
    write("config/source-policy.json", policy_raw, "source_only_configuration", "reviewed_neutral_projection")
    write("evaluation/comparison.json", comparison_raw, "evaluation_only", "reviewed_historical_hash_projection")
    manifest = parse_json(checked_read(FIXTURES / "manifest.json", FIXTURE_SHA))
    fixture_files = {i["path"]: i for i in manifest["files"]}
    descriptors = {}
    for key in [*("C" + f"{i:02d}" for i in range(1, 5)), *("F" + f"{i:02d}" for i in range(1, 11))]:
        logical = key + "/scenario.json"
        item = fixture_files[logical]
        scenario = parse_json(checked_read(FIXTURES / logical, item["sha256"]))
        scenario["snapshot"]["raw_root"] = None
        descriptors[key] = {k: scenario[k] for k in ("scenario_id", "case", "task", "snapshot", "catalog", "original_source_anchors")}
        descriptors[key]["originals_root"] = "fictional/" + key + "/originals"
    safe_public(descriptors)
    write("config/controls.json", canonical(descriptors) + b"\n", "fictional_source_configuration", "pinned_project_authored_scenarios")
    # Receipts are project transport metadata. Preserve their exact bytes; no
    # redaction/re-encoding can impersonate the original receipt hash.
    for item in policy["inventory"]:
        receipt = item["receipt"]
        raw = checked_read(RAW_ROOT / receipt["relative_path"], receipt["sha256"])
        need(len(raw) == receipt["bytes"], "Receipt length differs")
        safe_public(parse_json(raw))
        write("included-originals/" + receipt["relative_path"], raw, "exact_transport_receipt", "project_acquisition_metadata")
    if include_hgnc:
        item, = [i for i in policy["inventory"] if i["family"] == "hgnc"]
        raw = checked_read(RAW_ROOT / item["relative_path"], HGNC_SHA)
        need(item["sha256"] == HGNC_SHA and len(raw) == item["bytes"] == 16973159, "Only approved exact HGNC original may be included")
        write("included-originals/" + item["relative_path"], raw, "reference_original_CC0", "HGNC_official_CC0_and_exact_replay_addendum")
    for source in sorted((ROOT / "paper/release/cards").glob("*.md")):
        copy("cards/" + source.name, source, "rights_documentation")
    for name in ("manuscript.md", "supplement.md", "references.bib", "references.json", "RELATED-WORK-SOURCE-AUDIT.md", "asof-source-reporting-preprint.pdf"):
        copy("paper/" + name, ROOT / "paper" / name, "working_draft_documentation")
    expected = parse_json(checked_read(presentation_metadata_root / "expected-payloads.json",
        "30dfdeceabe87bf4db58ec78e5106cf4a73f3286d788962d21033f27312b48c8"))
    for logical, proof in expected["payloads"].items():
        raw = checked_read(presentation_root / logical, proof["sha256"])
        need(len(raw) == proof["bytes"], "Presentation payload size differs")
        write("paper/results/" + logical, raw, "aggregated_technical_results", "37_exact_historical_payload_commitments")
    for name in ("README.md", "ARTIFACTS.json"):
        raw = (presentation_root / name).read_bytes()
        if name.endswith(".json"):
            safe_public(parse_json(raw))
        write("paper/results/" + name, raw, "portable_presentation_metadata", "new_public_version_not_old_private_manifest")
    for name, expected_sha in (
        ("historical-resources.json", "af588a157854752e66ff4de8393d000af727d1c15a1542fb6a01b9ba4ddb2970"),
        ("expected-payloads.json", "30dfdeceabe87bf4db58ec78e5106cf4a73f3286d788962d21033f27312b48c8"),
    ):
        raw = checked_read(presentation_metadata_root / name, expected_sha)
        safe_public(parse_json(raw))
        write("presentation-inputs/" + name, raw, "evaluation_only", "reviewed_historical_metadata_projection")
    for source in sorted((ROOT / "paper/release/presentation").iterdir()):
        if source.is_file() and source.name in ("build_results.py", "README.md", "LICENSE"):
            copy("source/presentation/" + source.name, source, "project_portable_presentation_code")
    for source in sorted((ROOT / "src/asof").rglob("*")):
        if source.is_file() and source.suffix in (".py", ".json"):
            copy("source/core/src/asof/" + source.relative_to(ROOT / "src/asof").as_posix(), source, "project_code_or_synthetic_resource")
    for name in ("pyproject.toml", "LICENSE", "uv.lock"):
        copy("source/core/" + name, ROOT / name, "project_build_metadata")
    for source in sorted((ROOT / "paper/release/code").rglob("*")):
        rel = source.relative_to(ROOT / "paper/release/code")
        allowed = rel.parts[0] in ("src", "tests") and source.suffix == ".py" or rel.as_posix() in ("pyproject.toml", "README.md", "LICENSE")
        if source.is_file() and "__pycache__" not in rel.parts and allowed:
            copy("source/replay/" + rel.as_posix(), source, "project_reconstruction_code_or_fictional_test")
    copy("build-constraints.txt", ROOT / "paper/release/build-constraints.txt", "pinned_build_configuration")
    for wheel, name, prefix in ((core_wheel, "core", "asof"), (replay_wheel, "replay", "asof_p05_replay")):
        copy("wheels/" + wheel.name, wheel, "project_wheel")
    core_files = payload_inventory(ROOT / "src/asof")
    replay_files = payload_inventory(ROOT / "paper/release/code/src/asof_p05_replay")
    need(wheel_payloads(core_wheel, "asof") == core_files, "Core wheel differs from current pinned source")
    need(wheel_payloads(replay_wheel, "asof_p05_replay") == replay_files, "Replay wheel differs from current reviewed source")
    import pyarrow
    protocol = dict(schema_version=1, method="p09.public_reconstruction_protocol.v1", status="DRAFT_ROOT_AUTHORIZATION_PENDING",
        actual_reconstruction_authorized=False, source_policy=files["config/source-policy.json"], comparison=files["evaluation/comparison.json"],
        controls=files["config/controls.json"], files=files, core_files=core_files, replay_files=replay_files,
        environment=dict(python=platform.python_version(), pyarrow=pyarrow.__version__, platform=sys.platform),
        limits=dict(seconds=3600, memory_bytes=2 * 1024**3, output_bytes=256 * 1024**2),
        original_archive_integrity="not_claimed_by_public_reconstruction", reference_projection="remove_only_method_catalog_sha256.v1",
        scientific_validation="not_established", model_calls=0, network_calls=0, provider_spending_usd=0,
        declarations="owner_deferred_working_draft", dataset_payloads=dict(open_targets_external_files=136,hgnc_included=include_hgnc))
    safe_public(protocol)
    raw = canonical(protocol) + b"\n"
    (output / "protocol.json").write_bytes(raw)
    report = dict(schema_version=1,status="PREPARED_DRAFT_NOT_EXECUTED", created_at_utc=datetime.now(timezone.utc).isoformat(),
        draft_protocol_sha256=sha(raw), members=len(files), member_bytes=sum(f["bytes"] for f in files.values()),
        source_policy_sha256=POLICY_SHA, comparison_sha256=COMPARISON_SHA, origins=origins,
        builder_sha256=sha(Path(__file__).read_bytes()), root_READY_required=True, new_downloads=0, model_calls=0)
    (output / "preparation.json").write_bytes(canonical(report) + b"\n")
    journal.append("build_completed", draft_protocol_sha256=sha(raw), actual_reconstruction=False)
    return report


def prepare(bridge_root, output, core_wheel, replay_wheel, include_hgnc, presentation_root, presentation_metadata_root):
    journal = RunJournal(output, kind="build")
    try:
        journal.append("build_stage", stage="draft_bundle_preparation")
        return _prepare(bridge_root, output, core_wheel, replay_wheel, include_hgnc, presentation_root, presentation_metadata_root, journal)
    except BaseException as error:
        try:
            journal.fail(error, "draft_bundle_preparation")
        finally:
            raise
    finally:
        journal.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--core-wheel", type=Path, required=True)
    parser.add_argument("--replay-wheel", type=Path, required=True)
    parser.add_argument("--include-hgnc", action="store_true")
    parser.add_argument("--presentation-root", type=Path, required=True)
    parser.add_argument("--presentation-metadata-root", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output.absolute()
    need(output.is_relative_to(ROOT / "data/cache"), "Draft bundle preparation stays in ignored workspace cache")
    print(json.dumps(prepare(args.bridge_root.absolute(), output, args.core_wheel.absolute(), args.replay_wheel.absolute(), args.include_hgnc,
        args.presentation_root.absolute(), args.presentation_metadata_root.absolute()), indent=2))


if __name__ == "__main__":
    main()
