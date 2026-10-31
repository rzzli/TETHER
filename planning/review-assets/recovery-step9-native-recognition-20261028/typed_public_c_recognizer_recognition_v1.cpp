// DRAFT recognition v1: prospective singleton document/EOG qualification; source/pure only.
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
#include <exception>
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
constexpr uint64_t COOPERATIVE_MS = 117000;
static const ULONGLONG START_MS = GetTickCount64();
static uint64_t token_budget_used = 0, tokenize_calls = 0, piece_calls = 0, apply_calls = 0, accept_calls = 0;

struct BridgeError : std::runtime_error { std::string diagnostic_fields; explicit BridgeError(const char* text) : std::runtime_error(text) {} };
static void need(bool ok, const char* text) { if (!ok) throw BridgeError(text); }
static void tick() { need(GetTickCount64() - START_MS < COOPERATIVE_MS, "cooperative_deadline_expired"); }

// Aggregate in-memory native reservations/returns; durable stage snapshots only.
enum NativeKind { NATIVE_ggml_backend_dev_count, NATIVE_ggml_backend_dev_get, NATIVE_ggml_backend_dev_name, NATIVE_ggml_backend_dev_type, NATIVE_ggml_backend_load, NATIVE_ggml_backend_reg_count, NATIVE_ggml_backend_reg_dev_count, NATIVE_ggml_backend_reg_dev_get, NATIVE_ggml_backend_reg_get, NATIVE_ggml_backend_reg_name, NATIVE_llama_backend_free, NATIVE_llama_backend_init, NATIVE_llama_model_default_params, NATIVE_llama_model_free, NATIVE_llama_model_get_vocab, NATIVE_llama_model_load_from_splits, NATIVE_llama_sampler_accept, NATIVE_llama_sampler_apply, NATIVE_llama_sampler_free, NATIVE_llama_sampler_init_grammar, NATIVE_llama_token_to_piece, NATIVE_llama_tokenize, NATIVE_llama_version, NATIVE_llama_vocab_is_eog, NATIVE_llama_vocab_n_tokens, NATIVE_COUNT };
static const char* NATIVE_NAMES[NATIVE_COUNT] = {"ggml_backend_dev_count", "ggml_backend_dev_get", "ggml_backend_dev_name", "ggml_backend_dev_type", "ggml_backend_load", "ggml_backend_reg_count", "ggml_backend_reg_dev_count", "ggml_backend_reg_dev_get", "ggml_backend_reg_get", "ggml_backend_reg_name", "llama_backend_free", "llama_backend_init", "llama_model_default_params", "llama_model_free", "llama_model_get_vocab", "llama_model_load_from_splits", "llama_sampler_accept", "llama_sampler_apply", "llama_sampler_free", "llama_sampler_init_grammar", "llama_token_to_piece", "llama_tokenize", "llama_version", "llama_vocab_is_eog", "llama_vocab_n_tokens"};
static constexpr uint64_t NATIVE_CAPS[NATIVE_COUNT] = {2ull, 2ull, 2ull, 2ull, 1ull, 2ull, 3ull, 3ull, 2ull, 2ull, 1ull, 1ull, 1ull, 1ull, 1ull, 1ull, 1000000ull, 1013184ull, 206ull, 206ull, 2000000ull, 412ull, 1ull, 262144ull, 1ull};
static constexpr uint64_t NATIVE_TOTAL_CAP = 4276181;
static const char* NATIVE_CALL_CONTRACT_SHA = "30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861";
struct NativeState {
    std::array<uint64_t, NATIVE_COUNT> attempted{}, returned{}; uint64_t total_attempted = 0, total_returned = 0, exceptions = 0;
    NativeKind last_attempt = NATIVE_COUNT, last_return = NATIVE_COUNT; int last_return_kind = 0; int64_t last_scalar = 0; bool last_pointer_nonnull = false;
    bool cpu_load_return_observed = false, cpu_registry_nonnull = false, backend_init_return_observed = false;
    bool backend_owned = false, model_load_return_observed = false, model_return_nonnull = false, model_owned = false;
    bool model_free_attempted = false, model_free_return_observed = false, model_release_unknown = false;
    bool backend_free_attempted = false, backend_free_return_observed = false, backend_release_unknown = false, cleanup_failed = false;
    uint64_t sampler_nonnull_returns = 0, samplers_owned = 0, sampler_release_unknown = 0, sampler_free_returned_nonnull = 0;
    uint64_t cases_computed = 0, case_results_written = 0, prefix_slots_seen = 0, prefix_results_written = 0, EOG_ids_examined = 0;
    int64_t current_case_index = -1, current_prefix_slot = -1, last_tokenize_return = 0, last_piece_return = 0;
    bool last_apply_return_observed = false, last_apply_shape_valid = false; int last_apply_logit_kind = 0;
    int32_t last_EOG_id = -1; bool last_EOG_returned = false, last_EOG_value = false, required_UTF8_prefix_unavailable = false;
    std::array<uint64_t, 3> group_computed{}, group_results_written{};
};
static NativeState native_state;
static void native_reserve(NativeKind kind, bool cleanup) {
    if (!cleanup) { tick(); need(!native_state.cleanup_failed, "prior_native_cleanup_failed"); }
    need(kind < NATIVE_COUNT && native_state.attempted[kind] < NATIVE_CAPS[kind] && native_state.total_attempted < NATIVE_TOTAL_CAP, "native_call_attempt_cap");
    ++native_state.attempted[kind]; ++native_state.total_attempted; native_state.last_attempt = kind;
    if (kind == NATIVE_llama_tokenize) ++tokenize_calls;
    if (kind == NATIVE_llama_token_to_piece) ++piece_calls;
    if (kind == NATIVE_llama_sampler_apply) ++apply_calls;
    if (kind == NATIVE_llama_sampler_accept) ++accept_calls;
    if (kind == NATIVE_llama_sampler_free) { need(native_state.samplers_owned > 0, "sampler_free_without_owned_return"); --native_state.samplers_owned; ++native_state.sampler_release_unknown; }
    if (kind == NATIVE_llama_model_free) { native_state.model_free_attempted = true; native_state.model_owned = false; native_state.model_release_unknown = true; }
    if (kind == NATIVE_llama_backend_free) { native_state.backend_free_attempted = true; native_state.backend_owned = false; native_state.backend_release_unknown = true; }
}
static void native_returned(NativeKind kind) noexcept {
    ++native_state.returned[kind]; ++native_state.total_returned; native_state.last_return = kind;
    if (kind == NATIVE_llama_backend_init) { native_state.backend_init_return_observed = true; native_state.backend_owned = true; }
    if (kind == NATIVE_llama_backend_free) { native_state.backend_free_return_observed = true; native_state.backend_release_unknown = false; }
    if (kind == NATIVE_llama_model_free) { native_state.model_free_return_observed = true; native_state.model_release_unknown = false; }
    if (kind == NATIVE_llama_sampler_free) { --native_state.sampler_release_unknown; ++native_state.sampler_free_returned_nonnull; }
}
template<class F> static decltype(auto) native_call(NativeKind kind, F&& call, bool cleanup = false) {
    native_reserve(kind, cleanup);
    try {
        if constexpr (std::is_void<decltype(call())>::value) { call(); native_returned(kind); native_state.last_return_kind = 1; return; }
        else { auto value = call(); native_returned(kind);
            if constexpr (std::is_pointer<decltype(value)>::value) {
                native_state.last_return_kind = 3; native_state.last_pointer_nonnull = value != nullptr;
                if (kind == NATIVE_ggml_backend_load) { native_state.cpu_load_return_observed = true; native_state.cpu_registry_nonnull = value != nullptr; }
                if (kind == NATIVE_llama_model_load_from_splits) { native_state.model_load_return_observed = true; native_state.model_return_nonnull = value != nullptr; native_state.model_owned = value != nullptr; }
                if (kind == NATIVE_llama_sampler_init_grammar && value) { ++native_state.sampler_nonnull_returns; ++native_state.samplers_owned; }
            } else if constexpr (std::is_integral<decltype(value)>::value || std::is_enum<decltype(value)>::value) { native_state.last_return_kind = 2; native_state.last_scalar = static_cast<int64_t>(value); if (kind == NATIVE_llama_tokenize) native_state.last_tokenize_return = native_state.last_scalar; if (kind == NATIVE_llama_token_to_piece) native_state.last_piece_return = native_state.last_scalar; }
            else { static_assert(std::is_trivially_copyable<decltype(value)>::value, "Native return bookkeeping must not throw"); native_state.last_return_kind = 4; }
            return value;
        }
    } catch (...) { ++native_state.exceptions; throw; }
}
static std::string native_snapshot_fields();
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
static std::string native_snapshot_fields() {
    std::string counters = "{"; for (size_t k = 0; k < static_cast<size_t>(NATIVE_COUNT); ++k) { if (k) counters += ','; counters += q(NATIVE_NAMES[k]) + ":{\"attempted\":" + std::to_string(native_state.attempted[k]) + ",\"returned\":" + std::to_string(native_state.returned[k]) + "}"; } counters += '}';
    auto b = [](bool value) { return value ? "true" : "false"; };
    return ",\"native_call_contract_sha256\":" + q(NATIVE_CALL_CONTRACT_SHA) + ",\"native_call_counters\":" + counters + ",\"native_call_scope\":\"explicit_bridge_export_calls_only\",\"unrecorded_killed_tail\":\"unknown_since_last_acknowledged_snapshot\",\"native_state\":{\"total_attempted\":" + std::to_string(native_state.total_attempted) + ",\"total_returned\":" + std::to_string(native_state.total_returned) + ",\"exceptions\":" + std::to_string(native_state.exceptions) +
        ",\"last_attempt\":" + (native_state.last_attempt == NATIVE_COUNT ? "null" : q(NATIVE_NAMES[native_state.last_attempt])) + ",\"last_return\":" + (native_state.last_return == NATIVE_COUNT ? "null" : q(NATIVE_NAMES[native_state.last_return])) + ",\"last_return_kind\":" + std::to_string(native_state.last_return_kind) + ",\"last_scalar\":" + std::to_string(native_state.last_scalar) + ",\"last_pointer_nonnull\":" + b(native_state.last_pointer_nonnull) + ",\"last_tokenize_return\":" + std::to_string(native_state.last_tokenize_return) + ",\"last_piece_return\":" + std::to_string(native_state.last_piece_return) + ",\"last_apply_return_observed\":" + b(native_state.last_apply_return_observed) + ",\"last_apply_shape_valid\":" + b(native_state.last_apply_shape_valid) + ",\"last_apply_logit_kind\":" + std::to_string(native_state.last_apply_logit_kind) +
        ",\"cpu_load_return_observed\":" + b(native_state.cpu_load_return_observed) + ",\"cpu_registry_nonnull\":" + b(native_state.cpu_registry_nonnull) + ",\"backend_init_return_observed\":" + b(native_state.backend_init_return_observed) + ",\"backend_owned\":" + b(native_state.backend_owned) + ",\"model_load_return_observed\":" + b(native_state.model_load_return_observed) + ",\"model_return_nonnull\":" + b(native_state.model_return_nonnull) + ",\"model_owned\":" + b(native_state.model_owned) + ",\"model_free_attempted\":" + b(native_state.model_free_attempted) + ",\"model_free_return_observed\":" + b(native_state.model_free_return_observed) + ",\"model_release_unknown\":" + b(native_state.model_release_unknown) + ",\"backend_free_attempted\":" + b(native_state.backend_free_attempted) + ",\"backend_free_return_observed\":" + b(native_state.backend_free_return_observed) + ",\"backend_release_unknown\":" + b(native_state.backend_release_unknown) + ",\"cleanup_failed\":" + b(native_state.cleanup_failed) +
        ",\"sampler_nonnull_returns\":" + std::to_string(native_state.sampler_nonnull_returns) + ",\"samplers_owned\":" + std::to_string(native_state.samplers_owned) + ",\"sampler_release_unknown\":" + std::to_string(native_state.sampler_release_unknown) + ",\"sampler_free_returned_nonnull\":" + std::to_string(native_state.sampler_free_returned_nonnull) + ",\"token_work_reserved\":" + std::to_string(token_budget_used) + ",\"current_case_index\":" + std::to_string(native_state.current_case_index) + ",\"current_prefix_slot\":" + std::to_string(native_state.current_prefix_slot) + ",\"group_computed\":[" + std::to_string(native_state.group_computed[0]) + "," + std::to_string(native_state.group_computed[1]) + "," + std::to_string(native_state.group_computed[2]) + "],\"group_results_written\":[" + std::to_string(native_state.group_results_written[0]) + "," + std::to_string(native_state.group_results_written[1]) + "," + std::to_string(native_state.group_results_written[2]) + "],\"cases_computed\":" + std::to_string(native_state.cases_computed) + ",\"case_results_written\":" + std::to_string(native_state.case_results_written) + ",\"prefix_slots_seen\":" + std::to_string(native_state.prefix_slots_seen) + ",\"prefix_results_written\":" + std::to_string(native_state.prefix_results_written) + ",\"EOG_ids_examined\":" + std::to_string(native_state.EOG_ids_examined) + ",\"last_EOG_id\":" + std::to_string(native_state.last_EOG_id) + ",\"last_EOG_returned\":" + b(native_state.last_EOG_returned) + ",\"last_EOG_value\":" + b(native_state.last_EOG_value) + ",\"required_UTF8_prefix_unavailable\":" + b(native_state.required_UTF8_prefix_unavailable) + "}";
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
    bool census = false, census_finalizing = false, recognition_mode = false; uint64_t structured_reserved = 0, structured_written_known = 0;
    static constexpr uint64_t CENSUS_MAX = 2ull * 1024 * 1024, CENSUS_RESERVE = 65536, CENSUS_ERROR_RESERVE = 8192;
    explicit Output(const fs::path& p, const std::string& mode) : dir(p), partial(p / L"result.partial.jsonl"), final(p / L"result.jsonl"), census(mode == "--module-census"), recognition_mode(mode == "--recognize") {
        no_reparse(p, true); need(GetFileAttributesW(p.c_str()) & FILE_ATTRIBUTE_DIRECTORY, "output_directory_required");
        need(fs::is_empty(p), "output_directory_not_empty");
        for (const wchar_t* name : {L"attempt.json", L"result.partial.jsonl", L"result.jsonl", L"failure.json"}) { fs::path f = p / name; no_reparse(f, false); need(GetFileAttributesW(f.c_str()) == INVALID_FILE_ATTRIBUTES && GetLastError() == ERROR_FILE_NOT_FOUND, "exclusive_output_exists"); }
        std::string claim_bytes = "{\"schema_version\":1,\"mode\":" + q(mode) + ",\"status\":\"claimed_before_native_load\",\"draft\":true}\n";
        Handle claim(CreateFileW((p / L"attempt.json").c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr)); need(claim.h != INVALID_HANDLE_VALUE, "attempt_claim_failed");
        if (census) structured_reserved += claim_bytes.size(); write_all(claim.h, claim_bytes); if (census) structured_written_known += claim_bytes.size();
        stream = Handle(CreateFileW(partial.c_str(), GENERIC_WRITE, FILE_SHARE_READ, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr)); need(stream.h != INVALID_HANDLE_VALUE, "partial_create_failed");
    }
    void row(const std::string& s, bool add_snapshot = true) {
        std::string payload = s;
        if (recognition_mode && add_snapshot) { need(!payload.empty() && payload.back() == '}', "snapshot_requires_object_row"); payload.pop_back(); payload += native_snapshot_fields() + '}'; }
        need(payload.size() <= 65536 && bytes + payload.size() + 1 <= OUTPUTMAX, "output_capture_cap");
        if (census) { uint64_t ceiling = CENSUS_MAX - (census_finalizing ? CENSUS_ERROR_RESERVE : CENSUS_RESERVE); need(payload.size() + 1 <= ceiling - structured_reserved, "census_structured_byte_cap"); structured_reserved += payload.size() + 1; }
        write_all(stream.h, payload + "\n"); bytes += payload.size() + 1; if (census) structured_written_known += payload.size() + 1;
    }
    void commit() { stream.close(); need(MoveFileExW(partial.c_str(), final.c_str(), MOVEFILE_WRITE_THROUGH), "exclusive_result_publish_failed"); committed = true; }
    void failure(const std::string& msg, const std::string& diagnostic_fields = std::string()) noexcept {
        if (committed) return; std::string s;
        try { s = "{\"schema_version\":1,\"status\":\"failed\",\"message\":" + q(msg) + ",\"elapsed_ms\":" + std::to_string(GetTickCount64() - START_MS) + ",\"token_budget_used\":" + std::to_string(token_budget_used) + ",\"apply_calls\":" + std::to_string(apply_calls) + ",\"accept_calls\":" + std::to_string(accept_calls) + diagnostic_fields + (recognition_mode ? native_snapshot_fields() : std::string()) + "}";
            if (census && s.size() > 4095) s = "{\"schema_version\":1,\"status\":\"failed\",\"message\":" + q(msg) + ",\"census_diagnostic_omitted_due_to_error_record_cap\":true}";
        } catch (...) { return; }
        if (census) census_finalizing = true;
        try { if (stream.h != INVALID_HANDLE_VALUE) row(s, false); } catch (...) {}
        // Reserve the independent marker separately, never reusing possibly written bytes.
        try { if (census) { need(s.size() + 1 <= CENSUS_MAX - structured_reserved, "census_error_marker_byte_cap"); structured_reserved += s.size() + 1; }
            Handle marker(CreateFileW((dir / L"failure.json").c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr));
            if (marker.h != INVALID_HANDLE_VALUE) { write_all(marker.h, s + "\n"); if (census) structured_written_known += s.size() + 1; }
        } catch (...) {}
    }
};

