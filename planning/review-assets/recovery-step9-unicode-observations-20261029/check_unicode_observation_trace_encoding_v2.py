"""Narrow fictional-v2 encoding/formula checks; NOT observe() implementation."""
import hashlib
import json
from pathlib import Path
import time
import unittest

HERE=Path(__file__).resolve().parent
TARGET=HERE/"UNICODE-OBSERVATIONS-TRACE-FIXTURES-v2.json"
REPORT=HERE/"UNICODE-OBSERVATIONS-TRACE-ENCODING-PROOF-v2.json"
STARTED=time.monotonic()


def sha(raw): return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")


def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=sha(raw))


def lines(base):
    raw=bytes.fromhex(base["raw_hex"]); assert raw.endswith(b"\n")
    return [line+b"\n" for line in raw[:-1].split(b"\n")]


def rows(base): return [json.loads(line) for line in lines(base)]


assert pin(TARGET)["sha256"]=="cecd6aad28b91a526541ffc1694e5fa9e7c91749f8b920453316314319bf065b"
F=json.loads(TARGET.read_bytes())
V1=json.loads((HERE/"UNICODE-OBSERVATIONS-TRACE-FIXTURES-v1.json").read_bytes())
B={base["id"]:base for base in F["base_traces"]}


class SupplementEncoding(unittest.TestCase):
    def setUp(self):
        if time.monotonic()-STARTED>20: raise TimeoutError("Encoding supplement20s")

    def test_preserved_v1_and_exact_prior_records(self):
        self.assertEqual(F["base_traces"][:4],V1["base_traces"])
        for key in ("scenarios","callback_cases","sources","synthetic_context_sha256","in_memory_pack"):
            self.assertEqual(F[key],V1[key])
        for row in F["v2_delta"]["prior_inputs"].values(): self.assertEqual(pin(Path(row["path"])),row)
        self.assertEqual(len(F["base_traces"]),6)
        for key in ("validator_implemented","profile_qualified","originals_authenticated","runtime_authorized"):
            self.assertIs(F[key],False)

    def test_all_six_literal_frames_caps_and_markers(self):
        for base in F["base_traces"]:
            raw=bytes.fromhex(base["raw_hex"]); framed=lines(base); offset=0; offsets=[]
            self.assertEqual((len(raw),sha(raw)),(base["bytes"],base["sha256"]))
            self.assertEqual(len(framed),base["row_count"])
            self.assertLessEqual(len(framed),276); self.assertLessEqual(len(raw),7995392)
            for i,line in enumerate(framed):
                row=json.loads(line)
                self.assertEqual(canonical(row)+b"\n",line); self.assertEqual(row["row_sequence"],i)
                cap=65536 if row["event"] in ("unicode_case_result","unicode_selected_prefix_result") else 8192
                self.assertLessEqual(len(line),cap); offsets.append(offset); offset+=len(line)
            self.assertEqual(offsets,base["row_offsets"])
            marker=base["failure_marker_hex"]
            if marker is not None:
                marker_bytes=bytes.fromhex(marker); m=json.loads(marker_bytes); last=json.loads(framed[-1])
                self.assertLessEqual(len(marker_bytes),65536)
                self.assertEqual((m["failure_row_publication"]["known_bytes"],m["failure_row_publication"]["sha256"]),(len(framed[-1]),sha(framed[-1])))
                self.assertEqual(m["row_sequence_reserved"],last["row_sequence"])
                self.assertEqual(m["elapsed_ms"],last["elapsed_ms"])
                identity={key:m[key] for key in ("pid","error_class","reason_code","elapsed_ms","row_sequence_reserved")}
                self.assertEqual(sha(canonical(identity)),m["primary_failure_id"])
                self.assertEqual(m["primary_failure_id"],last["body"]["primary_failure_id"])

    def test_mixed_EOG_exact_one_row_delta_geometry_kept(self):
        old=B["complete_membership_conflict"]; new=B["complete_mixed_EOG_unknown_membership"]
        old_rows,new_rows=rows(old),rows(new)
        self.assertEqual([i for i,(a,b) in enumerate(zip(old_rows,new_rows)) if a!=b],[24])
        a,b=old_rows[24]["body"],new_rows[24]["body"]
        for key in set(a)-{"observation","matches_authored_native_expectation"}: self.assertEqual(a[key],b[key])
        self.assertEqual(b["QC"],dict(status="ok",reason=None))
        self.assertEqual(b["observation"],dict(status="native_EOG_disagreement",native_member=None,all_input_tokens_admitted=True,
            first_rejected_token_index=None,first_rejected_byte_start=None,first_rejected_byte_end=None,
            completion_EOG=[dict(id=1022,admitted=True),dict(id=1023,admitted=False)]))
        self.assertIsNone(b["matches_authored_native_expectation"])
        self.assertEqual(new["authored_geometry_summary"],old["authored_geometry_summary"])
        self.assertEqual(new["authored_final_counters"],old["authored_final_counters"])
        self.assertEqual(new["failure_marker_hex"],old["failure_marker_hex"])
        p=new["expected_projection"]
        self.assertEqual((p["validated_native_geometry_rows"],p["known_membership_outcomes"]),(78,77))
        self.assertIsNone(p["all_expected_membership_outcomes_match"])

    def test_existing_rejection_formula_reference_not_duplicate(self):
        reference=F["supplemental_branch_references"][0]
        self.assertEqual(reference["id"],"existing_coherent_native_token_rejection")
        self.assertEqual(reference["base_sha256"],B["complete_positive"]["sha256"])
        positive=rows(B["complete_positive"]); before,result=positive[151:153]; body=result["body"]
        self.assertEqual(body["case_id"],"negative/unknown_quote")
        self.assertEqual(body["QC"],dict(status="ok",reason=None))
        ledger=body["ledger"]; o=body["observation"]; expected=reference["expected"]
        self.assertEqual((len(ledger["token_ids"]),o["first_rejected_token_index"]),(227,226))
        start=sum(ledger["piece_byte_lengths"][:226]); end=start+ledger["piece_byte_lengths"][226]
        self.assertEqual([start,end],[225,226]); self.assertEqual(expected["first_rejected_interval"],[start,end])
        self.assertIs(o["native_member"],False); self.assertIsNone(o["completion_EOG"])
        self.assertIs(body["matches_authored_native_expectation"],True)
        self.assertIsNotNone(body["compact_analysis"]["counts"])
        for api,n in expected["native_call_delta_each_attempted_returned"].items():
            for outcome in ("attempted","returned"):
                self.assertEqual(result["native_call_counters"][api][outcome]-before["native_call_counters"][api][outcome],n)
        self.assertEqual(result["native_state"]["token_work_reserved"]-before["native_state"]["token_work_reserved"],227)
        rejected=[r["body"]["case_ordinal"] for r in positive if r["event"]=="unicode_case_result" and r["body"]["observation"]["status"]=="native_token_rejection"]
        self.assertEqual(rejected,[68,69,70,72,73,74,75,76,77])

    def test_nonpopulation_unknown_exact_case_and_known_population(self):
        new=B["complete_nonpopulation_QC_unknown"]; r=rows(new); positive=rows(B["complete_positive"])
        self.assertEqual(r[:152],positive[:152])
        body=r[152]["body"]
        self.assertEqual(body["case_ordinal"],68); self.assertIs(body["authored_expected"]["coverage_population"],False)
        self.assertEqual(body["QC"],dict(status="unknown",reason="tokenize_size_invalid"))
        self.assertIsNone(body["ledger"]); self.assertIsNone(body["matches_authored_native_expectation"])
        self.assertEqual(body["compact_analysis"],dict(counts=None,matrix=None,zero_piece_count=None))
        self.assertEqual(body["observation"]["status"],"not_attempted_QC_unknown")
        self.assertTrue(all(value is None for key,value in body["observation"].items() if key!="status"))
        p_cases={row["body"]["case_ordinal"]:row["body"] for row in positive if row["event"]=="unicode_case_result"}
        n_cases={row["body"]["case_ordinal"]:row["body"] for row in r if row["event"]=="unicode_case_result"}
        self.assertEqual(len(n_cases),84)
        for index in set(range(84))-{68}: self.assertEqual(n_cases[index],p_cases[index])
        summary=new["authored_geometry_summary"]; original=B["complete_positive"]["authored_geometry_summary"]
        for key in ("coverage_complete","counts","matrix","selectors","selected_prefixes","required_available","known_counts_lower_bound","known_matrix_lower_bound","unknown_population_ordinals"):
            self.assertEqual(summary[key],original[key])
        self.assertIs(summary["all_case_QC_complete"],False)
        self.assertEqual(summary["unknown_population_ordinals"],[])
        self.assertEqual(r[183]["event"],"unicode_coverage_summary")
        self.assertEqual(r[183]["body"]["case_counts"],dict(expected=84,computed=84,written=84,native=78,harness=6,population=68))
        self.assertEqual(r[183]["native_state"]["coverage_state"],"complete_available")

    def test_nonpopulation_unknown_counter_delta_and_clean_failure(self):
        new=B["complete_nonpopulation_QC_unknown"]; r=rows(new); old=rows(B["complete_membership_conflict"])
        expected=F["supplemental_branch_references"][0]["expected"]["native_call_delta_each_attempted_returned"]
        removed=dict(expected); removed["llama_tokenize"]-=1
        for i,(source,newrow) in enumerate(zip(old,r)):
            for name,c in source["native_call_counters"].items():
                for outcome in ("attempted","returned"):
                    n=c[outcome]-(removed[name] if i>=152 else 0)
                    self.assertEqual(newrow["native_call_counters"][name][outcome],n,(i,name,outcome))
            self.assertEqual(newrow["native_state"]["token_work_reserved"],source["native_state"]["token_work_reserved"]-(227 if i>=152 else 0))
        row=r[152]; before=r[151]
        self.assertEqual((row["native_state"]["last_attempt"],row["native_state"]["last_return"]),("llama_tokenize","llama_tokenize"))
        self.assertEqual(row["native_state"]["last_tokenize_return"],0)
        for name,c in row["native_call_counters"].items():
            expected_delta=1 if name=="llama_tokenize" else 0
            for outcome in ("attempted","returned"):
                self.assertEqual(c[outcome]-before["native_call_counters"][name][outcome],expected_delta)
        self.assertEqual(r[-1]["body"]["reason_code"],"document_QC_unknown")
        self.assertEqual(r[-1]["event"],"failure")
        for prefix in ("model","backend"):
            self.assertIs(r[-1]["native_state"][prefix+"_free_return_observed"],True)
            self.assertIs(r[-1]["native_state"][prefix+"_owned"],False)
            self.assertIs(r[-1]["native_state"][prefix+"_release_unknown"],False)
        self.assertNotIn("unicode_selection_plan",[row["event"] for row in r])
        projection=new["expected_projection"]
        self.assertEqual((projection["validated_native_geometry_rows"],projection["known_membership_outcomes"]),(77,77))
        self.assertEqual(projection["unique_selected_prefix_results"],0)
        self.assertEqual(projection["classification"],"complete_negative_consistent")


if __name__=="__main__":
    assert not REPORT.exists()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SupplementEncoding))
    proof=dict(schema_version=2,status="passed" if result.wasSuccessful() else "failed",tests=result.testsRun,
        failures=[dict(test=str(test),detail=detail) for test,detail in result.failures],errors=[dict(test=str(test),detail=detail) for test,detail in result.errors],
        fixture=pin(TARGET),freeze=pin(HERE/"UNICODE-OBSERVATIONS-TRACE-FREEZE-v2.json"),checker=pin(Path(__file__).resolve()),
        scope="Narrow fictional literal/source-branch bookkeeping only, not an observation validator or derived classification proof.",
        observation_validator_implemented=False,pack_file_created=False,native_payload_SDK_operations=0,profile_qualified=False,
        elapsed_seconds=time.monotonic()-STARTED)
    REPORT.write_bytes(canonical(proof)+b"\n"); print(json.dumps(pin(REPORT)))
    raise SystemExit(0 if result.wasSuccessful() else 1)
