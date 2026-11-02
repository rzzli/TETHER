"""Check retained BG01 gates without running tests, builds, models or benchmarks.

All required final records must exist. Output is exclusively created and failures
produce FAILED evidence, never a partial PASS. This is an evidence consistency
check; it is not an attestation against a malicious filesystem owner.
"""
from __future__ import annotations

import argparse
import ast
import base64
import csv
from collections import Counter
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parents[1]
BASELINE = "114fecf"
VERSIONS = {"asof-target-agents": "0.3.12", "tether-target-agents": "0.5.1"}
SOURCE_ROOTS = {"asof": ROOT / "src/asof", "tether": ROOT / "packages/tether/src/tether"}
PROFILE_PATH = "src/asof/archive/semantic_dependencies.json"
OLD_PROFILE_SHA256 = "f30b24c24af91523d67e98c0daec50a78aba1e637db89fd8d21c20386988dba5"
FIRST_PROFILE_SHA256 = "27282ad12814df284cb9a81c25f935f0c47177ead845c9e831bc687c64d85e59"
NEW_PROFILE_SHA256 = "645b1fb409b11f4d0e8d5d9e96e14f2b6302b1ecb5d03c64ddf5cfc8d683d016"
# Immutable BG01 evidence, matched byte-for-byte against commits 5cd633b and
# 4aa3328. Pinning the records also prevents a smaller check list being resealed.
PRESERVATION_SHA256 = "9c6f2a3168b1cd083dbc973a7d15141b5d9ff3e7e3ac6551a4f23010b63f493c"
PRESERVATION_READBACK_SHA256 = "945faf8789de924d916f2d8ad52355014c73fa92bd2eb0130a3b4b0122e6edfd"
PRESERVATION_CHECK_COUNTS = {
    "exact_core_wheel_member": 1, "installed_wheel_payload": 110,
    "monitor_configuration_disabled": 1, "old_demo_finalized": 1,
    "old_engine_source_pin": 66, "old_environment_identity": 1,
    "old-identity_exit": 1, "old-offline-demo_exit": 1, "old-offline-verify_exit": 1,
    "retained_hash": 12, "tracked_paper_worker_monitor_unchanged": 1,
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class Audit:
    def __init__(self):
        self.inputs, self.checks = {}, []

    def need(self, condition, name, **detail):
        self.checks.append(dict(name=name, passed=bool(condition), **detail))
        if not condition:
            raise ValueError(name)

    def read(self, path):
        path = Path(path).absolute()
        self.need(path.is_file(), "required evidence exists", path=str(path))
        raw = path.read_bytes()
        self.inputs[str(path)] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        return json.loads(raw)

    def pins(self, pins):
        self.need(bool(pins), "nonempty runtime/test pins")
        for relative, expected in pins.items():
            path = ROOT / relative.replace("\\", "/")
            self.need(path.is_file() and sha(path) == expected, "retained source pin matches", path=str(path))

    def tests(self, document, count, success_key="success", skip_key="skips"):
        self.need(document.get(success_key) is True and document.get("tests") == count and
                  document.get("failures") == document.get("errors") == document.get(skip_key) == 0,
                  "targeted suite complete", expected_tests=count)

    def unittest_log(self, path, count, *, driver_report=None):
        path = Path(path).absolute()
        raw = path.read_bytes()
        self.inputs[str(path)] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        terminals = list(re.finditer(r"^Ran (\d+) tests? in [^\n]+\n(?:[ \t]*\n)*OK[ \t]*(?:\n|$)",
                                     text, re.MULTILINE))
        self.need(len(terminals) == 1 and int(terminals[0].group(1)) == count and
                  len(re.findall(r"^Ran\b", text, re.MULTILINE)) == 1 and
                  len(re.findall(r"^OK\b", text, re.MULTILINE)) == 1 and
                  not re.search(r"^FAILED\b|^ERROR:|^FAIL:", text, re.MULTILINE),
                  "unittest terminal log matches", path=str(path), expected_tests=count)
        trailing = text[terminals[0].end():]
        if driver_report is None:
            self.need(not trailing.strip(), "ordinary unittest log ends with successful summary", path=str(path))
        else:
            # The full driver prints probe output and its final report after
            # unittest. Other logs cannot opt into this by merely having text.
            self.need(isinstance(driver_report, dict), "full driver report is a mapping")
            candidates = []
            for start in re.finditer(r"^[ \t]*\{", trailing, re.MULTILINE):
                try:
                    value = json.loads(trailing[start.start():])
                except json.JSONDecodeError:
                    continue
                candidates.append((start.start(), value))
            self.need(len(candidates) == 1 and candidates[0][1] == driver_report,
                      "full driver log ends with exact supplied report", path=str(path))
            prefix = trailing[:candidates[0][0]]
            self.need(re.search(r"^(?:Ran\b|OK\b|FAILED\b|ERROR:|FAIL:|Traceback\b|"
                                r"KeyboardInterrupt\b|InterruptedError\b|SystemExit\b|"
                                r"\S[^\n]*\([^\n]+\)[ \t]+\.\.\.|[-=]{5,}[ \t]*$)",
                                prefix, re.MULTILINE) is None,
                      "full driver has no later unittest execution or interruption", path=str(path))


def current_gate_sources():
    """Independently enumerate the bounded runtime/test/build inputs of run_gate."""
    paths = set()
    for relative in ("src/asof", "packages/tether/src/tether", "tests", "packages/tether/tests", "tools"):
        paths.update(p for p in (ROOT / relative).rglob("*") if p.is_file() and
                     "__pycache__" not in p.parts and p.suffix in {".py", ".ps1", ".json"})
    paths.update(ROOT / name for name in ("pyproject.toml", "uv.lock", "packages/tether/pyproject.toml",
                 "packages/tether/uv.lock", "paper/release/build-constraints.txt", "data/catalog/sources.json",
                 "data/catalog/policy-v2.json"))
    paths.add(Path(__file__).with_name("run_gate.py"))
    return {p.relative_to(ROOT).as_posix(): dict(sha256=sha(p), bytes=p.stat().st_size) for p in sorted(paths)}


def check_source_bracket(audit, path, full_gate, full_log):
    bracket = audit.read(path)
    audit.need(bracket["schema_version"] == 1 and bracket["status"] == "PASS" and
               bracket["exit_code"] == 0 and bracket["changed_sources"] == [], "full gate source bracket passed")
    before_path = Path(bracket["before_path"])
    before = audit.read(before_path)
    audit.need(sha(before_path) == bracket["before_sha256"] and before["schema_version"] == 1,
               "full gate launch manifest bound")
    audit.need(before["sources"] == bracket["after_sources"] == current_gate_sources(),
               "full gate source inventory unchanged before after and now")
    for field, supplied in (("report", full_gate), ("log", full_log)):
        recorded = Path(bracket[field + "_path"])
        audit.need(recorded.resolve() == supplied.resolve() and sha(supplied) == bracket[field + "_sha256"],
                   "full gate bracket binds report/log", field=field)
    started = audit.read(Path(str(path).removesuffix(".source-bracket.json") + ".started.json"))
    audit.need(started["status"] == "started" and all(started[field] == bracket[field] for field in
               ("schema_version", "argv", "cwd", "started_at_utc", "before_path", "before_sha256", "pid")),
               "full gate start record binds bracket")
    argv = bracket["argv"]
    audit.need(len(argv) == 9 and argv[1] == "-B" and Path(argv[2]).resolve() == (ROOT / "tools/validate.py").resolve()
               and argv[3:8] == ["--mode", "full", "--package", "--failfast", "--report"] and
               Path(argv[8]).resolve() == full_gate.resolve() and Path(bracket["cwd"]).resolve() == ROOT,
               "full gate invoked required complete driver")
    start, finish = (datetime.fromisoformat(bracket[field]) for field in ("started_at_utc", "finished_at_utc"))
    audit.need(start.utcoffset() is not None and finish.utcoffset() is not None and finish >= start,
               "full gate bracket timestamps ordered")


def check_profile_step(audit, directory, old_pin, new_pin, changed_modules, profile_name):
    prepared_path, applied_path = directory / "PREPARED.json", directory / "APPLIED.json"
    prepared, applied = audit.read(prepared_path), audit.read(applied_path)
    old_path, candidate_path = ROOT / prepared["old_copy"], ROOT / prepared["candidate"]
    old, candidate = audit.read(old_path), audit.read(candidate_path)
    audit.need(prepared["baseline"] == applied["baseline"] == BASELINE and
               prepared["active_resource"] == applied["active_resource"] == PROFILE_PATH and
               prepared["old_resource_sha256"] == applied["old_resource_sha256"] == sha(old_path) == old_pin and
               prepared["new_resource_sha256"] == applied["new_resource_sha256"] == sha(candidate_path) == new_pin,
               "exact reviewed archive profile migration", migration=directory.name)
    audit.need(applied["prepared_sha256"] == sha(prepared_path) and
               applied["review_sha256"] == sha(ROOT / prepared["review"]), "archive migration application binds review")
    unchanged_metadata = {key: value for key, value in old.items() if key not in
                          {"modules", "executing_build_profile", "previous_resource_sha256", "scope", "compatibility_review"}}
    audit.need(set(candidate) == set(old) and
               all(candidate[key] == value for key, value in unchanged_metadata.items()) and
               candidate["previous_resource_sha256"] == old_pin and
               candidate["executing_build_profile"] == profile_name and
               candidate["compatibility_review"] == prepared["review"], "archive policy and metadata delta bounded")
    changed = {name for name in old["modules"] if old["modules"][name] != candidate["modules"].get(name)}
    audit.need(set(old["modules"]) == set(candidate["modules"]) and len(old["modules"]) == 22 and
               changed == set(prepared["changed_modules"]) == changed_modules and
               prepared["unchanged_module_count"] == 22 - len(changed_modules) and prepared["policy_unchanged"] is True,
               "archive inventory changes only reviewed module pins", migration=directory.name)
    for name in changed:
        audit.need(prepared["changed_modules"][name] == dict(old_sha256=old["modules"][name], new_sha256=candidate["modules"][name]),
                   "archive reviewed module delta matches", module=name)
    return old_path, candidate_path, candidate


def check_profile_validation(audit, validation_path, directory, profile_pin, modules):
    validation = audit.read(validation_path)
    audit.need(validation["status"] == "PASS" and validation["profile_sha256"] == profile_pin and
               validation["modules"] == modules and
               validation["script_sha256"] == sha(directory / "run_archive_regressions.py"), "archive profile qualification bound")
    audit.need(validation["tests"] == dict(run=52, failures=0, errors=0, skipped=0), "archive profile regression suite passed")
    work = Path(validation["work"])
    audit.need(sha(work / "tests.log") == validation["tests_log_sha256"], "archive test log unchanged")
    audit.unittest_log(work / "tests.log", 52)
    producer = validation["old_producer"]
    audit.need(producer["exit_code"] == 0 and all(sha(work / ("old." + stream + ".log")) == producer[stream + "_sha256"]
               for stream in ("stdout", "stderr")), "old archive fixture producer completed")
    old_manifest = audit.read(work / "old/manifest.json")
    audit.need(sha(work / "old/manifest.json") == validation["old_manifest_sha256"] and
               old_manifest["engine_version"] == "0.3.11", "old archive producer manifest bound")
    controls = validation["relocated_controls"]
    audit.need(len(controls) == 3 and {row["kind"] for row in controls} == {"normal", "unknown-timeout", "invalid-overquote"},
               "archive old-run comparison controls complete")
    for row in controls:
        if row["kind"] == "invalid-overquote":
            audit.need(row["expected"] == row["disposition"] == "rejected" and
                       row["error"] == "Failed local response lost its validated usage", "contradictory old overquote rejects honestly")
        else:
            verified = row["verification"]
            audit.need(row["expected"] == row["disposition"] == "verified" and
                       verified["semantic_consistency"] == "verified" and verified["external_anchor_checked"] is True and
                       verified["archived_code_executed"] is False and
                       verified["executing_dependency_resource_sha256"] == profile_pin,
                       "ordinary valid old archive verifies under reviewed helper profile", kind=row["kind"])


def check_archive_profile(audit, validation_path):
    first_dir, second_dir = EVIDENCE / "archive-profile", EVIDENCE / "archive-profile-v2"
    old_path, first_path, first = check_profile_step(audit, first_dir, OLD_PROFILE_SHA256, FIRST_PROFILE_SHA256,
        {"__init__.py", "local_model.py", "provenance.py"}, "tether-ce-corrections-0.3.12-20261102")
    baseline_bytes = subprocess.check_output(["git", "show", BASELINE + ":" + PROFILE_PATH], cwd=ROOT)
    audit.need(baseline_bytes == old_path.read_bytes(), "old profile bytes preserved from baseline")
    check_profile_validation(audit, first_dir / "VALIDATION.json", first_dir, FIRST_PROFILE_SHA256, first["modules"])
    previous_path, candidate_path, candidate = check_profile_step(audit, second_dir, FIRST_PROFILE_SHA256, NEW_PROFILE_SHA256,
        {"serde.py"}, "tether-ce-corrections-0.3.12-atomic-retry-20261102")
    audit.need(first_path.read_bytes() == previous_path.read_bytes() and
               (ROOT / PROFILE_PATH).read_bytes() == candidate_path.read_bytes(),
               "active profile follows exact two-step reviewed migration")
    audit.pins({"src/asof/" + name: expected for name, expected in candidate["modules"].items()})
    check_profile_validation(audit, validation_path, second_dir, NEW_PROFILE_SHA256, candidate["modules"])
    return old_path


def inspect_wheel(audit, proof, expected_sources):
    path = Path(proof["path"])
    audit.need(sha(path) == proof["sha256"] and path.stat().st_size == proof["bytes"], "wheel bytes match", path=str(path))
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        audit.need(len(names) == len(set(names)) and all(not n.startswith("/") and ".." not in n.split("/") for n in names),
                   "wheel member names valid")
        namespace = "asof" if proof["distribution"] == "asof-target-agents" else "tether"
        observed = {n: hashlib.sha256(archive.read(n)).hexdigest() for n in names if n.startswith(namespace + "/")}
        audit.need(observed == expected_sources == proof["source_sha256"], "wheel exact source inventory matches", namespace=namespace)
        records = [n for n in names if n.endswith(".dist-info/RECORD")]
        audit.need(len(records) == 1, "one wheel RECORD")
        rows = list(csv.reader(io.StringIO(archive.read(records[0]).decode())))
        audit.need(len(rows) == len(names) and {row[0] for row in rows} == set(names), "wheel RECORD closes inventory")
        for name, encoded, size in rows:
            payload = archive.read(name)
            if name == records[0]:
                correct = encoded == size == ""
            else:
                digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
                correct = encoded == "sha256=" + digest and int(size) == len(payload)
            audit.need(correct, "wheel RECORD member matches", member=name)
        metadata_names = [n for n in names if n.endswith(".dist-info/METADATA")]
        audit.need(len(metadata_names) == 1, "one wheel METADATA")
        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        audit.need(metadata["Name"] == proof["distribution"] and metadata["Version"] == VERSIONS[metadata["Name"]], "wheel version matches")
        if namespace == "tether":
            audit.need("asof-target-agents==0.3.12" in metadata.get_all("Requires-Dist", []), "facade pins corrected engine")


def check_build_context(audit, path, result, manifest):
    gating = result["parent_gating"]
    mode = gating.get("execution_mode")
    audit.need(mode in {"isolated_build_context", "core_gate_terminal"}, "qualification execution mode recognized")
    terminal = mode == "core_gate_terminal"
    expected_gating = dict(execution_mode=mode, parent_core_gate_terminal_confirmed=terminal,
                          parent_gate_status="terminal_confirmed_by_caller" if terminal else "not_asserted",
                          aggregate_stage_status="pending_parent_integration_gate")
    audit.need(gating == expected_gating and gating["parent_core_gate_terminal_confirmed"] is terminal,
               "qualification reports truthful separate parent gating")
    context_path = path.parent / "build-context"
    proof_path = path.parent / "build-context-proof.json"
    proof = audit.read(proof_path)
    context = result["build_context"]
    audit.need(Path(context["path"]).resolve() == Path(proof["context"]).resolve() == context_path.resolve() and
               context["proof_sha256"] == sha(proof_path) and context["post_capture_stability"] == "verified",
               "isolated build context and proof bound")
    expected_build_inputs = {"pyproject.toml", "packages/tether/pyproject.toml", "LICENSE",
                             "packages/tether/LICENSE", "paper/release/build-constraints.txt"}
    audit.need(set(manifest["build_inputs"]) == expected_build_inputs, "isolated build prerequisites complete")
    expected_inputs = dict(manifest["build_inputs"])
    for namespace, members in manifest["sources"].items():
        audit.need(namespace in SOURCE_ROOTS, "build context namespace recognized", namespace=namespace)
        prefix = "src/" if namespace == "asof" else "packages/tether/src/"
        expected_inputs.update({prefix + member: pin for member, pin in members.items()})
    audit.need(set(proof["inputs"]) == set(expected_inputs) and type(context["inputs"]) is int and
               context["inputs"] == len(expected_inputs), "isolated build input inventory complete")
    for relative, expected in expected_inputs.items():
        item = proof["inputs"][relative]
        original, copied = Path(item["original"]), Path(item["copied"])
        audit.need(original.resolve() == (ROOT / relative).resolve() and
                   copied.resolve() == (context_path / relative).resolve() and
                   copied.resolve().is_relative_to(context_path.resolve()),
                   "isolated build member paths match", member=relative)
        audit.need(item["sha256"] == expected == sha(original) == sha(copied) and type(item["bytes"]) is int and
                   item["bytes"] == original.stat().st_size == copied.stat().st_size,
                   "isolated build member bytes unchanged", member=relative)
    return expected_gating, dict(context=str(context_path), inputs=len(expected_inputs), proof_sha256=sha(proof_path))


def check_installed(audit, path):
    path = path.resolve()
    path = path / "QUALIFICATION.json" if path.is_dir() else path
    result = audit.read(path)
    audit.need(result.get("status") == "PASS" and result.get("versions") == VERSIONS, "installed qualification complete")
    audit.need(not (path.parent / "FAILURE.json").exists(), "installed attempt has no terminal failure")
    manifest = audit.read(path.parent / "source-manifest.json")
    audit.need(manifest == result["source_manifest"] and manifest["versions"] == VERSIONS, "installed manifest identity")
    audit.need(manifest["qualifier_sha256"] == sha(Path(__file__).with_name("qualify_release.py")), "qualifier code unchanged")
    audit.pins(manifest["build_inputs"])
    gating, context_event = check_build_context(audit, path, result, manifest)
    wheels = audit.read(path.parent / "wheel-proofs.json")
    audit.need(wheels == result["wheel_proofs"] and {r["distribution"] for r in wheels} == set(VERSIONS) and len(wheels) == 2,
               "two expected wheel proofs")
    audit.pins(audit.read(path.parent / "fixture-producer-pins.json"))
    for namespace, root in SOURCE_ROOTS.items():
        paths = set(root.rglob("*.py"))
        if namespace == "asof":
            for pattern in ("demo/*.json", "demo/v2/*.json", "archive/*.json", "study/resources/*.json"):
                paths.update(root.glob(pattern))
        current = {namespace + "/" + p.relative_to(root).as_posix(): sha(p) for p in paths if "__pycache__" not in p.parts}
        audit.need(current == manifest["sources"][namespace], "current runtime/resource inventory matches qualification", namespace=namespace)
        inspected = result["installed"]["packages"][namespace]
        audit.need(inspected["version"] == VERSIONS["asof-target-agents" if namespace == "asof" else "tether-target-agents"] and
                   inspected["source_sha256"] == current, "installed package proof matches", namespace=namespace)
        installed_root = Path(inspected["root"])
        audit.need(installed_root.is_relative_to(path.parent / "environment") and "site-packages" in installed_root.parts,
                   "installed package isolated from checkout", namespace=namespace)
        observed = {namespace + "/" + p.relative_to(installed_root).as_posix(): sha(p)
                    for p in installed_root.rglob("*") if p.is_file() and p.suffix in {".py", ".json"} and "__pycache__" not in p.parts}
        audit.need(observed == current, "installed files freshly match manifest", namespace=namespace)
        module = ast.parse((root / "__init__.py").read_text())
        declared = next(node.value.value for node in module.body if isinstance(node, ast.Assign) and
                        any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets))
        audit.need(declared == inspected["version"], "runtime version declaration matches", namespace=namespace)
    for proof in wheels:
        inspect_wheel(audit, proof, manifest["sources"]["asof" if proof["distribution"] == "asof-target-agents" else "tether"])
    audit.need(result["installed"]["isolated"] == 1, "installed interpreter isolated")
    commands = result["commands"]
    labels = ["uv-version", "build-core", "build-facade", "create-environment", "install-wheels", "installed-source-proof",
              "tether-version", "asof-demo", "asof-verify", "tether-demo", "tether-verify", "policy-valid", "policy-source-verify", "policy-invalid"]
    audit.need([row["label"] for row in commands] == labels, "installed required command schedule complete")
    for command in commands:
        expected = 2 if command["label"] == "policy-invalid" else 0
        audit.need(command["expected_exit"] == command["exit_code"] == expected, "installed command terminal", label=command["label"])
        for field in ("stdout", "stderr"):
            audit.need(sha(command[field]) == command[field + "_sha256"], "installed command log unchanged", label=command["label"], stream=field)
    by_label = {command["label"]: command for command in commands}
    for label, directory in (("build-core", path.parent / "build-context"),
                             ("build-facade", path.parent / "build-context/packages/tether")):
        command, argv = by_label[label], by_label[label]["argv"]
        audit.need(Path(command["cwd"]).resolve() == directory.resolve() and len(argv) == 10 and
                   argv[0] == by_label["uv-version"]["argv"][0] and argv[1:4] == ["build", "--offline", "--build-constraints"] and
                   Path(argv[4]).resolve() == (path.parent / "build-context/paper/release/build-constraints.txt").resolve() and
                   argv[5] == "--python" and argv[7:9] == ["--wheel", "--out-dir"] and
                   Path(argv[9]).resolve() == (path.parent / "wheels").resolve(),
                   "wheel build uses isolated context and copied constraints", label=label)
    audit.need(audit.read(by_label["installed-source-proof"]["stdout"]) == result["installed"], "installed proof equals retained stdout")
    version_text = Path(by_label["tether-version"]["stdout"]).read_text().strip()
    audit.need(version_text == "TETHER 0.5.1 (compatibility engine 0.3.12)", "installed CLI version proof")
    for label, key in (("asof-verify", "asof_demo"), ("tether-verify", "tether_demo"), ("policy-source-verify", "valid_policy")):
        audit.need(audit.read(by_label[label]["stdout"]) == result["results"][key], "installed verification equals retained stdout", run=key)
    journal_path = path.parent / "journal.jsonl"
    audit.need(sha(journal_path) == result["journal_sha256"], "qualification journal hash matches")
    previous, events, journal = None, [], []
    for sequence, line in enumerate(journal_path.read_bytes().splitlines()):
        row = json.loads(line)
        claimed = row.pop("sha256")
        audit.need(row["sequence"] == sequence and row["previous_sha256"] == previous and
                   hashlib.sha256(canonical(row)).hexdigest() == claimed, "qualification journal chain valid", sequence=sequence)
        previous = claimed; events.append(row["event"]); journal.append(row)
    audit.need(events[0] == "qualification_started" and events[-1] == "qualification_completed" and not any("failed" in e for e in events),
               "qualification journal terminal success")
    for event in ("qualification_started", "qualification_completed"):
        records = [row["details"] for row in journal if row["event"] == event]
        audit.need(len(records) == 1 and all(records[0].get(key) == value for key, value in gating.items()) and
                   records[0].get("parent_core_gate_terminal_confirmed") is gating["parent_core_gate_terminal_confirmed"],
                   "qualification journal agrees with parent gating", event=event)
    audit.need(journal[0]["details"]["manifest_sha256"] == sha(path.parent / "source-manifest.json") and
               journal[-1]["details"]["versions"] == VERSIONS and
               journal[-1]["details"]["scientific_validation"] == "not_established",
               "qualification journal binds manifest versions and scope")
    context_records = [row["details"] for row in journal if row["event"] == "isolated_build_context_verified"]
    audit.need(context_records == [context_event] and events.index("isolated_build_context_verified") < events.index("command_reserved"),
               "qualification journal binds context before any build command")
    audit.need([row["details"] for row in journal if row["event"] == "command_returned"] == commands,
               "qualification journal binds completed command records")
    for name in ("asof_demo", "tether_demo", "valid_policy"):
        verified = result["results"][name]
        engine = verified.get("engine", verified)
        audit.need(verified["status"] == "integrity_verified" and verified["external_anchor_checked"] is True and
                   engine["semantic_consistency"] == "verified" and engine["code_matches_current"] is True and
                   engine["source_binding"] == "current_originals", "installed run fully verified", run=name)
    negative = result["results"]["invalid_unused"]
    policy_proof = result["results"]["valid_policy"]["artifact_policy"]
    audit.need(policy_proof["checked_inputs"] == 4 and policy_proof["status"] == "artifact_policy_consistency_verified", "installed complete policy proof")
    audit.need(negative["expected_rejection"] is True and negative["backend_dispatches"] == 0 and
               negative["failure"]["stage"] == "artifact_policy_preflight" and "engine_dispatch" not in negative["events"],
               "installed unused-node rejection before dispatch")
    return {proof["distribution"]: proof["sha256"] for proof in wheels}