static fs::path module_path(HMODULE m) { std::array<wchar_t, 32768> b{}; DWORD n = GetModuleFileNameW(m, b.data(), static_cast<DWORD>(b.size())); need(n && n < b.size(), "module_path_failed"); return absolute(std::wstring(b.data(), n).c_str()); }
// Raw module metadata only. Never normalize, stat, open or resolve a reported path.
static std::wstring raw_reported_module_path(HMODULE module) {
    std::array<wchar_t, 32768> buffer{}; DWORD n = GetModuleFileNameW(module, buffer.data(), static_cast<DWORD>(buffer.size()));
    need(n > 0 && n < buffer.size() && buffer[n] == L'\0', "reported_module_path_incomplete");
    std::wstring result(buffer.data(), n); need(result.find(L'\0') == std::wstring::npos, "reported_module_path_embedded_NUL"); return result;
}
static std::wstring raw_snapshot_module_name(const MODULEENTRY32W& entry) {
    size_t count = 0; while (count < sizeof(entry.szModule) / sizeof(entry.szModule[0]) && entry.szModule[count] != L'\0') ++count;
    need(count > 0 && count < sizeof(entry.szModule) / sizeof(entry.szModule[0]), "snapshot_module_name_incomplete"); return std::wstring(entry.szModule, count);
}
static const ModulePin* pin(const std::wstring& name) { for (const auto& p : APPROVED_RUNTIME_DLLS) if (fold(name) == fold(p.name)) return &p; return nullptr; }
static bool core_name(const std::wstring& name) { auto n = fold(name); return n == L"llama.dll" || n == L"ggml.dll" || n == L"ggml-base.dll"; }
static bool allowed_runtime(const std::wstring& name, bool recognition) { return core_name(name) || (R09_LIBOMP_REQUIRED && fold(name) == L"libomp.dll") || (recognition && fold(name) == L"ggml-cpu-x64.dll"); }
constexpr size_t MODULE_DIAGNOSTIC_NAME_UNITS = 256, MODULE_DIAGNOSTIC_PATH_UNITS = 2048;
constexpr size_t MODULE_DIAGNOSTIC_FIELDS_MAX = 32768;
static std::string wide_diagnostic(const std::wstring& value, size_t cap) {
    size_t count = (std::min)(value.size(), cap); bool pair_cut_adjusted = false;
    if (count && count < value.size() && value[count - 1] >= 0xd800 && value[count - 1] <= 0xdbff && value[count] >= 0xdc00 && value[count] <= 0xdfff) { --count; pair_cut_adjusted = true; }
    std::wstring prefix = value.substr(0, count); std::ostringstream units;
    for (wchar_t c : prefix) units << std::hex << std::setw(4) << std::setfill('0') << static_cast<uint16_t>(c);
    std::string rendered = "null"; bool converted = false;
    try { rendered = q(utf8(prefix)); converted = true; } catch (...) { /* Exact code units remain available. */ }
    return "{\"utf16_units\":" + std::to_string(value.size()) + ",\"prefix_utf16_units\":" + std::to_string(count) + ",\"truncated\":" + (count < value.size() ? "true" : "false") +
        ",\"pair_cut_adjusted\":" + (pair_cut_adjusted ? "true" : "false") + ",\"utf8_conversion\":" + q(converted ? "returned" : "failed") + ",\"utf8\":" + rendered + ",\"utf16_code_units_hex\":" + q(units.str()) + "}";
}
// Shared prospective pure policy. Fingerprint is bound only after contract freeze.
static const char* PLATFORM_POLICY_ID = "trusted-System32-platform-v1";
static const char* PLATFORM_POLICY_SHA256 = "807995f6061d7a2c85144c58668fc2e4ecb79a4fb51d462e43d0a8dfc586d589";
static const char* RECOGNITION_POLICY_ID = "trusted-System32-recognition-v1";
static const char* RECOGNITION_POLICY_SHA256 = "4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713";
enum class ModulePhase { ABI, PreCPU, PostCPU };
struct PolicyPath { std::wstring key, parent, basename; };
static std::wstring policy_ascii_key(std::wstring value) {
    for (wchar_t& c : value) { if (c == L'/') c = L'\\'; if (c >= L'A' && c <= L'Z') c = static_cast<wchar_t>(c + (L'a' - L'A')); } return value;
}
static bool policy_scalar_units(const std::wstring& value) {
    for (size_t i = 0; i < value.size(); ++i) {
        uint16_t c = static_cast<uint16_t>(value[i]);
        if (c >= 0xd800 && c <= 0xdbff) { if (i + 1 >= value.size()) return false; uint16_t low = static_cast<uint16_t>(value[++i]); if (low < 0xdc00 || low > 0xdfff) return false; }
        else if (c >= 0xdc00 && c <= 0xdfff) return false;
    } return true;
}
static bool policy_device_stem(const std::wstring& value) {
    std::wstring stem = policy_ascii_key(value.substr(0, value.find(L'.')));
    if (stem == L"con" || stem == L"prn" || stem == L"aux" || stem == L"nul") return true;
    return stem.size() == 4 && (stem.substr(0, 3) == L"com" || stem.substr(0, 3) == L"lpt") && stem[3] >= L'1' && stem[3] <= L'9';
}
static bool policy_component(const std::wstring& value) {
    if (value.empty() || value == L"." || value == L".." || value.back() == L'.' || value.back() == L' ' || !policy_scalar_units(value) || policy_device_stem(value)) return false;
    for (wchar_t c : value) if (c <= 31 || c == 127 || c == L'~' || c == L'\\' || c == L'/' || c == L'<' || c == L'>' || c == L':' || c == L'"' || c == L'|' || c == L'?' || c == L'*') return false;
    return true;
}
static bool policy_name(const std::wstring& raw, std::wstring& key) {
    if (raw.size() > 255 || !policy_component(raw)) return false; key = policy_ascii_key(raw); return true;
}
static bool policy_path(const std::wstring& raw, PolicyPath& value) {
    if (raw.size() < 4 || raw.size() > 32767 || !policy_scalar_units(raw) || !((raw[0] >= L'A' && raw[0] <= L'Z') || (raw[0] >= L'a' && raw[0] <= L'z')) || raw[1] != L':' || (raw[2] != L'\\' && raw[2] != L'/')) return false;
    std::wstring key = policy_ascii_key(raw); size_t at = 3;
    while (at < key.size()) { size_t end = key.find(L'\\', at); if (end == std::wstring::npos) end = key.size(); if (!policy_component(key.substr(at, end - at))) return false; if (end == key.size()) break; at = end + 1; if (at == key.size()) return false; }
    size_t split = key.find_last_of(L'\\'); if (split == std::wstring::npos) return false;
    value.key = key; value.parent = key.substr(0, split); value.basename = key.substr(split + 1); return true;
}
static bool policy_platform_leaf(const std::wstring& key) {
    if (key.size() < 5 || key.substr(key.size() - 4) != L".dll") return false;
    auto initial = [](wchar_t c) { return (c >= L'a' && c <= L'z') || (c >= L'0' && c <= L'9') || c == L'_'; };
    if (!initial(key[0])) return false; for (wchar_t c : key) if (!initial(c) && c != L'.' && c != L'-') return false;
    std::wstring stem = key.substr(0, key.find(L'.')); if (stem == L"con" || stem == L"prn" || stem == L"aux" || stem == L"nul") return false;
    if (stem.size() == 4 && (stem.substr(0, 3) == L"com" || stem.substr(0, 3) == L"lpt") && stem[3] >= L'1' && stem[3] <= L'9') return false; return true;
}
struct ModulePolicyResult { const char* category = nullptr; const char* reason = "unclassified"; PolicyPath path; std::wstring name; size_t required = 6; bool canonical_metadata = false; };
static ModulePolicyResult evaluate_module_report(const std::wstring& raw_name, const std::wstring& raw_path, const PolicyPath& self, const PolicyPath& runtime, bool allow_cpu) {
    ModulePolicyResult result;
    if (!policy_name(raw_name, result.name)) { result.reason = "invalid_name"; return result; }
    if (!policy_path(raw_path, result.path)) { result.reason = "invalid_path"; return result; }
    if (result.name != result.path.basename) { result.reason = "name_path_mismatch"; return result; }
    result.canonical_metadata = true;
    if (result.path.key == self.key) { result.category = "self_executable"; result.reason = "accepted"; result.required = 0; return result; }
    if (result.name == self.basename) { result.reason = "reserved_self_wrong_path"; return result; }
    static const wchar_t* required[] = {L"libomp.dll", L"ggml-base.dll", L"ggml.dll", L"llama.dll", L"ggml-cpu-x64.dll"};
    size_t index = 0; while (index < 5 && result.name != required[index]) ++index;
    bool protected_name = result.name.rfind(L"ggml", 0) == 0 || result.name.rfind(L"llama", 0) == 0 || result.name.rfind(L"libomp", 0) == 0;
    if (result.path.parent == runtime.key || index < 5 || protected_name) {
        if ((index < 4 || (allow_cpu && index == 4)) && result.path.parent == runtime.key) { result.category = "pinned_runtime"; result.reason = "accepted"; result.required = index + 1; }
        else result.reason = "protected_native_not_eligible";
        return result;
    }
    if (result.path.parent == L"c:\\windows\\system32") {
        if (policy_platform_leaf(result.name)) { result.category = "trusted_platform_context"; result.reason = "accepted"; }
        else result.reason = "unsafe_platform_basename"; return result;
    }
    result.reason = "outside_declared_roots"; return result;
}
[[noreturn]] static void reject_platform_report(Output& output, size_t ordinal, const std::wstring& name, const std::wstring& path, const char* reason, const char* policy_id, const char* policy_sha, const char* phase) {
    BridgeError rejection("unapproved_non_native_module"); const char* publication = "not_attempted";
    try {
        std::string context = "\"context_status\":\"built\",\"original_tag\":\"unapproved_non_native_module\",\"branch\":\"trusted_System32_platform_policy\",\"policy_id\":" + q(policy_id) + ",\"policy_sha256\":" + q(policy_sha) + ",\"module_policy_phase\":" + q(phase) + ",\"reason\":" + q(reason) + ",\"enumeration_index\":" + std::to_string(ordinal) + ",\"path_representation\":\"raw_GetModuleFileNameW_no_filesystem_resolution\",\"name\":" + wide_diagnostic(name, MODULE_DIAGNOSTIC_NAME_UNITS) + ",\"path\":" + wide_diagnostic(path, MODULE_DIAGNOSTIC_PATH_UNITS);
        auto fields = [&](const char* state) { return std::string(",\"module_policy\":{") + context + ",\"diagnostic_row_publication\":" + q(state) + "}"; };
        publication = "attempt_reserved"; rejection.diagnostic_fields = fields(publication); need(rejection.diagnostic_fields.size() <= MODULE_DIAGNOSTIC_FIELDS_MAX, "module_diagnostic_cap");
        try { output.row("{\"event\":\"module_policy_rejection\"" + rejection.diagnostic_fields + "}"); publication = "returned"; } catch (...) { publication = "failed"; }
        rejection.diagnostic_fields = fields(publication); need(rejection.diagnostic_fields.size() <= MODULE_DIAGNOSTIC_FIELDS_MAX, "module_diagnostic_cap");
    } catch (...) { try { rejection.diagnostic_fields = std::string(",\"module_policy\":{\"context_status\":\"construction_failed\",\"original_tag\":\"unapproved_non_native_module\",\"diagnostic_row_publication\":") + q(publication) + "}"; } catch (...) { rejection.diagnostic_fields.clear(); } }
    throw rejection;
}
struct Runtime {
    fs::path root; PolicyPath self_context, runtime_context; std::vector<std::unique_ptr<Lease>> leases; DLL_DIRECTORY_COOKIE cookie = nullptr; bool recognition = false; ModulePhase module_phase = ModulePhase::ABI;
    explicit Runtime(fs::path p, const fs::path& executable, bool recognition_mode) : root(std::move(p)) {
        if (recognition_mode) module_phase = ModulePhase::PreCPU;
        need(policy_path(executable.wstring(), self_context) && policy_path(root.wstring(), runtime_context), "invalid_context");
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
    const char* policy_id() const { return module_phase == ModulePhase::ABI ? PLATFORM_POLICY_ID : RECOGNITION_POLICY_ID; }
    const char* policy_sha() const { return module_phase == ModulePhase::ABI ? PLATFORM_POLICY_SHA256 : RECOGNITION_POLICY_SHA256; }
    const char* phase_name() const { return module_phase == ModulePhase::ABI ? "abi" : (module_phase == ModulePhase::PreCPU ? "pre_cpu" : "post_cpu"); }
    std::string policy_fields() const { return ",\"module_policy_id\":" + q(policy_id()) + ",\"module_policy_sha256\":" + q(policy_sha()) + ",\"module_policy_phase\":" + q(phase_name()); }
    std::string modules(Output& diagnostics) {
        Handle snap(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, GetCurrentProcessId())); need(snap.h != INVALID_HANDLE_VALUE, "module_snapshot_failed"); MODULEENTRY32W entry{}; entry.dwSize = sizeof(entry); need(Module32FirstW(snap.h, &entry), "module_enumeration_failed");
        std::array<size_t, 6> required{}; std::vector<std::wstring> paths, names; paths.reserve(64); names.reserve(64); std::ostringstream result; result << '['; size_t ordinal = 0;
        do {
            tick(); ++ordinal; need(ordinal <= 64, "module_count_limit");
            std::wstring raw_name = raw_snapshot_module_name(entry), raw_path = raw_reported_module_path(entry.hModule);
            ModulePolicyResult match = evaluate_module_report(raw_name, raw_path, self_context, runtime_context, module_phase == ModulePhase::PostCPU);
            if (match.canonical_metadata && (std::find(paths.begin(), paths.end(), match.path.key) != paths.end() || std::find(names.begin(), names.end(), match.name) != names.end())) reject_platform_report(diagnostics, ordinal, raw_name, raw_path, "duplicate_report", policy_id(), policy_sha(), phase_name());
            if (!match.category) reject_platform_report(diagnostics, ordinal, raw_name, raw_path, match.reason, policy_id(), policy_sha(), phase_name());
            paths.push_back(match.path.key); names.push_back(match.name);
            if (match.required < required.size()) { ++required[match.required]; if (match.required) { const ModulePin* item = pin(match.name); need(item && allowed_runtime(item->name, module_phase == ModulePhase::PostCPU), "matched_runtime_pin_missing"); lease(item->name); } }
            if (ordinal > 1) result << ','; result << "{\"name\":" << q(utf8(raw_name)) << ",\"path\":" << q(utf8(raw_path)) << '}'; entry.dwSize = sizeof(entry);
        } while (Module32NextW(snap.h, &entry));
        need(GetLastError() == ERROR_NO_MORE_FILES, "module_enumeration_error"); for (size_t i = 0; i < (module_phase == ModulePhase::PostCPU ? 6u : 5u); ++i) need(required[i] == 1, "missing_required_reports"); result << ']'; return result.str();
    }
};

