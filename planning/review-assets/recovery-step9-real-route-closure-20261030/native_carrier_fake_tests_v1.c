/* Independent finite fake-target tests. AUTHORING ONLY until Root build/run scope.
 * No real file/handle/path, loader, kernel ticket or native capability is used.
 * Expected bytes come from contracts16aa/4cf/08e and the public header, not C body.
 */
#include "preflight_file14_raw_v1.h"
#include <stdio.h>
#include <string.h>
#include <setjmp.h>

#define ARRAY_N(a) (sizeof(a) / sizeof((a)[0]))
#define SCRATCH UINT32_C(0xa5a5a5a5)
#define HANDLE_BITS UINT64_C(0x1234)
#define INVALID_BITS UINT64_C(0xffffffffffffffff)
#define REQUEST_N UINT32_C(16)

typedef struct Vector {
    const char *id;
    unsigned api;
    uint64_t scalar;
    uint32_t count, error;
    int writes_count, probes_error;
} Vector;

/* Literal scalar/error/count vectors. Nonzero BOOL bits are never normalized. */
static const Vector vectors[] = {
    {"A01_handle",1,HANDLE_BITS,0,77,0,0},
    {"A01_null",1,0,0,77,0,0},
    {"A01_invalid",1,INVALID_BITS,0,5,0,1},
    {"A02_disk",2,1,0,77,0,0},
    {"A02_unknown_error0",2,0,0,0,0,1},
    {"A02_raw2",2,2,0,77,0,0},
    {"A03_false",3,0,0,5,0,1},
    {"A03_bool2",3,2,0,77,0,0},
    {"A03_bool_minus1",3,UINT32_MAX,0,77,0,0},
    {"A04_length2",4,2,0,77,0,0},
    {"A04_zero",4,0,0,5,0,1},
    {"A04_required4101",4,4101,0,77,0,0},
    {"A05_false",5,0,0,5,0,1},
    {"A05_bool2",5,2,0,77,0,0},
    {"A05_bool_minus1",5,UINT32_MAX,0,77,0,0},
    {"A06_false_count0",6,0,0,5,1,1},
    {"A06_bool2_count16",6,2,16,77,1,0},
    {"A06_bool_minus1_count17",6,UINT32_MAX,17,77,1,0},
    {"A07_false",7,0,0,5,0,1},
    {"A07_bool2",7,2,0,77,0,0},
    {"A07_bool_minus1",7,UINT32_MAX,0,77,0,0},
    {"A08_false",8,0,0,5,0,1},
    {"A08_bool2",8,2,0,77,0,0},
    {"A08_bool_minus1",8,UINT32_MAX,0,77,0,0},
    {"A09_handle",9,HANDLE_BITS,0,77,0,0},
    {"A09_null",9,0,0,77,0,0},
    {"A09_invalid",9,INVALID_BITS,0,2,0,1},
    {"A10_end_error18",10,0,0,18,0,1},
    {"A10_bool2",10,2,0,77,0,0},
    {"A10_bool_minus1",10,UINT32_MAX,0,77,0,0},
    {"A11_false",11,0,0,5,0,1},
    {"A11_bool2",11,2,0,77,0,0},
    {"A11_bool_minus1",11,UINT32_MAX,0,77,0,0},
    {"A12_exists",12,0,0,183,0,1},
    {"A12_bool2",12,2,0,77,0,0},
    {"A12_bool_minus1",12,UINT32_MAX,0,77,0,0},
    {"A13_false_count0",13,0,0,5,1,1},
    {"A13_bool2_count16",13,2,16,77,1,0},
    {"A13_bool_minus1_count17",13,UINT32_MAX,17,77,1,0},
    {"A14_false",14,0,0,5,0,1},
    {"A14_bool2",14,2,0,77,0,0},
    {"A14_bool_minus1",14,UINT32_MAX,0,77,0,0},
    {"A06_true_count0",6,2,0,77,1,0},
    {"A13_true_count0",13,2,0,77,1,0},
    {"A06_false_unchanged_scratch",6,0,SCRATCH,0,0,1},
    {"A13_false_count7",13,0,7,0,1,1}
};