def check_regressions(audit):
    before = audit.read(EVIDENCE / "ce01/before-regression.json")
    audit.need(before["expected_assertion_failure"] is True and before["exit_code"] == 1, "CE01 red witness retained")
    ce01 = audit.read(EVIDENCE / "ce01/VALIDATION.json")
    audit.need(ce01["status"] == "PASS" and ce01["tests"] == 12 and
               ce01["failures"] == ce01["errors"] == ce01["skipped"] == 0, "CE01 green suite")
    audit.pins({"tools/data/Test-DownloadBatch.ps1": ce01["fixed_script_sha256"],
                "tests/test_download_report_publication.py": ce01["regression_sha256"]})
    audit.unittest_log(EVIDENCE / "ce01" / ce01["after_tests"], 12)
    red = audit.read(EVIDENCE / "ce02/red-results.json")
    audit.need(red["success"] is False and red["failures"] > 0, "CE02 red assertions retained")
    ce02 = audit.read(EVIDENCE / "ce02/green4-results.json"); audit.tests(ce02, 12); audit.pins(ce02["source_sha256"])
    related = audit.read(EVIDENCE / "ce02/compatibility2-results.json"); audit.tests(related, 122)
    audit.need(related["source_sha256"] == sha(ROOT / "src/asof/local_model.py"), "CE02 compatibility source unchanged")
    red = audit.read(EVIDENCE / "ce03/red-v2/results.json")
    audit.need(red["successful"] is False and red["tests"] == 9 and red["failures"] == 5 and red["errors"] == 0,
               "CE03 red witness retained")
    ce03 = audit.read(EVIDENCE / "ce03/related-v2/results.json")
    audit.tests(ce03, 85, "successful", "skipped"); audit.pins(ce03["source_sha256"])
    audit.unittest_log(EVIDENCE / "ce03/related-v2/tests.log", 85)
    peer02 = audit.read(EVIDENCE / "peer-ce02/new-v2.json")
    audit.need(peer02["passed"] is True and peer02["module_sha256"] == sha(ROOT / "src/asof/local_model.py"), "CE02 peer source/passed")
    over = next(row for row in peer02["runs"] if row["mode"] == "overquote")
    audit.need(over["calls"] == over["violations"] == 1 and over["claims"] == 0 and over["measured"]["input_tokens"] == 1000000 and
               over["estimated"]["input_tokens"] == 0 and over["verification"]["semantic_consistency"] == "verified", "CE02 sealed overquote evidence")
    audit.need(len(peer02["mutations"]) == 4 and all(row["rejected"] is True for row in peer02["mutations"]), "CE02 peer mutations reject")
    old02 = audit.read(EVIDENCE / "peer-ce02/old-reverified-v1.json")
    audit.need(old02["passed"] is True and len(old02["runs"]) == 2 and all(
        row["verification"]["semantic_consistency"] == "verified" and row["verification"]["external_anchor_checked"] is True and
        row["verification"]["code_matches_current"] is False for row in old02["runs"]), "CE02 unchanged old failed runs verify honestly")
    peer03 = audit.read(EVIDENCE / "peer-ce03/results.json")
    audit.need(peer03["status"] == "PASS" and len(peer03["cases"]) == 12, "CE03 independent cases complete")
    for module in peer03["modules"].values():
        audit.need(sha(module["path"]) == module["sha256"], "CE03 peer module unchanged", path=module["path"])
    for row in peer03["cases"]:
        expected = "accepted" if row["name"] in {"exact_utc_alias", "separate_release_basis"} else "rejected"
        audit.need(row["status"] == expected, "CE03 peer expected disposition", name_of_case=row["name"], used=row["used"])
    old03 = audit.read(EVIDENCE / "ce03/legacy-verify-v1/results.json")
    audit.need(old03["passed"] is True and len(old03["results"]) == 3 and all(row["passed"] is True for row in old03["results"]),
               "CE03 old seal paired compatibility")


