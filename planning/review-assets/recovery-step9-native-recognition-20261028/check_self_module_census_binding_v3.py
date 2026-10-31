"""Acyclic metadata binding/role checks; no constructor, child or candidate protocol."""
import ast
import copy
import ctypes  # stdlib declarations before no-dlopen guard.
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"run_self_module_census_v3.py"
OLD=HERE/"run_self_module_census_v1.py"
REPORT=HERE/"SELF-MODULE-CENSUS-BINDING-PURE-PROOF-v3.json"
ROOT=HERE.parents[2]/"data/cache"/("r09-census-binding-pure-"+str(time.time_ns()))
ROOT.mkdir()
DENIED,VECTORS,PUBLICATION_FIXTURES=[],[],[]


def guard(event,args):
    if event in ("subprocess.Popen","os.system","ctypes.dlopen") or event.startswith("socket."):
        DENIED.append(event);raise RuntimeError("Binding checks cannot construct/load/connect/dispatch")
    if event=="open" and args and isinstance(args[0],(str,bytes)) and str(args[0]).casefold().endswith("apphelp.dll"):
        DENIED.append("reported_image_open");raise RuntimeError("Reported unknown image is not a static input")


sys.addaudithook(guard)
spec=util.spec_from_file_location("bound_census_metadata_for_pure",SOURCE)
h=util.module_from_spec(spec);spec.loader.exec_module(h)


def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


STATIC=json.loads(h.EXECUTION_AUTHORITY.read_bytes())["static_inputs"]
def fake_evidence(name):
    path=ROOT/(name+".json")
    path.write_text(json.dumps(dict(status="passed",helper_sha256=h.sha(SOURCE),checker_sha256=h.sha(Path(__file__)),
                                  actual_children=0,actual_SDK_constructors=0)),encoding="utf-8")
    return path


