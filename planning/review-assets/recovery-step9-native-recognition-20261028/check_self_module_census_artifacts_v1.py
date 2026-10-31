"""Own-output artifact/argv/unbound-gate checks; no real SDK instance or experiment."""
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
SOURCE=HERE/"run_self_module_census_v1.py"
REPORT=HERE/"SELF-MODULE-CENSUS-ARTIFACT-PURE-PROOF-v1.json"
ROOT=HERE.parents[2]/"data/cache"/("r09-census-artifacts-pure-"+str(time.time_ns()))
ROOT.mkdir()
DENIED,FIXTURES=[],[]


def guard(event,args):
    if event in ("subprocess.Popen","os.system","ctypes.dlopen") or event.startswith("socket."):
        DENIED.append(event);raise RuntimeError("Artifact tests cannot construct SDK/load/connect/dispatch")
    if event=="open" and args and isinstance(args[0],(str,bytes)) and "neveropen" in str(args[0]).lower():
        DENIED.append("reported_image_open");raise RuntimeError("Reported module path is data only")


sys.addaudithook(guard)
def load(name,path):
    spec=util.spec_from_file_location(name,path);module=util.module_from_spec(spec);spec.loader.exec_module(module);return module
h=load("source_only_census_parent_for_artifacts",SOURCE)
f=load("authored_census_fixture_for_artifacts",HERE/"census_fixture_v1.py")
EXE=ROOT/"authored-not-an-executable.exe"
EXE.write_bytes(b"Own synthetic executable data; never dispatched or parsed as PE")


def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def fixture(name):
    child=ROOT/name;child.mkdir()
    item=f.make_census_fixture(pid=20,executable=str(EXE),runtime=str(h.RUNTIME))
    (child/"attempt.json").write_bytes(item["attempt_raw"])
    (child/"result.jsonl").write_bytes(b"".join(item["raw_lines"]))
    return child,item


def remember(name,path):
    FIXTURES.append(dict(case=name,root=str(path),files=[pin(p) for p in sorted(path.rglob("*")) if p.is_file()]))


