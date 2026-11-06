"""Native Inspect Task, solver and scorer; archive helpers stay Inspect-free."""
from pathlib import Path
from inspect_ai import Task
from inspect_ai.dataset import Sample
from inspect_ai.model import GenerateConfig, ModelOutput
from inspect_ai.scorer import Score, Target, accuracy, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver
from .records import canonical, checked_json, inspect_record, safe_path, thaw
from .archive import checked_rows, execute_archive_case, compare_result

@solver
def archive_solver(rows: list[dict], output_root: str, execute=None) -> Solver:
    schedule = {row["control_id"]: row for row in checked_rows(rows)}
    execute = execute_archive_case if execute is None else execute

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        row = schedule[str(state.sample_id)]
        if state.input_text != canonical(row).decode("utf-8"):
            raise ValueError("Inspect sample input differs from captured schedule")
        returned = execute(row, output_root)
        state.metadata["policy_record"] = {"path": returned["output"], "receipt": returned["receipt"],
                                           "case_wall_seconds": returned["case_wall_seconds"],
                                           "case_cpu_seconds": returned["case_cpu_seconds"]}
        result = returned["result"]
        state.output = ModelOutput.from_content(model="none", content=canonical(result).decode("utf-8"))
        if result["status"] != "completed":
            raise RuntimeError("Policy execution did not complete: " + result["status"])
        state.completed = True
        return state

    return solve


@scorer(metrics=[accuracy()])
def archive_scorer(oracle_path: str, oracle_proof: dict):
    async def score(state: TaskState, target: Target):
        # The oracle is deliberately not read while constructing the Task and is
        # absent from Sample.target, metadata, messages and solver arguments.
        retained = state.metadata["policy_record"]
        record = inspect_record(retained["path"], receipt_sha256=retained["receipt"]["sha256"])
        if (record["request"].get("control_id") != str(state.sample_id) or
                record["result"].get("control_id") != str(state.sample_id) or
                record["result"].get("decision", {}).get("control_id") != str(state.sample_id)):
            raise ValueError("Sample and retained policy case identities differ")
        if record["result"]["status"] != "completed" or state.output.completion != canonical(record["result"]).decode("utf-8"):
            raise ValueError("Inspect/native result binding differs")
        oracle = checked_json(oracle_path, oracle_proof)
        expected = [row for row in oracle["cases"] if row["control_id"] == str(state.sample_id)]
        if len(expected) != 1:
            raise ValueError("Oracle identity missing or duplicated")
        observed = record["result"]["decision"]
        comparison = compare_result(observed, expected[0])
        if not comparison["has_verdict"]:
            return Score.unscored(reason=comparison["reason"], metadata=comparison)
        return Score(value="C" if comparison["full_match"] else "I", answer=observed["decision"],
                     metadata=comparison)
    return score


def build_archive_task(rows, output_root, oracle_path, oracle_proof, *, execute=None):
    rows = [thaw(row) for row in checked_rows(rows)]
    output_root = safe_path(output_root)
    if not output_root.is_dir():
        raise ValueError("Caller must reserve an empty output root before Task construction")
    if any(output_root.iterdir()):
        raise ValueError("Task output root must be empty")
    return Task(dataset=[Sample(id=row["control_id"], input=canonical(row).decode("utf-8"), target="") for row in rows],
                solver=archive_solver(rows, str(output_root), execute=execute),
                scorer=archive_scorer(str(oracle_path), dict(oracle_proof)),
                model="none", config=GenerateConfig(max_retries=0, cache=False),
                fail_on_error=False, score_on_error=False, epochs=1,
                name="tether_equivalent_policy_archive", version=1,
                metadata={"scheduled": len(rows), "scope": "exposed_authored_archive_conformance",
                          "scientific_validation": "not_established", "oracle_in_solver_input": False})
