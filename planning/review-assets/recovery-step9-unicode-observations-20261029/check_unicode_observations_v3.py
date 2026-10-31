"""Actual pure validator tests against pre-frozen fictional histories/faults."""
import ast
import copy
from dataclasses import FrozenInstanceError, replace as dataclass_replace
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest

HERE=Path(__file__).resolve().parent
# Explicit technical support only. Never a runtime/package discovery path.
sys.path.insert(0,str(HERE))
import unicode_observation_test_support_v2 as S

SOURCE=HERE/"unicode_observations_v2.py"
U=S.load(SOURCE,"unicode_observations_v2","47c7cc1fc3889e32c5a3ff3efff50425ef208a041a308f5a447872bd788414b6")
REPORT=HERE/"UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v3.json"
VECTORS=[]


class Count:
    def __init__(self,stop=None,error=None): self.calls=0; self.stop=stop; self.error=error
    def __call__(self):
        S.budget(); self.calls+=1
        if self.calls==self.stop: raise self.error


def observe(raw,marker=None,check=None,b=None):
    return S.invoke(U.observe,raw,S.PROFILE,b or S.bindings(U),failure_marker=marker,check=check or Count())


def exceptions():
    class Stop(BaseException): pass
    return [UnicodeError("caller"),UnicodeDecodeError("utf8",b"x",0,1,"caller"),UnicodeEncodeError("utf8","x",0,1,"caller"),
        UnicodeTranslateError("x",0,1,"caller"),ValueError("caller"),json.JSONDecodeError("caller","x",0),RecursionError("caller"),
        TimeoutError("caller"),KeyboardInterrupt("caller"),SystemExit("caller"),Stop("caller")]


