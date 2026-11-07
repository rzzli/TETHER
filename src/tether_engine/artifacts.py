"""Reviewable run artifacts, trace verification and integrity receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import platform
from importlib import metadata

from . import __version__
from .chrono import EvidenceStore, admit_snapshot, required_source_proofs
from .scorer import ScorerArtifact
from .serde import (ContractError, MAX_LEDGER_JSON_BYTES, canonical, decode, encode, fingerprint,
                    read_json, read_ledger_json, safe_child, sha256_file, write_json)
from .contracts import Case, Category, Claim, Snapshot
from .features import FeatureVector
from .scorer import Prediction
from .semantics import check_execution, check_semantics
from .journal import RunJournal, read_chain
from .workflow import RunResult


LEGACY_RUN_FILES = ("run.json", "inputs.json", "ledger.json", "features.json", "prediction.json",
             "trace.jsonl", "dossier.md")
RUN_FILES = LEGACY_RUN_FILES + ("journal.jsonl",)


def _check_source_inventory(snapshot, case, root, policy, proofs):
    expected = required_source_proofs(snapshot, case, root, policy)
    actual = {item["artifact_id"]: item for item in proofs}
    if (len(actual) != len(proofs) or
            fingerprint(actual) != fingerprint({item["artifact_id"]: item for item in expected})):
        raise ContractError("Semantic source proof inventory differs from eligible artifact/ancestor closure")


def dossier(result: RunResult, store: EvidenceStore) -> str:
    case, prediction = result.case, result.prediction
    lines = [f"# TETHER dossier: {case.case_id}", "",
             f"Target: {case.hypothesis.target_id}; indication: {case.hypothesis.indication_id}.",
             f"Intended action: {case.hypothesis.intended_action}; modality: {case.hypothesis.modality}; "
             f"tissue: {case.hypothesis.tissue or 'unspecified'}.",
             f"Origin: {case.origin}; profile: {result.profile}; task: {case.task}.",
             f"Workflow: {result.status}; backend: {result.backend_id}.", ""]
    if store.snapshot.coverage.get("interpretation_scope") == "resource_annotation_only":
        lines += ["## Evidence relevance and hypothesis limits", "",
                  "Resource annotation support: source-linked target/disease records are reproduced. "
                  "Therapeutic relevance: not assessed for the intended action, modality, population or regimen. "
                  "A literature mention, genetic association or provider score does not establish intervention efficacy.", "",
                  "Clinical outcomes and reviewer judgments remain evaluator-only. No disease subtype was inferred "
                  "and this hypothesis has not been refined.", "",
                  "| Unresolved qualification | Value |", "| --- | --- |"]
        for name, qualification in store.snapshot.coverage.get("hypothesis_qualification", {}).items():
            lines.append(f"| {name.replace('_', ' ')} | {qualification['value'] or 'unspecified'} |")
        lines.append("")
    if prediction.synthetic:
        lines += ["**Synthetic demonstration: the weights and observations are fixtures. "
                  "This number is not a scientific prediction.**", ""]
    if prediction.probability is None:
        lines += [f"Probability withheld: {prediction.reason}.", ""]
    else:
        lines += [f"Probability of {prediction.endpoint} within {prediction.horizon_months} months: "
                  f"{prediction.probability:.4f}.",
                  f"Scorer: {prediction.scorer_id}; calibration: {prediction.calibration}; "
                  f"model-feature coverage: {prediction.feature_coverage:.1%}.", ""]
    if prediction.contributions:
        lines += ["## Frozen scorer contributions", "",
                  "Contributions are in log odds and describe the predictor, not biological causality.", "",
                  "| Feature | Value | Coefficient | Contribution | Imputed |",
                  "| --- | ---: | ---: | ---: | --- |"]
        for name, item in prediction.contributions.items():
            lines.append(f"| {name} | {item.value:.4g} | {item.coefficient:.4g} | "
                         f"{item.log_odds:.4g} | {item.imputed} |")
        lines += [f"\nIntercept: {prediction.intercept:.4g}.", ""]
    lines += ["## Grounded claims", "",
              "Statements below are copied from the approved normalized records. Citation "
              "grounding does not establish that a source interpretation or method is scientifically correct.", ""]
    for claim in result.claims:
        record, citation = claim.evidence.observation, claim.evidence.citation
        lines += [f"### {claim.claim_id} ({claim.specialist.value})", "",
                  "> " + record.statement.replace("\n", "\n> "), "",
                  f"Interpretation: {record.polarity.value}; direction: {record.mechanism_direction}. "
                  f"Dependency group: {record.dependency_group}; declared QC: {record.method.qc_status}.",
                  f"Source: {citation.dataset_id}/{citation.release_id}; "
                  f"artifact {citation.artifact_id}; observation {record.observation_id}.",
                  f"SHA-256: `{citation.artifact_sha256}`.", ""]
        if record.method.limitations:
            lines += ["Limitations: " + "; ".join(record.method.limitations) + ".", ""]
        if record.source_metrics:
            lines += ["Provider metrics (descriptive): `" + canonical(record.source_metrics).decode("utf-8") + "`.", ""]
        if record.missingness:
            lines += ["Unknown fields: " + "; ".join(f"{key}: {value}" for key, value in record.missingness.items()) + ".", ""]
    if not result.claims:
        lines += ["No approved observed claims were selected.", ""]
    lines += ["## Coverage and exclusions", "",
              "| Specialist | Run status | Available | Selected |",
              "| --- | --- | ---: | ---: |"]
    for category, coverage in result.coverage.items():
        lines.append(f"| {category} | {coverage['status']} | {coverage['available_observations']} | "
                     f"{coverage['selected_observations']} |")
    for category, coverage in result.coverage.items():
        for record in coverage["nonobserved"]:
            lines.append(f"\n{category}: {record['status']} ({record['observation_id']}): {record['reason']}")
    for exclusion in store.exclusions:
        lines.append(f"\nExcluded {exclusion.level} {exclusion.item_id}: {exclusion.reason}.")
    if store.snapshot.coverage:
        lines += ["", "Source coverage: `" + canonical(store.snapshot.coverage).decode("utf-8") + "`."]
    lines += ["", f"Calls: {result.calls}; accounted cost: ${result.usage.cost_usd:.4f}; "
              f"input/output tokens: {result.usage.input_tokens}/{result.usage.output_tokens}.", "",
              f"Measured cost: ${result.measured_usage.cost_usd:.4f}; conservatively estimated upper cost: "
              f"${result.estimated_usage.cost_usd:.4f}.", "",
              "No live model provider or scientific computation is invoked by the default backend. "
              "Historical retrieval controls do not certify a model's training cutoff or knowledge. "
              "OS-level isolation is required before running arbitrary agents on locked benchmarks.", ""]
    return "\n".join(lines)


def write_run(output: Path, result: RunResult, store: EvidenceStore,
              model: ScorerArtifact | None, journal: RunJournal | None = None) -> str:
    # Do not overwrite existing predictions or accidentally write into a data tree.
    store.execution_base()  # Also guards callers that bypass run_workflow.
    check_semantics(result.case, store.snapshot, result.claims, result.features, result.prediction,
                    result.coverage, result.configuration, result.status, model, store.admitted_fingerprints,
                    store.catalog_policy, store.snapshot_base, result.trace)
    _check_source_inventory(store.snapshot, result.case, store.snapshot_base, store.catalog_policy, store.source_proofs)
    if result.backend_id == 'local-structured-selection-v1':
        from .local_model import verify_backend_execution
        from .retrieval import RetrievalPolicy, verify_retrieval_trace
        verify_backend_execution(read_json(output / 'backend-execution.json'), encode(result.trace), encode(result.configuration))
        verify_retrieval_trace(result.case, store, encode(result.trace),
            RetrievalPolicy(**result.configuration['backend_provenance']['config']['retrieval']))
    elif result.backend_id == 'recorded-selection-replay-v1':
        from .replay_validation import verify_replay_archive
        verify_replay_archive(result.case, result.configuration, result.trace, store)
    if journal is None:
        output.mkdir(parents=True, exist_ok=False)
    elif output.resolve() != journal.output or fingerprint(journal.events) != fingerprint(result.trace):
        raise ContractError("Run journal does not own output or match finalized trace")
    environment = {"python": sys.version, "platform": platform.platform(), "runtime_dependencies": {}}
    for name in ("tether-target-engine", "pyarrow"):
        try:
            environment["runtime_dependencies"][name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            environment["runtime_dependencies"][name] = None
    project = Path(__file__).resolve().parents[2]
    environment["build_inputs"] = {name: sha256_file(project / name) for name in ("pyproject.toml", "uv.lock")
                                    if (project / name).is_file()}
    inputs = {"case": result.case, "snapshot": store.snapshot, "scorer": model,
              "catalog_policy": store.catalog_policy, "configuration": result.configuration,
              "snapshot_base": str(store.snapshot_base), "environment": environment}
    run = {"schema_version": 2, "software_version": __version__,
           "created_at_utc": datetime.now(timezone.utc).isoformat(),
           "case_id": result.case.case_id, "status": result.status, "profile": result.profile,
           "snapshot_id": result.snapshot_id, "backend_id": result.backend_id,
           "input_fingerprint": fingerprint(inputs), "budget": result.budget,
           "calls": result.calls, "usage": result.usage, "plan": result.plan,
           "coverage": result.coverage, "exclusions": store.exclusions,
           "measured_usage": result.measured_usage, "estimated_usage": result.estimated_usage}
    check_execution(encode(run), result.case, store.snapshot, encode(result.configuration), result.claims, result.trace)
    write_json(output / "run.json", run)
    write_json(output / "inputs.json", inputs)
    write_json(output / "ledger.json", {"schema_version": 2, "claims": result.claims})
    if (output / "ledger.json").stat().st_size > MAX_LEDGER_JSON_BYTES:
        raise ContractError("Ledger JSON output exceeds the 256 MiB limit")
    write_json(output / "features.json", result.features)
    write_json(output / "prediction.json", result.prediction)
    (output / "trace.jsonl").write_bytes(b"".join(canonical(event) + b"\n" for event in result.trace))
    if journal is None:
        (output / "journal.jsonl").write_bytes((output / "trace.jsonl").read_bytes())
    (output / "dossier.md").write_text(dossier(result, store), encoding="utf-8")
    code_root = Path(__file__).parent
    receipt = {"schema_version": 2, "software_version": __version__,
               "input_fingerprint": fingerprint(inputs),
               "outputs": {name: sha256_file(output / name) for name in RUN_FILES},
               "sources": store.source_proofs,
               "admitted_fingerprints": store.admitted_fingerprints,
               "code": {path.relative_to(code_root).as_posix(): sha256_file(path) for path in sorted(code_root.rglob("*.py"))}}
    auxiliary = {name: sha256_file(output / name) for name in ('request.json', 'backend-execution.json')
                 if (output / name).is_file()}
    if auxiliary:
        receipt["auxiliary_outputs"] = auxiliary
    write_json(output / "receipt.json", receipt)
    # Return this digest for external anchoring. A local receipt is not a trusted timestamp.
    return sha256_file(output / "receipt.json")


def verify_run(output: Path, expected_receipt_sha256: str | None = None,
               verify_sources: bool = True) -> dict:
    receipt_path = output / "receipt.json"
    if expected_receipt_sha256 and sha256_file(receipt_path) != expected_receipt_sha256:
        raise ContractError("Externally anchored receipt hash mismatch")
    receipt = read_json(receipt_path)
    legacy = receipt.get("schema_version") == 1
    if not legacy and receipt.get("software_version") != __version__:
        raise ContractError("Semantic verification requires the original engine checkout; this engine verifies version " + __version__)
    replay_binding = None
    if receipt.get("schema_version") not in (1, 2) or set(receipt.get("outputs", {})) != set(LEGACY_RUN_FILES if legacy else RUN_FILES):
        raise ContractError("Invalid run receipt or incomplete output set")
    for relative, expected in receipt["outputs"].items():
        path = safe_child(output, relative)
        if not path.is_file() or sha256_file(path) != expected:
            raise ContractError(f"Run output integrity failure: {relative}")
    auxiliary = receipt.get("auxiliary_outputs", {})
    if not isinstance(auxiliary, dict) or set(auxiliary) - {"request.json", "backend-execution.json"}:
        raise ContractError("Invalid auxiliary output inventory")
    for relative, expected in auxiliary.items():
        path = safe_child(output, relative)
        if not path.is_file() or sha256_file(path) != expected:
            raise ContractError(f"Run auxiliary output integrity failure: {relative}")
    inputs = read_json(output / "inputs.json")
    if fingerprint(inputs) != receipt["input_fingerprint"]:
        raise ContractError("Input fingerprint mismatch")
    trace = read_chain(output / "trace.jsonl")
    count = len(trace)
    if not legacy and (output / "journal.jsonl").read_bytes() != (output / "trace.jsonl").read_bytes():
        raise ContractError("Semantic durable journal/trace mismatch")
    if verify_sources and legacy:
        for proof in receipt["sources"]:
            path = Path(proof["path"])
            if not path.is_absolute():
                path = safe_child(output, proof["path"])
            if not path.is_file() or sha256_file(path) != proof["sha256"]:
                raise ContractError(f"Source integrity failure: {proof['artifact_id']}")
            if proof.get("receipt_path") and sha256_file(Path(proof["receipt_path"])) != proof["receipt_sha256"]:
                raise ContractError("Source receipt integrity failure")
    if not legacy:
        case = decode(Case, inputs["case"])
        snapshot = decode(Snapshot, inputs["snapshot"])
        model = decode(ScorerArtifact, inputs["scorer"]) if inputs["scorer"] else None
        ledger = read_ledger_json(output / "ledger.json")
        if ledger.get("schema_version") != 2:
            raise ContractError("Semantic ledger schema mismatch")
        claims = decode(tuple[Claim, ...], ledger["claims"])
        run = read_json(output / "run.json")
        if run.get("software_version") != __version__:
            raise ContractError("Run and executing engine versions differ")
        if run['backend_id'] == 'local-structured-selection-v1':
            from .local_model import verify_backend_execution
            if 'backend-execution.json' not in auxiliary:
                raise ContractError('Local model run is missing its sealed execution archive')
            verify_backend_execution(read_json(output / 'backend-execution.json'), trace, inputs['configuration'])
        if run["input_fingerprint"] != receipt["input_fingerprint"]:
            raise ContractError("Semantic run input fingerprint mismatch")
        admitted = receipt["admitted_fingerprints"]
        _check_source_inventory(snapshot, case, Path(inputs["snapshot_base"]), inputs["catalog_policy"], receipt["sources"])
        restored = None
        if verify_sources:
            try:
                restored = admit_snapshot(snapshot, case, Path(inputs["snapshot_base"]), inputs["catalog_policy"])
            except (ContractError, OSError) as error:
                raise ContractError(f"Source integrity or admission failure: {error}") from error
            if fingerprint(restored.admitted_fingerprints) != fingerprint(admitted):
                raise ContractError("Semantic admitted fingerprints differ from eligible source packets")
            if run['backend_id'] == 'local-structured-selection-v1':
                from .retrieval import RetrievalPolicy, verify_retrieval_trace
                verify_retrieval_trace(case, restored, trace,
                    RetrievalPolicy(**inputs['configuration']['backend_provenance']['config']['retrieval']))
            if fingerprint(restored.exclusions) != fingerprint(run["exclusions"]):
                raise ContractError("Semantic source exclusions mismatch")
            for category, coverage in run["coverage"].items():
                records = restored.query(case, Category(category))
                observed = sum(item.observation.status.value == "observed" for item in records)
                nonobserved = [{"observation_id": item.observation.observation_id,
                                "status": item.observation.status.value, "reason": item.observation.statement}
                               for item in records if item.observation.status.value != "observed"]
                if (coverage["available_observations"] != observed or
                        fingerprint(coverage["nonobserved"]) != fingerprint(nonobserved) or
                        fingerprint(coverage["source_coverage"]) != fingerprint(snapshot.coverage)):
                    raise ContractError("Semantic coverage differs from eligible source packets")
        check_execution(run, case, snapshot, inputs["configuration"], claims, trace)
        check_semantics(case, snapshot, claims, decode(FeatureVector, read_json(output / "features.json")),
                        decode(Prediction, read_json(output / "prediction.json")), run["coverage"],
                        inputs["configuration"], run["status"], model, admitted, inputs["catalog_policy"],
                        inputs["snapshot_base"], trace)
        if run['backend_id'] == 'recorded-selection-replay-v1':
            from .replay_validation import verify_replay_archive
            replay_binding = verify_replay_archive(case, inputs['configuration'], trace, restored)
    code_root = Path(__file__).parent
    current_code = {path.relative_to(code_root).as_posix(): sha256_file(path)
                    for path in sorted(code_root.glob("*.py") if legacy else code_root.rglob("*.py"))}
    result = {"status": "integrity_verified", "outputs": len(LEGACY_RUN_FILES if legacy else RUN_FILES),
            "source_artifacts_checked": len(receipt["sources"]) if verify_sources else 0,
            "trace_events": count, "receipt_sha256": sha256_file(receipt_path),
            "external_anchor_checked": expected_receipt_sha256 is not None,
            "auxiliary_outputs_checked": len(auxiliary),
            "unsealed_auxiliary_outputs": ["request.json"] if (output / "request.json").is_file() and not auxiliary else [],
            "code_matches_current": receipt.get("code") == current_code,
            "semantic_consistency": "unavailable_legacy_v1" if legacy else "verified",
            "source_binding": "current_originals" if verify_sources else "archived_fingerprints_only",
            "scientific_validity": "not_established"}
    if replay_binding is not None:
        result['replay_binding'] = replay_binding
    return result

