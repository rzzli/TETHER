// AUTHOR-WRITTEN SOURCE PREPARATION ONLY. No compilation or execution authorized.
// Prospective /MD x64 harmless launcher fixture, matching the existing ABI build.
// No target API/model/network. Eventual CRT/system imports require pinned review.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <cstdint>
#include <string>
#include <vector>

static constexpr wchar_t CACHE[] = L"D:\\Projects\\drug_target_agents\\data\\cache";
static constexpr DWORD MARKER_CAP = 4096;
static constexpr DWORD PROTOCOL_CAP = 1024 * 1024;
static constexpr SIZE_T SMALL_BYTES = 64 * 1024;
static constexpr SIZE_T LARGE_BYTES = 384 * 1024 * 1024;

struct Failure { const char* code; DWORD error; };
static void need(bool ok, const char* code, DWORD error = 0) {
    if (!ok) throw Failure{code, error};
}
static void win_need(bool ok, const char* code) {
    if (!ok) throw Failure{code, GetLastError()};
}

struct Handle {
    HANDLE value = INVALID_HANDLE_VALUE;
    explicit Handle(HANDLE h = INVALID_HANDLE_VALUE) : value(h) {}
    ~Handle() { if (value != INVALID_HANDLE_VALUE && value != nullptr) CloseHandle(value); }
    void close(const char* code) {
        HANDLE old = value; value = INVALID_HANDLE_VALUE;
        win_need(CloseHandle(old) != FALSE, code);
    }
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
};

static bool same(const std::wstring& a, const std::wstring& b) {
    return CompareStringOrdinal(a.c_str(), -1, b.c_str(), -1, TRUE) == CSTR_EQUAL;
}

static std::wstring full(const std::wstring& supplied) {
    need(!supplied.empty() && supplied.size() < 32767, "path_length");
    need(supplied.find_first_of(L"/\"*?<>|") == std::wstring::npos
         && supplied.size() > 3 && supplied[1] == L':' && supplied[2] == L'\\'
         && supplied.find(L':', 2) == std::wstring::npos, "path_form");
    wchar_t buffer[32768];
    DWORD n = GetFullPathNameW(supplied.c_str(), 32768, buffer, nullptr);
    need(n > 0 && n < 32768, "path_normalization", GetLastError());
    std::wstring value(buffer, n), prefix = std::wstring(CACHE) + L"\\";
    need(same(value, supplied) && value.size() > prefix.size()
         && same(value.substr(0, prefix.size()), prefix), "path_outside_exact_cache");
    // Existing paths only. Inspect every ancestor from the volume root, without
    // following a reparse point. Parent-held leases remain the dispatch authority.
    for (size_t i = 3; i <= value.size(); ++i) {
        if (i != 3 && i < value.size() && value[i] != L'\\') continue;
        DWORD attributes = GetFileAttributesW(value.substr(0, i).c_str());
        need(attributes != INVALID_FILE_ATTRIBUTES, "path_attributes", GetLastError());
        need(!(attributes & FILE_ATTRIBUTE_REPARSE_POINT), "path_reparse");
        if (i < value.size()) need(attributes & FILE_ATTRIBUTE_DIRECTORY, "path_ancestor_not_directory");
    }
    return value;
}

static std::string utf8(const std::wstring& value) {
    need(value.size() <= 32767, "utf8_input_cap");
    int n = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(),
        static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    need(n > 0 && n <= 131068, "utf8_conversion", GetLastError());
    std::string result(static_cast<size_t>(n), '\0');
    int converted = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(),
        static_cast<int>(value.size()), result.data(), n, nullptr, nullptr);
    need(converted == n, "utf8_conversion_changed", GetLastError());
    return result;
}

static std::string quote(const std::string& value) {
    std::string result = "\"";
    for (unsigned char c : value) {
        need(c >= 32, "json_control_character");
        if (c == '\\' || c == '"') result += '\\';
        result += static_cast<char>(c);
    }
    return result + "\"";
}

static void write_all(HANDLE handle, const char* bytes, DWORD count) {
    for (DWORD done = 0; done < count;) {
        DWORD written = 0;
        win_need(WriteFile(handle, bytes + done, count - done, &written, nullptr) != FALSE,
                 "write_file");
        need(written > 0 && written <= count - done, "write_progress");
        done += written;
    }
}