def check_atomic_validation(audit, path):
    result = audit.read(path)
    directory = EVIDENCE / "integration/windows-replace"
    audit.need(result["status"] == "PASS" and result["attempt_limit"] == 3 and
               result["requested_backoff_seconds"] == [0.05, 0.1] and result["eligible_native_errors"] == [5, 32, 33] and
               result["no_clobber_sources_unchanged"] is True and
               result["provider_spending_usd"] == result["actual_model_calls"] == 0,
               "bounded atomic replacement qualification passed")
    audit.need(set(result["source_sha256"]) == {"src/asof/serde.py", "src/asof/atomic.py", "src/asof/maintenance.py",
                                               "tests/test_serde_atomic_replace.py"}, "atomic source and regression pins complete")
    audit.pins(result["source_sha256"])
    audit.need(result["driver_sha256"] == sha(directory / "run_regressions.py") and
               result["summarizer_sha256"] == sha(directory / "summarize.py"), "atomic regression driver and summary code unchanged")
    phases = {"red": 10, "green": 10, "compatibility": 72, "atomic-maintenance": 21}
    audit.need(set(result["evidence_sha256"]) == {phase + "-results.json" for phase in phases} and
               set(result["log_sha256"]) == {phase + "-tests.log" for phase in phases},
               "atomic retained result and log inventories complete")
    for phase, count in phases.items():
        record_path, log_path = directory / (phase + "-results.json"), directory / (phase + "-tests.log")
        record = audit.read(record_path)
        audit.need(result["evidence_sha256"][record_path.name] == sha(record_path) and
                   result["log_sha256"][log_path.name] == record["log_sha256"] == sha(log_path) and
                   record["driver_sha256"] == result["driver_sha256"] and
                   all(record[key] == value for key, value in result["results"][phase].items()),
                   "atomic phase evidence bound", phase=phase)
        if phase == "red":
            audit.need(record["tests"] == count and record["success"] is False and
                       (record["failures"], record["errors"], record["skipped"]) == (5, 6, 0) and
                       record["source_sha256"]["src\\asof\\serde.py"] ==
                       "5f5daf814e4debe49cfce22a25b2d6b71cc20b6e9184ddb6a4a4c5a4eeb5b7a8",
                       "atomic pre-fix regression witness retained")
            audit.pins({name: pin for name, pin in record["source_sha256"].items() if name != "src\\asof\\serde.py"})
        else:
            audit.tests(record, count, skip_key="skipped")
            audit.pins(record["source_sha256"])
            audit.unittest_log(log_path, count)


