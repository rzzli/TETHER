"""Finite intended-state models/static source checks; no C++/SDK/payload execution."""
from collections import Counter
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "typed_public_c_recognizer_recognition_v2.cpp"
CONTRACT = HERE / "RECOGNITION-EXECUTION-CONTRACT-v1.json"
POLICY = HERE / "RECOGNITION-MODULE-POLICY-v1.json"
VECTORS = HERE / "RECOGNITION-MODULE-VECTORS-v1.json"
DESCRIPTOR = HERE / "RECOGNITION-RUNTIME-PIN-DESCRIPTOR-v1.json"
HEADER = HERE / "recognition_runtime_pins_v1.hpp"
PROOF = HERE / "RECOGNITION-CHILD-SOURCE-PURE-PROOF-v2.json"
LIMITS = json.loads(CONTRACT.read_bytes())["native_call_policy"]
CAPS = LIMITS["per_API_caps"]

# Reuse only our already frozen mathematical lexical functions, not a parent or SDK.
lexical = ast.parse((HERE / "check_platform_policy_source_v1.py").read_bytes())
LEX = dict(re=re)
exec(compile(ast.Module(body=[n for n in lexical.body if isinstance(n, ast.FunctionDef)
                             and n.name in {"units", "key", "component", "path", "leaf"}], type_ignores=[]),
             "<own-frozen-lexical-math>", "exec"), LEX)
LEX["DEVICES"] = {"con", "prn", "aux", "nul", *("com" + str(i) for i in range(1, 10)),
                   *("lpt" + str(i) for i in range(1, 10))}
CORE = ("libomp.dll", "ggml-base.dll", "ggml.dll", "llama.dll")
CPU = "ggml-cpu-x64.dll"


def match(rows, context, phase):
    if type(phase) is not str or phase not in ("pre_cpu", "post_cpu"):
        raise ValueError("invalid_phase")
    eligible = (*CORE, CPU) if phase == "post_cpu" else CORE
    try:
        own, _, own_name = LEX["path"](context["expected_self"])
        runtime, _, _ = LEX["path"](context["expected_runtime"])
    except ValueError as error:
        raise ValueError("invalid_context") from error
    if type(rows) is not list or not 1 <= len(rows) <= 64:
        raise ValueError("module_count_limit")
    paths, names, result, required = set(), set(), [], Counter()
    for row in rows:
        if type(row) is not dict or set(row) != {"name", "path"}:
            raise ValueError("invalid_metadata")
        name = row["name"]
        if type(name) is not str or not LEX["component"](name) or LEX["units"](name) > 255:
            raise ValueError("invalid_name")
        name = LEX["key"](name)
        reported, parent, basename = LEX["path"](row["path"])
        if name != basename:
            raise ValueError("name_path_mismatch")
        if name in names or reported in paths:
            raise ValueError("duplicate_report")
        names.add(name)
        paths.add(reported)
        if reported == own:
            category = "self_executable"
            required["self"] += 1
        elif name == own_name:
            raise ValueError("reserved_self_wrong_path")
        elif parent == runtime or name in (*CORE, CPU) or name.startswith(("ggml", "llama", "libomp")):
            if name not in eligible or reported != runtime + "\\" + name:
                raise ValueError("protected_native_not_eligible")
            category = "pinned_runtime"
            required[name] += 1
        elif parent == r"c:\windows\system32":
            if not LEX["leaf"](name):
                raise ValueError("unsafe_platform_basename")
            category = "trusted_platform_context"
        else:
            raise ValueError("outside_declared_roots")
        result.append(category)
    if any(required[n] != 1 for n in ("self", *eligible)):
        raise ValueError("missing_required_reports")
    return result


