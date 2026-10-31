"""Finite SOURCE/DATA-only proposal review; never imports/executes a port."""
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROPOSAL=HERE/"PORTABLE-FILE-PORTS-CORRECTION-PROPOSAL-v1.json"
TARGET=HERE/"PORTABLE-FILE-PORTS-CORRECTION-INDEPENDENT-REVIEW-v2.json"


def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def same(a,b):
    if type(a) is not type(b): return False
    if type(a) is dict: return set(a)==set(b) and all(same(a[k],b[k]) for k in a)
    if type(a) is list: return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b


assert not TARGET.exists()
assert pin(PROPOSAL)["sha256"]=="c30fbddf1019dee9a457705ec2553d0662b6555ae5a753a6bab7aeecd51dfc22"
p=json.loads(PROPOSAL.read_bytes())
for row in p["inputs"].values(): assert pin(Path(row["path"]))==row
original_path=HERE/"FILE-PORTS-FIXTURES-v3.json"
original=json.loads(original_path.read_bytes()); by={row["id"]:row for row in original["cases"]}
assert len(by)==84
candidate=copy.deepcopy(by); patches={row["id"]:row for row in p["patches"]}
assert len(patches)==18
for identity,patch in patches.items():
    old=by[identity]; new=candidate[identity]
    if patch["script_changed"]: new["script"]=patch["new_script"]
    for key,change in patch["expected_field_changes"].items():
        assert same(old["expected"][key],change["before"])
        new["expected"][key]=change["proposed"]
    assert len(old["script"])==patch["old_script_steps"] and len(new["script"])==patch["new_script_steps"]
script_ids={row["id"] for row in p["patches"] if row["script_changed"]}
assert script_ids==set(p["thirteen_script_case_ids"]) and len(script_ids)==13
details=[]
for identity in p["thirteen_script_case_ids"]:
    old=by[identity]["script"]; new=candidate[identity]["script"]
    assert new[0]["kind"]=="clock" and new[0]["now_ns"]==0
    assert len(new)<=512
    prior=0
    for step in new:
        if step["kind"]=="clock":
            assert type(step["now_ns"]) is int and step["now_ns"]>=prior; prior=step["now_ns"]
    if identity=="namespace_owned_journal_reserve_failure": continue
    # The old script is an unchanged subsequence. Only same-time fresh clock
    # reads and an explicit timely-owned-original no-op log hook are inserted.
    i=0; added_clocks=added_logs=0; now=0
    for j,step in enumerate(new):
        if i<len(old) and same(step,old[i]): i+=1
        elif step["kind"]=="clock":
            assert step==dict(kind="clock",now_ns=now,raises=None,before_projection={})
            added_clocks+=1
        else:
            assert step==dict(kind="hook",name="log_append",raises=None,before_projection={"slots.o0.open_state":"observed_owned"})
            assert j>=2 and new[j-1]["kind"]=="clock" and now<295000000000
            api=new[j-2]
            assert api["kind"]=="api" and api["name"]=="CreateFileW" and api["arguments"]["desired_access"]==2147483648
            assert api["outcome"]["raise"] is None
            raw=api["outcome"]["raw_return"]["value"]
            assert type(raw) is int and raw not in (0,2**64-1)
            added_logs+=1
        if step["kind"]=="clock": now=step["now_ns"]
    assert i==len(old)
    for kind in ("api",):
        assert same([s for s in old if s["kind"]==kind],[s for s in new if s["kind"]==kind])
    details.append(dict(id=identity,inserted_fresh_same_time_clocks=added_clocks,inserted_noop_owned_log_hooks=added_logs,
        original_API_arguments_returns_exceptions_preserved=True,original_time_advances_preserved=True,
        first_origin_sample_ns=0,old_steps=len(old),proposed_steps=len(new)))

namespace="namespace_owned_journal_reserve_failure"
ns=candidate[namespace]; baseline=candidate["success_baseline"]
assert same(ns["request"]["actions"][0],baseline["request"]["actions"][0])
stop=next(i for i,s in enumerate(baseline["script"]) if s["kind"]=="api" and s["name"]=="CreateFileW" and s["arguments"]["path"].endswith("\\journal.jsonl"))
assert same(ns["script"][:stop],baseline["script"][:stop])
old_failure=next(s for s in by[namespace]["script"] if s["kind"]=="api" and s["name"]=="CreateFileW")
assert same(ns["script"][stop]["outcome"],old_failure["outcome"])
assert len(ns["script"])==stop+2
assert ns["script"][-1]["kind"]=="clock" and ns["script"][-1]["before_projection"]=={"slots.j0.open_state":"known_failure_no_handle"}
attempts={name:0 for name in ns["expected"]["api_attempts"]}; returns=dict(attempts)
for step in ns["script"]:
    if step["kind"]=="api":
        attempts[step["name"]]+=1
        returns[step["name"]]+=int(step["outcome"]["raise"] is None)
assert attempts==ns["expected"]["api_attempts"] and returns==ns["expected"]["api_returns"]
assert ns["expected"]["namespace_owned"] is True and ns["expected"]["reservation_ready"] is False
for key in ("known_write_bytes","write_hash_bytes","flushed_known_bytes"): assert ns["expected"][key]==20
for key in ("known_read_bytes","hashed_bytes","captured_bytes"): assert ns["expected"][key]==0
assert attempts["ReadFile"]==returns["ReadFile"]==0
assert ns["expected"]["slots"][0]["id"]=="r0" and ns["expected"]["slots"][0]["close_state"]=="returned_success"
assert ns["expected"]["slots"][1]["id"]=="j0" and ns["expected"]["slots"][1]["handle"] is None

