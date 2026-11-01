"""Assemble NON-AUTHORIZING P05 READY metadata; never load native fact values.

Only the dedicated frozen runner can execute a separately root-authorized READY.
This helper never creates that file, invokes execution/source replay or parses a
native packet/reference. Actual references.json is streamed only into SHA-256.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time

WORKSPACE = Path(__file__).resolve().parents[2]
ASSETS = WORKSPACE / "planning/review-assets/preprint-p05-20261031"
OUTPUT = ASSETS / "EXPERIMENT-READY-DRAFT-v1.json"
RUNNER = WORKSPACE / "tools/science/run_source_validation_experiment.py"
RUNNER_SHA256 = "9a63d63eacbfb71712376862d38d77f72dd4edf616521073ad287e53eb275bf8"
PEER_REVIEW_SHA256 = "70c21a9c33dba3bf397c3f44cd1760c1d1a325ce831175a4e68245b4f579c012"
REFERENCE_FINGERPRINT = "f29444743dfa2acc9cb0a555d5f39ce866a5da04ec919280cb17afe2f82ab13a"
PUBLIC_METADATA = (
    "INPUT-AUDIT-v1.json", "REFERENCE-AUDIT-v1.json", "REFERENCE-ACCEPTANCE-v1.json",
    "REGISTER-MANIFEST-v1.json", "EXPERIMENT-NATIVE-BINDINGS-v1.json", "EXPERIMENT-INDEPENDENT-REVIEW-v1.json",
)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_sha(value):
    need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, "Explicit lowercase SHA-256 required")
    return value


def opaque_hash(path, *, maximum=64 * 1024**2):
    """Return hash/length only. Never return or parse reference bytes."""
    path = Path(path)
    size = path.stat().st_size
    need(size <= maximum, "Opaque hash input exceeds frozen metadata-file bound")
    digest, seen = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            seen += len(block)
            need(seen <= maximum, "Opaque hash bound exceeded")
            digest.update(block)
    need(seen == size == path.stat().st_size, "Opaque hash input size changed")
    return dict(sha256=digest.hexdigest(), bytes=seen)


def frozen_runner():
    need(opaque_hash(RUNNER)["sha256"] == RUNNER_SHA256, "Frozen runner changed; helper cannot update or import another version")
    spec = importlib.util.spec_from_file_location("p05_frozen_runner_ready_metadata", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata(path, *, allowed, runtime, expected_sha256=None):
    path = Path(path)
    need(path in set(allowed), "JSON path is outside the explicit metadata allowlist")
    need(path.name != "references.json" and path.parent.name != "packets", "Native fact files cannot be parsed by READY preparation")
    runtime.checked_path(WORKSPACE, path.relative_to(WORKSPACE).as_posix())
    raw = runtime.read_file(path, time.monotonic() + 60, 16 * 1024**2)
    if expected_sha256 is not None:
        need(sha_bytes(raw) == exact_sha(expected_sha256), "Explicit metadata SHA differs")
    return runtime.parse_json(raw), dict(path=str(path), sha256=sha_bytes(raw), bytes=len(raw))


def audit_ok(document):
    need(type(document.get("status")) is str and document["status"].startswith("PASS") and
         not document.get("issues") and not document.get("findings"), "Required public audit/review is not PASS")


def make_ready_payload(*, runtime_metadata, native_cases, reference_manifest_fingerprint,
                       reference_ready_sha256, inputs, fictional_references, preparation_metadata):
    """Pure RAM-only proposal. The helper NEVER serializes these authority flags.

    The root may independently review this structure and choose its own final
    authorization. Calling this function grants no execution authority.
    """
    return dict(schema_version=1, status="READY", frozen_by="root", actual_execution_authorized=True,
        scope=runtime_metadata["method"], plan_sha256=runtime_metadata["plan_sha256"],
        design_sha256=runtime_metadata["design_sha256"], code_sha256=deepcopy(runtime_metadata["code_sha256"]),
        environment=deepcopy(runtime_metadata["environment"]), limits=deepcopy(runtime_metadata["limits"]),
        cutoff=runtime_metadata["cutoff"], schedule=deepcopy(runtime_metadata["schedule"]),
        extra_code_sha256=deepcopy(runtime_metadata["extra_code_sha256"]),
        analysis_code_sha256=runtime_metadata["analysis_code_sha256"], approved_raw_root=runtime_metadata["approved_raw_root"],
        native_cases=deepcopy(native_cases), reference_manifest_fingerprint=reference_manifest_fingerprint,
        reference_ready_sha256=reference_ready_sha256, inputs=deepcopy(inputs),
        fictional_references=deepcopy(fictional_references), preparation_metadata=deepcopy(preparation_metadata))


def non_authorizing_draft(proposal):
    draft = deepcopy(proposal)
    draft.update(status="DRAFT_ROOT_AUTHORIZATION_PENDING", frozen_by="NOT_ROOT", actual_execution_authorized=False)
    return draft


def prepare(*, fixture_manifest, fixture_sha256, qualification_ledger, qualification_sha256,
            auditor_sha256, auditor_test_sha256, output=OUTPUT):
    output = Path(output).absolute()
    need(output.parent == ASSETS and re.fullmatch(r"EXPERIMENT-READY-DRAFT-v[1-9]\d*\.json", output.name) is not None and not output.exists(),
         "Only a new explicit EXPERIMENT-READY-DRAFT-vN.json leaf may be written; no overwrite or actual READY")
    runtime = frozen_runner()
    fixture_manifest, qualification_ledger = Path(fixture_manifest).absolute(), Path(qualification_ledger).absolute()
    need(fixture_manifest.is_relative_to(WORKSPACE / "data/cache") and fixture_manifest.name == "manifest.json" and
         qualification_ledger.is_relative_to(WORKSPACE / "data/cache") and qualification_ledger.name == "ledger.json",
         "Only explicit fictional cache manifest/qualification paths are permitted")
    allowed = [ASSETS / name for name in PUBLIC_METADATA] + [fixture_manifest, qualification_ledger]
    documents, proofs = {}, {}
    with runtime.stable_files(allowed + runtime.code_paths(), deadline=time.monotonic() + 120):
        for name in PUBLIC_METADATA:
            documents[name], proofs[name] = metadata(ASSETS / name, allowed=allowed, runtime=runtime,
                expected_sha256=PEER_REVIEW_SHA256 if name == "EXPERIMENT-INDEPENDENT-REVIEW-v1.json" else None)
        fixtures, fixture_proof = metadata(fixture_manifest, allowed=allowed, runtime=runtime, expected_sha256=fixture_sha256)
        qualification, qualification_proof = metadata(qualification_ledger, allowed=allowed, runtime=runtime, expected_sha256=qualification_sha256)
        input_audit, reference_audit = documents["INPUT-AUDIT-v1.json"], documents["REFERENCE-AUDIT-v1.json"]
        acceptance = documents["REFERENCE-ACCEPTANCE-v1.json"]
        register, bindings = documents["REGISTER-MANIFEST-v1.json"], documents["EXPERIMENT-NATIVE-BINDINGS-v1.json"]
        peer = documents["EXPERIMENT-INDEPENDENT-REVIEW-v1.json"]
        for report in (input_audit, reference_audit, peer, qualification):
            audit_ok(report)
        need(input_audit.get("raw_scientific_values_in_report") is False, "Input audit must remain value-free metadata")
        need(reference_audit.get("raw_scientific_values_or_expected_answers_written") is False,
             "Reference audit must remain value-free metadata")
        need(peer["reviewed_code_sha256"] == RUNNER_SHA256, "Peer review does not cover frozen runner")
        need(bindings.get("status") == "EVALUATOR_PROTOCOL_BINDINGS_METADATA_ONLY" and bindings.get("expected_fact_values_included") is False and
             bindings.get("role") == "evaluation_only" and bindings.get("agent_visible") is False, "Only root-projected value-free native bindings are allowed")
        need(register["status"] == "FROZEN" and register["case_ids"] == list(runtime.CASES) and register["other_exposure"] == "UNKNOWN" and
             register["independent_studies_established"] is False, "Public original-only register is unqualified")
        registered = {x["case_id"]: x for x in register["native_cases"]}
        need(list(bindings["native_cases"]) == list(runtime.CASES) == list(registered), "Native metadata frame differs")
        for case_id, item in bindings["native_cases"].items():
            need(item["disposition"] == "compiled" and all(item[name] == registered[case_id][name] for name in
                ("task_sha256", "requested_facts", "measurement_answerable_facts", "measurement_answerable_groups")),
                "Root projected native counts/task differ from independent source-only register")
        need(bindings["reference_manifest_fingerprint"] == REFERENCE_FINGERPRINT == acceptance["pins"]["manifest_sha256"] ==
             reference_audit["pins"]["manifest_sha256"], "Independent canonical manifest fingerprints differ")
        need(bindings["reference_ready_sha256"] == acceptance["pins"]["ready_sha256"] == reference_audit["pins"]["ready_sha256"], "Retained reference READY differs")
        need(acceptance["run"] == reference_audit["run"] and bindings["source_parent"] == acceptance["run"] + "/references.json" and
             re.fullmatch(r"data/benchmark/gold_evidence/preprint-p05-references-\d{8}T\d{6}Z", acceptance["run"]), "Unexpected reference metadata path")
        need(re.fullmatch(r"data/derived/preprint-p05-source-inputs-\d{8}T\d{6}Z", input_audit["run"]), "Unexpected source-input metadata root")
        input_seal_path = runtime.checked_path(WORKSPACE, input_audit["run"] + "/seal.json")
        input_seal, input_seal_proof = metadata(input_seal_path, allowed=allowed + [input_seal_path], runtime=runtime,
            expected_sha256=input_audit["terminal"]["seal_sha256"])
        need(input_seal["status"] == "completed_source_only_stage2_inputs" and input_seal["packet_count"] == 12 and
             input_seal["blocked_case_count"] == 0, "Input metadata seal differs")
        packet_pins = {x["path"]: x["sha256"] for x in input_seal["artifacts"] if x["path"].startswith("packets/")}
        need(set(packet_pins) == {"packets/" + key + ".json" for key in runtime.CASES} and all(
            packet_pins["packets/" + key + ".json"] == item["packet_sha256"] for key, item in bindings["native_cases"].items()),
            "Projected packet hashes differ from source-input seal metadata")
        # Actual native reference bytes enter a one-way hash only. They are never
        # passed to parse_json/metadata or retained/copied by this helper.
        reference_path = runtime.checked_path(WORKSPACE, bindings["source_parent"])
        with runtime.stable_files([reference_path], deadline=time.monotonic() + 60):
            reference_byte_proof = opaque_hash(reference_path)
        need(fixtures["status"] == "FROZEN_FICTIONAL_SOURCES_ONLY_NOT_STUDY_RESULTS" and fixtures["candidate_outputs_created"] is False and
             fixtures["code_sha256"] == runtime.code_pins() and tuple(fixtures["scenarios"]) == runtime.SCENARIOS, "Wholly fictional source freeze differs")
        need(qualification.get("qualification_only") is True and qualification.get("native_outputs_executed") == 0 and
             qualification.get("scenario_count") == 14 and qualification.get("reviewed_code_sha256") == RUNNER_SHA256 and
             qualification.get("fixture_manifest_sha256") == fixture_proof["sha256"] and qualification.get("failure") is None,
             "Qualification is not the zero-native-output fictional test")
        need(set(qualification["fictional_references"]) == set(runtime.SCENARIOS) and len(qualification["output_cells"]) == 38 and
             len(qualification["decision_cells"]) == 90 and all(x["terminal"] == "unexecuted" and x["raw_path"] is None
             for x in qualification["output_cells"] if x["stratum"] == "native"), "Fictional qualification schedule/native isolation differs")
        need(not (qualification_ledger.parent / "failure-seal.json").exists() and
             not (qualification_ledger.parent / "emergency-failure-seal.json").exists(), "Qualification lifecycle failure present")
        qualification_seal_path = qualification_ledger.parent / "seal.json"
        qualification_seal, _ = metadata(qualification_seal_path, allowed=[qualification_seal_path], runtime=runtime)
        chain = runtime.read_chain(qualification_ledger.parent / "journal.jsonl")
        need(qualification_seal["status"] == "PASS_FICTIONAL_QUALIFICATION_ONLY" and qualification_seal["intended_ledger_sha256"] == qualification_proof["sha256"] and
             chain[-1]["event"] == "experiment_completed" and chain[-1]["details"]["seal_sha256"] == runtime.fingerprint(qualification_seal) and
             chain[-1]["details"]["ledger_sha256"] == qualification_proof["sha256"] and
             qualification_seal["journal_prefix_sha256"] == chain[-2]["sha256"],
             "Fictional qualification seal/journal differs")
        extras = {name: opaque_hash(runtime.checked_path(WORKSPACE, name))["sha256"] for name in runtime.EXTRA_CODE}
        need(extras[runtime.ANALYSIS_CODE] == peer["analysis_preparation"]["module_sha256"] and
             extras["planning/review-assets/preprint-p05-20261031/test_analyze_source_validation_experiment.py"] == peer["analysis_preparation"]["test_sha256"],
             "Analyzer/test differ from the public preparation review metadata")
        need(extras["tools/science/audit_source_validation_experiment.py"] == exact_sha(auditor_sha256) and
             extras["planning/review-assets/preprint-p05-20261031/test_audit_source_validation_experiment.py"] == exact_sha(auditor_test_sha256),
             "Explicit final auditor/test pins differ from current code")
        inputs = dict(
            input_seal={k: input_seal_proof[k] for k in ("path", "sha256")},
            input_audit=dict(path=proofs["INPUT-AUDIT-v1.json"]["path"], sha256=proofs["INPUT-AUDIT-v1.json"]["sha256"],
                expected_fields={"terminal.seal_sha256": input_seal_proof["sha256"], "run": input_audit["run"]}),
            reference_manifest=dict(path=str(reference_path), sha256=reference_byte_proof["sha256"]),
            reference_seal=dict(path=str(reference_path.parent / "seal.json"), sha256=acceptance["pins"]["seal_sha256"]),
            reference_audit=dict(path=proofs["REFERENCE-AUDIT-v1.json"]["path"], sha256=proofs["REFERENCE-AUDIT-v1.json"]["sha256"],
                expected_fields={"pins.manifest_sha256": REFERENCE_FINGERPRINT, "pins.ready_sha256": bindings["reference_ready_sha256"], "run": reference_audit["run"]}),
            fixture_manifest={k: fixture_proof[k] for k in ("path", "sha256")},
            exposure_dependence={k: proofs["REGISTER-MANIFEST-v1.json"][k] for k in ("path", "sha256")},
            peer_review=dict(path=proofs["EXPERIMENT-INDEPENDENT-REVIEW-v1.json"]["path"], sha256=proofs["EXPERIMENT-INDEPENDENT-REVIEW-v1.json"]["sha256"],
                expected_fields={"reviewed_code_sha256": RUNNER_SHA256}),
            fictional_qualification=dict(path=str(qualification_ledger), sha256=qualification_proof["sha256"], expected_fields={
                "reviewed_code_sha256": RUNNER_SHA256, "fixture_manifest_sha256": fixture_proof["sha256"],
                "native_outputs_executed": 0, "qualification_only": True, "scenario_count": 14}))
        runtime_metadata = dict(method=runtime.METHOD, plan_sha256=opaque_hash(runtime.PLAN_PATH)["sha256"],
            design_sha256=opaque_hash(runtime.DESIGN_PATH)["sha256"], code_sha256=runtime.code_pins(), environment=runtime.stage1.environment(),
            limits=runtime.LIMITS, cutoff=runtime.CUTOFF, schedule=runtime.schedule(), extra_code_sha256=extras,
            analysis_code_sha256=extras[runtime.ANALYSIS_CODE], approved_raw_root=str(runtime.reference_builder.RAW_ROOT))
        preparation = dict(method="p05.metadata_only_ready_preparation.v1", status="METADATA_ONLY_NOT_ROOT_AUTHORIZATION",
            helper_sha256=opaque_hash(Path(__file__).resolve())["sha256"], public_metadata=proofs,
            native_packet_values_read=0, native_reference_values_parsed=0, original_source_values_read=0,
            reference_manifest_byte_hash_only=reference_byte_proof, models=0, network_calls=0, new_downloads=0,
            provider_spending_usd=0, scientific_validation="not_established")
        proposal = make_ready_payload(runtime_metadata=runtime_metadata, native_cases=bindings["native_cases"],
            reference_manifest_fingerprint=REFERENCE_FINGERPRINT, reference_ready_sha256=bindings["reference_ready_sha256"],
            inputs=inputs, fictional_references=qualification["fictional_references"], preparation_metadata=preparation)
        # This API validates metadata/authority structure only. It does not load
        # native source/reference values, replay sources or execute any cell.
        plan_raw = runtime.PLAN_PATH.read_bytes()
        proposal_raw = runtime.canonical(proposal) + b"\n"
        runtime.validate_freeze(plan_raw, proposal_raw, sha_bytes(proposal_raw))
        draft = non_authorizing_draft(proposal)
        draft_raw = runtime.canonical(draft) + b"\n"
        try:
            runtime.validate_freeze(plan_raw, draft_raw, sha_bytes(draft_raw))
        except runtime.ContractError as error:
            need(str(error) == "Separate root READY required", "DRAFT failed for an unexpected reason")
        else:
            raise ValueError("NON-AUTHORIZING DRAFT unexpectedly passed runtime gate")
        runtime.publish_bytes(output, draft_raw)
    need(opaque_hash(RUNNER)["sha256"] == RUNNER_SHA256, "Frozen runner changed during preparation")
    return dict(status=draft["status"], actual_execution_authorized=False, frozen_by="NOT_ROOT", output=str(output),
        draft_sha256=sha_bytes(draft_raw), native_units=12, native_requested_facts=sum(x["requested_facts"] for x in draft["native_cases"].values()),
        native_answerable_measurement_facts=sum(x["measurement_answerable_facts"] for x in draft["native_cases"].values()),
        output_cells=38, decisions=90, reference_facts_parsed=0, native_packets_opened=0, original_values_read=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-manifest", required=True, type=Path)
    parser.add_argument("--fixture-sha256", required=True)
    parser.add_argument("--qualification-ledger", required=True, type=Path)
    parser.add_argument("--qualification-sha256", required=True)
    parser.add_argument("--auditor-sha256", required=True)
    parser.add_argument("--auditor-test-sha256", required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT, help="New ASSETS/EXPERIMENT-READY-DRAFT-vN.json only; never overwrite or actual READY")
    args = parser.parse_args(argv)
    print(json.dumps(prepare(fixture_manifest=args.fixture_manifest, fixture_sha256=args.fixture_sha256,
        qualification_ledger=args.qualification_ledger, qualification_sha256=args.qualification_sha256,
        auditor_sha256=args.auditor_sha256, auditor_test_sha256=args.auditor_test_sha256, output=args.output), sort_keys=True))


if __name__ == "__main__":
    main()
