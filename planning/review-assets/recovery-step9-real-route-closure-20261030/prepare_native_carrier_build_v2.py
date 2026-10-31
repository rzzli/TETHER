"""Coherent selected build preparation, metadata only; no build binding issued."""
from pathlib import Path
import hashlib
import json

base=Path(__file__).resolve().parent
root=base.parents[2]
def pin(path):
    item=Path(path)
    if not item.is_absolute():item=root/item
    raw=item.read_bytes()
    return dict(path=str(item.relative_to(root)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
old_path=base/"NATIVE-CARRIER-BUILD-PREPARATION-v1.json"
value=json.loads(old_path.read_text(encoding="utf-8"))
value["schema_version"]=2
value["supersedes_preparation"]=pin(old_path)
value["driver"]="build_native_carrier_component_v6.py"
value["selected_inputs"]={name:pin(base/file)for name,file in dict(
    source="preflight_file14_raw_v3.c",header="preflight_file14_raw_v1.h",
    tests="native_carrier_fake_tests_v1.c",expectations="NATIVE-CARRIER-FAKE-EXPECTATIONS-v1.json",
    test_preparation="NATIVE-CARRIER-FAKE-TEST-PREPARATION-v1.json",
    phase_clarification="NATIVE-CARRIER-PARTIAL-PHASE-CLARIFICATION-v1.json",
    driver="build_native_carrier_component_v6.py",
    cleanup_fake_regressions="NATIVE-CARRIER-BUILD-DRIVER-FAKE-REGRESSIONS-v2.json",
    journal_fake_regressions="NATIVE-CARRIER-BUILD-JOURNAL-FAKE-REGRESSIONS-v1.json",
    first_prebuild_hold="NATIVE-CARRIER-INDEPENDENT-PREBUILD-REVIEW-v1.json").items()}
value["proposed_build"]["clock_scope"]="Unchanged60s starts after input checks/exclusive reservation, through post-inventory eligibility. Same-start fresh pre/postPopen samples and2s cleanup reserve inside60. Final report construction/write and failure-only diagnostic tail excluded; no full-process fit claim."
value["proposed_build"]["failure"]="First command/error and raw partial outputs retained. Kill/reap failures and exit/pipe unknowns separate; no unbounded second communicate. Outer/inventory/report failure cannot return successful disposition. Journal acknowledges full append+close only; failed tail disables further appends. No retry, image dispatch or OS-wide descendant attestation."
value["selected_counts"]=dict(named_controls=79,semantic=46,malformed=22,initializer_negative=10,
    interrupted_error=1,planned_initializer_attempts=79,planned_wrapper_attempts=116,
    planned_fake_targets=47,planned_error_entries=17,planned_error_returns=16)
value["regression_boundary"]="Root trusted-helper fake controls only:4 subprocess controls plus3 emitter controls; no C builds/runs. V3/V6 subprocess AST is unchanged. These do not replace independent static review or later native execution."
value["independent_prebuild_closure"]=None
value["closure_reason"]="Final independentV6/sourceV3/79oracle/phase/preparation review must be retained and selected by the separate Root build binding. No compiler has run for this component."
output=base/"NATIVE-CARRIER-BUILD-PREPARATION-v2.json"
raw=(json.dumps(value,indent=2)+"\n").encode()
with output.open("xb")as stream:stream.write(raw)
print(json.dumps(dict(path=str(output),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())))
