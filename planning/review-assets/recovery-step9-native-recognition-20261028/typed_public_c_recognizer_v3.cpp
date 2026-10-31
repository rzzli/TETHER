// DRAFT v3 ONLY: pack format2 separates one unchanged primary raw-NUL case.
// Not compiled, run, or authorized by this source file. Prior versions preserved.
// Consume exact public declarations; never compile fetched implementations.
// The separate parent protocol owns Job limits, leases, pin-header creation,
// permission, source/build review, DLL/GGUF access and all final qualification.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define _WIN32_WINNT 0x0602
#define LLAMA_SHARED
#define GGML_SHARED
#define GGML_BACKEND_SHARED
#if defined(LLAMA_BUILD) || defined(GGML_BUILD) || defined(GGML_BACKEND_BUILD)
#error Library-build macros are forbidden in this consumer
#endif
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cwctype>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <initializer_list>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>
#include "llama.h"

namespace fs = std::filesystem;
static_assert(sizeof(void*) == 8 && sizeof(size_t) == 8, "x64 required");
static_assert(sizeof(llama_token) == 4 && sizeof(bool) == 1, "Unexpected scalar ABI");
static_assert(std::is_standard_layout<llama_model_params>::value, "Public layout required");
static_assert(sizeof(llama_model_params) == 80 && alignof(llama_model_params) == 8, "Pinned x64 model-params layout differs");
static_assert(offsetof(llama_model_params, devices) == 0 && offsetof(llama_model_params, n_gpu_layers) == 16, "Pinned params offsets differ");
static_assert(offsetof(llama_model_params, tensor_split) == 40 && offsetof(llama_model_params, vocab_only) == 72, "Pinned params offsets differ");
static_assert(sizeof(llama_token_data) == 12 && offsetof(llama_token_data, logit) == 4, "Pinned candidate layout differs");
static_assert(sizeof(llama_token_data_array) == 32 && offsetof(llama_token_data_array, selected) == 16 && offsetof(llama_token_data_array, sorted) == 24, "Pinned array layout differs");

// Parent-generated DATA ONLY header contract; described in BRIDGE-DRAFT-DESIGN-v2.md.
struct ModulePin { const wchar_t* name; const char* sha256; uint64_t bytes; };
struct FilePin { const wchar_t* path; const char* sha256; uint64_t bytes; };
#ifndef R09_PIN_HEADER
#error Supply the separately reviewed parent-generated exact pin header
#endif
#include R09_PIN_HEADER
static_assert(sizeof(R09_SHARDS) / sizeof(R09_SHARDS[0]) == 3, "Exactly three parent-bound shards required");

constexpr uint32_t B = 65536, K = 65536, P = 65536, G = 65536;
constexpr uint32_t VMAX = 262144, EMAX = 64, CASEMAX = 200, PREFIXMAX = 6;
constexpr uint64_t PACKMAX = 20ull * 1024 * 1024, TOTALTOKENS = 1000000;
constexpr uint64_t DLLMAX = 128ull * 1024 * 1024, OUTPUTMAX = 8ull * 1024 * 1024;
constexpr uint64_t COOPERATIVE_MS = 120000;
static const ULONGLONG START_MS = GetTickCount64();
static uint64_t token_budget_used = 0, tokenize_calls = 0, piece_calls = 0, apply_calls = 0, accept_calls = 0;

