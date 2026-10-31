"""Named pre-build structural corrections; originals and expected tests stay fixed."""
from pathlib import Path
import hashlib
import json

base=Path(__file__).resolve().parent
source=base/"preflight_file14_raw_v2.c"
old=source.read_text(encoding="utf-8")
old_raw=source.read_bytes()
if hashlib.sha256(old_raw).hexdigest()!="ab117f5bd8c8411c7f3a7c451e7576c4acf858a9477d2f728136a75f053e7fc0":
    raise ValueError("Expected unchanged V2")
marker="static int has_count(unsigned api) { return api==6 || api==13; }\n"
helper="""static unsigned frame_bytes(unsigned api) {
    return api==3 || api==5 ? 8 : api==4 ? 8202 : api==8 ? 36 :
           api==9 || api==10 ? 592 : 0;
}
static int metadata_valid(unsigned api,unsigned actor,unsigned target_kind,
    uint64_t target_generation,uint32_t requested,uint64_t handle_bits,
    uint32_t buffer_id,uint32_t buffer_generation,uint32_t capacity,uint32_t flags) {
    return api>=1 && api<=14 && actor<=7 && target_kind>=1 && target_kind<=5 &&
        target_generation && !(flags & ~35u) &&
        (!!(flags & PF14_REQUESTED) == has_count(api)) &&
        (!!(flags & PF14_INPUT_HANDLE) == has_handle(api)) &&
        ((flags & PF14_REQUESTED) || !requested) &&
        ((flags & PF14_INPUT_HANDLE) || !handle_bits) &&
        (!has_handle(api) || (handle_bits && handle_bits!=UINT64_MAX)) &&
        (!!(flags & PF14_CLOSE_CONSUMED) == (api==7 || api==11)) &&
        (buffer_id!=UINT32_MAX || (!buffer_generation && !capacity)) &&
        (buffer_id==UINT32_MAX || (buffer_generation && capacity)) &&
        (!has_count(api) || (buffer_id!=UINT32_MAX && requested && requested<=capacity)) &&
        (!frame_bytes(api) || (buffer_id!=UINT32_MAX && capacity>=frame_bytes(api)));
}
"""
if old.count(marker)!=1:raise ValueError("Unique helper insertion")
new=old.replace(marker,marker+helper)
start=new.index("    if (!c || ((uintptr_t)c & 15) || !generation || api<1")
end=new.index("    memset(c,0,sizeof(*c));",start)
new=new[:start]+"""    if (!c || ((uintptr_t)c & 15) || !generation ||
        !metadata_valid(api,actor,target_kind,target_generation,requested,handle_bits,
                        buffer_id,buffer_generation,capacity,flags))
        return PF14_INVALID;
"""+new[end:]
start=new.index("static int begin(volatile PF14Cell *c,const PF14Functions *f,unsigned api) {")
end=new.index("static void publish(volatile PF14Axis *a) {",start)
new=new[:start]+"""static int begin(volatile PF14Cell *c,const PF14Functions *f,unsigned api) {
    unsigned i;
    LONG phase;
    if (!c || ((uintptr_t)c & 15) || !f || !f->last_error ||
        c->header.schema!=1 || c->header.slot_bytes!=256 || c->header.api_id!=api ||
        !c->header.generation)
        return PF14_INVALID;
    phase=c->header.native_exit_phase;
    if (phase==1 || phase==2) return PF14_ALREADY_ENTERED;
    if (phase!=0 || !metadata_valid(api,c->header.actor_id,c->header.target_kind,
        c->header.target_generation,c->header.requested,c->header.input_handle_bits,
        c->header.buffer_id,c->header.buffer_generation,c->header.buffer_capacity,
        c->header.predeclared_flags) || c->header.reserved28 || c->header.conversion_phase ||
        c->header.query_capture_state || c->header.count_out_scratch!=0xa5a5a5a5u ||
        c->header.count_scratch_initial_pattern!=0xa5a5a5a5u ||
        !axis_empty(&c->scalar,scalar_kind(api),c->header.generation) ||
        !axis_empty(&c->count,PF14_COUNT32,c->header.generation) ||
        !axis_empty(&c->error_value,PF14_DWORD32,c->header.generation) ||
        !axis_empty(&c->error_definition,PF14_DEFINEDNESS,c->header.generation))
        return PF14_INVALID;
    for (i=0;i<48;i++) if (c->header.reserved80[i]) return PF14_INVALID;
    if (_InterlockedCompareExchange(&c->header.native_exit_phase,1,0)!=0)
        return PF14_ALREADY_ENTERED;
    c->header.predeclared_flags |= PF14_NATIVE_ENTERED;
    return PF14_OK;
}
"""+new[end:]
raw=new.encode()
output=base/"preflight_file14_raw_v3.c"
with output.open("xb")as stream:stream.write(raw)
record=dict(schema_version=1,status="ROOT_STATIC_FINDINGS_AND_NAMED_SOURCE_CORRECTION_NOT_EXECUTED",
    before=dict(path=str(source),bytes=len(old_raw),sha256=hashlib.sha256(old_raw).hexdigest()),
    after=dict(path=str(output),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    findings=[
        dict(id="C2",deduction="V2 checks nonempty axes before its once-only phase, so repeated committed/partial calls reach INVALID rather than declared ALREADY_ENTERED. No second target call occurs, but the expected status is wrong.",change="Recognize valid ENTERED/RAW_EXIT_PREPARED phase before empty-axis checks; preserve existing no-second-dispatch CAS."),
        dict(id="C3",deduction="V2 begin does not revalidate initializer metadata: unknown flags, absent handle/buffer metadata and cleared close-reservation flags can reach a fake target after a trusted test corrupts a fresh cell.",change="One common metadata_valid guard for initialization and fresh invocation. It is a structural guard only, not authentication of caller-owned bits."),
        dict(id="C4",deduction="V2 typed query wrappers use fixed8/8202/36/592-byte output frames without checking that the reserved buffer metadata has a present id/generation and sufficient capacity.",change="Validate fixed per-API frame-capacity metadata before dispatch in initializer and begin. Actual pointer bounds/lifetimes still require the absent genuine ticket bridge.")],
    provenance="Root source deductions while comparing the independent authored79-case oracle with V2. No C build or execution observed; expectations are retained. Independent static review of V3 remains required.",
    unchanged="Header/layout,14 typed wrapper bodies, direct scalar stores, publish/finish and phase meanings unchanged; originalV1/V2 and their reviews retained.",
    activity=dict(subject_builds=0,subject_runs=0,SDK_or_FFI_calls=0,original_target_reads=0))
with(base/"NATIVE-CARRIER-METADATA-CORRECTION-v3.json").open("x",encoding="utf-8")as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
if source.read_bytes()!=old_raw:raise ValueError("V2 preservation")
print(json.dumps(record["after"]))