// Census metadata comparison is deliberately lexical, ASCII-only and in-memory.
// It neither reuses approved_system nor canonicalizes/opens an observed image path.
static std::wstring census_key(std::wstring value) {
    for (wchar_t& c : value) { if (c == L'/') c = L'\\'; if (c >= L'A' && c <= L'Z') c = static_cast<wchar_t>(c + (L'a' - L'A')); } return value;
}
static std::wstring census_basename(const std::wstring& value) { size_t at = value.find_last_of(L"\\/"); return at == std::wstring::npos ? value : value.substr(at + 1); }
static std::wstring census_parent(const std::wstring& value) { size_t at = value.find_last_of(L"\\/"); return at == std::wstring::npos ? std::wstring() : value.substr(0, at); }
static const char* json_bool(bool value) { return value ? "true" : "false"; }
struct CensusModule { size_t ordinal = 0; std::wstring name, path; bool name_terminated = false, path_ok = false, path_terminated = false, path_nul = false; };
struct ModuleCensus {
    enum Kind { Snapshot, First, Next, Path, Close, System, Count };
    static constexpr size_t MODULE_LIMIT = 64;
    static constexpr uint64_t DEADLINE_MS = 28000;
    Output& out; DWORD pid = GetCurrentProcessId(); HANDLE snapshot = INVALID_HANDLE_VALUE;
    std::array<uint32_t, Count> reserved{}, returned{}; uint64_t call_id = 0; size_t seen = 0;
    bool natural_end = false, metadata_complete = true, snapshot_close_returned = false, snapshot_close_ok = false, snapshot_close_publication_failed = false; DWORD snapshot_close_error = ERROR_SUCCESS;
    std::vector<CensusModule> rows; std::string reason = "not_finished";
    explicit ModuleCensus(Output& output) : out(output) { rows.reserve(MODULE_LIMIT); }
    static const char* name(Kind k) { static const char* names[Count] = {"CreateToolhelp32Snapshot", "Module32FirstW", "Module32NextW", "GetModuleFileNameW", "CloseHandle", "GetSystemDirectoryW"}; return names[k]; }
    static uint32_t maximum(Kind k) { return k == Next || k == Path ? 64u : 1u; }
    void check() const { need(GetTickCount64() - START_MS < DEADLINE_MS, "module_census_work_deadline"); }
    static std::string ordinal_text(size_t ordinal) { return ordinal ? std::to_string(ordinal) : "null"; }
    uint64_t reserve(Kind k, size_t ordinal, bool cleanup = false) {
        if (!cleanup) check(); need(reserved[k] < maximum(k), "module_census_api_attempt_cap"); ++reserved[k]; uint64_t id = ++call_id;
        out.row("{\"event\":\"census_call_reserved\",\"call_id\":" + std::to_string(id) + ",\"api\":" + q(name(k)) + ",\"ordinal\":" + ordinal_text(ordinal) + ",\"started_ms\":" + std::to_string(GetTickCount64() - START_MS) + "}"); return id;
    }
    void result(Kind k, uint64_t id, size_t ordinal, bool ok, DWORD error, const std::string& count, const std::string& more, bool clipped, bool cleanup = false) {
        ++returned[k]; out.row("{\"event\":\"census_call_returned\",\"call_id\":" + std::to_string(id) + ",\"api\":" + q(name(k)) + ",\"ordinal\":" + ordinal_text(ordinal) + ",\"ended_ms\":" + std::to_string(GetTickCount64() - START_MS) + ",\"ok\":" + json_bool(ok) + ",\"error\":" + (ok ? "null" : std::to_string(error)) + ",\"returned_count\":" + count + ",\"more_entries\":" + more + ",\"buffer_clipped\":" + json_bool(clipped) + "}"); if (!cleanup) check();
    }
    std::string counters() const { std::string value = "{"; for (size_t k = 0; k < Count; ++k) { if (k) value += ','; value += q(name(static_cast<Kind>(k))) + ":{\"reserved\":" + std::to_string(reserved[k]) + ",\"returned\":" + std::to_string(returned[k]) + "}"; } return value + '}'; }
    void close_snapshot() {
        if (snapshot == INVALID_HANDLE_VALUE) return;
        // Release ownership BEFORE the sole attempt: no destructor/failure retry.
        HANDLE owned = snapshot; snapshot = INVALID_HANDLE_VALUE; std::exception_ptr first_error; uint64_t id = call_id + 1;
        try { id = reserve(Close, 0, true); } catch (...) { snapshot_close_publication_failed = true; first_error = std::current_exception(); }
        BOOL ok = CloseHandle(owned); DWORD error = ok ? ERROR_SUCCESS : GetLastError(); snapshot_close_returned = true; snapshot_close_ok = ok != FALSE; snapshot_close_error = error;
        try { result(Close, id, 0, ok != FALSE, error, "null", "null", false, true); } catch (...) { snapshot_close_publication_failed = true; if (!first_error) first_error = std::current_exception(); }
        if (first_error) std::rethrow_exception(first_error); need(snapshot_close_ok, "module_census_snapshot_close_failed");
    }
    void capture(MODULEENTRY32W& entry) {
        CensusModule row; row.ordinal = rows.size() + 1; size_t nname = 0;
        while (nname < sizeof(entry.szModule) / sizeof(entry.szModule[0]) && entry.szModule[nname] != L'\0') ++nname;
        row.name_terminated = nname < sizeof(entry.szModule) / sizeof(entry.szModule[0]); row.name.assign(entry.szModule, nname);
        uint64_t id = reserve(Path, row.ordinal); std::array<wchar_t, 32768> buffer{};
        DWORD n = GetModuleFileNameW(entry.hModule, buffer.data(), static_cast<DWORD>(buffer.size()));
        bool clipped = n >= buffer.size(); bool ok = n > 0 && !clipped; DWORD error = ok ? ERROR_SUCCESS : GetLastError();
        // Retain a bounded exact return before post-call admission checks.
        size_t captured = (std::min)(static_cast<size_t>(n), buffer.size()); if (n) row.path.assign(buffer.data(), captured);
        row.path_ok = ok; row.path_terminated = ok && buffer[n] == L'\0'; row.path_nul = row.path.find(L'\0') != std::wstring::npos;
        result(Path, id, row.ordinal, ok, error, std::to_string(n), "null", clipped, true);
        std::string path = n ? wide_diagnostic(row.path, MODULE_DIAGNOSTIC_PATH_UNITS) : "null";
        bool complete = row.name_terminated && row.path_ok && row.path_terminated && !row.path_nul && row.name.size() <= MODULE_DIAGNOSTIC_NAME_UNITS && row.path.size() <= MODULE_DIAGNOSTIC_PATH_UNITS;
        out.row("{\"event\":\"module_metadata\",\"ordinal\":" + std::to_string(row.ordinal) + ",\"snapshot_name\":" + wide_diagnostic(row.name, MODULE_DIAGNOSTIC_NAME_UNITS) + ",\"snapshot_name_terminated\":" + json_bool(row.name_terminated) + ",\"path\":" + path + ",\"path_query_call_id\":" + std::to_string(id) + ",\"path_full_utf16_units_known\":" + (ok ? std::to_string(n) : "null") + ",\"path_buffer_terminated\":" + json_bool(row.path_terminated) + ",\"path_contains_NUL\":" + json_bool(row.path_nul) + "}");
        rows.push_back(std::move(row)); metadata_complete = metadata_complete && complete; check();
    }
    std::string partial_fields(const std::string& why) const {
        return ",\"module_census\":{\"reason\":" + q(why) + ",\"pid\":" + std::to_string(pid) + ",\"entries_recorded\":" + std::to_string(rows.size()) + ",\"entries_returned_at_least\":" + std::to_string(seen) + ",\"natural_end\":" + json_bool(natural_end) + ",\"metadata_complete\":" + json_bool(metadata_complete) + ",\"snapshot_close_returned\":" + json_bool(snapshot_close_returned) + ",\"snapshot_close_ok\":" + json_bool(snapshot_close_ok) + ",\"snapshot_close_error\":" + (snapshot_close_returned && !snapshot_close_ok ? std::to_string(snapshot_close_error) : "null") + ",\"snapshot_close_publication_failed\":" + json_bool(snapshot_close_publication_failed) + ",\"counters\":" + counters() + "}";
    }
    void collect(const fs::path& executable, const fs::path& runtime) {
        try {
            out.row("{\"event\":\"module_census_started\",\"schema_version\":1,\"mode\":\"--module-census\",\"scope\":\"post_core4_current_process_metadata_only\",\"pid\":" + std::to_string(pid) + ",\"known_core4_load_stage_returned\":true,\"Api_constructed\":false,\"target_C_queries\":0,\"ABI_eligibility_established\":false,\"max_modules\":64,\"max_structured_bytes\":2097152,\"reserved_terminal_bytes\":65536}");
            uint64_t id = reserve(Snapshot, 0); snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid); bool ok = snapshot != INVALID_HANDLE_VALUE; DWORD error = ok ? ERROR_SUCCESS : GetLastError(); result(Snapshot, id, 0, ok, error, "null", "null", false); need(ok, "module_census_snapshot_failed");
            MODULEENTRY32W entry{}; entry.dwSize = sizeof(entry); id = reserve(First, 0); BOOL found = Module32FirstW(snapshot, &entry); error = found ? ERROR_SUCCESS : GetLastError(); if (found) ++seen; reason = found ? "module_cap" : "api_error"; result(First, id, 0, found != FALSE, error, "null", json_bool(found != FALSE), false);
            while (found) {
                if (rows.size() == MODULE_LIMIT) { reason = "module_cap"; break; }
                capture(entry); entry.dwSize = sizeof(entry); id = reserve(Next, rows.size()); found = Module32NextW(snapshot, &entry); error = found ? ERROR_SUCCESS : GetLastError(); if (found) ++seen; else { natural_end = error == ERROR_NO_MORE_FILES; reason = natural_end ? "natural_end" : "api_error"; } result(Next, id, rows.size(), found != FALSE, error, "null", json_bool(found != FALSE), false);
            }
            out.row("{\"event\":\"module_census_enumeration_end\",\"entries_recorded\":" + std::to_string(rows.size()) + ",\"entries_returned_at_least\":" + std::to_string(seen) + ",\"natural_end\":" + json_bool(natural_end) + ",\"termination_reason\":" + q(reason) + "}");
            close_snapshot(); check();
            id = reserve(System, 0); std::array<wchar_t, 32768> system_buffer{}; UINT n = GetSystemDirectoryW(system_buffer.data(), static_cast<UINT>(system_buffer.size())); bool clipped = n >= system_buffer.size(); ok = n > 0 && !clipped; error = ok ? ERROR_SUCCESS : GetLastError();
            size_t captured = (std::min)(static_cast<size_t>(n), system_buffer.size()); std::wstring system_path(system_buffer.data(), captured); result(System, id, 0, ok, error, std::to_string(n), "null", clipped);
            bool system_complete = ok && system_buffer[n] == L'\0' && system_path.find(L'\0') == std::wstring::npos && system_path.size() <= MODULE_DIAGNOSTIC_PATH_UNITS;
            std::array<size_t, 5> required{}; std::string classifications = "["; std::wstring exe_key = census_key(executable.wstring()), runtime_key = census_key(runtime.wstring()), system_key = census_key(system_path);
            for (const CensusModule& row : rows) {
                std::wstring path_key = census_key(row.path), base = census_key(census_basename(row.path)); bool comparable = row.name_terminated && row.path_ok && row.path_terminated && !row.path_nul && row.name.size() <= MODULE_DIAGNOSTIC_NAME_UNITS && row.path.size() <= MODULE_DIAGNOSTIC_PATH_UNITS && system_complete;
                bool basename_match = comparable && census_key(row.name) == base, system_match = comparable && census_key(census_parent(row.path)) == system_key, listed = false;
                for (const wchar_t* allowed : R09_SYSTEM_DLL_NAMES) if (comparable && base == census_key(allowed)) listed = true;
                const char* category = "unresolved_metadata";
                if (comparable && basename_match) { category = "unlisted_report";
                    if (path_key == exe_key) { category = "self_executable"; ++required[0]; }
                    else { size_t index = 1; for (const wchar_t* core : {L"libomp.dll", L"ggml-base.dll", L"ggml.dll", L"llama.dll"}) { if (path_key == runtime_key + L"\\" + core) { category = "pinned_runtime_report"; ++required[index]; } ++index; }
                        if (std::string(category) == "unlisted_report" && system_match && listed) category = "listed_system_report"; }
                }
                metadata_complete = metadata_complete && basename_match;
                if (row.ordinal != 1) classifications += ',';
                classifications += "{\"ordinal\":" + std::to_string(row.ordinal) + ",\"category\":" + q(category) + ",\"snapshot_basename_matches_path\":" + (comparable ? json_bool(basename_match) : "null") + ",\"system_directory_matches\":" + (comparable ? json_bool(system_match) : "null") + ",\"system_basename_listed\":" + (comparable ? json_bool(listed) : "null") + "}";
            }
            classifications += ']'; bool all_required = true; for (size_t count : required) all_required = all_required && count == 1;
            out.census_finalizing = true;
            out.row("{\"event\":\"module_census_classification\",\"system_directory\":" + (n ? wide_diagnostic(system_path, MODULE_DIAGNOSTIC_PATH_UNITS) : "null") + ",\"rows\":" + classifications + ",\"required_report_counts\":{\"self_executable\":" + std::to_string(required[0]) + ",\"libomp.dll\":" + std::to_string(required[1]) + ",\"ggml-base.dll\":" + std::to_string(required[2]) + ",\"ggml.dll\":" + std::to_string(required[3]) + ",\"llama.dll\":" + std::to_string(required[4]) + "},\"all_required_once\":" + json_bool(all_required) + ",\"classification_is_eligibility\":false}");
            need(natural_end && metadata_complete && system_complete && all_required && snapshot_close_returned && snapshot_close_ok, "module_census_incomplete"); check();
            uint64_t before_reserved = out.structured_reserved, before_written = out.structured_written_known;
            out.row("{\"event\":\"module_census_complete\",\"pid\":" + std::to_string(pid) + ",\"entries_recorded\":" + std::to_string(rows.size()) + ",\"natural_end\":true,\"metadata_complete\":true,\"all_prior_rows_durable\":true,\"required_known_reports_complete\":true,\"classification_complete\":true,\"snapshot_close_returned\":true,\"Api_constructed\":false,\"target_C_queries\":0,\"ABI_eligibility_established\":false,\"counters\":" + counters() + ",\"structured_bytes_reserved_before_complete\":" + std::to_string(before_reserved) + ",\"structured_bytes_written_known_before_complete\":" + std::to_string(before_written) + "}");
        } catch (...) {
            std::exception_ptr primary = std::current_exception(); std::string why = "nonprotocol_or_unknown_exception";
            try { std::rethrow_exception(primary); } catch (const BridgeError& error) { why = error.what(); } catch (...) {}
            try { close_snapshot(); } catch (...) { /* Sole close attempt/outcome counters remain retained; never retry. */ }
            BridgeError failure("module_census_incomplete"); try { failure.diagnostic_fields = partial_fields(why); } catch (...) {} throw failure;
        }
    }
};
static void module_census(Output& out, const fs::path& executable, const fs::path& runtime) { ModuleCensus census(out); census.collect(executable, runtime); }

