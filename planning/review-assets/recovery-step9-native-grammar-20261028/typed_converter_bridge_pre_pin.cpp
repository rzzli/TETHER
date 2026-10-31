// Author-written consumer only. Never compile the fetched implementation files.
// Execution is forbidden until the root's separate finite execution protocol.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define _WIN32_WINNT 0x0602
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <algorithm>
#include <cctype>
#include <cwctype>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "json-schema-to-grammar.h"
#include "approved_runtime.hpp"

namespace fs = std::filesystem;
static_assert(sizeof(void*) == 8, "An x64 build is required");
static_assert(_ITERATOR_DEBUG_LEVEL == 0, "Release iterator ABI is required");
constexpr size_t MAX_INPUT_BYTES = 2 * 1024 * 1024;
constexpr size_t MAX_OUTPUT_BYTES = 4 * 1024 * 1024;
constexpr size_t MAX_NATIVE_DLL_BYTES = 128 * 1024 * 1024;

struct Handle {
    HANDLE value = INVALID_HANDLE_VALUE;
    explicit Handle(HANDLE v) : value(v) {}
    ~Handle() { if (value != INVALID_HANDLE_VALUE && value != nullptr) CloseHandle(value); }
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
};

static void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}

static std::wstring lower(std::wstring text) {
    std::transform(text.begin(), text.end(), text.begin(), [](wchar_t c) { return static_cast<wchar_t>(towlower(c)); });
    return text;
}

static bool same_path(const fs::path& a, const fs::path& b) {
    return lower(a.lexically_normal().wstring()) == lower(b.lexically_normal().wstring());
}

static fs::path local_absolute(const wchar_t* value) {
    std::wstring text(value);
    require(text.size() >= 3 && text[1] == L':' && (text[2] == L'\\' || text[2] == L'/'), "Expected an absolute local drive path");
    require(text.find(L'\n') == std::wstring::npos && text.find(L'\r') == std::wstring::npos, "Invalid path controls");
    std::vector<wchar_t> buffer(32768);
    DWORD count = GetFullPathNameW(text.c_str(), static_cast<DWORD>(buffer.size()), buffer.data(), nullptr);
    require(count > 0 && count < buffer.size(), "Cannot normalize local path");
    fs::path path(std::wstring(buffer.data(), count));
    require(GetDriveTypeW(path.root_path().c_str()) == DRIVE_FIXED, "Expected a fixed local drive");
    return path.lexically_normal();
}

static void no_reparse(const fs::path& path, bool leaf_must_exist) {
    bool first = true;
    for (fs::path part = path; !part.empty();) {
        DWORD attrs = GetFileAttributesW(part.c_str());
        if (attrs == INVALID_FILE_ATTRIBUTES) {
            require(first && !leaf_must_exist && GetLastError() == ERROR_FILE_NOT_FOUND, "Missing or unreadable path ancestor");
        } else {
            require((attrs & FILE_ATTRIBUTE_REPARSE_POINT) == 0, "Reparse points are unsupported");
        }
        fs::path parent = part.parent_path();
        if (parent == part) break;
        part = parent;
        first = false;
    }
}

static std::string utf8(const std::wstring& value) {
    if (value.empty()) return {};
    require(value.size() <= 32768, "Wide string exceeds bound");
    int size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    require(size > 0, "Cannot encode path as UTF-8");
    std::string result(static_cast<size_t>(size), '\0');
    require(WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), result.data(), size, nullptr, nullptr) == size, "UTF-8 path conversion differs");
    return result;
}

static bool valid_utf8(const std::string& value) {
    return value.empty() || (value.size() <= MAX_OUTPUT_BYTES && MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0) > 0);
}

static std::string escaped(const std::string& value) {
    std::ostringstream out;
    out << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') out << '\\' << static_cast<char>(c);
        else if (c < 0x20) out << "\\u00" << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(c) << std::dec;
        else out << static_cast<char>(c);
    }
    out << '"';
    return out.str();
}

static std::string sha256(const std::string& bytes) {
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    try {
        require(BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) >= 0, "Cannot open SHA256 provider");
        DWORD object_bytes = 0, returned = 0;
        require(BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, reinterpret_cast<PUCHAR>(&object_bytes), sizeof(object_bytes), &returned, 0) >= 0 && returned == sizeof(object_bytes), "Cannot size SHA256 state");
        std::vector<UCHAR> state(object_bytes), digest(32);
        require(BCryptCreateHash(algorithm, &hash, state.data(), object_bytes, nullptr, 0, 0) >= 0, "Cannot create SHA256 state");
        require(bytes.size() <= MAX_NATIVE_DLL_BYTES, "Hash input exceeds bound");
        require(BCryptHashData(hash, reinterpret_cast<PUCHAR>(const_cast<char*>(bytes.data())), static_cast<ULONG>(bytes.size()), 0) >= 0, "Cannot hash bytes");
        require(BCryptFinishHash(hash, digest.data(), static_cast<ULONG>(digest.size()), 0) >= 0, "Cannot finish SHA256");
        BCryptDestroyHash(hash); hash = nullptr;
        BCryptCloseAlgorithmProvider(algorithm, 0); algorithm = nullptr;
        std::ostringstream out;
        for (UCHAR c : digest) out << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(c);
        return out.str();
    } catch (...) {
        if (hash) BCryptDestroyHash(hash);
        if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
        throw;
    }
}