class Observations(unittest.TestCase):
    def setUp(self): S.budget()

    def test_all_six_frozen_bases_and_strict_dispositions(self):
        for base in S.F["base_traces"]:
            with self.subTest(base=base["id"]):
                raw,marker=S.capture(base); result=observe(raw,marker,b=S.bindings(U,base)); data=result.to_dict()
                for key,value in base["expected_projection"].items():
                    self.assertEqual(data[key],value,key); self.assertIs(type(data[key]),type(value),key)
                if base["id"]=="complete_positive": self.assertIs(S.invoke(U.require_complete_success,result,check=Count()),result)
                else:
                    with self.assertRaises(U.ObservationError): S.invoke(U.require_complete_success,result,check=Count())
                VECTORS.append(dict(id=base["id"],classification=data["classification"],validated_rows=data["validated_rows"]))

    def test_all_36_frozen_literal_scenarios(self):
        for scenario in S.F["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                raw,marker=S.materialize(scenario); expected=scenario["expected_projection"]
                if expected.get("raises"):
                    with self.assertRaises(U.ObservationError): observe(raw,marker)
                    VECTORS.append(dict(id=scenario["id"],outcome="ObservationError")); continue
                result=observe(raw,marker); data=result.to_dict()
                for key,value in expected.items():
                    if key in ("raises","strict_requires"): continue
                    self.assertEqual(data[key],value,key); self.assertIs(type(data[key]),type(value),key)
                if expected.get("strict_requires"):
                    with self.assertRaises(U.ObservationError): S.invoke(U.require_complete_success,result,check=Count())
                VECTORS.append(dict(id=scenario["id"],classification=data["classification"]))

    def test_11_callback_families_first_middle_last_observe(self):
        raw,marker=S.capture(S.BASES["complete_positive"]); baseline=Count(); observe(raw,marker,check=baseline)
        self.assertGreater(baseline.calls,3)
        for error in exceptions():
            for name,point in (("first",1),("middle",baseline.calls//2),("last",baseline.calls)):
                with self.subTest(error=type(error).__name__,point=name):
                    check=Count(point,error)
                    try: observe(raw,marker,check=check)
                    except BaseException as caught: self.assertIs(caught,error)
                    else: self.fail("callback returned an Observation")
                    self.assertEqual(check.calls,point)
                    VECTORS.append(dict(id="callback_"+type(error).__name__+"_"+name,callback=point,baseline=baseline.calls,identity_preserved=True))

    def test_11_callback_families_strict_first_last(self):
        result=observe(*S.capture(S.BASES["complete_positive"]))
        for error in exceptions():
            for point in (1,2):
                with self.subTest(error=type(error).__name__,point=point):
                    try: S.invoke(U.require_complete_success,result,check=Count(point,error))
                    except BaseException as caught: self.assertIs(caught,error)
                    else: self.fail("strict callback returned")

    def test_nested_field_mutation_batch(self):
        mutations=[
            ("schema_bool",0,lambda r:r.update(schema_version=True)),
            ("layout_bool",1,lambda r:r["body"]["layouts"].update(bool_size=True)),
            ("wrong_phase",1,lambda r:r["body"].update(module_policy_phase="post_cpu")),
            ("bad_default_type",2,lambda r:r["body"]["defaults"].update(load_mode=True)),
            ("pack_binding",3,lambda r:r["body"].update(pack_sha256="0"*64)),
            ("descriptor_type",4,lambda r:r["body"].update(expected_bytes=True)),
            ("vocab_bool",14,lambda r:r["body"].update(vocabulary_count=True)),
            ("EOG_order",14,lambda r:r["body"].update(EOG_ids=[1023,1022])),
            ("source_expectation",16,lambda r:r["body"]["authored_expected"].update(native_member=False)),
            ("unknown_QC_enum",16,lambda r:r["body"].update(QC=dict(status="unknown",reason="invented"))),
            ("ordinary_bool_ID",16,lambda r:r["body"]["ledger"]["token_ids"].__setitem__(0,False)),
            ("bool_piece_length",16,lambda r:r["body"]["ledger"]["piece_byte_lengths"].__setitem__(0,False)),
            ("uppercase_piece_hex",16,lambda r:r["body"]["ledger"]["piece_hex"].__setitem__(1,"7B")),
            ("duplicate_completion_EOG",16,lambda r:r["body"]["observation"]["completion_EOG"][1].update(id=1022)),
            ("lost_sampler_ownership",16,lambda r:r["native_state"].update(sampler_nonnull_returns=0,sampler_free_returned_nonnull=0)),
            ("all84_count_bool",183,lambda r:r["body"]["case_counts"].update(computed=True)),
            ("selector_bool",184,lambda r:r["body"]["selectors"].update(pending_width2=False)),
            ("coverage_state_rewind",184,lambda r:r["native_state"].update(coverage_state="not_computed")),
            ("witness_width_bool",185,lambda r:r["body"]["witnesses"][0].__setitem__(0,True)),
            ("cleanup_bool_as_int",188,lambda r:r["body"].update(model_free_return_observed=1)),
            ("cleanup_return_contradiction",188,lambda r:r["native_state"].update(model_free_return_observed=False)),
            ("batch_extra_ready",189,lambda r:r["body"].update(ready=True)),
        ]
        for identity,index,edit in mutations:
            with self.subTest(mutation=identity):
                with self.assertRaises(U.ObservationError): observe(S.replace(index,edit))
                VECTORS.append(dict(id=identity,outcome="ObservationError"))

    def test_missing_capture_types_factories_context_and_caps(self):
        absent=observe(None).to_dict(); empty=observe(b"").to_dict()
        self.assertEqual(absent["classification"],"partial_observation"); self.assertIs(absent["raw_capture_present"],False)
        self.assertIs(empty["raw_capture_present"],True); self.assertEqual(empty["raw_bytes"],0)
        for raw in ("",bytearray(),memoryview(b""),[],True,b"x"*7995393):
            with self.subTest(raw_type=type(raw).__name__):
                with self.assertRaises(U.ObservationError): observe(raw)
        raw,_=S.capture(S.BASES["complete_positive"])
        b=S.bindings(U)
        malformed=(dataclass_replace(b,expected_child_pid=True),dataclass_replace(b,expected_newpack_sha256="0"*64),
            dataclass_replace(b,ordered_shard_descriptors=list(b.ordered_shard_descriptors)),
            dataclass_replace(b,ordered_shard_descriptors=(dataclass_replace(b.ordered_shard_descriptors[0],bytes=True),)+b.ordered_shard_descriptors[1:]))
        for value in malformed:
            with self.assertRaises(U.ObservationError): observe(raw,b=value)
        for value in ({"classification":"complete_success_consistent"},object(),object.__new__(U.Observation)):
            with self.assertRaises(U.ObservationError): S.invoke(U.require_complete_success,value,check=Count())
        for value in ({"source_pins":S.PROFILE.source_pins},object(),object.__new__(S.CODEC.ValidatedProfile)):
            with self.assertRaises(U.ObservationError): S.invoke(U.observe,raw,value,b,failure_marker=None,check=Count())
        with self.assertRaises(U.ObservationError): S.invoke(U.observe,raw,S.PROFILE,b,failure_marker=None,check=None)

    def test_results_and_error_prefix_deep_immutability(self):
        result=observe(*S.capture(S.BASES["complete_positive"])); a=result.to_dict(); b=result.to_dict()
        a["cases"][0]["ledger"]["piece_hex"][0]="ff"; a["recomputed_summary"]["counts"]["pending_width2"]=-1
        a["final_native_state"]["stratum_computed"][0]=-1
        self.assertEqual(result.to_dict(),b)
        with self.assertRaises(TypeError): result._data["profile_qualified"]=True
        with self.assertRaises(TypeError): result._data["cases"][0]["ledger"]["piece_hex"][0]="bad"
        with self.assertRaises((FrozenInstanceError,AttributeError)): result._data={}
        raw=S.replace(18,lambda r:r["body"].update(raw_sha256="0"*64))
        with self.assertRaises(U.ObservationError) as caught: observe(raw)
        error=caught.exception; self.assertEqual(error.validated_prefix["validated_case_rows"],1)
        detached=error.to_dict(); detached["validated_prefix"]["stratum_validated_counts"][0]=99
        self.assertNotEqual(error.validated_prefix["stratum_validated_counts"][0],99)
        with self.assertRaises(TypeError): error.validated_prefix["validated_case_rows"]=99

    def test_data_error_integer_conversion_is_bounded(self):
        # CPython3.11's integer-string limit is a data ValueError, not a caller
        # callback. Preserve its type boundary as the component's bounded error.
        with self.assertRaises(U.ObservationError): observe(b'{"schema_version":'+b"9"*5000+b"}\n")

    def test_marker_only_after_normal_cannot_add_new_tokenize_work(self):
        scenario=next(row for row in S.F["scenarios"] if row["id"]=="marker_only_after_complete_rows")
        raw,marker=S.materialize(scenario); m=json.loads(marker)
        c=m["native_call_counters"]["llama_tokenize"]; c["attempted"]+=1; c["returned"]+=1
        s=m["native_state"]; s["total_attempted"]+=1; s["total_returned"]+=1
        s.update(last_attempt="llama_tokenize",last_return="llama_tokenize",last_return_kind=2,last_scalar=0,last_tokenize_return=0)
        with self.assertRaises(U.ObservationError): observe(raw,S.canonical(m)+b"\n")

    def test_supplied_marker_presence_survives_first_bad_row(self):
        for marker,expected in ((b"malformed-marker",True),(None,False)):
            with self.assertRaises(U.ObservationError) as caught:
                observe(b"{bad}\n",marker)
            self.assertIs(caught.exception.validated_prefix["terminal_negative_seen"],expected)
            self.assertEqual(caught.exception.validated_prefix["validated_rows"],0)

    def test_original_clock_stop_after_actual_deepfreeze(self):
        raw,marker=S.capture(S.BASES["complete_positive"])
        original=U._issue; clock=dict(after_freeze=False); error=TimeoutError("original_owner_deadline_after_freeze")
        def measured_issue(data):
            result=original(data)
            clock["after_freeze"]=True
            return result
        def check():
            S.budget()
            if clock["after_freeze"]: raise error
        U._issue=measured_issue
        try:
            try: observe(raw,marker,check=check)
            except BaseException as caught: self.assertIs(caught,error)
            else: self.fail("expired original clock returned an issued Observation")
        finally: U._issue=original
        self.assertTrue(clock["after_freeze"])

    def test_inflight_declared_prefix_remains_partial_without_dependent_frees(self):
        path=HERE/"UNICODE-OBSERVATIONS-PREFIX-PHASE-VECTOR-v1.json"
        self.assertEqual(S.pin(path)["sha256"],"8bc3f027f94e4db9d9681c059f2e3ce125bd17af5c25649ea4b6bb3e8325939c")
        vector=json.loads(path.read_bytes()); raw=bytes.fromhex(vector["raw_hex"])
        result=observe(raw); data=result.to_dict()
        for key,value in vector["expected"].items():
            self.assertEqual(data[key],value,key); self.assertIs(type(data[key]),type(value))
        self.assertEqual(data["terminal_source_phase"],"declared_next_prefix")
        self.assertEqual(data["final_native_call_counters"]["llama_sampler_init_grammar"],dict(attempted=79,returned=78))
        for name in ("llama_model_free","llama_backend_free"):
            self.assertEqual(data["final_native_call_counters"][name],dict(attempted=0,returned=0))
        with self.assertRaises(U.ObservationError): S.invoke(U.require_complete_success,result,check=Count())

    def test_exact_four_guard_delta_and_unchanged_other_AST(self):
        old=ast.parse((HERE/"unicode_observations_v1.py").read_bytes()); new=ast.parse(SOURCE.read_bytes())
        changed={"parse","failure_row","process","marker_record","finish","observe"}
        for tree in (old,new):
            for node in ast.walk(tree):
                if isinstance(node,ast.ClassDef) and node.name=="_Reader":
                    node.body=[item for item in node.body if not isinstance(item,ast.FunctionDef) or item.name!="failure_tail"]
                if isinstance(node,ast.FunctionDef) and node.name in changed: node.body=[]
        self.assertEqual(ast.dump(old,include_attributes=False),ast.dump(new,include_attributes=False))
        self.assertEqual(S.pin(HERE/"unicode_observations_v1.py")["sha256"],"58d6a62fe6a9416c94e5637b615886cecd90bc78ef1559f05f7d1d1ebd6e32c0")

    def test_source_has_no_fixture_or_filesystem_or_clock_dispatch(self):
        tree=ast.parse(SOURCE.read_bytes()); forbidden={"open","exec","eval","compile","__import__"}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): self.assertFalse(any(alias.name in ("os","sys","ctypes","subprocess","pathlib","time","socket") for alias in node.names))
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name): self.assertNotIn(node.func.id,forbidden)
            if isinstance(node,ast.Constant) and type(node.value) is str:
                self.assertNotIn("TRACE-FIXTURES",node.value); self.assertNotIn("complete_positive",node.value)
        self.assertEqual(S.DENIALS,[])


if __name__=="__main__":
    assert not REPORT.exists()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Observations))
    report=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",tests=result.testsRun,
        failures=[dict(test=str(test),detail=detail) for test,detail in result.failures],errors=[dict(test=str(test),detail=detail) for test,detail in result.errors],
        source=S.pin(SOURCE),tables=S.pin(HERE/"unicode_observation_tables_v1.py"),checker=S.pin(Path(__file__).resolve()),support=S.pin(HERE/"unicode_observation_test_support_v2.py"),
        fixture=S.pin(S.FIXTURE),dependency_pins=[S.pin(path) for path,_,_ in S.DEPENDENCIES],vectors=VECTORS,
        preserved_before=[S.pin(HERE/name) for name in ("UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v1.json",
            "UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v2.json","UNICODE-OBSERVATIONS-ROOT-BOUNDARY-BEFORE-v1.json",
            "UNICODE-OBSERVATIONS-PREFIX-PHASE-BEFORE-v1.json","UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-PEER-v1.json")],
        correction_scope=S.pin(HERE/"UNICODE-OBSERVATIONS-ROOT-CORRECTION-SCOPE-v2.json"),
        elapsed_seconds=time.monotonic()-S.STARTED,audit_denials=S.DENIALS,SDK_native_payload_operations=0,pack_file_created=False,
        old_source_qualification=False,profile_qualified=False,production_activation=False)
    REPORT.write_bytes(S.canonical(report)+b"\n"); print(json.dumps(dict(proof=S.pin(REPORT),status=report["status"],tests=result.testsRun)))
    raise SystemExit(0 if result.wasSuccessful() else 1)
