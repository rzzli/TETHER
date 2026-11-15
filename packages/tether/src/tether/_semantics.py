"""Wrapper prose reconstruction using the engine's shared execution-state checks.

This is a deterministic consistency check, not source authenticity, therapeutic
validation or an operating-system boundary. Historical artifacts remain unchanged.
"""
from types import SimpleNamespace
from tether_engine.artifacts import dossier_for_format
from tether_engine.chrono import Exclusion
from tether_engine.agents import Usage
from tether_engine.contracts import Case, Claim, Snapshot
from tether_engine.features import FeatureVector
from tether_engine.scorer import Prediction
from tether_engine.serde import ContractError, canonical, decode
from tether_engine.workflow import Budget, PlanStep, RunResult

from tether_engine.execution_states import check_states, need


def check_engine_semantics(root, load_json, read_bytes, journal_events, ledger_limit):
    run, inputs = load_json(root / "run.json"), load_json(root / "inputs.json")
    trace = journal_events(read_bytes(root / "trace.jsonl"))
    check_states(run, trace, inputs["configuration"])
    from tether_engine.serde import parse_json
    ledger = parse_json(read_bytes(root / "ledger.json", max_bytes=ledger_limit))
    fields = {k: run[k] for k in ("snapshot_id", "profile", "backend_id", "status", "budget", "calls",
              "usage", "plan", "coverage", "measured_usage", "estimated_usage")}
    fields.update(case=inputs["case"], claims=ledger["claims"], features=load_json(root / "features.json"),
                  prediction=load_json(root / "prediction.json"), trace=trace, configuration=inputs["configuration"])
    # RunResult contains deliberately unparameterized immutable Mapping fields;
    # its original wire decoder does not support decoding the complete class.
    # Decode typed members explicitly; coverage/configuration/trace were checked
    # by the engine and the state replay above, then Frozen copies their data.
    for key, kind in (("case", Case), ("claims", tuple[Claim, ...]), ("features", FeatureVector),
                      ("prediction", Prediction), ("budget", Budget), ("plan", tuple[PlanStep, ...]),
                      ("usage", Usage), ("measured_usage", Usage), ("estimated_usage", Usage)):
        fields[key] = decode(kind, fields[key])
    result = RunResult(**fields)
    store = SimpleNamespace(snapshot=decode(Snapshot, inputs["snapshot"]),
                            exclusions=decode(tuple[Exclusion, ...], run["exclusions"]))
    expected = dossier_for_format(result, store, run.get("dossier_format")).encode("utf-8")
    actual = read_bytes(root / "dossier.md", max_bytes=ledger_limit)
    need(actual in (expected, expected.replace(b"\n", b"\r\n")), "dossier prose differs from deterministic rendering")
    return {"method": "tether.execution_semantics.v1", "coverage_state_machine": "verified",
            "review_to_claims": "verified", "dossier_reconstruction": "verified"}
