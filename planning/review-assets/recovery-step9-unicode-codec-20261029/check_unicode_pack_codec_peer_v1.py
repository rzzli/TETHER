"""Independent source/pure wire reconstruction; complete pack stays in memory."""
import ast
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import sys
import time
import types
import unittest

HERE = Path(__file__).resolve().parent
WIRE = HERE.parent / "recovery-step9-unicode-wire-20261029"
CONTROL = HERE.parent / "recovery-step9-unicode-control-20261029"
SOURCE = HERE / "unicode_pack_codec_v1.py"
PROOF = HERE / "UNICODE-PACK-CODEC-INDEPENDENT-PURE-PROOF-v1.json"
SOURCE_SHA = "c2e579f9a5f0e485d4af1fe5bfeaed75c62debffb5f779391b294d740f1f5b40"
PATHS = dict(base_design=WIRE / "UNICODE-WIRE-DESIGN-CONTRACT-v2.json",
    framing_contract=WIRE / "UNICODE-WIRE-FRAMING-CONTRACT-v1.json",
    corpus=CONTROL / "UNICODE-CONTROL-CORPUS-v1.json", stages=CONTROL / "UNICODE-CONTROL-STAGES-v1.json",
    profile_contract=CONTROL / "UNICODE-CONTROL-CONTRACT-v2.json",
    analyzer_contract=CONTROL / "UNICODE-PIECE-ANALYZER-CONTRACT-v1.json")
STAGES = ("mechanism_asof0", "genetics_asof0", "mechanism_vb_chief0", "genetics_vb_chief0")
STRATA = ("stage_source_report", "scalar_field_grid", "ASCII_escape_counterparts", "mixed_normalization_escape",
          "grammar_semantic_JSON_controls", "byte_harness_guards")
DIMENSIONS = ("project_JSON_parse", "Unicode_scalar_JSON", "complete_v3_semantic_validation",
              "generation_grammar_membership", "native_membership", "JSON_syntax")


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def word(value):
    # Deliberately independent of codec's struct-based integer writer.
    return value.to_bytes(4, "little", signed=False)


def identified(value):
    raw = value.encode("ascii")
    return word(len(raw)) + raw


def reference_pack(documents, captured):
    base, framing = documents["base_design"], documents["framing_contract"]
    base_sha = hashlib.sha256(canonical(base["semantic_contract"])).hexdigest()
    effective = hashlib.sha256(canonical(dict(base_design_semantic_sha256=base_sha,
                                             framing_semantics=framing["framing_semantics"]))).hexdigest()
    digests = [effective] + [hashlib.sha256(captured[key]).hexdigest() for key in
                            ("corpus", "stages", "profile_contract", "analyzer_contract")]
    result = bytearray(b"R09NU01\0" + word(1) + b"".join(bytes.fromhex(h) for h in digests)
                       + b"".join(word(value) for value in (4, 2, 84, 4)))
    assert len(result) == 188
    stage_rows = documents["stages"]["stages"]
    unique = []
    for stage in stage_rows:
        h = stage["grammar_sha256"]
        if h not in [row[0] for row in unique]:
            unique.append((h, stage["prepared"]["generation_grammar"]["grammar"].encode("utf-8")))
    offsets = {}
    for index, (h, raw) in enumerate(unique):
        start = len(result); prefix = identified("grammar/" + str(index))
        offsets["grammar", index] = dict(start=start, hash=start+len(prefix), length=start+len(prefix)+32,
                                         body=start+len(prefix)+36)
        result += prefix + bytes.fromhex(h) + word(len(raw)) + raw
        offsets["grammar", index]["end"] = len(result)
    for index, stage in enumerate(stage_rows):
        start = len(result); prefix = identified(stage["id"])
        offsets["stage", index] = dict(start=start, request=start+len(prefix), payload=start+len(prefix)+32,
                                       grammar_index=start+len(prefix)+64)
        result += (prefix + bytes.fromhex(stage["request_sha256"]) + bytes.fromhex(stage["payload_sha256"])
                   + word([row[0] for row in unique].index(stage["grammar_sha256"])))
        offsets["stage", index]["end"] = len(result)
    for index, case in enumerate(documents["corpus"]["cases"]):
        start = len(result); prefix = identified(case["id"]); raw = bytes.fromhex(case["raw_hex"])
        offset = dict(start=start, ordinal=start+len(prefix), stage=start+len(prefix)+4,
                      stratum=start+len(prefix)+8, hash=start+len(prefix)+12, length=start+len(prefix)+44,
                      body=start+len(prefix)+48)
        result += prefix + word(index) + word(STAGES.index(case["stage_id"])) + word(STRATA.index(case["stratum"]))
        result += bytes.fromhex(case["sha256"]) + word(len(raw)) + raw
        offset["dimensions"] = len(result)
        result += b"".join(word(2 if case["expected"][key] is None else (1 if case["expected"][key] else 0)) for key in DIMENSIONS)
        offset["eligible"] = len(result)
        try: raw.decode("utf-8", "strict"); valid = True
        except UnicodeError: valid = False
        kind = 2 if 0 in raw else (0 if valid else 1)
        result += word(int(case["expected"]["native_byte_eligible"])) + word(kind) + word(min(65536, 4*len(raw)+32))
        offset["end"] = len(result); offsets["case", index] = offset
    return bytes(result), offsets


