/* Internal Windows-x64 raw return component. Not a capability/dispatch issuer. */
#ifndef PREFLIGHT_FILE14_RAW_V1_H
#define PREFLIGHT_FILE14_RAW_V1_H
#if !defined(_WIN64) || !defined(_M_X64) || !defined(_MSC_VER)
#error This component requires the separately qualified MSVC Windows x64 ABI.
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stddef.h>

typedef union PF14Payload {
    uint64_t u64;
    uint32_t u32;
    uint8_t u8;
} PF14Payload;

typedef struct PF14Axis {
    PF14Payload payload;
    uint32_t epoch;
    uint16_t kind;
    uint8_t width;
    uint8_t reserved15;
    volatile LONG stage_hint;
    volatile LONG commit;
    uint64_t reserved24;
} PF14Axis;

typedef struct PF14Header {
    uint16_t schema;
    uint16_t slot_bytes;
    uint32_t ordinal;
    uint32_t generation;
    uint16_t api_id;
    uint8_t actor_id;
    uint8_t target_kind;
    uint32_t target_ordinal;
    uint32_t requested;
    uint32_t predeclared_flags;
    uint32_t reserved28;
    uint64_t target_generation;
    uint64_t input_handle_bits;
    uint32_t buffer_id;
    uint32_t buffer_generation;
    uint32_t buffer_capacity;
    uint32_t query_capture_state;
    DWORD count_out_scratch;
    uint32_t count_scratch_initial_pattern;
    volatile LONG native_exit_phase;
    uint32_t conversion_phase;
    uint8_t reserved80[48];
} PF14Header;

typedef struct __declspec(align(16)) PF14Cell {
    PF14Header header;
    PF14Axis scalar;
    PF14Axis count;
    PF14Axis error_value;
    PF14Axis error_definition;
} PF14Cell;

#define PF14_ASSERT(name, expression) typedef char pf14_assert_##name[(expression) ? 1 : -1]
#define PF14_OFFSET(type, field, value) PF14_ASSERT(type##_##field, offsetof(type, field) == (value))
PF14_ASSERT(pointer64, sizeof(void *) == 8);
PF14_ASSERT(handle64, sizeof(HANDLE) == 8);
PF14_ASSERT(bool32, sizeof(BOOL) == 4);
PF14_ASSERT(dword32, sizeof(DWORD) == 4);
PF14_ASSERT(long32, sizeof(LONG) == 4);
PF14_ASSERT(wchar16, sizeof(WCHAR) == 2);
PF14_ASSERT(axis32, sizeof(PF14Axis) == 32);
PF14_ASSERT(header128, sizeof(PF14Header) == 128);
PF14_ASSERT(cell256, sizeof(PF14Cell) == 256);
PF14_ASSERT(alignment16, __alignof(PF14Cell) == 16);
PF14_ASSERT(tag8, sizeof(FILE_ATTRIBUTE_TAG_INFO) == 8);
PF14_ASSERT(attributes36, sizeof(WIN32_FILE_ATTRIBUTE_DATA) == 36);
PF14_ASSERT(find592, sizeof(WIN32_FIND_DATAW) == 592);
PF14_OFFSET(PF14Axis, payload, 0);
PF14_OFFSET(PF14Axis, epoch, 8);
PF14_OFFSET(PF14Axis, kind, 12);
PF14_OFFSET(PF14Axis, width, 14);
PF14_OFFSET(PF14Axis, reserved15, 15);
PF14_OFFSET(PF14Axis, stage_hint, 16);
PF14_OFFSET(PF14Axis, commit, 20);
PF14_OFFSET(PF14Axis, reserved24, 24);
PF14_OFFSET(PF14Header, schema, 0);
PF14_OFFSET(PF14Header, slot_bytes, 2);
PF14_OFFSET(PF14Header, ordinal, 4);
PF14_OFFSET(PF14Header, generation, 8);
PF14_OFFSET(PF14Header, api_id, 12);
PF14_OFFSET(PF14Header, actor_id, 14);
PF14_OFFSET(PF14Header, target_kind, 15);
PF14_OFFSET(PF14Header, target_ordinal, 16);
PF14_OFFSET(PF14Header, requested, 20);
PF14_OFFSET(PF14Header, predeclared_flags, 24);
PF14_OFFSET(PF14Header, reserved28, 28);
PF14_OFFSET(PF14Header, target_generation, 32);
PF14_OFFSET(PF14Header, input_handle_bits, 40);
PF14_OFFSET(PF14Header, buffer_id, 48);
PF14_OFFSET(PF14Header, buffer_generation, 52);
PF14_OFFSET(PF14Header, buffer_capacity, 56);
PF14_OFFSET(PF14Header, query_capture_state, 60);
PF14_OFFSET(PF14Header, count_out_scratch, 64);
PF14_OFFSET(PF14Header, count_scratch_initial_pattern, 68);
PF14_OFFSET(PF14Header, native_exit_phase, 72);
PF14_OFFSET(PF14Header, conversion_phase, 76);
PF14_OFFSET(PF14Header, reserved80, 80);
PF14_OFFSET(PF14Cell, header, 0);
PF14_OFFSET(PF14Cell, scalar, 128);
PF14_OFFSET(PF14Cell, count, 160);
PF14_OFFSET(PF14Cell, error_value, 192);
PF14_OFFSET(PF14Cell, error_definition, 224);

