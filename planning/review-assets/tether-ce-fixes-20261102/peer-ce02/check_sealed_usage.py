"""Independent CE02 sealed-run witnesses; fake in-memory HTTP transport only."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys

import asof
import asof.local_model as local
from asof.artifacts import verify_run, write_run
from asof.chrono import load_snapshot
from asof.contracts import Case
from asof.journal import RunJournal
from asof.serde import ContractError, canonical, decode, encode, read_json, write_json
from asof.workflow import Budget, run_workflow

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "src/asof/demo/v2"


class InMemoryTransport:
    def __init__(self, mode):
        self.mode, self.calls = mode, 0

    def open(self, request, timeout):
        self.calls += 1
        if self.mode == "timeout":
            raise TimeoutError("Fictional peer transport timeout")
        payload = json.loads(request.data)
        choices = payload["json_schema"]["properties"]["observation_ids"]["items"]["enum"]
        tokens = 1_000_000 if self.mode == "overquote" else True if self.mode == "bool-count" else 50
        return io.BytesIO(canonical(dict(content=json.dumps(dict(observation_ids=choices[:1])),
                                        truncated=False, tokens_evaluated=tokens, tokens_predicted=1)))


def execute(base, mode):
    folder = base / mode
    folder.mkdir()
    config = folder / "config.json"
    write_json(config, dict(schema_version=1, endpoint="http://127.0.0.1:55580",
        model_id="peer-fictional-never-contacted", model_provenance=dict(
            weights_sha256={"fictional": "a" * 64}, runtime_sha256="b" * 64),
        retrieval=dict(max_records=12, max_request_bytes=12000), max_output_tokens=256,
        timeout_seconds=1, seed=42))
    backend = local.LocalSelectionBackend(config)
    backend.opener = InMemoryTransport(mode)
    case = decode(Case, read_json(FIXTURE / "case.json"))
    store = load_snapshot(FIXTURE / "snapshot.json", case)
    output = folder / "run"
    journal = RunJournal(output)
    try:
        result = run_workflow(case, store, backend, budget=Budget(
            max_input_tokens=200000, max_output_tokens=10000, max_retries=3), journal=journal)
        write_json(output / "backend-execution.json", dict(schema_version=1, attempts=backend.records))
        receipt = write_run(output, result, store, None, journal)
    finally:
        journal.close()
    verified = verify_run(output, receipt)
    assert verified["semantic_consistency"] == "verified"
    assert verified["source_binding"] == "current_originals"
    trace = encode(result.trace)
    accounts = [row["details"] for row in trace if row["event"] == "attempt_accounted"]
    dispatches = [row["details"] for row in trace if row["event"] == "dispatch"]
    violations = [row for row in trace if row["event"] == "backend_usage_contract_violated"]
    if mode == "overquote":
        assert backend.opener.calls == result.calls == 1
        assert result.status == "budget_exhausted" and len(violations) == 1
        assert result.usage.input_tokens == result.measured_usage.input_tokens == 1_000_000
        assert result.estimated_usage.input_tokens == 0 and not result.claims
        assert accounts[0]["basis"] == "adapter_reported"
    elif mode in ("bool-count", "timeout"):
        assert result.calls == len(dispatches) == backend.opener.calls
        assert result.measured_usage.input_tokens == 0 and not violations
        assert result.estimated_usage.input_tokens == sum(row["reserved"]["input_tokens"] for row in dispatches)
        assert all(row["basis"] == "quoted_upper_bound_not_measured" for row in accounts)
    else:
        assert result.measured_usage.input_tokens == 50 * result.calls
        assert result.estimated_usage.input_tokens == 0 and not violations
    return dict(mode=mode, output=str(output), receipt_sha256=receipt, calls=result.calls,
        measured=encode(result.measured_usage), estimated=encode(result.estimated_usage),
        status=result.status, claims=len(result.claims), violations=len(violations), verification=verified)


def mutation_controls(case):
    output = Path(case["output"])
    document = read_json(output / "backend-execution.json")
    trace = [json.loads(line) for line in (output / "trace.jsonl").read_text().splitlines()]
    config = read_json(output / "inputs.json")["configuration"]
    controls = []
    for name in ("wrong-attempt", "wrong-reservation", "swapped-accounts", "wrong-unknown-amount"):
        changed = deepcopy(trace)
        accounts = [row["details"] for row in changed if row["event"] == "attempt_accounted"]
        dispatches = [row["details"] for row in changed if row["event"] == "dispatch"]
        if name == "wrong-attempt":
            accounts[0]["attempt_id"] = "not-the-dispatched-attempt"
        elif name == "wrong-reservation":
            dispatches[0]["reserved"]["input_tokens"] += 1
        elif name == "swapped-accounts":
            first, second = deepcopy(accounts[0]), deepcopy(accounts[1])
            accounts[0].clear(); accounts[0].update(second)
            accounts[1].clear(); accounts[1].update(first)
        else:
            accounts[0]["usage"]["input_tokens"] -= 1
        try:
            local.verify_backend_execution(document, changed, config)
        except ContractError as error:
            controls.append(dict(mutation=name, rejected=True, message=str(error)))
        else:
            raise AssertionError("Mutation accepted: " + name)
    return controls


mode, base, results = sys.argv[1], Path(sys.argv[2]).absolute(), Path(sys.argv[3]).absolute()
results.parent.mkdir(parents=True, exist_ok=True)
record = dict(scope="Fictional sealed usage controls; no server, model, network or scientific evaluation",
              engine_version=asof.__version__, module_path=local.__file__,
              module_sha256=hashlib.sha256(Path(local.__file__).read_bytes()).hexdigest())
if mode in ("produce-new", "produce-old"):
    expected = "0.3.12" if mode == "produce-new" else "0.3.11"
    assert asof.__version__ == expected
    base.mkdir(parents=True, exist_ok=False)
    modes = ("overquote", "bool-count", "timeout") if mode == "produce-new" else ("bool-count", "timeout")
    record["runs"] = [execute(base, condition) for condition in modes]
    if mode == "produce-new":
        record["mutations"] = mutation_controls(next(row for row in record["runs"] if row["mode"] == "timeout"))
    with (base / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
elif mode == "reverify-old":
    prior = json.loads((base / "manifest.json").read_bytes())
    assert prior["engine_version"] == "0.3.11" and asof.__version__ == "0.3.12"
    record["old_manifest_sha256"] = hashlib.sha256((base / "manifest.json").read_bytes()).hexdigest()
    record["runs"] = []
    for run in prior["runs"]:
        verified = verify_run(Path(run["output"]), run["receipt_sha256"])
        assert verified["semantic_consistency"] == "verified"
        record["runs"].append(dict(mode=run["mode"], receipt_sha256=run["receipt_sha256"], verification=verified))
else:
    raise ValueError("Unknown mode")
record["passed"] = True
with results.open("x", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(json.dumps(record, indent=2))
