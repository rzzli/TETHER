"""Static literal/encoding/arithmetic checks only, NOT an adoption interpreter."""
import hashlib
import json
from pathlib import Path
import time
import unittest

HERE=Path(__file__).resolve().parent
REPORT=HERE/"RAW-ADOPTION-LITERAL-SHAPE-PROOF-v2.json"
STARTED=time.monotonic()


def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def same(a,b):
    if type(a) is not type(b): return False
    if type(a) is dict: return set(a)==set(b) and all(same(a[k],b[k]) for k in a)
    if type(a) is list: return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b


def atom_valid(value):
    if type(value) is not dict or set(value)!={"tag","value"}: return False
    t,n=value["tag"],value["value"]
    if t in ("UNOBSERVED","NULL"): return n is None
    if type(n) is not int: return False
    if t=="HANDLE": return 0<=n<2**64
    if t=="BOOL32": return -2**31<=n<2**31
    return t in ("DWORD","COUNT32") and 0<=n<2**32


SCHEMA_PATH=HERE/"ADOPTION-FIXTURE-SCHEMA-v2.json"
FIXTURE_PATH=HERE/"RAW-ADOPTION-FIXTURES-v2.json"
assert pin(SCHEMA_PATH)["sha256"]=="b4b6670c71d08133670af0af357088447c452f0e973f179c07e69702f900ade5"
assert pin(FIXTURE_PATH)["sha256"]=="09f79b6a5f7bca50a3da63f3d95a6041e8bc2acf84ec85f1db5d96a4e7c1d5f6"
S=json.loads(SCHEMA_PATH.read_bytes()); F=json.loads(FIXTURE_PATH.read_bytes())
OLD=json.loads((HERE/"RAW-ADOPTION-FIXTURES-v1.json").read_bytes())
BY={row["id"]:row for row in F["cases"]}
SUMMARY={}