struct BridgeError : std::runtime_error { explicit BridgeError(const char* text) : std::runtime_error(text) {} };
static void need(bool ok, const char* text) { if (!ok) throw BridgeError(text); }
static void tick() { need(GetTickCount64() - START_MS < COOPERATIVE_MS, "cooperative_deadline_expired"); }
static std::wstring fold(std::wstring s) { for (auto& c : s) c = static_cast<wchar_t>(towlower(c)); return s; }
static bool same(const fs::path& a, const fs::path& b) { return fold(a.lexically_normal().wstring()) == fold(b.lexically_normal().wstring()); }
static std::string utf8(const std::wstring& s) {
    if (s.empty()) return {};
    need(s.size() <= 32768, "wide_string_cap");
    int n = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, s.data(), static_cast<int>(s.size()), nullptr, 0, nullptr, nullptr);
    need(n > 0, "wide_utf8_conversion"); std::string out(static_cast<size_t>(n), '\0');
    need(WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, s.data(), static_cast<int>(s.size()), out.data(), n, nullptr, nullptr) == n, "wide_utf8_conversion_changed"); return out;
}
static bool valid_utf8(const std::string& s) { return s.empty() || MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, s.data(), static_cast<int>(s.size()), nullptr, 0) > 0; }
static std::string q(const std::string& s) {
    std::ostringstream o; o << '"';
    for (unsigned char c : s) { if (c == '"' || c == '\\') o << '\\' << static_cast<char>(c); else if (c < 32) o << "\\u00" << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(c) << std::dec; else o << static_cast<char>(c); }
    o << '"'; return o.str();
}
static fs::path absolute(const wchar_t* raw) {
    std::wstring s(raw); need(s.size() >= 3 && s[1] == L':' && (s[2] == L'\\' || s[2] == L'/'), "local_absolute_path_required");
    need(s.find_first_of(L"\r\n\t") == std::wstring::npos && s.find(L':', 2) == std::wstring::npos, "path_controls_or_stream");
    std::array<wchar_t, 32768> b{}; DWORD n = GetFullPathNameW(s.c_str(), static_cast<DWORD>(b.size()), b.data(), nullptr);
    need(n > 0 && n < b.size(), "path_resolution"); fs::path p(std::wstring(b.data(), n));
    need(GetDriveTypeW(p.root_path().c_str()) == DRIVE_FIXED, "fixed_drive_required"); return p.lexically_normal();
}
static void no_reparse(const fs::path& p, bool exists) {
    bool leaf = true;
    for (fs::path at = p; !at.empty();) {
        DWORD a = GetFileAttributesW(at.c_str());
        if (a == INVALID_FILE_ATTRIBUTES) need(leaf && !exists && GetLastError() == ERROR_FILE_NOT_FOUND, "missing_path_ancestor");
        else need((a & FILE_ATTRIBUTE_REPARSE_POINT) == 0, "reparse_path_forbidden");
        fs::path parent = at.parent_path(); if (parent == at) break; at = parent; leaf = false;
    }
}
struct Handle {
    HANDLE h = INVALID_HANDLE_VALUE;
    explicit Handle(HANDLE v = INVALID_HANDLE_VALUE) : h(v) {}
    ~Handle() { close(); }
    Handle(Handle&& x) noexcept : h(x.h) { x.h = INVALID_HANDLE_VALUE; }
    Handle& operator=(Handle&& x) noexcept { if (this != &x) { close(); h = x.h; x.h = INVALID_HANDLE_VALUE; } return *this; }
    Handle(const Handle&) = delete; Handle& operator=(const Handle&) = delete;
    void close() { if (h != INVALID_HANDLE_VALUE && h != nullptr) CloseHandle(h); h = INVALID_HANDLE_VALUE; }
};
static uint64_t length(HANDLE h) { LARGE_INTEGER n{}; need(GetFileSizeEx(h, &n) && n.QuadPart >= 0, "file_size_failed"); return static_cast<uint64_t>(n.QuadPart); }
static std::string hex(const unsigned char* p, size_t n) { std::ostringstream o; for (size_t i = 0; i < n; ++i) o << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(p[i]); return o.str(); }
struct Sha {
    BCRYPT_ALG_HANDLE alg = nullptr; BCRYPT_HASH_HANDLE hash = nullptr; std::vector<UCHAR> state;
    Sha() {
        try { need(BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) >= 0, "bcrypt_open"); DWORD n = 0, got = 0;
            need(BCryptGetProperty(alg, BCRYPT_OBJECT_LENGTH, reinterpret_cast<PUCHAR>(&n), sizeof(n), &got, 0) >= 0 && got == sizeof(n) && n <= 65536, "bcrypt_size");
            state.resize(n); need(BCryptCreateHash(alg, &hash, state.data(), n, nullptr, 0, 0) >= 0, "bcrypt_create");
        } catch (...) { if (hash) BCryptDestroyHash(hash); if (alg) BCryptCloseAlgorithmProvider(alg, 0); throw; }
    }
    ~Sha() { if (hash) BCryptDestroyHash(hash); if (alg) BCryptCloseAlgorithmProvider(alg, 0); }
    void add(const void* p, size_t n) { need(n <= 1048576, "hash_chunk_cap"); if (n) need(BCryptHashData(hash, reinterpret_cast<PUCHAR>(const_cast<void*>(p)), static_cast<ULONG>(n), 0) >= 0, "bcrypt_update"); }
    std::string finish() { std::array<UCHAR, 32> b{}; need(BCryptFinishHash(hash, b.data(), static_cast<ULONG>(b.size()), 0) >= 0, "bcrypt_finish"); return hex(b.data(), b.size()); }
};
static std::string digest(const std::string& s) { Sha h; for (size_t i = 0; i < s.size();) { size_t n = (std::min)(s.size() - i, size_t(1048576)); h.add(s.data() + i, n); i += n; } return h.finish(); }
static bool hash_text(const char* s) { if (!s || std::char_traits<char>::length(s) != 64) return false; for (size_t i = 0; i < 64; ++i) if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f'))) return false; return true; }
struct Lease {
    fs::path path; Handle file; uint64_t bytes = 0; std::string sha;
    Lease(const fs::path& p, uint64_t cap) : path(p) {
        no_reparse(p, true); file = Handle(CreateFileW(p.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, nullptr));
        need(file.h != INVALID_HANDLE_VALUE, "lease_open_failed"); bytes = length(file.h); need(bytes <= cap, "leased_file_cap");
        BY_HANDLE_FILE_INFORMATION info{}; need(GetFileInformationByHandle(file.h, &info) && !(info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY), "regular_file_required");
    }
    void verify(uint64_t expected_bytes, const char* expected_sha) {
        need(hash_text(expected_sha) && bytes == expected_bytes, "pin_size_or_hash_format");
        Sha h; std::vector<char> b(1048576); uint64_t got_total = 0;
        while (got_total < bytes) { tick(); DWORD got = 0; DWORD n = static_cast<DWORD>((std::min)(bytes - got_total, uint64_t(b.size())));
            need(ReadFile(file.h, b.data(), n, &got, nullptr) && got == n, "leased_hash_read"); h.add(b.data(), got); got_total += got; }
        sha = h.finish(); need(sha == expected_sha && length(file.h) == bytes, "leased_hash_mismatch"); LARGE_INTEGER zero{}; need(SetFilePointerEx(file.h, zero, nullptr, FILE_BEGIN), "leased_rewind");
    }
    std::string read(size_t cap) { need(bytes <= cap, "read_cap"); std::string out(static_cast<size_t>(bytes), '\0'); size_t at = 0;
        while (at < out.size()) { tick(); DWORD n = static_cast<DWORD>((std::min)(out.size() - at, size_t(65536))), got = 0; need(ReadFile(file.h, out.data() + at, n, &got, nullptr) && got == n, "leased_read"); at += got; } return out; }
};
static void write_all(HANDLE h, const std::string& s) { size_t at = 0; while (at < s.size()) { DWORD got = 0, n = static_cast<DWORD>((std::min)(s.size() - at, size_t(65536))); need(WriteFile(h, s.data() + at, n, &got, nullptr) && got == n, "output_write"); at += got; } need(FlushFileBuffers(h), "output_flush"); }
struct Output {
    fs::path dir, partial, final; Handle stream; uint64_t bytes = 0; bool committed = false;
    explicit Output(const fs::path& p, const std::string& mode) : dir(p), partial(p / L"result.partial.jsonl"), final(p / L"result.jsonl") {
        no_reparse(p, true); need(GetFileAttributesW(p.c_str()) & FILE_ATTRIBUTE_DIRECTORY, "output_directory_required");
        need(fs::is_empty(p), "output_directory_not_empty");
        for (const wchar_t* name : {L"attempt.json", L"result.partial.jsonl", L"result.jsonl", L"failure.json"}) { fs::path f = p / name; no_reparse(f, false); need(GetFileAttributesW(f.c_str()) == INVALID_FILE_ATTRIBUTES && GetLastError() == ERROR_FILE_NOT_FOUND, "exclusive_output_exists"); }
        Handle claim(CreateFileW((p / L"attempt.json").c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr)); need(claim.h != INVALID_HANDLE_VALUE, "attempt_claim_failed");
        write_all(claim.h, "{\"schema_version\":1,\"mode\":" + q(mode) + ",\"status\":\"claimed_before_native_load\",\"draft\":true}\n");
        stream = Handle(CreateFileW(partial.c_str(), GENERIC_WRITE, FILE_SHARE_READ, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr)); need(stream.h != INVALID_HANDLE_VALUE, "partial_create_failed");
    }
    void row(const std::string& s) { need(s.size() <= 65536 && bytes + s.size() + 1 <= OUTPUTMAX, "output_capture_cap"); write_all(stream.h, s + "\n"); bytes += s.size() + 1; }
    void commit() { stream.close(); need(MoveFileExW(partial.c_str(), final.c_str(), MOVEFILE_WRITE_THROUGH), "exclusive_result_publish_failed"); committed = true; }
    void failure(const std::string& msg) noexcept {
        if (committed) return; std::string s;
        try { s = "{\"schema_version\":1,\"status\":\"failed\",\"message\":" + q(msg) + ",\"elapsed_ms\":" + std::to_string(GetTickCount64() - START_MS) + ",\"token_budget_used\":" + std::to_string(token_budget_used) + ",\"apply_calls\":" + std::to_string(apply_calls) + ",\"accept_calls\":" + std::to_string(accept_calls) + "}"; } catch (...) { return; }
        try { if (stream.h != INVALID_HANDLE_VALUE) row(s); } catch (...) {}
        // A broken/full JSONL stream must not suppress the independent marker attempt.
        try { Handle marker(CreateFileW((dir / L"failure.json").c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr)); if (marker.h != INVALID_HANDLE_VALUE) write_all(marker.h, s + "\n"); } catch (...) {}
    }
};

static fs::path module_path(HMODULE m) { std::array<wchar_t, 32768> b{}; DWORD n = GetModuleFileNameW(m, b.data(), static_cast<DWORD>(b.size())); need(n && n < b.size(), "module_path_failed"); return absolute(std::wstring(b.data(), n).c_str()); }
static const ModulePin* pin(const std::wstring& name) { for (const auto& p : APPROVED_RUNTIME_DLLS) if (fold(name) == fold(p.name)) return &p; return nullptr; }
static bool core_name(const std::wstring& name) { auto n = fold(name); return n == L"llama.dll" || n == L"ggml.dll" || n == L"ggml-base.dll"; }
static bool allowed_runtime(const std::wstring& name, bool recognition) { return core_name(name) || (R09_LIBOMP_REQUIRED && fold(name) == L"libomp.dll") || (recognition && fold(name) == L"ggml-cpu-x64.dll"); }
static bool approved_system(const fs::path& p) { std::array<wchar_t, 32768> b{}; UINT n = GetSystemDirectoryW(b.data(), static_cast<UINT>(b.size())); need(n && n < b.size(), "system_directory_failed"); if (!same(p.parent_path(), fs::path(std::wstring(b.data(), n)))) return false; for (const auto& name : R09_SYSTEM_DLL_NAMES) if (fold(p.filename().wstring()) == fold(name)) return true; return false; }
struct Runtime {
    fs::path root; std::vector<std::unique_ptr<Lease>> leases; DLL_DIRECTORY_COOKIE cookie = nullptr; bool recognition = false;
    explicit Runtime(fs::path p) : root(std::move(p)) {
        need(same(root, absolute(R09_RUNTIME_DIRECTORY)), "runtime_directory_not_parent_bound"); no_reparse(root, true);
        need(SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32 | LOAD_LIBRARY_SEARCH_USER_DIRS), "restrict_dll_search_failed"); cookie = AddDllDirectory(root.c_str()); need(cookie != nullptr, "add_runtime_directory_failed");
        for (const auto& item : APPROVED_RUNTIME_DLLS) need(allowed_runtime(item.name, true) && hash_text(item.sha256) && item.bytes <= DLLMAX, "runtime_pin_allowlist_invalid");
        for (size_t i = 0; i < sizeof(APPROVED_RUNTIME_DLLS) / sizeof(APPROVED_RUNTIME_DLLS[0]); ++i) for (size_t j = 0; j < i; ++j) need(fold(APPROVED_RUNTIME_DLLS[i].name) != fold(APPROVED_RUNTIME_DLLS[j].name), "duplicate_runtime_pin");
        need(pin(L"llama.dll") && pin(L"ggml.dll") && pin(L"ggml-base.dll") && pin(L"ggml-cpu-x64.dll"), "runtime_pin_missing");
        need(!R09_LIBOMP_REQUIRED || pin(L"libomp.dll"), "required_OpenMP_dependency_pin_missing");
    }
    ~Runtime() { if (cookie) RemoveDllDirectory(cookie); } // Native modules remain process-pinned until OS exit.
    void lease(const wchar_t* name) { for (const auto& l : leases) if (same(l->path, root / name)) return; const ModulePin* p = pin(name); need(p && allowed_runtime(name, recognition), "unapproved_runtime_lease"); auto l = std::make_unique<Lease>(root / p->name, DLLMAX); l->verify(p->bytes, p->sha256); leases.push_back(std::move(l)); }
    HMODULE load_core(const wchar_t* name) { need((core_name(name) || (R09_LIBOMP_REQUIRED && fold(name) == L"libomp.dll")) && GetModuleHandleW(name) == nullptr, "core_or_required_dependency_already_loaded_or_unapproved"); lease(name); tick(); HMODULE m = LoadLibraryExW((root / name).c_str(), nullptr, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32); tick(); need(m && same(module_path(m), root / name), "exact_core_or_required_dependency_load_failed"); HMODULE hold = nullptr; need(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_PIN, (root / name).c_str(), &hold) && hold == m, "core_or_dependency_process_pin_failed"); return m; }
    std::string modules() {
        Handle snap(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, GetCurrentProcessId())); need(snap.h != INVALID_HANDLE_VALUE, "module_snapshot_failed"); MODULEENTRY32W e{}; e.dwSize = sizeof(e); need(Module32FirstW(snap.h, &e), "module_enumeration_failed");
        std::ostringstream o; o << '['; bool comma = false; size_t seen_core = 0;
        do { fs::path p = module_path(e.hModule); auto name = p.filename().wstring();
            if (same(p, module_path(nullptr))) { /* bridge executable, parent hash/lease */ }
            else if (same(p.parent_path(), root) || pin(name) || fold(name).rfind(L"llama", 0) == 0 || fold(name).rfind(L"ggml", 0) == 0 || fold(name) == L"libomp.dll") {
                need(allowed_runtime(name, recognition) && same(p.parent_path(), root), "unexpected_native_module"); const ModulePin* item = pin(name); need(item, "loaded_module_pin_missing"); lease(item->name); if (core_name(name)) ++seen_core;
            } else need(approved_system(p), "unapproved_non_native_module");
            if (comma) o << ','; comma = true; o << "{\"name\":" << q(utf8(name)) << ",\"path\":" << q(utf8(p.wstring())) << '}'; e.dwSize = sizeof(e);
        } while (Module32NextW(snap.h, &e));
        need(GetLastError() == ERROR_NO_MORE_FILES && seen_core == 3, "module_enumeration_or_core_count"); o << ']'; return o.str();
    }
};
template<class T> static T symbol(HMODULE m, const char* name) { FARPROC p = GetProcAddress(m, name); need(p != nullptr, "required_export_missing"); return reinterpret_cast<T>(p); }
#define LLAMA_APIS(X) X(llama_version) X(llama_model_default_params) X(llama_backend_init) X(llama_backend_free) X(llama_model_load_from_splits) X(llama_model_free) X(llama_model_get_vocab) X(llama_vocab_n_tokens) X(llama_vocab_is_eog) X(llama_tokenize) X(llama_token_to_piece) X(llama_sampler_init_grammar) X(llama_sampler_apply) X(llama_sampler_accept) X(llama_sampler_free)
#define GGML_APIS(X) X(ggml_backend_load) X(ggml_backend_reg_count) X(ggml_backend_reg_get) X(ggml_backend_reg_name) X(ggml_backend_reg_dev_count) X(ggml_backend_reg_dev_get) X(ggml_backend_dev_count) X(ggml_backend_dev_get) X(ggml_backend_dev_name) X(ggml_backend_dev_type)
struct Api {
#define DECL(n) decltype(&::n) n = nullptr;
    LLAMA_APIS(DECL) GGML_APIS(DECL)
#undef DECL
    Api(HMODULE llama, HMODULE ggml) {
#define LOADL(n) n = symbol<decltype(&::n)>(llama, #n);
        LLAMA_APIS(LOADL)
#undef LOADL
#define LOADG(n) n = symbol<decltype(&::n)>(ggml, #n);
        GGML_APIS(LOADG)
#undef LOADG
    }
};
static std::string native_text(const char* p, size_t cap) { need(p != nullptr, "null_native_string"); std::string s; uintptr_t address = reinterpret_cast<uintptr_t>(p);
    for (size_t i = 0; i < cap; ++i) { need(address <= (std::numeric_limits<uintptr_t>::max)() - i, "native_string_address_overflow"); char c = 0; SIZE_T got = 0; need(ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<const void*>(address + i), &c, 1, &got) && got == 1, "unreadable_native_string"); if (!c) { need(valid_utf8(s), "native_string_not_utf8"); return s; } s += c; } throw BridgeError("native_string_not_terminated_within_cap"); }
