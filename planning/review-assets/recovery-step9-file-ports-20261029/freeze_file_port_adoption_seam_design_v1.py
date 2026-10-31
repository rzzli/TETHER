"""Metadata-only freeze for independent next-gate design review."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TARGET=HERE/"FILE-PORTS-ADOPTION-SEAM-FREEZE-v1.json"
DESIGN=HERE/"FILE-PORTS-ADOPTION-SEAM-DESIGN-v1.json"

def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

assert not TARGET.exists()
assert pin(DESIGN)["sha256"]=="055db993a35f173d19a01c52c3b88515d97d3752d7dd409e1273b55f63c15cd6"
d=json.loads(DESIGN.read_bytes())
assert len(d["minimal_exports"])==14 and len(d["method_successor_map"])==10 and len(d["fixture_expectations_to_freeze_before_code"])==14
for row in d["sources"]: assert pin(Path(row["path"]))==row
assert pin(Path(d["prior_gap"]["path"]))==d["prior_gap"]
acceptance=HERE/"PORTABLE-FILE-PORTS-SCOPED-ACCEPTANCE-v2.json"
record=dict(schema_version=1,status="FROZEN_FINITE_INTERFACE_DESIGN_FOR_PEER_NO_IMPLEMENTATION_OR_ACTUAL_API_AUTHORITY",
    design=pin(DESIGN),author=d["author"],freeze_author=pin(Path(__file__).resolve()),sources=d["sources"],gap=d["prior_gap"],
    portable_scoped_acceptance=pin(acceptance),raw_C_vs_wrapper_axes_separated=True,one_owner_no_run_once_reset=True,
    literal_expectation_count=14,expectations_are_proposed_not_native_observations=True,
    next="Independent design peer and root decision before closing literal fixture format and any source successor.",
    source_changed=False,portable_helper_imports_or_executions=0,actual_API_calls=0,old_payload_or_sourceclosure_operations=0,
    FFI_registration_proven=False,production_owner_bound=False,originals_authenticated=False,profile_qualified=False,runtime_authorized=False)
with TARGET.open("xb") as out: out.write(json.dumps(record,sort_keys=True,indent=2).encode("utf-8")+b"\n")
print(json.dumps(pin(TARGET)))