class Checks(unittest.TestCase):
    def test_static_manifest_is_exact_and_non_self_referential(self):
        value=h.authority();h.validate_static_records(value["static_inputs"])
        self.assertEqual(len(STATIC),179)
        self.assertEqual(set(h.STATIC_PATHS),{r["path"] for r in STATIC})
        self.assertFalse(set(h.STATIC_PATHS)&{str(p) for p in h.dynamic_paths()})
        self.assertNotIn(str(h.PROTOCOL),h.STATIC_PATHS)
        self.assertNotIn(h.sha(SOURCE),h.EXECUTION_AUTHORITY.read_text(encoding="utf-8"))
        self.assertFalse(value["execution_authorized"]);self.assertFalse(value["ABI_eligibility_established"])
        VECTORS.append("acyclic-static-body")

    def test_exact_static_schema_universe_rejects_before_any_leaf_read(self):
        variants=[]
        variants.append(("missing",copy.deepcopy(STATIC[:-1])))
        variants.append(("extra",copy.deepcopy(STATIC)+[dict(path=str(ROOT/"extra.json"),bytes=0,sha256="0"*64)]))
        for name,path in (("self",str(SOURCE)),("authority",str(h.EXECUTION_AUTHORITY)),("proof",str(h.PURE)),
                          ("checker",str(h.CHECKER)),("protocol",str(h.PROTOCOL)),("output",str(ROOT/"future-output.json")),
                          ("unknown_image",r"C:\Windows\System32\apphelp.dll"),
                          ("arbitrary_text",str(ROOT/"arbitrary.json"))):
            records=copy.deepcopy(STATIC);records[0]["path"]=path;variants.append((name,records))
        records=copy.deepcopy(STATIC);records[1]=copy.deepcopy(records[0]);variants.append(("duplicate",records))
        for field,value in (("bytes",True),("bytes",-1),("sha256","g"*64),("sha256","A"*64),("path",True)):
            records=copy.deepcopy(STATIC);records[0][field]=value;variants.append(("malformed-"+field,records))
        records=copy.deepcopy(STATIC);records[0]["extra"]=None;variants.append(("extra-field",records))
        with patch.object(h,"pin",side_effect=AssertionError("Scope validation must precede leaf reads")):
            for name,records in variants:
                with self.subTest(name=name),self.assertRaises(RuntimeError):h.validate_static_records(records)
                VECTORS.append("static-"+name)

    def test_direct_and_indirect_dynamic_collision_cannot_enter_static_body(self):
        for path in h.dynamic_paths():
            records=copy.deepcopy(STATIC);records[0]["path"]=str(path)
            paths=list(h.STATIC_PATHS);paths[0]=str(path)
            with patch.object(h,"STATIC_PATHS",tuple(paths)),patch.object(h,"pin",side_effect=AssertionError("No read on cycle")):
                combined=records+[dict(path=str(p),bytes=0,sha256="0"*64) for p in h.dynamic_paths()]
                with self.assertRaisesRegex(RuntimeError,"cycle"):h.validate_inputs(combined,records)
            VECTORS.append("collision-"+path.name)

    def test_static_current_bytes_are_rechecked_despite_manifest_status(self):
        target=STATIC[0]["path"];original=h.pin;calls=[]
        def changed(path):
            calls.append(str(path))
            value=original(path)
            if str(path)==target:value["sha256"]="0"*64
            return value
        with patch.object(h,"PURE",fake_evidence("fresh-read")),patch.object(h,"pin",side_effect=changed):
            with self.assertRaisesRegex(RuntimeError,"Current static input differs"):h.collect_inputs()
        self.assertIn(target,calls);VECTORS.append("fresh-hash-not-serialized-status")

    def test_dynamic_evidence_is_separate_and_current_bytes_checked(self):
        evidence=fake_evidence("positive")
        with patch.object(h,"PURE",evidence):
            records=h.collect_inputs()
            self.assertEqual(len(records),183)
            self.assertEqual(h.validate_inputs(records,STATIC),records)
            self.assertEqual({r["path"] for r in records}-{r["path"] for r in STATIC},{str(p) for p in h.dynamic_paths()})
            evidence.write_bytes(b'{"status":"changed after pin"}\n')
            with self.assertRaisesRegex(RuntimeError,"Dynamic"):h.validate_inputs(records,STATIC)
        VECTORS.append("dynamic-current-byte-check")

    def test_malformed_dynamic_and_static_pins_cannot_enter_role(self):
        with patch.object(h,"PURE",fake_evidence("malformed")):
            records=STATIC+[h.pin(path) for path in h.dynamic_paths()]
            for field,value in (("bytes",True),("bytes",-1),("sha256","z"*64),("sha256","0"*63)):
                bad=copy.deepcopy(records);bad[-1][field]=value
                with self.assertRaises(RuntimeError):h.validate_inputs(bad,STATIC)
                VECTORS.append("dynamic-malformed-"+field)
            bad=copy.deepcopy(records);bad[-1]["extra"]=0
            with self.assertRaises(RuntimeError):h.validate_inputs(bad,STATIC)
            bad=copy.deepcopy(records);bad[0]["sha256"]="0"*64
            with self.assertRaisesRegex(RuntimeError,"Static pin differs"):h.validate_inputs(bad,STATIC)
            bad=copy.deepcopy(records);bad.append(dict(path=str(ROOT/"unreviewed.py"),bytes=0,sha256="0"*64))
            with self.assertRaises(RuntimeError):h.validate_inputs(bad,STATIC)

    def test_exact_census_role_rejects_ABI_recognition_and_scope_mutations(self):
        with patch.object(h,"PURE",fake_evidence("roles")):
            records=STATIC+[h.pin(path) for path in h.dynamic_paths()]
            config=h.configuration(ROOT/"future-run",records)
            self.assertEqual(h.validate_role(config),ROOT/"future-run")
            self.assertFalse(config["execution_authorized_by_preparation"])
            for field,value in (("mode","--abi"),("mode","--recognize"),("ABI_eligibility_established",True),
                                ("explicit_target_C_calls",1),("target_export_resolution",1),("maximum_attempts",2),
                                ("automatic_retry",True),("execution_authorized_by_preparation",True)):
                bad=copy.deepcopy(config);bad[field]=value
                with self.assertRaises(RuntimeError):h.validate_role(bad)
                VECTORS.append("role-"+field)
            for index,value in ((0,str(ROOT/"wrong.exe")),(1,"--abi"),(2,str(ROOT/"arbitrary-runtime"))):
                bad=copy.deepcopy(config);bad["argv"][index]=value
                with self.assertRaises(RuntimeError):h.validate_role(bad)
                VECTORS.append("argv-"+str(index))

    def test_accepted_runtime_and_declaration_provenance_are_explicit(self):
        paths=set(h.STATIC_PATHS)
        self.assertIn(str(h.q.DEFAULT),paths);self.assertIn(str(h.q.BASE),paths)
        self.assertIn(str(h.q.DEFAULT.parent.parent/"pyvenv.cfg"),paths)
        self.assertIn(str(h.CLASSIFICATION_METADATA),paths)
        package=[p for p in paths if "\\Lib\\site-packages\\asof\\" in p]
        dist=[p for p in paths if ".dist-info\\" in p]
        sdk=[p for p in paths if "\\Windows Kits\\10\\Include\\" in p]
        self.assertEqual((len(package),len(dist),len(sdk)),(85,3,6))
        self.assertEqual(len([p for p in paths if p.lower().endswith(".dll")]),20)
        self.assertFalse(any(p.lower().endswith((".gguf",".pyd",".obj",".lib")) for p in paths))
        self.assertFalse(any(Path(p).name.lower() in ("cl.exe","link.exe","apphelp.dll","ggml-cpu-x64.dll") for p in paths))
        VECTORS.append("finite-selected-provenance-only")

    def test_full_prepare_publishes_protocol_and_cache_report(self):
        self.assertTrue(h.PREPARATION.is_relative_to(h.ROOT/"data/cache"))
        protocol=ROOT/"full-prepare-protocol.json";report=ROOT/"full-prepare-report.json"
        evidence=fake_evidence("full-prepare")
        with patch.object(h,"PURE",evidence),patch.object(h,"PROTOCOL",protocol),patch.object(h,"PREPARATION",report):
            h.prepare()
        self.assertTrue(protocol.is_file());self.assertTrue(report.is_file())
        value=json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(value["protocol"],pin(protocol))
        self.assertEqual(value["status"],"prepared_census_only_not_execution_authority")
        self.assertFalse(value["execution_authorized"]);self.assertTrue(value["output_absent"])
        self.assertEqual(value["actual_SDK_constructors"],0);self.assertEqual(value["actual_children"],0)
        PUBLICATION_FIXTURES.append(dict(case="full_prepare",protocol=pin(protocol),report=pin(report)))
        VECTORS.append("full-prepare-both-exclusive-publications")

    def test_report_write_failure_preserves_protocol_and_blocks_repeat(self):
        protocol=ROOT/"fault-prepare-protocol.json";report=ROOT/"fault-prepare-report.json"
        evidence=fake_evidence("fault-prepare")
        original=h.write_new
        def fail(path,value):
            if Path(path)==report:raise OSError("Synthetic report publication failure")
            return original(path,value)
        with patch.object(h,"PURE",evidence),patch.object(h,"PROTOCOL",protocol),patch.object(h,"PREPARATION",report),patch.object(h,"write_new",side_effect=fail):
            with self.assertRaisesRegex(OSError,"Synthetic report"):h.prepare()
            before=protocol.read_bytes()
            with self.assertRaisesRegex(RuntimeError,"already consumed"):h.prepare()
        self.assertTrue(protocol.is_file());self.assertFalse(report.exists())
        self.assertEqual(protocol.read_bytes(),before)
        PUBLICATION_FIXTURES.append(dict(case="report_publication_failure",protocol=pin(protocol),report_absent=True,repeat_rejected=True))
        VECTORS.append("failed-report-preserves-protocol-no-automatic-repeat")

    def test_existing_mechanics_and_all_pure_evidence_remain_bound(self):
        before={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(OLD.read_bytes()).body if isinstance(n,ast.FunctionDef)}
        now={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(SOURCE.read_bytes()).body if isinstance(n,ast.FunctionDef)}
        names=("execute","api_class","terminal_observer","census_sealer","census_validator","validate_child_artifacts",
               "inspect_child_artifact_bounds","validate_success_stdout","census_argv","wire_schema","json_value","exact","runtime_pins","sha")
        for name in names:self.assertEqual(now[name],before[name],name)
        for filename,digest in (("SELF-MODULE-CENSUS-PARENT-PURE-PROOF-v1.json","37a4e859555d16ad523b936ba2356b592b190d0640b100cb5b66adadd9dcf542"),
                               ("SELF-MODULE-CENSUS-ARTIFACT-PURE-PROOF-v1.json","4305c7a17d879be3ecf5a051c21966e2ff0032c7614eb87f92b6b8a37dee9a39"),
                               ("SELF-MODULE-CENSUS-VALIDATION-PURE-PROOF-v1.json","7f48713863e7345a48ef159d0c6c4c70737139a43a0636a025ab6253320af31b"),
                               ("SELF-MODULE-CENSUS-SEALER-PURE-PROOF-v1.json","5c7b65641baf9a518d8672cb0395fe0014297ceb507f14e0a5cd6faeaad68e1b")):
            self.assertEqual(pin(HERE/filename)["sha256"],digest)
        self.assertFalse(h.sdk.NATIVE_EXECUTION_ENABLED)
        VECTORS.append("14-runtime-functions-and-prior33-methods-reused")


