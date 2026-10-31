"""Root one-shot source/data diagnostic binding; no native image authorization."""
from pathlib import Path
import hashlib
import json

BASE=Path(__file__).resolve().parent
def pin(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(path,value):
    raw=(json.dumps(value,indent=2)+"\n").encode()
    with path.open("xb")as stream:stream.write(raw)
    return pin(path)
review_path=BASE/"NATIVE25-COMPONENT-INDEPENDENT-STATIC-REVIEW-v3.json"
review=json.loads(review_path.read_text())
if review["status"]!="CLEAR_STATIC_NATIVE25_COMPONENT_ONLY":raise ValueError("Independent native25 static peer not clear")
if pin(review_path)["sha256"]!="9ad2bcac3d052c1c98191ce42e58895b999d460a5aa0d73df7dd53169c51dfa2":raise ValueError("Exact selected peer")
freeze_path=BASE/"NATIVE25-COMPONENT-FREEZE-v3.json";freeze=json.loads(freeze_path.read_text())
if pin(freeze_path)["sha256"]!="3ec335327d414de40fe6e1c49ed726692995d629ef757c596716c80b3f26f987":raise ValueError("Exact coherent freeze")
for selected in freeze["pins"].values():
    if pin(Path(selected["path"]))!=selected:raise ValueError("Frozen input differs")
scope=dict(schema_version=3,status="ROOT_AUTHORIZED_SINGLE_NATIVE25_COMPONENT_EXECUTION",
    deadline_seconds=60,freeze=pin(freeze_path),independent_static_peer=pin(review_path),
    geometry=dict(normative_families=25,branches=48,executable=43,source_runtime=21,data=22,static=1,deferred=4,
                  genuine_worlds_max=20,data_instances_max=32,synthetic_capacity_max=20,bulk_bytes=2097169),
    selected_subjects="Unchanged Source4 kernel/Ops/FileView/codec only. Root C14 component is excluded.",
    diagnostic="Callback-only control after first31/12proof2519: seven leading EntryWorld arguments fixed, case bodies/assertions/source unchanged. Resolve ten masked runtime behaviors; both valid-kind guards still require refusal and remain ordinary failures if absent. Preserve both results, no xfail or healing.",
    allowed="One source/synthetic suite, actual source-issued objects and frozen fictional small/empty inputs. Retain actual256B rows, original errors, immutable snapshots, audit denials, accounting and partial persistence.",
    excluded="No original-target paths, C/SDK/FFI/compiler/native image/model, live ticket/lease/child/path lifetime, physical14/cap/default/downloader/monitor change,122or4GB replay.",
    limitations="Static/deferred rows are not passed native tests. Source DATA cannot qualify native ABI, OS search, full joint profile or science. Timing excludes final proof persistence/startup as declared.",
    provider_spend_usd=0)
scope_pin=write(BASE/"NATIVE25-COMPONENT-EXECUTION-SCOPE-v3.json",scope)
binding=dict(schema_version=3,status="ROOT_BOUND_NATIVE25_COMPONENT_ONE_SHOT",run_authorized=True,
    deadline_seconds=60,freeze=pin(freeze_path),execution_scope=scope_pin,independent_peer=pin(review_path))
binding_pin=write(BASE/"NATIVE25-COMPONENT-BINDING-v3.json",binding)
print(json.dumps(dict(scope=scope_pin,binding=binding_pin)))
