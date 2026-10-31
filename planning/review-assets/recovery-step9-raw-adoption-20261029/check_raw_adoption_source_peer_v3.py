"""Independent same-counterexample checks of the exact three-method successor."""
from pathlib import Path
from types import ModuleType
import ast
import dataclasses
import hashlib
import json
import sys

PHASE = Path(__file__).resolve().parent
SOURCE = PHASE / "raw_adoption_core_v3.py"
raw = SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "f4fcae07926927f509f455b1b8e243cec2be8fdbc91fa710aacf14618e9b5bea"
previous_raw = (PHASE / "raw_adoption_core_v2.py").read_bytes()
assert hashlib.sha256(previous_raw).hexdigest() == "a6877861860ba7a42d22d581d4bfa565984e6ce377d937ff3c4525b04130fd8a"


def methods(blob):
    tree = ast.parse(blob)
    result = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = ast.dump(node, include_attributes=False)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result[node.name + "." + child.name] = ast.dump(child, include_attributes=False)
    return tree, result


old_tree, old_methods = methods(previous_raw)
new_tree, new_methods = methods(raw)
assert old_methods.keys() == new_methods.keys()
changed = sorted(k for k in old_methods if old_methods[k] != new_methods[k])
assert changed == ["Owner._component", "Owner.handoff", "Owner.raise_exception"]
for tree in (old_tree, new_tree):
    if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str):
        tree.body.pop(0)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Owner":
            node.body = [child for child in node.body if not isinstance(child, ast.FunctionDef) or "Owner." + child.name not in changed]
assert ast.dump(old_tree, include_attributes=False) == ast.dump(new_tree, include_attributes=False)

module = ModuleType("independent_raw_adoption_candidate_v3")
sys.modules[module.__name__] = module
exec(compile(raw, str(SOURCE), "exec"), module.__dict__)
armed, denials = True, []


def audit(event, args):
    if armed and (event in ("open", "os.listdir", "os.scandir", "subprocess.Popen") or event.startswith("ctypes.")):
        denials.append(event)
        raise RuntimeError("pure probe denied " + event)


sys.addaudithook(audit)


def fresh():
    factory = module.HarnessFactory()
    context = module.Context(factory.ref("owner"), factory.ref("origin"), factory.ref("nonce"),
                             factory.ref("registry"), factory.ref("port"), factory.ref("output"),
                             factory.ref("source_context"), factory.ref("loader"), factory.ref("journal"))
    return factory, context, factory.owner(context, namespace_owned=True, reservation_ready=True)


def known_read():
    factory, context, owner = fresh()
    owner.declare_slot("f0", "original_file", handle=102, closer="CloseHandle", identity_ref=factory.ref("file_identity"))
    buffer_ref = factory.ref("buffer")
    owner.declare_buffer(buffer_ref, 3, b"abc")
    call = owner.reserve(0, "ReadFile", "f0", requested=3, buffer_ref=buffer_ref)
    owner.invoke(call)
    owner.store_scalar(call, 1)
    owner.store_count(call, 3)
    owner.wrapper_return(call)
    return context, owner, call


factory, context, owner = fresh()
owner.declare_slot("early", "original_file", handle=101, closer="CloseHandle", identity_ref=factory.ref("file_identity"))
blob = b"early"
owner.install_early(context.early_context, ("early",), blob, hashlib.sha256(blob).hexdigest(), 5, 5, 5, 7)
close = owner.reserve(0, "CloseHandle", "early")
owner.invoke(close)
owner.store_scalar(close, 1)
owner.wrapper_return(close)
owner.reconcile(close, context.owner)
before = owner.snapshot().to_dict()
assert before["slots"][0]["liveness"] == "closed_known" and owner.primary is None
caught = None
try:
    owner.handoff(context)
except module.AdoptionError as error:
    caught = error