if __name__=="__main__":
    if REPORT.exists():raise RuntimeError("Preserve prior proof")
    original=pin(SOURCE)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert pin(SOURCE)==original,"Bound parent source changed during pure checks"
    value=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",tests=result.testsRun,
        failures=[str(c) for c,_ in result.failures],errors=[str(c) for c,_ in result.errors],vector_labels=VECTORS,
        helper_sha256=original["sha256"],checker_sha256=pin(Path(__file__))["sha256"],helper=original,
        static_authority=pin(h.EXECUTION_AUTHORITY),static_inputs=179,combined_inputs_after_real_proof=183,
        old_parent=pin(OLD),unchanged_mechanics_functions=14,actual_children=0,actual_SDK_constructors=0,
        actual_execution_protocols_created=0,denied_real_operations=DENIED,publication_fixtures=PUBLICATION_FIXTURES,
        scope="Acyclic binding and census role; source-identical v1 mechanics. Full prepare tests use private patched cache paths/current-proof fixtures; no actual candidate protocol, constructor or child is created")
    with REPORT.open("x",encoding="utf-8") as stream:json.dump(value,stream,sort_keys=True,indent=2);stream.write("\n")
    print(json.dumps(dict(proof=str(REPORT),sha256=pin(REPORT)["sha256"],vectors=len(VECTORS))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
