"""Adversarial data-only ABI result checks; no launcher import or API call."""
import ast
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import time
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / "run_detached_abi_observation_v1.py"
CONTRACT = HERE / "DETACHED-ABI-EXECUTION-CONTRACT-v1.json"
CONTRACT_SHA = "2be3241b97ca3a4f0f237ebb6cbcff4884366f37d10303608c09366c4e709457"
REPORT = HERE / "DETACHED-ABI-RESULTS-ADVERSARIAL-PROOF-v1.json"
COMPONENTS = ("sha", "authority", "exact", "json_value", "runtime_pins", "validate_modules", "validate_child_artifacts")
RAW = SOURCE.read_bytes()
SOURCE_SHA = hashlib.sha256(RAW).hexdigest()
TREE = ast.parse(RAW.decode("utf-8"))
NODES = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in COMPONENTS]
assert {node.name for node in NODES} == set(COMPONENTS)
CONTRACT_RAW = CONTRACT.read_bytes()
assert hashlib.sha256(CONTRACT_RAW).hexdigest() == CONTRACT_SHA
SPEC = json.loads(CONTRACT_RAW)
SDK_SOURCE = Path(SPEC["sdk"]["path"])
SDK_RAW = SDK_SOURCE.read_bytes()
assert hashlib.sha256(SDK_RAW).hexdigest() == SPEC["sdk"]["sha256"]
SAFE = next(node for node in ast.parse(SDK_RAW.decode("utf-8")).body
            if isinstance(node, ast.FunctionDef) and node.name == "safe")
BUILD = json.loads(Path(SPEC["build_protocol"]["path"]).read_bytes())
SYSTEM_NAMES = {name.casefold() for name in SPEC["System32_candidate_names"]}
SYSTEM_PINS = {item["path"]: item for item in BUILD["inputs"]
               if Path(item["path"]).parent == Path(r"C:\Windows\System32")
               and Path(item["path"]).name.casefold() in SYSTEM_NAMES}
assert len(SYSTEM_PINS) == 16


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


NS = dict(Path=Path, json=json, os=os, hashlib=hashlib, math=math, stat=stat,
          ROOT=ROOT, require=require, pin=pin,
          EXE=Path(SPEC["bridge_executable"]["path"]), EXE_SHA=SPEC["bridge_executable"]["sha256"],
          RUNTIME=Path(SPEC["runtime_pins"][0]["path"]).parent,
          RUNTIME_EXPECTED={Path(item["path"]).name: {k: item[k] for k in ("bytes", "sha256")}
                            for item in SPEC["runtime_pins"]},
          SYSTEM_PINS=SYSTEM_PINS, _system_names=SYSTEM_NAMES,
          CONTRACT=CONTRACT, CONTRACT_SHA=CONTRACT_SHA,
          DESIGN=HERE/"DETACHED-ABI-EXECUTION-CHECKLIST-v1.md",
          DESIGN_SHA="eea8e52dbc55215039fa5ee78305a0ac823c2d008a1626a961b8c5d78e415806",
          QUALIFICATION=Path(SPEC["harmless_prerequisite"]["path"]),
          QUALIFICATION_SHA=SPEC["harmless_prerequisite"]["sha256"],
          q=types.SimpleNamespace(SDK_SOURCE=SDK_SOURCE), SDK_SHA=SPEC["sdk"]["sha256"],
          BUILD_PROTOCOL=Path(SPEC["build_protocol"]["path"]),
          BUILD_PROTOCOL_SHA=SPEC["build_protocol"]["sha256"])
exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(SAFE), *copy.deepcopy(NODES)],
                                                 type_ignores=[])), str(SOURCE)+"::<pure AST only>", "exec"), NS)


