"""Static source/PE owner regressions only; never load DLLs or execute a bridge."""

import ast
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE / "typed_public_c_recognizer_v3.cpp"
NEW = HERE / "typed_public_c_recognizer_v4.cpp"
PARSER = HERE.parent / "recovery-step9-native-grammar-20261028/build_typed_converter_bridge_v3.py"
PROTOCOL = HERE / "DETACHED-ABI-OBSERVATION-PROTOCOL-v1.json"
REPORT = HERE / "BRIDGE-SYMBOL-OWNERS-PURE-PROOF-v4.json"
EXPECTED_SOURCE = "2f34035545c6d7bd742b8932a95449aeb76ebc48084e8dc170cbea6b740794ae"
EXPECTED_OLD = "0d6d7c8bf7495d35811fda56df805dba4e0cf7aa5470776df0903cd5215ad9f4"
OLD_EXE = ROOT / "data/cache/r09-public-c-bridge-build-20261028T175036Z/typed_public_c_recognizer_abi.exe"
PINS = []


def audit(event, args):
    if event in ("subprocess.Popen", "os.system", "ctypes.dlopen", "socket.connect",
                 "socket.getaddrinfo", "socket.__new__"):
        raise RuntimeError("Static source/PE regression only")
    if event == "open" and args and isinstance(args[0], (str, bytes)):
        name = str(args[0]).lower()
        if name.startswith("e:") or name.endswith(".gguf") or "\\data\\benchmark\\" in name:
            raise RuntimeError("No model/external/evaluation payloads")


sys.addaudithook(audit)


def read(path):
    path = path.absolute()
    if not path.is_relative_to(ROOT):
        raise RuntimeError("Input leaves workspace")
    for item in (path, *path.parents):
        status = item.lstat()
        if item.is_symlink() or getattr(status, "st_file_attributes", 0) & 0x400:
            raise RuntimeError("Reparse input")
    raw = path.read_bytes()
    row = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    if row not in PINS:
        PINS.append(row)
    return raw


def require_mapping(rows, exports):
    names = set()
    for row in rows:
        if row["symbol"] in names:
            raise ValueError("Duplicate symbol")
        names.add(row["symbol"])
        if row["owner"] not in exports or row["symbol"] not in exports[row["owner"]]:
            raise ValueError("Required export absent from exact owner: " + row["owner"] + ":" + row["symbol"])


def extract_mapping(source):
    table = {}
    for group, body in re.findall(r"^#define (\w+_APIS)\(X\) (.+)$", source, re.M):
        table[group] = re.findall(r"X\((\w+)\)", body)
    loaders = {}
    for macro, handle, owner in re.findall(
        r'^#define (LOAD\w+)\(n\) n = symbol<decltype\(&::n\)>\((\w+), "([\w.-]+)", #n\);$',
        source, re.M,
    ):
        loaders[macro] = (handle, owner)
    rows = []
    for group, macro in re.findall(r"^        (\w+_APIS)\((LOAD\w+)\)$", source, re.M):
        handle, owner = loaders[macro]
        rows.extend(dict(symbol=name, owner=owner, handle=handle, group=group) for name in table[group])
    return rows