static std::string read_bounded(const fs::path& path, size_t maximum) {
    no_reparse(path, true);
    Handle file(CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr));
    require(file.value != INVALID_HANDLE_VALUE, "Cannot read input file");
    LARGE_INTEGER length{};
    require(GetFileSizeEx(file.value, &length) && length.QuadPart >= 0 && static_cast<unsigned long long>(length.QuadPart) <= maximum, "Input file exceeds bound");
    std::string result(static_cast<size_t>(length.QuadPart), '\0');
    size_t offset = 0;
    while (offset < result.size()) {
        DWORD got = 0;
        DWORD request = static_cast<DWORD>((std::min)(result.size() - offset, static_cast<size_t>(65536)));
        require(ReadFile(file.value, result.data() + offset, request, &got, nullptr) && got > 0, "Input read failed");
        offset += got;
    }
    return result;
}

static void write_new(const fs::path& path, const std::string& bytes) {
    no_reparse(path, false);
    Handle file(CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr));
    require(file.value != INVALID_HANDLE_VALUE, "Output already exists or cannot be created");
    size_t offset = 0;
    while (offset < bytes.size()) {
        DWORD wrote = 0;
        DWORD request = static_cast<DWORD>((std::min)(bytes.size() - offset, static_cast<size_t>(65536)));
        require(WriteFile(file.value, bytes.data() + offset, request, &wrote, nullptr) && wrote > 0, "Output write failed");
        offset += wrote;
    }
    require(FlushFileBuffers(file.value) != FALSE, "Output flush failed");
}

static fs::path module_path(HMODULE module) {
    std::vector<wchar_t> buffer(32768);
    DWORD count = GetModuleFileNameW(module, buffer.data(), static_cast<DWORD>(buffer.size()));
    require(count > 0 && count < buffer.size(), "Cannot resolve loaded module path");
    return local_absolute(std::wstring(buffer.data(), count).c_str());
}

static const ModulePin* pin_for(const std::wstring& name) {
    for (const auto& pin : APPROVED_RUNTIME_DLLS) if (lower(name) == lower(pin.name)) return &pin;
    return nullptr;
}

static std::string native_modules(const fs::path& root) {
    Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, GetCurrentProcessId()));
    require(snapshot.value != INVALID_HANDLE_VALUE, "Cannot snapshot loaded modules");
    MODULEENTRY32W entry{}; entry.dwSize = sizeof(entry);
    require(Module32FirstW(snapshot.value, &entry), "Cannot enumerate loaded modules");
    std::ostringstream out; out << '[';
    bool comma = false, common_seen = false;
    do {
        fs::path path = module_path(entry.hModule);
        std::wstring name = path.filename().wstring();
        const ModulePin* pin = pin_for(name);
        bool inside = same_path(path.parent_path(), root);
        bool native_name = lower(name).rfind(L"llama", 0) == 0 || lower(name).rfind(L"ggml", 0) == 0 || lower(name) == L"mtmd.dll" || lower(name) == L"libomp.dll";
        if (inside || pin || native_name) {
            require(pin != nullptr && inside && same_path(path, root / pin->name), "Native module loaded from an unapproved path");
            std::string bytes = read_bounded(path, MAX_NATIVE_DLL_BYTES);
            std::string digest = sha256(bytes);
            require(bytes.size() == pin->bytes && digest == pin->sha256, "Native module bytes differ");
            if (lower(name) == L"llama-common.dll") common_seen = true;
            if (comma) out << ',';
            comma = true;
            out << "{\"name\":" << escaped(utf8(name)) << ",\"path\":" << escaped(utf8(path.wstring()))
                << ",\"sha256\":" << escaped(digest) << ",\"bytes\":" << bytes.size() << '}';
        }
        entry.dwSize = sizeof(entry);
    } while (Module32NextW(snapshot.value, &entry));
    require(GetLastError() == ERROR_NO_MORE_FILES && common_seen, "Loaded module enumeration incomplete");
    out << ']';
    return out.str();
}

