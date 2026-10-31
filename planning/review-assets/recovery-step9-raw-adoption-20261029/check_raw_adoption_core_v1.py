"""Independent frozen32 driver and ordinary adversarial pure-core tests."""
import ast
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import raw_adoption_fixture_driver_v1 as D

STARTED=time.monotonic()
SOURCE=HERE/"raw_adoption_core_v1.py"
PAUSED_SHA="2ef902a12e20f3ff6eb40bbc37504969970b1d86880ba0c396a6e7ad0e94edcb"
REPORT=HERE/"RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v1.json"
CORE=D.load_core(SOURCE,PAUSED_SHA)
FIXTURE,SCHEMA=D.load_literals()
BY={case["id"]:case for case in FIXTURE["cases"]}
RUNS=[]
EXTRA=[]


def fresh(identity="success_read_capture_close"):
    run=D.FrozenRun(CORE,BY[identity]); D.invoke(run.setup); return run


class CoreTests(unittest.TestCase):
    def setUp(self):
        if time.monotonic()-STARTED>60: raise TimeoutError("Adoption pure driver60s")

    def test_all32_final_snapshots_and9_checkpoints(self):
        self.assertEqual(len(FIXTURE["cases"]),32)
        for case in FIXTURE["cases"]:
            with self.subTest(case=case["id"]):
                run=D.FrozenRun(CORE,case)
                result=run.run(); RUNS.append(result)
                self.assertTrue(result["matched"],json.dumps(dict(differences=result["differences"],checkpoints=result["checkpoints"]),sort_keys=True))
                self.assertEqual(len(result["snapshots"]),len(case["steps"])+1)
                for row in result["snapshots"]:
                    self.assertEqual(row["data"]["qualification"],SCHEMA["qualification_exact_value"])
        self.assertEqual(sum(len(r["checkpoints"]) for r in RUNS),9)

    def test_first_fact_survives_actual_fold_interruption(self):
        run=fresh("open_first_fact_before_aux"); o=run.owner
        call=D.invoke(o.reserve,0,"CreateFileW","f0"); D.invoke(o.invoke,call)
        error=MemoryError("after_first_scalar_before_fold")
        original=o._fold
        def stop(_): raise error
        o._fold=stop
        try:
            try: D.invoke(o.store_scalar,call,101)
            except BaseException as caught: self.assertIs(caught,error)
            else: self.fail("injected store tail did not throw")
        finally: o._fold=original
        self.assertEqual(call.raw_scalar,101)
        self.assertIs(call.scalar_aux_ack,False)
        D.invoke(o.raise_exception,call,error,"after_scalar_before_aux")
        D.invoke(o.reconcile,call,run.context.owner)
        snapshot,data=D.invoke(run.snapshot)
        self.assertIs(o.primary,error)
        self.assertEqual(data["counters"]["known_scalar_returns"],1)
        self.assertEqual(data["slots"][0]["close_right"],"available")
        EXTRA.append(dict(id="actual_fold_interruption",original_object_preserved=True,scalar_fact=101))

    def test_actual_copy_hash_interruptions_keep_known_bytes_and_buffer(self):
        for component in ("copy","hash"):
            for error in (MemoryError("copy_or_hash"),KeyboardInterrupt("copy_or_hash"),SystemExit("copy_or_hash")):
                with self.subTest(component=component,error=type(error).__name__):
                    run=fresh(); o=run.owner
                    call=D.invoke(o.reserve,0,"ReadFile","f0",3,run.refs["buf0"])
                    D.invoke(o.invoke,call); D.invoke(o.store_scalar,call,1); D.invoke(o.store_count,call,3); D.invoke(o.wrapper_return,call)
                    def before(): raise error
                    try: D.invoke(getattr(o,component),call,before=before)
                    except BaseException as caught: self.assertIs(caught,error)
                    else: self.fail("component hook did not throw")
                    _,data=D.invoke(run.snapshot)
                    self.assertIs(o.primary,error)
                    self.assertEqual(data["known_read_bytes"],3)
                    self.assertEqual(data["hashed_bytes"],0); self.assertEqual(data["captured_bytes"],0)
                    self.assertEqual(data["buffers"][0]["hex"],"616263")
                    self.assertIs(data["buffers"][0]["reusable"],False)

    def test_same_numeric_foreign_second_factory_handoff_rejected(self):
        run=fresh("same_owner_early_handoff"); o=run.owner; first=o.context
        second=CORE.HarnessFactory(); initial=BY["same_owner_early_handoff"]["initial"]
        refs={}
        for field,kind in zip(CORE.Context.__dataclass_fields__,CORE.CONTEXT_KINDS):
            refs[field]=second.origin(**initial["clock"]) if kind=="origin" else second.ref(kind)
        context=CORE.Context(**refs)
        self.assertEqual(context.origin.start_ns,first.origin.start_ns)
        self.assertEqual(context.origin.now_ns,first.origin.now_ns)
        self.assertIsNot(context.origin,first.origin)
        with self.assertRaises(CORE.AdoptionError): D.invoke(o.handoff,context)
        _,data=D.invoke(run.snapshot)
        self.assertEqual(data["handoff"]["claims"],0)
        self.assertIs(o.context,first); self.assertIs(o.origin,first.origin)
        self.assertTrue(data["namespace_owned"] and data["reservation_ready"])

    def test_no_new_origin_owner_or_output_on_handoff(self):
        run=fresh("same_owner_early_handoff"); o=run.owner
        origin_type=type(o.origin); owner_type=type(o)
        origin_init,owner_init=origin_type.__init__,owner_type.__init__; calls=[]
        def forbidden_origin(*args,**kwargs): calls.append("origin"); return origin_init(*args,**kwargs)
        def forbidden_owner(*args,**kwargs): calls.append("owner"); return owner_init(*args,**kwargs)
        origin_type.__init__=forbidden_origin; owner_type.__init__=forbidden_owner
        try: view=D.invoke(o.handoff,run.context)
        finally: origin_type.__init__=origin_init; owner_type.__init__=owner_init
        self.assertEqual(calls,[])
        self.assertIs(o.context,run.context)
        self.assertEqual(view.to_dict()["context"],run.context)
        _,data=D.invoke(run.snapshot)
        self.assertEqual(data["handoff"]["new_output_reservations"],0)
        self.assertEqual(data["handoff"]["early_source_reopens"],0)
        self.assertEqual(data["known_read_bytes"],5)

    def test_nonowning_view_and_plain_ready_dict_cannot_invoke(self):
        run=fresh("open_first_fact_before_aux"); o=run.owner
        call=D.invoke(o.reserve,0,"CreateFileW","f0"); D.invoke(o.invoke,call); D.invoke(o.store_scalar,call,101)
        view=D.invoke(o.reconcile,call,run.context.owner)
        self.assertTrue(view.to_dict()["nonowning"])
        before=o.snapshot().to_dict()["counters"].copy()
        for value in (view,{"ordinal":0,"owner":run.context.owner,"ready":True},object()):
            with self.assertRaises(CORE.AdoptionError): D.invoke(o.invoke,value)
        self.assertEqual(o.snapshot().to_dict()["counters"],before)

    def test_strict_fields_conflicting_facts_and_after_stop(self):
        for value in (True,False,-2**31-1,2**31,None,CORE.UNOBSERVED):
            with self.subTest(rawBOOL=repr(value)):
                run=fresh(); o=run.owner
                call=D.invoke(o.reserve,0,"ReadFile","f0",3,run.refs["buf0"]); D.invoke(o.invoke,call)
                with self.assertRaises(CORE.AdoptionError): D.invoke(o.store_scalar,call,value)
                self.assertIs(call.raw_scalar,CORE.UNOBSERVED)
        run=fresh(); o=run.owner
        call=D.invoke(o.reserve,0,"ReadFile","f0",3,run.refs["buf0"]); D.invoke(o.invoke,call); D.invoke(o.store_scalar,call,1)
        D.invoke(o.store_count,call,3); D.invoke(o.store_count,call,3)
        before=o.snapshot().to_dict()["counters"]
        with self.assertRaises(CORE.AdoptionError): D.invoke(o.store_count,call,2)
        self.assertEqual(call.raw_count,3)
        self.assertEqual(o.snapshot().to_dict()["counters"],before)
        original=RuntimeError("wrapper_stopped")
        other=fresh(); p=other.owner
        pending=D.invoke(p.reserve,0,"ReadFile","f0",3,other.refs["buf0"]); D.invoke(p.invoke,pending)
        D.invoke(p.store_scalar,pending,1); D.invoke(p.raise_exception,pending,original,"RawReturn_allocation")
        with self.assertRaises(CORE.AdoptionError): D.invoke(p.store_count,pending,3)
        self.assertIs(pending.raw_count,CORE.UNOBSERVED); self.assertIs(p.primary,original)

    def test_snapshot_containers_detached_and_immutable(self):
        run=fresh(); o=run.owner
        call=D.invoke(o.reserve,0,"ReadFile","f0",3,run.refs["buf0"]); D.invoke(o.invoke,call); D.invoke(o.store_scalar,call,1)
        issued=o.snapshot(); a=issued.to_dict(); b=issued.to_dict()
        a["records"][0]["raw_scalar"]["value"]=999
        a["counters"]["known_scalar_returns"]=999; a["qualification"]["runtime_authorized"]=True
        a["slots"].clear(); a["buffers"][0]["hex"]="ff"
        self.assertTrue(D.same(issued.to_dict(),b))
        self.assertEqual(call.raw_scalar,1)
        with self.assertRaises(TypeError): issued._data["counters"]["known_scalar_returns"]=999
        with self.assertRaises((FrozenInstanceError,AttributeError)): issued._data={}

    def test_original_exception_args_cannot_mutate_issued_diagnostic(self):
        run=fresh("existing_primary_known_close_false"); o=run.owner
        original=run.exceptions["err0"]; self.assertIs(o.primary,original)
        issued=o.snapshot(); data=issued.to_dict(); leaf=data["primary_exception"]
        # This probe intentionally inspects the raw diagnostic leaf BEFORE the
        # driver's identity-label normalization can hide a mutable reference.
        self.assertIsInstance(leaf,BaseException)
        before=(type(leaf).__name__,tuple(leaf.args),str(leaf))
        original.args=("mutated_original_after_snapshot",)
        after_leaf=issued.to_dict()["primary_exception"]
        after=(type(after_leaf).__name__,tuple(after_leaf.args),str(after_leaf))
        self.assertEqual(after,before,"already-issued diagnostic leaked original Exception.args")
        self.assertIs(o.primary,original)

    def test_source_purity_fixed_inputs_and_no_IO_during_core(self):
        tree=ast.parse(SOURCE.read_bytes())
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): self.assertTrue(all(a.name not in ("os","sys","ctypes","subprocess","socket","pathlib","importlib") for a in node.names))
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name): self.assertNotIn(node.func.id,("open","eval","exec","compile","__import__"))
            if isinstance(node,ast.Constant) and type(node.value) is str:
                self.assertNotIn("RAW-ADOPTION-FIXTURES",node.value)
                self.assertNotIn("same_owner_early_handoff",node.value)
        self.assertEqual(D.AUDIT_DENIALS,[])