template<class T> static T symbol(HMODULE m, const char* owner, const char* name) { FARPROC p = GetProcAddress(m, name); if (!p) { std::string message = std::string("required_export_missing:") + owner + ":" + name; throw BridgeError(message.c_str()); } return reinterpret_cast<T>(p); }
#define LLAMA_APIS(X) X(llama_version) X(llama_model_default_params) X(llama_backend_init) X(llama_backend_free) X(llama_model_load_from_splits) X(llama_model_free) X(llama_model_get_vocab) X(llama_vocab_n_tokens) X(llama_vocab_is_eog) X(llama_tokenize) X(llama_token_to_piece) X(llama_sampler_init_grammar) X(llama_sampler_apply) X(llama_sampler_accept) X(llama_sampler_free)
#define GGML_APIS(X) X(ggml_backend_load) X(ggml_backend_reg_count) X(ggml_backend_reg_get) X(ggml_backend_dev_count) X(ggml_backend_dev_get)
#define GGML_BASE_APIS(X) X(ggml_backend_reg_name) X(ggml_backend_reg_dev_count) X(ggml_backend_reg_dev_get) X(ggml_backend_dev_name) X(ggml_backend_dev_type)
struct Api {
#define DECL(n) decltype(&::n) n = nullptr;
    LLAMA_APIS(DECL) GGML_APIS(DECL) GGML_BASE_APIS(DECL)
#undef DECL
    Api(HMODULE llama, HMODULE ggml, HMODULE base) {
#define LOADL(n) n = symbol<decltype(&::n)>(llama, "llama.dll", #n);
        LLAMA_APIS(LOADL)
#undef LOADL
#define LOADG(n) n = symbol<decltype(&::n)>(ggml, "ggml.dll", #n);
        GGML_APIS(LOADG)
#undef LOADG
#define LOADB(n) n = symbol<decltype(&::n)>(base, "ggml-base.dll", #n);
        GGML_BASE_APIS(LOADB)
#undef LOADB
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
    void close() noexcept {
        if (model) {
            if (native_state.samplers_owned || native_state.sampler_release_unknown) { native_state.cleanup_failed = true; return; }
            llama_model* releasing = model; model = nullptr; // reserve ownership once, before potentially entered free
            try { native_call(NATIVE_llama_model_free, [&]() { return api.llama_model_free(releasing); }, true); }
            catch (...) { native_state.cleanup_failed = true; native_state.model_release_unknown = true; }
        }
        if (native_state.model_release_unknown || native_state.samplers_owned || native_state.sampler_release_unknown) { native_state.cleanup_failed = true; return; }
        if (backend) {
            backend = false; // no retry if the following free was entered but did not return
            try { native_call(NATIVE_llama_backend_free, [&]() { return api.llama_backend_free(); }, true); }
            catch (...) { native_state.cleanup_failed = true; native_state.backend_release_unknown = true; }
        }
    }
    ~NativeSession() { close(); }
};
struct Sampler {
    Api& api; llama_sampler* value = nullptr;
    Sampler(Api& a, const llama_vocab* v, const Grammar& g) : api(a) {
        value = native_call(NATIVE_llama_sampler_init_grammar, [&]() { return api.llama_sampler_init_grammar(v, g.text.c_str(), "root"); });
        try { tick(); need(value != nullptr, "grammar_initialization_failed"); }
        catch (...) { std::exception_ptr primary = std::current_exception(); close(); std::rethrow_exception(primary); }
    }
    void close() noexcept {
        if (!value) return; llama_sampler* releasing = value; value = nullptr;
        try { native_call(NATIVE_llama_sampler_free, [&]() { return api.llama_sampler_free(releasing); }, true); }
        catch (...) { native_state.cleanup_failed = true; }
    }
    ~Sampler() { close(); }
    Sampler(const Sampler&) = delete; Sampler& operator=(const Sampler&) = delete;
};
static bool admitted(Api& a, Sampler& s, llama_token id) {
    llama_token_data value{id, 0.0f, 0.0f}; llama_token_data_array array{&value, 1, -1, false}; tick();  native_call(NATIVE_llama_sampler_apply, [&]() { return a.llama_sampler_apply(s.value, &array); });
    native_state.last_apply_return_observed = true; native_state.last_apply_shape_valid = array.data == &value && array.size == 1 && array.selected == -1 && !array.sorted && value.id == id && value.p == 0.0f; native_state.last_apply_logit_kind = (std::isinf(value.logit) && value.logit < 0) ? 1 : ((std::isfinite(value.logit) && value.logit == 0.0f) ? 2 : 3); tick();
    need(array.data == &value && array.size == 1 && array.selected == -1 && !array.sorted && value.id == id && value.p == 0.0f, "candidate_shape_changed");
    if (std::isinf(value.logit) && value.logit < 0) return false; need(std::isfinite(value.logit) && value.logit == 0.0f, "unexpected_candidate_logit"); return true;
}
static std::vector<llama_token> tokenize(Api& a, const llama_vocab* v, const std::string& s) {
    need(s.size() <= B, "document_byte_cap"); llama_token first{}; const char empty = '\0'; const char* p = s.empty() ? &empty : s.data();
    tick();  int32_t n = native_call(NATIVE_llama_tokenize, [&]() { return a.llama_tokenize(v, p, static_cast<int32_t>(s.size()), &first, 1, false, false); }); tick();
    need(n != (std::numeric_limits<int32_t>::min)(), "tokenize_overflow"); std::vector<llama_token> out;
    if (n >= 0) { need(n <= 1, "tokenize_success_exceeds_capacity"); if (n) out.push_back(first); }
    else { int64_t required = -static_cast<int64_t>(n); need(required > 1 && required <= K, "token_required_cap"); out.resize(static_cast<size_t>(required)); tick();  int32_t again = native_call(NATIVE_llama_tokenize, [&]() { return a.llama_tokenize(v, p, static_cast<int32_t>(s.size()), out.data(), static_cast<int32_t>(out.size()), false, false); }); tick(); need(again == required, "token_retry_size_changed"); }
    need(out.size() <= TOTALTOKENS - token_budget_used, "total_token_budget"); token_budget_used += out.size(); return out;
}
static std::string piece(Api& a, const llama_vocab* v, llama_token id) {
    char first = 0; tick();  int32_t n = native_call(NATIVE_llama_token_to_piece, [&]() { return a.llama_token_to_piece(v, id, &first, 1, 0, true); }); tick(); need(n != (std::numeric_limits<int32_t>::min)(), "piece_unexpected_int32min");
    if (n >= 0) { need(n <= 1, "piece_success_exceeds_capacity"); return std::string(&first, static_cast<size_t>(n)); }
    int64_t required = -static_cast<int64_t>(n); need(required > 1 && required <= P, "piece_required_cap"); std::string out(static_cast<size_t>(required), '\0'); tick(); 
    int32_t again = native_call(NATIVE_llama_token_to_piece, [&]() { return a.llama_token_to_piece(v, id, out.data(), static_cast<int32_t>(out.size()), 0, true); }); tick(); need(again == required, "piece_retry_size_changed"); return out;
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
    for (size_t i = 0; i < take; ++i) { need(!std::binary_search(eog.begin(), eog.end(), ids[i]), "input_EOG_forbidden_before_accept"); if (!admitted(a, s, ids[i])) { out.status = "native_token_rejection"; out.rejected = i; s.close(); need(!native_state.cleanup_failed, "sampler_cleanup_failed"); tick(); return out; } tick();  native_call(NATIVE_llama_sampler_accept, [&]() { return a.llama_sampler_accept(s.value, ids[i]); }); tick(); }
    out.all_tokens = true; out.all_eog = true; out.no_eog = true; std::ostringstream results; results << '[';
    for (size_t i = 0; i < eog.size(); ++i) { bool yes = admitted(a, s, eog[i]); if (i) results << ','; results << "{\"id\":" << eog[i] << ",\"admitted\":" << (yes ? "true" : "false") << '}'; out.all_eog = out.all_eog && yes; out.no_eog = out.no_eog && !yes; }
    results << ']'; out.eog_json = results.str(); need(out.all_eog || out.no_eog, "eog_branch_disagreement"); out.status = out.all_eog ? "native_member" : "native_eog_rejection"; s.close(); need(!native_state.cleanup_failed, "sampler_cleanup_failed"); tick(); return out;
}
static std::string observation(const Observation& o) { return "\"status\":" + q(o.status) + ",\"all_input_tokens_admitted\":" + (o.all_tokens ? "true" : "false") + ",\"first_rejected_token_index\":" + (o.rejected == (std::numeric_limits<size_t>::max)() ? std::string("null") : std::to_string(o.rejected)) + ",\"completion_EOG\":" + o.eog_json; }
static std::string rejection_span(const Observation& o, const Tokens& tokens) { if (o.rejected == (std::numeric_limits<size_t>::max)()) return ",\"first_rejected_byte_start\":null,\"first_rejected_byte_end\":null"; need(o.rejected < tokens.ends.size(), "rejected_span_bounds"); return ",\"first_rejected_byte_start\":" + std::to_string(o.rejected ? tokens.ends[o.rejected - 1] : 0) + ",\"first_rejected_byte_end\":" + std::to_string(tokens.ends[o.rejected]); }
// Input is already strict valid UTF-8. Returns scalar width only if cut is inside it.
static unsigned split_width(const std::string& s, size_t cut) { if (!cut || cut >= s.size() || (static_cast<unsigned char>(s[cut]) & 0xc0) != 0x80) return 0; size_t start = cut; while (start && (static_cast<unsigned char>(s[start]) & 0xc0) == 0x80) --start; unsigned char c = static_cast<unsigned char>(s[start]); return c < 0xe0 ? 2u : (c < 0xf0 ? 3u : 4u); }
struct CpuIdentity { ggml_backend_reg_t reg = nullptr; ggml_backend_dev_t dev = nullptr; };
static void check_cpu_identity(Api& api, const CpuIdentity& cpu) {
    tick(); need(cpu.reg && cpu.dev && native_call(NATIVE_ggml_backend_reg_count, [&]() { return api.ggml_backend_reg_count(); }) == 1 && native_call(NATIVE_ggml_backend_reg_get, [&]() { return api.ggml_backend_reg_get(0); }) == cpu.reg && native_text(native_call(NATIVE_ggml_backend_reg_name, [&]() { return api.ggml_backend_reg_name(cpu.reg); }), 128) == R09_CPU_REGISTRY_NAME, "cpu_registry_not_exact_singleton");
    need(native_call(NATIVE_ggml_backend_reg_dev_count, [&]() { return api.ggml_backend_reg_dev_count(cpu.reg); }) == 1 && native_call(NATIVE_ggml_backend_dev_count, [&]() { return api.ggml_backend_dev_count(); }) == 1 && native_call(NATIVE_ggml_backend_reg_dev_get, [&]() { return api.ggml_backend_reg_dev_get(cpu.reg, 0); }) == cpu.dev && native_call(NATIVE_ggml_backend_dev_get, [&]() { return api.ggml_backend_dev_get(0); }) == cpu.dev && native_call(NATIVE_ggml_backend_dev_type, [&]() { return api.ggml_backend_dev_type(cpu.dev); }) == GGML_BACKEND_DEVICE_TYPE_CPU && native_text(native_call(NATIVE_ggml_backend_dev_name, [&]() { return api.ggml_backend_dev_name(cpu.dev); }), 128) == R09_CPU_DEVICE_NAME, "cpu_device_identity_or_name_changed"); tick();
}
static CpuIdentity cpu_before_init(Runtime& runtime, Api& api, Output& out, const std::wstring& cpu) {
    need(cpu == L"ggml-cpu-x64.dll" && cpu == R09_CPU_BASENAME, "cpu_basename_not_bound"); need(GetEnvironmentVariableW(L"GGML_BACKEND_PATH", nullptr, 0) == 0 && GetLastError() == ERROR_ENVVAR_NOT_FOUND, "ambient_backend_path_forbidden");
    runtime.recognition = true; runtime.lease(L"ggml-cpu-x64.dll"); if (R09_LIBOMP_REQUIRED) runtime.lease(L"libomp.dll");
    std::string path = utf8((runtime.root / cpu).wstring()); tick(); auto reg = native_call(NATIVE_ggml_backend_load, [&]() { return api.ggml_backend_load(path.c_str()); }); runtime.module_phase = ModulePhase::PostCPU; tick(); need(reg != nullptr, "explicit_cpu_load_failed");
    need(native_call(NATIVE_ggml_backend_reg_dev_count, [&]() { return api.ggml_backend_reg_dev_count(reg); }) == 1, "cpu_registration_device_count"); CpuIdentity identity{reg, native_call(NATIVE_ggml_backend_reg_dev_get, [&]() { return api.ggml_backend_reg_dev_get(reg, 0); })}; check_cpu_identity(api, identity);
    HMODULE module = GetModuleHandleW(cpu.c_str()), hold = nullptr; need(module && same(module_path(module), runtime.root / cpu) && GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_PIN, (runtime.root / cpu).c_str(), &hold) && hold == module, "cpu_module_pin_failed");
    out.row("{\"event\":\"cpu_registry_verified_before_llama_backend_init\",\"registry_count\":1,\"device_count\":1,\"registry_name\":" + q(R09_CPU_REGISTRY_NAME) + ",\"device_name\":" + q(R09_CPU_DEVICE_NAME) + runtime.policy_fields() + ",\"modules\":" + runtime.modules(out) + "}");
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
    CpuIdentity cpu_identity = cpu_before_init(runtime, api, out, cpu); NativeSession session(api); tick(); native_call(NATIVE_llama_backend_init, [&]() { return api.llama_backend_init(); }); session.backend = true; tick();
    check_cpu_identity(api, cpu_identity); out.row("{\"event\":\"backend_init_returned_exact_CPU_identity_rechecked\"" + runtime.policy_fields() + ",\"modules\":" + runtime.modules(out) + "}");
    params.devices = session.empty_devices; params.tensor_buft_overrides = nullptr; params.n_gpu_layers = 0; params.split_mode = LLAMA_SPLIT_MODE_NONE; params.load_mode = LLAMA_LOAD_MODE_NONE; params.lazy_mode = LLAMA_LAZY_MODE_OFF; params.main_gpu = -1; params.tensor_split = nullptr; params.progress_callback = nullptr; params.progress_callback_user_data = nullptr; params.kv_overrides = nullptr; params.vocab_only = true; params.check_tensors = false; params.use_extra_bufts = false; params.no_host = false; params.no_alloc = true; params.load_mtp = false;
    out.row("{\"event\":\"before_model_load_from_three_explicit_splits\",\"effective_params\":" + defaults(params) + ",\"empty_devices_array_nonnull\":true,\"cooperative_deadline_not_interruptible_native_call\":true}");
    tick(); session.model = native_call(NATIVE_llama_model_load_from_splits, [&]() { return api.llama_model_load_from_splits(shard_ptrs.data(), shard_ptrs.size(), params); }); tick(); need(session.model, "vocabulary_only_model_load_failed"); const llama_vocab* vocab = native_call(NATIVE_llama_model_get_vocab, [&]() { return api.llama_model_get_vocab(session.model); }); need(vocab, "null_borrowed_vocabulary"); int32_t nv = native_call(NATIVE_llama_vocab_n_tokens, [&]() { return api.llama_vocab_n_tokens(vocab); }); need(nv > 0 && nv <= static_cast<int32_t>(VMAX), "vocabulary_count_cap");
    std::vector<llama_token> eog; for (int32_t id = 0; id < nv; ++id) { native_state.last_EOG_id = id; native_state.last_EOG_returned = false; bool yes = native_call(NATIVE_llama_vocab_is_eog, [&]() { return api.llama_vocab_is_eog(vocab, id); }); native_state.last_EOG_returned = true; native_state.last_EOG_value = yes; ++native_state.EOG_ids_examined; tick(); if (yes) { need(eog.size() < EMAX, "EOG_count_cap"); eog.push_back(id); } } need(!eog.empty(), "empty_EOG_set");
    std::ostringstream e; e << '['; for (size_t i = 0; i < eog.size(); ++i) { if (i) e << ','; e << eog[i]; } e << ']';
    out.row("{\"event\":\"all_vocabulary_ids_EOG_enumerated\",\"vocabulary_count\":" + std::to_string(nv) + ",\"EOG_ids\":" + e.str() + ",\"EOG_JSON_sha256\":" + q(digest(e.str())) + runtime.policy_fields() + ",\"modules\":" + runtime.modules(out) + "}");
    size_t completed = 0, prefix_done = 0; std::array<size_t, 3> completed_groups{}, native_results{}, harness_dispositions{}; bool unavailable = false;
    for (size_t index = 0; index < pack.cases.size(); ++index) { const auto& c = pack.cases[index]; native_state.current_case_index = static_cast<int64_t>(index); tick(); out.row("{\"event\":\"before_case\",\"case_index\":" + std::to_string(index) + ",\"id\":" + q(c.id) + ",\"document_sha256\":" + q(c.sha) + "}");
        Tokens tokens = prepare(api, vocab, nv, eog, c.bytes); bool match = false; std::string fields;
        if (!tokens.harness.empty()) { ++harness_dispositions[c.group]; match = (c.expected == 2 && tokens.harness == "harness_utf8_rejection") || (c.expected == 3 && tokens.harness == "harness_raw_nul_rejection"); fields = "\"status\":" + q(tokens.harness) + ",\"native_membership\":null,\"completion_EOG\":null"; }
        else { ++native_results[c.group]; Observation o = observe(api, vocab, pack.grammars[c.grammar], tokens.ids, tokens.ids.size(), eog); match = (c.expected == 1 && o.status == "native_member") || (c.expected == 0 && (o.status == "native_token_rejection" || o.status == "native_eog_rejection")); fields = observation(o) + rejection_span(o, tokens); }
        ++completed; ++completed_groups[c.group]; ++native_state.cases_computed; ++native_state.group_computed[c.group];
        out.row("{\"event\":\"case_result\",\"case_index\":" + std::to_string(index) + ",\"source_group\":" + std::to_string(c.group) + ",\"id\":" + q(c.id) + ",\"bytes\":" + std::to_string(c.bytes.size()) + ",\"document_sha256\":" + q(c.sha) + ",\"tokens\":" + std::to_string(tokens.ids.size()) + ",\"used_piece_NUL_seen\":" + (tokens.nul_piece == (std::numeric_limits<size_t>::max)() ? "false" : "true") + ",\"first_NUL_piece_index\":" + (tokens.nul_piece == (std::numeric_limits<size_t>::max)() ? std::string("null") : std::to_string(tokens.nul_piece)) + ",\"first_NUL_offset_in_piece\":" + (tokens.nul_offset == (std::numeric_limits<size_t>::max)() ? std::string("null") : std::to_string(tokens.nul_offset)) + ",\"expected_kind\":" + std::to_string(c.expected) + ",\"expected_native_membership\":" + (c.expected <= 1 ? (c.expected == 1 ? "true" : "false") : "null") + ",\"matches_expected\":" + (match ? "true" : "false") + "," + fields + "}"); ++native_state.case_results_written; ++native_state.group_results_written[c.group]; need(match, "case_expectation_mismatch_stop");
        for (const auto& p : pack.prefixes) if (p.doc == index) { ++prefix_done; ++native_state.prefix_slots_seen; native_state.current_prefix_slot = static_cast<int64_t>(prefix_done - 1); need(tokens.harness.empty(), "prefix_base_ineligible"); size_t count = 0, cut = p.cut; Tokens fresh; const Tokens* source = &tokens;
            if (p.kind == 0) { fresh = prepare(api, vocab, nv, eog, c.bytes.substr(0, cut)); need(fresh.harness.empty(), "byte_prefix_harness_failure"); count = fresh.ids.size(); source = &fresh; }
            else { bool found = false; for (size_t j = 0; j < tokens.ends.size(); ++j) { unsigned width = split_width(c.bytes, tokens.ends[j]); if ((p.kind == 1 && (width == 2 || width == 3)) || (p.kind == 2 && width == 4)) { count = j + 1; cut = tokens.ends[j]; found = true; break; } }
                if (!found) { unavailable = true; native_state.required_UTF8_prefix_unavailable = true; out.row("{\"event\":\"prefix_result\",\"id\":" + q(p.id) + ",\"status\":\"coverage_unavailable\",\"matches_expected\":null}"); ++native_state.prefix_results_written; continue; } }
            if (p.kind != 0) { need(count <= TOTALTOKENS - token_budget_used, "total_prefix_token_budget"); token_budget_used += count; }
            Observation o = observe(api, vocab, pack.grammars[c.grammar], source->ids, count, eog); bool pass = o.all_tokens && o.no_eog;
            bool complete_before_partial = count && source->complete_before_partial[count - 1];
            out.row("{\"event\":\"prefix_result\",\"id\":" + q(p.id) + ",\"base_id\":" + q(c.id) + ",\"prefix_kind\":" + std::to_string(p.kind) + ",\"byte_cut\":" + std::to_string(cut) + ",\"token_count\":" + std::to_string(count) + ",\"prefix_sha256\":" + q(digest(c.bytes.substr(0, cut))) + ",\"partial_UTF8_at_cut\":" + (split_width(c.bytes, cut) ? "true" : "false") + ",\"last_piece_complete_codepoints_before_partial\":" + (complete_before_partial ? "true" : "false") + ",\"matches_expected\":" + (pass ? "true" : "false") + "," + observation(o) + rejection_span(o, *source) + "}"); ++native_state.prefix_results_written; need(pass, "prefix_expectation_mismatch_stop");
        }
    }
    need(completed == pack.cases.size() && prefix_done == pack.prefixes.size(), "case_or_prefix_accounting"); need(!unavailable, "required_partial_UTF8_prefix_coverage_unavailable");
    need(pack.cases.size() == 189 && pack.grammars.size() == 4 && pack.prefixes.size() == 6 && native_state.cases_computed == 189 && native_state.case_results_written == 189 && native_state.prefix_slots_seen == 6 && native_state.prefix_results_written == 6, "frozen_pack_progress_incomplete");
    // Explicit cleanup is reported before final publication; destructors remain fallback.
    session.close(); need(!native_state.cleanup_failed && native_state.model_free_return_observed && native_state.backend_free_return_observed && !native_state.model_release_unknown && !native_state.backend_release_unknown && native_state.samplers_owned == 0 && native_state.sampler_release_unknown == 0, "recognition_cleanup_incomplete"); tick();
    for (size_t k = 0; k < static_cast<size_t>(NATIVE_COUNT); ++k) need(native_state.attempted[k] == native_state.returned[k], "native_call_return_incomplete");
    need(native_state.returned[NATIVE_llama_sampler_init_grammar] == 190 && native_state.returned[NATIVE_llama_sampler_free] == 190 && native_state.EOG_ids_examined == static_cast<uint64_t>(nv) && native_state.exceptions == 0, "whole_pack_native_accounting_incomplete");
    out.row("{\"event\":\"recognition_batch_returned\",\"pack_format_version\":2,\"cases_completed\":" + std::to_string(completed) + ",\"source_group_completed\":{\"primary_frozen_wire\":" + std::to_string(completed_groups[0]) + ",\"new_serialization_of_retained_authored_abstention\":" + std::to_string(completed_groups[1]) + ",\"harness_byte_guards\":" + std::to_string(completed_groups[2]) + "},\"primary_native_results\":" + std::to_string(native_results[0]) + ",\"primary_harness_dispositions\":" + std::to_string(harness_dispositions[0]) + ",\"new_authored_native_results\":" + std::to_string(native_results[1]) + ",\"independent_guard_dispositions\":" + std::to_string(harness_dispositions[2]) + ",\"prefix_slots\":" + std::to_string(prefix_done) + ",\"total_token_budget_used\":" + std::to_string(token_budget_used) + ",\"tokenize_calls\":" + std::to_string(tokenize_calls) + ",\"piece_calls\":" + std::to_string(piece_calls) + ",\"apply_calls\":" + std::to_string(apply_calls) + ",\"accept_calls\":" + std::to_string(accept_calls) + ",\"EOG_accept_calls\":0,\"samplers_freed_before_model\":true,\"model_freed\":true,\"backend_free_returned\":true" + runtime.policy_fields() + ",\"modules\":" + runtime.modules(out) + ",\"scientific_validation\":\"not_established\"}");
}