def check_preservation_records(audit, preservation_path, readback_path):
    preserved, readback = audit.read(preservation_path), audit.read(readback_path)
    audit.need(sha(preservation_path) == PRESERVATION_SHA256 and
               sha(readback_path) == PRESERVATION_READBACK_SHA256,
               "exact committed old-release preservation records")
    checks = preserved["checks"]
    audit.need(len(checks) == 196 and Counter(row["name"] for row in checks) == PRESERVATION_CHECK_COUNTS,
               "old preservation complete reviewed check inventory")
    audit.need(preserved["status"] == readback["status"] == "PASS" and preserved["baseline"] == BASELINE and
               all(row["passed"] is True for row in checks), "old release preservation passed")
    audit.need(readback["source_record_sha256"] == sha(preservation_path) and readback["old_semantics"] == "verified" and
               readback["old_code_identity"] is True and readback["installed_payloads_rehashed_after_demo"] == 110,
               "old preservation readback binds complete source record")
    return preserved, readback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("full-gate", "full-log", "source-bracket", "archive-profile-validation", "atomic-validation", "facade-log", "installed",
                 "preservation", "preservation-readback", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        parser.error("Output already exists; choose a new validation file")
    audit = Audit()
    report = dict(schema_version=1, stage="BG01", status="FAILED", baseline=BASELINE, versions=VERSIONS,
        scope="Retained correctness/test/installed-release evidence consistency; no benchmark/model execution",
        limitations=["Source bracketing covers the declared runtime, resources, tests, tools and build inputs; documentation and evidence files outside that inventory are not a whole-worktree attestation.",
                    "No claim of hostile-worktree tamper resistance, scientific validity, Linux execution, benchmark integration or whole-goal completion."])
    try:
        platform = audit.read(EVIDENCE / "integration/platform-scope.json")
        audit.need(platform["status"] == "PASS" and platform["tests"] == 7 and
                   platform["failures"] == platform["errors"] == platform["skips"] == 0,
                   "validator platform-scope controls passed")
        audit.pins(platform["files"])
        audit.unittest_log(EVIDENCE / "integration/platform-gate-tests.log", 7)
        peer_directory = EVIDENCE / "integration/windows-replace-peer"
        peer = audit.read(peer_directory / "PEER-REVIEW.json")
        audit.need(peer["status"] == "SCOPED_PASS_WITH_EXPLICIT_CONTENTION_FAILURES" and
                   peer["primary_control_families"] == 7, "atomic peer safety scope explicit")
        audit.pins(peer["source_pins"])
        for item in peer["evidence"]:
            evidence_path = ROOT / item["path"].replace("\\", "/")
            audit.need(sha(evidence_path) == item["sha256"] and evidence_path.stat().st_size == item["bytes"],
                       "atomic peer evidence unchanged", path=str(evidence_path))
        first_peer = audit.read(peer_directory / "INITIAL-STRESS-RESULT.json")
        final_peer = audit.read(peer_directory / "peer-v2-console.json")
        audit.need(first_peer["status"] == "FAILED" and final_peer["status"] == "PASS" and
                   final_peer["source_stability"] == "verified", "failed stress expectation and scoped followup retained")
        controls = final_peer["controls"]
        audit.need(len(controls) == 7 and all(row["status"] == "PASS" for row in controls) and
                   {row["name"] for row in controls} == {"released_handle", "persistent_handle", "noneligible_and_interrupt",
                   "cleanup_preserves_primary", "no_clobber_unchanged", "concurrent_complete_json", "stale_writer_semantics"},
                   "atomic peer control families complete")
        old_profile_copy = check_archive_profile(audit, args.archive_profile_validation)
        check_atomic_validation(audit, args.atomic_validation)
        check_source_bracket(audit, args.source_bracket, args.full_gate, args.full_log)
        full = audit.read(args.full_gate)
        audit.need(full["status"] == "passed" and full["stage"] == "complete" and full["mode"] == "full", "full gate terminal pass")
        tests = full["tests"]
        audit.need(tests["run"] == 2020 and tests["failures"] == tests["errors"] == 0 and tests["skipped"] == [], "complete 2020-test gate no failures/skips")
        audit.unittest_log(args.full_log, tests["run"], driver_report=full)
        audit.need(full["powershell_syntax"] is True and full["required_probes_exit_code"] == 0 and
                   full["packaging"]["dependency_free_demo"] == "passed" and full["packaging"]["package_network_policy"] == "offline" and
                   full["packaging"]["wheel"] == "asof_target_agents-0.3.12-py3-none-any.whl", "full gate required syntax/probes/package pass")
        audit.need(full["packaging"]["build_constraints_sha256"] == sha(ROOT / "paper/release/build-constraints.txt"), "full gate build constraints unchanged")
        audit.unittest_log(args.facade_log, 138)
        check_regressions(audit)
        preserved, readback = check_preservation_records(audit, args.preservation, args.preservation_readback)
        for row in preserved["checks"]:
            if row["name"] == "retained_hash":
                path = ROOT / row["path"].replace("\\", "/")
                if path.resolve() == (ROOT / PROFILE_PATH).resolve():
                    audit.need(row["expected_sha256"] == row["actual_sha256"] == sha(old_profile_copy) == OLD_PROFILE_SHA256 and
                               sha(path) == NEW_PROFILE_SHA256, "active profile superseded by exact reviewed migration; old bytes retained",
                               path=str(path), retained_old_copy=str(old_profile_copy))
                else:
                    audit.need(sha(path) == row["expected_sha256"] == row["actual_sha256"], "old retained artifact freshly unchanged", path=str(path))
        protected = ["paper", "data/catalog", "src/asof/archive", "src/asof/demo", "tools/data/Start-DownloadBatch.ps1",
                     "tools/data/Watch-DownloadBatch.ps1", "tools/data/Get-DownloadStatus.ps1", "tools/data/Sync-DownloadCatalog.ps1"]
        changed = subprocess.check_output(["git", "diff", "--name-only", BASELINE, "--", *protected], cwd=ROOT, text=True).splitlines()
        audit.need(changed == [PROFILE_PATH], "protected tracked artifacts unchanged except exact reviewed profile migration", changed=changed)
        for relative in ("pyproject.toml", "packages/tether/pyproject.toml"):
            project = tomllib.loads((ROOT / relative).read_text())["project"]
            audit.need(VERSIONS.get(project["name"]) == project["version"], "declared distribution version matches", path=relative)
        report["wheel_sha256"] = check_installed(audit, args.installed)
        report.update(status="PASS", full_tests=tests["run"], facade_tests=138,
                      archive_profile_sha256=NEW_PROFILE_SHA256,
                      source_bracket_sha256=sha(args.source_bracket),
                      targeted_scopes="Overlapping targeted/peer scopes retained separately; counts are not summed")
    except Exception as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
    report.update(checked_at_utc=datetime.now(timezone.utc).isoformat(), inputs=audit.inputs, checks=audit.checks,
                  checker_sha256=sha(Path(__file__)))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(canonical(report) + b"\n")
    print(json.dumps(dict(status=report["status"], output=str(output), checks=len(audit.checks),
                         validation_sha256=sha(output), failure=report.get("failure")), indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