if __name__=="__main__":
    assert not REPORT.exists()
    source_before=D.pin(SOURCE)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CoreTests))
    report=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",methods=result.testsRun,
        failures=[dict(test=str(test),detail=detail) for test,detail in result.failures],errors=[dict(test=str(test),detail=detail) for test,detail in result.errors],
        core=source_before,source_unchanged=D.pin(SOURCE)==source_before,driver=D.pin(HERE/"raw_adoption_fixture_driver_v1.py"),
        checker=D.pin(Path(__file__).resolve()),fixture=D.pin(D.FIXTURE_PATH),schema=D.pin(D.SCHEMA_PATH),
        runs=RUNS,extras=EXTRA,all32_matched=sum(r["matched"] for r in RUNS),checkpoint_count=sum(len(r["checkpoints"]) for r in RUNS),
        actual_snapshots=sum(r["snapshot_count"] for r in RUNS),audit_denials=D.AUDIT_DENIALS,
        scope="Actual new pure-core methods under frozen literal inputs and independent ordinary API faults; no actual FFI/C/port/production/source qualification.",
        elapsed_seconds=time.monotonic()-STARTED,FFI_API_calls=0,SDK_calls=0,old_payload_or_sourceclosure_operations=0,
        FFI_registration_proven=False,production_owner_bound=False,profile_qualified=False,runtime_authorized=False)
    with REPORT.open("xb") as out: out.write(D.canonical(report)+b"\n")
    print(json.dumps(dict(proof=D.pin(REPORT),status=report["status"],methods=result.testsRun,all32_matched=report["all32_matched"],checkpoints=report["checkpoint_count"])))
    raise SystemExit(0 if result.wasSuccessful() else 1)