static PF14Cell cells[79];
static PF14Cell *current_cell;
static unsigned allocated_cells;
#define cell (*current_cell)
static __declspec(align(16)) unsigned char frame[8202];
static unsigned char final_copy[256], partial_copy[256];
static __declspec(align(16)) unsigned char misaligned_store[sizeof(PF14Cell)+16];
static const WCHAR path_text[] = L"D:\\OwnedSynthetic\\never-opened.bin";
static const WCHAR search_text[] = L"D:\\OwnedSynthetic\\never-searched-*";
static const unsigned char write_data[16] = {
    0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
};
static PF14Functions functions;
static const Vector *active;
static uint32_t current_ordinal;
static unsigned failures, checks, named_cases, init_attempts, wrapper_attempts;
static unsigned target_calls, error_entries, error_returns, partial_copies;
static unsigned current_partial_copies;
static int escape_error;
static jmp_buf error_escape;

static void check_at(int ok,const char *message,int line) {
    ++checks;
    if (!ok) {
        if (failures < 16) fprintf(stderr,"FAIL line=%d case=%s detail=%s\n",
            line,active ? active->id : "initializer",message);
        ++failures;
    }
}
#define CHECK(x,m) check_at(!!(x),(m),__LINE__)

static void copy256(unsigned char dst[256],const volatile PF14Cell *src) {
    const volatile unsigned char *p=(const volatile unsigned char *)src;
    unsigned i; for(i=0;i<256;++i) dst[i]=p[i];
}
static void put16(unsigned char *p,unsigned off,uint16_t n) {
    p[off]=(unsigned char)n;p[off+1]=(unsigned char)(n>>8);
}
static void put32(unsigned char *p,unsigned off,uint32_t n) {
    unsigned i;for(i=0;i<4;++i)p[off+i]=(unsigned char)(n>>(8*i));
}
static void put64(unsigned char *p,unsigned off,uint64_t n) {
    unsigned i;for(i=0;i<8;++i)p[off+i]=(unsigned char)(n>>(8*i));
}
static int has_count(unsigned api) { return api==6 || api==13; }
static int has_handle(unsigned api) {
    return (api>=2 && api<=7) || api==10 || api==11 || api==13 || api==14;
}
static unsigned frame_bytes(unsigned api) {
    switch(api) { case 3:case 5:return 8;case 4:return 8202;
        case 8:return 36;case 9:case 10:return 592;case 6:case 13:return 16;default:return 0; }
}
static unsigned actor(unsigned api) {
    return api<=7 ? 1 : api==8 ? 4 : api<=11 ? 5 : api==12 ? 6 : 2;
}
static unsigned target(unsigned api) {
    return api<=7 ? 1 : api==8 ? 2 : api<=11 ? 3 : api==12 ? 5 : 4;
}
static uint32_t base_flags(unsigned api) {
    return (has_count(api)?1u:0u) | (has_handle(api)?2u:0u) |
           ((api==7 || api==11)?32u:0u);
}
static void expected_axis(unsigned char *out,unsigned off,unsigned kind,
                          unsigned width,uint64_t value,int committed) {
    put64(out,off,value);put32(out,off+8,7);put16(out,off+12,(uint16_t)kind);
    out[off+14]=(unsigned char)width;
    if(committed) {put32(out,off+16,1);put32(out,off+20,1);}
}
/* phase0=initialized; phase1=fake LastError boundary; phase2=normal raw exit. */
static void expected256(unsigned char out[256],const Vector *v,unsigned phase) {
    unsigned k=v->api==1 || v->api==9 ? 1 : v->api==2 || v->api==4 ? 3 : 2;
    unsigned width=k==1 ? 8 : 4;unsigned cap=frame_bytes(v->api);
    uint32_t flags=base_flags(v->api);
    memset(out,0,256);
    put16(out,0,1);put16(out,2,256);put32(out,4,current_ordinal);put32(out,8,7);
    put16(out,12,(uint16_t)v->api);out[14]=(unsigned char)actor(v->api);
    out[15]=(unsigned char)target(v->api);put32(out,16,9);
    put32(out,20,has_count(v->api)?REQUEST_N:0);
    if(phase)flags|=4;if(phase==2)flags|=8;put32(out,24,flags);
    put64(out,32,19);put64(out,40,has_handle(v->api)?HANDLE_BITS:0);
    put32(out,48,cap?3:UINT32_MAX);put32(out,52,cap?5:0);put32(out,56,cap);
    put32(out,64,phase && has_count(v->api) && v->writes_count ? v->count : SCRATCH);
    put32(out,68,SCRATCH);put32(out,72,phase==2?2:phase?1:0);
    expected_axis(out,128,k,width,phase?v->scalar:0,phase!=0);
    expected_axis(out,160,4,4,phase==2 && has_count(v->api)?v->count:0,
                  phase==2 && has_count(v->api));
    expected_axis(out,192,3,4,phase==2 && v->probes_error?v->error:0,
                  phase==2 && v->probes_error);
    expected_axis(out,224,5,1,phase?v->probes_error:0,phase!=0);
}

