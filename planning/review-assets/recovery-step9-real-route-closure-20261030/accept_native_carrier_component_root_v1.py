"""Root finite compiled/fake-target acceptance, not a native route release."""
from pathlib import Path
import hashlib
import json

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
def pin(path):
    item=Path(path)
    if not item.is_absolute():item=ROOT/item
    raw=item.read_bytes()
    try:label=str(item.relative_to(ROOT))
    except ValueError:label=str(item)
    return dict(path=label,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
build_dir=ROOT/"data/cache/r09-native-carrier-component-build-20261030T055706Z"
run_dir=ROOT/"data/cache/r09-native-carrier-component-run-20261030T061649Z"
references=dict(
    build_result=pin(build_dir/"build-result.json"),run_result=pin(run_dir/"run-result.json"),
    compiled_artifact_review=pin(BASE/"NATIVE-CARRIER-INDEPENDENT-BUILD-ARTIFACT-REVIEW-v1.json"),
    actual_fake_review=pin(BASE/"NATIVE-CARRIER-FAKE-RUN-INDEPENDENT-ACTUAL-REVIEW-v1.json"),
    prebuild_review=pin(BASE/"NATIVE-CARRIER-INDEPENDENT-PREBUILD-REVIEW-v2.json"),
    runtime_static_review=pin(BASE/"NATIVE-CARRIER-RUNTIME-INDEPENDENT-STATIC-REVIEW-v4.json"),
    build_scope=pin(BASE/"NATIVE-CARRIER-COMPONENT-BUILD-SCOPE-v1.json"),
    build_binding=pin(BASE/"NATIVE-CARRIER-COMPONENT-BUILD-BINDING-v1.json"),
    run_scope=pin(BASE/"NATIVE-CARRIER-FAKE-RUN-SCOPE-v1.json"),
    run_binding=pin(BASE/"NATIVE-CARRIER-FAKE-RUN-BINDING-v1.json"),
    source=pin(BASE/"preflight_file14_raw_v3.c"),header=pin(BASE/"preflight_file14_raw_v1.h"),
    tests=pin(BASE/"native_carrier_fake_tests_v1.c"),expectations=pin(BASE/"NATIVE-CARRIER-FAKE-EXPECTATIONS-v1.json"))
expected={"build_result":"9275174036dfab54a50fea143cd3d547e5dbadd5e41af559d95b4eacbfc4fa8e",
          "run_result":"6167028f2285fbf491a79e73bbb07ae143b77dd4161f2e3f4e5e9935f3fc259c",
          "compiled_artifact_review":"5796bcc69efd666491baf3fdbc04b96c509f8c772173817370c3ca4b341d9cb4",
          "actual_fake_review":"1b10326d2e368708d876f67ba1f6e6a5eed47f2756766fa881d98fd83c67f33b"}
for key,value in expected.items():
    if references[key]["sha256"]!=value:raise ValueError("Exact selected result/review: "+key)
run=json.loads((run_dir/"run-result.json").read_text())
if run["status"]!="ALL_79_FAKE_TARGET_CONTROLS_PASSED"or run["failure"]or run["grade_error"]:raise ValueError("Actual C result not passed")
value=dict(schema_version=1,status="ACCEPTED_COMPILED_FAKE_TARGET_COMPONENT_ONLY",
    references=references,
    actual=dict(builds=1,build_commands=3,build_exits=[0,0,0],build_elapsed_seconds=1.047000000020489,
                generated_image_dispatches=1,fake_controls_passed=79,C_assertions_passed=29310,
                initializer_attempts=79,wrapper_attempts=116,fake_target_calls=47,
                last_error_entries=17,last_error_normal_returns=16,partial_boundary_copies=17,
                primary_cell_copies=79,raw_cell_payload_bytes=24576,run_elapsed_seconds=0.1720000000204891,
                build_journal_acknowledgments=8,run_journal_acknowledgments=4,
                artifact_review_checks=129,actual_review_checks=399,
                build_inventory_files=11,build_inventory_bytes=339767,run_files_including_result=4,run_bytes_including_result=121790),
    compiled="Exact Windows x64 SDK widths/128-byte header/four32-byte axes/256-byte aligned cell asserted. All14 scalar-first native-width stores and publication/error/count paths tied listing to COFF and linked PE;19 relevant bodies/3524 listed instruction bytes checked.",
    actual_behavior="All79 ordered controls and17 pre-error boundary copies match frozen256-byte goldens. Noncanonical BOOL bits, NULL/INVALID, count/error independence, partial error transport, malformed metadata and repeat refusal preserved. These are fixed own-source fake targets, not real Win32 calls.",
    measurement_limits="Build timer1.047s excludes interpreter/input preflight and final report construction/write; run0.172s excludes final result construction/write/startup as declared. File lengths and logical copies do not measure RSS, child/inference fit, disk durability or real original-file throughput. Ordinary harness writes only.",
    preservation="C V1 static HOLD and named V2/V3 source corrections, D1 build-helper V1-V6 lineage, runtime V3 lexical HOLD/V4 correction and all original proofs retained. No C test/build executed before both respective peers and Root bindings. First build/run only; no old native experiment replay or expected-result weakening.",
    concurrent_unfinished="Native25 Source4 diagnostic2519c0b1 remains31PASS/12FAIL/4deferred/1static. Ten intended runtime branches were masked by harness callback arity; two valid alternate kinds were incorrectly accepted. Callback-only control and a later separately named guard successor are pending. C acceptance cannot close that source defect.",
    qualification=dict(compiled_layout_and_fake_target_behavior=True,real_Win32_file_targets=False,
        actual_Python_conversion_bridge=False,same_Core_native_bank_or_ticket=False,positive_native_input_or_child=False,
        path_lifetime=False,physical14=False,native25_complete=False,new84_runtime=False,
        resource_fit=False,scientific=False,R09_complete=False,project_complete=False),
    next="Correct and independently validate the native25 harness control, then the narrowly named API/axis-kind guard. Close selected source/consumer roster and same-Core native/physical contracts before any real-route activation.",
    provider_spend_usd=0,application_defaults_changed=False,downloader_or_stopped_monitor_changed=False)
path=BASE/"NATIVE-CARRIER-ROOT-ACCEPTANCE-v1.json";raw=(json.dumps(value,indent=2)+"\n").encode()
with path.open("xb")as stream:stream.write(raw)
print(json.dumps(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),status=value["status"])))
