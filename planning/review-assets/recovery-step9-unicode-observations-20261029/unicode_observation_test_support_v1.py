"""Explicit captured NEW-source loader/fictional materializer for pure tests."""
import hashlib
import json
from pathlib import Path
import sys
import time
import types

HERE=Path(__file__).resolve().parent
REVIEW=HERE.parent
STARTED=time.monotonic()
ACTIVE=[False]
DENIALS=[]


def budget():
    if time.monotonic()-STARTED>90: raise TimeoutError("Finite observation pure suite90s")


def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")


def load(path,name,expected):
    raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()==expected
    module=types.ModuleType(name); module.__file__=str(path); sys.modules[name]=module
    exec(compile(raw,str(path),"exec"),module.__dict__); return module


DEPENDENCIES=(
    (REVIEW/"recovery-step9-utf8-oracle-20261029/strict_utf8_oracle_v1.py","strict_utf8_oracle_v1","4e5d36afa001339735a349a8ebab88a312cde1cb57fa43336e38ee4195134c21"),
    (REVIEW/"recovery-step9-unicode-control-20261029/unicode_piece_analyzer_v1.py","unicode_piece_analyzer_v1","537a780a3d2d3b95d5fe4976cd8a073cf528db908badf3edf3e861e729ff8f9d"),
    (REVIEW/"recovery-step9-unicode-codec-20261029/unicode_pack_codec_v2.py","unicode_pack_codec_v2","8ff0d6228fbec2900d52125f2e94e311cc22762d2d0b8b52c3eaadf0e59be91a"),
    (REVIEW/"recovery-step9-native-recognition-20261028/recognition_module_policy_v1.py","recognition_module_policy_v1","5031f2e3d1672684ef0d0dee1aa8370184cd8bc4df05042bfc135c1451f48f12"),
    (HERE/"unicode_observation_tables_v1.py","unicode_observation_tables_v1","009e46ee19e945575472afb5105e88fe708a38b30c2f1014bbf8f6549d76786d"))
for path,name,expected in DEPENDENCIES: load(path,name,expected)
CODEC=sys.modules["unicode_pack_codec_v2"]
WIRE=REVIEW/"recovery-step9-unicode-wire-20261029"; CONTROL=REVIEW/"recovery-step9-unicode-control-20261029"
SOURCE_PATHS=dict(base_design=WIRE/"UNICODE-WIRE-DESIGN-CONTRACT-v2.json",framing_contract=WIRE/"UNICODE-WIRE-FRAMING-CONTRACT-v1.json",
    corpus=CONTROL/"UNICODE-CONTROL-CORPUS-v1.json",stages=CONTROL/"UNICODE-CONTROL-STAGES-v1.json",
    profile_contract=CONTROL/"UNICODE-CONTROL-CONTRACT-v2.json",analyzer_contract=CONTROL/"UNICODE-PIECE-ANALYZER-CONTRACT-v1.json")
PROFILE=CODEC.make_profile(CODEC.SourceBytes(**{key:path.read_bytes() for key,path in SOURCE_PATHS.items()}),check=budget)
FIXTURE=HERE/"UNICODE-OBSERVATIONS-TRACE-FIXTURES-v2.json"
assert pin(FIXTURE)["sha256"]=="cecd6aad28b91a526541ffc1694e5fa9e7c91749f8b920453316314319bf065b"
F=json.loads(FIXTURE.read_bytes()); BASES={base["id"]:base for base in F["base_traces"]}


def audit(event,args):
    if ACTIVE[0] and (event=="open" or event.startswith(("ctypes.","subprocess.","socket.")) or event in ("os.system","os.startfile")):
        DENIALS.append(event)
        raise RuntimeError("pure_observation_io_denied")


sys.addaudithook(audit)


def invoke(function,*args,**kwargs):
    ACTIVE[0]=True
    try: return function(*args,**kwargs)
    finally: ACTIVE[0]=False


def bindings(module,base=None):
    b=(base or BASES["complete_positive"])["bindings"]
    return module.ObservationBindings(b["expected_child_pid"],b["expected_self"],b["expected_runtime"],
        tuple(module.ShardDescriptor(**item) for item in b["ordered_shard_descriptors"]),b["expected_newpack_sha256"])


def capture(base):
    return bytes.fromhex(base["raw_hex"]),None if base["failure_marker_hex"] is None else bytes.fromhex(base["failure_marker_hex"])


def materialize(scenario):
    base=BASES[scenario["base_trace"]]; raw,marker=capture(base)
    lines=[line+b"\n" for line in raw[:-1].split(b"\n")]
    if scenario["prefix_rows"] is not None: lines=lines[:scenario["prefix_rows"]]
    for row in scenario["replace_rows"]: lines[row["index"]]=bytes.fromhex(row["raw_hex"])
    lines.extend(bytes.fromhex(item) for item in scenario["append_rows_hex"])
    raw=b"".join(lines)+bytes.fromhex(scenario["tail_hex"])
    assert len(raw)==scenario["materialized_bytes"] and hashlib.sha256(raw).hexdigest()==scenario["materialized_sha256"]
    if scenario["failure_marker"]!="inherit": marker=None if scenario["failure_marker"] is None else bytes.fromhex(scenario["failure_marker"])
    return raw,marker


def replace(index,edit):
    base=BASES["complete_positive"]; raw,_=capture(base)
    lines=[line+b"\n" for line in raw[:-1].split(b"\n")]
    row=json.loads(lines[index]); edit(row); lines[index]=canonical(row)+b"\n"
    return b"".join(lines)
