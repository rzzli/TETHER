"""Root build-only binding. Run only after the final independent static review."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]


def pin(path):
    item=Path(path)
    if not item.is_absolute():item=ROOT/item
    raw=item.read_bytes()
    try:label=str(item.relative_to(ROOT))
    except ValueError:label=str(item)
    return dict(path=label,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def write_new(path,value):
    raw=(json.dumps(value,indent=2)+"\n").encode()
    with path.open("xb")as stream:stream.write(raw)
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


review_path=BASE/"NATIVE-CARRIER-INDEPENDENT-PREBUILD-REVIEW-v2.json"
review=json.loads(review_path.read_text(encoding="utf-8"))
if review["status"]!="CLEAR_STATIC_PREBUILD_ONLY":raise ValueError("Final independent prebuild review is not clear")
prep_path=BASE/"NATIVE-CARRIER-BUILD-PREPARATION-v2.json"
prep=json.loads(prep_path.read_text(encoding="utf-8"))
for item in prep["selected_inputs"].values():
    if pin(item["path"])!=item:raise ValueError("Prepared input changed: "+item["path"])
inputs=dict(prep["selected_inputs"])
inputs["independent_review"]=pin(review_path)
inputs["preparation"]=pin(prep_path)
probe_path=ROOT/"planning/review-assets/recovery-step9-native-grammar-20261028/TOOLCHAIN-LOCAL-PROBE-v2.json"
probe=json.loads(probe_path.read_text(encoding="utf-8"))
if probe["status"]!="installed_x64_toolchain_probe_passed":raise ValueError("Installed toolchain not qualified by retained probe")
inputs["toolchain_probe"]=pin(probe_path)
inputs["build_environment"]=pin(probe["filtered_environment"]["path"])
if any(inputs["build_environment"][key]!=probe["filtered_environment"][key]for key in("bytes","sha256")):
    raise ValueError("Build environment differs from accepted probe")
for name in("compiler","linker"):
    actual=pin(probe[name])
    original=next(p for p in probe["input_proofs"]if p["path"].casefold()==probe[name].casefold())
    if actual["bytes"]!=original["bytes"]or actual["sha256"]!=original["sha256"]:
        raise ValueError("Installed "+name+" differs from accepted probe")
    inputs[name]=actual
timestamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
scope=dict(schema_version=1,status="ROOT_AUTHORIZED_BUILD_ONLY_NOT_IMAGE_EXECUTION",
    purpose="First build of the selected own-source internal return-publication component and independent fake79 harness",
    created_at_utc=timestamp,budget_seconds=60,
    independent_review=inputs["independent_review"],preparation=inputs["preparation"],
    commands=["compile-carrier","compile-tests","link-tests"],
    output_relative="data/cache/r09-native-carrier-component-build-"+timestamp,
    exclusions="No image dispatch, model/clinical original, actual fourteen-port target, C/ABI behavior qualification, same-Core ticket/lease/lifetime, physical14 or runtime/default/cap change.",
    TCB="Pinned existing compiler/linker and accepted installed MSVC/SDK/UCRT build environment; transitive installed toolchain inputs remain external trusted prerequisites, not freshly complete-restored sources.",
    first_result="Retain attempt, command results, raw output, chained acknowledged journal and failure. No retry/healing. Artifact/disassembly peer required before a separately bound image run.",
    provider_spend_usd=0)
scope_pin=write_new(BASE/"NATIVE-CARRIER-COMPONENT-BUILD-SCOPE-v1.json",scope)
inputs["root_scope"]=pin(scope_pin["path"])
binding=dict(schema_version=1,status="ROOT_BOUND_BUILD_ONLY",budget_seconds=60,
    output_relative=scope["output_relative"],inputs=inputs,
    selected_driver="build_native_carrier_component_v6.py",effective_C_source="preflight_file14_raw_v3.c",
    note="Binding created after independent static clearance. Compiler3commands only; executable remains unconsumed until artifact/disassembly and distinct Root runtime binding.")
binding_pin=write_new(BASE/"NATIVE-CARRIER-COMPONENT-BUILD-BINDING-v1.json",binding)
print(json.dumps(dict(scope=scope_pin,binding=binding_pin,output_relative=scope["output_relative"])))