/* Types intentionally match SDK WINAPI declarations. No loader is provided. */
typedef HANDLE (WINAPI *PF14CreateFile)(LPCWSTR,DWORD,DWORD,LPSECURITY_ATTRIBUTES,DWORD,DWORD,HANDLE);
typedef DWORD (WINAPI *PF14GetFileType)(HANDLE);
typedef BOOL (WINAPI *PF14GetFileInformation)(HANDLE,FILE_INFO_BY_HANDLE_CLASS,LPVOID,DWORD);
typedef DWORD (WINAPI *PF14GetFinalPath)(HANDLE,LPWSTR,DWORD,DWORD);
typedef BOOL (WINAPI *PF14GetFileSize)(HANDLE,PLARGE_INTEGER);
typedef BOOL (WINAPI *PF14ReadFile)(HANDLE,LPVOID,DWORD,LPDWORD,LPOVERLAPPED);
typedef BOOL (WINAPI *PF14CloseHandle)(HANDLE);
typedef BOOL (WINAPI *PF14GetAttributes)(LPCWSTR,GET_FILEEX_INFO_LEVELS,LPVOID);
typedef HANDLE (WINAPI *PF14FindFirst)(LPCWSTR,FINDEX_INFO_LEVELS,LPVOID,FINDEX_SEARCH_OPS,LPVOID,DWORD);
typedef BOOL (WINAPI *PF14FindNext)(HANDLE,LPWIN32_FIND_DATAW);
typedef BOOL (WINAPI *PF14FindClose)(HANDLE);
typedef BOOL (WINAPI *PF14CreateDirectory)(LPCWSTR,LPSECURITY_ATTRIBUTES);
typedef BOOL (WINAPI *PF14WriteFile)(HANDLE,LPCVOID,DWORD,LPDWORD,LPOVERLAPPED);
typedef BOOL (WINAPI *PF14Flush)(HANDLE);
typedef DWORD (WINAPI *PF14LastError)(void);

typedef struct PF14Functions {
    PF14CreateFile create_file;
    PF14GetFileType get_type;
    PF14GetFileInformation get_information;
    PF14GetFinalPath get_path;
    PF14GetFileSize get_size;
    PF14ReadFile read_file;
    PF14CloseHandle close_handle;
    PF14GetAttributes get_attributes;
    PF14FindFirst find_first;
    PF14FindNext find_next;
    PF14FindClose find_close;
    PF14CreateDirectory create_directory;
    PF14WriteFile write_file;
    PF14Flush flush;
    PF14LastError last_error;
} PF14Functions;

enum { PF14_OK=0, PF14_INVALID=1, PF14_ALREADY_ENTERED=2 };
enum { PF14_HANDLE64=1, PF14_BOOL32=2, PF14_DWORD32=3, PF14_COUNT32=4, PF14_DEFINEDNESS=5 };
enum { PF14_REQUESTED=1, PF14_INPUT_HANDLE=2, PF14_NATIVE_ENTERED=4,
       PF14_RAW_EXIT=8, PF14_STOPPED=16, PF14_CLOSE_CONSUMED=32 };

/* Trusted component initializer only; this never reserves a kernel call/right. */
int pf14_initialize(PF14Cell *, uint32_t ordinal, uint32_t generation,
                    uint16_t api_id, uint8_t actor_id, uint8_t target_kind,
                    uint32_t target_ordinal, uint64_t target_generation,
                    uint32_t requested, uint64_t input_handle_bits,
                    uint32_t buffer_id, uint32_t buffer_generation,
                    uint32_t buffer_capacity, uint32_t flags);
int pf14_create_file(volatile PF14Cell *,const PF14Functions *,LPCWSTR,DWORD,DWORD,LPSECURITY_ATTRIBUTES,DWORD,DWORD,HANDLE);
int pf14_get_type(volatile PF14Cell *,const PF14Functions *);
int pf14_get_information(volatile PF14Cell *,const PF14Functions *,FILE_ATTRIBUTE_TAG_INFO *);
int pf14_get_path(volatile PF14Cell *,const PF14Functions *,WCHAR *);
int pf14_get_size(volatile PF14Cell *,const PF14Functions *,LARGE_INTEGER *);
int pf14_read(volatile PF14Cell *,const PF14Functions *,void *);
int pf14_close(volatile PF14Cell *,const PF14Functions *);
int pf14_get_attributes(volatile PF14Cell *,const PF14Functions *,LPCWSTR,WIN32_FILE_ATTRIBUTE_DATA *);
int pf14_find_first(volatile PF14Cell *,const PF14Functions *,LPCWSTR,WIN32_FIND_DATAW *);
int pf14_find_next(volatile PF14Cell *,const PF14Functions *,WIN32_FIND_DATAW *);
int pf14_find_close(volatile PF14Cell *,const PF14Functions *);
int pf14_create_directory(volatile PF14Cell *,const PF14Functions *,LPCWSTR);
int pf14_write(volatile PF14Cell *,const PF14Functions *,const void *);
int pf14_flush(volatile PF14Cell *,const PF14Functions *);
#endif