static std::string defaults(const llama_model_params& p) { std::ostringstream o; o << std::boolalpha << "{\"devices_null\":" << (p.devices == nullptr ? "true" : "false") << ",\"tensor_buft_overrides_null\":" << (p.tensor_buft_overrides == nullptr ? "true" : "false") << ",\"n_gpu_layers\":" << p.n_gpu_layers << ",\"split_mode\":" << static_cast<int>(p.split_mode) << ",\"load_mode\":" << static_cast<int>(p.load_mode) << ",\"lazy_mode\":" << static_cast<int>(p.lazy_mode) << ",\"main_gpu\":" << p.main_gpu << ",\"tensor_split_null\":" << (p.tensor_split == nullptr ? "true" : "false") << ",\"progress_callback_null\":" << (p.progress_callback == nullptr ? "true" : "false") << ",\"progress_userdata_null\":" << (p.progress_callback_user_data == nullptr ? "true" : "false") << ",\"kv_overrides_null\":" << (p.kv_overrides == nullptr ? "true" : "false") << ",\"vocab_only\":" << p.vocab_only << ",\"check_tensors\":" << p.check_tensors << ",\"use_extra_bufts\":" << p.use_extra_bufts << ",\"no_host\":" << p.no_host << ",\"no_alloc\":" << p.no_alloc << ",\"load_mtp\":" << p.load_mtp << '}'; return o.str(); }
static void check_defaults(const llama_model_params& p) { need(p.devices == nullptr && p.tensor_buft_overrides == nullptr && p.n_gpu_layers == -1 && p.split_mode == LLAMA_SPLIT_MODE_LAYER && p.load_mode == LLAMA_LOAD_MODE_AUTO && p.lazy_mode == LLAMA_LAZY_MODE_AUTO && p.main_gpu == 0 && p.tensor_split == nullptr && p.progress_callback == nullptr && p.progress_callback_user_data == nullptr && p.kv_overrides == nullptr && !p.vocab_only && !p.check_tensors && p.use_extra_bufts && !p.no_host && !p.no_alloc && !p.load_mtp, "typed_default_values_differ_from_pinned_source"); }
static std::string layouts() { std::ostringstream o; o << "{\"pointer\":" << sizeof(void*) << ",\"token_size\":" << sizeof(llama_token) << ",\"bool_size\":" << sizeof(bool) << ",\"model_params_size\":" << sizeof(llama_model_params) << ",\"model_params_align\":" << alignof(llama_model_params) << ",\"token_data_size\":" << sizeof(llama_token_data) << ",\"token_array_size\":" << sizeof(llama_token_data_array) << ",\"model_offsets\":{";
#define OFFSET(n) o << "\"" #n "\":" << offsetof(llama_model_params, n)
    OFFSET(devices); o << ','; OFFSET(tensor_buft_overrides); o << ','; OFFSET(n_gpu_layers); o << ','; OFFSET(split_mode); o << ','; OFFSET(load_mode); o << ','; OFFSET(lazy_mode); o << ','; OFFSET(main_gpu); o << ','; OFFSET(tensor_split); o << ','; OFFSET(progress_callback); o << ','; OFFSET(progress_callback_user_data); o << ','; OFFSET(kv_overrides); o << ','; OFFSET(vocab_only); o << ','; OFFSET(check_tensors); o << ','; OFFSET(use_extra_bufts); o << ','; OFFSET(no_host); o << ','; OFFSET(no_alloc); o << ','; OFFSET(load_mtp);
#undef OFFSET
    o << "},\"candidate_offsets\":{\"id\":" << offsetof(llama_token_data, id) << ",\"logit\":" << offsetof(llama_token_data, logit) << ",\"p\":" << offsetof(llama_token_data, p) << "},\"array_offsets\":{\"data\":" << offsetof(llama_token_data_array, data) << ",\"size\":" << offsetof(llama_token_data_array, size) << ",\"selected\":" << offsetof(llama_token_data_array, selected) << ",\"sorted\":" << offsetof(llama_token_data_array, sorted) << "}}"; return o.str(); }