def valid_rows():
    """Independent contract-based fixture, including all 16 permitted system paths."""
    paths = [str(NS["EXE"]), *[item["path"] for item in SPEC["runtime_pins"]], *SYSTEM_PINS]
    return [
        dict(event=SPEC["child_artifacts"]["result_events"][0], dependency_native_initialization_possible=True),
        dict(event=SPEC["child_artifacts"]["result_events"][1],
             modules=[dict(name=Path(path).name, path=path) for path in paths],
             layouts=copy.deepcopy(SPEC["expected_layouts"])),
        dict(event=SPEC["child_artifacts"]["result_events"][2], version="synthetic-ABI-observation",
             defaults=copy.deepcopy(SPEC["expected_defaults"]), no_backend_or_model_call_so_far=True),
        dict(event=SPEC["child_artifacts"]["result_events"][3], version_expected_previously_known=False,
             backend_init_called=False, registry_called=False, model_called=False,
             scope="typed version/defaults observation; independent ABI acceptance pending"),
        dict(event=SPEC["child_artifacts"]["result_events"][4], mode="--abi", elapsed_ms=0,
             parent_qualification_required=True),
    ]


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def make_valid_child(child: Path):
    """Write synthetic artifacts only; callable by the separate fake lifecycle checker."""
    child = NS["safe"](Path(child), output=True)
    child.mkdir(parents=True, exist_ok=True)
    require(not any(child.iterdir()), "Synthetic fixture child must be empty")
    rows = valid_rows()
    with (child/"attempt.json").open("xb") as stream:
        stream.write(encode(SPEC["child_artifacts"]["exact_attempt_claim"]) + b"\n")
    with (child/"result.jsonl").open("xb") as stream:
        stream.write(b"\n".join(encode(row) for row in rows) + b"\n")
    return rows


VECTORS = []
DENIED = []
TEST_ROOT = None
COUNTER = 0


def guard(event, args):
    if event == "ctypes.dlopen" or event in ("subprocess.Popen", "os.system") or event.startswith("socket."):
        DENIED.append(event)
        raise AssertionError("Real operation forbidden in data-only check: " + event)


def nested_leaves(value, prefix=()):
    for key, item in value.items():
        if type(item) is dict:
            yield from nested_leaves(item, prefix+(key,))
        else:
            yield prefix+(key,), item


def at(value, keys):
    for key in keys[:-1]:
        value = value[key]
    return value, keys[-1]