int wmain(int argc, wchar_t** argv) {
    std::unique_ptr<Output> out;
    try {
        need(argc >= 2, "expected_mode"); std::string mode = utf8(argv[1]); need((mode == "--abi" && argc == 4) || (mode == "--module-census" && argc == 4) || (mode == "--recognize" && argc == 9), "expected_abi_runtime_output_or_recognize_runtime_output_pack_cpu_three_shards");
        fs::path root = absolute(argv[2]), output = absolute(argv[3]); out = std::make_unique<Output>(output, mode); tick(); Runtime runtime(root, absolute(argv[0]), mode == "--recognize");
        // No backend registry/device API is called in --abi mode.
        // The pinned base DLL imports OpenMP: preload its exact leased bytes first.
        // Dependency DLL initialization may run even in ABI-only mode.
        if (R09_LIBOMP_REQUIRED) { out->row("{\"event\":\"before_explicit_required_OpenMP_dependency_load\",\"dependency_native_initialization_possible\":true}"); runtime.load_core(L"libomp.dll"); }
        HMODULE base = runtime.load_core(L"ggml-base.dll"); HMODULE ggml = runtime.load_core(L"ggml.dll"); HMODULE llama = runtime.load_core(L"llama.dll");
        if (mode == "--module-census") { module_census(*out, absolute(argv[0]), root); out->commit(); std::cout << "{\"status\":\"module_census_child_returned_metadata_requires_review\"}\n"; return 0; }
        Api api(llama, ggml, base); out->row("{\"event\":\"exact_core_modules_loaded_exports_resolved\",\"module_policy_id\":" + q(runtime.policy_id()) + ",\"module_policy_sha256\":" + q(runtime.policy_sha()) + ",\"module_policy_phase\":" + q(runtime.phase_name()) + ",\"modules\":" + runtime.modules(*out) + ",\"layouts\":" + layouts() + "}");
        tick(); std::string version = native_text(native_call(NATIVE_llama_version, [&]() { return api.llama_version(); }), 256); tick(); need(!version.empty(), "empty_version_observation"); for (unsigned char c : version) need(c >= 32 && c <= 126, "version_observation_not_printable_ASCII");
        bool version_pinned = R09_EXPECTED_LLAMA_VERSION[0] != '\0';
        if (version_pinned) need(version == R09_EXPECTED_LLAMA_VERSION, "version_string_not_parent_bound");
        else need(mode == "--abi", "recognition_requires_version_pinned_from_reviewed_ABI_report");
        tick(); llama_model_params params = native_call(NATIVE_llama_model_default_params, [&]() { return api.llama_model_default_params(); }); tick(); out->row("{\"event\":\"typed_version_and_defaults_observed\",\"version\":" + q(version) + ",\"defaults\":" + defaults(params) + ",\"no_backend_or_model_call_so_far\":true}"); check_defaults(params);
        if (mode == "--abi") out->row("{\"event\":\"abi_observations_returned\",\"version_expected_previously_known\":" + std::string(version_pinned ? "true" : "false") + ",\"backend_init_called\":false,\"registry_called\":false,\"model_called\":false,\"scope\":\"typed version/defaults observation; independent ABI acceptance pending\"}");
        else { std::array<fs::path, 3> shards{absolute(argv[6]), absolute(argv[7]), absolute(argv[8])}; recognize(runtime, api, *out, absolute(argv[4]), argv[5], shards, params); }
        tick(); out->row("{\"event\":\"child_normal_completion\",\"mode\":" + q(mode) + ",\"elapsed_ms\":" + std::to_string(GetTickCount64() - START_MS) + ",\"parent_qualification_required\":true}"); out->commit(); std::cout << "{\"status\":\"child_returned_results_require_parent_review\"}\n"; return 0;
    } catch (const BridgeError& error) { std::string msg(error.what()); if (out) out->failure(msg, error.diagnostic_fields); std::cout << "{\"status\":\"failed\",\"message\":" << q(msg) << error.diagnostic_fields << "}\n"; return 2; }
      catch (const std::exception&) { if (out) out->failure("nonprotocol_cpp_exception_no_document_text_copied"); std::cout << "{\"status\":\"failed_nonprotocol_cpp_exception\"}\n"; return 3; }
      catch (...) { if (out) out->failure("unknown_cpp_exception"); std::cout << "{\"status\":\"failed_unknown_cpp_exception\"}\n"; return 4; }
}
