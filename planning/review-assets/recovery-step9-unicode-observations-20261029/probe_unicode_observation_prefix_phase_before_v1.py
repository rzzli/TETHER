"""Freeze a literal in-flight-prefix negative, then retain V1 over-rejection."""
import copy
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import unicode_observation_test_support_v2 as S

HERE=Path(__file__).resolve().parent
VECTOR=HERE/"UNICODE-OBSERVATIONS-PREFIX-PHASE-VECTOR-v1.json"
REPORT=HERE/"UNICODE-OBSERVATIONS-PREFIX-PHASE-BEFORE-v1.json"
assert not VECTOR.exists() and not REPORT.exists()
U=S.load(HERE/"unicode_observations_v1.py","unicode_observations_v1","58d6a62fe6a9416c94e5637b615886cecd90bc78ef1559f05f7d1d1ebd6e32c0")
base=S.BASES["complete_positive"]; raw,_=S.capture(base); lines=[x+b"\n" for x in raw[:-1].split(b"\n")]
selection=json.loads(lines[184]); choice=selection["body"]["selected_prefixes"][0]
row=copy.deepcopy(selection); row.update(row_sequence=185,event="failure",elapsed_ms=1950)
row["native_call_counters"]["llama_sampler_init_grammar"]["attempted"]+=1
s=row["native_state"]; s["total_attempted"]+=1; s["last_attempt"]="llama_sampler_init_grammar"
s["current_selected_prefix_index"]=0; s["token_work_reserved"]+=choice["take_tokens"]
s["exceptions"]=1; s["cleanup_failed"]=True
identity=dict(pid=base["bindings"]["expected_child_pid"],error_class="BridgeError",reason_code="native_ownership_or_cleanup_unknown",elapsed_ms=1950,row_sequence_reserved=185)
row["body"]=dict(primary_failure_id=hashlib.sha256(S.canonical(identity)).hexdigest(),error_class="BridgeError",
    reason_code=identity["reason_code"],diagnostic_file=None,profile_qualification="not_established")
raw=b"".join(lines[:185])+S.canonical(row)+b"\n"
vector=dict(schema_version=1,status="AUTHORED_LITERAL_PREFIX_FAILURE_BEFORE_CORRECTION",source_base_sha256=base["sha256"],
    raw_hex=raw.hex(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),failure_marker_hex=None,
    expected=dict(classification="partial_observation",validated_case_rows=84,validated_native_geometry_rows=78,
        known_membership_outcomes=78,unique_selected_prefix_results=0,source_cleanup_consistent=False,
        normal_schedule_complete=False,terminal_negative_seen=True),
    scope="Next declared prefix init reservation has no observed return; all84 fixed cases known, no dependent frees or invented control result.",
    profile_qualified=False,native_payload_SDK_operations=0)
VECTOR.write_bytes(S.canonical(vector)+b"\n")
try:
    result=S.invoke(U.observe,raw,S.PROFILE,S.bindings(U),failure_marker=None,check=S.budget)
    outcome=dict(returned=result.to_dict()["classification"],status="unexpected_before_acceptance")
except U.ObservationError as error:
    outcome=dict(status="reproduced_over_rejection",error=error.to_dict())
REPORT.write_bytes(S.canonical(dict(schema_version=1,source=S.pin(HERE/"unicode_observations_v1.py"),vector=S.pin(VECTOR),
    probe=S.pin(Path(__file__).resolve()),outcome=outcome,native_payload_SDK_operations=0,profile_qualified=False))+b"\n")
print(json.dumps(dict(vector=S.pin(VECTOR),before=S.pin(REPORT),outcome=outcome["status"])))