class ResultTests(unittest.TestCase):
    def child(self):
        global COUNTER
        COUNTER += 1
        child = TEST_ROOT / str(COUNTER)
        rows = make_valid_child(child)
        return child, rows

    def write_rows(self, child, rows):
        (child/"result.jsonl").write_bytes(b"\n".join(encode(row) for row in rows)+b"\n")

    def rejected(self, label, mutate=None, raw=None, setup=None):
        child, rows = self.child()
        if mutate:
            mutate(rows)
        self.write_rows(child, rows)
        if raw:
            raw(child)
        if setup:
            with setup(child):
                with self.assertRaises((RuntimeError, ValueError, UnicodeError, OSError), msg=label):
                    NS["validate_child_artifacts"](child)
        else:
            with self.assertRaises((RuntimeError, ValueError, UnicodeError, OSError), msg=label):
                NS["validate_child_artifacts"](child)
        VECTORS.append(dict(vector=label, expected="reject", passed=True))

    def test_positive_and_boundary_controls(self):
        for version in ["v", " "*255]:
            child, rows = self.child(); rows[2]["version"] = version
            self.write_rows(child, rows)
            result = NS["validate_child_artifacts"](child)
            self.assertEqual(result["version"], version)
            VECTORS.append(dict(vector="version-boundary-"+str(len(version)), expected="accept", passed=True))
        child, rows = self.child(); rows[1]["modules"] = rows[1]["modules"][:5]
        self.write_rows(child, rows); NS["validate_child_artifacts"](child)
        VECTORS.append(dict(vector="five-required-module-minimum", expected="accept", passed=True))
        child, rows = self.child(); raw=(child/"attempt.json").read_bytes();(child/"attempt.json").write_bytes(raw+b" "*(4096-len(raw)))
        NS["validate_child_artifacts"](child)
        child, rows = self.child(); parts=[encode(row) for row in rows];parts[0]+=b" "*(65536-len(parts[0]));(child/"result.jsonl").write_bytes(b"\n".join(parts)+b"\n")
        NS["validate_child_artifacts"](child)
        VECTORS.extend([dict(vector=name,expected="accept",passed=True) for name in ["attempt-exact4096", "row-exact65536"]])

    def test_every_default_missing_wrong_type_and_value(self):
        self.assertEqual(len(SPEC["expected_defaults"]), 17)
        for key, value in SPEC["expected_defaults"].items():
            self.rejected("default-missing-"+key, lambda rows,k=key: rows[2]["defaults"].pop(k))
            wrong_type = int(value) if type(value) is bool else float(value)
            self.rejected("default-type-"+key, lambda rows,k=key,v=wrong_type: rows[2]["defaults"].__setitem__(k,v))
            wrong_value = not value if type(value) is bool else value+1
            self.rejected("default-value-"+key, lambda rows,k=key,v=wrong_value: rows[2]["defaults"].__setitem__(k,v))
        self.rejected("default-extra-key", lambda rows: rows[2]["defaults"].__setitem__("unapproved", False))

    def test_every_layout_size_offset_type_and_presence(self):
        for keys, value in nested_leaves(SPEC["expected_layouts"]):
            def change(rows, keys=keys, value=value, mode="value"):
                obj, key = at(rows[1]["layouts"], keys)
                if mode == "missing": obj.pop(key)
                else: obj[key] = value+1 if mode == "value" else float(value)
            for mode in ["value", "type", "missing"]:
                self.rejected("layout-"+mode+"-"+"/".join(keys), lambda rows,m=mode: change(rows,mode=m))
        self.rejected("layout-extra", lambda rows: rows[1]["layouts"].__setitem__("extra", 8))

    def test_version_completion_and_scope(self):
        for value in ["", "x"*256, "\n", "\x7f", "é", "\ud800", True, 1, None]:
            if value == "\ud800":
                self.rejected("version-lone-surrogate", raw=lambda child: (child/"result.jsonl").write_bytes((child/"result.jsonl").read_bytes().replace(b'synthetic-ABI-observation',b'\\ud800')))
            else:
                self.rejected("version-invalid-"+repr(value),lambda rows,v=value: rows[2].__setitem__("version",v))
        for value in [-1,30001,True,0.0,"0"]:
            self.rejected("completion-time-"+repr(value),lambda rows,v=value: rows[4].__setitem__("elapsed_ms",v))
        for index,key,value in [(0,"dependency_native_initialization_possible",1),(2,"no_backend_or_model_call_so_far",1),
                                (3,"model_called",True),(3,"backend_init_called",True),(3,"registry_called",True),
                                (3,"version_expected_previously_known",True),(4,"parent_qualification_required",1),(4,"mode","--recognize")]:
            self.rejected("scope-"+str(index)+"-"+key,lambda rows,i=index,k=key,v=value:rows[i].__setitem__(k,v))

    def test_event_sequence_and_exact_sets(self):
        for index in range(5):
            self.rejected("event-missing-"+str(index),lambda rows,i=index:rows.pop(i))
            self.rejected("event-duplicate-"+str(index),lambda rows,i=index:rows.insert(i,copy.deepcopy(rows[i])))
            self.rejected("event-extra-field-"+str(index),lambda rows,i=index:rows[i].__setitem__("extra",True))
        self.rejected("event-reordered",lambda rows:rows.__setitem__(slice(0,2),[rows[1],rows[0]]))
        self.rejected("event-nonobject",lambda rows:rows.__setitem__(0,[]))
        self.rejected("event-failed-child",lambda rows:rows[4].__setitem__("event","failed"))

    def test_modules_required_paths_duplicates_and_CPU(self):
        for index in range(5):
            self.rejected("module-missing-required-"+str(index),lambda rows,i=index:rows[1]["modules"].pop(i))
        for index in [0,1,5]:
            self.rejected("module-duplicate-"+str(index),lambda rows,i=index:rows[1]["modules"].__setitem__(i+1,copy.deepcopy(rows[1]["modules"][i])))
        for path in [str(NS["RUNTIME"]/"ggml-cpu-x64.dll"),r"D:\unapproved\llama.dll",r"C:\Windows\evil.dll","llama.dll"]:
            self.rejected("module-path-"+path,lambda rows,v=path:rows[1]["modules"].__setitem__(1,dict(name=Path(v).name,path=v)))
        self.rejected("module-name-mismatch",lambda rows:rows[1]["modules"][1].__setitem__("name","llama.dll"))
        self.rejected("module-extra-field",lambda rows:rows[1]["modules"][1].__setitem__("sha256","0"*64))
        self.rejected("module-noncanonical-dot",lambda rows:rows[1]["modules"][1].__setitem__("path",str(NS["RUNTIME"])+"\\.\\"+rows[1]["modules"][1]["name"]))
        self.rejected("module-too-many",lambda rows:rows[1]["modules"].append(copy.deepcopy(rows[1]["modules"][0])))

    def test_JSON_duplicates_nonfinite_and_file_caps(self):
        self.rejected("duplicate-root-key",raw=lambda child:(child/"result.jsonl").write_bytes((child/"result.jsonl").read_bytes().replace(b'"elapsed_ms":0',b'"elapsed_ms":0,"elapsed_ms":0')))
        self.rejected("duplicate-nested-key",raw=lambda child:(child/"result.jsonl").write_bytes((child/"result.jsonl").read_bytes().replace(b'"pointer":8',b'"pointer":8,"pointer":8')))
        for token in [b'NaN',b'Infinity',b'-Infinity',b'1e999']:
            self.rejected("nonfinite-child-"+token.decode(),raw=lambda child,t=token:(child/"result.jsonl").write_bytes((child/"result.jsonl").read_bytes().replace(b'"elapsed_ms":0',b'"elapsed_ms":'+t)))
        for name,count in [("attempt.json",4097),("result.jsonl",4194305)]:
            self.rejected("file-cap-"+name,raw=lambda child,n=name,c=count:(child/n).write_bytes(b'x'*c))
        self.rejected("row-cap",raw=lambda child:(child/"result.jsonl").write_bytes(b' '*65537+b'\n'+b'{}\n'*4))
        self.rejected("no-final-LF",raw=lambda child:(child/"result.jsonl").write_bytes((child/"result.jsonl").read_bytes().rstrip(b'\n')))
        self.rejected("blank-extra-row",raw=lambda child:(child/"result.jsonl").write_bytes((child/"result.jsonl").read_bytes()+b'\n'))
        for marker in ["failure.json","result.partial.jsonl","unapproved.txt"]:
            self.rejected("extra-file-"+marker,raw=lambda child,n=marker:(child/n).write_bytes(b'{}'))
        for key,value in [("draft",1),("mode","--recognize"),("schema_version",True)]:
            self.rejected("attempt-claim-"+key,raw=lambda child,k=key,v=value:(child/"attempt.json").write_bytes(encode({**SPEC["child_artifacts"]["exact_attempt_claim"],k:v})))

    def test_child_entries_reparse_rejected_before_read(self):
        original = Path.lstat
        for name in ["attempt.json","result.jsonl"]:
            def setup(child,name=name):
                target=child/name
                def lstat(path,*args,**kwargs):
                    if path==target:return types.SimpleNamespace(st_file_attributes=0x400,st_mode=stat.S_IFREG)
                    return original(path,*args,**kwargs)
                return mock.patch.object(Path,"lstat",lstat)
            self.rejected("mock-reparse-entry-"+name,setup=setup)

    def test_authority_missing_proof_fails_without_mutation(self):
        original=NS["sha"]
        for name in ["CONTRACT","DESIGN","QUALIFICATION","BUILD_PROTOCOL"]:
            child,rows=self.child();target=NS[name]
            NS["sha"]=lambda path,t=target: "0"*64 if Path(path)==t else original(path)
            try:
                with self.assertRaises(RuntimeError):NS["validate_child_artifacts"](child)
            finally:NS["sha"]=original
            VECTORS.append(dict(vector="authority-mismatch-"+name,expected="reject",passed=True))


