"""Read-only review of installed qualification; write only a fresh compact index."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/cache/tether-051-installed-qualification-attempt01"
EXPECTED = "6ea45e6f05a4b6702a44c81f04a45813b837c88b9313fd7f1f0b66f941531a79"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def main():
    qualification = BASE / "QUALIFICATION.json"
    assert sha(qualification) == EXPECTED
    q = json.loads(qualification.read_bytes())
    assert q["status"] == "PASS"
    assert q["versions"] == {"asof-target-agents": "0.3.12", "tether-target-agents": "0.5.1"}
    assert q["parent_gating"]["parent_gate_status"] == "not_asserted"
    assert q["parent_gating"]["aggregate_stage_status"] == "pending_parent_integration_gate"
    assert len(q["commands"]) == 14
    pins = {}

    def pin(path, role):
        path = Path(path)
        relative = path.relative_to(BASE).as_posix()
        pins[relative] = dict(sha256=sha(path), bytes=path.stat().st_size, role=role)
        return pins[relative]["sha256"]

    for name in ("QUALIFICATION.json", "source-manifest.json", "wheel-proofs.json", "build-context-proof.json",
                 "fixture-producer-pins.json", "inspect-installed.py", "journal.jsonl"):
        pin(BASE / name, "qualification_control")
    for command in q["commands"]:
        assert command["exit_code"] == command["expected_exit"]
        for stream in ("stdout", "stderr"):
            assert pin(command[stream], "command_" + stream) == command[stream + "_sha256"]
        if command["label"] in ("build-core", "build-facade"):
            assert Path(command["cwd"]).is_relative_to(BASE / "build-context")
    for command in q["commands"][5:]:
        assert command["argv"][0] == q["installed"]["executable"] and "-I" in command["argv"]
    assert q["installed"]["isolated"] == 1
    environment = BASE / "environment"
    assert Path(q["installed"]["executable"]).is_relative_to(environment)
    for value in q["installed"]["sys_path"]:
        path = Path(value).resolve()
        assert path != ROOT and not path.is_relative_to(ROOT / "src")
        assert not path.is_relative_to(ROOT / "packages/tether/src")
    package_counts = {}
    sources = q["source_manifest"]["sources"]
    for wheel in q["wheel_proofs"]:
        namespace = "asof" if wheel["distribution"] == "asof-target-agents" else "tether"
        assert pin(wheel["path"], "wheel") == wheel["sha256"]
        with zipfile.ZipFile(wheel["path"]) as archive:
            observed = {name: hashlib.sha256(archive.read(name)).hexdigest()
                        for name in archive.namelist() if name.startswith(namespace + "/")}
        expected = sources[namespace]
        assert observed == expected == wheel["source_sha256"]
        package = q["installed"]["packages"][namespace]
        package_root = Path(package["root"])
        assert package_root.is_relative_to(environment) and "site-packages" in package_root.parts
        actual = {namespace + "/" + p.relative_to(package_root).as_posix(): sha(p)
                  for p in package_root.rglob("*") if p.is_file() and p.suffix in (".py", ".json")
                  and "__pycache__" not in p.parts}
        assert actual == expected == package["source_sha256"]
        checkout = ROOT / ("src" if namespace == "asof" else "packages/tether/src")
        for relative, wanted in expected.items():
            assert sha(checkout / relative) == wanted
        package_counts[namespace] = dict(members=len(expected), python=sum(p.endswith(".py") for p in expected),
                                         json=sum(p.endswith(".json") for p in expected))
    captured = json.loads((BASE / "build-context-proof.json").read_bytes())["inputs"]
    assert len(captured) == 115
    for relative, item in captured.items():
        assert sha(Path(item["original"])) == sha(Path(item["copied"])) == item["sha256"]
    assert sha(BASE / "build-context-proof.json") == q["build_context"]["proof_sha256"]
    qualifier = ROOT / "planning/review-assets/tether-ce-fixes-20261102/integration/qualify_release.py"
    assert sha(qualifier) == q["source_manifest"]["qualifier_sha256"]
    previous = None
    chain = [json.loads(line) for line in (BASE / "journal.jsonl").read_bytes().splitlines()]
    for sequence, event in enumerate(chain):
        expected = event.pop("sha256")
        assert event["sequence"] == sequence and event["previous_sha256"] == previous
        assert hashlib.sha256(canonical(event)).hexdigest() == expected
        previous = expected
    assert chain[-1]["event"] == "qualification_completed" and sha(BASE / "journal.jsonl") == q["journal_sha256"]
    core_code = {k.removeprefix("asof/"): v for k, v in sources["asof"].items() if k.endswith(".py")}
    for prefix in ("asof-demo", "tether-demo/engine", "policy-valid/outer/engine"):
        receipt = BASE / prefix / "receipt.json"
        document = json.loads(receipt.read_bytes())
        assert document["code"] == core_code and document["software_version"] == "0.3.12"
        pin(receipt, "engine_receipt")
        pin(BASE / prefix / "run.json", "run_result")
    for prefix, key in (("tether-demo", "tether_demo"), ("policy-valid/outer", "valid_policy")):
        for name in ("tether-receipt.json", "tether-manifest.json", "attempt/journal.jsonl"):
            pin(BASE / prefix / name, "outer_proof")
        assert sha(BASE / prefix / "tether-receipt.json") == q["results"][key]["receipt_sha256"]
    invalid = BASE / "policy-invalid-unused/outer"
    for name in ("tether-failure.json", "attempt/journal.jsonl"):
        pin(invalid / name, "expected_rejection_proof")
    assert not (invalid / "engine").exists() and not (invalid / "tether-receipt.json").exists()
    assert q["results"]["invalid_unused"]["backend_dispatches"] == 0
    assert q["results"]["invalid_unused"]["failure"]["stage"] == "artifact_policy_preflight"
    assert "Contemporary availability bound does not match public-download receipt" in Path(q["commands"][-1]["stderr"]).read_text()
    result = dict(status="PASS", reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
        qualification_root=str(BASE), qualification_sha256=EXPECTED, versions=q["versions"],
        aggregate_stage_status="BG01 pending clean full gate", commands=14, expected_nonzero_exits={"policy-invalid": 2},
        journal_events=len(chain), package_counts=package_counts, exact_copied_build_inputs=115,
        checks=dict(installed_isolated_paths=True, no_checkout_import_path_in_probe=True,
            wheels_installed_and_checkout_sources_equal=True, captured_build_inputs_stable=True,
            command_log_hashes_verified=True, qualification_chain_verified=True,
            core_run_receipts_bind_installed_code=True, valid_policy_checked_inputs=4,
            invalid_unused_rejected_before_dispatch=True),
        qualifier=dict(path=str(qualifier.relative_to(ROOT)), sha256=sha(qualifier)),
        indexer_sha256=sha(Path(__file__)), artifacts=pins,
        limits="Software integration only; source checkout imports were permitted solely in fixture production. No benchmark, model or scientific validation.")
    destination = Path(__file__).with_name("INSTALLED-QUALIFICATION-INDEX.json")
    with destination.open("xb") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False).encode() + b"\n")
    print(json.dumps(dict(status="PASS", index=str(destination), artifact_pins=len(pins),
                         package_counts=package_counts, journal_events=len(chain)), indent=2))


if __name__ == "__main__":
    main()