struct Reader {
    const std::string& bytes; size_t at = 0;
    explicit Reader(const std::string& s) : bytes(s) {}
    std::string take(size_t n) { need(n <= bytes.size() - at, "pack_truncated"); std::string s = bytes.substr(at, n); at += n; return s; }
    uint32_t u32() { auto s = take(4); uint32_t x = 0; for (unsigned i = 0; i < 4; ++i) x |= uint32_t(static_cast<unsigned char>(s[i])) << (i * 8); return x; }
    std::string span(size_t cap) { uint32_t n = u32(); need(n <= cap, "pack_span_cap"); return take(n); }
    std::string id() { auto s = span(256); need(!s.empty(), "empty_pack_id"); for (unsigned char c : s) need(c >= 32 && c <= 126, "pack_id_ascii_required"); return s; }
    std::string sha() { auto s = take(32); return hex(reinterpret_cast<const unsigned char*>(s.data()), s.size()); }
};
struct Grammar { std::string id, text, sha; };
struct Case { std::string id, bytes, sha; uint32_t group = 0, grammar = 0, expected = 0; };
struct Prefix { std::string id, sha; uint32_t doc = 0, kind = 0, cut = 0; };
struct Pack { std::vector<Grammar> grammars; std::vector<Case> cases; std::vector<Prefix> prefixes; };
static Pack parse_pack(const std::string& bytes) {
    Reader r(bytes); need(r.take(8) == std::string("R09NC02\0", 8) && r.u32() == 2, "pack_magic_version"); uint32_t ng = r.u32(), nc = r.u32(), np = r.u32();
    need(ng >= 1 && ng <= 20 && nc >= 1 && nc <= CASEMAX && np <= PREFIXMAX, "pack_counts"); Pack out;
    for (uint32_t i = 0; i < ng; ++i) { Grammar g; g.id = r.id(); g.sha = r.sha(); g.text = r.span(G); need(!g.text.empty() && valid_utf8(g.text) && g.text.find('\0') == std::string::npos && digest(g.text) == g.sha, "grammar_bytes_or_hash"); out.grammars.push_back(std::move(g)); }
    for (uint32_t i = 0; i < nc; ++i) { Case c; c.id = r.id(); c.group = r.u32(); c.grammar = r.u32(); c.expected = r.u32(); c.sha = r.sha(); c.bytes = r.span(B); need(c.group <= 2 && c.grammar < ng && c.expected <= 3 && digest(c.bytes) == c.sha, "case_binding_or_hash");
        if (c.group == 0) {
            if (c.expected == 3) need(c.id == "primary/161" && c.sha == "8414c3ed0614d67fa5b8c152438a2f2eb71f534a7ba1a1658c386f642349b308" && c.bytes.find('\0') == 169 && c.bytes.find('\0', 170) == std::string::npos, "unreviewed_primary_NUL_harness_disposition");
            else need(c.expected <= 1 && valid_utf8(c.bytes) && c.bytes.find('\0') == std::string::npos, "primary_native_byte_preflight");
        } else if (c.group == 1) need(c.expected == 1 && valid_utf8(c.bytes) && c.bytes.find('\0') == std::string::npos, "new_authored_native_byte_preflight");
        else need(c.expected >= 2, "independent_guard_expected_kind");
        if (c.expected == 2) need(!valid_utf8(c.bytes), "declared_UTF8_guard_is_not_invalid");
        if (c.expected == 3) need(valid_utf8(c.bytes) && c.bytes.find('\0') != std::string::npos, "declared_NUL_guard_is_not_NUL"); out.cases.push_back(std::move(c)); }
    for (uint32_t i = 0; i < np; ++i) { Prefix p; p.id = r.id(); p.doc = r.u32(); p.kind = r.u32(); p.cut = r.u32(); p.sha = r.sha(); need(p.doc < nc && p.kind <= 2 && out.cases[p.doc].expected == 1, "prefix_binding");
        if (p.kind == 0) need(p.cut < out.cases[p.doc].bytes.size() && digest(out.cases[p.doc].bytes.substr(0, p.cut)) == p.sha, "prefix_cut_or_hash");
        else need(p.cut == 0 && p.sha == std::string(64, '0'), "natural_prefix_reserved_fields"); out.prefixes.push_back(std::move(p)); }
    need(r.at == bytes.size(), "pack_trailing_bytes"); std::vector<std::string> ids;
    for (const auto& g : out.grammars) ids.push_back("g:" + g.id); for (const auto& c : out.cases) ids.push_back("d:" + c.id); for (const auto& p : out.prefixes) ids.push_back("p:" + p.id);
    std::sort(ids.begin(), ids.end()); need(std::adjacent_find(ids.begin(), ids.end()) == ids.end(), "duplicate_pack_ids"); return out;
}
struct NativeSession {
    Api& api; bool backend = false; llama_model* model = nullptr; ggml_backend_dev_t empty_devices[1] = {nullptr};
    explicit NativeSession(Api& a) : api(a) {}
    ~NativeSession() { if (model) api.llama_model_free(model); if (backend) api.llama_backend_free(); }
};
struct Sampler {
    Api& api; llama_sampler* value = nullptr;
    Sampler(Api& a, const llama_vocab* v, const Grammar& g) : api(a) { tick(); value = api.llama_sampler_init_grammar(v, g.text.c_str(), "root"); try { tick(); need(value != nullptr, "grammar_initialization_failed"); } catch (...) { if (value) { api.llama_sampler_free(value); value = nullptr; } throw; } }
    ~Sampler() { if (value) api.llama_sampler_free(value); }
    Sampler(const Sampler&) = delete; Sampler& operator=(const Sampler&) = delete;
};
static bool admitted(Api& a, Sampler& s, llama_token id) {
    llama_token_data value{id, 0.0f, 0.0f}; llama_token_data_array array{&value, 1, -1, false}; tick(); ++apply_calls; a.llama_sampler_apply(s.value, &array); tick();
    need(array.data == &value && array.size == 1 && array.selected == -1 && !array.sorted && value.id == id && value.p == 0.0f, "candidate_shape_changed");
    if (std::isinf(value.logit) && value.logit < 0) return false; need(std::isfinite(value.logit) && value.logit == 0.0f, "unexpected_candidate_logit"); return true;
}
static std::vector<llama_token> tokenize(Api& a, const llama_vocab* v, const std::string& s) {
    need(s.size() <= B, "document_byte_cap"); llama_token first{}; const char empty = '\0'; const char* p = s.empty() ? &empty : s.data();
    tick(); ++tokenize_calls; int32_t n = a.llama_tokenize(v, p, static_cast<int32_t>(s.size()), &first, 1, false, false); tick();
    need(n != (std::numeric_limits<int32_t>::min)(), "tokenize_overflow"); std::vector<llama_token> out;
    if (n >= 0) { need(n <= 1, "tokenize_success_exceeds_capacity"); if (n) out.push_back(first); }
    else { int64_t required = -static_cast<int64_t>(n); need(required > 1 && required <= K, "token_required_cap"); out.resize(static_cast<size_t>(required)); tick(); ++tokenize_calls; int32_t again = a.llama_tokenize(v, p, static_cast<int32_t>(s.size()), out.data(), static_cast<int32_t>(out.size()), false, false); tick(); need(again == required, "token_retry_size_changed"); }
    need(out.size() <= TOTALTOKENS - token_budget_used, "total_token_budget"); token_budget_used += out.size(); return out;
}
static std::string piece(Api& a, const llama_vocab* v, llama_token id) {
    char first = 0; tick(); ++piece_calls; int32_t n = a.llama_token_to_piece(v, id, &first, 1, 0, true); tick(); need(n != (std::numeric_limits<int32_t>::min)(), "piece_unexpected_int32min");
    if (n >= 0) { need(n <= 1, "piece_success_exceeds_capacity"); return std::string(&first, static_cast<size_t>(n)); }
    int64_t required = -static_cast<int64_t>(n); need(required > 1 && required <= P, "piece_required_cap"); std::string out(static_cast<size_t>(required), '\0'); tick(); ++piece_calls;
    int32_t again = a.llama_token_to_piece(v, id, out.data(), static_cast<int32_t>(out.size()), 0, true); tick(); need(again == required, "piece_retry_size_changed"); return out;
}
struct Tokens { std::vector<llama_token> ids; std::vector<size_t> ends; std::vector<bool> complete_before_partial; std::string harness; size_t nul_piece = (std::numeric_limits<size_t>::max)(), nul_offset = (std::numeric_limits<size_t>::max)(); };
static Tokens prepare(Api& a, const llama_vocab* v, int32_t nv, const std::vector<llama_token>& eog, const std::string& bytes) {
    Tokens out; if (!valid_utf8(bytes)) { out.harness = "harness_utf8_rejection"; return out; } if (bytes.find('\0') != std::string::npos) { out.harness = "harness_raw_nul_rejection"; return out; }
    out.ids = tokenize(a, v, bytes); size_t offset = 0;
    for (size_t i = 0; i < out.ids.size(); ++i) { auto id = out.ids[i]; if (id < 0 || id >= nv) { out.harness = "harness_token_id_bounds"; return out; }
        if (std::binary_search(eog.begin(), eog.end(), id)) { out.harness = "harness_input_eog_excluded"; return out; }
        std::string p = piece(a, v, id); size_t nul = p.find('\0'); if (nul != std::string::npos && out.nul_piece == (std::numeric_limits<size_t>::max)()) { out.nul_piece = i; out.nul_offset = nul; }
        if (p.size() > bytes.size() - offset || bytes.compare(offset, p.size(), p) != 0) { out.harness = "harness_roundtrip_failure"; return out; }
        size_t next = offset + p.size(); bool earlier_complete = false;
        if (next < bytes.size() && (static_cast<unsigned char>(bytes[next]) & 0xc0) == 0x80) for (size_t j = offset + 1; j < next; ++j) if ((static_cast<unsigned char>(bytes[j]) & 0xc0) != 0x80) { earlier_complete = true; break; }
        offset = next; out.ends.push_back(offset); out.complete_before_partial.push_back(earlier_complete);
    }
    if (offset != bytes.size()) out.harness = "harness_roundtrip_failure"; return out;
}
struct Observation { std::string status, eog_json = "null"; size_t rejected = (std::numeric_limits<size_t>::max)(); bool all_tokens = false, all_eog = false, no_eog = false; };
static Observation observe(Api& a, const llama_vocab* v, const Grammar& g, const std::vector<llama_token>& ids, size_t take, const std::vector<llama_token>& eog) {
    Sampler s(a, v, g); Observation out;
    for (size_t i = 0; i < take; ++i) { if (!admitted(a, s, ids[i])) { out.status = "native_token_rejection"; out.rejected = i; return out; } tick(); ++accept_calls; a.llama_sampler_accept(s.value, ids[i]); tick(); }
    out.all_tokens = true; out.all_eog = true; out.no_eog = true; std::ostringstream results; results << '[';
    for (size_t i = 0; i < eog.size(); ++i) { bool yes = admitted(a, s, eog[i]); if (i) results << ','; results << "{\"id\":" << eog[i] << ",\"admitted\":" << (yes ? "true" : "false") << '}'; out.all_eog = out.all_eog && yes; out.no_eog = out.no_eog && !yes; }
    results << ']'; out.eog_json = results.str(); need(out.all_eog || out.no_eog, "eog_branch_disagreement"); out.status = out.all_eog ? "native_member" : "native_eog_rejection"; return out;
}
static std::string observation(const Observation& o) { return "\"status\":" + q(o.status) + ",\"all_input_tokens_admitted\":" + (o.all_tokens ? "true" : "false") + ",\"first_rejected_token_index\":" + (o.rejected == (std::numeric_limits<size_t>::max)() ? std::string("null") : std::to_string(o.rejected)) + ",\"completion_EOG\":" + o.eog_json; }
static std::string rejection_span(const Observation& o, const Tokens& tokens) { if (o.rejected == (std::numeric_limits<size_t>::max)()) return ",\"first_rejected_byte_start\":null,\"first_rejected_byte_end\":null"; need(o.rejected < tokens.ends.size(), "rejected_span_bounds"); return ",\"first_rejected_byte_start\":" + std::to_string(o.rejected ? tokens.ends[o.rejected - 1] : 0) + ",\"first_rejected_byte_end\":" + std::to_string(tokens.ends[o.rejected]); }
// Input is already strict valid UTF-8. Returns scalar width only if cut is inside it.
static unsigned split_width(const std::string& s, size_t cut) { if (!cut || cut >= s.size() || (static_cast<unsigned char>(s[cut]) & 0xc0) != 0x80) return 0; size_t start = cut; while (start && (static_cast<unsigned char>(s[start]) & 0xc0) == 0x80) --start; unsigned char c = static_cast<unsigned char>(s[start]); return c < 0xe0 ? 2u : (c < 0xf0 ? 3u : 4u); }
struct CpuIdentity { ggml_backend_reg_t reg = nullptr; ggml_backend_dev_t dev = nullptr; };
static void check_cpu_identity(Api& api, const CpuIdentity& cpu) {
    tick(); need(cpu.reg && cpu.dev && api.ggml_backend_reg_count() == 1 && api.ggml_backend_reg_get(0) == cpu.reg && native_text(api.ggml_backend_reg_name(cpu.reg), 128) == R09_CPU_REGISTRY_NAME, "cpu_registry_not_exact_singleton");
    need(api.ggml_backend_reg_dev_count(cpu.reg) == 1 && api.ggml_backend_dev_count() == 1 && api.ggml_backend_reg_dev_get(cpu.reg, 0) == cpu.dev && api.ggml_backend_dev_get(0) == cpu.dev && api.ggml_backend_dev_type(cpu.dev) == GGML_BACKEND_DEVICE_TYPE_CPU && native_text(api.ggml_backend_dev_name(cpu.dev), 128) == R09_CPU_DEVICE_NAME, "cpu_device_identity_or_name_changed"); tick();
}
static CpuIdentity cpu_before_init(Runtime& runtime, Api& api, Output& out, const std::wstring& cpu) {
    need(cpu == L"ggml-cpu-x64.dll" && cpu == R09_CPU_BASENAME, "cpu_basename_not_bound"); need(GetEnvironmentVariableW(L"GGML_BACKEND_PATH", nullptr, 0) == 0 && GetLastError() == ERROR_ENVVAR_NOT_FOUND, "ambient_backend_path_forbidden");
    runtime.recognition = true; runtime.lease(L"ggml-cpu-x64.dll"); if (R09_LIBOMP_REQUIRED) runtime.lease(L"libomp.dll");
    std::string path = utf8((runtime.root / cpu).wstring()); tick(); auto reg = api.ggml_backend_load(path.c_str()); tick(); need(reg != nullptr, "explicit_cpu_load_failed");
    need(api.ggml_backend_reg_dev_count(reg) == 1, "cpu_registration_device_count"); CpuIdentity identity{reg, api.ggml_backend_reg_dev_get(reg, 0)}; check_cpu_identity(api, identity);
    HMODULE module = GetModuleHandleW(cpu.c_str()), hold = nullptr; need(module && same(module_path(module), runtime.root / cpu) && GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_PIN, (runtime.root / cpu).c_str(), &hold) && hold == module, "cpu_module_pin_failed");
    out.row("{\"event\":\"cpu_registry_verified_before_llama_backend_init\",\"registry_count\":1,\"device_count\":1,\"registry_name\":" + q(R09_CPU_REGISTRY_NAME) + ",\"device_name\":" + q(R09_CPU_DEVICE_NAME) + ",\"modules\":" + runtime.modules() + "}");
    return identity;
}
static void recognize(Runtime& runtime, Api& api, Output& out, const fs::path& pack_path, const std::wstring& cpu, const std::array<fs::path, 3>& shards, llama_model_params params) {
    need(R09_RECOGNITION_ENABLED, "recognition_not_enabled_by_separately_reviewed_parent_pin_header");
    need(same(pack_path, absolute(R09_PACK.path)), "pack_path_not_parent_bound"); Lease packed(pack_path, PACKMAX); packed.verify(R09_PACK.bytes, R09_PACK.sha256); Pack pack = parse_pack(packed.read(PACKMAX));
    out.row("{\"event\":\"pack_verified_before_backend_or_model\",\"pack_sha256\":" + q(packed.sha) + ",\"cases\":" + std::to_string(pack.cases.size()) + ",\"prefixes\":" + std::to_string(pack.prefixes.size()) + "}");
    std::vector<std::unique_ptr<Lease>> model_leases; std::array<std::string, 3> shard_utf8; std::array<const char*, 3> shard_ptrs{};
    for (size_t i = 0; i < shards.size(); ++i) { need(same(shards[i], absolute(R09_SHARDS[i].path)), "shard_path_not_parent_bound"); for (size_t j = 0; j < i; ++j) need(!same(shards[i], shards[j]), "duplicate_shard_path");
        out.row("{\"event\":\"before_exact_shard_hash\",\"index\":" + std::to_string(i) + ",\"path\":" + q(utf8(shards[i].wstring())) + ",\"expected_bytes\":" + std::to_string(R09_SHARDS[i].bytes) + "}");
        auto l = std::make_unique<Lease>(shards[i], R09_SHARDS[i].bytes); l->verify(R09_SHARDS[i].bytes, R09_SHARDS[i].sha256);
        out.row("{\"event\":\"exact_shard_hash_returned\",\"index\":" + std::to_string(i) + ",\"bytes\":" + std::to_string(l->bytes) + ",\"sha256\":" + q(l->sha) + "}");
        model_leases.push_back(std::move(l)); shard_utf8[i] = utf8(shards[i].wstring()); shard_ptrs[i] = shard_utf8[i].c_str(); }
    out.row("{\"event\":\"three_exact_shards_hash_verified_and_read_leased\",\"weight_file_hash_reads\":true,\"tensor_weight_allocation_claim\":false}");
    CpuIdentity cpu_identity = cpu_before_init(runtime, api, out, cpu); NativeSession session(api); tick(); api.llama_backend_init(); session.backend = true; tick();
    check_cpu_identity(api, cpu_identity); out.row("{\"event\":\"backend_init_returned_exact_CPU_identity_rechecked\",\"modules\":" + runtime.modules() + "}");
    params.devices = session.empty_devices; params.tensor_buft_overrides = nullptr; params.n_gpu_layers = 0; params.split_mode = LLAMA_SPLIT_MODE_NONE; params.load_mode = LLAMA_LOAD_MODE_NONE; params.lazy_mode = LLAMA_LAZY_MODE_OFF; params.main_gpu = -1; params.tensor_split = nullptr; params.progress_callback = nullptr; params.progress_callback_user_data = nullptr; params.kv_overrides = nullptr; params.vocab_only = true; params.check_tensors = false; params.use_extra_bufts = false; params.no_host = false; params.no_alloc = true; params.load_mtp = false;
    out.row("{\"event\":\"before_model_load_from_three_explicit_splits\",\"effective_params\":" + defaults(params) + ",\"empty_devices_array_nonnull\":true,\"cooperative_deadline_not_interruptible_native_call\":true}");
    tick(); session.model = api.llama_model_load_from_splits(shard_ptrs.data(), shard_ptrs.size(), params); tick(); need(session.model, "vocabulary_only_model_load_failed"); const llama_vocab* vocab = api.llama_model_get_vocab(session.model); need(vocab, "null_borrowed_vocabulary"); int32_t nv = api.llama_vocab_n_tokens(vocab); need(nv > 0 && nv <= static_cast<int32_t>(VMAX), "vocabulary_count_cap");
    std::vector<llama_token> eog; for (int32_t id = 0; id < nv; ++id) { tick(); if (api.llama_vocab_is_eog(vocab, id)) { need(eog.size() < EMAX, "EOG_count_cap"); eog.push_back(id); } } need(!eog.empty(), "empty_EOG_set");
    std::ostringstream e; e << '['; for (size_t i = 0; i < eog.size(); ++i) { if (i) e << ','; e << eog[i]; } e << ']';
    out.row("{\"event\":\"all_vocabulary_ids_EOG_enumerated\",\"vocabulary_count\":" + std::to_string(nv) + ",\"EOG_ids\":" + e.str() + ",\"EOG_JSON_sha256\":" + q(digest(e.str())) + ",\"modules\":" + runtime.modules() + "}");
    size_t completed = 0, prefix_done = 0; std::array<size_t, 3> completed_groups{}, native_results{}, harness_dispositions{}; bool unavailable = false;
    for (size_t index = 0; index < pack.cases.size(); ++index) { const auto& c = pack.cases[index]; tick(); out.row("{\"event\":\"before_case\",\"case_index\":" + std::to_string(index) + ",\"id\":" + q(c.id) + ",\"document_sha256\":" + q(c.sha) + "}");
        Tokens tokens = prepare(api, vocab, nv, eog, c.bytes); bool match = false; std::string fields;
        if (!tokens.harness.empty()) { ++harness_dispositions[c.group]; match = (c.expected == 2 && tokens.harness == "harness_utf8_rejection") || (c.expected == 3 && tokens.harness == "harness_raw_nul_rejection"); fields = "\"status\":" + q(tokens.harness) + ",\"native_membership\":null,\"completion_EOG\":null"; }
        else { ++native_results[c.group]; Observation o = observe(api, vocab, pack.grammars[c.grammar], tokens.ids, tokens.ids.size(), eog); match = (c.expected == 1 && o.status == "native_member") || (c.expected == 0 && (o.status == "native_token_rejection" || o.status == "native_eog_rejection")); fields = observation(o) + rejection_span(o, tokens); }
        out.row("{\"event\":\"case_result\",\"case_index\":" + std::to_string(index) + ",\"source_group\":" + std::to_string(c.group) + ",\"id\":" + q(c.id) + ",\"bytes\":" + std::to_string(c.bytes.size()) + ",\"document_sha256\":" + q(c.sha) + ",\"tokens\":" + std::to_string(tokens.ids.size()) + ",\"used_piece_NUL_seen\":" + (tokens.nul_piece == (std::numeric_limits<size_t>::max)() ? "false" : "true") + ",\"first_NUL_piece_index\":" + (tokens.nul_piece == (std::numeric_limits<size_t>::max)() ? std::string("null") : std::to_string(tokens.nul_piece)) + ",\"first_NUL_offset_in_piece\":" + (tokens.nul_offset == (std::numeric_limits<size_t>::max)() ? std::string("null") : std::to_string(tokens.nul_offset)) + ",\"expected_kind\":" + std::to_string(c.expected) + ",\"expected_native_membership\":" + (c.expected <= 1 ? (c.expected == 1 ? "true" : "false") : "null") + ",\"matches_expected\":" + (match ? "true" : "false") + "," + fields + "}"); ++completed; ++completed_groups[c.group]; need(match, "case_expectation_mismatch_stop");
        for (const auto& p : pack.prefixes) if (p.doc == index) { ++prefix_done; need(tokens.harness.empty(), "prefix_base_ineligible"); size_t count = 0, cut = p.cut; Tokens fresh; const Tokens* source = &tokens;
            if (p.kind == 0) { fresh = prepare(api, vocab, nv, eog, c.bytes.substr(0, cut)); need(fresh.harness.empty(), "byte_prefix_harness_failure"); count = fresh.ids.size(); source = &fresh; }
            else { bool found = false; for (size_t j = 0; j < tokens.ends.size(); ++j) { unsigned width = split_width(c.bytes, tokens.ends[j]); if ((p.kind == 1 && (width == 2 || width == 3)) || (p.kind == 2 && width == 4)) { count = j + 1; cut = tokens.ends[j]; found = true; break; } }
                if (!found) { unavailable = true; out.row("{\"event\":\"prefix_result\",\"id\":" + q(p.id) + ",\"status\":\"coverage_unavailable\",\"matches_expected\":null}"); continue; } }
            if (p.kind != 0) { need(count <= TOTALTOKENS - token_budget_used, "total_prefix_token_budget"); token_budget_used += count; }
            Observation o = observe(api, vocab, pack.grammars[c.grammar], source->ids, count, eog); bool pass = o.all_tokens && o.no_eog;
            bool complete_before_partial = count && source->complete_before_partial[count - 1];
            out.row("{\"event\":\"prefix_result\",\"id\":" + q(p.id) + ",\"base_id\":" + q(c.id) + ",\"prefix_kind\":" + std::to_string(p.kind) + ",\"byte_cut\":" + std::to_string(cut) + ",\"token_count\":" + std::to_string(count) + ",\"prefix_sha256\":" + q(digest(c.bytes.substr(0, cut))) + ",\"partial_UTF8_at_cut\":" + (split_width(c.bytes, cut) ? "true" : "false") + ",\"last_piece_complete_codepoints_before_partial\":" + (complete_before_partial ? "true" : "false") + ",\"matches_expected\":" + (pass ? "true" : "false") + "," + observation(o) + rejection_span(o, *source) + "}"); need(pass, "prefix_expectation_mismatch_stop");
        }
    }
    need(completed == pack.cases.size() && prefix_done == pack.prefixes.size(), "case_or_prefix_accounting"); need(!unavailable, "required_partial_UTF8_prefix_coverage_unavailable");
    // Explicit cleanup is reported before final publication; destructors remain fallback.
    tick(); llama_model* releasing = session.model; session.model = nullptr; api.llama_model_free(releasing); tick(); session.backend = false; api.llama_backend_free(); tick();
    out.row("{\"event\":\"recognition_batch_returned\",\"pack_format_version\":2,\"cases_completed\":" + std::to_string(completed) + ",\"source_group_completed\":{\"primary_frozen_wire\":" + std::to_string(completed_groups[0]) + ",\"new_serialization_of_retained_authored_abstention\":" + std::to_string(completed_groups[1]) + ",\"harness_byte_guards\":" + std::to_string(completed_groups[2]) + "},\"primary_native_results\":" + std::to_string(native_results[0]) + ",\"primary_harness_dispositions\":" + std::to_string(harness_dispositions[0]) + ",\"new_authored_native_results\":" + std::to_string(native_results[1]) + ",\"independent_guard_dispositions\":" + std::to_string(harness_dispositions[2]) + ",\"prefix_slots\":" + std::to_string(prefix_done) + ",\"total_token_budget_used\":" + std::to_string(token_budget_used) + ",\"tokenize_calls\":" + std::to_string(tokenize_calls) + ",\"piece_calls\":" + std::to_string(piece_calls) + ",\"apply_calls\":" + std::to_string(apply_calls) + ",\"accept_calls\":" + std::to_string(accept_calls) + ",\"EOG_accept_calls\":0,\"samplers_freed_before_model\":true,\"model_freed\":true,\"backend_free_returned\":true,\"modules\":" + runtime.modules() + ",\"scientific_validation\":\"not_established\"}");
}

