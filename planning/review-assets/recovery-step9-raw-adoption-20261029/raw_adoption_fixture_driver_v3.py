"""Independent v3 literal dispatcher/comparator; never supplies expected data to core.

Only NEW frozen metadata and the separately paused pure core source are loaded.
No real port/binding or original file is constructed. Labels are harness-local.
"""
import copy
import encodings.utf_16_le
import hashlib
import json
from pathlib import Path
import sys
import time
import types

HERE=Path(__file__).resolve().parent
SCHEMA_PATH=HERE/"ADOPTION-FIXTURE-SCHEMA-v3.json"
FIXTURE_PATH=HERE/"RAW-ADOPTION-FIXTURES-v3.json"
SCHEMA_SHA="1dfc199ced5a8f055cd82557b1f38defb5fa49d37b31e330e03d6c78f1dfc0ec"
FIXTURE_SHA="37e3c0d614a5aaeca2125c05e8d94c42707d901e039c41ac02978bb23caacc64"
ACTIVE=[False]
AUDIT_DENIALS=[]


class DriverError(RuntimeError): pass


def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")


def same(a,b):
    if type(a) is not type(b): return False
    if type(a) is dict: return set(a)==set(b) and all(same(a[k],b[k]) for k in a)
    if type(a) is list: return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b


def load_literals():
    raw=FIXTURE_PATH.read_bytes(); schema=SCHEMA_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=FIXTURE_SHA or hashlib.sha256(schema).hexdigest()!=SCHEMA_SHA:
        raise DriverError("frozen_literal_pin")
    return json.loads(raw),json.loads(schema)


def load_core(path,expected_sha):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha: raise DriverError("paused_core_pin")
    name="raw_adoption_core_under_independent_test"
    module=types.ModuleType(name); module.__file__=str(path); sys.modules[name]=module
    exec(compile(raw,str(path),"exec"),module.__dict__)
    return module


def audit(event,args):
    if ACTIVE[0] and (event=="open" or event.startswith(("ctypes.","subprocess.","socket.")) or event in ("os.system","os.startfile")):
        AUDIT_DENIALS.append(event)
        raise DriverError("core_IO_denied")


sys.addaudithook(audit)


def invoke(function,*args,**kwargs):
    previous=ACTIVE[0]; ACTIVE[0]=True
    try: return function(*args,**kwargs)
    finally: ACTIVE[0]=previous


