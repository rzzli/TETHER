"""Correct only registration of independently injected hook objects in harness.

Preserves first full proof7fd... and does not edit core/fixtures/driver/checker.
"""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import raw_adoption_fixture_driver_v1 as D

HERE=Path(__file__).resolve().parent
REPORT=HERE/"RAW-ADOPTION-HOOK-IDENTITY-HARNESS-CORRECTION-v1.json"
assert not REPORT.exists()
C=D.load_core(HERE/"raw_adoption_core_v1.py","2ef902a12e20f3ff6eb40bbc37504969970b1d86880ba0c396a6e7ad0e94edcb")
F,S=D.load_literals(); by={case["id"]:case for case in F["cases"]}; outcomes=[]
for component in ("copy","hash"):
    for error in (MemoryError("direct_hook"),KeyboardInterrupt("direct_hook"),SystemExit("direct_hook")):
        run=D.FrozenRun(C,by["success_read_capture_close"]); D.invoke(run.setup)
        run.exceptions["extra_injected"]=error # explicit identity provenance, never supplied as an expected outcome
        o=run.owner; call=D.invoke(o.reserve,0,"ReadFile","f0",3,run.refs["buf0"])
        D.invoke(o.invoke,call); D.invoke(o.store_scalar,call,1); D.invoke(o.store_count,call,3); D.invoke(o.wrapper_return,call)
        def before(): raise error
        caught=None
        try: D.invoke(getattr(o,component),call,before=before)
        except BaseException as actual: caught=actual
        snapshot,data=D.invoke(run.snapshot)
        assert caught is error and o.primary is error and data["primary_exception_ref"]=="extra_injected"
        assert data["known_read_bytes"]==3 and data["hashed_bytes"]==data["captured_bytes"]==0
        assert data["buffers"][0]["hex"]=="616263" and data["buffers"][0]["reusable"] is False
        outcomes.append(dict(component=component,error_class=type(error).__name__,original_identity=True,known_read_bytes=3,hash_and_capture=0,buffer_retained=True))
run=D.FrozenRun(C,by["open_first_fact_before_aux"]); D.invoke(run.setup)
error=MemoryError("first_fact_fold"); run.exceptions["extra_injected"]=error
o=run.owner; call=D.invoke(o.reserve,0,"CreateFileW","f0"); D.invoke(o.invoke,call)
original=o._fold
def stop(_): raise error
o._fold=stop
caught=None
try:
    try: D.invoke(o.store_scalar,call,101)
    except BaseException as actual: caught=actual
finally: o._fold=original
assert caught is error and call.raw_scalar==101 and call.scalar_aux_ack is False
D.invoke(o.raise_exception,call,error,"after_scalar_before_aux"); D.invoke(o.reconcile,call,run.context.owner)
_,data=D.invoke(run.snapshot)
assert o.primary is error and data["primary_exception_ref"]=="extra_injected"
assert data["counters"]["known_scalar_returns"]==1 and data["slots"][0]["close_right"]=="available"
outcomes.append(dict(component="after_scalar_before_fold",error_class="MemoryError",original_identity=True,stored_scalar=101,close_right_recovered=True))
assert not D.AUDIT_DENIALS
report=dict(schema_version=1,status="passed",probes=outcomes,core=D.pin(HERE/"raw_adoption_core_v1.py"),
    preserved_full_before=D.pin(HERE/"RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v1.json"),checker=D.pin(Path(__file__).resolve()),
    correction_scope="Only harness identity-table registration for extra injected objects; all32/frozen expectations/source bytes untouched.",
    actual_FFI_API_calls=0,old_payload_or_sourceclosure_operations=0,profile_qualified=False)
with REPORT.open("xb") as out: out.write(D.canonical(report)+b"\n")
print(json.dumps(D.pin(REPORT)))
