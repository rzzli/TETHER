"""Freeze literal preparation only; no adopter source or actual binding."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TARGET=HERE/"RAW-ADOPTION-FIXTURE-FREEZE-v2.json"


def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


assert not TARGET.exists()
fixture=HERE/"RAW-ADOPTION-FIXTURES-v2.json"; schema=HERE/"ADOPTION-FIXTURE-SCHEMA-v2.json"
proof=HERE/"RAW-ADOPTION-LITERAL-SHAPE-PROOF-v2.json"
f=json.loads(fixture.read_bytes()); p=json.loads(proof.read_bytes())
assert p["status"]=="passed" and p["methods"]==6 and not p["failures"] and not p["errors"]
assert p["fixture"]==pin(fixture) and p["schema"]==pin(schema)
assert pin(Path(f["root_scope"]["path"]))==f["root_scope"]
for row in f["preserved_v1"].values(): assert pin(Path(row["path"]))==row
record=dict(schema_version=2,status="CLOSED_FICTIONAL_ADOPTION_FIXTURE_PREPARATION_FROZEN_FOR_PEER_SOURCE_IMPLEMENTATION_NOT_AUTHORIZED",
    fixture=pin(fixture),schema=pin(schema),author=f["author"],shape_proof=pin(proof),checker=p["checker"],freeze_author=pin(Path(__file__).resolve()),
    root_scope=f["root_scope"],design=f["design"],design_freeze=f["design_freeze"],preserved_v1=f["preserved_v1"],
    preserved_drafts=[pin(HERE/name) for name in ("ADOPTION-FIXTURE-SCHEMA-DRAFT-v1.json","ADOPTION-FIXTURE-SCHEMA-DRAFT-v2.json","RAW-ADOPTION-RAWVALUE-COUNTER-SUBSET-REVIEW-v1.json")],
    cases=32,families=15,summary=p["summary"],exact_v2_delta=f["exact_v2_delta"],
    count_domain="Successful defined0 is known0 primitive success, not missing data or a whole-file EOF claim. Pending count may later resolve before wrapper stop; failed/unreturned data remains unknown, never reset0.",
    identity_domain="Opaque object labels/initial claims are instructions for typed HARNESS_ONLY construction in a later closed injected harness, not serialized producer-ready authority or real live-source qualification.",
    first_fact_domain="One dedicated UNOBSERVED sentinel differs from observedNULL/HANDLE0/BOOL0/COUNT0. Raw value facts survive interruption before auxiliary flags/right transfer; contributions reconcile by ordinal+field without duplicate counts or retry.",
    source_implementation_authorized=False,actual_FFI_binding_or_ctypes_construction=False,actual_target_file_port_API_calls=0,
    old_source_closure_or_payload_operations=0,source_originals_qualified=False,FFI_registration_proven=False,
    production_owner_bound=False,originals_authenticated=False,runtime_authorized=False,profile_qualified=False,
    next="Independent exact v2 schema/literal delta reviews, then a separate root source/pure implementation decision; real entry/FFI/runtime remains later.")
with TARGET.open("xb") as out: out.write(json.dumps(record,sort_keys=True,indent=2).encode("utf-8")+b"\n")
print(json.dumps(pin(TARGET)))