after = owner.snapshot().to_dict()
assert caught is owner.primary and caught.code == "early_context_not_live"
assert after["handoff"]["claims"] == 0 and after["handoff"]["next_event_sequence"] == 7
assert owner.context is context and owner.origin is context.origin
assert after["known_read_bytes"] == after["hashed_bytes"] == after["captured_bytes"] == 5
assert after["namespace_owned"] is True and after["reservation_ready"] is True
assert after["slots"][0]["close_invocations"] == 1
handoff = {"id": "closed_early_source_handoff", "status": "passed", "rejection": caught.code,
           "claims": 0, "event_sequence": 7, "known_bytes_carried": 5, "same_objects": True}

context, owner, call = known_read()
injected = module.AdoptionError("hook_owned_error")


def stop():
    raise injected


caught = None
try:
    owner.copy(call, before=stop)
except BaseException as error:
    caught = error
after = owner.snapshot().to_dict()
assert caught is injected and owner.primary is injected and owner.secondary == ()
assert after["primary_code"] == "wrapper_exception" and after["disposition"] != "primitive_complete"
assert call.stopped and after["known_read_bytes"] == 3 and after["captured_bytes"] == after["hashed_bytes"] == 0
assert after["counters"]["portable_wrapper_returns"] == 1 and not after["buffers"][0]["reusable"]
callback = {"id": "fresh_injected_AdoptionError", "status": "passed", "same_original_primary": True,
            "secondary_count": 0, "known_read_bytes": 3, "captured_bytes": 0, "wrapper_returns": 1}

context, owner, call = known_read()
before = owner.snapshot().to_dict()
later = RuntimeError("later cleanup publication failure")
owner.raise_exception(call, later, "cleanup_publication")
after = owner.snapshot().to_dict()
assert owner.primary is later and call.stopped and call.wrapper_state == "returned"
assert after["counters"] == before["counters"] and after["counters"]["portable_wrapper_returns"] == 1
assert after["known_read_bytes"] == 3
owner.reconcile(call, context.owner)
owner.reconcile(call, context.owner)
close = owner.reserve(1, "CloseHandle", "f0")
owner.invoke(close)
owner.store_scalar(close, 1)
owner.wrapper_return(close)
final = owner.snapshot().to_dict()
assert owner.primary is later and final["slots"][0]["close_invocations"] == 1
assert final["counters"]["portable_wrapper_returns"] == 2 and final["slots"][0]["liveness"] == "closed_known"
wrapper = {"id": "known_wrapper_return_then_later_stop", "status": "passed", "wrapper_returns_after_stop": 1,
           "wrapper_returns_after_legal_close": 2, "same_original_primary": True, "close_invocations": 1}
assert denials == []
armed = False


def pin(path):
    blob = path.read_bytes()
    return {"path": str(path), "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}


report = {"schema_version": 3, "status": "passed", "source": pin(SOURCE),
          "prior_source": pin(PHASE / "raw_adoption_core_v2.py"), "checker": pin(Path(__file__).resolve()),
          "before": pin(PHASE / "RAW-ADOPTION-SOURCE-INDEPENDENT-BEFORE-v2.json"),
          "author_wrapper_before": pin(PHASE / "RAW-ADOPTION-WRAPPER-RETURN-BEFORE-v2.json"),
          "AST_changed_methods": changed, "AST_unchanged_methods": len(new_methods) - len(changed),
          "all_other_AST_except_module_docstring_equal": True,
          "probes": [handoff, callback, wrapper], "audit_denials": denials, "synthetic_owners": 3,
          "fixture_histories_replayed": 0, "actual_API_calls": 0, "old_payload_or_source_closure_operations": 0,
          "FFI_registration_proven": False, "production_owner_bound": False, "profile_qualified": False,
          "runtime_authorized": False}
out = PHASE / "RAW-ADOPTION-SOURCE-INDEPENDENT-AFTER-v3.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
print(json.dumps({"proof": pin(out), "status": "passed", "probes": 3}, sort_keys=True))