static void publish(const std::wstring& directory, const wchar_t* name, const std::string& json) {
    need(!json.empty() && json.size() + 1 <= MARKER_CAP, "marker_cap");
    std::wstring destination = directory + L"\\" + name, pending = destination + L".pending";
    {
        Handle file(CreateFileW(pending.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW,
                                 FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        need(file.value != INVALID_HANDLE_VALUE, "marker_create", GetLastError());
        write_all(file.value, json.data(), static_cast<DWORD>(json.size()));
        write_all(file.value, "\n", 1);
        win_need(FlushFileBuffers(file.value) != FALSE, "marker_flush");
        file.close("marker_close");
    }
    // No replace-existing flag. A failed/partial publication remains visible as
    // a pending file for the parent and is never silently retried or removed.
    win_need(MoveFileExW(pending.c_str(), destination.c_str(), 0) != FALSE,
             "marker_nonoverwriting_publish");
}

static std::string hex(const unsigned char* value, size_t count) {
    static constexpr char digits[] = "0123456789abcdef";
    std::string result; result.reserve(count * 2);
    for (size_t i = 0; i < count; ++i) {
        result += digits[value[i] >> 4]; result += digits[value[i] & 15];
    }
    return result;
}

static std::string protocol_hash(const std::wstring& path) {
    Handle file(CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
        OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
    need(file.value != INVALID_HANDLE_VALUE, "protocol_open", GetLastError());
    FILE_ATTRIBUTE_TAG_INFO tag{};
    win_need(GetFileInformationByHandleEx(file.value, FileAttributeTagInfo, &tag, sizeof(tag)) != FALSE,
             "protocol_attributes");
    need(!(tag.FileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY)), "protocol_not_regular");
    LARGE_INTEGER size{};
    win_need(GetFileSizeEx(file.value, &size) != FALSE, "protocol_size_query");
    need(size.QuadPart > 0 && size.QuadPart <= PROTOCOL_CAP, "protocol_size");
    std::vector<unsigned char> bytes(static_cast<size_t>(size.QuadPart));
    DWORD got = 0;
    win_need(ReadFile(file.value, bytes.data(), static_cast<DWORD>(bytes.size()), &got, nullptr) != FALSE,
             "protocol_read");
    need(got == bytes.size(), "protocol_read_length");
    unsigned char extra = 0; DWORD trailing = 0;
    win_need(ReadFile(file.value, &extra, 1, &trailing, nullptr) != FALSE, "protocol_trailing_read");
    need(trailing == 0, "protocol_changed_size");
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    NTSTATUS status = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0);
    need(status >= 0, "sha256_provider", static_cast<DWORD>(status));
    try {
        DWORD object_bytes = 0, returned = 0;
        status = BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH,
            reinterpret_cast<PUCHAR>(&object_bytes), sizeof(object_bytes), &returned, 0);
        need(status >= 0 && returned == sizeof(object_bytes) && object_bytes <= 1024 * 1024,
             "sha256_object_length", static_cast<DWORD>(status));
        std::vector<unsigned char> object(object_bytes);
        status = BCryptCreateHash(algorithm, &hash, object.data(), object_bytes, nullptr, 0, 0);
        need(status >= 0, "sha256_create", static_cast<DWORD>(status));
        status = BCryptHashData(hash, bytes.data(), static_cast<ULONG>(bytes.size()), 0);
        need(status >= 0, "sha256_input", static_cast<DWORD>(status));
        unsigned char digest[32]{};
        status = BCryptFinishHash(hash, digest, sizeof(digest), 0);
        need(status >= 0, "sha256_finish", static_cast<DWORD>(status));
        status = BCryptDestroyHash(hash); hash = nullptr;
        need(status >= 0, "sha256_destroy", static_cast<DWORD>(status));
        status = BCryptCloseAlgorithmProvider(algorithm, 0); algorithm = nullptr;
        need(status >= 0, "sha256_close", static_cast<DWORD>(status));
        return hex(digest, sizeof(digest));
    } catch (...) {
        if (hash) BCryptDestroyHash(hash);
        if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
        throw;
    }
}

