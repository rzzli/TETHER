"""Check fictional fixture encoding/source links; NOT an observation validator.

This checks literal authored containers, source case frames, arithmetic and caps.
It does not implement observe(), infer authored classifications, or qualify any
native observation. Only new review metadata is consumed; no runtime pack file.
"""
import hashlib
import json
from pathlib import Path
import time
import unittest

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent
CONTROL = REVIEW / "recovery-step9-unicode-control-20261029"
WIRE = REVIEW / "recovery-step9-unicode-wire-20261029"
FIXTURE = HERE / "UNICODE-OBSERVATIONS-TRACE-FIXTURES-v1.json"
REPORT = HERE / "UNICODE-OBSERVATIONS-TRACE-ENCODING-PROOF-v1.json"
STARTED = time.monotonic()


def sha(raw): return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw))


def budget():
    if time.monotonic()-STARTED > 20: raise TimeoutError("Fixture encoding check20s")


RAW = FIXTURE.read_bytes()
assert sha(RAW) == "113bdf35742cf0be7eeae760dba966220ed0941d61de6254c89d3c7371b86ef1"
F = json.loads(RAW)
BASES = {base["id"]: base for base in F["base_traces"]}
CONTEXT = json.loads((HERE/"UNICODE-OBSERVATIONS-SYNTHETIC-CONTEXT-v1.json").read_bytes())
CORPUS = json.loads((CONTROL/"UNICODE-CONTROL-CORPUS-v1.json").read_bytes())["cases"]
SEMANTICS = json.loads((WIRE/"UNICODE-WIRE-DESIGN-CONTRACT-v2.json").read_bytes())["semantic_contract"]


def lines_of(base):
    raw = bytes.fromhex(base["raw_hex"])
    assert raw.endswith(b"\n")
    return [part+b"\n" for part in raw[:-1].split(b"\n")]


def rows_of(base): return [json.loads(line) for line in lines_of(base)]