def direct_exports(pe):
    rva, size = pe.directory(0)
    directory = pe.offset(rva)
    _, functions, count, function_rva, names_rva, ordinals_rva = struct.unpack_from("<IIIIII", pe.raw, directory + 16)
    result = {}
    for i in range(count):
        name = pe.string(struct.unpack_from("<I", pe.raw, pe.offset(names_rva) + 4 * i)[0])
        index = struct.unpack_from("<H", pe.raw, pe.offset(ordinals_rva) + 2 * i)[0]
        if index >= functions:
            raise ValueError("Export ordinal outside table")
        address = struct.unpack_from("<I", pe.raw, pe.offset(function_rva) + 4 * index)[0]
        result[name] = None if not rva <= address < rva + size else pe.string(address)
    return result


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.new = read(NEW).decode("utf-8")
        cls.old = read(OLD).decode("utf-8")
        cls.rows = extract_mapping(cls.new)
        protocol = json.loads(read(PROTOCOL))
        cls.expected = {str(Path(row["path"]).absolute()).lower(): row for row in protocol["inputs"]}
        tree = ast.parse(read(PARSER).decode("utf-8-sig"))
        node = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == "PE")
        namespace = dict(struct=struct)
        # Only this retained data-reader class executes, never the build helper body.
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(PARSER), "exec"), namespace)
        cls.exports = {}
        cls.direct = {}
        runtime = ROOT / "data/cache/approved-native-mirror-20261028T004531Z/runtime"
        for name in ("llama.dll", "ggml.dll", "ggml-base.dll", "libomp.dll"):
            path = runtime / name
            raw = read(path)
            expected = cls.expected[str(path.absolute()).lower()]
            if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
                raise RuntimeError("Pinned runtime changed")
            pe = namespace["PE"](raw)
            cls.exports[name] = set(pe.exports())
            cls.direct[name] = direct_exports(pe)

    def test_complete_exact_owner_table_matches_actual_PE(self):
        self.assertEqual(len(self.rows), 25)
        self.assertEqual({owner: sum(r["owner"] == owner for r in self.rows)
                          for owner in ("llama.dll", "ggml.dll", "ggml-base.dll")},
                         {"llama.dll": 15, "ggml.dll": 5, "ggml-base.dll": 5})
        require_mapping(self.rows, self.exports)
        for row in self.rows:
            self.assertIsNone(self.direct[row["owner"]][row["symbol"]])

    def test_original_mapping_has_exact_five_wrong_owner_failures(self):
        body = re.search(r"^#define GGML_APIS\(X\) (.*)$", self.old, re.M).group(1)
        missing = [name for name in re.findall(r"X\((\w+)\)", body) if name not in self.exports["ggml.dll"]]
        self.assertEqual(missing, ["ggml_backend_reg_name", "ggml_backend_reg_dev_count",
                                  "ggml_backend_reg_dev_get", "ggml_backend_dev_name", "ggml_backend_dev_type"])

    def test_every_wrong_owner_mutation_rejected_without_fallback(self):
        for row in self.rows:
            if row["owner"] == "ggml-base.dll":
                with self.subTest(symbol=row["symbol"]):
                    bad = [{**r, "owner": "ggml.dll"} if r is row else r for r in self.rows]
                    with self.assertRaisesRegex(ValueError, "Required export absent"):
                        require_mapping(bad, self.exports)

    def test_unknown_missing_duplicate_and_unlisted_owner_rejected(self):
        for row in ({**self.rows[0], "symbol": "not_a_real_required_export"},
                    {**self.rows[0], "owner": "unapproved.dll"}):
            with self.assertRaises(ValueError):
                require_mapping([row], self.exports)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            require_mapping([self.rows[0], self.rows[0]], self.exports)

    def test_owner_handles_and_diagnostic_are_explicit(self):
        self.assertEqual({r["owner"]: r["handle"] for r in self.rows},
                         {"llama.dll": "llama", "ggml.dll": "ggml", "ggml-base.dll": "base"})
        self.assertIn("Api api(llama, ggml, base);", self.new)
        self.assertIn('std::string("required_export_missing:") + owner + ":" + name', self.new)
        symbol_body = self.new.split("template<class T> static T symbol", 1)[1].split("\n#define", 1)[0]
        self.assertEqual(symbol_body.count("GetProcAddress("), 1)
        self.assertNotIn("GetModuleHandle", symbol_body)

    def test_unaffected_source_bytes_and_public_requirements_preserved(self):
        start = "template<class T> static T symbol"
        end = "static std::string native_text"
        before_old, after_old = self.old.split(start, 1)
        before_new, after_new = self.new.split(start, 1)
        self.assertEqual(before_old, before_new)
        tail_old = after_old.split(end, 1)[1]
        tail_new = after_new.split(end, 1)[1]
        tail_new = tail_new.replace('HMODULE base = runtime.load_core(L"ggml-base.dll");',
                                    'HMODULE base = runtime.load_core(L"ggml-base.dll"); (void)base;')
        tail_new = tail_new.replace("Api api(llama, ggml, base);", "Api api(llama, ggml);")
        self.assertEqual(tail_old, tail_new)
        old_names = re.findall(r"X\((\w+)\)", self.old.split("struct Api", 1)[0])
        self.assertEqual(set(old_names), {r["symbol"] for r in self.rows})
        self.assertEqual(len(old_names), 25)

    def test_original_source_executable_and_disabled_header_remain_pinned(self):
        self.assertEqual(hashlib.sha256(read(OLD)).hexdigest(), EXPECTED_OLD)
        self.assertEqual(hashlib.sha256(read(NEW)).hexdigest(), EXPECTED_SOURCE)
        self.assertEqual(hashlib.sha256(read(OLD_EXE)).hexdigest(),
                         "9f955aec8310ded1cd26648c7d9828369751219975893d5f45b35073b6927696")
        header = ROOT / "data/cache/r09-public-c-bridge-preparation-20261028T175036Z/recognizer_runtime_pins.hpp"
        self.assertIn("R09_RECOGNITION_ENABLED = false;", read(header).decode("utf-8"))


if __name__ == "__main__":
    if REPORT.exists():
        raise RuntimeError("Proof already exists; no automatic repeat")
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    proof = dict(schema_version=1, status="passed_static_symbol_owner_regressions" if result.wasSuccessful() else "failed",
                 source=dict(path=str(NEW), bytes=NEW.stat().st_size,
                             sha256=hashlib.sha256(read(NEW)).hexdigest()),
                 helper=dict(path=str(Path(__file__).resolve()), sha256=hashlib.sha256(read(Path(__file__).resolve())).hexdigest()),
                 tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                 wrong_owner_negative_vectors=5, required_symbol_count=25,
                 complete_symbol_mapping=Checks.rows if hasattr(Checks, "rows") else [], inputs=PINS,
                 activity=dict(DLL_loads=0, target_calls=0, compiler_calls=0, model_reads=0,
                               network_requests=0, bridge_executions=0),
                 qualification="Static PE owner availability only; no signature, execution or ABI acceptance")
    with REPORT.open("x", encoding="utf-8") as output:
        json.dump(proof, output, indent=2)
        output.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
