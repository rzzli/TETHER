"""Focused pure framing/completeness/call-ledger vectors; no SDK or filesystem paths from reports."""
import copy
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "module_census_validation_v1.py"
FIXTURE_SOURCE = HERE / "census_fixture_v1.py"
WIRE = HERE / "SELF-MODULE-CENSUS-WIRE-v2.json"
REPORT = HERE / "SELF-MODULE-CENSUS-VALIDATION-PURE-PROOF-v1.json"
DENIED, VECTORS = [], []


def guard(event, args):
    if event in ("subprocess.Popen", "os.system", "ctypes.dlopen") or event.startswith("socket."):
        DENIED.append(event); raise RuntimeError("Pure census validation only")
    if event == "open" and args and isinstance(args[0], (str, bytes)) and "neveropen" in str(args[0]).lower():
        DENIED.append("reported_path_open"); raise RuntimeError("Never open reported module paths")


sys.addaudithook(guard)
def load(name, path):
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
v = load("census_pure_validation", SOURCE)
f = load("census_authored_fixtures", FIXTURE_SOURCE)


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def validate(item, label):
    VECTORS.append(label)
    return v.validate_census_rows(item["rows"], expected_pid=item["expected_pid"],
        expected_executable=item["expected_executable"], expected_runtime=item["expected_runtime"],
        raw_lines=item["raw_lines"], attempt_bytes=item["attempt_bytes"])


