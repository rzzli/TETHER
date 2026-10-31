"""Named source correction from the first independent static finding; no build."""
from pathlib import Path
import hashlib
import json

base = Path(__file__).resolve().parent
source = base / "preflight_file14_raw_v1.c"
original = source.read_bytes()
expected = "a462fac861faf4149a36763c30f74441ac0df049a37c7a2e2e557828913188bc"
if hashlib.sha256(original).hexdigest() != expected:
    raise ValueError("Original C source changed")
before = b"(has_count(api) && (buffer_id==UINT32_MAX || requested>capacity)))"
after = b"(has_count(api) && (buffer_id==UINT32_MAX || requested==0 || requested>capacity)))"
if original.count(before) != 1:
    raise ValueError("Expected one exact initializer guard")
corrected = original.replace(before, after)
output = base / "preflight_file14_raw_v2.c"
with output.open("xb") as stream:
    stream.write(corrected)
record = dict(
    schema_version=1, status="NAMED_SOURCE_CORRECTION_NOT_BUILT_OR_EXECUTED",
    finding="Native peer's first static review: initializer accepted REQUESTED_PRESENT=true/requested0 for API6 or13, contrary to4cf7 typed_defaults' iff rule.",
    source_before=dict(path=str(source),bytes=len(original),sha256=expected),
    source_after=dict(path=str(output),bytes=len(corrected),sha256=hashlib.sha256(corrected).hexdigest()),
    change="Only add requested==0 refusal to the existing ReadFile/WriteFile initializer guard. Fourteen wrappers, shared header, layout, bounds and publication ordering are unchanged.",
    expected_regressions=["API6 requested0 returns PF14_INVALID with no target call", "API13 requested0 returns PF14_INVALID with no target call", "Positive request with returned count0 remains recorded raw count0, not positive progress"],
    preservation="V1 and its first static HOLD remain evidence. No observed run selected an expected result; neither C version is built/executed.",
    activity=dict(C_builds=0, native_or_SDK_calls=0, original_target_reads=0, subject_executions=0)
)
record_path = base / "NATIVE-CARRIER-REQUEST-CORRECTION-v2.json"
with record_path.open("x",encoding="utf-8") as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
if source.read_bytes() != original:
    raise ValueError("Preserved source changed")
print(json.dumps(record["source_after"]))
