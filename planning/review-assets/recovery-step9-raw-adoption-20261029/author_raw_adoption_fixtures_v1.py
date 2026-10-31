"""Literal fictional input/expected-state author; no transition implementation.

All expected counters/outcomes below are authored arguments, not folded from a
future adopter or from execution of the scripts. Common helpers only frame JSON.
"""
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PORTS=HERE.parent/"recovery-step9-file-ports-20261029"
TARGET=HERE/"RAW-ADOPTION-FIXTURES-v1.json"


def atom(tag="UNOBSERVED",value=None): return dict(tag=tag,value=value)
U=atom()
H=lambda value:atom("HANDLE",value)
B=lambda value:atom("BOOL32",value)
N=lambda value:atom("COUNT32",value)


def step(op,**fields): return dict(op=op,**fields)
def reserve(ordinal,api,slot,requested=None,buffer_ref=None,prepared_hex="",declared_empty=False):
    return step("reserve",ordinal=ordinal,api=api,slot=slot,requested=requested,buffer_ref=buffer_ref,prepared_hex=prepared_hex,declared_empty=declared_empty)
def invoke(n): return step("invoke",ordinal=n)
def scalar(n,value): return step("scalar",ordinal=n,fact=value)
def count(n,value): return step("count",ordinal=n,fact=value)
def aux(n,field): return step("aux",ordinal=n,field=field)
def reconcile(n,owner="ownerA"): return step("reconcile",ordinal=n,owner_ref=owner)
def returned(n): return step("wrapper_return",ordinal=n)
def stop(n,phase="RawReturn_allocation",ref="err0"): return step("raise",ordinal=n,phase=phase,exception_ref=ref)


def initial_slot(identity="f0",kind="original_file",value=None,closer="CloseHandle",capability=None):
    return dict(id=identity,kind=kind,handle_fact=U if value is None else H(value),closer=closer,
        identity_capability_ref=capability,close_state="none" if value is None else "available")


def expected_slot(identity="f0",value=None,liveness="no_handle",right="none",closer="CloseHandle",closes=0,success=None):
    return dict(id=identity,handle_fact=U if value is None else H(value),liveness=liveness,close_right=right,
        closer=closer,close_invocations=closes,close_success=success)


def expected_record(n,api,value=U,raw_count=U,*,invoked=True,scalar_aux=False,count_aux=False,right_aux=False,
        defined=False,count_state="not_applicable",wrapper="raised",error=U,error_defined=False):
    return dict(ordinal=n,api=api,invocation_reserved=invoked,raw_scalar=value,raw_count=raw_count,
        scalar_aux_ack=scalar_aux,count_aux_ack=count_aux,right_transfer_ack=right_aux,
        count_defined=defined,count_state=count_state,wrapper_state=wrapper,raw_error=error,error_defined=error_defined)


def initial(slots=(),buffers=(),now=0,early=False,primary=None,error_class="RuntimeError"):
    kinds=dict(ownerA="owner",originA="origin",nonceA="nonce",registryA="registry",portA="port",outputA="output",
        loaderA="loader",journalA="journal",contextA="source_context",foreignOrigin="origin",foreignOwner="owner",foreignContext="source_context",
        identityA="file_identity",identityEarly="file_identity",buf0="buffer",err0="exception",err1="exception")
    refs={key:key+"A" for key in ("owner","origin","nonce","registry","port","output","loader","journal")}
    refs["early_context"]="contextA" if early else None
    source=None
    if early:
        source=dict(context_ref="contextA",slot_refs=["early"],blob_hex=b"early".hex(),digest=hashlib.sha256(b"early").hexdigest(),
            known_read_bytes=5,hashed_bytes=5,captured_bytes=5,event_sequence=7,scope="HARNESS_ONLY")
        slots=tuple(slots)+(initial_slot("early",value=301,capability="identityEarly"),)
    return dict(objects=[dict(id=key,kind=value,scope="HARNESS_ONLY") for key,value in kinds.items()],current=refs,
        clock=dict(start_ns=0,now_ns=now,work_end_ns=295000000000,hard_end_ns=300000000000),slots=list(slots),
        buffers=list(buffers),exceptions=[dict(id="err0",**{"class":error_class},message="authored first stop"),
            dict(id="err1",**{"class":"RuntimeError"},message="authored later cleanup stop")],
        primary_exception_ref=primary,early_context=source,identity_prefix=[])


