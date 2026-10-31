"""First finite pure six-history implementation probe; retains every outcome."""
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import types

HERE=Path(__file__).resolve().parent
REVIEW=HERE.parent
STARTED=time.monotonic()
REPORT=HERE/"UNICODE-OBSERVATIONS-FIRST-IMPLEMENTATION-PROBE-v1.json"

def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def load(path,name,expected=None):
    raw=path.read_bytes()
    if expected is not None: assert hashlib.sha256(raw).hexdigest()==expected
    m=types.ModuleType(name); m.__file__=str(path); sys.modules[name]=m
    exec(compile(raw,str(path),"exec"),m.__dict__); return m

def check():
    if time.monotonic()-STARTED>20: raise TimeoutError("First probe20s")

assert not REPORT.exists()
load(REVIEW/"recovery-step9-utf8-oracle-20261029/strict_utf8_oracle_v1.py","strict_utf8_oracle_v1","4e5d36afa001339735a349a8ebab88a312cde1cb57fa43336e38ee4195134c21")
load(REVIEW/"recovery-step9-unicode-control-20261029/unicode_piece_analyzer_v1.py","unicode_piece_analyzer_v1","537a780a3d2d3b95d5fe4976cd8a073cf528db908badf3edf3e861e729ff8f9d")
codec=load(REVIEW/"recovery-step9-unicode-codec-20261029/unicode_pack_codec_v2.py","unicode_pack_codec_v2","8ff0d6228fbec2900d52125f2e94e311cc22762d2d0b8b52c3eaadf0e59be91a")
load(REVIEW/"recovery-step9-native-recognition-20261028/recognition_module_policy_v1.py","recognition_module_policy_v1","5031f2e3d1672684ef0d0dee1aa8370184cd8bc4df05042bfc135c1451f48f12")
load(HERE/"unicode_observation_tables_v1.py","unicode_observation_tables_v1","009e46ee19e945575472afb5105e88fe708a38b30c2f1014bbf8f6549d76786d")
source=HERE/"unicode_observations_v1.py"; helper=load(source,"unicode_observations_v1")
wire=REVIEW/"recovery-step9-unicode-wire-20261029"; control=REVIEW/"recovery-step9-unicode-control-20261029"
paths=dict(base_design=wire/"UNICODE-WIRE-DESIGN-CONTRACT-v2.json",framing_contract=wire/"UNICODE-WIRE-FRAMING-CONTRACT-v1.json",
    corpus=control/"UNICODE-CONTROL-CORPUS-v1.json",stages=control/"UNICODE-CONTROL-STAGES-v1.json",profile_contract=control/"UNICODE-CONTROL-CONTRACT-v2.json",
    analyzer_contract=control/"UNICODE-PIECE-ANALYZER-CONTRACT-v1.json")
profile=codec.make_profile(codec.SourceBytes(**{key:path.read_bytes() for key,path in paths.items()}),check=check)
fixture=HERE/"UNICODE-OBSERVATIONS-TRACE-FIXTURES-v2.json"; f=json.loads(fixture.read_bytes()); outcomes=[]
for base in f["base_traces"]:
    b=base["bindings"]
    bindings=helper.ObservationBindings(b["expected_child_pid"],b["expected_self"],b["expected_runtime"],
        tuple(helper.ShardDescriptor(**s) for s in b["ordered_shard_descriptors"]),b["expected_newpack_sha256"])
    try:
        result=helper.observe(bytes.fromhex(base["raw_hex"]),profile,bindings,
            failure_marker=None if base["failure_marker_hex"] is None else bytes.fromhex(base["failure_marker_hex"]),check=check)
        d=result.to_dict(); expected=base["expected_projection"]
        mismatches={key:dict(expected=value,actual=d.get(key)) for key,value in expected.items() if d.get(key)!=value or type(d.get(key)) is not type(value)}
        outcomes.append(dict(id=base["id"],status="passed" if not mismatches else "mismatch",mismatches=mismatches,
            classification=d["classification"],validated_rows=d["validated_rows"]))
    except BaseException as error:
        outcomes.append(dict(id=base["id"],status="error",error_class=type(error).__name__,error=str(error),
            detail=error.to_dict() if type(error) is helper.ObservationError else None,traceback=traceback.format_exc()))
report=dict(schema_version=1,status="passed" if all(o["status"]=="passed" for o in outcomes) else "failed",source=pin(source),
    fixture=pin(fixture),probe=pin(Path(__file__).resolve()),outcomes=outcomes,elapsed_seconds=time.monotonic()-STARTED,
    actual_native_calls=0,SDK_calls=0,payload_operations=0,pack_file_created=False,profile_qualified=False)
REPORT.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(dict(report=pin(REPORT),status=report["status"],outcomes=[{k:v for k,v in row.items() if k not in ("traceback","detail")} for row in outcomes])))