struct LoadedCommon {
    DLL_DIRECTORY_COOKIE cookie = nullptr;
    HMODULE module = nullptr;
    explicit LoadedCommon(const fs::path& root) {
        try {
        require(GetModuleHandleW(L"llama-common.dll") == nullptr, "Common DLL was already loaded before approval");
        require(SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32 | LOAD_LIBRARY_SEARCH_USER_DIRS), "Cannot restrict DLL search");
        cookie = AddDllDirectory(root.c_str());
        require(cookie != nullptr, "Cannot add approved native directory");
        const ModulePin* pin = pin_for(L"llama-common.dll");
        require(pin != nullptr, "Common DLL proof missing");
        fs::path path = root / pin->name;
        std::string bytes = read_bounded(path, MAX_NATIVE_DLL_BYTES);
        require(bytes.size() == pin->bytes && sha256(bytes) == pin->sha256, "Common DLL bytes differ before load");
        module = LoadLibraryExW(path.c_str(), nullptr, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
        require(module != nullptr && same_path(module_path(module), path), "Cannot load exact approved common DLL");
        } catch (...) {
            if (module) { FreeLibrary(module); module = nullptr; }
            if (cookie) { RemoveDllDirectory(cookie); cookie = nullptr; }
            throw;
        }
    }
    ~LoadedCommon() {
        if (module) FreeLibrary(module);
        if (cookie) RemoveDllDirectory(cookie);
    }
    LoadedCommon(const LoadedCommon&) = delete;
    LoadedCommon& operator=(const LoadedCommon&) = delete;
};

int wmain(int argc, wchar_t** argv) {
    std::string mode, input_hash;
    try {
        require(argc == 5, "Expected mode, native directory, input JSON and new report JSON");
        mode = utf8(argv[1]);
        require(mode == "roundtrip" || mode == "convert", "Unknown fixed bridge mode");
        fs::path root = local_absolute(argv[2]);
        fs::path input = local_absolute(argv[3]);
        fs::path report = local_absolute(argv[4]);
        require(lower(input.extension().wstring()) == L".json" && lower(report.extension().wstring()) == L".json", "Expected JSON input/report filenames");
        no_reparse(root, true); no_reparse(report.parent_path(), true);
        fs::path output = report.parent_path() / (report.stem().wstring() + L".output.bin");
        fs::path attempt = report.parent_path() / (report.stem().wstring() + L".attempt.json");
        std::string text = read_bounded(input, MAX_INPUT_BYTES);
        require(!text.empty() && valid_utf8(text), "Input must be nonempty bounded UTF-8 JSON");
        input_hash = sha256(text);
        std::ostringstream initial;
        initial << "{\"schema_version\":1,\"status\":\"before_native_load\",\"mode\":" << escaped(mode)
                << ",\"input_sha256\":" << escaped(input_hash) << ",\"input_bytes\":" << text.size()
                << ",\"native_root\":" << escaped(utf8(root.wstring())) << ",\"force_gbnf\":false}\n";
        write_new(attempt, initial.str());
        LoadedCommon loaded(root);
        std::string before = native_modules(root);
        std::string returned;
        {
            // Ordinary typed prvalue and automatic destructor. No opaque storage access.
            common_json document = common_json::parse(text);
            if (mode == "roundtrip") returned = document.dump(-1);
            else returned = json_schema_to_grammar(document, false);
        }
        require(!returned.empty() && returned.size() <= MAX_OUTPUT_BYTES, "Native return is empty or exceeds bound");
        std::string output_hash = sha256(returned);
        write_new(output, returned); // Preserve original bytes even if later backend checks fail.
        require(valid_utf8(returned) && returned.find('\0') == std::string::npos, "Native return is not bounded UTF-8 text");
        if (mode == "convert") {
            require(returned.rfind("%", 0) != 0, "Unexpected grammar backend marker; no fallback allowed");
            require(returned.rfind("root ::=", 0) == 0 || returned.find("\nroot ::=") != std::string::npos, "Unrecognized nonempty grammar format");
        }
        std::string after = native_modules(root);
        std::ostringstream result;
        result << "{\"schema_version\":1,\"status\":\"native_call_returned\",\"mode\":" << escaped(mode)
               << ",\"input_sha256\":" << escaped(input_hash) << ",\"input_bytes\":" << text.size()
               << ",\"output_sha256\":" << escaped(output_hash) << ",\"output_bytes\":" << returned.size()
               << ",\"output_path\":" << escaped(utf8(output.wstring())) << ",\"force_gbnf\":false"
               << ",\"normal_cpp_lifetime_completed\":true,\"native_modules_before\":" << before
               << ",\"native_modules_after\":" << after
               << ",\"stderr_policy\":\"Any stderr diagnostics fail external qualification\""
               << ",\"abi_qualification\":\"caller_must_validate_roundtrip\",\"grammar_conformance\":\"not_established\"}\n";
        write_new(report, result.str());
        std::cout << result.str();
        return 0;
    } catch (const std::exception& error) {
        std::string message(error.what());
        if (message.size() > 4096 || !valid_utf8(message)) message = "Native/bridge exception message exceeds safe text bounds";
        std::cout << "{\"schema_version\":1,\"status\":\"failed\",\"mode\":" << escaped(mode)
                  << ",\"input_sha256\":" << escaped(input_hash) << ",\"message\":" << escaped(message) << "}\n";
        std::cerr << "Typed converter bridge failed; see structured stdout and preserved native diagnostics.\n";
        return 2;
    } catch (...) {
        std::cout << "{\"schema_version\":1,\"status\":\"failed_unknown_cpp_exception\"}\n";
        std::cerr << "Typed converter bridge failed with an unknown C++ exception.\n";
        return 3;
    }
}
