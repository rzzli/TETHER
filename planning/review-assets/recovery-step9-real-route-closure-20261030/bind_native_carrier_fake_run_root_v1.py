"""Root one generated-image fake-target binding after both independent reviews."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
def pin(path):
    item=Path(path)
    if not item.is_absolute():item=ROOT/item
    raw=item.read_bytes()
    try:label=str(item.relative_to(ROOT))
    except ValueError:label=str(item)
    return dict(path=label,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(path,value):
    raw=(json.dumps(value,indent=2)+"\n").encode()
    with path.open("xb")as stream:stream.write(raw)
    return pin(path)
artifact_review=BASE/"NATIVE-CARRIER-INDEPENDENT-BUILD-ARTIFACT-REVIEW-v1.json"
runtime_review=BASE/"NATIVE-CARRIER-RUNTIME-INDEPENDENT-STATIC-REVIEW-v4.json"
if pin(artifact_review)["sha256"]!="5796bcc69efd666491baf3fdbc04b96c509f8c772173817370c3ca4b341d9cb4":raise ValueError("Selected artifact peer")
if json.loads(artifact_review.read_text())["status"]!="CLEAR_COMPILED_LAYOUT_AND_ORDERING_ONLY":raise ValueError("Artifact peer not clear")
if pin(runtime_review)["sha256"]!="5bd681cbb9af82f7c182e4a412c5af93c02fbc2813282e169d1f33a35b11c64b":raise ValueError("Selected runtime peer")
if json.loads(runtime_review.read_text())["status"]!="CLEAR_STATIC_ONE_FAKE_RUN_HELPER_ONLY":raise ValueError("Runtime peer not clear")
build_dir=ROOT/"data/cache/r09-native-carrier-component-build-20261030T055706Z"
build_path=build_dir/"build-result.json";build=json.loads(build_path.read_text())
if pin(build_path)["sha256"]!="9275174036dfab54a50fea143cd3d547e5dbadd5e41af559d95b4eacbfc4fa8e"or build["status"]!="BUILT_NOT_EXECUTED":raise ValueError("Exact first successful build")
for item in build["artifacts"]:
    if pin(item["path"])!=item:raise ValueError("Build artifact differs")
inputs={name:pin(BASE/file)for name,file in dict(
    driver="run_native_carrier_fake_tests_v4.py",command_executor="build_native_carrier_component_v6.py",
    expectations="NATIVE-CARRIER-FAKE-EXPECTATIONS-v1.json",tests="native_carrier_fake_tests_v1.c",
    preparation="NATIVE-CARRIER-FAKE-TEST-PREPARATION-v1.json",phase="NATIVE-CARRIER-PARTIAL-PHASE-CLARIFICATION-v1.json").items()}
inputs.update(image=pin(build_dir/"native-carrier-fake-tests.exe"),build_result=pin(build_path),
              artifact_peer=pin(artifact_review),runtime_peer=pin(runtime_review))
if inputs["driver"]["sha256"]!="1ca55b9c8855e4898d018f3e4a145b5f619c0e627595295b22f8752561adb76c":raise ValueError("Exact cleared runtime helper")
if inputs["image"]["sha256"]!="4eef5fc52eac8868e963dad15e92e2101a7fda428cc6ddb8412076aaf8eeebbd":raise ValueError("Exact reviewed own-source image")
stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
scope=dict(schema_version=1,status="ROOT_AUTHORIZED_ONE_MODEL_FREE_C_FAKE_TARGET_RUN",
    created_at_utc=stamp,budget_seconds=60,cleanup_reserve_inside_budget_seconds=2,
    inputs=inputs,expected_controls=79,expected_wrapper_attempts=116,expected_fake_target_calls=47,
    expected_error_entries=17,expected_error_returns=16,
    output_relative="data/cache/r09-native-carrier-component-run-"+stamp,
    authority="User-authorized framework correctness work and installed toolchain; both independent artifact/ordering and runtime-helper reviews clear before this binding.",
    boundary="Exactly one own-source compiled image, fixed fake14 API target functions, preallocated cells and buffers, full256B oracle comparison. Standard executable/CRT/pipe startup is external test TCB, not qualified physical14 activity.",
    exclusions="No model/clinical/original payload, real fourteen-port target, old native experiment replay, same-Core ticket/bank/lease/path lifetime, physical14/new84/inference/scientific qualification or cap/default/downloader/monitor change.",
    first_result="Exclusive output reservation and no retry. Preserve original errors/raw output/acknowledged journal/first grade; failed tests remain failed until separately named corrections and review.",provider_spend_usd=0)
scope_pin=write(BASE/"NATIVE-CARRIER-FAKE-RUN-SCOPE-v1.json",scope)
inputs["root_scope"]=scope_pin
binding=dict(schema_version=1,status="ROOT_BOUND_ONE_FAKE_TARGET_RUN",budget_seconds=60,
             output_relative=scope["output_relative"],inputs=inputs)
binding_pin=write(BASE/"NATIVE-CARRIER-FAKE-RUN-BINDING-v1.json",binding)
print(json.dumps(dict(scope=scope_pin,binding=binding_pin,output_relative=scope["output_relative"])))
