"""Pure diagnostic-contract/source checks, not execution of C++ or Windows APIs."""

import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "typed_public_c_recognizer_v5.cpp"
OLD = HERE / "typed_public_c_recognizer_v4.cpp"
PROOF = HERE / "MODULE-POLICY-DIAGNOSTIC-PURE-PROOF-v5.json"
SOURCE_SHA = "c2b802507dd135c33df512a386250d0781bbee0673ed6276bb5512f42adead8c"
OLD_SHA = "2f34035545c6d7bd742b8932a95449aeb76ebc48084e8dc170cbea6b740794ae"
TAG = "unapproved_non_native_module"
BRANCH = "non_native_system_policy"
PINS = []
MAXIMUM_FRAMING = {}


def guard(event, args):
    if event in ("ctypes.dlopen", "subprocess.Popen", "os.system", "socket.__new__",
                 "socket.connect", "socket.getaddrinfo"):
        raise RuntimeError("Pure source/model check only")
    if event == "open" and args and isinstance(args[0], (str, bytes)):
        name = str(args[0]).lower()
        if name.startswith("e:") or name.endswith((".gguf", ".dll", ".exe", ".pyd")):
            raise RuntimeError("No image/model reads in diagnostic contract checks")


sys.addaudithook(guard)


def read(path):
    raw = path.read_bytes()
    item = dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    if item not in PINS:
        PINS.append(item)
    return raw


def units(value):
    raw = value.encode("utf-16-le", "surrogatepass")
    return [int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw), 2)]


def wide_contract(value, cap):
    """Independent intended-format oracle; no claim to execute the C++ formatter."""
    original = units(value)
    count = min(len(original), cap)
    adjusted = bool(count and count < len(original)
                    and 0xD800 <= original[count - 1] <= 0xDBFF
                    and 0xDC00 <= original[count] <= 0xDFFF)
    count -= int(adjusted)
    selected = original[:count]
    raw = b"".join(n.to_bytes(2, "little") for n in selected)
    try:
        rendered = raw.decode("utf-16-le", "strict")
        rendered.encode("utf-8", "strict")
        conversion = "returned"
    except UnicodeError:
        rendered = None
        conversion = "failed"
    return dict(utf16_units=len(original), prefix_utf16_units=count,
                truncated=count < len(original), pair_cut_adjusted=adjusted,
                utf8_conversion=conversion, utf8=rendered,
                utf16_code_units_hex="".join(f"{n:04x}" for n in selected))


def module_context(name, path, directory, listed, publication, ordinal=(1 << 64) - 1):
    return dict(context_status="built", original_tag=TAG, branch=BRANCH,
                enumeration_index=ordinal,
                path_representation="GetModuleFileNameW_then_existing_GetFullPathNameW_lexical_normalization",
                name=wide_contract(name, 256), path=wide_contract(path, 2048),
                system_directory_matches=directory, system_basename_listed=listed,
                diagnostic_row_publication=publication)