class FixtureEncoding(unittest.TestCase):
    def setUp(self): budget()

    def test_exact_inputs_and_scope(self):
        self.assertEqual(len(F["base_traces"]),4)
        for row in F["sources"]:
            self.assertEqual(pin(Path(row["path"])),row)
        self.assertEqual(F["in_memory_pack"],dict(bytes=37766,sha256=CONTEXT["expected_newpack_sha256"],persisted=False))
        for key in ("validator_implemented","profile_qualified","originals_authenticated","runtime_authorized"):
            self.assertIs(F[key],False)
        for key in ("actual_native_observations","SDK_native_payload_operations","old_run_operations"):
            self.assertEqual(F[key],0)

    def test_literal_roundtrips_caps_and_offsets(self):
        caps = {"setup":8192,"unicode_before_case":8192,"unicode_case_result":65536,
                "unicode_selected_prefix_result":65536,"footer":8192}
        self.assertEqual(len(F["scenarios"]),36)
        for base in BASES.values():
            lines=lines_of(base); raw=b"".join(lines); offset=0
            self.assertEqual((len(raw),sha(raw)),(base["bytes"],base["sha256"]))
            self.assertEqual(len(lines),base["row_count"])
            self.assertLessEqual(len(lines),276); self.assertLessEqual(len(raw),7995392)
            offsets=[]
            for i,line in enumerate(lines):
                budget(); row=json.loads(line)
                self.assertEqual(canonical(row)+b"\n",line)
                self.assertEqual(row["row_sequence"],i)
                bucket="setup" if i<15 else row["event"]
                cap=caps.get(bucket,caps["footer"])
                self.assertLessEqual(len(line),cap)
                offsets.append(offset); offset+=len(line)
            self.assertEqual(offsets,base["row_offsets"])
            marker=base["failure_marker_hex"]
            if marker is not None: self.assertLessEqual(len(bytes.fromhex(marker)),65536)

    def test_shared_piece_ids_source84_and_null_harness(self):
        table={row["id"]:bytes.fromhex(row["piece_hex"]) for row in CONTEXT["ordinary_piece_table"]}
        self.assertEqual(len(table),117); self.assertEqual(len(set(table.values())),117)
        self.assertEqual(table[0],b""); self.assertFalse(set(table)&set(CONTEXT["EOG_ids"]))
        null_keys={"native_member","all_input_tokens_admitted","first_rejected_token_index",
                   "first_rejected_byte_start","first_rejected_byte_end","completion_EOG"}
        for base in BASES.values():
            rows=rows_of(base)
            cases=[row for row in rows if row["event"]=="unicode_case_result"]
            self.assertEqual(len(cases),84)
            for index,(row,source) in enumerate(zip(cases,CORPUS)):
                body=row["body"]; self.assertEqual(body["case_ordinal"],index)
                self.assertEqual(body["case_id"],source["id"])
                self.assertEqual(body["stage_instance_id"],source["stage_id"])
                self.assertEqual(body["grammar_sha256"],source["grammar_sha256"])
                source_raw=bytes.fromhex(source["raw_hex"])
                self.assertEqual((body["raw_bytes"],body["raw_sha256"]),(len(source_raw),sha(source_raw)))
                self.assertEqual(body["authored_expected"]["coverage_population"],source["coverage_population"])
                ledger=body["ledger"]
                if ledger is not None:
                    pieces=[bytes.fromhex(x) for x in ledger["piece_hex"]]
                    self.assertEqual(b"".join(pieces),source_raw)
                    self.assertEqual(ledger["piece_byte_lengths"],[len(p) for p in pieces])
                    self.assertEqual([table[token] for token in ledger["token_ids"]],pieces)
                if not source["expected"]["native_byte_eligible"]:
                    self.assertIsNone(ledger)
                    self.assertEqual(set(body["observation"]),null_keys|{"status"})
                    for key in null_keys: self.assertIsNone(body["observation"][key])
                    self.assertEqual(body["compact_analysis"],dict(counts=None,matrix=None,zero_piece_count=None))

    def test_setup_source_vectors_and_final_cap_arithmetic(self):
        names=SEMANTICS["API_accounting"]["names"]
        for base in BASES.values():
            rows=rows_of(base)
            for row,expected in zip(rows,SEMANTICS["event_order"]["setup_events"]):
                self.assertEqual(row["event"],expected["event"])
                vector={name:1024 if isinstance(n,str) else n for name,n in expected["cumulative_attempted_equals_returned"].items()}
                self.assertEqual(row["native_call_counters"],{name:dict(attempted=n,returned=n) for name,n in vector.items()})
            final=rows[-1]; counters=final["native_call_counters"]
            self.assertEqual(set(counters),set(names))
            self.assertEqual(counters,base["authored_final_counters"])
            self.assertEqual(sum(c["attempted"] for c in counters.values()),final["native_state"]["total_attempted"])
            self.assertEqual(sum(c["returned"] for c in counters.values()),final["native_state"]["total_returned"])
            self.assertLessEqual(final["native_state"]["total_attempted"],530477)
            self.assertLessEqual(final["native_state"]["token_work_reserved"],69108)
            for name,c in counters.items():
                self.assertEqual(c["attempted"],c["returned"])
                self.assertLessEqual(c["attempted"],SEMANTICS["API_accounting"]["hard_caps"][name])

    def test_positive_191_u3_write_lag_and_prefix_table(self):
        base=BASES["complete_positive"]; rows=rows_of(base)
        self.assertEqual(len(rows),191)
        for index in range(84):
            before,result=rows[15+2*index:17+2*index]
            self.assertEqual((before["event"],result["event"]),("unicode_before_case","unicode_case_result"))
            self.assertEqual((before["native_state"]["cases_computed"],before["native_state"]["case_results_written"]),(index,index))
            self.assertEqual((result["native_state"]["cases_computed"],result["native_state"]["case_results_written"]),(index+1,index))
        self.assertEqual([r["event"] for r in rows[183:185]], ["unicode_coverage_summary","unicode_selection_plan"])
        self.assertEqual([r["event"] for r in rows[-3:]], ["unicode_cleanup_returned","unicode_batch_returned","child_normal_completion"])
        self.assertEqual(rows[-1]["native_state"]["selected_prefix_results_written"],3)
        selected=[r for r in rows if r["event"]=="unicode_selected_prefix_result"]
        self.assertEqual(len(selected),3)
        for index,row in enumerate(selected):
            self.assertEqual((row["native_state"]["selected_prefixes_computed"],row["native_state"]["selected_prefix_results_written"]),(index+1,index))
            b=row["body"]; pending=b["pending_interval"]; piece=b["piece_interval"]
            self.assertLess(pending[0],b["byte_cut"]); self.assertLess(b["byte_cut"],pending[1])
            self.assertEqual(piece[1],b["byte_cut"])
            self.assertEqual(b["complete_widths"],sorted(set(b["complete_widths"])))
        self.assertIsNone(base["failure_marker_hex"])

    def test_authored_negative_distinctions_and_callbacks(self):
        known=BASES["complete_known_mixed_unavailable"]["authored_geometry_summary"]
        self.assertEqual(known["counts"]["same_piece_complete_scalar_then_pending"],0)
        self.assertIs(known["required_available"],False)
        unknown=BASES["complete_population_QC_unknown"]["authored_geometry_summary"]
        self.assertIsNone(unknown["counts"]); self.assertIsNone(unknown["selectors"])
        self.assertEqual(unknown["unknown_population_ordinals"],[4])
        for name in ("complete_known_mixed_unavailable","complete_membership_conflict","complete_population_QC_unknown"):
            base=BASES[name]; rows=rows_of(base)
            self.assertEqual(rows[-1]["event"],"failure")
            self.assertNotIn("unicode_cleanup_returned",[r["event"] for r in rows])
            self.assertIsNotNone(base["failure_marker_hex"])
            self.assertEqual(base["expected_projection"]["classification"],"complete_negative_consistent")
        self.assertEqual(len(F["callback_cases"]),11)
        self.assertTrue(all(len(row["positions"])==3 for row in F["callback_cases"]))

    def test_literal_mutation_materialization(self):
        ids=set()
        for scenario in F["scenarios"]:
            self.assertNotIn(scenario["id"],ids); ids.add(scenario["id"])
            base=BASES[scenario["base_trace"]]
            self.assertEqual(scenario["base_sha256"],base["sha256"])
            lines=lines_of(base)
            if scenario["prefix_rows"] is not None: lines=lines[:scenario["prefix_rows"]]
            for item in scenario["replace_rows"]: lines[item["index"]]=bytes.fromhex(item["raw_hex"])
            lines.extend(bytes.fromhex(x) for x in scenario["append_rows_hex"])
            raw=b"".join(lines)+bytes.fromhex(scenario["tail_hex"])
            self.assertEqual((len(raw),sha(raw)),(scenario["materialized_bytes"],scenario["materialized_sha256"]))
            for key in ("profile_qualified","originals_authenticated","runtime_authorized"):
                self.assertIs(scenario["expected_projection"][key],False)
        required={"first_case_own_write_lag","unterminated_mid_scalar_tail","unknown_model_release_no_backend_free",
                  "marker_only_after_complete_rows","terminal_failure_after_complete_rows","completed_row_after_terminal_failure"}
        self.assertTrue(required<=ids)


if __name__=="__main__":
    assert not REPORT.exists()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(FixtureEncoding)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    proof=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",tests=result.testsRun,
        failures=[dict(test=str(test),detail=detail) for test,detail in result.failures],
        errors=[dict(test=str(test),detail=detail) for test,detail in result.errors],
        fixture=pin(FIXTURE),checker=pin(Path(__file__).resolve()),freeze=pin(HERE/"UNICODE-OBSERVATIONS-TRACE-FREEZE-v1.json"),
        elapsed_seconds=time.monotonic()-STARTED,scope="Fictional container encoding/framing/source-case bookkeeping only; expected semantic classifications remain authored, NOT validator outputs.",
        observation_validator_implemented=False,pack_file_created=False,native_calls=0,profile_qualified=False)
    REPORT.write_bytes(canonical(proof)+b"\n")
    print(json.dumps(pin(REPORT)))
    raise SystemExit(0 if result.wasSuccessful() else 1)
