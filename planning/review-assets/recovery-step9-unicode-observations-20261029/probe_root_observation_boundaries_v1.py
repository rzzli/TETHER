"""Two finite pure probes of the preserved first observer implementation.

The retained lexical matcher is reused as a single isolated pure dependency.
No original run, source closure, target, DLL, pack file or model is inspected.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
PINS = (
    ("recovery-step9-utf8-oracle-20261029/strict_utf8_oracle_v1.py", "strict_utf8_oracle_v1", "4e5d36afa001339735a349a8ebab88a312cde1cb57fa43336e38ee4195134c21"),
    ("recovery-step9-unicode-control-20261029/unicode_piece_analyzer_v1.py", "unicode_piece_analyzer_v1", "537a780a3d2d3b95d5fe4976cd8a073cf528db908badf3edf3e861e729ff8f9d"),
    ("recovery-step9-unicode-codec-20261029/unicode_pack_codec_v2.py", "unicode_pack_codec_v2", "8ff0d6228fbec2900d52125f2e94e311cc22762d2d0b8b52c3eaadf0e59be91a"),
    ("recovery-step9-native-recognition-20261028/recognition_module_policy_v1.py", "recognition_module_policy_v1", "5031f2e3d1672684ef0d0dee1aa8370184cd8bc4df05042bfc135c1451f48f12"),
    ("recovery-step9-unicode-observations-20261029/unicode_observation_tables_v1.py", "unicode_observation_tables_v1", "009e46ee19e945575472afb5105e88fe708a38b30c2f1014bbf8f6549d76786d"),
    ("recovery-step9-unicode-observations-20261029/unicode_observations_v1.py", "unicode_observations_v1", "58d6a62fe6a9416c94e5637b615886cecd90bc78ef1559f05f7d1d1ebd6e32c0"),
)
modules, inputs = {}, {}
for relative, name, expected in PINS:
    raw = (ASSETS / relative).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, name
    inputs[relative] = {"bytes": len(raw), "sha256": expected}
    module = types.ModuleType(name)
    module.__file__ = str(ASSETS / relative)
    sys.modules[name] = module
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    modules[name] = module
codec = modules["unicode_pack_codec_v2"]
observer = modules["unicode_observations_v1"]
control = ASSETS / "recovery-step9-unicode-control-20261029"
wire = ASSETS / "recovery-step9-unicode-wire-20261029"
sources = {
    "base_design": wire / "UNICODE-WIRE-DESIGN-CONTRACT-v2.json",
    "framing_contract": wire / "UNICODE-WIRE-FRAMING-CONTRACT-v1.json",
    "corpus": control / "UNICODE-CONTROL-CORPUS-v1.json",
    "stages": control / "UNICODE-CONTROL-STAGES-v1.json",
    "profile_contract": control / "UNICODE-CONTROL-CONTRACT-v2.json",
    "analyzer_contract": control / "UNICODE-PIECE-ANALYZER-CONTRACT-v1.json",
}
profile = codec.make_profile(codec.SourceBytes(**{key: path.read_bytes() for key, path in sources.items()}), check=lambda: None)
fixture_raw = (HERE / "UNICODE-OBSERVATIONS-TRACE-FIXTURES-v2.json").read_bytes()
assert hashlib.sha256(fixture_raw).hexdigest() == "cecd6aad28b91a526541ffc1694e5fa9e7c91749f8b920453316314319bf065b"
base = next(value for value in json.loads(fixture_raw)["base_traces"] if value["id"] == "complete_positive")
b = base["bindings"]
bindings = observer.ObservationBindings(b["expected_child_pid"], b["expected_self"], b["expected_runtime"],
    tuple(observer.ShardDescriptor(**value) for value in b["ordered_shard_descriptors"]), b["expected_newpack_sha256"])
outcomes = []

# Presence of a supplied marker is known even if the first row is malformed.
try:
    observer.observe(b'{"bad":true}\n', profile, bindings, failure_marker=b'not-json', check=lambda: None)
except observer.ObservationError as error:
    prefix = error.to_dict()["validated_prefix"]
    assert prefix["terminal_negative_seen"] is False
    outcomes.append({"id": "marker_presence_before_bad_completed_row", "reproduced": True,
        "reason": error.reason, "observed_terminal_negative_seen": False,
        "required_supplied_marker_presence": True, "success_returned": False})
else:
    raise AssertionError("Malformed completed row unexpectedly accepted")

# Test-local finalization-cost instrumentation: advance the caller's synthetic
# deadline during ordinary result freezing, without altering source bytes.
class SyntheticDeadline(TimeoutError):
    pass
stop = SyntheticDeadline("synthetic deadline crossed during final result freeze")
expired = False
calls = 0
def check():
    global calls
    calls += 1
    if expired:
        raise stop
original_issue = observer._issue
def delayed_issue(data):
    global expired
    result = original_issue(data)
    expired = True
    return result
observer._issue = delayed_issue
try:
    result = observer.observe(bytes.fromhex(base["raw_hex"]), profile, bindings, check=check)
    classification = result.to_dict()["classification"]
    assert expired and classification == "complete_success_consistent"
    outcomes.append({"id": "post_result_freeze_callback_missing", "reproduced": True,
        "classification_returned": classification, "synthetic_deadline_crossed_before_return": True,
        "required": "Invoke original check after issuing/freezing result; propagate the exact stop object instead of returning it.",
        "callback_calls_before_freeze": calls, "runtime_profile_qualified": False})
finally:
    observer._issue = original_issue

report = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "TWO_PURE_BOUNDARY_DEFECTS_REPRODUCED",
    "scope": "First implementation only; no source byte edits. Result-issue wrapper is test-local cost instrumentation, not a hostile-Python or real timing experiment.",
    "inputs": inputs, "outcomes": outcomes,
    "retained_pure_lexical_matcher_reused": True,
    "old_original_source_closure_qualified": False,
    "old_run_or_payload_operations": 0, "native_or_SDK_calls": 0,
    "profile_qualified": False,
}
output = HERE / "UNICODE-OBSERVATIONS-ROOT-BOUNDARY-BEFORE-v1.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": report["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
