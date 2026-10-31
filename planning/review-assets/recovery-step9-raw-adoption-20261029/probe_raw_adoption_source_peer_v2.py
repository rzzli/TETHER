"""Two bounded synthetic source probes; no file-port/FFI or fixture execution."""
from pathlib import Path
from types import ModuleType
import dataclasses
import hashlib
import json
import sys

PHASE = Path(__file__).resolve().parent
SOURCE = PHASE / "raw_adoption_core_v2.py"
raw = SOURCE.read_bytes()
digest = hashlib.sha256(raw).hexdigest()
assert digest == "a6877861860ba7a42d22d581d4bfa565984e6ce377d937ff3c4525b04130fd8a"
module = ModuleType("independent_raw_adoption_candidate_v2")
sys.modules[module.__name__] = module
exec(compile(raw, str(SOURCE), "exec"), module.__dict__)
armed = True
denials = []


def audit(event, args):
    if armed and (event in ("open", "os.listdir", "os.scandir", "subprocess.Popen") or event.startswith("ctypes.")):
        denials.append(event)
        raise RuntimeError("pure probe denied " + event)


sys.addaudithook(audit)


def owner_with_context():
    factory = module.HarnessFactory()
    context = module.Context(factory.ref("owner"), factory.ref("origin"), factory.ref("nonce"),
                             factory.ref("registry"), factory.ref("port"), factory.ref("output"),
                             factory.ref("source_context"), factory.ref("loader"), factory.ref("journal"))
    return factory, context, factory.owner(context, namespace_owned=True, reservation_ready=True)


# A current source context must not gain a live-source handoff after its only
# declared source handle has been deliberately and successfully closed.
factory, context, owner = owner_with_context()
slot = owner.declare_slot("early", "original_file", handle=101, closer="CloseHandle", identity_ref=factory.ref("file_identity"))
blob = b"early"
owner.install_early(context.early_context, ("early",), blob, hashlib.sha256(blob).hexdigest(), 5, 5, 5, 7)
close = owner.reserve(0, "CloseHandle", "early")
owner.invoke(close)
owner.store_scalar(close, 1)
owner.wrapper_return(close)
owner.reconcile(close, context.owner)
state_before = owner.snapshot().to_dict()
rejected = None
try:
    owner.handoff(context)
except module.AdoptionError as error:
    rejected = error.code
state_after = owner.snapshot().to_dict()
handoff = {
    "name": "handoff_after_known_early_source_close",
    "slot_before": state_before["slots"][0],
    "primary_before": state_before["primary_code"],
    "rejection_code": rejected,
    "claims_after": state_after["handoff"]["claims"],
    "same_objects_after": state_after["handoff"]["same_objects"],
    "disposition_after": state_after["disposition"],
    "observed_problem": rejected is None and state_after["handoff"]["claims"] == 1,
}
assert handoff["slot_before"]["liveness"] == "closed_known"
assert handoff["observed_problem"]


# The public component hook accepts a callable. An error of the core's own
# exception class can originate in that hook without already being latched.
factory, context, owner = owner_with_context()
owner.declare_slot("f0", "original_file", handle=102, closer="CloseHandle", identity_ref=factory.ref("file_identity"))
buffer_ref = factory.ref("buffer")
owner.declare_buffer(buffer_ref, 3, b"abc")
read = owner.reserve(0, "ReadFile", "f0", requested=3, buffer_ref=buffer_ref)
owner.invoke(read)
owner.store_scalar(read, 1)
owner.store_count(read, 3)
owner.wrapper_return(read)
injected = module.AdoptionError("hook_owned_error")


def stop():
    raise injected


caught = None
try:
    owner.copy(read, before=stop)
except BaseException as error:
    caught = error
snapshot = owner.snapshot().to_dict()
hook = {
    "name": "injected_core_exception_class_from_copy_hook",
    "caught_same_object": caught is injected,
    "owner_primary_is_injected": owner.primary is injected,
    "owner_primary_is_none": owner.primary is None,
    "primary_code": snapshot["primary_code"],
    "disposition": snapshot["disposition"],
    "known_read_bytes": snapshot["known_read_bytes"],
    "captured_bytes": snapshot["captured_bytes"],
    "call_stopped": read.stopped,
    "observed_problem": caught is injected and owner.primary is None and snapshot["disposition"] == "primitive_complete",
}
assert hook["observed_problem"] and hook["call_stopped"] and hook["captured_bytes"] == 0
assert denials == []
armed = False
report = {
    "schema_version": 1,
    "status": "REPRODUCED_TWO_SOURCE_BOUNDARY_FINDINGS",
    "source": {"path": str(SOURCE), "bytes": len(raw), "sha256": digest},
    "probe_source": {"path": str(Path(__file__).resolve()), "bytes": Path(__file__).stat().st_size,
                     "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
    "probes": [handoff, hook],
    "audit_denials": denials,
    "synthetic_owners": 2, "fixture_histories_replayed": 0,
    "actual_API_calls": 0, "old_payload_or_source_closure_operations": 0,
    "FFI_registration_proven": False, "production_owner_bound": False,
    "profile_qualified": False, "runtime_authorized": False,
}
out = PHASE / "RAW-ADOPTION-SOURCE-INDEPENDENT-BEFORE-v2.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
saved = out.read_bytes()
print(json.dumps({"path": str(out), "bytes": len(saved), "sha256": hashlib.sha256(saved).hexdigest(),
                  "status": report["status"]}, sort_keys=True))