static std::string resource_result(const std::wstring& executable, const std::wstring& output) {
    void* control = VirtualAlloc(nullptr, SMALL_BYTES, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    need(control != nullptr, "small_allocation_control", GetLastError());
    for (SIZE_T i = 0; i < SMALL_BYTES; i += 4096) static_cast<volatile unsigned char*>(control)[i] = 0x5a;
    win_need(VirtualFree(control, 0, MEM_RELEASE) != FALSE, "small_allocation_release");
    void* large = VirtualAlloc(nullptr, LARGE_BYTES, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    DWORD allocation_error = large ? 0 : GetLastError();
    bool memory_rejected = large == nullptr;
    if (large) win_need(VirtualFree(large, 0, MEM_RELEASE) != FALSE, "large_allocation_release");

    std::wstring command = L"\"" + executable + L"\" --rejected-child";
    std::vector<wchar_t> mutable_command(command.begin(), command.end()); mutable_command.push_back(0);
    // Exactly one attempt; no shell, PATH resolution, inherited handles or loop.
    wchar_t environment[] = L"SystemRoot=C:\\Windows\0\0";
    STARTUPINFOW startup{}; startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    BOOL created = CreateProcessW(executable.c_str(), mutable_command.data(), nullptr, nullptr, FALSE,
        CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT, environment, output.c_str(), &startup, &process);
    DWORD spawn_error = created ? 0 : GetLastError();
    DWORD first_wait = 0, final_wait = 0, terminate_error = 0, thread_close_error = 0, process_close_error = 0;
    bool terminate_attempted = false, terminate_ok = false, reaped = false;
    bool thread_closed = false, process_closed = false;
    if (created) {
        Handle thread(process.hThread), child(process.hProcess);
        first_wait = WaitForSingleObject(child.value, 1000);
        reaped = first_wait == WAIT_OBJECT_0;
        if (!reaped) {
            terminate_attempted = true;
            terminate_ok = TerminateProcess(child.value, 125) != FALSE;
            terminate_error = terminate_ok ? 0 : GetLastError();
            final_wait = WaitForSingleObject(child.value, 1000);
            reaped = final_wait == WAIT_OBJECT_0;
        }
        thread_closed = CloseHandle(thread.value) != FALSE;
        thread_close_error = thread_closed ? 0 : GetLastError(); thread.value = INVALID_HANDLE_VALUE;
        process_closed = CloseHandle(child.value) != FALSE;
        process_close_error = process_closed ? 0 : GetLastError(); child.value = INVALID_HANDLE_VALUE;
    }
    const auto nullable_number = [created](DWORD value) { return created ? std::to_string(value) : "null"; };
    const auto nullable_bool = [created](bool value) { return created ? (value ? "true" : "false") : "null"; };
    std::string result = std::string("{\"small_control_bytes\":65536,\"small_control_released\":true,\"memory_rejected\":")
        + (memory_rejected ? "true" : "false") + ",\"allocation_winerror\":" + std::to_string(allocation_error)
        + ",\"descendant_spawn_attempts\":1,\"spawn\":{\"rejected\":" + (created ? "false" : "true")
        + ",\"winerror\":" + std::to_string(spawn_error)
        + ",\"child_pid\":" + nullable_number(process.dwProcessId)
        + ",\"thread_id\":" + nullable_number(process.dwThreadId)
        + ",\"first_wait_result\":" + nullable_number(first_wait)
        + ",\"terminate_attempted\":" + nullable_bool(terminate_attempted)
        + ",\"terminate_ok\":" + (created && terminate_attempted ? (terminate_ok ? "true" : "false") : "null")
        + ",\"terminate_winerror\":" + (created && terminate_attempted ? std::to_string(terminate_error) : "null")
        + ",\"final_wait_result\":" + (created && terminate_attempted ? std::to_string(final_wait) : "null")
        + ",\"reaped\":" + nullable_bool(reaped)
        + ",\"thread_handle_closed\":" + nullable_bool(thread_closed)
        + ",\"thread_close_winerror\":" + nullable_number(thread_close_error)
        + ",\"process_handle_closed\":" + nullable_bool(process_closed)
        + ",\"process_close_winerror\":" + nullable_number(process_close_error)
        + "},\"target_library_calls\":0,\"model_calls\":0,\"network_requests\":0}";
    publish(output, L"worker-result.json", result);
    write_all(GetStdHandle(STD_OUTPUT_HANDLE), result.data(), static_cast<DWORD>(result.size()));
    write_all(GetStdHandle(STD_OUTPUT_HANDLE), "\n", 1);
    need(memory_rejected && !created && spawn_error == 1816, "resource_expectations_not_met", spawn_error);
    return result;
}

static void error_bytes(const char* bytes, DWORD count) noexcept {
    // Best-effort counted diagnostic only; no file creation, retry or fallback.
    if (count > MARKER_CAP) return;
    for (DWORD done = 0; done < count;) {
        DWORD written = 0;
        if (!WriteFile(GetStdHandle(STD_ERROR_HANDLE), bytes + done, count - done, &written, nullptr)
            || written == 0 || written > count - done) return;
        done += written;
    }
}

int wmain(int argc, wchar_t** argv) {
    std::wstring output;
    try {
        // The only prospective descendant has no recursive branch, marker or I/O.
        if (argc == 2 && std::wstring(argv[1]) == L"--rejected-child") return 0;
        need(argc == 5, "mode_output_protocol_sha256_required");
        std::wstring mode = argv[1];
        need(mode == L"resources" || mode == L"overflow" || mode == L"sleep" || mode == L"suspended_abort", "mode");
        wchar_t self_buffer[32768];
        DWORD n = GetModuleFileNameW(nullptr, self_buffer, 32768);
        need(n > 0 && n < 32768, "own_module_path", GetLastError());
        std::wstring executable = full(std::wstring(self_buffer, n));
        need(same(executable, full(argv[0])), "argv0_not_own_module");
        std::wstring protocol = full(argv[3]);
        size_t slash = protocol.find_last_of(L'\\');
        need(slash != std::wstring::npos && same(protocol.substr(slash + 1), L"effective-protocol.json"), "protocol_name");
        output = full(argv[2]);
        need(same(output, protocol.substr(0, slash) + L"\\execution\\" + mode + L"\\child"), "exact_case_output");
        DWORD output_attributes = GetFileAttributesW(output.c_str());
        need(output_attributes != INVALID_FILE_ATTRIBUTES && (output_attributes & FILE_ATTRIBUTE_DIRECTORY), "output_directory");
        std::wstring expected_w = argv[4];
        need(expected_w.size() == 64 && expected_w.find_first_not_of(L"0123456789abcdef") == std::wstring::npos, "sha256_form");
        std::string expected = utf8(expected_w);
        need(protocol_hash(protocol) == expected, "protocol_hash_mismatch");
        std::string identity = "{\"pid\":" + std::to_string(GetCurrentProcessId())
            + ",\"executable\":" + quote(utf8(executable)) + ",\"mode\":" + quote(utf8(mode))
            + ",\"protocol_sha256\":" + quote(expected) + ",\"binding_authority\":\"parent_pinned_protocol_and_executable\"}";
        publish(output, L"worker-started.json", identity);
        if (mode == L"suspended_abort") throw Failure{"suspended_abort_worker_reached_body", 0};
        if (mode == L"overflow") {
            const std::string bytes(73728, 'x');
            write_all(GetStdHandle(STD_OUTPUT_HANDLE), bytes.data(), static_cast<DWORD>(bytes.size()));
            Sleep(120000); throw Failure{"overflow_cleanup_did_not_stop_worker", 0};
        }
        if (mode == L"sleep") { Sleep(120000); throw Failure{"timeout_cleanup_did_not_stop_worker", 0}; }
        resource_result(executable, output);
        return 0;
    } catch (const Failure& failure) {
        std::string report = "{\"status\":\"failed\",\"code\":" + quote(failure.code)
            + ",\"winerror_or_status\":" + std::to_string(failure.error) + "}\n";
        error_bytes(report.data(), static_cast<DWORD>(report.size()));
        return 2;
    } catch (...) {
        static constexpr char failure[] = "{\"status\":\"failed\",\"code\":\"unexpected_cpp_exception\"}\n";
        error_bytes(failure, sizeof(failure) - 1);
        return 3;
    }
}
