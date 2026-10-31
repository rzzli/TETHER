"""Retain exact SOURCE/PURE component pins; no runtime/source authority."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TARGET=HERE/"UNICODE-OBSERVATIONS-IMPLEMENTATION-FREEZE-v2.json"
PROOF=HERE/"UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v3.json"

def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

assert not TARGET.exists()
proof=json.loads(PROOF.read_bytes())
assert proof["status"]=="passed" and proof["tests"]==14 and not proof["failures"] and not proof["errors"]
assert proof["source"]["sha256"]=="47c7cc1fc3889e32c5a3ff3efff50425ef208a041a308f5a447872bd788414b6"
for key in ("source","tables","checker","support","fixture"):
    assert proof[key]==pin(Path(proof[key]["path"]))
for row in proof["dependency_pins"]+proof["preserved_before"]: assert row==pin(Path(row["path"]))
extra=("UNICODE-OBSERVATIONS-DESIGN-CONTRACT-v2.json","UNICODE-OBSERVATIONS-DESIGN-FREEZE-v2.json",
    "UNICODE-OBSERVATIONS-TRACE-FREEZE-v2.json","UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v2.json",
    "UNICODE-OBSERVATIONS-PREPARATION-AND-SOURCE-SCOPE-v1.json","UNICODE-OBSERVATIONS-ROOT-CORRECTION-SCOPE-v2.json",
    "UNICODE-OBSERVATIONS-PREFIX-PHASE-VECTOR-v1.json","UNICODE-OBSERVATIONS-FIRST-IMPLEMENTATION-PROBE-v1.json",
    "author_unicode_observation_tables_v1.py")
record=dict(schema_version=2,status="FROZEN_SOURCE_PURE_COMPONENT_AWAITING_INDEPENDENT_PEER_NOT_PROFILE_QUALIFICATION",
    source=proof["source"],tables=proof["tables"],proof=pin(PROOF),checker=proof["checker"],support=proof["support"],
    dependencies=proof["dependency_pins"],fixture=proof["fixture"],preserved_before=proof["preserved_before"],
    contract_and_scope_inputs=[pin(HERE/name) for name in extra],author=pin(Path(__file__).resolve()),
    results=dict(methods=14,full_fictional_bases=6,literal_scenarios=36,observe_callback_identities=33,
        strict_callback_identities=22,nested_field_mutations=22,prefix_phase_before_after=True,
        after_actual_deepfreeze_original_stop_identity=True,elapsed_seconds=proof["elapsed_seconds"],audit_denials=proof["audit_denials"]),
    four_guard_delta=dict(data_integer_ValueError_bounded=True,marker_presence_before_parse=True,
        failure_tail_phase_aware=True,original_callback_after_issue=True),
    ordinary_API="Exact factory-issued codec profile, immutable declared lexical bindings, exact source-issued Observation; no serialized passed/ready token.",
    optional_module_diagnostic="Current frozen Unicode tables do not provide a machine-closed module-diagnostic value schema. A bounded dict is retained opaque as external_pending and forces partial; none/null is fully closed. This does not borrow an older C++ schema.",
    filesystem_scope="No explicit filesystem/source discovery/clock/SDK/native dispatch in the component. Harness preloads the ordinary stdlib UTF16 codec before denying I/O during pure calls. This is not proof of no OS loader/internals or hostile-Python isolation.",
    resource_scope="Fixed source/row/array bounds constrain data; actual memory/time fit and owner clocks are not qualified by synthetic pure checks.",
    pending_bindings=["actual module/file identity and native returns","fresh original hashes/live leases/source authority",
        "capture provenance/parent PID/exit/reaping/EOF","resource limits/peaks/cleanup/owner clock",
        "archive/seal universe and closed production source integration","native profile/application/scientific qualification"],
    old_pack_CPU_GGUF_operations=0,SDK_native_calls=0,runtime_pack_file_created=False,production_activation=False,
    originals_authenticated=False,runtime_authorized=False,profile_qualified=False,scientific_validation="not_established")
raw=json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")+b"\n"
with TARGET.open("xb") as out: out.write(raw)
print(json.dumps(pin(TARGET)))
