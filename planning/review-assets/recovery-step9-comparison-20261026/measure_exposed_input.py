"""Planning-only size measurement; never admits or dispatches a request."""
import copy
import hashlib
import json
from pathlib import Path
from asof.serde import canonical, encode, fingerprint
from asof.study.diagnostic import ACTIVE_SIMPLIFIED_SCHEMA
from asof.study.diagnostic_codec import quote_choices

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
RUN = ROOT / "runs/r07-native-diagnostic-20261026T165505Z"
SEAL = "863bf2a9cfb8d4fd01a5223b993d87fbe2ac06992e7206d3d32ef4c712cf2d41"
REQUEST = "14b735ef940bde56c04ea964cf145f3f7d1e343b2fe1e35de157cc8a5af2d61a"
PLAN = "33d2b7dff7a3f834132b005be650129f0378cf74a1f3083dc60f8db2688e3a52"
def checked(path, expected, size=None):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    assert size is None or len(raw) == size
    return json.loads(raw)
seal = checked(RUN / "terminal-seal.json", SEAL)
def member(name):
    pin = seal["files"][name]
    return checked(RUN / name, pin["sha256"], pin["bytes"])
request = member("cells/exposed-il6r-genetics-current/request.json")
assert fingerprint(request) == REQUEST
assert request == member("inputs/exposed-il6r-genetics-current/request.json")
run_plan = checked(RUN / "run-plan.json", seal["plan"]["sha256"], seal["plan"]["bytes"])
gate_pin = run_plan["source_gate"]
gate = checked(Path(gate_pin["path"]), gate_pin["sha256"], gate_pin["bytes"])
assert gate["request_sha256"] == gate["expected_request_sha256"] == REQUEST
assert gate["selected_observation_ids"] == [r["observation_id"] for r in request["source_scope"]["observations"]]
plan = checked(OUT / "PLAN-v2.json", PLAN)
aliases = encode(quote_choices(request))
table = [{"source_id": alias, "observation_id": request["source_request"]["evidence"][i]["observation_id"], "pointers": list(pointers)} for i, (alias, pointers) in enumerate(aliases.items())]
schema = copy.deepcopy(encode(ACTIVE_SIMPLIFIED_SCHEMA))
schema.pop("$comment", None)
schema["properties"]["claims"]["maxItems"] = request["source_request"]["bounds"]["max_claims"]
claim = schema["properties"]["claims"]["items"]["properties"]
claim["source_ids"]["items"] = {"type": "string", "enum": list(aliases)}
claim["quote_pointers"]["items"] = {"type": "string", "enum": sorted({p for choices in aliases.values() for p in choices})}
records = []
for arm, stages in [("asof_interpretation", plan["asof_stages"]), ("adapted_virtual_biotech_interpretation", plan["stage_order"])]:
    for index, stage in enumerate(stages):
        history = [{"stage": prev, "source_ids": list(aliases)} for prev in stages[:index]]
        data = {"original_request": request, "original_source_table": table, "stage": stage, "prior_source_id_feedback": history, "feedback_authority": "untrusted_generated_selection_not_evidence"}
        prompt = "<|im_start|>system\n" + plan["guide"] + "\n" + plan["role_guides"][stage] + "<|im_end|>\n<|im_start|>user\n" + canonical(data).decode().replace("<|", "<\\u007c") + "<|im_end|>\n<|im_start|>assistant\n"
        payload = {"prompt": prompt, "n_predict": 1024, "temperature": 0.0, "seed": 42, "cache_prompt": False, "json_schema": schema, "stop": ["<|im_end|>"], "stream": False}
        assert fingerprint(data["original_request"]) == REQUEST
        records.append({"arm": arm, "stage": stage, "original_request_sha256": fingerprint(data["original_request"]), "source_scope_sha256": fingerprint(data["original_request"]["source_scope"]), "evidence_sha256": fingerprint(data["original_request"]["source_request"]["evidence"]), "prompt_utf8_bytes": len(prompt.encode()), "payload_utf8_bytes": len(canonical(payload)), "payload_sha256": fingerprint(payload), "input_reservation": len(prompt.encode()) + 32, "output_reservation": 1024, "history_bytes": len(canonical(history)), "prompt_fits": len(prompt.encode()) <= 6368, "payload_fits": len(canonical(payload)) <= 65536})
result = {"schema_version": 1, "role": "planning_only", "dispatchable": False, "scope": "already_exposed_single_real_request_size_measurement_not_admission", "terminal_seal_sha256": SEAL, "child_request_pin": seal["files"]["cells/exposed-il6r-genetics-current/request.json"], "canonical_request_sha256": REQUEST, "input_request_pin": seal["files"]["inputs/exposed-il6r-genetics-current/request.json"], "source_gate_pin": gate_pin, "source_gate_status": gate["status"], "source_gate_revalidation_status": gate["revalidation_status"], "source_gate_interpretation": "Historical metadata identity checked; no new source-inclusive admission performed", "plan_sha256": PLAN, "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "stage_records": records, "aggregate_input_reservation": sum(r["input_reservation"] for r in records), "aggregate_output_reservation": sum(r["output_reservation"] for r in records), "aggregate_input_cap": 32000, "aggregate_output_cap": 8000, "per_stage_prompt_cap": 6368, "all_sources_unchanged": True, "unique_observations": len(aliases), "quote_pointer_count": sum(map(len, aliases.values())), "guide_claim_limit": 3, "request_and_schema_claim_limit": request["source_request"]["bounds"]["max_claims"], "actual_model_calls": 0, "raw_candidate_answers_read": False, "clinical_outcomes_read": False, "full_payloads_retained": False}
result["aggregate_fits"] = result["aggregate_input_reservation"] <= 32000 and result["aggregate_output_reservation"] <= 8000
result["per_stage_fits"] = all(r["prompt_fits"] and r["payload_fits"] for r in records)
with (OUT / "REAL-INPUT-FEASIBILITY.json").open("xb") as f:
    f.write(canonical(result))
print(json.dumps(result, indent=2))