class Meter:
    """Own model of reservation/return and known-owned cleanup; no native calls."""
    def __init__(self):
        self.attempted = Counter()
        self.returned = Counter()
        self.expired = False
        self.calls = []
        self.model_owned = self.backend_owned = False
        self.model_unknown = self.backend_unknown = False
        self.samplers_owned = self.sampler_unknown = 0
        self.cleanup_failed = False

    def invoke(self, name, callback, cleanup=False):
        if not cleanup and (self.expired or self.cleanup_failed):
            raise TimeoutError("No new native work")
        if self.attempted[name] >= CAPS[name] or sum(self.attempted.values()) >= LIMITS["aggregate_attempt_cap"]:
            raise RuntimeError("Native fixed cap")
        self.attempted[name] += 1
        if name == "llama_model_free":
            self.model_owned, self.model_unknown = False, True
        if name == "llama_backend_free":
            self.backend_owned, self.backend_unknown = False, True
        if name == "llama_sampler_free":
            if not self.samplers_owned:
                raise RuntimeError("No sampler ownership")
            self.samplers_owned -= 1
            self.sampler_unknown += 1
        self.calls.append(name)
        value = callback()
        self.returned[name] += 1  # observed before caller deadline/publication
        if name == "llama_backend_init":
            self.backend_owned = True
        elif name == "llama_model_load_from_splits":
            self.model_owned = value is not None
        elif name == "llama_sampler_init_grammar" and value is not None:
            self.samplers_owned += 1
        elif name == "llama_model_free":
            self.model_unknown = False
        elif name == "llama_backend_free":
            self.backend_unknown = False
        elif name == "llama_sampler_free":
            self.sampler_unknown -= 1
        return value


class Session:
    def __init__(self, meter):
        self.m = meter
        self.backend = False
        self.model = None

    def initialize(self):
        self.m.invoke("llama_backend_init", lambda: None)
        self.backend = True

    def load(self):
        self.model = self.m.invoke("llama_model_load_from_splits", object)

    def close(self, model_error=False, backend_error=False):
        if self.m.attempted["llama_sampler_init_grammar"] != self.m.returned["llama_sampler_init_grammar"]:
            self.m.cleanup_failed = True
            return
        def error(): raise RuntimeError("Synthetic native free did not return")
        if self.model is not None:
            if self.m.samplers_owned or self.m.sampler_unknown:
                self.m.cleanup_failed = True
                return
            self.model = None
            try:
                self.m.invoke("llama_model_free", error if model_error else lambda: None, cleanup=True)
            except RuntimeError:
                self.m.cleanup_failed = self.m.model_unknown = True
        if self.m.attempted["llama_model_load_from_splits"] != self.m.returned["llama_model_load_from_splits"] or self.m.model_unknown or self.m.samplers_owned or self.m.sampler_unknown:
            self.m.cleanup_failed = True
            return
        if self.backend:
            self.backend = False
            try:
                self.m.invoke("llama_backend_free", error if backend_error else lambda: None, cleanup=True)
            except RuntimeError:
                self.m.cleanup_failed = self.m.backend_unknown = True


class Sampler:
    def __init__(self, meter):
        self.m = meter
        self.value = self.m.invoke("llama_sampler_init_grammar", object)

    def close(self, fail=False):
        def error(): raise RuntimeError("Synthetic sampler free did not return")
        if self.value is None:
            return
        self.value = None
        try:
            self.m.invoke("llama_sampler_free", error if fail else lambda: None, cleanup=True)
        except RuntimeError:
            self.m.cleanup_failed = True