if __name__ == "__main__":
    sys.addaudithook(guard)
    TEST_ROOT=ROOT/"data/cache"/("r09-detached-ABI-result-pure-"+str(time.time_ns()))
    TEST_ROOT.mkdir(exist_ok=False)
    started=time.monotonic();suite=unittest.defaultTestLoader.loadTestsFromTestCase(ResultTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA,"Parent changed during pure result check"
    components={node.name:hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest() for node in NODES}
    report=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        status="passed" if result.wasSuccessful() else "failed",scope="AST-extracted data-only validator vectors, not real ABI or launcher qualification",
        source=dict(path=str(SOURCE),sha256=SOURCE_SHA),contract=pin(CONTRACT),checker=pin(Path(__file__)),
        component_AST_sha256=components,safe_source=pin(SDK_SOURCE),
        tests=result.testsRun,failures=[str(case) for case,_ in result.failures],errors=[str(case) for case,_ in result.errors],
        vector_count=len(VECTORS),vectors=VECTORS,fixture_root=str(TEST_ROOT),elapsed_seconds=time.monotonic()-started,
        denied_real_operations=DENIED,activity=dict(SDK_API_calls=0,child_or_DLL_or_model_calls=0,CPU_DLL_or_GGUF_reads=0))
    with REPORT.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write("\n")
    print(json.dumps(dict(report=str(REPORT),sha256=pin(REPORT)["sha256"],vectors=len(VECTORS))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
