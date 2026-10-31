"""Pure new-data tests; complete packs never leave process memory."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
CONTROL = HERE.parent / "recovery-step9-unicode-control-20261029"
WIRE = HERE.parent / "recovery-step9-unicode-wire-20261029"
SOURCE = HERE / "unicode_pack_codec_v2.py"
PROOF = HERE / "UNICODE-PACK-CODEC-PURE-PROOF-v2.json"
SOURCE_PATHS = dict(base_design=WIRE/"UNICODE-WIRE-DESIGN-CONTRACT-v2.json",
                    framing_contract=WIRE/"UNICODE-WIRE-FRAMING-CONTRACT-v1.json",
                    corpus=CONTROL/"UNICODE-CONTROL-CORPUS-v1.json",
                    stages=CONTROL/"UNICODE-CONTROL-STAGES-v1.json",
                    profile_contract=CONTROL/"UNICODE-CONTROL-CONTRACT-v2.json",
                    analyzer_contract=CONTROL/"UNICODE-PIECE-ANALYZER-CONTRACT-v1.json")


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def main():
    assert not PROOF.exists(), "Preserve the first pure proof"
    started = time.monotonic()
    paths = [SOURCE, Path(__file__), HERE/"UNICODE-PACK-CODEC-SOURCE-IMPLEMENTATION-DECISION-v1.json",
             HERE/"UNICODE-PACK-CODEC-API-v1.md", WIRE/"UNICODE-WIRE-FRAMING-FIXTURES-v1.json",
             WIRE/"UNICODE-WIRE-FRAMING-FREEZE-v1.json", *SOURCE_PATHS.values()]
    before = {str(path):pin(path) for path in paths}
    spec = importlib.util.spec_from_file_location("pure_unicode_pack_codec_v2", SOURCE)
    codec = importlib.util.module_from_spec(spec); sys.modules[spec.name] = codec; spec.loader.exec_module(codec)
    captured = {key:path.read_bytes() for key,path in SOURCE_PATHS.items()}
    sources = codec.SourceBytes(**captured)
    profile = codec.make_profile(sources,check=lambda:None)
    packed = codec.encode(profile,check=lambda:None)
    corpus = json.loads(captured["corpus"])["cases"]
    fixtures = json.loads((WIRE/"UNICODE-WIRE-FRAMING-FIXTURES-v1.json").read_text(encoding="utf-8"))
    fragments = {row["id"]:row for row in fixtures["pack_fragments"]}
    counts = dict(literal_fragments=0,literal_positive_records=0,literal_negative_mutations=0,
                  independent_cases=0,format_mutations=0,truncation_points=0,callback_faults=0)
    # Independent offset inspection for this one source pack, not the codec decoder.
    offsets = {}; at = 188
    for kind,total in (("grammar",2),("stage",4),("case",84)):
        for index in range(total):
            begin = at; n, = struct.unpack_from("<I",packed,at); at += 4
            identity = packed[at:at+n].decode("ascii"); at += n
            record = dict(start=begin,id_end=at,id=identity)
            if kind == "grammar":
                record["hash"] = at; at += 32; record["length"] = at
                size, = struct.unpack_from("<I",packed,at); at += 4; record["body"] = at; at += size
            elif kind == "stage":
                record["request"] = at; at += 64; record["index"] = at; at += 4
            else:
                record["indices"] = at; at += 12; record["hash"] = at; at += 32; record["length"] = at
                size, = struct.unpack_from("<I",packed,at); at += 4; record["body"] = at; at += size
                record["tail"] = at; at += 36
            record["end"] = at; offsets[kind,index] = record
    assert at == len(packed)

    def changed(at,raw): return packed[:at]+raw+packed[at+len(raw):]

    class Checks(unittest.TestCase):
        def reject(self,raw,reason=None):
            with self.assertRaises(codec.CodecError) as caught:codec.decode(raw,profile,check=lambda:None)
            if reason is not None:self.assertEqual(str(caught.exception),reason)

        def test_factory_exact_source_profile_and_complete_memory_roundtrip(self):
            result = codec.decode(packed,profile,check=lambda:None)
            self.assertEqual((len(result.grammars),len(result.stages),len(result.cases)),(2,4,84))
            self.assertEqual((result.grammars,result.stages,result.cases),(profile.grammars,profile.stages,profile.cases))
            self.assertEqual(result.sha256,hashlib.sha256(packed).hexdigest())
            self.assertEqual(result.bytes,len(packed));self.assertLess(len(packed),codec.MAX_PACK_BYTES)
            self.assertEqual(sum(c.native_byte_eligible for c in result.cases),78)
            self.assertEqual(sum(c.harness_kind!=0 for c in result.cases),6)

        def test_all25_frozen_literal_fragments_and_independent_positive_bytes(self):
            self.assertEqual(packed[:188],bytes.fromhex(fragments["header/exact"]["raw_hex"]))
            for fragment in fragments.values():
                raw=bytes.fromhex(fragment["raw_hex"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(),fragment["sha256"]);self.assertEqual(len(raw),fragment["bytes"])
                counts["literal_fragments"]+=1
                if fragment["component_framing_expected"]:
                    if fragment["component"]=="fixed_header":actual=packed[:188]
                    else:
                        kind,index=fragment["id"].split("/");pos=offsets[kind,int(index)];actual=packed[pos["start"]:pos["end"]]
                    self.assertEqual(raw,actual);counts["literal_positive_records"]+=1
                else:
                    if fragment["component"]=="fixed_header":mutated=raw+packed[188:]
                    elif fragment["component"]=="ID":
                        pos=offsets["grammar",0];mutated=packed[:188]+raw+packed[pos["id_end"]:]
                    else:
                        ordinal=int(fragment["id"].split("/")[1]);pos=offsets["case",ordinal]
                        mutated=packed[:pos["start"]]+raw+packed[pos["end"]:]
                    self.reject(mutated);counts["literal_negative_mutations"]+=1
            self.assertEqual((counts["literal_positive_records"],counts["literal_negative_mutations"]),(11,14))

        def test_manual_header_and_all84_case_fields_against_new_corpus(self):
            self.assertEqual(packed[:12],b"R09NU01\0\x01\0\0\0")
            self.assertEqual(struct.unpack_from("<4I",packed,172),(4,2,84,4))
            expected=[codec.WIRE_SHA256]+[hashlib.sha256(captured[k]).hexdigest() for k in ("corpus","stages","profile_contract","analyzer_contract")]
            self.assertEqual([packed[i:i+32].hex() for i in range(12,172,32)],expected)
            strata=("stage_source_report","scalar_field_grid","ASCII_escape_counterparts","mixed_normalization_escape","grammar_semantic_JSON_controls","byte_harness_guards")
            dimensions=("project_JSON_parse","Unicode_scalar_JSON","complete_v3_semantic_validation","generation_grammar_membership","native_membership","JSON_syntax")
            stage_ids=("mechanism_asof0","genetics_asof0","mechanism_vb_chief0","genetics_vb_chief0")
            for index,row in enumerate(corpus):
                pos=offsets["case",index];tail=struct.unpack_from("<9I",packed,pos["tail"])
                self.assertEqual(pos["id"],row["id"])
                self.assertEqual(struct.unpack_from("<3I",packed,pos["indices"]),(index,stage_ids.index(row["stage_id"]),strata.index(row["stratum"])))
                self.assertEqual(packed[pos["hash"]:pos["hash"]+32].hex(),row["sha256"])
                self.assertEqual(packed[pos["body"]:pos["tail"]],bytes.fromhex(row["raw_hex"]))
                self.assertEqual(tail[:6],tuple(2 if row["expected"][k] is None else int(row["expected"][k]) for k in dimensions))
                self.assertEqual(tail[6],int(row["expected"]["native_byte_eligible"]));self.assertEqual(tail[8],4*row["bytes"]+32)
                counts["independent_cases"]+=1

        def test_exact_source_mutation_type_size_and_factory_token(self):
            for name in captured:
                altered=bytearray(captured[name]);altered[-1]^=1
                with self.assertRaisesRegex(codec.CodecError,"source_hash"):
                    codec.make_profile(replace(sources,**{name:bytes(altered)}),check=lambda:None)
                with self.assertRaisesRegex(codec.CodecError,"source_bytes_or_size"):
                    codec.make_profile(replace(sources,**{name:captured[name]+b"x"}),check=lambda:None)
            with self.assertRaises(codec.CodecError):codec.make_profile(captured,check=lambda:None)
            with self.assertRaises(codec.CodecError):codec.encode(codec.ValidatedProfile(),check=lambda:None)
            with self.assertRaises(codec.CodecError):codec.decode(packed,{"ready":True},check=lambda:None)

        def test_header_and_record_hashes_bind_all_slots(self):
            for at in range(12,172,32):
                self.reject(changed(at,bytes([packed[at]^1])));counts["format_mutations"]+=1
            for key in (("grammar",0),("grammar",1),("case",0),("case",83)):
                pos=offsets[key]
                for field in ("hash","body"):
                    at=pos[field];self.reject(changed(at,bytes([packed[at]^1])));counts["format_mutations"]+=1

        def test_lengths_checked_before_large_copy_and_unsigned_overflow(self):
            first=offsets["grammar",0];case=offsets["case",0]
            self.reject(changed(first["start"],struct.pack("<I",0xffffffff)),"ID_cap")
            self.reject(changed(first["length"],struct.pack("<I",0xffffffff)),"grammar_cap")
            self.reject(changed(case["length"],struct.pack("<I",0xffffffff)),"case_bytes_cap")
            self.reject(changed(first["length"],struct.pack("<I",0)),"grammar_cap")
            self.reject(changed(case["length"],struct.pack("<I",0)),"case_bytes_cap")
            self.reject(b"x"*(codec.MAX_PACK_BYTES+1),"pack_bytes_or_cap")
            self.reject(bytearray(packed),"pack_bytes_or_cap")
            with self.assertRaisesRegex(codec.CodecError,"grammar_source_cap"):
                codec._grammar_bytes("a"*65537,65536,lambda:None)
            with self.assertRaisesRegex(codec.CodecError,"grammar_source_cap"):
                codec._grammar_bytes("\U0001f600"*20000,65536,lambda:None)
            counts["format_mutations"]+=9

        def test_duplicate_IDs_enums_indices_and_source_expectations(self):
            for kind,index in (("grammar",1),("stage",1),("case",1)):
                first=offsets[kind,0];second=offsets[kind,index]
                replacement=packed[first["start"]:first["id_end"]]
                self.reject(packed[:second["start"]]+replacement+packed[second["id_end"]:],"duplicate_ID")
                counts["format_mutations"]+=1
            pos=offsets["case",0]
            for at,value in [(pos["indices"],1),(pos["indices"]+4,4),(pos["indices"]+8,6),(pos["tail"],3),(pos["tail"]+24,2),(pos["tail"]+28,3),(pos["tail"]+32,1),(pos["tail"],0)]:
                self.reject(changed(at,struct.pack("<I",value)));counts["format_mutations"]+=1
            self.reject(packed+b"\0","trailing_bytes");counts["format_mutations"]+=1

        def test_truncation_at_each_record_and_final_field(self):
            points={0,7,8,11,12,43,171,172,187,188,len(packed)-1}
            for pos in offsets.values():points.update((pos["start"],pos["id_end"]-1,pos["end"]-1))
            for point in sorted(points):
                self.reject(packed[:point]);counts["truncation_points"]+=1

        def test_check_callback_required_and_interruptions_propagate(self):
            class Stop(BaseException):pass
            for action in (lambda check:codec.make_profile(sources,check=check),lambda check:codec.encode(profile,check=check),lambda check:codec.decode(packed,profile,check=check)):
                with self.assertRaises(codec.CodecError):action(None)
                calls=[0]
                def counting():calls[0]+=1
                action(counting);total=calls[0]
                for target in (1,total//2,total):
                    marker=Stop("synthetic callback stop");current=[0]
                    def fail():
                        current[0]+=1
                        if current[0]==target:raise marker
                    with self.assertRaises(Stop) as caught:action(fail)
                    self.assertIs(caught.exception,marker);counts["callback_faults"]+=1

        def test_deep_immutability_and_no_geometry_or_runtime_authority(self):
            result=codec.decode(packed,profile,check=lambda:None)
            for value,field in ((profile,"cases"),(profile.cases[0],"raw"),(result,"cases"),(result.stages[0],"id")):
                with self.assertRaises((FrozenInstanceError,AttributeError)):setattr(value,field,None)
            summary=result.to_dict();summary["cases"][0]["authored_dimensions"][0]=99;summary["stages"].clear()
            self.assertNotEqual(result.to_dict()["cases"][0]["authored_dimensions"][0],99)
            self.assertEqual(len(result.to_dict()["stages"]),4)
            for key in ("profile_qualified","originals_authenticated","runtime_authorized"):self.assertIs(result.to_dict()[key],False)
            self.assertFalse(any("token_ids" in str(k) or "geometry" in str(k) for k in result.to_dict()))

        def test_module_has_only_closed_stdlib_imports_no_filesystem_ports(self):
            tree=ast.parse(SOURCE.read_text(encoding="utf-8"));imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
                elif isinstance(node,ast.ImportFrom):imports.append(node.module)
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):self.assertNotIn(node.func.id,("open","exec","eval","compile","__import__"))
            self.assertEqual(set(imports),{"dataclasses","hashlib","json","re","struct"})

    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    stable=before=={str(path):pin(path) for path in paths}
    record=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),status="passed" if result.wasSuccessful() and stable else "failed",
        source=pin(SOURCE),checker=pin(Path(__file__)),inputs=before,inputs_unchanged=stable,methods=result.testsRun,counts=counts,
        failures=[dict(test=str(t),traceback=trace) for t,trace in result.failures],errors=[dict(test=str(t),traceback=trace) for t,trace in result.errors],
        elapsed_seconds=time.monotonic()-started,in_memory_new_pack=dict(bytes=len(packed),sha256=hashlib.sha256(packed).hexdigest(),persisted=False),
        scope="Captured NEW source metadata and in-memory pack consistency only; literal fragment interoperability plus independent field inspection, not encoder/decoder agreement alone.",
        profile_qualified=False,originals_authenticated=False,runtime_authorized=False,old_original_source_qualification=False,
        CPU_GGUF_oldpack_operations=0,SDK_native_compiler_operations=0,persisted_complete_pack=False)
    with PROOF.open("x",encoding="utf-8") as out:json.dump(record,out,sort_keys=True,indent=2);out.write("\n")
    print(json.dumps(dict(proof=pin(PROOF),status=record["status"],methods=result.testsRun,counts=counts)))
    return 0 if record["status"]=="passed" else 1


if __name__=="__main__":raise SystemExit(main())
