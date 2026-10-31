"""Pure boundary models and static source guards; never execute the C++ collector."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "typed_public_c_recognizer_v7.cpp"
WIRE = HERE / "SELF-MODULE-CENSUS-WIRE-v2.json"
PROOF = HERE / "SELF-MODULE-CENSUS-CHILD-PURE-PROOF-v2.json"
MAX = 2 * 1024 * 1024
RESERVE = 65536
ERROR_RESERVE = 8192
RESULTS: list[dict] = []


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def enumeration(count: int, *, next_error=18, first_ok=True):
    """Intended finite collector model, not an execution of fetched/native code."""
    recorded, seen, queries, nexts = 0, 0, 0, 0
    found = first_ok
    natural = False
    while found:
        seen += 1
        if recorded == 64:
            break
        recorded += 1
        queries += 1
        nexts += 1
        found = recorded < count
        if not found:
            natural = next_error == 18
    return recorded, seen, queries, nexts, natural


class Budget:
    def __init__(self):
        self.reserved = 0
        self.written = 0

    def write(self, n, *, final=False, fail=False):
        ceiling = MAX - (ERROR_RESERVE if final else RESERVE)
        if self.reserved > ceiling or n > ceiling - self.reserved:
            raise ValueError("cap")
        self.reserved += n
        if fail:
            raise OSError("partial write; exact count unknown")
        self.written += n

    def marker(self, n):
        if n > 4096 or n > MAX - self.reserved:
            raise ValueError("marker cap")
        self.reserved += n
        self.written += n


def close_model(*, primary=None, reserve_fail=False, close_ok=True, returned_fail=False):
    state = dict(owned=True, attempts=0, returned=False, ok=False, error=None,
                 publication_failed=False, first_error=primary)

    def close_once():
        if not state["owned"]:
            return
        state["owned"] = False
        if reserve_fail:
            state["publication_failed"] = True
            state["first_error"] = state["first_error"] or "reservation_publication"
        state["attempts"] += 1
        state["returned"] = True
        state["ok"] = close_ok
        state["error"] = None if close_ok else 6
        if returned_fail:
            state["publication_failed"] = True
            state["first_error"] = state["first_error"] or "return_publication"
        if not close_ok:
            state["first_error"] = state["first_error"] or "close_failed"

    close_once()
    close_once()  # exception cleanup must observe ownership already released
    return state


def ascii_key(value):
    return "".join("\\" if c == "/" else chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in value)


def wide(value: str, cap: int):
    raw = value.encode("utf-16-le", errors="surrogatepass")
    units = [int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw), 2)]
    n = min(len(units), cap)
    adjusted = bool(n and n < len(units) and 0xD800 <= units[n - 1] <= 0xDBFF and 0xDC00 <= units[n] <= 0xDFFF)
    if adjusted:
        n -= 1
    prefix = b"".join(u.to_bytes(2, "little") for u in units[:n]).decode("utf-16-le", errors="surrogatepass")
    try:
        prefix.encode("utf-8")
        conversion, text = "returned", prefix
    except UnicodeEncodeError:
        conversion, text = "failed", None
    return dict(utf16_units=len(units), prefix_utf16_units=n, truncated=n < len(units),
                pair_cut_adjusted=adjusted, utf8_conversion=conversion, utf8=text,
                utf16_code_units_hex="".join(f"{u:04x}" for u in units[:n]))


class Cases(unittest.TestCase):
    def test_enumeration_one_and_exact64_end(self):
        self.assertEqual(enumeration(1), (1, 1, 1, 1, True))
        self.assertEqual(enumeration(64), (64, 64, 64, 64, True))

    def test_65th_entry_is_not_queried_or_stored(self):
        self.assertEqual(enumeration(65), (64, 65, 64, 64, False))
        self.assertEqual(enumeration(1000), (64, 65, 64, 64, False))

    def test_successful_return_count_survives_publication_deadline(self):
        for prior in (0, 1, 63, 64):
            seen = prior
            # A successful First/Next return is known before publication/check.
            seen += 1
            try:
                raise TimeoutError("post-call publication or deadline")
            except TimeoutError:
                pass
            self.assertEqual(seen, prior + 1)

    def test_unretained_inputs_never_classify(self):
        cases = [dict(name_terminated=True, path_ok=True, path_terminated=True,
                      path_nul=False, name_units=11, path_units=31, system_complete=True)]
        for field, invalid in (("name_terminated", False), ("path_ok", False),
                               ("path_terminated", False), ("path_nul", True),
                               ("name_units", 257), ("path_units", 2049),
                               ("system_complete", False)):
            row = {**cases[0], field: invalid}
            comparable = (row["name_terminated"] and row["path_ok"] and row["path_terminated"]
                          and not row["path_nul"] and row["name_units"] <= 256
                          and row["path_units"] <= 2048 and row["system_complete"])
            self.assertFalse(comparable)
            self.assertEqual({"category": "unresolved_metadata", "predicate": None},
                             {"category": "unresolved_metadata" if not comparable else "known",
                              "predicate": None if not comparable else True})

    def test_error_not_natural_end(self):
        self.assertFalse(enumeration(1, next_error=5)[4])
        self.assertEqual(enumeration(0, first_ok=False), (0, 0, 0, 0, False))

    def test_query_zero_and_capacity_are_incomplete(self):
        for n in (0, 32768, 40000):
            ok = 0 < n < 32768
            full = n if ok else None
            self.assertFalse(ok)
            self.assertIsNone(full)
        self.assertTrue(0 < 32767 < 32768)

    def test_reservation_survives_partial_write(self):
        b = Budget()
        with self.assertRaises(OSError):
            b.write(1000, fail=True)
        self.assertEqual((b.reserved, b.written), (1000, 0))
        with self.assertRaises(ValueError):
            b.write(MAX - RESERVE)
        self.assertEqual(b.reserved, 1000)

    def test_reserved_finalization_and_both_error_records(self):
        b = Budget()
        b.write(MAX - RESERVE)
        b.write(RESERVE - ERROR_RESERVE, final=True)
        b.marker(4096)
        b.marker(4096)
        self.assertEqual((b.reserved, b.written), (MAX, MAX))
        with self.assertRaises(ValueError):
            b.marker(1)

    def test_close_failure_is_one_attempt(self):
        for reserve_fail in (False, True):
            for returned_fail in (False, True):
                state = close_model(close_ok=False, reserve_fail=reserve_fail, returned_fail=returned_fail)
                self.assertEqual(state["attempts"], 1)
                self.assertTrue(state["returned"])
                self.assertFalse(state["owned"])
                self.assertEqual(state["error"], 6)

    def test_close_publication_failure_preserves_primary(self):
        state = close_model(primary="first_capture_failure", reserve_fail=True, returned_fail=True)
        self.assertEqual(state["first_error"], "first_capture_failure")
        self.assertEqual(state["attempts"], 1)
        self.assertTrue(state["publication_failed"])

    def test_conservative_ascii_fold_and_mismatch(self):
        self.assertEqual(ascii_key("C:/Windows/SYSTEM32/APPHELP.DLL"), "c:\\windows\\system32\\apphelp.dll")
        self.assertNotEqual(ascii_key("C:\\X\\..\\Y"), ascii_key("C:\\Y"))
        self.assertNotEqual(ascii_key("\u0130"), ascii_key("i\u0307"))
        self.assertNotEqual(ascii_key("kernel32.dll"), ascii_key("different.dll"))

    def test_wide_hex_and_surrogate_boundary(self):
        self.assertEqual(wide("A\u20ac", 10)["utf16_code_units_hex"], "004120ac")
        self.assertEqual(wide("x\U0001f600z", 2)["prefix_utf16_units"], 1)
        self.assertTrue(wide("x\U0001f600z", 2)["pair_cut_adjusted"])
        broken = wide("\ud800", 10)
        self.assertIsNone(broken["utf8"])
        self.assertEqual(broken["utf16_code_units_hex"], "d800")

    def test_worst_case_metadata_and_terminal_reserve(self):
        # Control characters maximize JSON escaping per UTF16 unit. These rows are
        # partial (embedded NUL), but still must fit without hiding bytes.
        raw = dict(event="module_metadata", ordinal=64, snapshot_name=wide("\x00" * 256, 256),
                   snapshot_name_terminated=False, path=wide("\x00" * 32768, 2048),
                   path_query_call_id=9999, path_full_utf16_units_known=None,
                   path_buffer_terminated=False, path_contains_NUL=True)
        row_bytes = len(encoded(raw)) + 1
        self.assertLess(row_bytes, 65536)
        # Each of 132 calls has two <512-byte metadata records; classification
        # 64 <256-byte rows + fixed metadata, and two <=4096-byte errors.
        bound = row_bytes * 64 + 132 * 2 * 512 + 64 * 256 + 8192 + 8192
        RESULTS.append(dict(kind="conservative_structured_bound", raw_row_bytes=row_bytes, corpus_bound_bytes=bound))
        self.assertLess(bound, MAX)

    def test_source_branch_stops_before_Api(self):
        s = SOURCE.read_text()
        main = s[s.index("int wmain("):]
        branch = main[main.index('if (mode == "--module-census")'):main.index("Api api(")]
        self.assertIn("return 0;", branch)
        self.assertIn("out->commit()", branch)
        self.assertNotIn("api.", branch)
        collector = s[s.index("// Census metadata comparison"):s.index("template<class T> static T symbol")]
        for forbidden in ("GetProcAddress(", "LoadLibrary", "CreateFile", "absolute(", "module_path(", "runtime.modules", "llama_", "ggml_"):
            self.assertNotIn(forbidden, collector)
        self.assertIn("snapshot = INVALID_HANDLE_VALUE; std::exception_ptr first_error", collector)
        self.assertLess(collector.index("snapshot = INVALID_HANDLE_VALUE; std::exception_ptr first_error"), collector.index("BOOL ok = CloseHandle(owned)"))

    def test_source_prior_native_and_policy_blocks_unchanged(self):
        old = (HERE / "typed_public_c_recognizer_v5.cpp").read_text()
        new = SOURCE.read_text()
        for left, right in (("struct Runtime {", "\ntemplate<class T> static T symbol"),
                            ("template<class T> static T symbol", "\nint wmain(")):
            before = old[old.index(left):old.index(right, old.index(left))]
            end = "\n// Census metadata comparison" if left == "struct Runtime {" else right
            after = new[new.index(left):new.index(end, new.index(left))]
            self.assertEqual(before.strip(), after.strip())
        self.assertIn("structured_reserved += s.size() + 1;", new)
        self.assertIn("snapshot_close_publication_failed = true", new)


if __name__ == "__main__":
    started = time.monotonic()
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    proof = dict(schema_version=1, status="passed" if result.wasSuccessful() and before == after else "failed",
                 source=str(SOURCE), source_sha256=before, source_unchanged=before == after,
                 checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 wire_sha256=hashlib.sha256(WIRE.read_bytes()).hexdigest(), tests_run=result.testsRun,
                 failures=[str(x) for x in result.failures], errors=[str(x) for x in result.errors],
                 measured_seconds=time.monotonic() - started, bounds=RESULTS,
                 actual_children=0, real_SDK_constructions=0, compiler_calls=0,
                 native_target_calls=0,
                 scope="Pure intended boundary models and static source comparisons; not compiled C++ behavior or native census qualification")
    with PROOF.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(proof, output, indent=2)
        output.write("\n")
    raise SystemExit(0 if proof["status"] == "passed" else 1)