def wire(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def publication_model(name, path, *, row_fails=False, construction_fails=False, marker_fails=False):
    # A separate contract model and source-connectivity checks below cover this
    # control flow. No actual native output/publication claim follows.
    if construction_fails:
        context = dict(context_status="construction_failed", original_tag=TAG,
                       branch=BRANCH, diagnostic_row_publication="not_attempted")
        row = None
    else:
        context = module_context(name, path, False, True, "attempt_reserved")
        row = wire(dict(event="module_policy_rejection", module_policy=context))
        context = {**context, "diagnostic_row_publication": "failed" if row_fails else "returned"}
    failure = wire(dict(schema_version=1, status="failed", message=TAG, elapsed_ms=120000,
                        token_budget_used=1000000, apply_calls=(1 << 64) - 1,
                        accept_calls=(1 << 64) - 1, module_policy=context))
    stdout = wire(dict(status="failed", message=TAG, module_policy=context)) + b"\n"
    return dict(row=row, marker=None if marker_fails else failure + b"\n", stdout=stdout,
                context=context, original_tag=TAG)


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.new = read(SOURCE).decode("utf-8").replace("\r\n", "\n")
        cls.old = read(OLD).decode("utf-8").replace("\r\n", "\n")
        if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA:
            raise RuntimeError("Diagnostic source moved")
        if hashlib.sha256(OLD.read_bytes()).hexdigest() != OLD_SHA:
            raise RuntimeError("Preserved original source moved")
        cls.body = cls.new.split("[[noreturn]] static void reject_module_policy", 1)[1].split("\nstruct Runtime", 1)[0]

    def test_caps_are_bound_to_exact_source_and_full_frames(self):
        self.assertIn("MODULE_DIAGNOSTIC_NAME_UNITS = 256, MODULE_DIAGNOSTIC_PATH_UNITS = 2048", self.new)
        self.assertIn("MODULE_DIAGNOSTIC_FIELDS_MAX = 32768", self.new)
        # Six JSON bytes + four hex digits per UTF16 unit is conservative;
        # 8KiB remains for all fixed fields, counters and framing.
        self.assertLess((256 + 2048) * 10 + 8192, 32768)
        for name, path in (("\x01" * 256, "\x01" * 2048),
                           ('"\\' * 128, '"\\' * 1024),
                           ("漢" * 256, "漢" * 2048),
                           ("😀" * 200, "😀" * 2000),
                           ("n" * 32767, "p" * 32767)):
            for state in ("not_attempted", "attempt_reserved", "returned", "failed"):
                context = module_context(name, path, False, False, state)
                fields = b',"module_policy":' + wire(context)
                row = wire(dict(event="module_policy_rejection", module_policy=context)) + b"\n"
                failure = publication_model(name, path)["marker"]
                stdout = publication_model(name, path)["stdout"]
                sizes = dict(fields=len(fields), row=len(row), failure=len(failure), stdout=len(stdout))
                for key, size in sizes.items():
                    MAXIMUM_FRAMING[key] = max(MAXIMUM_FRAMING.get(key, 0), size)
                self.assertLessEqual(len(fields), 32768)
                for block in (row, failure, stdout):
                    self.assertLess(len(block), 65536)
                    json.loads(block)

    def test_utf16_hex_is_numeric_code_unit_order_not_byte_hex(self):
        value = wide_contract("A😀", 256)
        self.assertEqual(value["utf16_code_units_hex"], "0041d83dde00")
        self.assertNotEqual(value["utf16_code_units_hex"], "A😀".encode("utf-16-le").hex())
        self.assertEqual(value["utf16_units"], 3)

    def test_valid_surrogate_pair_cut_moves_back_once(self):
        for cap in (256, 2048):
            value = wide_contract("a" * (cap - 1) + "😀z", cap)
            self.assertEqual(value["prefix_utf16_units"], cap - 1)
            self.assertTrue(value["pair_cut_adjusted"])
            self.assertTrue(value["truncated"])
            self.assertEqual(value["utf8_conversion"], "returned")
            self.assertEqual(value["utf8"], "a" * (cap - 1))

    def test_conversion_failures_preserve_units_and_explicit_null(self):
        for text in ("\ud800", "\udc00", "x\ud800a", "x\udc00z"):
            value = wide_contract(text, 256)
            self.assertEqual(value["utf8_conversion"], "failed")
            self.assertIsNone(value["utf8"])
            self.assertEqual(len(value["utf16_code_units_hex"]), value["prefix_utf16_units"] * 4)
            self.assertEqual(value["utf16_units"], len(units(text)))

    def test_empty_exact_caps_and_long_paths_remain_distinct(self):
        self.assertEqual(wide_contract("", 256)["utf8"], "")
        for cap in (256, 2048):
            self.assertFalse(wide_contract("a" * cap, cap)["truncated"])
            result = wide_contract("a" * (cap + 100), cap)
            self.assertEqual(result["utf16_units"], cap + 100)
            self.assertEqual(result["prefix_utf16_units"], cap)
            self.assertTrue(result["truncated"])

    def test_original_predicate_truth_table_and_error_semantics(self):
        self.assertIn("return directory_matches && basename_listed;", self.new)
        self.assertEqual(self.new.count("GetSystemDirectoryW(b.data(),"), 1)
        self.assertIn('need(n && n < b.size(), "system_directory_failed")', self.new)
        self.assertIn("if (!approval.approved()) reject_module_policy", self.new)
        for directory in (False, True):
            for listed in (False, True):
                original = False if not directory else listed
                self.assertEqual(original, directory and listed)
                context = module_context("known.dll", "X:/known.dll", directory, listed, "returned")
                self.assertIs(context["system_directory_matches"], directory)
                self.assertIs(context["system_basename_listed"], listed)

    def test_publication_failure_does_not_erase_tag_or_marker_context(self):
        for row_fails, marker_fails in ((False, False), (True, False), (True, True)):
            result = publication_model("known.dll", "X:/known.dll", row_fails=row_fails, marker_fails=marker_fails)
            self.assertEqual(result["original_tag"], TAG)
            self.assertEqual(json.loads(result["row"])["module_policy"]["diagnostic_row_publication"], "attempt_reserved")
            final = json.loads(result["stdout"])
            self.assertEqual(final["message"], TAG)
            self.assertEqual(final["module_policy"]["diagnostic_row_publication"], "failed" if row_fails else "returned")
            if not marker_fails:
                self.assertEqual(json.loads(result["marker"])["module_policy"], final["module_policy"])
        self.assertIn('publication = "failed";', self.body)
        self.assertIn("throw rejection;", self.body)
        self.assertIn("out->failure(msg, error.diagnostic_fields)", self.new)
        self.assertIn('<< q(msg) << error.diagnostic_fields << "}\\n"', self.new)

    def test_construction_fallback_keeps_original_failure(self):
        result = publication_model("known.dll", "X:/known.dll", construction_fails=True)
        self.assertIsNone(result["row"])
        self.assertEqual(json.loads(result["marker"])["message"], TAG)
        self.assertEqual(result["context"]["context_status"], "construction_failed")
        self.assertIn('BridgeError rejection("unapproved_non_native_module")', self.body)
        self.assertIn("rejection.diagnostic_fields.clear();", self.body)

    def test_symbol_tables_and_target_api_calls_are_unchanged(self):
        start, end = "template<class T> static T symbol", "static std::string native_text"
        self.assertEqual(self.new.split(start, 1)[1].split(end, 1)[0],
                         self.old.split(start, 1)[1].split(end, 1)[0])
        for api in ("llama_version", "llama_model_default_params", "llama_backend_init",
                    "llama_model_load_from_splits", "llama_tokenize", "llama_sampler_apply"):
            pattern = r"(?:api|a)\." + api + r"\("
            self.assertGreater(len(re.findall(pattern, self.old)), 0)
            self.assertEqual(len(re.findall(pattern, self.new)), len(re.findall(pattern, self.old)))
        self.assertEqual(self.new.count("runtime.modules(out)"), 4)
        self.assertEqual(self.new.count("runtime.modules(*out)"), 1)
        self.assertNotIn("runtime.modules()", self.new)

    def test_no_unknown_image_io_or_new_API_in_diagnostic_helper(self):
        self.assertEqual(self.body.count("output.row("), 1)
        for call in ("CreateFileW(", "LoadLibraryExW(", "GetProcAddress(", "OpenProcess(",
                     "ReadFile(", "GetFileSizeEx(", "CreateProcessW("):
            self.assertNotIn(call, self.body)
            self.assertEqual(self.new.count(call), self.old.count(call))
        self.assertIn("GetCurrentProcessId()", self.new.split("std::string modules", 1)[1])
        self.assertIn("else if (same(p.parent_path(), root) || pin(name)", self.new)

    def test_original_runtime_header_and_success_output_contract_unchanged(self):
        header = HERE.parents[2] / "data/cache/r09-typed-ABI-preparation-v4-20261028T231155Z/recognizer_runtime_pins.hpp"
        raw = read(header)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "dee857596074375218a3c3f8d11130f4066fbfb07b7ae08e454f1f12306a1784")
        self.assertIn(b"R09_RECOGNITION_ENABLED = false;", raw)
        tail = self.new.split("int wmain(", 1)[1]
        tail = tail.replace("runtime.modules(*out)", "runtime.modules()")
        tail = tail.replace("out->failure(msg, error.diagnostic_fields)", "out->failure(msg)")
        tail = tail.replace("<< q(msg) << error.diagnostic_fields <<", "<< q(msg) <<")
        self.assertEqual(tail, self.old.split("int wmain(", 1)[1])
        # Existing independent marker attempt still follows its own catch-protected
        # JSONL attempt. Context is appended to that same failure object.
        failure = self.new.split("void failure(", 1)[1].split("static fs::path module_path", 1)[0]
        self.assertIn("diagnostic_fields", failure)
        self.assertIn('try { if (stream.h != INVALID_HANDLE_VALUE) row(s); } catch (...) {}', failure)
        self.assertIn('L"failure.json"', failure)


if __name__ == "__main__":
    if PROOF.exists():
        raise RuntimeError("Pure proof already exists; no automatic repeat")
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    record = dict(schema_version=1, status="passed" if result.wasSuccessful() else "failed",
                  source=dict(path=str(SOURCE), sha256=SOURCE_SHA),
                  checker_sha256=hashlib.sha256(read(Path(__file__).resolve())).hexdigest(),
                  tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                  maximum_modelled_bytes=MAXIMUM_FRAMING, inputs=PINS,
                  scope="Independent intended-format model plus static source checks; C++ formatter was not compiled or executed",
                  activity=dict(CPP_executions=0, compiler_calls=0, target_API_calls=0,
                                DLL_loads=0, unknown_image_reads=0, model_reads=0, network=0))
    with PROOF.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
