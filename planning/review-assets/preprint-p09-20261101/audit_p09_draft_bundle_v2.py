"""Read-only positive-allowlist draft audit; HGNC content is hashed, never parsed."""
from __future__ import annotations
import ast
import base64
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import time
import zipfile

from asof_p05_replay import audit_v1 as independent

WORKSPACE = Path(__file__).resolve().parents[3]
BUNDLE = WORKSPACE / "data/cache/p09-bundle-draft-20261101T204800Z"
EXPECTED_PROTOCOL = "f451c523387eec94155b0f24b62762adffc380a73cf83401f099530efce43d1c"
POLICY_PIN = "8d88c5dca9dfbebfd7851a6e50b5d668bdedd0a6f35bd0b77aebdff01fabf6c1"
COMPARISON_PIN = "1fc123d3c368d355c1f3d66a76eeaacea9ae954c6a6fad9aa3d05390d225cce0"
HGNC_PIN = "64fcdfcdf9bc0853ec502e0e4c7d6eb12647b2ca8b0e635ea04bdb584856baf7"
EXPECTED_PIN = "30dfdeceabe87bf4db58ec78e5106cf4a73f3286d788962d21033f27312b48c8"
RESOURCES_PIN = "af588a157854752e66ff4de8393d000af727d1c15a1542fb6a01b9ba4ddb2970"


def wire(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in root.rglob("*")
            if p.is_file() and p.suffix in (".py", ".json")}