def main():
    started = time.monotonic()
    if PROOF.exists(): raise FileExistsError(PROOF)
    tracked = [SOURCE, Path(__file__).resolve(), HERE / "UNICODE-PACK-CODEC-PURE-PROOF-v1.json",
               HERE / "check_unicode_pack_codec_v1.py", HERE / "UNICODE-PACK-CODEC-FREEZE-v1.json", *PATHS.values()]
    before = [pin(path) for path in tracked]
    raw_source = SOURCE.read_bytes()
    assert hashlib.sha256(raw_source).hexdigest() == SOURCE_SHA
    codec = types.ModuleType("independent_unicode_codec_v1"); codec.__file__ = str(SOURCE)
    sys.modules[codec.__name__] = codec
    exec(compile(raw_source, str(SOURCE), "exec"), codec.__dict__)
    captured = {key: path.read_bytes() for key, path in PATHS.items()}
    documents = {key: json.loads(raw) for key, raw in captured.items()}
    sources = codec.SourceBytes(**captured)
    profile = codec.make_profile(sources, check=lambda: None)
    reference, offsets = reference_pack(documents, captured)
    counts = dict(source_fields=0, record_fields=0, negative_mutations=0, callback_stops=0)

    class Peer(unittest.TestCase):
        def reject(self, raw):
            with self.assertRaises(codec.CodecError): codec.decode(raw, profile, check=lambda: None)
            counts["negative_mutations"] += 1

        def change(self, at, value):
            return reference[:at] + value + reference[at+len(value):]

        def test_independent_complete_byte_reconstruction_and_offset_cardinality(self):
            self.assertEqual(codec.encode(profile, check=lambda: None), reference)
            self.assertEqual((len(reference), hashlib.sha256(reference).hexdigest()),
                             (37766, "d2537df43e7e6e8113c4e08f0536c2e3a698bd274963ab71a4efced4fa32c8ab"))
            result = codec.decode(reference, profile, check=lambda: None)
            self.assertEqual((len(result.grammars), len(result.stages), len(result.cases)), (2, 4, 84))
            self.assertEqual(len(offsets), 90)
            self.assertEqual(result.bytes, len(reference))

        def test_all_case_fields_and_authored_domains_independently(self):
            result = codec.decode(reference, profile, check=lambda: None)
            self.assertEqual(tuple(s.id for s in result.stages), STAGES)
            population = 0
            for expected, decoded in zip(documents["corpus"]["cases"], result.cases):
                self.assertEqual(decoded.id, expected["id"])
                self.assertEqual(decoded.ordinal, expected["ordinal"])
                self.assertEqual(decoded.raw, bytes.fromhex(expected["raw_hex"]))
                self.assertEqual(decoded.sha256, hashlib.sha256(decoded.raw).hexdigest())
                self.assertEqual(decoded.authored_dimensions,
                    tuple(2 if expected["expected"][key] is None else int(expected["expected"][key]) for key in DIMENSIONS))
                self.assertEqual(decoded.token_cap, 4*len(decoded.raw)+32)
                self.assertEqual(decoded.stage_index, STAGES.index(expected["stage_id"]))
                self.assertEqual(decoded.stratum_index, STRATA.index(expected["stratum"]))
                population += (expected["expected"]["native_byte_eligible"] and
                               expected["expected"]["generation_grammar_membership"] is True and
                               expected["expected"]["complete_v3_semantic_validation"] is True)
                counts["record_fields"] += 8
            self.assertEqual((sum(c.native_byte_eligible for c in result.cases), population), (78, 68))
            guards = [case for case in result.cases if not case.native_byte_eligible]
            self.assertEqual(len(guards), 6)
            self.assertTrue(any(b"\0" in case.raw for case in guards))
            self.assertTrue(all(case.authored_dimensions[4] == 2 for case in guards))

        def test_every_header_word_and_last_record_valid_but_wrong_values(self):
            for at in (8, 172, 176, 180, 184):
                self.reject(self.change(at, word(0xffffffff)))
            for at in range(12, 172, 32):
                self.reject(self.change(at+31, bytes([reference[at+31] ^ 1])))
            pos = offsets["case", 83]
            for key, value in (("ordinal", 82), ("stage", (int.from_bytes(reference[pos["stage"]:pos["stage"]+4], "little")+1)%4),
                               ("stratum", (int.from_bytes(reference[pos["stratum"]:pos["stratum"]+4], "little")+1)%6)):
                self.reject(self.change(pos[key], word(value)))
            for dimension in range(6):
                at = pos["dimensions"] + 4*dimension
                old = int.from_bytes(reference[at:at+4], "little")
                self.reject(self.change(at, word((old+1)%3)))
            for delta, value in ((0, 1), (4, 0), (8, 0xffffffff)):
                self.reject(self.change(pos["eligible"]+delta, word(value)))
            for index in range(4):
                at = offsets["stage", index]["grammar_index"]
                self.reject(self.change(at, word(1-int.from_bytes(reference[at:at+4], "little"))))

        def test_length_hash_order_and_trailing_interior_faults(self):
            for kind, index in (("grammar", 0), ("grammar", 1), ("case", 0), ("case", 40), ("case", 83)):
                pos = offsets[kind, index]
                self.reject(self.change(pos["length"], word(0)))
                self.reject(self.change(pos["length"], word(0xffffffff)))
                self.reject(self.change(pos["body"], bytes([reference[pos["body"]] ^ 1])))
                self.reject(reference[:pos["end"]-1])
            for left, right in ((0, 1), (40, 41), (82, 83)):
                a, b = offsets["case", left], offsets["case", right]
                self.reject(reference[:a["start"]] + reference[b["start"]:b["end"]] + reference[a["start"]:a["end"]] + reference[b["end"]:])
            self.reject(reference + b"\0")
            self.reject(reference[:-1])

        def test_profile_factory_and_exact_byte_types_without_serialized_authority(self):
            for name, raw in captured.items():
                for alternate in (raw+b"x", raw[:-1], bytes([raw[0]^1])+raw[1:], bytearray(raw)):
                    changed = dict(captured, **{name: alternate})
                    with self.assertRaises(codec.CodecError): codec.make_profile(codec.SourceBytes(**changed), check=lambda: None)
                    counts["source_fields"] += 1
            class BytesSubclass(bytes): pass
            alternate = dict(captured, corpus=BytesSubclass(captured["corpus"]))
            with self.assertRaises(codec.CodecError): codec.make_profile(codec.SourceBytes(**alternate), check=lambda: None)
            for foreign in ({"ready": True}, codec.ValidatedProfile(), object(), None):
                with self.assertRaises(codec.CodecError): codec.encode(foreign, check=lambda: None)
                with self.assertRaises(codec.CodecError): codec.decode(reference, foreign, check=lambda: None)
            for raw in (bytearray(reference), memoryview(reference), BytesSubclass(reference)):
                self.reject(raw)

        def test_callbacks_preserve_original_exception_and_result_is_unavailable(self):
            actions = (lambda callback: codec.make_profile(sources, check=callback),
                       lambda callback: codec.encode(profile, check=callback),
                       lambda callback: codec.decode(reference, profile, check=callback))
            for action in actions:
                calls = [0]
                def count(): calls[0] += 1
                action(count)
                for which in (1, 2, calls[0]//2, calls[0]):
                    for error in (TimeoutError("owner cutoff"), KeyboardInterrupt("stop"), SystemExit(17)):
                        current = [0]
                        def stop():
                            current[0] += 1
                            if current[0] == which: raise error
                        with self.assertRaises(type(error)) as caught: action(stop)
                        self.assertIs(caught.exception, error)
                        counts["callback_stops"] += 1
                for malformed in (None, False, 1):
                    with self.assertRaises(codec.CodecError): action(malformed)

        def test_immutable_return_and_detached_diagnostics(self):
            result = codec.decode(reference, profile, check=lambda: None)
            for target, name in ((profile, "header_digests"), (profile.cases[0], "raw"),
                                 (result, "cases"), (result.grammars[0], "raw")):
                with self.assertRaises(FrozenInstanceError): setattr(target, name, None)
            summary = result.to_dict()
            summary["cases"][0]["authored_dimensions"].clear(); summary["stages"].clear(); summary["grammars"][0]["id"] = "forged"
            fresh = result.to_dict()
            self.assertEqual(len(fresh["cases"][0]["authored_dimensions"]), 6)
            self.assertEqual(len(fresh["stages"]), 4)
            self.assertEqual(fresh["grammars"][0]["id"], "grammar/0")
            for key in ("profile_qualified", "originals_authenticated", "runtime_authorized"):
                self.assertIs(fresh[key], False)
            self.assertEqual(fresh["scientific_validation"], "not_established")

        def test_closed_module_scope_and_preserved_author_proof(self):
            tree = ast.parse(raw_source)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import): imports += [name.name for name in node.names]
                elif isinstance(node, ast.ImportFrom): imports.append(node.module)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"open", "exec", "eval", "compile", "__import__"})
            self.assertEqual(set(imports), {"dataclasses", "hashlib", "json", "re", "struct"})
            author = json.loads((HERE / "UNICODE-PACK-CODEC-PURE-PROOF-v1.json").read_bytes())
            self.assertEqual(author["status"], "passed")
            self.assertEqual(author["source"]["sha256"], SOURCE_SHA)

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Peer))
    elapsed = time.monotonic() - started
    stable = before == [pin(path) for path in tracked]
    report = dict(schema_version=1, status="passed" if result.wasSuccessful() and stable and elapsed < 20 else "failed",
        source=pin(SOURCE), checker=pin(Path(__file__).resolve()), inputs=before, inputs_unchanged=stable,
        methods=result.testsRun, counts=counts, failures=len(result.failures), errors=len(result.errors),
        failure_details=[dict(test=str(case), traceback=trace) for case, trace in result.failures+result.errors],
        elapsed_seconds=elapsed, maximum_seconds=20,
        independent_in_memory_pack=dict(bytes=len(reference), sha256=hashlib.sha256(reference).hexdigest(), persisted=False),
        independent_field_encoding="Explicit source/wire reconstruction with int.to_bytes, independent of codec encode/struct writer; all84 source records inspected.",
        complete_runtime_pack_files_written=0, profile_qualified=False, originals_authenticated=False,
        runtime_authorized=False, source_closure_qualification=False, SDK_native_compiler_operations=0,
        CPU_GGUF_oldpack_operations=0, hostile_Python_security_claim=False)
    with PROOF.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(report, out, indent=2); out.write("\n")
    print(json.dumps(dict(status=report["status"], methods=result.testsRun, counts=counts,
                          elapsed_seconds=elapsed, proof_sha256=pin(PROOF)["sha256"])))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