class FrozenRun:
    """Translate only closed inputs. All comparisons are outside core calls."""
    def __init__(self,core,case):
        self.core=core
        self.case=copy.deepcopy(case)
        self.refs={}; self.exceptions={}; self.calls={}; self.guards=[]
        self.snapshots=[]; self.checkpoints=[]; self.return_views=[]
        self.factory=None; self.owner=None; self.context=None

    def atom_value(self,atom):
        if atom["tag"]=="UNOBSERVED": return self.core.UNOBSERVED
        if atom["tag"]=="NULL": return None
        return atom["value"] # never bool/int-normalize an observed value

    def setup(self):
        c=self.core; initial=self.case["initial"]; self.factory=c.HarnessFactory()
        for description in initial["objects"]:
            identity,kind=description["id"],description["kind"]
            self.refs[identity]=self.factory.origin(**initial["clock"]) if kind=="origin" else self.factory.ref(kind)
        classes=dict(RuntimeError=RuntimeError,MemoryError=MemoryError,TimeoutError=TimeoutError,KeyboardInterrupt=KeyboardInterrupt,SystemExit=SystemExit)
        for description in initial["exceptions"]:
            self.exceptions[description["id"]]=classes[description["class"]](description["message"])
        kwargs={key:None if value is None else self.refs[value] for key,value in initial["current"].items()}
        self.context=c.Context(**kwargs)
        ns=initial["namespace_state"]
        primary=None if initial["primary_exception_ref"] is None else self.exceptions[initial["primary_exception_ref"]]
        self.owner=self.factory.owner(self.context,namespace_owned=ns["namespace_owned"],reservation_ready=ns["reservation_ready"],primary=primary)
        for slot in initial["slots"]:
            self.owner.declare_slot(slot["id"],slot["kind"],handle=self.atom_value(slot["handle_fact"]),closer=slot["closer"],
                identity_ref=None if slot["identity_capability_ref"] is None else self.refs[slot["identity_capability_ref"]])
        for buffer in initial["buffers"]:
            self.owner.declare_buffer(self.refs[buffer["id"]],buffer["capacity"],bytes.fromhex(buffer["hex"]),buffer["generation"])
        for prefix in initial["identity_prefix"]:
            self.owner.declare_identity_prefix(prefix["slot_ref"],tuple(prefix["query_names"]))
        early=initial["early_context"]
        if early is not None:
            self.owner.install_early(self.refs[early["context_ref"]],tuple(early["slot_refs"]),bytes.fromhex(early["blob_hex"]),early["digest"],
                early["known_read_bytes"],early["hashed_bytes"],early["captured_bytes"],early["event_sequence"])
        return self.owner

    def exception_ref(self,error):
        if error is None: return None
        for label,issued in self.exceptions.items():
            if error is issued: return label
        if type(error) is self.core.AdoptionError: return None # source-created semantic guard, no injected identity claim
        raise DriverError("core_replaced_injected_exception_object")

    def diagnostic_error(self,diagnostic):
        if diagnostic is None: return None
        # Inspect the raw detached diagnostic BEFORE label normalization.
        # Any live exception/container leak is a harness failure, not hidden.
        if type(diagnostic) is not dict or set(diagnostic)!={"identity","class_name","message","args_repr","format_failed"}:
            raise DriverError("immutable_diagnostic_exact_fields_required")
        if any(isinstance(value,BaseException) for value in diagnostic.values()):
            raise DriverError("mutable_exception_leaf")
        if not (type(diagnostic["class_name"]) is str and len(diagnostic["class_name"])<=128
            and type(diagnostic["message"]) is str and len(diagnostic["message"])<=256
            and type(diagnostic["format_failed"]) is bool
            and type(diagnostic["args_repr"]) is list and len(diagnostic["args_repr"])<=8
            and all(type(value) is str and len(value)<=256 for value in diagnostic["args_repr"])):
            raise DriverError("immutable_diagnostic_scalar_domains")
        original=self.owner.exception_for_token(diagnostic["identity"])
        if not isinstance(original,BaseException): raise DriverError("diagnostic_token_did_not_resolve_original")
        if diagnostic["class_name"]!=type(original).__name__[:128]: raise DriverError("diagnostic_class_identity")
        return original

    def ref_label(self,value):
        for label,ref in self.refs.items():
            if value is ref: return label
        raise DriverError("snapshot_foreign_or_replaced_reference")

    def snapshot(self):
        snapshot=self.owner.snapshot()
        if type(snapshot) is not self.core.Snapshot: raise DriverError("source_snapshot_required")
        raw=snapshot.to_dict()
        data=dict(raw)
        data["primary_exception_ref"]=self.exception_ref(self.diagnostic_error(data.pop("primary_exception")))
        secondary=data.pop("secondary_exceptions")
        data["secondary_exception_refs"]=[label for diagnostic in secondary if (label:=self.exception_ref(self.diagnostic_error(diagnostic))) is not None]
        data["buffers"]=[dict(buffer,id=self.ref_label(buffer["id"])) for buffer in data["buffers"]]
        return snapshot,data

    @staticmethod
    def projection(data,path):
        parts=path.split(".")
        if parts[0].startswith("record") and parts[0][6:].isdigit():
            ordinal=int(parts.pop(0)[6:]); found=[r for r in data["records"] if r["ordinal"]==ordinal]
            if len(found)!=1: raise DriverError("checkpoint_missing_ordinal")
            value=found[0]
        elif parts[0]=="slot":
            parts.pop(0); label=parts.pop(0); found=[s for s in data["slots"] if s["id"]==label]
            if len(found)!=1: raise DriverError("checkpoint_missing_slot")
            value=found[0]
        else: value=data
        for field in parts:
            if type(value) is not dict or field not in value: raise DriverError("checkpoint_field_missing")
            value=value[field]
        return value

    def dispatch(self,step):
        o=self.owner; op=step["op"]
        if op=="reserve":
            value=o.reserve(step["ordinal"],step["api"],step["slot"],step["requested"],
                None if step["buffer_ref"] is None else self.refs[step["buffer_ref"]],bytes.fromhex(step["prepared_hex"]),step["declared_empty"])
            if step["ordinal"] in self.calls: raise DriverError("core_accepted_duplicate_reserve")
            self.calls[step["ordinal"]]=value
        elif op=="invoke": o.invoke(self.calls[step["ordinal"]])
        elif op=="scalar": o.store_scalar(self.calls[step["ordinal"]],self.atom_value(step["fact"]))
        elif op=="count": o.store_count(self.calls[step["ordinal"]],self.atom_value(step["fact"]))
        elif op=="error": o.store_error(self.calls[step["ordinal"]],self.atom_value(step["fact"]),step["defined"])
        elif op=="aux": o.aux(self.calls[step["ordinal"]],step["field"])
        elif op=="wrapper_return": o.wrapper_return(self.calls[step["ordinal"]])
        elif op=="raise":
            # A real Python raise/catch yields the original injected object;
            # the core records that wrapper observation, not a class-name stub.
            try: raise self.exceptions[step["exception_ref"]]
            except BaseException as error:
                o.raise_exception(None if step["ordinal"] is None else self.calls[step["ordinal"]],error,step["phase"])
        elif op=="reconcile":
            self.return_views.append(o.reconcile(self.calls[step["ordinal"]],self.refs[step["owner_ref"]]))
        elif op=="copy": o.copy(self.calls[step["ordinal"]])
        elif op=="hash": o.hash(self.calls[step["ordinal"]])
        elif op=="clock": o.advance(step["now_ns"])
        elif op=="handoff":
            context=self.core.Context(**{key:None if value is None else self.refs[value] for key,value in step["refs"].items()})
            self.return_views.append(o.handoff(context))
        elif op=="reuse_buffer": o.reuse_buffer(self.refs[step["buffer_ref"]],step["new_generation"],bytes.fromhex(step["hex"]))
        elif op=="buffer_write": o.buffer_write(self.refs[step["buffer_ref"]],step["generation"],bytes.fromhex(step["hex"]))
        else: raise DriverError("unimplemented_closed_step")

    def run(self):
        invoke(self.setup)
        initial_snapshot,initial_data=invoke(self.snapshot)
        self.snapshots.append(dict(after_step=-1,data=initial_data))
        for index,step in enumerate(self.case["steps"]):
            try: invoke(self.dispatch,step)
            except self.core.AdoptionError as error:
                self.guards.append(dict(step=index,code=error.code))
            snapshot,data=invoke(self.snapshot)
            self.snapshots.append(dict(after_step=index,data=data))
            # Object continuity is checked directly, not trusted from a scalar
            # report or matched by names/numeric clock values.
            if self.owner.context is not self.context or self.owner.origin is not self.context.origin:
                raise DriverError("core_replaced_original_context_or_origin")
            for checkpoint in self.case["checkpoints"]:
                if checkpoint["after_step"]!=index: continue
                differences=[]
                for path,expected in checkpoint["projection"].items():
                    actual=self.projection(data,path)
                    if not same(actual,expected): differences.append(dict(path=path,expected=expected,actual=actual))
                self.checkpoints.append(dict(after_step=index,matched=not differences,differences=differences))
        final_snapshot,actual=invoke(self.snapshot)
        expected=self.case["expected"]
        differences=[]
        if set(actual)!=set(expected): differences.append(dict(path="$keys",expected=sorted(expected),actual=sorted(actual)))
        for field,value in expected.items():
            if field not in actual or not same(actual[field],value): differences.append(dict(path=field,expected=value,actual=actual.get(field)))
        # Independent ordinary-interface identity assertions beyond formatting.
        expected_primary=expected["primary_exception_ref"]
        if expected_primary is not None and self.owner.primary is not self.exceptions[expected_primary]:
            differences.append(dict(path="primary_object_identity",expected=expected_primary,actual="different_object"))
        if expected["disposition"]=="primitive_complete" and self.owner.primary is not None:
            differences.append(dict(path="unexpected_primary_object",expected=None,actual=type(self.owner.primary).__name__))
        if expected["disposition"]!="primitive_complete" and not isinstance(self.owner.primary,BaseException):
            differences.append(dict(path="missing_primary_object",expected="BaseException",actual=type(self.owner.primary).__name__))
        if len(self.checkpoints)!=len(self.case["checkpoints"]): raise DriverError("checkpoint_count")
        return dict(id=self.case["id"],matched=not differences and all(c["matched"] for c in self.checkpoints),
            differences=differences,checkpoints=self.checkpoints,guards=self.guards,snapshots=self.snapshots,actual=actual,
            snapshot_count=len(self.snapshots)+1,scope="Fictional source/pure execution only; no native C call or production authority")