def run():
    started = time.monotonic()
    checks, findings, observations, counters = [], [], [], Counter()
    logical_bytes_hashed = 0

    def need(name, condition):
        checks.append({"check": name, "pass": bool(condition)})
        if not condition:
            findings.append(name)

    def digest(path):
        nonlocal logical_bytes_hashed
        raw = path.read_bytes()
        logical_bytes_hashed += len(raw)
        return dict(sha256=sha(raw), bytes=len(raw))

    def member(name):
        pure = PurePosixPath(name)
        need("portable_member_" + name, not pure.is_absolute() and ".." not in pure.parts and "\\" not in name and ":" not in name)
        path = BUNDLE.joinpath(*pure.parts)
        need("contained_member_" + name, path.resolve().is_relative_to(BUNDLE.resolve()) and not path.is_symlink())
        return path

    protocol_raw = (BUNDLE / "protocol.json").read_bytes()
    protocol = json.loads(protocol_raw)
    need("external_draft_protocol_bytes", sha(protocol_raw) == EXPECTED_PROTOCOL)
    need("draft_not_actual_authority", type(protocol["schema_version"]) is int and protocol["schema_version"] == 1
         and protocol["method"] == "p09.public_reconstruction_protocol.v1" and protocol["status"] == "DRAFT_ROOT_AUTHORIZATION_PENDING"
         and protocol["actual_reconstruction_authorized"] is False)
    files = protocol["files"]
    actual = {p.relative_to(BUNDLE).as_posix() for p in BUNDLE.rglob("*") if p.is_file()}
    need("exact_preparation_tree_inventory", actual == set(files) | {"protocol.json", "preparation.json", "journal.jsonl"})
    need("private_preparation_metadata_outside_public_allowlist", not {"protocol.json", "preparation.json", "journal.jsonl"} & set(files))
    need("allowlist_count_and_total", len(files) == 311 and sum(x["bytes"] for x in files.values()) == 20486521)
    for name, descriptor in files.items():
        need("descriptor_shape_" + name, set(descriptor) == {"path", "sha256", "bytes", "role"} and descriptor["path"] == name
             and type(descriptor["bytes"]) is int and descriptor["bytes"] >= 0 and re.fullmatch("[0-9a-f]{64}", descriptor["sha256"]) is not None)
        path = member(name)
        need("exact_member_bytes_" + name, digest(path) == {k: descriptor[k] for k in ("sha256", "bytes")})
        counters[descriptor["role"]] += 1
        need("excluded_asset_class_" + name, path.suffix.lower() not in (".gguf", ".safetensors", ".parquet", ".ttf", ".otf", ".woff", ".pyc", ".exe")
             and not re.search(r"(?i)(?:^|/)(?:\.env|credentials|human[_-]responses?|clinical[_-]outcomes?|gold_evidence)(?:/|$)", name))

    for key, expected in (("source_policy", POLICY_PIN), ("comparison", COMPARISON_PIN)):
        need("protocol_" + key + "_binding", protocol[key] == files[protocol[key]["path"]] and protocol[key]["sha256"] == expected)
    need("controls_descriptor_binding", protocol["controls"] == files["config/controls.json"])
    need("evaluation_roles", files["evaluation/comparison.json"]["role"] == "evaluation_only"
         and all(files["presentation-inputs/" + n]["role"] == "evaluation_only" for n in ("historical-resources.json", "expected-payloads.json"))
         and files["config/source-policy.json"]["role"] == "source_only_configuration")
    policy = load(BUNDLE / "config/source-policy.json")
    comparison = load(BUNDLE / "evaluation/comparison.json")
    originals = policy["inventory"]
    need("complete_native_inventory", len(originals) == 137 and sum(x["bytes"] for x in originals) == 2866248239
         and Counter(x["family"] for x in originals) == dict(gwas_credible_sets=100, credible_set=25, target=10, disease=1, hgnc=1))
    need("fixed_cases_and_tasks", [c["case_id"] for c in policy["cases"]] == list(independent.CASES) and set(policy["tasks"]) == set(independent.CASES))
    need("neutral_snapshot_root", policy["snapshot"]["raw_root"] is None and not policy["snapshot"]["artifacts"])
    sources = {s["source_id"]: s for s in policy["snapshot"]["sources"]}
    need("snapshot_has_all137_unique_sources", len(sources) == len(policy["snapshot"]["sources"]) == 137)
    expected_catalog = {x["dataset_id"]: ["reference" if x["family"] == "hgnc" else "agent_evidence"] for x in originals}
    need("catalog_only_original_roles", {x["dataset_id"]: x["roles"] for x in policy["catalog"]["datasets"]} == expected_catalog)
    for cid, task in policy["tasks"].items():
        need("neutral_task_only_original_bindings_" + cid, all(r["source_id"] in sources for r in task["records"])
             and all(task["scope"][key] is None for key in ("action", "modality", "tissue"))
             and all(j["cardinality"] == "one_to_many" and j["left_field"] == j["right_field"] == "studyLocusId" for j in task["joins"]))
    receipt_paths = set()
    for item in originals:
        sid = item["source_id"]
        expected_role = "reference" if item["family"] == "hgnc" else "agent_evidence"
        receipt_name = "included-originals/" + item["receipt"]["relative_path"]
        receipt_paths.add(receipt_name)
        need("receipt_allowlist_" + sid, receipt_name in files and files[receipt_name]["role"] == "exact_transport_receipt"
             and {k: files[receipt_name][k] for k in ("sha256", "bytes")} == {k: item["receipt"][k] for k in ("sha256", "bytes")})
        receipt = load(member(receipt_name))
        need("receipt_source_identity_" + sid, receipt["status"] == "completed" and all(receipt[k] == item[k] for k in ("dataset_id", "release_id", "sha256", "bytes"))
             and receipt["url"] == item["source_url"] and receipt["relative_path"].replace("\\", "/") == item["relative_path"]
             and independent.utc(receipt["completed_at_utc"]) <= independent.utc(policy["cutoff"]))
        node = sources[sid]
        need("original_source_graph_" + sid, item["role"] == node["role"] == expected_role and not node["parents"] and node["computed_at"] is None
             and node["method_id"] is None and node["method_version"] is None
             and all(node[k] == item[k] for k in ("dataset_id", "release_id", "sha256")) and node["path"] == item["relative_path"]
             and node["receipt_path"] == item["receipt"]["relative_path"] and node["receipt_sha256"] == item["receipt"]["sha256"])
    hgnc, = [i for i in originals if i["family"] == "hgnc"]
    hgnc_name = "included-originals/" + hgnc["relative_path"]
    need("included_originals_are_only_receipts_and_exact_hgnc", {n for n in files if n.startswith("included-originals/")} == receipt_paths | {hgnc_name})
    need("hgnc_hash_only_exact_approved_original", files[hgnc_name]["sha256"] == hgnc["sha256"] == HGNC_PIN
         and files[hgnc_name]["bytes"] == hgnc["bytes"] == 16973159 and files[hgnc_name]["role"] == "reference_original_CC0")
    need("external_originals_not_bundled", protocol["dataset_payloads"] == dict(open_targets_external_files=136, hgnc_included=True))
    need("comparison_remains_evaluator_only", comparison["role"] == "evaluation_only" and comparison["agent_visible"] is False
         and comparison["source_policy_sha256"] == POLICY_PIN and comparison["scientific_validation"] == "not_established"
         and len(comparison["outputs"]) == 38 and len(comparison["decisions"]) == 90)

    for label, prefix, current in (("core", "source/core/src/asof/", WORKSPACE / "src/asof"),
                                   ("replay", "source/replay/src/asof_p05_replay/", WORKSPACE / "paper/release/code/src/asof_p05_replay")):
        bundle_pins = {name[len(prefix):]: d["sha256"] for name, d in files.items() if name.startswith(prefix)}
        need(label + "_source_inventory_complete", bundle_pins == protocol[label + "_files"] == inventory(current)
             and (len(bundle_pins) == 92 if label == "core" else len(bundle_pins) == 8))
    replay_source = WORKSPACE / "paper/release/code"
    current_tests = {p.name: sha(p.read_bytes()) for p in (replay_source / "tests").glob("*.py")}
    bundled_tests = {name.removeprefix("source/replay/tests/"): d["sha256"] for name, d in files.items() if name.startswith("source/replay/tests/")}
    need("reviewed_all4_replay_tests", len(bundled_tests) == 4 and bundled_tests == current_tests)

    wheel_reports = {}
    for name in [n for n in files if n.endswith(".whl")]:
        package = "asof_p05_replay" if "asof_p05_replay" in name else "asof"
        label = "replay" if package == "asof_p05_replay" else "core"
        with zipfile.ZipFile(member(name)) as archive:
            names = archive.namelist()
            need(label + "_wheel_unique_members", len(names) == len(set(names)))
            payloads = {n[len(package) + 1:]: sha(archive.read(n)) for n in names if n.startswith(package + "/") and n.endswith((".py", ".json"))}
            need(label + "_wheel_exact_package", payloads == protocol[label + "_files"])
            dist_info = ("asof_p05_replay-0.1.0.dist-info/" if label == "replay" else "asof_target_agents-0.3.11.dist-info/")
            metadata_names = {dist_info + suffix for suffix in ("licenses/LICENSE", "METADATA", "WHEEL", "entry_points.txt", "top_level.txt", "RECORD")}
            need(label + "_wheel_exact_full_member_inventory", set(names) == {package + "/" + n for n in payloads} | metadata_names
                 and not any((i.external_attr >> 16) & 0o170000 == 0o120000 for i in archive.infolist()))
            record_name, = [n for n in names if n.endswith(".dist-info/RECORD")]
            records = list(csv.reader(io.StringIO(archive.read(record_name).decode())))
            need(label + "_wheel_record_complete", {r[0] for r in records} == set(names) and len(records) == len(names))
            for path, encoded, byte_count in records:
                if path == record_name:
                    need(label + "_wheel_record_self_empty", encoded == byte_count == "")
                    continue
                raw = archive.read(path)
                need(label + "_wheel_record_" + path, encoded == "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode() and int(byte_count) == len(raw))
            need(label + "_wheel_only_project_payload_and_dist_info", all(n.startswith(package + "/") or ".dist-info/" in n for n in names))
            licence, = [n for n in names if n.endswith("/licenses/LICENSE")]
            need(label + "_wheel_license", archive.read(licence) == (BUNDLE / ("source/" + label + "/LICENSE")).read_bytes())
            wheel_reports[label] = dict(path=name, package_payloads=len(payloads), all_members=len(names), record_entries=len(records), sha256=files[name]["sha256"])

    controls = load(BUNDLE / "config/controls.json")
    need("all14_control_descriptors", list(controls) == list(independent.SCENARIOS))
    for key, spec in controls.items():
        case, documents, _, _, _, evaluation, anchors, catalog = independent._control_source_documents(key)
        groups = independent.json_groups(case, documents, declared_subset=key == "F04")
        expected = dict(scenario_id=key, case=case, task=independent.expected_task(case, groups), snapshot=independent.encode(evaluation),
                        catalog=catalog, original_source_anchors=anchors, originals_root="fictional/" + key + "/originals")
        need("independent_fixed_control_descriptor_" + key, wire(spec) == wire(expected))

    expected = load(BUNDLE / "presentation-inputs/expected-payloads.json")
    presentation = load(BUNDLE / "paper/results/ARTIFACTS.json")
    need("presentation_expected_pin", files["presentation-inputs/expected-payloads.json"]["sha256"] == EXPECTED_PIN)
    need("presentation_resources_pin", files["presentation-inputs/historical-resources.json"]["sha256"] == RESOURCES_PIN)
    need("exact37_presentation_commitments", len(expected["payloads"]) == 37)
    for name, anchor in expected["payloads"].items():
        descriptor = files["paper/results/" + name]
        need("historical_presentation_payload_" + name, descriptor["role"] == "aggregated_technical_results"
             and {k: descriptor[k] for k in ("sha256", "bytes")} == {k: anchor[k] for k in ("sha256", "bytes")})
    need("portable_presentation_has39_files", {n.removeprefix("paper/results/") for n in files if n.startswith("paper/results/")} == set(expected["payloads"]) | {"README.md", "ARTIFACTS.json"})
    need("new_presentation_scope", presentation["status"] == "PASS_PORTABLE_HISTORICAL_PAYLOAD_REPRODUCTION"
         and presentation["original_payload_reads"] == presentation["expected_reference_reads"] == presentation["raw_output_reads"] == 0)
    for key, name in (("comparison", "evaluation/comparison.json"), ("source_policy", "config/source-policy.json"),
                      ("historical_resources", "presentation-inputs/historical-resources.json"), ("expected_payloads", "presentation-inputs/expected-payloads.json")):
        need("presentation_input_" + key, all(presentation["inputs"][key][k] == files[name][k] for k in ("sha256", "bytes")))
    for name, anchor in presentation["tables_and_outputs"].items():
        need("portable_presentation_manifest_" + name, all(anchor[k] == files["paper/results/" + name][k] for k in ("sha256", "bytes")))

    privacy_findings = []
    text_suffixes = {".py", ".json", ".md", ".toml", ".lock", ".txt", ".csv", ".svg", ".bib"}
    owner_pattern = re.compile(r"(?i)(?:zzric|[A-Z]:[\\/]Users[\\/]|[A-Z]:[\\/]Projects(?:_data)?[\\/]|/Users/|/home/|drug_target_agents_data)")
    secret_pattern = re.compile(r"(?:sk-[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)")
    json_sensitive_keys = {"password", "authorization", "access_token", "secret", "api_key"}
    def inspect_json(node, name):
        if isinstance(node, dict):
            if json_sensitive_keys & {str(k).lower() for k in node}:
                privacy_findings.append(dict(path=name, kind="secret_like_json_key"))
            for v in node.values(): inspect_json(v, name)
        elif isinstance(node, list):
            for v in node: inspect_json(v, name)
    for name in files:
        path = member(name)
        if name == hgnc_name or path.suffix not in text_suffixes and path.name != "LICENSE":
            continue
        text = path.read_text(encoding="utf-8-sig")
        # Code may contain generic fictional machine-path predicates. Only actual
        # owner/project-root forms are flagged, without retaining matched text.
        if owner_pattern.search(text.replace("\\\\", "\\")):
            privacy_findings.append(dict(path=name, kind="owner_or_private_machine_path"))
        if secret_pattern.search(text):
            privacy_findings.append(dict(path=name, kind="credential_pattern"))
        if path.suffix == ".json" and not name.startswith("source/"):
            inspect_json(json.loads(text), name)
    need("privacy_text_and_metadata_scan", not privacy_findings)

    readme = (BUNDLE / "README.md").read_text(encoding="utf-8")
    need("readme_corrected_qualification_scope", "qualification target" in readme and "fresh exact-byte reacquisition of the 136 external originals has not been tested" in readme.lower())
    need("readme_installed_command_closure", all(flag in readme for flag in ("--protocol-sha256", "--bundle-root", "--originals-root", "--reconstruction-root"))
         and "-I -m asof_p05_replay reconstruct" in readme and "-I -m asof_p05_replay audit" in readme
         and "unittest discover -s" in readme and "Setuptools" not in readme)
    need("readme_installs_fail_closed", readme.count("if ($LASTEXITCODE -ne 0)") >= 6)
    need("readme_no_original_archive_or_science_claim", "does\nnot byte-verify unavailable old private journals" in readme and "Scientific validation remains unestablished" in readme)

    preparation = load(BUNDLE / "preparation.json")
    need("preparation_exact_draft_summary", preparation["draft_protocol_sha256"] == EXPECTED_PROTOCOL and preparation["members"] == len(files)
         and preparation["member_bytes"] == sum(x["bytes"] for x in files.values()) and preparation["status"] == "PREPARED_DRAFT_NOT_EXECUTED"
         and set(preparation["origins"]) == set(files) and preparation["root_READY_required"] is True)
    events = [json.loads(line) for line in (BUNDLE / "journal.jsonl").read_bytes().splitlines()]
    previous = None
    for number, event in enumerate(events):
        need("preparation_journal_" + str(number), event["sequence"] == number and event["previous_sha256"] == previous
             and event["sha256"] == sha(wire({k: v for k, v in event.items() if k != "sha256"})))
        previous = event["sha256"]
    need("preparation_terminal_success", events[0]["event"] == "build_reserved" and events[-1]["event"] == "build_completed"
         and events[-1]["details"] == dict(draft_protocol_sha256=EXPECTED_PROTOCOL, actual_reconstruction=False)
         and not any("failed" in x["event"] or "interrupted" in x["event"] for x in events))
    observations.extend(["Date-like directory suffix is a label; preparation created_at_utc is authoritative.",
        "Whole draft directory is not a runtime bundle: preparation.json and journal.jsonl must remain excluded. Copy only protocol.files, then add separately frozen READY protocol.",
        "HGNC bytes were hashed only. No provider payload was parsed; no originals outside this bundle were read.",
        "PDF/PNG binaries were hash-checked against pinned presentation commitments; text privacy scan covers public textual members, not a new PDF visual or font-rights review.",
        "Draft false authorization must be replaced only by root-reviewed exact READY authority; this audit authorizes no reconstruction."])
    report = dict(schema="p09.independent_draft_bundle_audit.v1", method="p09.positive_allowlist_metadata_audit.v1",
        status="PASS_DRAFT_METADATA_REVIEW" if not findings else "FAIL_DRAFT_METADATA_REVIEW", bundle_path=str(BUNDLE),
        protocol_sha256=EXPECTED_PROTOCOL, checks=checks, check_count=len(checks), unresolved_findings=findings,
        privacy_findings=privacy_findings, members=len(files), member_bytes=sum(x["bytes"] for x in files.values()),
        roles=dict(counters), wheels=wheel_reports, observations=observations,
        resources=dict(wall_seconds=time.monotonic()-started, logical_member_bytes_hashed=logical_bytes_hashed),
        provider_payloads_parsed=0, originals_outside_bundle_read=0, actual_reconstruction=False,
        scientific_validation="not_established", release_publication_authorized=False)
    return report


if __name__ == "__main__":
    report = run()
    target = Path(__file__).with_name("DRAFT-BUNDLE-AUDIT-v2.json")
    with target.open("xb") as stream:
        stream.write(json.dumps(report, indent=2, ensure_ascii=False).encode()+b"\n")
    print(json.dumps({k: report[k] for k in ("status", "check_count", "unresolved_findings", "privacy_findings", "members", "member_bytes", "resources")}, indent=2))
