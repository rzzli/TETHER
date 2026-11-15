"""Compatibility facade for shared engine state and dossier verification."""
from tether_engine.execution_states import check_states
from tether_engine.dossier_verification import check_dossier
from tether_engine.serde import parse_json


def check_engine_semantics(root, load_json, read_bytes, journal_events, ledger_limit):
    run, inputs = load_json(root / "run.json"), load_json(root / "inputs.json")
    trace = journal_events(read_bytes(root / "trace.jsonl"))
    check_states(run, trace, inputs["configuration"])
    ledger = parse_json(read_bytes(root / "ledger.json", max_bytes=ledger_limit))
    return check_dossier(run, inputs, ledger["claims"], load_json(root / "features.json"),
                         load_json(root / "prediction.json"), trace,
                         read_bytes(root / "dossier.md", max_bytes=ledger_limit))