class LiteralShapes(unittest.TestCase):
    def setUp(self):
        if time.monotonic()-STARTED>20: raise TimeoutError("Literal shapes20s")

    def keys(self,value,expected): self.assertIs(type(value),dict); self.assertEqual(set(value),set(expected))

    def test_pins_bounds_families_and_scope(self):
        self.assertEqual(len(F["cases"]),32); self.assertEqual(len(BY),32)
        self.assertEqual({row["family"] for row in F["cases"]},set(S["families"]))
        self.assertEqual(len(S["API_names"]),14)
        self.assertLessEqual(FIXTURE_PATH.stat().st_size,S["bounds"]["UTF8_document_bytes"])
        self.assertEqual(F["schema"],pin(SCHEMA_PATH))
        for row in F["preserved_v1"].values(): self.assertEqual(pin(Path(row["path"])),row)
        for flag in ("successor_implementation_exists","production_authority","profile_qualified"):
            self.assertIs(F[flag],False)
        self.assertEqual(F["actual_API_calls"],0)

    def test_exact_shapes_typed_refs_and_initial_context(self):
        for case in F["cases"]:
            self.keys(case,S["case_exact_keys"]); initial=case["initial"]; self.keys(initial,S["initial_exact_keys"])
            objects=initial["objects"]; self.assertLessEqual(len(objects),24)
            ids={o["id"]:o["kind"] for o in objects}; self.assertEqual(len(ids),len(objects))
            self.assertTrue(all(o["scope"]=="HARNESS_ONLY" for o in objects))
            self.keys(initial["current"],S["current_exact_keys"])
            expected_kind=dict(owner="owner",origin="origin",nonce="nonce",registry="registry",port="port",output="output",
                early_context="source_context",loader="loader",journal="journal")
            for key,ref in initial["current"].items():
                if ref is None: self.assertEqual(key,"early_context"); self.assertIsNone(initial["early_context"])
                else: self.assertEqual(ids[ref],expected_kind[key])
            ns=initial["namespace_state"]
            self.keys(ns,("scope","owner_ref","output_ref","namespace_owned","reservation_ready"))
            self.assertEqual(ns["scope"],"HARNESS_ONLY"); self.assertEqual(ns["owner_ref"],initial["current"]["owner"])
            self.assertEqual(ns["output_ref"],initial["current"]["output"])
            self.assertIs(type(ns["namespace_owned"]),bool); self.assertIs(type(ns["reservation_ready"]),bool)
            self.assertFalse(ns["reservation_ready"] and not ns["namespace_owned"])
            for slot in initial["slots"]: self.keys(slot,S["slot_exact_keys"]); self.assertTrue(atom_valid(slot["handle_fact"]))
            context=initial["early_context"]
            if context is not None:
                self.keys(context,S["early_context_exact_keys"])
                self.assertEqual(context["scope"],"HARNESS_ONLY")
                raw=bytes.fromhex(context["blob_hex"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(),context["digest"])
                self.assertEqual((context["known_read_bytes"],context["hashed_bytes"],context["captured_bytes"]),(len(raw),)*3)

    def test_step_domains_frame_bounds_no_execution(self):
        steps=0
        for case in F["cases"]:
            initial=case["initial"]; buffers={b["id"]:b for b in initial["buffers"]}
            self.assertLessEqual(len(case["steps"]),96); now=initial["clock"]["now_ns"]
            first_reserves={}
            for item in case["steps"]:
                steps+=1; self.keys(item,S["closed_steps"][item["op"]])
                if item["op"]=="clock": self.assertIs(type(item["now_ns"]),int); self.assertGreaterEqual(item["now_ns"],now); now=item["now_ns"]
                if item["op"]=="reserve":
                    self.assertIn(item["api"],S["API_names"]); self.assertIs(type(item["ordinal"]),int); self.assertTrue(0<=item["ordinal"]<=63)
                    first_reserves.setdefault(item["ordinal"],item)
                    if item["api"] in ("ReadFile","WriteFile"):
                        self.assertIs(type(item["requested"]),int); self.assertTrue(1<=item["requested"]<=65536)
                        if item["api"]=="WriteFile": self.assertEqual(len(bytes.fromhex(item["prepared_hex"])),item["requested"])
                        else: self.assertGreaterEqual(buffers[item["buffer_ref"]]["capacity"],item["requested"])
                    else: self.assertIsNone(item["requested"])
                    if item["api"] in S["reserved_buffer_domains"] and item["api"]!="ReadFile":
                        self.assertEqual(buffers[item["buffer_ref"]]["capacity"],S["reserved_buffer_domains"][item["api"]])
                    self.assertIs(type(item["declared_empty"]),bool)
                    if item["declared_empty"]: self.assertEqual(item["api"],"FindFirstFileExW")
                if item["op"] in ("scalar","count","error"):
                    self.assertTrue(atom_valid(item["fact"]))
                    if item["op"]=="count": self.assertEqual(item["fact"]["tag"],"COUNT32"); self.assertIn(first_reserves[item["ordinal"]]["api"],("ReadFile","WriteFile"))
                if item["op"]=="handoff": self.keys(item["refs"],S["current_exact_keys"])
                if item["op"]=="raise": self.assertIn(item["phase"],S["phase_enum"])
            for buffer in initial["buffers"]:
                self.keys(buffer,S["buffer_exact_keys"]); self.assertLessEqual(len(bytes.fromhex(buffer["hex"])),buffer["capacity"])
                self.assertLessEqual(buffer["capacity"],65536)
        SUMMARY["literal_steps"]=steps

    def test_expected_record_arithmetic_and_known_byte_sums(self):
        totals=dict(records=0,invocations=0,scalars=0,counts=0,wrapper_returns=0,reconciled=0)
        for case in F["cases"]:
            e=case["expected"]; self.keys(e,S["expected_exact_keys"]); self.keys(e["counters"],S["counter_exact_keys"])
            self.assertEqual(e["qualification"],S["qualification_exact_value"])
            self.assertTrue(all(value is False for value in e["qualification"].values()))
            r=e["records"]; self.assertLessEqual(len(r),8); self.assertEqual(len({x["ordinal"] for x in r}),len(r))
            authored=e["counters"]
            self.assertEqual(authored["logical_call_reservations"],len(r))
            self.assertEqual(authored["FFI_invocations_reserved"],sum(x["invocation_reserved"] for x in r))
            self.assertEqual(authored["known_scalar_returns"],sum(x["raw_scalar"]["tag"]!="UNOBSERVED" for x in r))
            self.assertEqual(authored["known_count_values"],sum(x["raw_count"]["tag"]!="UNOBSERVED" for x in r))
            self.assertEqual(authored["portable_wrapper_returns"],sum(x["wrapper_state"]=="returned" for x in r))
            self.assertLessEqual(authored["unique_reconciled_ordinals"],len(r))
            reserve={}
            for st in case["steps"]:
                if st["op"]=="reserve": reserve.setdefault(st["ordinal"],st)
            read=write=0
            for record in r:
                self.keys(record,S["expected_record_exact_keys"])
                self.assertTrue(atom_valid(record["raw_scalar"]) and atom_valid(record["raw_count"]) and atom_valid(record["raw_error"]))
                for flag in ("invocation_reserved","scalar_aux_ack","count_aux_ack","right_transfer_ack","count_defined","error_defined"):
                    self.assertIs(type(record[flag]),bool)
                self.assertIn(record["count_state"],S["count_states"])
                if record["api"] in ("ReadFile","WriteFile"):
                    defined=record["raw_scalar"]["tag"]=="BOOL32" and record["raw_scalar"]["value"]!=0 and record["raw_count"]["tag"]=="COUNT32" and record["raw_count"]["value"]<=reserve[record["ordinal"]]["requested"]
                    self.assertIs(record["count_defined"],defined)
                    if defined:
                        if record["api"]=="ReadFile": read+=record["raw_count"]["value"]
                        else: write+=record["raw_count"]["value"]
            early=case["initial"]["early_context"]
            if early: read+=early["known_read_bytes"]
            self.assertEqual(e["known_read_bytes"],read); self.assertEqual(e["known_write_bytes"],write)
            self.assertLessEqual(e["hashed_bytes"],read); self.assertLessEqual(e["captured_bytes"],read)
            for key,n in zip(totals,(len(r),authored["FFI_invocations_reserved"],authored["known_scalar_returns"],authored["known_count_values"],authored["portable_wrapper_returns"],authored["unique_reconciled_ordinals"])): totals[key]+=n
        SUMMARY["authored_expected_totals"]=totals

    def test_nullable_closes_buffers_primary_and_first_facts(self):
        for case in F["cases"]:
            e=case["expected"]
            for slot in e["slots"]:
                self.keys(slot,S["expected_slot_exact_keys"]); self.assertIn(slot["liveness"],S["liveness_enum"])
                self.assertTrue(slot["close_success"] is None or type(slot["close_success"]) is bool)
                self.assertTrue(type(slot["close_invocations"]) is int and slot["close_invocations"] in (0,1))
                if slot["close_invocations"]==0: self.assertIsNone(slot["close_success"])
                if slot["liveness"]=="closed_known": self.assertIs(slot["close_success"],True)
                if slot["liveness"]=="close_failed_known": self.assertIs(slot["close_success"],False)
            for buffer in e["buffers"]: self.keys(buffer,S["expected_buffer_exact_keys"])
            if case["initial"]["primary_exception_ref"] is not None:
                self.assertEqual(e["primary_exception_ref"],case["initial"]["primary_exception_ref"])
        for identity in ("open_first_fact_before_aux","open_first_fact_before_right_transfer"):
            c=BY[identity]; record=c["expected"]["records"][0]
            self.assertEqual(record["raw_scalar"],dict(tag="HANDLE",value=101)); self.assertIs(record["scalar_aux_ack"],False)
            self.assertIs(record["right_transfer_ack"],False); self.assertEqual(c["expected"]["counters"]["known_scalar_returns"],2)
            self.assertEqual(c["expected"]["slots"][0]["close_invocations"],1)
        inc=BY["incremental_scalar_then_count_fold"]
        self.assertEqual(inc["checkpoints"][0]["projection"]["counters.unique_reconciled_ordinals"],1)
        self.assertEqual(inc["checkpoints"][1]["projection"]["counters.unique_reconciled_ordinals"],1)

    def test_exact_narrow_v2_delta_and_continuity(self):
        changed_expected=[]
        for old,new in zip(OLD["cases"],F["cases"]):
            self.assertEqual(old["id"],new["id"])
            for key in ("family","variant","steps","checkpoints"): self.assertTrue(same(old[key],new[key]))
            initial=dict(new["initial"]); ns=initial.pop("namespace_state")
            self.assertTrue(same(initial,old["initial"]))
            early=initial["early_context"] is not None
            self.assertIs(ns["namespace_owned"],early); self.assertIs(ns["reservation_ready"],early)
            if not same(old["expected"],new["expected"]): changed_expected.append(new["id"])
            if early:
                for field in ("namespace_owned","reservation_ready"): self.assertIs(new["expected"][field],True)
                self.assertEqual(new["expected"]["handoff"]["new_origins"],0)
                self.assertEqual(new["expected"]["handoff"]["new_output_reservations"],0)
                self.assertEqual(new["expected"]["known_read_bytes"],5)
        self.assertEqual(changed_expected,["successful_defined_zero","same_owner_early_handoff","same_numeric_start_foreign_origin","same_owner_second_handoff_rejected"])
        zero=BY["successful_defined_zero"]["expected"]
        self.assertEqual((zero["disposition"],zero["primary_code"]),("primitive_complete",None))
        self.assertEqual(zero["known_read_bytes"],0); self.assertIs(zero["read_count_unknown"],False)
        self.assertIs(zero["records"][0]["count_defined"],True)


if __name__=="__main__":
    assert not REPORT.exists()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LiteralShapes))
    proof=dict(schema_version=2,status="passed" if result.wasSuccessful() else "failed",methods=result.testsRun,
        failures=[dict(test=str(test),detail=detail) for test,detail in result.failures],errors=[dict(test=str(test),detail=detail) for test,detail in result.errors],
        fixture=pin(FIXTURE_PATH),schema=pin(SCHEMA_PATH),checker=pin(Path(__file__).resolve()),summary=SUMMARY,
        scope="Closed literal shape/encoding/expected arithmetic only, not a raw-adopter transition implementation or observed port behavior.",
        successor_implementation_executed=False,actual_API_calls=0,old_payload_or_sourceclosure_operations=0,profile_qualified=False,
        elapsed_seconds=time.monotonic()-STARTED)
    with REPORT.open("xb") as out: out.write(json.dumps(proof,sort_keys=True,indent=2).encode("utf-8")+b"\n")
    print(json.dumps(dict(proof=pin(REPORT),status=proof["status"],methods=result.testsRun)))
    raise SystemExit(0 if result.wasSuccessful() else 1)
