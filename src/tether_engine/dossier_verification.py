"""Reconstruct the dossier from verified execution fields, not receipt text hashes."""
from types import SimpleNamespace
from tether_engine.chrono import Exclusion
from tether_engine.agents import Usage
from tether_engine.contracts import Case, Claim, Snapshot
from tether_engine.features import FeatureVector
from tether_engine.scorer import Prediction
from tether_engine.serde import decode
from tether_engine.workflow import Budget, PlanStep, RunResult

from tether_engine.execution_states import need


def check_dossier(run, inputs, claims, features, prediction, trace, actual):
    from .artifacts import dossier_for_format
    fields = {k: run[k] for k in ("snapshot_id", "profile", "backend_id", "status", "budget", "calls",
              "usage", "plan", "coverage", "measured_usage", "estimated_usage")}
    fields.update(case=inputs["case"], claims=claims, features=features,
                  prediction=prediction, trace=trace, configuration=inputs["configuration"])
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
    need(actual in (expected, expected.replace(b"\n", b"\r\n")), "dossier prose differs from deterministic rendering")
    return {"method": "tether.execution_semantics.v1", "coverage_state_machine": "verified",
            "review_to_claims": "verified", "dossier_reconstruction": "verified"}
