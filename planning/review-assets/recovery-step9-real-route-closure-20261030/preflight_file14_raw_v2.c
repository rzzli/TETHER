/* Source-only component. See NATIVE-CARRIER-SOURCE-DESIGN-v1.md for limits. */
#include "preflight_file14_raw_v1.h"
#include <intrin.h>
#include <string.h>
#pragma intrinsic(_InterlockedExchange)
#pragma intrinsic(_InterlockedCompareExchange)

static unsigned scalar_kind(unsigned api) {
    return api==1 || api==9 ? PF14_HANDLE64 :
           api==2 || api==4 ? PF14_DWORD32 : PF14_BOOL32;
}
static unsigned width(unsigned kind) {
    return kind==PF14_HANDLE64 ? 8 : kind==PF14_DEFINEDNESS ? 1 : 4;
}
static int has_handle(unsigned api) {
    return api==2 || api==3 || api==4 || api==5 || api==6 || api==7 ||
           api==10 || api==11 || api==13 || api==14;
}
static int has_count(unsigned api) { return api==6 || api==13; }
static void axis_initialize(PF14Axis *a,unsigned kind,uint32_t epoch) {
    a->epoch=epoch; a->kind=(uint16_t)kind; a->width=(uint8_t)width(kind);
}
int pf14_initialize(PF14Cell *c,uint32_t ordinal,uint32_t generation,
    uint16_t api,uint8_t actor,uint8_t target_kind,uint32_t target_ordinal,
    uint64_t target_generation,uint32_t requested,uint64_t handle_bits,
    uint32_t buffer_id,uint32_t buffer_generation,uint32_t capacity,uint32_t flags) {
    if (!c || ((uintptr_t)c & 15) || !generation || api<1 || api>14 || actor>7 ||
        target_kind<1 || target_kind>5 || !target_generation || (flags & ~35u) ||
        (!!(flags & PF14_REQUESTED) != has_count(api)) ||
        (!!(flags & PF14_INPUT_HANDLE) != has_handle(api)) ||
        (!(flags & PF14_REQUESTED) && requested) ||
        (!(flags & PF14_INPUT_HANDLE) && handle_bits) ||
        (has_handle(api) && (!handle_bits || handle_bits==UINT64_MAX)) ||
        ((api==7 || api==11) && !(flags & PF14_CLOSE_CONSUMED)) ||
        ((api!=7 && api!=11) && (flags & PF14_CLOSE_CONSUMED)) ||
        (buffer_id==UINT32_MAX && (buffer_generation || capacity)) ||
        (buffer_id!=UINT32_MAX && (!buffer_generation || !capacity)) ||
        (has_count(api) && (buffer_id==UINT32_MAX || requested==0 || requested>capacity)))
        return PF14_INVALID;
    memset(c,0,sizeof(*c));
    c->header.schema=1; c->header.slot_bytes=256;
    c->header.ordinal=ordinal; c->header.generation=generation;
    c->header.api_id=api; c->header.actor_id=actor; c->header.target_kind=target_kind;
    c->header.target_ordinal=target_ordinal; c->header.target_generation=target_generation;
    c->header.requested=requested; c->header.predeclared_flags=flags;
    c->header.input_handle_bits=handle_bits; c->header.buffer_id=buffer_id;
    c->header.buffer_generation=buffer_generation; c->header.buffer_capacity=capacity;
    c->header.count_out_scratch=0xa5a5a5a5u;
    c->header.count_scratch_initial_pattern=0xa5a5a5a5u;
    axis_initialize(&c->scalar,scalar_kind(api),generation);
    axis_initialize(&c->count,PF14_COUNT32,generation);
    axis_initialize(&c->error_value,PF14_DWORD32,generation);
    axis_initialize(&c->error_definition,PF14_DEFINEDNESS,generation);
    return PF14_OK;
}
static int axis_empty(volatile PF14Axis *a,unsigned kind,uint32_t epoch) {
    return a->payload.u64==0 && a->epoch==epoch && a->kind==kind &&
        a->width==width(kind) && !a->reserved15 && !a->stage_hint &&
        !a->commit && !a->reserved24;
}
/* One-call guard is structural only, NOT a trusted ticket or ownership proof. */
static int begin(volatile PF14Cell *c,const PF14Functions *f,unsigned api) {
    unsigned i;
    if (!c || ((uintptr_t)c & 15) || !f || !f->last_error ||
        c->header.schema!=1 || c->header.slot_bytes!=256 || c->header.api_id!=api ||
        !c->header.generation || c->header.reserved28 || c->header.conversion_phase ||
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
static void publish(volatile PF14Axis *a) {
    a->stage_hint=1;
    (void)_InterlockedExchange(&a->commit,1); /* Full barrier, stronger than release. */
}
static int finish(volatile PF14Cell *c,const PF14Functions *f,int probe) {
    c->error_definition.payload.u8=(uint8_t)(probe ? 1 : 0);
    publish(&c->error_definition);
    if (probe) {
        /* No Win32/Python helper between target return and this transport. */
        c->error_value.payload.u32=f->last_error();
        publish(&c->error_value);
    }
    if (has_count(c->header.api_id)) {
        c->count.payload.u32=c->header.count_out_scratch;
        publish(&c->count); /* Raw contents; FALSE/count0 is NOT defined progress. */
    }
    c->header.predeclared_flags |= PF14_RAW_EXIT;
    (void)_InterlockedExchange(&c->header.native_exit_phase,2);
    return PF14_OK;
}
#define HANDLE_INPUT(c) ((HANDLE)(uintptr_t)((c)->header.input_handle_bits))
#define START(api,member) int status; if (!f || !f->member) return PF14_INVALID; \
    status=begin(c,f,api); if (status!=PF14_OK) return status
#define BOOL_RESULT(expr) c->scalar.payload.u32=(uint32_t)(expr); \
    publish(&c->scalar); return finish(c,f,c->scalar.payload.u32==0)
#define DWORD_RESULT(expr) BOOL_RESULT(expr)
#define HANDLE_RESULT(expr) c->scalar.payload.u64=(uint64_t)(uintptr_t)(expr); \
    publish(&c->scalar); return finish(c,f,c->scalar.payload.u64==UINT64_MAX)

int pf14_create_file(volatile PF14Cell *c,const PF14Functions *f,LPCWSTR path,
    DWORD access,DWORD sharing,LPSECURITY_ATTRIBUTES security,DWORD disposition,
    DWORD attributes,HANDLE template_handle) {
    if (!path) return PF14_INVALID;
    START(1,create_file);
    HANDLE_RESULT(f->create_file(path,access,sharing,security,disposition,attributes,template_handle));
}
int pf14_get_type(volatile PF14Cell *c,const PF14Functions *f) {
    START(2,get_type); DWORD_RESULT(f->get_type(HANDLE_INPUT(c)));
}
int pf14_get_information(volatile PF14Cell *c,const PF14Functions *f,FILE_ATTRIBUTE_TAG_INFO *frame) {
    if (!frame) return PF14_INVALID;
    START(3,get_information);
    BOOL_RESULT(f->get_information(HANDLE_INPUT(c),FileAttributeTagInfo,frame,8));
}
int pf14_get_path(volatile PF14Cell *c,const PF14Functions *f,WCHAR *frame) {
    if (!frame) return PF14_INVALID;
    START(4,get_path); DWORD_RESULT(f->get_path(HANDLE_INPUT(c),frame,4101,0));
}
int pf14_get_size(volatile PF14Cell *c,const PF14Functions *f,LARGE_INTEGER *frame) {
    if (!frame) return PF14_INVALID;
    START(5,get_size); BOOL_RESULT(f->get_size(HANDLE_INPUT(c),frame));
}
int pf14_read(volatile PF14Cell *c,const PF14Functions *f,void *buffer) {
    if (!buffer) return PF14_INVALID;
    START(6,read_file);
    BOOL_RESULT(f->read_file(HANDLE_INPUT(c),buffer,c->header.requested,
        (LPDWORD)&c->header.count_out_scratch,NULL));
}
int pf14_close(volatile PF14Cell *c,const PF14Functions *f) {
    START(7,close_handle); BOOL_RESULT(f->close_handle(HANDLE_INPUT(c)));
}
int pf14_get_attributes(volatile PF14Cell *c,const PF14Functions *f,LPCWSTR path,WIN32_FILE_ATTRIBUTE_DATA *frame) {
    if (!path || !frame) return PF14_INVALID;
    START(8,get_attributes); BOOL_RESULT(f->get_attributes(path,GetFileExInfoStandard,frame));
}
int pf14_find_first(volatile PF14Cell *c,const PF14Functions *f,LPCWSTR path,WIN32_FIND_DATAW *frame) {
    if (!path || !frame) return PF14_INVALID;
    START(9,find_first);
    HANDLE_RESULT(f->find_first(path,FindExInfoBasic,frame,FindExSearchNameMatch,NULL,0));
}
int pf14_find_next(volatile PF14Cell *c,const PF14Functions *f,WIN32_FIND_DATAW *frame) {
    if (!frame) return PF14_INVALID;
    START(10,find_next); BOOL_RESULT(f->find_next(HANDLE_INPUT(c),frame));
}
int pf14_find_close(volatile PF14Cell *c,const PF14Functions *f) {
    START(11,find_close); BOOL_RESULT(f->find_close(HANDLE_INPUT(c)));
}
int pf14_create_directory(volatile PF14Cell *c,const PF14Functions *f,LPCWSTR path) {
    if (!path) return PF14_INVALID;
    START(12,create_directory); BOOL_RESULT(f->create_directory(path,NULL));
}
int pf14_write(volatile PF14Cell *c,const PF14Functions *f,const void *buffer) {
    if (!buffer) return PF14_INVALID;
    START(13,write_file);
    BOOL_RESULT(f->write_file(HANDLE_INPUT(c),buffer,c->header.requested,
        (LPDWORD)&c->header.count_out_scratch,NULL));
}
int pf14_flush(volatile PF14Cell *c,const PF14Functions *f) {
    START(14,flush); BOOL_RESULT(f->flush(HANDLE_INPUT(c)));
}
