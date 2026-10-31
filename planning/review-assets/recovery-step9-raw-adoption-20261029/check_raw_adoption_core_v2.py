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
import raw_adoption_fixture_driver_v2 as D

STARTED=time.monotonic()
SOURCE=HERE/"raw_adoption_core_v2.py"
PAUSED_SHA="a6877861860ba7a42d22d581d4bfa565984e6ce377d937ff3c4525b04130fd8a"
REPORT=HERE/"RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v2.json"
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
        run.exceptions["extra_injected"]=error
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
                    run.exceptions["extra_injected"]=error
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
        # Inspect raw source metadata before any fixture-label normalization.
        self.assertIs(type(leaf),dict)
        self.assertEqual(set(leaf),{"identity","class_name","message","args_repr","format_failed"})
        self.assertFalse(any(isinstance(v,BaseException) for v in leaf.values()))
        self.assertIs(o.exception_for_token(leaf["identity"]),original)
        before=(leaf["class_name"],leaf["message"],tuple(leaf["args_repr"]),leaf["format_failed"])
        original.args=("mutated_original_after_snapshot",)
        leaf["args_repr"].append("caller_modified_copy")
        leaf["message"]="caller_modified_message"
        after_leaf=issued.to_dict()["primary_exception"]
        after=(after_leaf["class_name"],after_leaf["message"],tuple(after_leaf["args_repr"]),after_leaf["format_failed"])
        self.assertEqual(after,before,"already-issued diagnostic leaked original Exception.args or detached copy")
        self.assertEqual(o.snapshot().to_dict()["primary_exception"]["message"],before[1])
        self.assertIs(o.primary,original)
        with self.assertRaises(TypeError):issued._data["primary_exception"]["message"]="mutable"
        self.assertEqual(D.invoke(run.snapshot)[1]["primary_exception_ref"],"err0")

    def test_diagnostic_format_failure_latches_original_and_keeps_secondary(self):
        run=fresh("open_first_fact_before_aux"); o=run.owner
        formatting_error=MemoryError("diagnostic formatting stopped")
        class FailedText(RuntimeError):
            def __str__(self): raise formatting_error
        original=FailedText("original stop")
        run.exceptions["extra_original"]=original; run.exceptions["extra_formatting"]=formatting_error
        D.invoke(o.raise_exception,None,original,"pre_dispatch")
        self.assertIs(o.primary,original); self.assertIs(o.secondary[-1],formatting_error)
        snapshot=o.snapshot(); data=snapshot.to_dict()
        self.assertIs(o.exception_for_token(data["primary_exception"]["identity"]),original)
        self.assertTrue(data["primary_exception"]["format_failed"])
        self.assertEqual(data["primary_exception"]["message"],"<diagnostic unavailable>")
        self.assertIs(o.exception_for_token(data["secondary_exceptions"][-1]["identity"]),formatting_error)
        self.assertTrue(data["secondary_exceptions"][-1]["format_failed"])
        primary_token=data["primary_exception"]["identity"]
        original.args=("later mutation",); formatting_error.args=("later formatting mutation",)
        after=snapshot.to_dict()
        self.assertIs(after["primary_exception"]["identity"],primary_token)
        self.assertEqual(after["primary_exception"]["args_repr"],[])
        _,normalized=D.invoke(run.snapshot)
        self.assertEqual(normalized["primary_exception_ref"],"extra_original")
        self.assertIn("extra_formatting",normalized["secondary_exception_refs"])

    def test_exception_tokens_are_owner_specific_without_diagnostic_mutation(self):
        first=fresh("existing_primary_known_close_false"); second=fresh("existing_primary_known_close_false")
        a=first.owner.snapshot().to_dict(); b=second.owner.snapshot().to_dict()
        self.assertIsNot(a["primary_exception"]["identity"],b["primary_exception"]["identity"])
        for token in (b["primary_exception"]["identity"],object(),{"class_name":"RuntimeError"}):
            with self.assertRaises(CORE.AdoptionError):D.invoke(first.owner.exception_for_token,token)
        self.assertEqual(first.owner.snapshot().to_dict(),a)
        self.assertIs(first.owner.primary,first.exceptions["err0"])

    def test_identity_deadline_does_not_reclassify_unrelated_runtime_error(self):
        run=fresh("identity_fourth_query_late"); o=run.owner
        for step in run.case["steps"]:
            if step["op"]=="raise":
                error=RuntimeError("not a timeout")
                run.exceptions[step["exception_ref"]]=error
                D.invoke(run.dispatch,step)
                break
            D.invoke(run.dispatch,step)
        _,data=D.invoke(run.snapshot)
        self.assertIs(o.primary,error)
        self.assertEqual(data["primary_code"],"wrapper_exception")
        self.assertEqual(data["disposition"],"incomplete_unknown")
        self.assertEqual(data["counters"]["known_scalar_returns"],1)

    def test_incremental_count_fold_keeps_one_ordinal_and_bytes(self):
        run=fresh();o=run.owner
        call=D.invoke(o.reserve,0,"ReadFile","f0",3,run.refs["buf0"])
        D.invoke(o.invoke,call);D.invoke(o.store_scalar,call,1);D.invoke(o.reconcile,call,run.context.owner)
        before=o.snapshot().to_dict()
        self.assertEqual(before["counters"]["unique_reconciled_ordinals"],1)
        self.assertEqual(before["counters"]["known_count_values"],0)
        self.assertEqual(before["known_read_bytes"],0)
        self.assertEqual(before["records"][0]["count_state"],"pending")
        D.invoke(o.store_count,call,3);D.invoke(o.reconcile,call,run.context.owner)
        after=o.snapshot().to_dict()
        self.assertEqual(after["counters"]["unique_reconciled_ordinals"],1)
        self.assertEqual(after["counters"]["known_scalar_returns"],1)
        self.assertEqual(after["counters"]["known_count_values"],1)
        self.assertEqual(after["known_read_bytes"],3)
        D.invoke(o.store_scalar,call,1);D.invoke(o.store_count,call,3);D.invoke(o.reconcile,call,run.context.owner)
        self.assertEqual(o.snapshot().to_dict()["counters"],after["counters"])
        self.assertEqual(o.snapshot().to_dict()["known_read_bytes"],3)

    def test_registered_unused_buffer_remains_visible_after_rejected_reserve(self):
        result=D.FrozenRun(CORE,BY["conflicting_reserve_keeps_original"]).run()
        self.assertTrue(result["matched"])
        self.assertEqual(result["actual"]["buffers"],[dict(id="buf0",generation=0,hex="616263",retained=True,reusable=True)])
        self.assertEqual(result["actual"]["primary_code"],"duplicate_ordinal")
        self.assertEqual(result["actual"]["counters"]["logical_call_reservations"],2)

    def test_invalid_generation_write_and_reserved_buffer_reuse_preserve_bytes(self):
        for operation in ("write_bad_generation","write_oversize","reuse_reserved"):
            run=fresh();o=run.owner
            before=o.snapshot().to_dict()["buffers"]
            if operation=="reuse_reserved":
                D.invoke(o.reserve,0,"ReadFile","f0",3,run.refs["buf0"])
                action=lambda:D.invoke(o.reuse_buffer,run.refs["buf0"],1,b"xyz")
            elif operation=="write_bad_generation":action=lambda:D.invoke(o.buffer_write,run.refs["buf0"],1,b"xyz")
            else:action=lambda:D.invoke(o.buffer_write,run.refs["buf0"],0,b"four")
            with self.assertRaises(CORE.AdoptionError):action()
            after=o.snapshot().to_dict()["buffers"]
            self.assertEqual(after[0]["hex"],before[0]["hex"])
            self.assertEqual(after[0]["generation"],before[0]["generation"])

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
        core=source_before,source_unchanged=D.pin(SOURCE)==source_before,driver=D.pin(HERE/"raw_adoption_fixture_driver_v2.py"),
        checker=D.pin(Path(__file__).resolve()),fixture=D.pin(D.FIXTURE_PATH),schema=D.pin(D.SCHEMA_PATH),
        preserved_v1_proof=D.pin(HERE/"RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v1.json"),hook_harness_correction=D.pin(HERE/"RAW-ADOPTION-HOOK-IDENTITY-HARNESS-CORRECTION-v1.json"),literal_correction=D.pin(HERE/"RAW-ADOPTION-LITERAL-CORRECTION-PROOF-v3.json"),literal_freeze=D.pin(HERE/"RAW-ADOPTION-FIXTURE-FREEZE-v3.json"),
        runs=RUNS,extras=EXTRA,all32_matched=sum(r["matched"] for r in RUNS),checkpoint_count=sum(len(r["checkpoints"]) for r in RUNS),
        actual_snapshots=sum(r["snapshot_count"] for r in RUNS),audit_denials=D.AUDIT_DENIALS,
        scope="Actual new pure-core methods under frozen literal inputs and independent ordinary API faults; no actual FFI/C/port/production/source qualification.",
        elapsed_seconds=time.monotonic()-STARTED,FFI_API_calls=0,SDK_calls=0,old_payload_or_sourceclosure_operations=0,
        FFI_registration_proven=False,production_owner_bound=False,profile_qualified=False,runtime_authorized=False)
    with REPORT.open("xb") as out: out.write(D.canonical(report)+b"\n")
    print(json.dumps(dict(proof=D.pin(REPORT),status=report["status"],methods=result.testsRun,all32_matched=report["all32_matched"],checkpoints=report["checkpoint_count"])))
    raise SystemExit(0 if result.wasSuccessful() else 1)