static void target_enter(unsigned api) {
    ++target_calls;
    CHECK(active && active->api==api,"selected exact fake function");
    CHECK((cell.header.predeclared_flags&4u)!=0 &&
          cell.header.native_exit_phase==1,"entered before target");
    CHECK(cell.scalar.stage_hint==0 && cell.scalar.commit==0 &&
          cell.scalar.payload.u64==0,"no scalar before target return");
    CHECK(cell.count.commit==0 && cell.error_value.commit==0 &&
          cell.error_definition.commit==0,"other axes not invented before return");
    CHECK(cell.header.count_out_scratch==SCRATCH,"preallocated scratch pattern");
    if(api==7 || api==11)CHECK((cell.header.predeclared_flags&32u)!=0,
        "closer requires preconsumed ledger flag, not a new right");
}
static void fill_frame(void *p,unsigned n) {
    unsigned i;CHECK(p==frame,"same preallocated output frame");
    for(i=0;i<n;++i)((unsigned char *)p)[i]=(unsigned char)(i*13u+7u);
}
static BOOL bool_result(void) { return (BOOL)(LONG)(uint32_t)active->scalar; }

static HANDLE WINAPI fake_create(LPCWSTR p,DWORD access,DWORD share,
    LPSECURITY_ATTRIBUTES security,DWORD disposition,DWORD flags,HANDLE templ) {
    target_enter(1);CHECK(p==path_text && access==UINT32_C(0x80000000) && share==1 &&
        security==NULL && disposition==3 && flags==UINT32_C(0x00200080) && templ==NULL,
        "all seven CreateFileW arguments");
    return (HANDLE)(uintptr_t)active->scalar;
}
static DWORD WINAPI fake_type(HANDLE h) {
    target_enter(2);CHECK((uintptr_t)h==HANDLE_BITS,"GetFileType handle");
    return (DWORD)active->scalar;
}
static BOOL WINAPI fake_information(HANDLE h,FILE_INFO_BY_HANDLE_CLASS k,LPVOID p,DWORD n) {
    target_enter(3);CHECK((uintptr_t)h==HANDLE_BITS && (unsigned)k==9 && n==8,
        "FileAttributeTagInfo9 fixed8B");fill_frame(p,8);return bool_result();
}
static DWORD WINAPI fake_path(HANDLE h,LPWSTR p,DWORD n,DWORD flags) {
    target_enter(4);CHECK((uintptr_t)h==HANDLE_BITS && n==4101 && flags==0,
        "FinalPath4101 WCHAR flags0, no resize");fill_frame(p,8202);return (DWORD)active->scalar;
}
static BOOL WINAPI fake_size(HANDLE h,PLARGE_INTEGER p) {
    target_enter(5);CHECK((uintptr_t)h==HANDLE_BITS,"GetFileSizeEx handle");
    fill_frame(p,8);return bool_result();
}
static BOOL WINAPI fake_read(HANDLE h,LPVOID p,DWORD n,LPDWORD count,LPOVERLAPPED overlapped) {
    target_enter(6);CHECK((uintptr_t)h==HANDLE_BITS && n==REQUEST_N &&
        count==&cell.header.count_out_scratch && overlapped==NULL,
        "ReadFile exact positive request/scratch/NULL overlap");fill_frame(p,16);
    if(active->writes_count)*count=active->count;return bool_result();
}
static BOOL WINAPI fake_close(HANDLE h) {
    target_enter(7);CHECK((uintptr_t)h==HANDLE_BITS,"CloseHandle target");return bool_result();
}
static BOOL WINAPI fake_attributes(LPCWSTR p,GET_FILEEX_INFO_LEVELS k,LPVOID out) {
    target_enter(8);CHECK(p==path_text && (unsigned)k==0,"GetAttributes Standard0/path identity");
    fill_frame(out,36);return bool_result();
}
static HANDLE WINAPI fake_first(LPCWSTR p,FINDEX_INFO_LEVELS info,LPVOID out,
    FINDEX_SEARCH_OPS search,LPVOID filter,DWORD flags) {
    target_enter(9);CHECK(p==search_text && (unsigned)info==1 && (unsigned)search==0 &&
        filter==NULL && flags==0,"FindFirst Basic1/NameMatch0/filterNULL/flags0");
    fill_frame(out,592);return (HANDLE)(uintptr_t)active->scalar;
}
static BOOL WINAPI fake_next(HANDLE h,LPWIN32_FIND_DATAW out) {
    target_enter(10);CHECK((uintptr_t)h==HANDLE_BITS,"FindNext search bits");
    fill_frame(out,592);return bool_result();
}
static BOOL WINAPI fake_find_close(HANDLE h) {
    target_enter(11);CHECK((uintptr_t)h==HANDLE_BITS,"FindClose search bits");return bool_result();
}
static BOOL WINAPI fake_directory(LPCWSTR p,LPSECURITY_ATTRIBUTES security) {
    target_enter(12);CHECK(p==path_text && security==NULL,"CreateDirectory path/securityNULL");return bool_result();
}
static BOOL WINAPI fake_write(HANDLE h,LPCVOID p,DWORD n,LPDWORD count,LPOVERLAPPED overlapped) {
    target_enter(13);CHECK((uintptr_t)h==HANDLE_BITS && p==write_data && n==REQUEST_N &&
        count==&cell.header.count_out_scratch && overlapped==NULL,
        "WriteFile immutable slice identity/positive request/scratch/NULL overlap");
    CHECK(memcmp(p,write_data,16)==0,"WriteFile immutable slice bytes");
    if(active->writes_count)*count=active->count;return bool_result();
}
static BOOL WINAPI fake_flush(HANDLE h) {
    target_enter(14);CHECK((uintptr_t)h==HANDLE_BITS,"FlushFileBuffers target");return bool_result();
}
static DWORD WINAPI fake_error(void) {
    unsigned char expected[256];++error_entries;
    CHECK(active->probes_error,"never probe stale LastError on nonprobe branch");
    expected256(expected,active,1);copy256(partial_copy,&cell);++partial_copies;++current_partial_copies;
    CHECK(memcmp(partial_copy,expected,256)==0,
        "LastError boundary:scalar+definition committed;error/count still uncommitted");
    if(escape_error)longjmp(error_escape,1);
    ++error_returns;return active->error;
}