def buffer(value="616263",capacity=3): return dict(id="buf0",generation=0,capacity=capacity,hex=value)
def expected_buffer(value="616263",reusable=False): return dict(id="buf0",generation=0,hex=value,retained=True,reusable=reusable)


def expected(disposition="incomplete_unknown",primary="err0",code="wrapper_exception",secondary=(),secondary_codes=(),counters=(0,0,0,0,0,0),
        records=(),slots=(),buffers=(),namespace=False,ready=False,read=0,read_unknown=False,write=0,write_unknown=False,
        hashed=0,captured=0,claims=0,now=0,event=0):
    names=("logical_call_reservations","FFI_invocations_reserved","known_scalar_returns","known_count_values","portable_wrapper_returns","unique_reconciled_ordinals")
    return dict(disposition=disposition,primary_exception_ref=primary,primary_code=code,secondary_exception_refs=list(secondary),secondary_codes=list(secondary_codes),
        counters=dict(zip(names,counters)),records=list(records),slots=list(slots),buffers=list(buffers),namespace_owned=namespace,
        reservation_ready=ready,known_read_bytes=read,read_count_unknown=read_unknown,known_write_bytes=write,write_count_unknown=write_unknown,
        hashed_bytes=hashed,captured_bytes=captured,handoff=dict(claims=claims,same_objects=claims==1,origin_start_ns=0,origin_now_ns=now,
            next_event_sequence=event,new_origins=0,new_output_reservations=0,early_source_reopens=0),
        qualification=dict(FFI_registration_proven=False,production_owner_bound=False,originals_authenticated=False,profile_qualified=False,runtime_authorized=False))


cases=[]
def case(identity,family,variant,setup,steps,outcome,checkpoints=()):
    cases.append(dict(id=identity,family=family,variant=variant,initial=setup,steps=steps,checkpoints=list(checkpoints),expected=outcome))


def close(n,slot="f0",api="CloseHandle",value=1,wrapper=True):
    # Literal input sequence; no outcome/counter computation.
    return [reserve(n,api,slot),invoke(n),scalar(n,B(value)),returned(n) if wrapper else stop(n,"close_wrapper"),reconcile(n)]


# Coherent primitive success: a predeclared HARNESS_ONLY inspected file, one
# successful read/copy/hash and one close. It does NOT claim a full bootstrap.
case("success_read_capture_close","success","primitive_success",initial([initial_slot(value=101,capability="identityA")],[buffer()]),
    [reserve(0,"ReadFile","f0",3,"buf0"),invoke(0),scalar(0,B(1)),count(0,N(3)),aux(0,"scalar_aux_ack"),aux(0,"count_aux_ack"),
     returned(0),reconcile(0),step("copy",ordinal=0),step("hash",ordinal=0),*close(1)],
    expected("primitive_complete",None,None,counters=(2,2,2,1,2,2),
        records=[expected_record(0,"ReadFile",B(1),N(3),scalar_aux=True,count_aux=True,defined=True,count_state="known_defined",wrapper="returned"),
            expected_record(1,"CloseHandle",B(1),wrapper="returned")],slots=[expected_slot(value=101,liveness="closed_known",right="consumed",closes=1,success=True)],
        buffers=[expected_buffer(reusable=True)],read=3,hashed=3,captured=3))
case("cutoff_before_invocation","pre_dispatch_cutoff","no_C_invocation",initial([initial_slot()],now=294000000000,error_class="TimeoutError"),
    [reserve(0,"CreateFileW","f0"),step("clock",now_ns=300000000000),stop(0,"pre_dispatch")],
    expected("incomplete_deadline",code="deadline",counters=(1,0,0,0,0,0),
        records=[expected_record(0,"CreateFileW",invoked=False)],slots=[expected_slot()],now=300000000000))