class Checks(unittest.TestCase):
    def test_positive_census_is_observational_and_owned_PID_is_required(self):
        child,item=fixture("positive")
        with patch.object(h,"EXE",EXE):
            result=h.validate_child_artifacts(child,expected_pid=20)
            self.assertEqual(result["status"],h.STATUS)
            self.assertFalse(result["ABI_eligibility_established"])
            with self.assertRaises(Exception):h.validate_child_artifacts(child,expected_pid=21)
        remember("positive",child)

    def test_all_child_cap_is_checked_before_content_read(self):
        child,item=fixture("cap-before-read")
        size=2097152-len(item["attempt_raw"])
        with (child/"result.jsonl").open("r+b") as stream:stream.truncate(size)
        self.assertEqual(h.inspect_child_artifact_bounds(child)["total_bytes"],2097152)
        with (child/"result.jsonl").open("r+b") as stream:stream.truncate(size+1)
        with patch.object(Path,"read_bytes",side_effect=AssertionError("No content read after cap")):
            with self.assertRaisesRegex(RuntimeError,"structured census byte cap"):
                h.validate_child_artifacts(child,expected_pid=20)
        remember("cap-before-read",child)

    def test_reserve_and_unexpected_entries_reject(self):
        child,item=fixture("failure-reserve")
        (child/"result.jsonl").unlink()  # Own test fixture only, never an experiment artifact.
        with (child/"failure.json").open("wb") as stream:stream.truncate(65536-len(item["attempt_raw"]))
        self.assertEqual(h.inspect_child_artifact_bounds(child)["total_bytes"],65536)
        with (child/"failure.json").open("r+b") as stream:stream.truncate(65537-len(item["attempt_raw"]))
        with self.assertRaisesRegex(RuntimeError,"reserve bound"):h.inspect_child_artifact_bounds(child)
        remember("failure-reserve",child)
        child,item=fixture("unexpected")
        (child/"not-a-census-file.bin").write_bytes(b"own unapproved entry")
        with self.assertRaisesRegex(RuntimeError,"Unexpected census child entry"):h.inspect_child_artifact_bounds(child)
        remember("unexpected",child)

    def test_entry_guard_precedes_content_and_directory_is_not_file(self):
        child,item=fixture("entry-guard")
        original=h.safe;seen=[]
        def deny_entry(path,**kwargs):
            seen.append(str(path))
            if Path(path).name=="result.jsonl":raise RuntimeError("Synthetic reparse entry rejected")
            return original(path,**kwargs)
        with patch.object(h,"safe",side_effect=deny_entry),patch.object(Path,"read_bytes",side_effect=AssertionError("No contents")):
            with self.assertRaisesRegex(RuntimeError,"reparse entry"):h.validate_child_artifacts(child,expected_pid=20)
        self.assertIn(str(child/"result.jsonl"),seen)
        remember("entry-guard",child)
        child,item=fixture("directory-entry")
        (child/"result.jsonl").unlink();(child/"result.jsonl").mkdir()
        with self.assertRaisesRegex(RuntimeError,"regular non-reparse"):h.inspect_child_artifact_bounds(child)
        remember("directory-entry",child)

    def test_wrong_attempt_failed_marker_and_unterminated_result_cannot_pass(self):
        for kind in ("mode","marker","newline"):
            child,item=fixture("invalid-"+kind)
            if kind=="mode":
                attempt=dict(item["attempt"],mode="--abi");(child/"attempt.json").write_bytes(f.encoded(attempt))
            elif kind=="marker":(child/"failure.json").write_bytes(b'{"status":"failed"}\n')
            else:(child/"result.jsonl").write_bytes(b"".join(item["raw_lines"])[:-1])
            with patch.object(h,"EXE",EXE),self.assertRaises(Exception):h.validate_child_artifacts(child,expected_pid=20)
            remember("invalid-"+kind,child)

    def test_stdout_has_distinct_metadata_only_status_and_cap(self):
        output=ROOT/"stdout";output.mkdir();path=output/"stdout.bin"
        path.write_bytes(f.encoded(h.wire_schema()["stdout_success"]))
        h.validate_success_stdout(path)
        for raw in (b'{"status":"ABI_eligible"}\n',b'{"status":"x","status":"x"}\n',b"",b"x"*65537):
            path.write_bytes(raw)
            with self.assertRaises(Exception):h.validate_success_stdout(path)
        remember("stdout",output)

    def test_unbound_authority_prepare_and_exact_argv_stay_closed(self):
        self.assertFalse(h.EXECUTION_ENABLED)
        self.assertIsNone(h.EXE);self.assertIsNone(h.VERIFIED_BUILD);self.assertIsNone(h.EXECUTION_AUTHORITY);self.assertIsNone(h.PROTOCOL)
        with patch.object(h,"sha",side_effect=AssertionError("Unbound guard must precede eligibility reads")):
            with self.assertRaisesRegex(RuntimeError,"unbound"):h.authority()
        with self.assertRaisesRegex(RuntimeError,"Source/pure-only"):h.prepare()
        child=ROOT/"future-child"
        with patch.object(h,"EXE",EXE):
            argv,command=h.census_argv(EXE,h.RUNTIME,child)
            self.assertEqual(argv[1],"--module-census");self.assertEqual(len(argv),4)
            with self.assertRaises(Exception):h.census_argv(ROOT/"wrong.exe",h.RUNTIME,child)
            with self.assertRaises(Exception):h.census_argv(EXE,ROOT/"wrong-runtime",child)
            with self.assertRaises(Exception):h.census_argv(EXE,h.RUNTIME,str(child)+"\0")
        self.assertFalse(h.sdk.NATIVE_EXECUTION_ENABLED)


if __name__=="__main__":
    if REPORT.exists():raise RuntimeError("Preserve existing proof")
    original=pin(SOURCE)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert pin(SOURCE)==original,"Frozen census parent changed"
    value=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",tests=result.testsRun,
        failures=[str(c) for c,_ in result.failures],errors=[str(c) for c,_ in result.errors],
        source=original,checker=pin(Path(__file__)),validator=pin(h.VALIDATOR_SOURCE),wire=pin(h.WIRE),
        status_sealer=pin(h.SEALER_SOURCE),fixtures=FIXTURES,denied_real_operations=DENIED,
        actual_SDK_constructors=0,actual_children=0,reported_image_file_opens=0,
        scope="Source-only v1 artifact/argv/unbound-gate tests, not future authority closure qualification; v1 remains blocked")
    with REPORT.open("x",encoding="utf-8") as stream:json.dump(value,stream,sort_keys=True,indent=2);stream.write("\n")
    print(json.dumps(dict(proof=str(REPORT),sha256=pin(REPORT)["sha256"],fixtures=len(FIXTURES))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