class Checks(unittest.TestCase):
    def test_all100_shared_phase_vectors(self):
        vectors = json.loads(VECTORS.read_bytes())
        self.assertEqual(len(vectors["cases"]), 100)
        for case in vectors["cases"]:
            with self.subTest(case=case["id"]):
                try:
                    classes = match(case["modules"], case["context"], case["phase"])
                except ValueError as error:
                    self.assertFalse(case["accepted"])
                    if "reason_if_isolated" in case:
                        self.assertEqual(str(error), case["reason_if_isolated"])
                else:
                    self.assertTrue(case["accepted"])
                    if "expected_classes" in case:
                        self.assertEqual(classes, case["expected_classes"])

    def test_native_caps_exact25_and_aggregate(self):
        self.assertEqual(len(CAPS), 25)
        self.assertEqual(sum(CAPS.values()), 4276181)
        source = SOURCE.read_text(encoding="utf-8")
        names = re.search(r"NATIVE_NAMES\[NATIVE_COUNT\] = \{([^}]+)\}", source).group(1)
        values = re.search(r"NATIVE_CAPS\[NATIVE_COUNT\] = \{([^}]+)\}", source).group(1)
        table = dict(zip(re.findall(r'"([^"]+)"', names), map(int, re.findall(r"([0-9]+)ull", values))))
        self.assertEqual(table, CAPS)

    def test_perAPI_and_aggregate_cap_admission(self):
        m = Meter()
        m.invoke("llama_backend_init", lambda: None)
        with self.assertRaises(RuntimeError): m.invoke("llama_backend_init", lambda: None)
        self.assertEqual(m.calls, ["llama_backend_init"])
        m.attempted = Counter(CAPS)
        with self.assertRaises(RuntimeError): m.invoke("llama_version", lambda: None)

    def test_model_return_then_deadline_preserves_cleanup(self):
        m = Meter(); s = Session(m); s.initialize(); s.load()
        self.assertTrue(m.model_owned)
        m.expired = True
        with self.assertRaises(TimeoutError): m.invoke("llama_model_get_vocab", object)
        s.close(); s.close()
        self.assertEqual(m.returned["llama_model_load_from_splits"], 1)
        self.assertEqual(m.calls[-2:], ["llama_model_free", "llama_backend_free"])
        self.assertFalse(m.model_owned or m.backend_owned or m.model_unknown or m.backend_unknown)

    def test_backend_return_before_late_error(self):
        m = Meter(); s = Session(m); s.initialize(); m.expired = True
        try: raise TimeoutError("Primary post-init check")
        except TimeoutError as original:
            s.close(); s.close()
            self.assertEqual(str(original), "Primary post-init check")
        self.assertEqual(m.returned["llama_backend_init"], 1)
        self.assertEqual(m.returned["llama_backend_free"], 1)

    def test_sampler_return_then_late_check_frees_once(self):
        m = Meter(); s = Sampler(m); m.expired = True
        s.close(); s.close()
        self.assertEqual((m.attempted["llama_sampler_free"], m.returned["llama_sampler_free"]), (1, 1))
        self.assertEqual((m.samplers_owned, m.sampler_unknown), (0, 0))

    def test_unreturned_sampler_creation_blocks_dependents(self):
        m = Meter(); s = Session(m); s.initialize(); s.load()
        def interrupted(): raise RuntimeError("Unknown sampler creation")
        with self.assertRaises(RuntimeError): m.invoke("llama_sampler_init_grammar", interrupted)
        s.close(); s.close()
        self.assertTrue(m.cleanup_failed)
        self.assertEqual((m.attempted["llama_sampler_init_grammar"], m.returned["llama_sampler_init_grammar"]), (1, 0))
        self.assertEqual(m.attempted["llama_model_free"], 0)
        self.assertEqual(m.attempted["llama_backend_free"], 0)

    def test_unreturned_model_creation_blocks_backend(self):
        m = Meter(); s = Session(m); s.initialize()
        def interrupted(): raise RuntimeError("Unknown model creation")
        with self.assertRaises(RuntimeError): m.invoke("llama_model_load_from_splits", interrupted)
        s.close(); s.close()
        self.assertTrue(m.cleanup_failed)
        self.assertEqual((m.attempted["llama_model_load_from_splits"], m.returned["llama_model_load_from_splits"]), (1, 0))
        self.assertEqual(m.attempted["llama_backend_free"], 0)

    def test_unknown_free_is_not_repeated_or_called_success(self):
        m = Meter(); s = Session(m); s.initialize(); s.load()
        primary = TimeoutError("Preserve primary")
        s.close(model_error=True); s.close()
        self.assertTrue(m.cleanup_failed and m.model_unknown)
        self.assertEqual((m.attempted["llama_model_free"], m.returned["llama_model_free"]), (1, 0))
        self.assertEqual(m.attempted["llama_backend_free"], 0)
        self.assertEqual(str(primary), "Preserve primary")

    def test_unknown_sampler_release_blocks_later_resource_free(self):
        m = Meter(); session = Session(m); session.initialize(); session.load(); sampler = Sampler(m)
        sampler.close(fail=True); sampler.close(); session.close()
        self.assertTrue(m.cleanup_failed)
        self.assertEqual(m.sampler_unknown, 1)
        self.assertEqual(m.attempted["llama_model_free"], 0)
        self.assertEqual(m.attempted["llama_backend_free"], 0)

    def test_returned_free_then_publication_error_no_repeat(self):
        m = Meter(); s = Session(m); s.initialize(); s.load(); s.close()
        try: raise OSError("Late publication")
        except OSError: s.close()
        self.assertEqual(m.attempted["llama_model_free"], 1)
        self.assertEqual(m.returned["llama_model_free"], 1)

    def test_progress_and_unavailable_coverage_are_not_completed(self):
        state = dict(computed=1, written=0, unavailable=True, slots=6)
        with self.assertRaises(OSError): raise OSError("Result write failed")
        self.assertNotEqual(state["computed"], state["written"])
        self.assertFalse(not state["unavailable"] and state["slots"] == 6)
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('need(!unavailable, "required_partial_UTF8_prefix_coverage_unavailable")', source)
        self.assertLess(source.index("++native_state.cases_computed"), source.index('out.row("{\\\"event\\\":\\\"case_result'))

    def test_all_native_calls_wrapped_and_no_hotloop_flush(self):
        source = SOURCE.read_text(encoding="utf-8")
        calls = list(re.finditer(r"\b(?:a|api)\.(" + "|".join(CAPS) + r")\(", source))
        self.assertEqual({m.group(1) for m in calls}, set(CAPS))
        for call in calls:
            prefix = source[max(0, call.start() - 150):call.start()]
            self.assertRegex(prefix, r"native_call\(NATIVE_" + call.group(1) + r",\s*\[&\]\(\)\s*\{\s*return\s*$")
        wrapper = source[source.index("template<class F> static decltype(auto) native_call"):source.index("static std::string native_snapshot_fields();")]
        self.assertNotIn("out.row", wrapper)
        self.assertNotIn("write_all", wrapper)
        self.assertIn("call(); native_returned(kind)", wrapper)
        self.assertIn("auto value = call(); native_returned(kind)", wrapper)

    def test_cleanup_ownership_precedes_call_and_no_work_tick(self):
        source = SOURCE.read_text(encoding="utf-8")
        block = source[source.index("struct NativeSession"):source.index("static bool admitted")]
        self.assertLess(block.index("model = nullptr; // reserve ownership"), block.index("NATIVE_llama_model_free"))
        self.assertLess(block.index("backend = false; // no retry"), block.index("NATIVE_llama_backend_free"))
        self.assertIn("}, true)", block)
        self.assertIn("native_state.model_release_unknown", block)
        self.assertIn("native_state.attempted[NATIVE_llama_sampler_init_grammar] != native_state.returned[NATIVE_llama_sampler_init_grammar]", block)
        self.assertIn("native_state.attempted[NATIVE_llama_model_load_from_splits] != native_state.returned[NATIVE_llama_model_load_from_splits]", block)

    def test_header_descriptor_is_metadata_only_and_exact(self):
        d = json.loads(DESCRIPTOR.read_bytes()); contract = json.loads(CONTRACT.read_bytes())
        self.assertEqual(d["observed_version"], "0.7.0-dev")
        self.assertEqual(d["pack"]["sha256"], "f75ab9937c57b5f03c2234643a8a9c91cda852ca0cca0de0478369f793e57e5f")
        self.assertEqual(sum(x["bytes"] for x in d["ordered_shard_descriptors"]), 8988110496)
        self.assertTrue(all(value == 0 for value in d["activity"].values()))
        self.assertTrue(all(value is False for value in d["authority"].values()))
        self.assertEqual(hashlib.sha256(HEADER.read_bytes()).hexdigest(), d["header"]["sha256"])
        self.assertIn('R09_EXPECTED_LLAMA_VERSION[] = "0.7.0-dev"', HEADER.read_text(encoding="utf-8"))
        self.assertEqual(contract["observed_version"], d["observed_version"])


if __name__ == "__main__":
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    proof = dict(schema_version=1, status="passed" if result.wasSuccessful() else "failed", tests=result.testsRun,
                 failures=[str(x) for x in result.failures], errors=[str(x) for x in result.errors],
                 source_sha256=before, source_unchanged=hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before,
                 checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 shared_vectors=100, execution_contract_sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
                 phase_policy_sha256=hashlib.sha256(POLICY.read_bytes()).hexdigest(),
                 descriptor_sha256=hashlib.sha256(DESCRIPTOR.read_bytes()).hexdigest(),
                 activity=dict(compiler_calls=0, SDK_constructors=0, children=0, CPU_GGUF_payload_open_hash=0),
                 scope="Own intended Python phase/ownership/counter models and static C++ source checks; not compiled native execution, asset identity revalidation or conformance")
    with PROOF.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(proof, output, indent=2)
        output.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