for identity,phase,ack,error in (("open_wrapper_allocation","RawReturn_allocation",True,"MemoryError"),
        ("open_first_fact_before_aux","after_scalar_before_aux",False,"KeyboardInterrupt"),
        ("open_first_fact_before_right_transfer","after_scalar_before_right_transfer",False,"SystemExit")):
    ops=[reserve(0,"CreateFileW","f0"),invoke(0),scalar(0,H(101))]
    if ack: ops+=[aux(0,"scalar_aux_ack")]
    checkpoint=dict(after_step=len(ops)-1,projection={"record0.raw_scalar":H(101),"record0.scalar_aux_ack":ack,
        "record0.right_transfer_ack":False,"counters.known_scalar_returns":1,"counters.unique_reconciled_ordinals":0})
    case(identity,"handle_then_error_copy",phase,initial([initial_slot()],error_class=error),ops+[stop(0,phase),reconcile(0),*close(1)],
        expected(counters=(2,2,2,0,1,2),records=[expected_record(0,"CreateFileW",H(101),scalar_aux=ack),
            expected_record(1,"CloseHandle",B(1),wrapper="returned")],slots=[expected_slot(value=101,liveness="closed_known",right="consumed",closes=1,success=True)]),[checkpoint])

for identity,fact,liveness,disposition,code in (("observed_INVALID_handle",H(2**64-1),"no_handle","incomplete_known_failure","raw_failure"),
        ("observed_NULL_handle",atom("NULL"),"ownership_unknown","incomplete_unknown","open_unknown"),
        ("observed_numeric_zero_handle",H(0),"ownership_unknown","incomplete_unknown","open_unknown")):
    out_slot=expected_slot(liveness=liveness); out_slot["handle_fact"]=fact
    case(identity,"INVALID_and_NULL",fact["tag"]+str(fact["value"]),initial([initial_slot()]),
        [reserve(0,"CreateFileW","f0"),invoke(0),scalar(0,fact),returned(0),reconcile(0)],
        expected(disposition,None,code,counters=(1,1,1,0,1,1),records=[expected_record(0,"CreateFileW",fact,wrapper="returned")],slots=[out_slot]))

read_init=initial([initial_slot(value=101,capability="identityA")],[buffer()],error_class="MemoryError")
read_partial=[reserve(0,"ReadFile","f0",3,"buf0"),invoke(0),scalar(0,B(1)),count(0,N(3)),stop(0,"after_count_before_aux"),reconcile(0)]
case("read_count_fact_before_aux","read_count_then_copy_failure","known3_before_aux",read_init,read_partial+close(1),
    expected(counters=(2,2,2,1,1,2),records=[expected_record(0,"ReadFile",B(1),N(3),defined=True,count_state="known_defined"),
        expected_record(1,"CloseHandle",B(1),wrapper="returned")],slots=[expected_slot(value=101,liveness="closed_known",right="consumed",closes=1,success=True)],
        buffers=[expected_buffer()],read=3),
    [dict(after_step=3,projection={"record0.raw_count":N(3),"record0.count_aux_ack":False,"counters.known_count_values":1,"known_read_bytes":3,"counters.unique_reconciled_ordinals":0})])
case("incremental_scalar_then_count_fold","read_count_then_copy_failure","incremental_idempotence",initial([initial_slot(value=101,capability="identityA")],[buffer()]),
    [reserve(0,"ReadFile","f0",3,"buf0"),invoke(0),scalar(0,B(1)),reconcile(0),count(0,N(3)),reconcile(0),reconcile(0),
        returned(0),step("copy",ordinal=0),step("hash",ordinal=0),*close(1)],
    expected("primitive_complete",None,None,counters=(2,2,2,1,2,2),records=[expected_record(0,"ReadFile",B(1),N(3),defined=True,count_state="known_defined",wrapper="returned"),
        expected_record(1,"CloseHandle",B(1),wrapper="returned")],slots=[expected_slot(value=101,liveness="closed_known",right="consumed",closes=1,success=True)],
        buffers=[expected_buffer(reusable=True)],read=3,hashed=3,captured=3),
    [dict(after_step=3,projection={"record0.count_state":"pending","counters.known_scalar_returns":1,"counters.known_count_values":0,"counters.unique_reconciled_ordinals":1}),
     dict(after_step=6,projection={"record0.count_state":"known_defined","counters.known_scalar_returns":1,"counters.known_count_values":1,"counters.unique_reconciled_ordinals":1,"known_read_bytes":3})])
case("pending_count_wrapper_stop","false_or_undefined_read","no_late_invented_count",initial([initial_slot(value=101,capability="identityA")],[buffer()]),
    [reserve(0,"ReadFile","f0",3,"buf0"),invoke(0),scalar(0,B(1)),stop(0,"RawReturn_allocation"),reconcile(0),*close(1)],
    expected(counters=(2,2,2,0,1,2),records=[expected_record(0,"ReadFile",B(1),count_state="return_unknown"),
        expected_record(1,"CloseHandle",B(1),wrapper="returned")],slots=[expected_slot(value=101,liveness="closed_known",right="consumed",closes=1,success=True)],
        buffers=[expected_buffer()],read_unknown=True))