static void reset_functions(void) {
    functions.create_file=fake_create;functions.get_type=fake_type;
    functions.get_information=fake_information;functions.get_path=fake_path;
    functions.get_size=fake_size;functions.read_file=fake_read;
    functions.close_handle=fake_close;functions.get_attributes=fake_attributes;
    functions.find_first=fake_first;functions.find_next=fake_next;
    functions.find_close=fake_find_close;functions.create_directory=fake_directory;
    functions.write_file=fake_write;functions.flush=fake_flush;functions.last_error=fake_error;
}
static int initialize(const Vector *v,uint32_t ordinal) {
    unsigned cap=frame_bytes(v->api);active=v;current_ordinal=ordinal;escape_error=0;
    current_partial_copies=0;
    CHECK(allocated_cells<ARRAY_N(cells),"bounded fresh cell bank");
    current_cell=&cells[allocated_cells++];
    memset(frame,0xcc,sizeof(frame));reset_functions();++init_attempts;
    return pf14_initialize(&cell,ordinal,7,(uint16_t)v->api,(uint8_t)actor(v->api),
        (uint8_t)target(v->api),9,19,has_count(v->api)?REQUEST_N:0,
        has_handle(v->api)?HANDLE_BITS:0,cap?3:UINT32_MAX,cap?5:0,cap,base_flags(v->api));
}
static int invoke(unsigned api,volatile PF14Cell *c,const PF14Functions *f,void *out) {
    ++wrapper_attempts;
    switch(api) {
    case 1:return pf14_create_file(c,f,path_text,UINT32_C(0x80000000),1,NULL,3,UINT32_C(0x00200080),NULL);
    case 2:return pf14_get_type(c,f);
    case 3:return pf14_get_information(c,f,(FILE_ATTRIBUTE_TAG_INFO *)out);
    case 4:return pf14_get_path(c,f,(WCHAR *)out);
    case 5:return pf14_get_size(c,f,(LARGE_INTEGER *)out);
    case 6:return pf14_read(c,f,out);
    case 7:return pf14_close(c,f);
    case 8:return pf14_get_attributes(c,f,path_text,(WIN32_FILE_ATTRIBUTE_DATA *)out);
    case 9:return pf14_find_first(c,f,search_text,(WIN32_FIND_DATAW *)out);
    case 10:return pf14_find_next(c,f,(WIN32_FIND_DATAW *)out);
    case 11:return pf14_find_close(c,f);
    case 12:return pf14_create_directory(c,f,path_text);
    case 13:return pf14_write(c,f,write_data);
    case 14:return pf14_flush(c,f);
    default:CHECK(0,"unknown test API");return -1;
    }
}
static void note(const char *id,unsigned before) {
    unsigned char retained[256];unsigned i;copy256(retained,&cell);
    ++named_cases;printf("{\"case\":\"%s\",\"outcome\":\"%s\",\"cell_copy256_hex\":\"",id,
        failures==before?"PASS":"FAIL");
    for(i=0;i<256;++i)printf("%02x",(unsigned)retained[i]);
    printf("\",\"error_boundary_copy256_hex\":");
    if(current_partial_copies) {
        printf("\"");for(i=0;i<256;++i)printf("%02x",(unsigned)partial_copy[i]);printf("\"");
    } else printf("null");
    printf("}\n");
}
static void semantic_vectors(void) {
    unsigned i,j;
    for(i=0;i<ARRAY_N(vectors);++i) {
        const Vector *v=&vectors[i];unsigned before=failures,t=target_calls,e=error_entries;
        unsigned char expected[256],actual[256],held[256];
        CHECK(initialize(v,100+i)==PF14_OK,"valid independent initializer");
        expected256(expected,v,0);copy256(actual,&cell);
        CHECK(memcmp(actual,expected,256)==0,"exact initialized256B, no observed zero defaults");
        CHECK(invoke(v->api,&cell,&functions,frame)==PF14_OK,"normal raw wrapper return");
        CHECK(target_calls==t+1 && error_entries==e+(unsigned)v->probes_error,"exact target/error probe count");
        expected256(expected,v,2);copy256(final_copy,&cell);
        CHECK(memcmp(final_copy,expected,256)==0,"all256 final bytes independently specified");
        memcpy(held,final_copy,256);
        CHECK(invoke(v->api,&cell,&functions,frame)==PF14_ALREADY_ENTERED,"once-only repeat refuses");
        copy256(actual,&cell);CHECK(memcmp(actual,held,256)==0,"repeat cannot overwrite raw facts");
        CHECK(target_calls==t+1 && error_entries==e+(unsigned)v->probes_error,"repeat makes no fake calls");
        if(frame_bytes(v->api) && v->api!=13) {
            for(j=0;j<frame_bytes(v->api);++j)CHECK(frame[j]==(unsigned char)(j*13u+7u),"exact target output frame");
        }
        /* Raw count bytes are asserted above. A committed count is not a
         * source-issued progress/lease flag; semantic eligibility stays in
         * the literal contract and future real consumer, not this C shim. */
        note(v->id,before);
    }
}

