"""Own Python boundary model/static C++ guards; no compilation/native execution."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "typed_public_c_recognizer_platform_v1.cpp"
CONTRACT = HERE / "TRUSTED-SYSTEM32-MODULE-POLICY-v1.json"
VECTORS = HERE / "TRUSTED-SYSTEM32-MODULE-VECTORS-v1.json"
PROOF = HERE / "TRUSTED-SYSTEM32-CHILD-SOURCE-PURE-PROOF-v1.json"
CORE = ("libomp.dll", "ggml-base.dll", "ggml.dll", "llama.dll")
DEVICES = {"con", "prn", "aux", "nul", *("com" + str(i) for i in range(1, 10)), *("lpt" + str(i) for i in range(1, 10))}


def units(value):
    return len(value.encode("utf-16-le")) // 2


def key(value):
    return "".join("\\" if c == "/" else chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in value)


def component(value):
    try:
        value.encode("utf-16-le")
    except UnicodeError:
        return False
    return bool(value) and value not in (".", "..") and value[-1] not in ". " and key(value.split(".", 1)[0]) not in DEVICES and not any(
        ord(c) <= 31 or ord(c) == 127 or c in '<>:"|?*~\\/' for c in value)


def path(value):
    if type(value) is not str:
        raise ValueError("invalid_path")
    try:
        n = units(value)
    except UnicodeError as error:
        raise ValueError("invalid_path") from error
    if not 4 <= n <= 32767 or not re.match(r"^[A-Za-z]:[\\/]", value):
        raise ValueError("invalid_path")
    result = key(value)
    parts = result[3:].split("\\")
    if not all(component(p) for p in parts):
        raise ValueError("invalid_path")
    parent, basename = result.rsplit("\\", 1)
    return result, parent, basename


def leaf(value):
    if re.fullmatch(r"[a-z0-9_][a-z0-9_.-]*\.dll", value) is None:
        return False
    stem = value.split(".", 1)[0]
    return stem not in {"con", "prn", "aux", "nul", *("com" + str(i) for i in range(1, 10)),
                        *("lpt" + str(i) for i in range(1, 10))}


def report(name, reported, executable, runtime, seen_paths=None, seen_names=None):
    if type(name) is not str or not component(name) or units(name) > 255:
        raise ValueError("invalid_name")
    p, parent, basename = path(reported)
    try:
        own, _, own_name = path(executable)
        rt, _, _ = path(runtime)
    except ValueError as error:
        raise ValueError("invalid_context") from error
    n = key(name)
    if n != basename:
        raise ValueError("name_path_mismatch")
    if (seen_paths is not None and p in seen_paths) or (seen_names is not None and n in seen_names):
        raise ValueError("duplicate_report")
    if p == own:
        return "self_executable", p, n
    if n == own_name:
        raise ValueError("reserved_self_wrong_path")
    if parent == rt or n in CORE or n.startswith(("ggml", "llama", "libomp")):
        if parent == rt and n in CORE:
            return "pinned_runtime", p, n
        raise ValueError("protected_native_not_eligible")
    if parent == r"c:\windows\system32":
        if leaf(n):
            return "trusted_platform_context", p, n
        raise ValueError("unsafe_platform_basename")
    raise ValueError("outside_declared_roots")


def batch(rows, executable, runtime):
    try:
        path(executable)
        path(runtime)
    except ValueError as error:
        raise ValueError("invalid_context") from error
    if type(rows) is not list or not 1 <= len(rows) <= 64:
        raise ValueError("module_count_limit")
    paths, names, categories, required = set(), set(), [], Counter()
    for row in rows:
        if type(row) is not dict or set(row) != {"name", "path"}:
            raise ValueError("invalid_metadata")
        category, p, n = report(row["name"], row["path"], executable, runtime, paths, names)
        if p in paths or n in names:
            raise ValueError("duplicate_report")
        paths.add(p)
        names.add(n)
        categories.append(category)
        if category == "self_executable":
            required["self"] += 1
        elif category == "pinned_runtime":
            required[n] += 1
    if any(required[n] != 1 for n in ("self", *CORE)):
        raise ValueError("missing_required_reports")
    return categories


class Checks(unittest.TestCase):
    def test_shared_73_vectors(self):
        self.assertEqual(hashlib.sha256(VECTORS.read_bytes()).hexdigest(), "b7e762b56a67370eeb82f8d9e1df1e3300fc9a9b9f729e8813a563c58c23634a")
        vectors = json.loads(VECTORS.read_bytes())
        self.assertEqual(len(vectors["cases"]), 73)
        for case in vectors["cases"]:
            with self.subTest(id=case["id"]):
                try:
                    classes = batch(case["modules"], case["context"]["expected_self"], case["context"]["expected_runtime"])
                except ValueError as error:
                    self.assertFalse(case["accepted"], str(error))
                    if "reason_if_isolated" in case:
                        self.assertEqual(str(error), case["reason_if_isolated"])
                else:
                    self.assertTrue(case["accepted"])
                    if "expected_classes" in case:
                        self.assertEqual(classes, case["expected_classes"])

    def test_source_report_guard_uses_only_raw_metadata(self):
        source = SOURCE.read_text(encoding="utf-8")
        guard = source[source.index("    std::string modules(Output& diagnostics)"):source.index("\n};", source.index("    std::string modules(Output& diagnostics)"))]
        self.assertIn("raw_snapshot_module_name(entry)", guard)
        self.assertIn("raw_reported_module_path(entry.hModule)", guard)
        for forbidden in ("module_path(", "absolute(", "no_reparse(", "GetDriveType", "GetFullPathName", "CreateFile", "system_approval("):
            self.assertIsNone(re.search(r"(?<![A-Za-z0-9_])" + re.escape(forbidden), guard))
        self.assertIn("lease(item->name)", guard)  # predeclared approved pin, never reported path
        pure = source[source.index("struct PolicyPath"):source.index("[[noreturn]] static void reject_platform_report")]
        for forbidden in ("CreateFile", "GetModule", "GetFile", "GetFullPath", "GetDriveType", "LoadLibrary", "Lease", "fs::"):
            self.assertNotIn(forbidden, pure)

    def test_existing_native_api_layout_default_code_unchanged(self):
        old = (HERE / "typed_public_c_recognizer_v8.cpp").read_text(encoding="utf-8")
        new = SOURCE.read_text(encoding="utf-8")
        begin, end = "template<class T> static T symbol", "\nint wmain("
        self.assertEqual(old[old.index(begin):old.index(end)], new[new.index(begin):new.index(end)])
        self.assertIn('bool recognition = false;', new)
        self.assertIn('allowed_runtime(item->name, false)', new)

    def test_contract_fingerprint_and_only_second_ABI_event_binding(self):
        policy = json.loads(CONTRACT.read_bytes())
        fingerprint = hashlib.sha256(json.dumps(policy["semantic_policy"], sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        self.assertEqual(fingerprint, policy["module_policy_sha256"])
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('PLATFORM_POLICY_SHA256 = "' + fingerprint + '";', source)
        line = next(line for line in source.splitlines() if 'Api api(llama, ggml, base);' in line)
        self.assertIn("module_policy_id", line)
        self.assertIn("module_policy_sha256", line)
        self.assertIn("exact_core_modules_loaded_exports_resolved", line)
        old = (HERE / "typed_public_c_recognizer_v8.cpp").read_text(encoding="utf-8")
        start, end = "// Census metadata comparison", "template<class T> static T symbol"
        self.assertEqual(old[old.index(start):old.index(end)], source[source.index(start):source.index(end)])

    def test_contract_alignment_regressions(self):
        source = SOURCE.read_text(encoding="utf-8")
        block = source[source.index("static bool policy_component"):source.index("static bool policy_name")]
        self.assertIn("policy_device_stem(value)", block)
        block = source[source.index("static bool policy_path"):source.index("static bool policy_platform_leaf")]
        self.assertNotIn("key.size() - split - 1 > 255", block)
        with self.assertRaises(ValueError):
            path(r"C:\NUL\apphelp.dll")
        self.assertEqual(path("D:\\" + "x" * 256)[0], "d:\\" + "x" * 256)

    def test_retained_17_reports_are_pure_metadata_input(self):
        proof = HERE / "SELF-MODULE-CENSUS-RESULT-VERIFICATION-v1.json"
        self.assertEqual(hashlib.sha256(proof.read_bytes()).hexdigest(), "4b628df880898e892482399585436b5fa2a068aed607947cd59e5f3d2f8b3f1e")
        reports = json.loads(proof.read_bytes())["census"]["modules"]
        rows = [dict(name=r["reported_name"], path=r["reported_path"]) for r in reports]
        exe = next(r["reported_path"] for r in reports if r["category"] == "self_executable")
        runtime = next(r["reported_path"].rsplit("\\", 1)[0] for r in reports if r["reported_name"].lower() == "llama.dll")
        categories = Counter(batch(rows, exe, runtime))
        self.assertEqual(categories, dict(self_executable=1, pinned_runtime=4, trusted_platform_context=12))
        self.assertEqual(len(rows), 17)

    def test_pure_canonical_boundaries(self):
        self.assertEqual(path("C:/Windows/SYSTEM32/Apphelp.dll")[0], r"c:\windows\system32\apphelp.dll")
        for value in (r"\\host\share\x.dll", r"\\?\C:\Windows\System32\x.dll", r"C:\Windows\..\System32\x.dll",
                      "C:\\Windows\\System32\\x.dll ", "C:\\Windows\\System32\\x.dll.",
                      "C:\\Windows\\System32\\x.dll:stream", "C:\\Windows\\System32\\X~1.DLL",
                      "C:\\Windows\\System32\\x\x00.dll", "C:\\Windows\\System32\\x\x7f.dll",
                      "C:\\Windows\\System32\\x\ud800.dll", "C:\\\\Windows\\System32\\x.dll"):
            with self.assertRaises(ValueError, msg=repr(value)):
                path(value)
        for value in ("con.dll", "prn.x.dll", "com1.dll", "lpt9.dll", "\u212akernel.dll", "\u0131lama.dll"):
            self.assertFalse(leaf(key(value)))

    def test_protected_names_precede_platform(self):
        exe, runtime = r"D:\fixed\own.exe", r"D:\fixed\runtime"
        for name in (*CORE, "ggml-cpu-x64.dll", "ggml-new.dll", "llamaX.dll", "libomp-extra.dll", "own.exe"):
            with self.assertRaises(ValueError, msg=name):
                report(name, "C:\\Windows\\System32\\" + name, exe, runtime)
        with self.assertRaises(ValueError):
            report("other.dll", runtime + r"\other.dll", exe, runtime)
        self.assertEqual(report("APPHELP.DLL", r"C:\Windows\SYSTEM32\APPHELP.DLL", exe, runtime)[0], "trusted_platform_context")

    def test_rejection_diagnostic_complete_framing_bound(self):
        def wide(n, cap):
            return dict(utf16_units=n, prefix_utf16_units=min(n, cap), truncated=n > cap,
                        pair_cut_adjusted=False, utf8_conversion="returned", utf8="\x01" * min(n, cap),
                        utf16_code_units_hex="0001" * min(n, cap))
        context = dict(context_status="built", original_tag="unapproved_non_native_module",
                       branch="trusted_System32_platform_policy", policy_id="trusted-System32-platform-v1",
                       policy_sha256="f" * 64, reason="outside_trusted_platform_or_unsafe_leaf",
                       enumeration_index=64, path_representation="raw_GetModuleFileNameW_no_filesystem_resolution",
                       name=wide(256, 256), path=wide(32767, 2048), diagnostic_row_publication="returned")
        fields = json.dumps(dict(module_policy=context), ensure_ascii=False, separators=(",", ":")).encode()
        row = json.dumps(dict(event="module_policy_rejection", module_policy=context), ensure_ascii=False, separators=(",", ":")).encode()
        failure = json.dumps(dict(schema_version=1, status="failed", message="unapproved_non_native_module",
                                 elapsed_ms=120000, token_budget_used=0, apply_calls=0, accept_calls=0,
                                 module_policy=context), ensure_ascii=False, separators=(",", ":")).encode()
        self.assertLess(len(fields), 32768)
        self.assertLess(max(len(row), len(failure)) + 1, 65536)

    def test_duplicate_required_and_module_caps(self):
        exe, runtime = r"D:\fixed\own.exe", r"D:\fixed\runtime"
        good = [dict(name="own.exe", path=exe)] + [dict(name=n, path=runtime + "\\" + n) for n in CORE]
        self.assertEqual(len(batch(good, exe, runtime)), 5)
        for rows in (good[1:], good + [dict(good[0])], good + [dict(name="OWN.EXE", path="D:/FIXED/OWN.EXE")],
                     good + [dict(name=f"x{i}.dll", path=rf"C:\Windows\System32\x{i}.dll") for i in range(60)]):
            with self.assertRaises(ValueError):
                batch(rows, exe, runtime)
        self.assertEqual(len(batch(good + [dict(name=f"x{i}.dll", path=rf"C:\Windows\System32\x{i}.dll") for i in range(59)], exe, runtime)), 64)


if __name__ == "__main__":
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    proof = dict(schema_version=1, status="passed" if result.wasSuccessful() else "failed",
                 source=dict(path=str(SOURCE), sha256=before), source_unchanged=hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before,
                 checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 contract_sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest(), vectors_sha256=hashlib.sha256(VECTORS.read_bytes()).hexdigest(),
                 module_policy_id="trusted-System32-platform-v1", module_policy_sha256="807995f6061d7a2c85144c58668fc2e4ecb79a4fb51d462e43d0a8dfc586d589",
                 tests=result.testsRun, shared_vectors=73, failures=[str(item) for item in result.failures], errors=[str(item) for item in result.errors],
                 actual_children=0, SDK_constructions=0, compiler_calls=0, reported_image_files_opened=0,
                 scope="Own intended Python model against frozen vectors plus static C++ comparisons/dataflow/bounds; not compiled C++ execution, native ABI or scientific qualification")
    with PROOF.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(proof, output, indent=2)
        output.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