for identity,flag,defined,state,disp,code,unknown in (("failed_read_observed_zero",0,False,"known_undefined","incomplete_unknown","count_unknown",True),
        ("successful_defined_zero",1,True,"known_defined","incomplete_known_failure","raw_failure",False)):
    case(identity,"false_or_undefined_read","observed_count0",initial([initial_slot(value=101,capability="identityA")],[buffer("")]),
        [reserve(0,"ReadFile","f0",3,"buf0"),invoke(0),scalar(0,B(flag)),count(0,N(0)),returned(0),reconcile(0),*close(1)],
        expected(disp,None,code,counters=(2,2,2,1,2,2),records=[expected_record(0,"ReadFile",B(flag),N(0),defined=defined,count_state=state,wrapper="returned"),
            expected_record(1,"CloseHandle",B(1),wrapper="returned")],slots=[expected_slot(value=101,liveness="closed_known",right="consumed",closes=1,success=True)],
            buffers=[expected_buffer("")],read_unknown=unknown))

case("write_known_before_hard_cutoff","write_count_then_late_clock","known4_not_hash_pin",initial([initial_slot("out",kind="output_file",value=201,capability="identityA")],now=299000000000,error_class="TimeoutError"),
    [reserve(0,"WriteFile","out",4,None,"41424344"),invoke(0),scalar(0,B(1)),count(0,N(4)),step("clock",now_ns=300000000000),
        stop(0,"post_call_clock"),reconcile(0)],
    expected("incomplete_deadline",code="deadline",counters=(1,1,1,1,0,1),
        records=[expected_record(0,"WriteFile",B(1),N(4),defined=True,count_state="known_defined")],
        slots=[expected_slot("out",201,"owned_live","available")],write=4,now=300000000000))
for identity,kind,handle,closer in (("file_close_first_fact_wrapper_stop","original_file",101,"CloseHandle"),
        ("search_close_first_fact_wrapper_stop","search",501,"FindClose")):
    case(identity,"close_return_then_wrapper_failure","known_close_without_aux",initial([initial_slot(kind=kind,value=handle,closer=closer)]),
        close(0,api=closer,wrapper=False),expected(counters=(1,1,1,0,0,1),records=[expected_record(0,closer,B(1))],
            slots=[expected_slot(value=handle,liveness="closed_known",right="consumed",closer=closer,closes=1,success=True)]))
fourth_initial=initial([initial_slot(value=101)],[buffer("0300000000000000",8)],now=294000000000,error_class="TimeoutError")
fourth_initial["identity_prefix"]=[dict(slot_ref="f0",query_names=["GetFileType","GetFileInformationByHandleEx","GetFinalPathNameByHandleW"],scope="HARNESS_ONLY")]
case("identity_fourth_query_late","query_fourth_return_then_expiry","no_content_after_expiry",fourth_initial,
    [reserve(0,"GetFileSizeEx","f0",None,"buf0"),invoke(0),scalar(0,B(1)),step("clock",now_ns=295000000000),
        stop(0,"identity_query"),reconcile(0),*close(1)],
    expected("incomplete_deadline",code="deadline",counters=(2,2,2,0,1,2),records=[expected_record(0,"GetFileSizeEx",B(1)),
        expected_record(1,"CloseHandle",B(1),wrapper="returned")],slots=[expected_slot(value=101,liveness="closed_known",right="consumed",closes=1,success=True)],
        buffers=[expected_buffer("0300000000000000")],now=295000000000))
case("invocation_without_scalar_fact","unreturned_invocation","conversion_window_unknown",initial([initial_slot()],error_class="MemoryError"),
    [reserve(0,"CreateFileW","f0"),invoke(0),stop(0,"RawReturn_allocation"),reconcile(0)],
    expected(code="return_unknown",counters=(1,1,0,0,0,1),records=[expected_record(0,"CreateFileW")],
        slots=[expected_slot(liveness="ownership_unknown")]))

