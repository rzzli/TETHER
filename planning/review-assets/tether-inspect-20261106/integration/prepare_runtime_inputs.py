"""Prepare prospective fictional input bytes only; never invoke Inspect or a model."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy.records import parse, proof, publish, read_bytes
from experiments.inspect_policy.witnesses import prepare_witnesses, make_source, make_row


def main():
    base = ROOT / "data/cache/tether-inspect-runtime-witnesses-20261106-attempt01"
    base.mkdir(exist_ok=False)
    ordinary = prepare_witnesses(base / "inputs")
    processes = base / "process-inputs"
    processes.mkdir()
    first = make_row(make_source(processes / "IX06-first", "IX06-first"), call_seconds=20.0)
    first["steps"][0]["script"].update(behavior="sleep", delay_seconds=10.0)
    second = make_row(make_source(processes / "IX06-second", "IX06-second"))
    owner = make_row(make_source(processes / "IX08-owner", "IX08-owner"))
    process_rows = publish(processes / "rows.json", {"IX06": [first, second], "IX08": owner})
    process_oracle = publish(processes / "oracle.json", {"schema_version": 1, "cases": [
        {"control_id": first["id"], "fields": {}},
        {"control_id": second["id"], "fields": {}},
        {"control_id": owner["id"], "fields": {"status": "completed"}}],
        "scope": "Separate process outcomes are independently evaluated; incomplete native calls are not scored correct."})
    rows = parse(read_bytes(ordinary["rows"]["path"]))
    recipe = publish(base / "ordinary-recipe.json", {"rows": rows,
        "output_root": str(base / "ordinary-cases"),
        "oracle_path": ordinary["oracle"]["path"],
        "oracle_proof": {key: ordinary["oracle"][key] for key in ("sha256", "bytes")}})
    inputs = {str(path.relative_to(base)).replace("\\", "/"): proof(path)
              for path in sorted(base.rglob("*")) if path.is_file()}
    result = {"schema_version": 1, "status": "prepared_not_executed", "ordinary": ordinary,
        "ordinary_recipe": {"path": str(base / "ordinary-recipe.json"), **recipe},
        "process_rows": {"path": str(processes / "rows.json"), **process_rows},
        "process_oracle": {"path": str(processes / "oracle.json"), **process_oracle},
        "input_inventory": inputs, "input_files": len(inputs),
        "input_bytes": sum(pin["bytes"] for pin in inputs.values()),
        "provider_calls": 0, "provider_cost_usd": 0,
        "scheduled_ordinary_rows": 16, "scheduled_process_groups": ["IX06", "IX08"],
        "process_expectations": {
            "IX06": {"status": "PASS", "provider_dispatches": 1, "first": "interrupted",
                     "second": "unexecuted", "outstanding_quote": first["steps"][0]["quote"],
                     "process_reaped": True, "automatic_retry": False},
            "IX08": {"status": "PASS", "owners": 1, "provider_dispatches": 1,
                     "native_sample_errors_sorted": [False, True], "processes_reaped": True,
                     "automatic_retry": False}},
        "scope": "Fictional exposed fault controls; outputs do not exist and no native task has run."}
    seal = publish(base / "PREPARATION.json", result)
    print({"root": str(base), "preparation": seal, "input_files": len(inputs),
           "input_bytes": result["input_bytes"], "ordinary_recipe": recipe})


if __name__ == "__main__":
    main()