primary=candidate["write_false_and_close_failure"]["expected"]
assert primary["primary"]=="false" and primary["secondary"]==["close_failed"]
assert same(candidate["write_false_and_close_failure"]["script"],by["write_false_and_close_failure"]["script"])
for identity in ("owned_open_log","read_hash","read_copy"):
    assert candidate[identity]["expected"]["disposition"]=="incomplete_unknown"
    assert patches[identity]["expected_field_changes"]=={"disposition":{"before":"incomplete_known_failure","proposed":"incomplete_unknown"}}
    for key in ("known_read_bytes","hashed_bytes","captured_bytes","read_count_unknown","known_write_bytes","write_count_unknown","primary","secondary"):
        assert same(candidate[identity]["expected"][key],by[identity]["expected"][key])
assert candidate["seal_close_return_late"]["expected"]["primary"]=="hard_deadline"
root_tags=[]
for identity in ("root_spelling_58","root_spelling_59","root_spelling_60"):
    case=candidate[identity]
    assert case["expected"]["primary"]=="path_root"
    assert same(case["script"],by[identity]["script"]) and all(n==0 for n in case["expected"]["api_attempts"].values())
    assert case["expected"]["disposition"]==by[identity]["expected"]["disposition"]=="admission_rejected"
    root_tags.append(dict(id=identity,subcase=case["subcase"],rejection_still="admission_rejected",API_attempts=0,primary="path_root"))
for case in candidate.values():
    for flag in ("profile_qualified","runtime_authorized","originals_authenticated","terminal_ack"): assert case["expected"][flag] is False
    assert case["expected"]["journal_recursive_events"]==0
unchanged=[identity for identity in by if same(by[identity],candidate[identity])]
replay_path=HERE/"PORTABLE-FILE-PORTS-PROPOSED-INTERFACE-REPLAY-v1.json"
replay=json.loads(replay_path.read_bytes())
record=dict(schema_version=1,status="CLEAR_FINITE_FIXTURE_REPAIR_PROPOSAL_ONLY_SOURCE_FIXES_AND_SUCCESSOR_REVIEW_PENDING",
    proposal=pin(PROPOSAL),portable_source=p["inputs"]["portable_file_ports_v1.py"],
    original_fixture=pin(original_path),reviewer=pin(Path(__file__).resolve()),
    scope="Independent finite literal/source-format review only. No portable helper/API/fixture-script replay/import, no FFI/source-closure/original/runtime qualification.",
    script_repairs=details,script_repair_cases=13,changed_cases=18,unchanged_cases=len(unchanged),
    preserved_reviewer_count_failure=pin(HERE/"PORTABLE-CORRECTION-REVIEW-AUTHOR-FAILURE-v1.json"),
    namespace_prefix=dict(old_steps=len(by[namespace]["script"]),proposed_steps=len(ns["script"]),
        coherent_baseline_prefix_until_journal_open=True,reservation_bytes_known_hashed_flushed=20,
        namespace_owned=True,reservation_ready=False,original_read_attempts=0,slot_r0_closed_once=True,slot_j0_no_handle=True,
        API_attempts=attempts,API_returns=returns),
    preserved_primary=dict(first="false",secondary=["close_failed"],script_unchanged=True),root_diagnostic_tags=root_tags,
    known_unknown="Three opaque hook failures change only terminal disposition to incomplete_unknown. Already known read/hash/capture/write counts and byte-definedness flags are unchanged; unobserved bytes are not zeroed. Flush-unreturned retains known write/hash lower bounds and unreturned API census, not a claim that no flush happened.",
    source_gate="No portable source guard or API return/argument is removed or weakened. Fresh samples use the same scripted origin; no clock/deadline reset. No-op log hook does not grant identity or skip four metadata queries.",
    conditions_before_any_source_acceptance=[
        "Native-owned source fix must reserve unknown WriteFile count before an entered call can fail/return unknown, preserving original exception and later cleanup as secondary.",
        "Native-owned content operations must require a successful same-owner four-query identity capability; primitive seeded preconditions remain explicitly HARNESS_ONLY, never a serialized identity_ok/ready dict or a general owned handle.",
        "Retain all before files, freeze separately named successor fixtures/source and rerun strict finite scripts and independent actual-source gates after source fixes.",
        "The retained proposed replay reports83/84 matching, not a completed source gate; byte-equal fictional projections do not authenticate a real file, FFI handoff, owner clock or production integration."],
    reported_replay_metadata=dict(pin=pin(replay_path),matched=replay["matched"],cases=replay["cases"],reviewer_did_not_replay=True),
    concrete_additional_proposal_blockers=[],source_corrections_required=p["source_corrections_required"],
    actual_portable_or_API_calls=0,old_original_payload_operations=0,source_closure_qualified=False,
    serialization_grants_identity=False,profile_qualified=False,runtime_authorized=False,originals_authenticated=False)
with TARGET.open("xb") as out: out.write(json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")+b"\n")
print(json.dumps(pin(TARGET)))
