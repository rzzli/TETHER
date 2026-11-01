"""Arbitrary SYNTHETIC ledgers only; no actual P05 outputs or values are read."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("independent_analysis", ROOT / "tools/science/analyze_source_validation_experiment.py")
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)


def fictional_directory():
    cache=ROOT/"data/cache"
    cache.mkdir(parents=True,exist_ok=True)
    return tempfile.TemporaryDirectory(prefix="p05-analysis-fictional-",dir=cache)


def accounting(answerable=4, matched=4, *, abstain=False):
    families = {name: dict(requested=0, answerable=0, expected_unknown_by_reason={}, matched=0,
                           correct_unknown=0, omitted=0, false_asserted=0) for name in
                ("identity_linkage", "reported_context", "reported_measurement", "provider_metric")}
    families["reported_measurement"] = dict(requested=4, answerable=answerable,
        expected_unknown_by_reason={"null_source_value": 4-answerable} if answerable != 4 else {},
        matched=0 if abstain else matched, correct_unknown=0 if abstain else 4-answerable,
        omitted=4 if abstain else 0, false_asserted=0)
    return dict(families=families, unknown_fact_id_emissions=0)


def score(identifier, *, denominator=4, matched=4, abstain=False):
    coverage = float(Fraction(matched, denominator)) if denominator else None
    eligible = not abstain
    passes = {key: bool(eligible and Fraction(matched, denominator) >= threshold) if denominator else None
              for key, threshold in (("60", Fraction(3,5)), ("80", Fraction(4,5)), ("100", Fraction(1)))}
    family = dict(answerable_facts=denominator, answerable_groups=1 if denominator else 0, coverage=coverage,
                  group_coverage=[dict(answerable_facts=denominator, matched_facts=matched)] if denominator else [])
    return dict(cell_id=identifier, scientific_validation="not_established", critical_errors=[],
                adapter_status="scorable", answer_status="abstained" if abstain else "answered",
                completion=passes["80"] is True, family_scores={"reported_measurement":family},
                primary=dict(families=["reported_measurement"], passes=passes))


def synthetic_ledger():
    expected_outputs, expected_decisions = a.schedule()
    outputs = []
    for identifier, (case, arm) in expected_outputs.items():
        native = case in a.CASES
        row = dict(cell_id=identifier, case_id=case, arm=arm,
                   stratum="native" if native else "fictional_json_core", terminal="returned", received_terminal="returned",
                   strict_exact_report=arm != "A", full_source_admitted=True, full_verified_exact=arm != "A",
                   core_score=None, fact_accounting=None)
        row["core_score"] = score(identifier, matched=0 if arm=="A" else 4, abstain=arm=="A")
        row["fact_accounting"] = accounting(matched=0 if arm=="A" else 4, abstain=arm=="A")
        outputs.append(row)
    decisions = [dict(decision_id=identifier, output_cell_id=output, policy=policy,
                      verdict="rejected" if output.startswith("N-A-") else "admitted", terminal="returned", first_failure_stage=None)
                 for identifier, (output,policy) in expected_decisions.items()]
    return dict(schema_version=1, method=a.METHOD, status="COMPLETED_PENDING_INDEPENDENT_AUDIT",
                scientific_validation="not_established", fixture="ARBITRARY_SYNTHETIC_NOT_STUDY_RESULTS",
                planned_output_cells=38, planned_decisions=90, native_units=12, independent_studies=None,
                output_cells=outputs, decision_cells=decisions,
                native_qualification={case:dict(disposition="compiled",measurement_answerable_facts=4,measurement_answerable_groups=1)
                                      for case in a.CASES},
                resources={"wall_seconds":123,"physical_io_bytes":None}, source_verification={"amortized":True})


def output(ledger, identifier):
    return next(row for row in ledger["output_cells"] if row["cell_id"]==identifier)


def decision(ledger, identifier):
    return next(row for row in ledger["decision_cells"] if row["decision_id"]==identifier)


class PureAnalysisTests(unittest.TestCase):
    def test_fixed_schedule_and_no_mutation(self):
        ledger=synthetic_ledger(); before=deepcopy(ledger)
        result=a.analyze(ledger)
        self.assertEqual(ledger,before)
        self.assertEqual(result["planned_output_cells"],38)
        self.assertEqual(result["planned_decisions"],90)
        self.assertEqual(result["native_primary"]["verified_exact_count"],12)
        self.assertEqual(result["native_primary"]["completion_80_count"],12)
        self.assertEqual(result["inferential_statistics"],"none")
        self.assertIsNone(result["independent_study_count"])

    def test_omitted_duplicate_unscheduled_and_wrong_binding_rejected(self):
        for mutate in (lambda l:l["output_cells"].pop(), lambda l:l["decision_cells"].append(l["decision_cells"][0]),
                       lambda l:l["output_cells"][0].update(cell_id="UNSCHEDULED"),
                       lambda l:l["decision_cells"][0].update(policy="WIRE_ONLY")):
            ledger=synthetic_ledger(); mutate(ledger)
            with self.assertRaises(ValueError): a.analyze(ledger)

    def test_nonreturn_stays_in_twelve_denominator_and_qualified_secondary(self):
        ledger=synthetic_ledger(); row=output(ledger,"N-L-p05-01")
        row.update(terminal="timeout",received_terminal=None,core_score=None,fact_accounting=None,
                   strict_exact_report=None,full_source_admitted=None,full_verified_exact=None)
        for policy in a.POLICIES:
            decision(ledger,"D-N-L-p05-01-"+policy).update(verdict="no_decision",terminal="unexecuted")
        result=a.analyze(ledger)
        self.assertEqual(result["native_primary"]["completion_80_count"],11)
        self.assertEqual(result["native_primary"]["completion_80_rate"],11/12)
        self.assertEqual(result["native_secondary"]["qualified_nonzero_denominator"],12)
        self.assertIsNone(result["native_cases"][0]["literal"]["coverage"])

    def test_zero_denominator_exact_report_is_admitted_but_not_completed(self):
        ledger=synthetic_ledger()
        ledger["native_qualification"]["p05-01"].update(measurement_answerable_facts=0,measurement_answerable_groups=0)
        for arm in ("L","A"):
            row=output(ledger,f"N-{arm}-p05-01")
            row["core_score"]=score(row["cell_id"],denominator=0,matched=0,abstain=arm=="A")
            row["fact_accounting"]=accounting(answerable=0,matched=0,abstain=arm=="A")
        result=a.analyze(ledger)
        self.assertEqual(result["native_primary"]["verified_exact_count"],12)
        self.assertEqual(result["native_primary"]["completion_80_count"],11)
        self.assertEqual(result["native_secondary"]["qualified_nonzero_denominator"],11)
        self.assertIsNone(result["native_cases"][0]["literal"]["coverage"])

    def test_exact_threshold_from_counts_and_exactness_separate(self):
        ledger=synthetic_ledger()
        ledger["native_qualification"]["p05-01"].update(measurement_answerable_facts=5)
        for arm in ("L","A"):
            row=output(ledger,f"N-{arm}-p05-01")
            row["core_score"]=score(row["cell_id"],denominator=5,matched=4 if arm=="L" else 0,abstain=arm=="A")
            row["fact_accounting"]["families"]["reported_measurement"].update(requested=5,answerable=5)
        output(ledger,"N-L-p05-01").update(strict_exact_report=False,full_verified_exact=False)
        decision(ledger,"D-N-L-p05-01-FULL")["verdict"]="rejected"
        result=a.analyze(ledger)
        self.assertEqual(result["native_primary"]["completion_80_count"],12)
        self.assertEqual(result["native_primary"]["verified_exact_count"],11)
        self.assertEqual(result["native_cases"][0]["literal"]["thresholds"],{"60":True,"80":True,"100":False})

    def test_missing_unknown_counter_never_becomes_zero(self):
        ledger=synthetic_ledger()
        del output(ledger,"N-L-p05-01")["fact_accounting"]["families"]["reported_measurement"]["correct_unknown"]
        with self.assertRaises(ValueError): a.analyze(ledger)

    def test_fictional_unknown_only_control_is_separate_from_report_admission(self):
        ledger=synthetic_ledger(); row=output(ledger,"S-C04")
        row["core_score"]=score(row["cell_id"],denominator=0,matched=0)
        row["fact_accounting"]=accounting(answerable=0,matched=0)
        result=a.analyze(ledger)
        control=next(item for item in result["fictional_cases"] if item["scenario_id"]=="C04")
        self.assertTrue(control["verified_exact"])
        self.assertIsNone(control["measurement_coverage"])
        self.assertFalse(control["measurement_completion"])

    def test_exact_admission_without_scored_metadata_is_rejected(self):
        ledger=synthetic_ledger(); output(ledger,"S-C01")["core_score"]=None
        with self.assertRaises(ValueError): a.analyze(ledger)

    def test_wrong_coverage_completion_and_scientific_claim_fail(self):
        for mutate in (lambda l:output(l,"N-L-p05-01")["core_score"].update(completion=False),
                       lambda l:output(l,"N-L-p05-01")["core_score"]["family_scores"]["reported_measurement"].update(coverage=0.1),
                       lambda l:l.update(scientific_validation="established")):
            ledger=synthetic_ledger(); mutate(ledger)
            with self.assertRaises(ValueError): a.analyze(ledger)

    def test_planned_attempted_no_decision_and_paired_policy_counts(self):
        ledger=synthetic_ledger()
        decision(ledger,"D-S-C01-FULL")["verdict"]="rejected"
        output(ledger,"S-C01")["full_verified_exact"]=False
        decision(ledger,"D-S-C02-FULL").update(verdict="no_decision",terminal="unexecuted")
        output(ledger,"S-C02")["full_verified_exact"]=False
        result=a.analyze(ledger)
        valid=result["fictional_policies"]["FULL"]["false_rejection"]
        self.assertEqual((valid["planned_denominator"],valid["attempted_denominator"],valid["no_decision"],valid["error_count"]),(4,3,1,1))
        self.assertEqual(result["fictional_policies"]["WIRE_ONLY"]["false_acceptance"]["error_count"],10)
        self.assertEqual(result["fictional_paired_discordance"]["FULL_vs_WIRE_ONLY"]["discordant_attempted"],1)

    def test_no_decision_is_not_successful_rejection(self):
        ledger=synthetic_ledger()
        decision(ledger,"D-S-F01-WIRE_ONLY").update(verdict="no_decision",terminal="unexecuted")
        result=a.analyze(ledger)["fictional_policies"]["WIRE_ONLY"]["false_acceptance"]
        self.assertEqual((result["planned_denominator"],result["attempted_denominator"],result["no_decision"]),(10,9,1))
        self.assertEqual(result["error_count"],9)

    def test_producer_shaped_blank_ledger_integration_without_producer_oracle(self):
        # Import only serialization defaults; expected zero/unknown accounting is
        # specified independently here, never by the producer analyzer/guards.
        spec=importlib.util.spec_from_file_location("producer_shape_only",ROOT/"tools/science/run_source_validation_experiment.py")
        producer=importlib.util.module_from_spec(spec); spec.loader.exec_module(producer)
        outs,decs=producer.blank_ledgers()
        ledger=synthetic_ledger()
        ledger.update(status="FAILED_PARTIAL_NOT_QUALIFIED",output_cells=list(outs.values()),decision_cells=list(decs.values()),
            native_qualification={case:dict(disposition="unverified",measurement_answerable_facts=None,measurement_answerable_groups=None) for case in a.CASES})
        result=a.analyze(ledger)
        self.assertEqual(result["native_primary"]["completion_80_count"],0)
        self.assertEqual(result["native_secondary"]["unverified_qualification_count"],12)
        self.assertIsNone(result["native_secondary"]["qualified_nonzero_denominator"])
        self.assertEqual(result["decision_verdict_counts"],{"no_decision":90})

    def test_producer_serialized_fictional_c02_metrics_integration(self):
        # This exercises serialization interoperability, not an actual study.
        # The independent expected denominator=1 comes from frozen C02's single
        # answerable exponent, not from a producer verdict or compiler oracle.
        spec=importlib.util.spec_from_file_location("producer_metrics_shape_only",ROOT/"tools/science/run_source_validation_experiment.py")
        producer=importlib.util.module_from_spec(spec); spec.loader.exec_module(producer)
        with fictional_directory() as folder:
            root=Path(folder)/"fixtures"
            manifest=producer.author_fictional_fixtures(root)
            bounds=producer.Bounds(Path(folder))
            scenario,packet=producer.load_fictional(root,"C02",manifest,bounds)
            raw=producer.fictional_candidate(packet,"C02")
            metrics=producer.evaluate_fictional(scenario,packet,raw,bounds,approved_fixture_root=root)
            outs,decs=producer.blank_ledgers()
            outs["S-C02"].update(terminal="returned",received_terminal="returned")
            producer.retain_fictional_metrics(outs["S-C02"],metrics)
            for item in metrics["decisions"]:
                decs[item["decision_id"]].update(item)
            ledger=synthetic_ledger()
            ledger.update(status="FAILED_PARTIAL_NOT_QUALIFIED",output_cells=list(outs.values()),decision_cells=list(decs.values()),
                native_qualification={case:dict(disposition="unverified",measurement_answerable_facts=None,measurement_answerable_groups=None) for case in a.CASES})
            result=a.analyze(ledger)
            c02=next(row for row in result["fictional_cases"] if row["scenario_id"]=="C02")
            self.assertEqual(c02["answerable_measurement_groups"],1)
            self.assertEqual(c02["measurement_coverage"],1.0)
            self.assertTrue(c02["measurement_completion"])
            self.assertEqual(result["native_primary"]["completion_80_count"],0)


class AuditedCLIContractTests(unittest.TestCase):
    def audit(self,path,sha):
        return dict(status=a.AUDIT_STATUS,method=a.AUDIT_METHOD,subject=dict(ledger_path=str(path),ledger_sha256=sha),
                    source_inclusive=True,independent_projection=True,unresolved_findings=[],scientific_validation="not_established")

    def test_audit_status_binding_projection_and_external_hash_required(self):
        path=Path("D:/fictional/ledger.json"); audit=self.audit(path,"a"*64)
        a.validate_audit(audit,path,"a"*64)
        for change in ({"source_inclusive":False},{"unresolved_findings":["issue"]},{"status":"PASS"},{"independent_projection":False}):
            with self.assertRaises(ValueError): a.validate_audit({**audit,**change},path,"a"*64)
        with self.assertRaises(ValueError): a.validate_audit(audit,path,"b"*64)

    def test_cli_reads_only_pinned_audited_synthetic_json_and_fresh_output(self):
        with fictional_directory() as folder:
            workspace=Path(folder); derived=workspace/"data/derived"; derived.mkdir(parents=True)
            assets=workspace/"planning/review-assets/p05"; assets.mkdir(parents=True)
            lr=derived/"preprint-p05-experiment-20990101T000000Z"; lr.mkdir()
            lp=lr/"ledger.json"; raw=a.canonical(synthetic_ledger()); lp.write_bytes(raw); sha=hashlib.sha256(raw).hexdigest()
            ap=assets/"P06-AUDIT.json"; ar=a.canonical(self.audit(lp,sha)); ap.write_bytes(ar); ah=hashlib.sha256(ar).hexdigest()
            out=derived/"preprint-p05-analysis-20990101T000000Z"
            with patch.object(a,"DERIVED",derived),patch.object(a,"ASSETS",assets):
                result=a.run(lp,sha,ap,ah,out,approved_ledger_root=lr,approved_audit_root=assets)
                self.assertEqual(result["native_denominator"],12)
                self.assertTrue((out/"analysis-seal.json").is_file())
                self.assertEqual(result["execution"]["environment"]["dependencies"],"Python standard library only")
                self.assertEqual(result["execution"]["audit_sha256"],ah)
                with self.assertRaises(ValueError): a.run(lp,sha,ap,ah,out,approved_ledger_root=lr,approved_audit_root=assets)
                bad=derived/"preprint-p05-analysis-20990101T000001Z"
                with self.assertRaises(ValueError): a.run(lp,sha,ap,"0"*64,bad,approved_ledger_root=lr,approved_audit_root=assets)
                self.assertFalse(bad.exists())

    def test_audited_frozen_analyzer_pin_mismatch_rejected_before_output(self):
        with fictional_directory() as folder:
            workspace=Path(folder); derived=workspace/"data/derived"; derived.mkdir(parents=True)
            assets=workspace/"audit"; assets.mkdir()
            lr=derived/"preprint-p05-experiment-20990101T000000Z"; lr.mkdir()
            lp=lr/"ledger.json"; ledger=synthetic_ledger(); ledger["analysis_code_sha256"]="0"*64
            raw=a.canonical(ledger); lp.write_bytes(raw); sha=hashlib.sha256(raw).hexdigest()
            ap=assets/"P06.json"; ar=a.canonical(self.audit(lp,sha)); ap.write_bytes(ar)
            out=derived/"preprint-p05-analysis-20990101T000000Z"
            with patch.object(a,"DERIVED",derived),patch.object(a,"ASSETS",assets):
                with self.assertRaisesRegex(ValueError,"frozen analysis pin"):
                    a.run(lp,sha,ap,hashlib.sha256(ar).hexdigest(),out,approved_ledger_root=lr,approved_audit_root=assets)
            self.assertFalse(out.exists())

    def test_duplicate_json_and_unpinned_bytes_are_rejected(self):
        with self.assertRaises(ValueError): a._parse(b'{"x":1,"x":2}')
        with self.assertRaises(ValueError): a._parse(b'{"x":NaN}')
        with fictional_directory() as folder:
            path=Path(folder)/"a.json"; path.write_bytes(b'{}')
            with self.assertRaises(ValueError): a.read_pinned(path,"0"*64)


if __name__=="__main__":
    unittest.main()