class Checks(unittest.TestCase):
    def rejected(self, item, label, *, reframe=True):
        if reframe: f.reframe(item)
        with self.assertRaises(v.CensusValidationError): validate(item, label)

    def test_complete_unlisted_and_exact64_natural_end(self):
        for count in (6,64):
            item=f.make_census_fixture(count=count); result=validate(item,"complete-"+str(count))
            self.assertEqual(result["entries_recorded"],count)
            self.assertFalse(result["ABI_eligibility_established"])
            self.assertGreater(result["category_counts"]["unlisted_report"],0)
            self.assertEqual(result["census_API_counters"]["CloseHandle"],dict(reserved=1,returned=1))

    def test_full_numeric_UTF16_survives_optional_UTF8_failure(self):
        for tail in ("astral_\U0001f600.dll","unpaired_\ud800.dll"):
            item=f.make_census_fixture(unknown_paths=("C:\\NeverOpen\\"+tail,))
            if "astral" in tail:
                row=next(r for r in item["rows"] if r.get("event")=="module_metadata" and r["ordinal"]==6)
                for key in ("snapshot_name","path"):
                    row[key]["utf8_conversion"]="failed";row[key]["utf8"]=None
                f.reframe(item)
            result=validate(item,"lossless-optional-conversion")
            self.assertTrue(result["metadata_complete"]);self.assertFalse(result["ABI_eligibility_established"])

    def test_snapshot_error_and_65th_entry_are_partial_even_with_footer(self):
        item=f.make_census_fixture()
        r=next(r for r in item["rows"] if r.get("event")=="census_call_returned" and r["api"]=="CreateToolhelp32Snapshot")
        r.update(ok=False,error=24)
        self.rejected(item,"snapshot-ERROR_BAD_LENGTH-no-retry")
        item=f.make_census_fixture(count=64)
        r=[r for r in item["rows"] if r.get("event")=="census_call_returned" and r["api"]=="Module32NextW"][-1]
        r.update(ok=True,error=None,more_entries=True)
        self.rejected(item,"65th-return-counter-stop-is-not-natural")

    def test_failed_or_missing_snapshot_close_cannot_complete(self):
        for missing in (False,True):
            item=f.make_census_fixture()
            if missing:
                item["rows"]=[r for r in item["rows"] if not(r.get("event") in ("census_call_reserved","census_call_returned") and r.get("api")=="CloseHandle")]
            else:
                r=next(r for r in item["rows"] if r.get("event")=="census_call_returned" and r["api"]=="CloseHandle")
                r.update(ok=False,error=6)
            self.rejected(item,"missing-or-failed-snapshot-close")

    def test_API_error_clipping_termination_and_length_cannot_be_hidden(self):
        for kind in ("error","clipping","unterminated","length","prefix"):
            item=f.make_census_fixture(); row=next(r for r in item["rows"] if r.get("event")=="module_metadata")
            query=next(r for r in item["rows"] if r.get("event")=="census_call_returned" and r["call_id"]==row["path_query_call_id"])
            if kind=="error":query.update(ok=False,error=5,returned_count=0)
            elif kind=="clipping":query.update(ok=False,error=122,returned_count=32768,buffer_clipped=True)
            elif kind=="unterminated":row["path_buffer_terminated"]=False
            elif kind=="length":row["path_full_utf16_units_known"]+=1
            else:row["path"]["truncated"]=True
            self.rejected(item,"metadata-"+kind)

    def test_reservation_return_and_natural_end_crosschecks(self):
        for kind in ("id","ordinal","time","counter","natural-error"):
            item=f.make_census_fixture()
            calls=[r for r in item["rows"] if r.get("event")=="census_call_returned"]
            if kind=="id":calls[0]["call_id"]=2
            elif kind=="ordinal":next(r for r in calls if r["api"]=="GetModuleFileNameW")["ordinal"]=2
            elif kind=="time":calls[0]["ended_ms"]=-1
            elif kind=="counter":item["rows"][-1]["counters"]["CloseHandle"]["returned"]=0
            else:[r for r in calls if r["api"]=="Module32NextW"][-1]["error"]=5
            self.rejected(item,"ledger-"+kind)

    def test_footer_cannot_invent_eligibility_target_calls_or_publication(self):
        for key,value in (("ABI_eligibility_established",True),("target_C_queries",1),("Api_constructed",True),
                          ("all_prior_rows_durable",False),("snapshot_close_returned",False),("pid",True)):
            item=f.make_census_fixture();item["rows"][-1][key]=value
            self.rejected(item,"footer-"+key)

    def test_required_core_reports_are_recomputed_and_not_counts_only(self):
        item=f.make_census_fixture();row=next(r for r in item["rows"] if r.get("event")=="module_metadata" and r["ordinal"]==2)
        path=r"C:\NeverOpen\replacement.dll";row["path"]=f.wide(path);row["snapshot_name"]=f.wide("replacement.dll",256)
        row["path_full_utf16_units_known"]=row["path"]["utf16_units"]
        next(r for r in item["rows"] if r.get("event")=="census_call_returned" and r["call_id"]==row["path_query_call_id"])["returned_count"]=row["path_full_utf16_units_known"]
        classification=next(r for r in item["rows"] if r.get("event")=="module_census_classification")
        classification["rows"][1].update(category="unlisted_report",system_directory_matches=False,system_basename_listed=False)
        self.rejected(item,"missing-required-core-with-forged-all-one-counts")

    def test_raw_bytes_and_decoded_data_are_bound(self):
        item=f.make_census_fixture();item["rows"][-1]["metadata_complete"]=False
        self.rejected(item,"decoded-wire-mismatch",reframe=False)
        item=f.make_census_fixture();item["rows"][-1]["structured_bytes_written_known_before_complete"]+=1
        f.reframe(item,repair_prefix_bytes=False)
        self.rejected(item,"forged-byte-counter",reframe=False)
        item=f.make_census_fixture();item["raw_lines"][0]=item["raw_lines"][0].replace(b'"event":',b'"event":"duplicate","event":')
        self.rejected(item,"duplicate-JSON-key",reframe=False)

    def test_structured_total_row_and_terminal_reserve_caps(self):
        item=f.make_census_fixture();item["raw_lines"][0]=b" "+b"x"*65536+b"\n"
        self.rejected(item,"row-cap",reframe=False)
        item=f.make_census_fixture()
        target=2097152-65536+1
        remaining=target-item["attempt_bytes"]-sum(len(x) for x in item["raw_lines"][:-1])
        for i in range(len(item["raw_lines"])-1):
            add=min(65537-len(item["raw_lines"][i]),remaining)
            item["raw_lines"][i]=item["raw_lines"][i][:-1]+b" "*add+b"\n";remaining-=add
        self.assertEqual(remaining,0)
        self.rejected(item,"data-consumes-terminal-reserve",reframe=False)
        item=f.make_census_fixture(count=64)
        remaining=2097153-item["attempt_bytes"]-sum(map(len,item["raw_lines"]))
        for i in range(len(item["raw_lines"])):
            add=min(65537-len(item["raw_lines"][i]),remaining)
            item["raw_lines"][i]=item["raw_lines"][i][:-1]+b" "*add+b"\n";remaining-=add
        self.assertEqual(remaining,0)
        self.rejected(item,"all-child-2MiB-cap",reframe=False)

    def test_wire_limits_and_existing_classification_set_match(self):
        wire=json.loads(WIRE.read_bytes())
        self.assertEqual(pin(WIRE)["sha256"],"228e8af00e3da2cba05cdc4d2523a99812ce84fb43968cd65d6bc08021843934")
        self.assertEqual({api:r["reserved_max"] for api,r in wire["apis"].items()},v.APIS)
        self.assertEqual(wire["bytes"]["all_child_artifacts"],v.TOTAL_BYTES)
        self.assertEqual(wire["bytes"]["terminal_reserve"],v.RESERVE_BYTES)
        self.assertEqual(len(v.SYSTEM_NAMES),16)


if __name__=="__main__":
    if REPORT.exists():raise RuntimeError("Preserve existing proof")
    original=pin(SOURCE)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert pin(SOURCE)==original,"Validator changed during pure run"
    proof=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",tests=result.testsRun,
        failures=[str(c) for c,_ in result.failures],errors=[str(c) for c,_ in result.errors],vectors=len(VECTORS),
        vector_labels=VECTORS,source=original,fixture_source=pin(FIXTURE_SOURCE),wire=pin(WIRE),checker=pin(Path(__file__)),
        denied_real_operations=DENIED,activity=dict(SDK_or_target_API_calls=0,children=0,reported_image_opens=0),
        scope="Pure wire/count/completeness/byte-reserve validation; no native formatting or census result")
    with REPORT.open("x",encoding="utf-8") as stream:json.dump(proof,stream,sort_keys=True,indent=2);stream.write("\n")
    print(json.dumps(dict(proof=str(REPORT),sha256=pin(REPORT)["sha256"],vectors=len(VECTORS))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