for identity,error,declared,disp,code in (("search_initial2_declared_empty",2,True,"primitive_complete",None),
        ("search_initial18_not_empty",18,True,"incomplete_known_failure","initial_search18")):
    # Raw last-error facts are part of the close search rule extension below.
    case(identity,"search_boundary","initial_INVALID_error"+str(error),initial([initial_slot(kind="search",closer="FindClose")],[buffer("",592)]),
        [reserve(0,"FindFirstFileExW","f0",buffer_ref="buf0",declared_empty=declared),invoke(0),scalar(0,H(2**64-1)),step("error",ordinal=0,fact=atom("DWORD",error),defined=True),returned(0),reconcile(0)],
        expected(disp,None,code,counters=(1,1,1,0,1,1),records=[expected_record(0,"FindFirstFileExW",H(2**64-1),wrapper="returned",error=atom("DWORD",error),error_defined=True)],
            slots=[dict(expected_slot(liveness="no_handle",closer="FindClose"),handle_fact=H(2**64-1))],buffers=[expected_buffer("")]))


case("search_next18_then_findclose","search_boundary","natural_end_after_known_search",initial([initial_slot(kind="search",value=501,closer="FindClose")],[buffer("",592)]),
    [reserve(0,"FindNextFileW","f0",None,"buf0"),invoke(0),scalar(0,B(0)),step("error",ordinal=0,fact=atom("DWORD",18),defined=True),
        returned(0),reconcile(0),*close(1,api="FindClose")],
    expected("primitive_complete",None,None,counters=(2,2,2,0,2,2),records=[expected_record(0,"FindNextFileW",B(0),wrapper="returned",error=atom("DWORD",18),error_defined=True),
        expected_record(1,"FindClose",B(1),wrapper="returned")],slots=[expected_slot(value=501,liveness="closed_known",right="consumed",closer="FindClose",closes=1,success=True)],
        buffers=[expected_buffer("")]))
case("namespace_first_flag_before_wrapper","namespace_partial","owned_not_ready",initial([initial_slot("dir",kind="namespace",closer=None)]),
    [reserve(0,"CreateDirectoryW","dir"),invoke(0),scalar(0,B(1)),stop(0,"error_copy"),reconcile(0)],
    expected(counters=(1,1,1,0,0,1),records=[expected_record(0,"CreateDirectoryW",B(1))],slots=[expected_slot("dir",closer=None)],namespace=True),
    [dict(after_step=2,projection={"record0.raw_scalar":B(1),"namespace_owned":True,"reservation_ready":False})])

open_return=[reserve(0,"CreateFileW","f0"),invoke(0),scalar(0,H(101)),returned(0)]
open_and_close_records=[expected_record(0,"CreateFileW",H(101),wrapper="returned"),expected_record(1,"CloseHandle",B(1),wrapper="returned")]
closed_f0=[expected_slot(value=101,liveness="closed_known",right="consumed",closes=1,success=True)]
case("same_ordinal_reconcile_twice","foreign_or_duplicate_adoption","idempotent_fold",initial([initial_slot()]),
    open_return+[reconcile(0),reconcile(0),*close(1)],
    expected("primitive_complete",None,None,counters=(2,2,2,0,2,2),records=open_and_close_records,slots=closed_f0),
    [dict(after_step=5,projection={"counters.known_scalar_returns":1,"counters.unique_reconciled_ordinals":1,"slot.f0.close_right":"available"})])
case("foreign_owner_reconcile_then_cleanup","foreign_or_duplicate_adoption","foreign_view_has_no_right",initial([initial_slot()]),
    open_return+[reconcile(0,"foreignOwner"),reconcile(0),*close(1)],
    expected("control_rejected",None,"foreign_reference",counters=(2,2,2,0,2,2),records=open_and_close_records,slots=closed_f0),
    [dict(after_step=4,projection={"counters.unique_reconciled_ordinals":0,"record0.raw_scalar":H(101)})])
case("conflicting_reserve_keeps_original","foreign_or_duplicate_adoption","duplicate_ordinal",initial([initial_slot()],[buffer()]),
    open_return+[reconcile(0),reserve(0,"ReadFile","f0",3,"buf0"),*close(1)],
    expected("control_rejected",None,"duplicate_ordinal",counters=(2,2,2,0,2,2),records=open_and_close_records,slots=closed_f0))
case("repeated_invoke_no_second_dispatch","foreign_or_duplicate_adoption","duplicate_invocation",initial([initial_slot()]),
    open_return+[reconcile(0),invoke(0),*close(1)],
    expected("control_rejected",None,"duplicate_invocation",counters=(2,2,2,0,2,2),records=open_and_close_records,slots=closed_f0))