int wmain(int argc, wchar_t** argv) {
    std::unique_ptr<Output> out;
    try {
        need(argc >= 2, "expected_mode"); std::string mode = utf8(argv[1]); need((mode == "--abi" && argc == 4) || (mode == "--recognize" && argc == 9), "expected_abi_runtime_output_or_recognize_runtime_output_pack_cpu_three_shards");
        fs::path root = absolute(argv[2]), output = absolute(argv[3]); out = std::make_unique<Output>(output, mode); tick(); Runtime runtime(root);
        // No backend registry/device API is called in --abi mode.
        // The pinned base DLL imports OpenMP: preload its exact leased bytes first.
        // Dependency DLL initialization may run even in ABI-only mode.
        if (R09_LIBOMP_REQUIRED) { out->row("{\"event\":\"before_explicit_required_OpenMP_dependency_load\",\"dependency_native_initialization_possible\":true}"); runtime.load_core(L"libomp.dll"); }
        HMODULE base = runtime.load_core(L"ggml-base.dll"); (void)base; HMODULE ggml = runtime.load_core(L"ggml.dll"); HMODULE llama = runtime.load_core(L"llama.dll");
        Api api(llama, ggml); out->row("{\"event\":\"exact_core_modules_loaded_exports_resolved\",\"modules\":" + runtime.modules() + ",\"layouts\":" + layouts() + "}");
        tick(); std::string version = native_text(api.llama_version(), 256); tick(); need(!version.empty(), "empty_version_observation"); for (unsigned char c : version) need(c >= 32 && c <= 126, "version_observation_not_printable_ASCII");
        bool version_pinned = R09_EXPECTED_LLAMA_VERSION[0] != '\0';
        if (version_pinned) need(version == R09_EXPECTED_LLAMA_VERSION, "version_string_not_parent_bound");
        else need(mode == "--abi", "recognition_requires_version_pinned_from_reviewed_ABI_report");
        tick(); llama_model_params params = api.llama_model_default_params(); tick(); out->row("{\"event\":\"typed_version_and_defaults_observed\",\"version\":" + q(version) + ",\"defaults\":" + defaults(params) + ",\"no_backend_or_model_call_so_far\":true}"); check_defaults(params);
        if (mode == "--abi") out->row("{\"event\":\"abi_observations_returned\",\"version_expected_previously_known\":" + std::string(version_pinned ? "true" : "false") + ",\"backend_init_called\":false,\"registry_called\":false,\"model_called\":false,\"scope\":\"typed version/defaults observation; independent ABI acceptance pending\"}");
        else { std::array<fs::path, 3> shards{absolute(argv[6]), absolute(argv[7]), absolute(argv[8])}; recognize(runtime, api, *out, absolute(argv[4]), argv[5], shards, params); }
        tick(); out->row("{\"event\":\"child_normal_completion\",\"mode\":" + q(mode) + ",\"elapsed_ms\":" + std::to_string(GetTickCount64() - START_MS) + ",\"parent_qualification_required\":true}"); out->commit(); std::cout << "{\"status\":\"child_returned_results_require_parent_review\"}\n"; return 0;
    } catch (const BridgeError& error) { std::string msg(error.what()); if (out) out->failure(msg); std::cout << "{\"status\":\"failed\",\"message\":" << q(msg) << "}\n"; return 2; }
      catch (const std::exception&) { if (out) out->failure("nonprotocol_cpp_exception_no_document_text_copied"); std::cout << "{\"status\":\"failed_nonprotocol_cpp_exception\"}\n"; return 3; }
      catch (...) { if (out) out->failure("unknown_cpp_exception"); std::cout << "{\"status\":\"failed_unknown_cpp_exception\"}\n"; return 4; }
}