typedef enum Bad {
    NULL_CELL,NULL_FUNCTIONS,NULL_TARGET,NULL_ERROR,BAD_API,ZERO_GENERATION,
    SCALAR_EPOCH,SCALAR_KIND,SCALAR_WIDTH,HEADER_PAD,AXIS_PAD,HIGH_PAYLOAD,
    UNKNOWN_FLAGS,ABSENT_HANDLE_BITS,ABSENT_BUFFER_CAP,QUERY_CAPACITY,NULL_QUERY,
    CLOSE_UNCONSUMED,FINDCLOSE_UNCONSUMED,MISALIGNED,COUNT_EPOCH,DEFINEDNESS_WIDTH
} Bad;
static const char *bad_names[]={
    "M01_null_cell","M02_null_functions","M03_null_target","M04_null_error",
    "M05_bad_api","M06_zero_generation","M07_scalar_epoch","M08_scalar_kind",
    "M09_scalar_width","M10_header_padding","M11_axis_padding","M12_high_payload",
    "M13_unknown_flags","M14_absent_handle_bits","M15_absent_buffer_capacity",
    "M16_query_capacity","M17_null_query","M18_close_unconsumed",
    "M19_findclose_unconsumed","M20_misaligned","M21_count_epoch","M22_definedness_width"
};
static void malformed_vectors(void) {
    unsigned i;
    for(i=0;i<ARRAY_N(bad_names);++i) {
        Vector v={bad_names[i],2,1,0,0,0,0};unsigned before=failures,t=target_calls,e=error_entries;
        volatile PF14Cell *ptr=&cell;const PF14Functions *fn=&functions;void *out=frame;
        unsigned char original[256],after[256],unaligned_before[sizeof(misaligned_store)];
        if(i==QUERY_CAPACITY || i==NULL_QUERY)v.api=3;
        if(i==CLOSE_UNCONSUMED)v.api=7;if(i==FINDCLOSE_UNCONSUMED)v.api=11;
        CHECK(initialize(&v,300+i)==PF14_OK,"healthy pre-mutation initializer");
        ptr=&cell;
        switch((Bad)i) {
        case NULL_CELL:ptr=NULL;break;case NULL_FUNCTIONS:fn=NULL;break;
        case NULL_TARGET:functions.get_type=NULL;break;case NULL_ERROR:functions.last_error=NULL;break;
        case BAD_API:cell.header.api_id=15;break;case ZERO_GENERATION:cell.header.generation=0;break;
        case SCALAR_EPOCH:cell.scalar.epoch=8;break;case SCALAR_KIND:cell.scalar.kind=4;break;
        case SCALAR_WIDTH:cell.scalar.width=8;break;case HEADER_PAD:cell.header.reserved28=1;break;
        case AXIS_PAD:cell.scalar.reserved24=1;break;case HIGH_PAYLOAD:cell.scalar.payload.u64=UINT64_C(1)<<40;break;
        case UNKNOWN_FLAGS:cell.header.predeclared_flags|=UINT32_C(0x80000000);break;
        case ABSENT_HANDLE_BITS:cell.header.predeclared_flags&=~2u;break;
        case ABSENT_BUFFER_CAP:cell.header.buffer_capacity=8;break;
        case QUERY_CAPACITY:cell.header.buffer_capacity=7;break;case NULL_QUERY:out=NULL;break;
        case CLOSE_UNCONSUMED:case FINDCLOSE_UNCONSUMED:cell.header.predeclared_flags&=~32u;break;
        case MISALIGNED:
            memset(misaligned_store,0xc3,sizeof(misaligned_store));
            memcpy(unaligned_before,misaligned_store,sizeof(misaligned_store));
            ptr=(volatile PF14Cell *)(misaligned_store+1);break;
        case COUNT_EPOCH:cell.count.epoch=8;break;case DEFINEDNESS_WIDTH:cell.error_definition.width=4;break;
        }
        copy256(original,&cell);
        CHECK(invoke(v.api,ptr,fn,out)==PF14_INVALID,"malformed shape refuses before fake dispatch");
        CHECK(target_calls==t && error_entries==e,"malformed no target/error transport");
        copy256(after,&cell);CHECK(memcmp(original,after,256)==0,"malformed attempt leaves original cell unchanged");
        if(i==MISALIGNED)CHECK(memcmp(unaligned_before,misaligned_store,sizeof(misaligned_store))==0,"misaligned guard before byte writes");
        note(bad_names[i],before);
    }
}
static void initializer_negatives(void) {
    unsigned i;const char *names[]={"I01_null_cell","I02_generation0","I03_api0","I04_api15",
        "I05_read_requested0_present","I06_write_requested0_present","I07_read_requested16_absent",
        "I08_write_requested16_absent","I09_unknown_flags","I10_misaligned"};
    for(i=0;i<ARRAY_N(names);++i) {
        unsigned before=failures;PF14Cell *ptr=&cell;unsigned api=2,gen=7;
        uint32_t request=0,flags=2,cap=0,bid=UINT32_MAX,bgen=0;
        unsigned char saved[256],after[256],unaligned_before[sizeof(misaligned_store)];active=NULL;current_partial_copies=0;
        CHECK(allocated_cells<ARRAY_N(cells),"bounded fresh invalid-destination cell");
        current_cell=&cells[allocated_cells++];ptr=&cell;
        memset(&cell,0xc3,sizeof(cell));copy256(saved,&cell);
        switch(i) {
        case 0:ptr=NULL;break;case 1:gen=0;break;case 2:api=0;break;case 3:api=15;break;
        case 4:case 5:api=i==4?6:13;request=0;flags=3;cap=16;bid=3;bgen=5;break;
        case 6:case 7:api=i==6?6:13;request=16;flags=2;cap=16;bid=3;bgen=5;break;
        case 8:flags|=UINT32_C(0x80000000);break;
        case 9:memset(misaligned_store,0xc3,sizeof(misaligned_store));
            memcpy(unaligned_before,misaligned_store,sizeof(misaligned_store));
            ptr=(PF14Cell *)(misaligned_store+1);break;
        }
        ++init_attempts;
        CHECK(pf14_initialize(ptr,500+i,gen,(uint16_t)api,(uint8_t)actor(api),(uint8_t)target(api),9,19,request,HANDLE_BITS,bid,bgen,cap,flags)==PF14_INVALID,
              "invalid initializer shape/domain");
        copy256(after,&cell);CHECK(memcmp(saved,after,256)==0,"initializer refuses before mutating destination");
        if(i==9)CHECK(memcmp(unaligned_before,misaligned_store,sizeof(misaligned_store))==0,"initializer alignment guard before byte writes");
        note(names[i],before);
    }
}
static void interrupted_error_transport(void) {
    static const Vector v={"P01_error_transport_escape",6,0,3,18,1,1};
    unsigned before=failures,t=target_calls,e=error_entries,er=error_returns;
    unsigned char expected[256],after[256];
    CHECK(initialize(&v,700)==PF14_OK,"partial target initializer");
    escape_error=1;
    if(setjmp(error_escape)==0) {
        (void)invoke(v.api,&cell,&functions,frame);
        CHECK(0,"fake LastError must escape before wrapper return");
    }
    escape_error=0;expected256(expected,&v,1);copy256(after,&cell);
    CHECK(memcmp(after,expected,256)==0 && memcmp(partial_copy,expected,256)==0,
          "partial256B retains scalar+definedness, scratch3 but unknown error/count");
    CHECK(target_calls==t+1 && error_entries==e+1 && error_returns==er,"partial callback entered, never returned");
    CHECK(invoke(v.api,&cell,&functions,frame)==PF14_ALREADY_ENTERED,"no retry after interrupted transport");
    copy256(after,&cell);CHECK(memcmp(after,partial_copy,256)==0,"partial original bytes remain unchanged");
    note(v.id,before);
}
int main(void) {
    semantic_vectors();malformed_vectors();initializer_negatives();interrupted_error_transport();
    CHECK(named_cases==79 && allocated_cells==79 && init_attempts==79,"exact frozen control/cell/initializer counts");
    CHECK(wrapper_attempts==116 && target_calls==47,"wrapper attempts versus actual fake targets");
    CHECK(error_entries==17 && error_returns==16 && partial_copies==17,
          "error callback entries/normal returns versus partial captures");
    printf("{\"summary\":{\"cases\":%u,\"checks\":%u,\"failures\":%u,\"initializer_attempts\":%u,\"wrapper_attempts\":%u,\"fake_targets\":%u,\"error_entries\":%u,\"error_returns\":%u,\"partial_copies\":%u}}\n",
        named_cases,checks,failures,init_attempts,wrapper_attempts,target_calls,error_entries,error_returns,partial_copies);
    return failures ? 1 : 0;
}