case("wrong_closer_then_correct_once","foreign_or_duplicate_adoption","wrong_closer",initial([initial_slot(value=101)]),
    [reserve(0,"FindClose","f0"),*close(1)],
    expected("control_rejected",None,"wrong_closer",counters=(1,1,1,0,1,1),records=[expected_record(1,"CloseHandle",B(1),wrapper="returned")],slots=closed_f0))

for identity,foreign,repeat,disp,code in (("same_owner_early_handoff",False,False,"primitive_complete",None),
        ("same_numeric_start_foreign_origin",True,False,"control_rejected","foreign_reference"),
        ("same_owner_second_handoff_rejected",False,True,"control_rejected","handoff_repeated")):
    setup=initial(early=True,now=289000000000); refs=copy.deepcopy(setup["current"])
    if foreign: refs["origin"]="foreignOrigin"
    ops=[step("clock",now_ns=289500000000),step("handoff",refs=refs)]
    if repeat: ops.append(step("handoff",refs=copy.deepcopy(refs)))
    # Lease remains live for the adopted continuation; this is a handoff slice,
    # not a full finalizer or permission to execute captured sources.
    case(identity,"same_owner_early_context","typed_current_context",setup,ops,
        expected(disp,None,code,slots=[expected_slot("early",301,"owned_live","available")],read=5,hashed=5,captured=5,
            claims=0 if foreign else 1,now=289500000000,event=7 if foreign else 8))

case("existing_primary_known_close_false","existing_primary_and_late_cleanup","original_object_wins",initial([initial_slot(value=101)],primary="err0"),
    [reserve(0,"CloseHandle","f0"),invoke(0),scalar(0,B(0)),stop(0,"close_wrapper","err1"),reconcile(0)],
    expected(code="existing_primary",secondary=["err1"],secondary_codes=["wrapper_exception"],counters=(1,1,1,0,0,1),
        records=[expected_record(0,"CloseHandle",B(0))],slots=[expected_slot(value=101,liveness="close_failed_known",right="consumed",closes=1,success=False)]))
case("buffer_generation_retained_after_stop","read_count_then_copy_failure","reject_reuse_after_known_read",read_init,
    read_partial+[step("reuse_buffer",buffer_ref="buf0",new_generation=1,hex="646566"),*close(1)],
    expected(secondary_codes=["buffer_reuse"],counters=(2,2,2,1,1,2),records=[expected_record(0,"ReadFile",B(1),N(3),defined=True,count_state="known_defined"),
        expected_record(1,"CloseHandle",B(1),wrapper="returned")],slots=closed_f0,buffers=[expected_buffer()],read=3))


def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def main():
    assert not TARGET.exists()
    schema=HERE/"ADOPTION-FIXTURE-SCHEMA-v1.json"; scope=PORTS/"FILE-PORTS-ADOPTION-ROOT-FIXTURE-SCOPE-v1.json"
    assert pin(scope)["sha256"]=="3b1a273a71bad198367f3d06c20f875e050c57c867b1ee9d05c3a68476244811"
    document=json.loads(schema.read_bytes())
    assert len(cases)==32 and {case["family"] for case in cases}==set(document["families"])
    result=dict(schema_version=1,status="AUTHORED_CLOSED_FICTIONAL_ADOPTION_VECTORS_BEFORE_IMPLEMENTATION",
        schema=pin(schema),root_scope=pin(scope),design=pin(PORTS/"FILE-PORTS-ADOPTION-SEAM-DESIGN-v1.json"),
        design_freeze=pin(PORTS/"FILE-PORTS-ADOPTION-SEAM-FREEZE-v1.json"),author=pin(Path(__file__).resolve()),cases=cases,
        expectation_provenance="All expected states/counters are authored literal arguments above. The author only frames/duplicates JSON; no transition interpreter, adopter, FFI, helper, source loader or gate was executed.",
        API_counter_scope="New fictional calls in this trace only. Preexisting HARNESS_ONLY early capture byte counts are explicitly carried, not reset or represented as a fresh measured native API census.",
        actual_API_calls=0,successor_implementation_exists=False,production_authority=False,profile_qualified=False)
    with TARGET.open("xb") as out: out.write(json.dumps(result,sort_keys=True,indent=2).encode("utf-8")+b"\n")
    print(json.dumps(dict(fixture=pin(TARGET),schema=pin(schema),cases=len(cases))))


if __name__=="__main__": main()
